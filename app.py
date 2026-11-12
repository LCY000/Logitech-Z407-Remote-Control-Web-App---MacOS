import sys
import os
import json
import signal
import socket
import time
import tempfile
import asyncio
import logging
import ipaddress
import threading
import webbrowser
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
# Based on Z407 Reverse Engineering by freundTech: https://github.com/freundTech/logi-z407-reverse-engineering

import rumps

from quart import Quart, render_template, jsonify, request
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakBluetoothNotAvailableError

from z407_ble import COMMAND_UUID, RESPONSE_UUID, SERVICE_UUID, is_z407_device
from z407_config import RuntimeConfig, build_runtime_config, get_lan_ip
from z407_platform import (
    AccessibilityPermissionError,
    PlatformInfo,
    get_capabilities,
    send_host_media_key,
)
from z407_version import __version__


APP_ID = "z407-control"
CURRENT_PLATFORM = PlatformInfo()

SCAN_TIMEOUT_SECONDS = 8.0
CONNECT_TIMEOUT_SECONDS = 15.0
RETRY_DELAY_SECONDS = 3
VOLUME_MAX = 32   # confirmed by user: beeps at step 32+
BASS_MAX   = 15   # confirmed by user real-world testing
STEP_DELAY_SECONDS = 0.15       # pause between repeated level steps
ACK_SETTLE_SECONDS = 0.5        # wait for the last confirmations to arrive
CALIBRATION_MARGIN_STEPS = 5    # extra steps so we are sure to hit the floor

STATE_FILE = Path.home() / ".z407_control_state.json"
PREFS_FILE = Path.home() / ".z407_control_prefs.json"
DEFAULT_LANGUAGE = "en"

# Speaker commands (written to COMMAND_UUID). See doc/Protocol.md in freundTech's repo.
SPEAKER_COMMAND_CODES = {
    "bass_up": "8000",
    "bass_down": "8001",
    "vol_up": "8002",
    "vol_down": "8003",
    "play_pause": "8004",
    "next_speaker": "8005",
    "prev_speaker": "8006",
    "input_bluetooth": "8101",
    "input_aux": "8102",
    "input_usb": "8103",
    "bluetooth_pair": "8200",
    "factory_reset": "8300",
}
HANDSHAKE_INITIATE = "8405"
HANDSHAKE_ACKNOWLEDGE = "8400"

# Speaker notifications (received on RESPONSE_UUID).
LEVEL_CONFIRMATIONS = {
    b"\xc0\x00": ("bass", +1),
    b"\xc0\x01": ("bass", -1),
    b"\xc0\x02": ("volume", +1),
    b"\xc0\x03": ("volume", -1),
}
INPUT_NOTIFICATIONS = {
    b"\xc1\x01": "bluetooth",
    b"\xc1\x02": "aux",
    b"\xc1\x03": "usb",
    b"\xcf\x04": "bluetooth",
    b"\xcf\x05": "aux",
    b"\xcf\x06": "usb",
}
FACTORY_RESET_CONFIRMED = b"\xc3\x00"
LEVEL_LIMITS = {"volume": VOLUME_MAX, "bass": BASS_MAX}
LEVEL_COMMANDS = {"volume": ("vol_up", "vol_down"), "bass": ("bass_up", "bass_down")}
VALID_INPUTS = ("aux", "usb", "bluetooth")

HOST_MEDIA_COMMANDS = {
    "next",
    "prev",
    "play_pause_pc",
    "vol_up_pc",
    "vol_down_pc",
    "mute_pc",
}
BLE_SPEAKER_COMMANDS = set(SPEAKER_COMMAND_CODES)
SUPPORTED_COMMANDS = HOST_MEDIA_COMMANDS | BLE_SPEAKER_COMMANDS

# Commands that only the Mac running the app may trigger (never a phone on the LAN).
LOCAL_ONLY_COMMANDS = {"factory_reset"}

# Every state-changing request must carry this header. Browsers refuse to let another
# website add a custom header without a CORS preflight, which this server never grants,
# so a random web page cannot drive the speaker behind the user's back.
CLIENT_HEADER = "X-Z407-Client"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
LOOPBACK_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}

QUIET_LOGGER_NAMES = ("hypercorn.access", "quart.serving")


def _asset_path(*parts: str) -> str:
    base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


app = Quart(
    __name__,
    template_folder=_asset_path("templates"),
    static_folder=_asset_path("static"),
)


class SpeakerError(RuntimeError):
    """A speaker operation failed in a way the UI can explain (see `code`)."""

    def __init__(self, code: str, message: str, status: int = 500):
        super().__init__(message)
        self.code = code
        self.status = status


class SpeakerState:
    """Last known volume / bass / input, persisted across restarts.

    The Z407 never reports absolute levels, so they are counted from the
    confirmations it sends after each step. `None` means "not calibrated yet".
    """

    def __init__(self) -> None:
        self.volume: int | None = None
        self.bass: int | None = None
        self.input: str | None = None

    def load(self) -> None:
        try:
            data = json.loads(STATE_FILE.read_text())
        except Exception:
            return
        if not isinstance(data, dict):
            return
        self.volume = self._clean_level(data.get("volume"), VOLUME_MAX)
        self.bass = self._clean_level(data.get("bass"), BASS_MAX)
        self.input = data.get("input") if data.get("input") in VALID_INPUTS else None

    @staticmethod
    def _clean_level(value, maximum: int) -> int | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return max(0, min(maximum, int(value)))

    def save(self) -> None:
        payload = json.dumps({"volume": self.volume, "bass": self.bass, "input": self.input})
        try:
            tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
            tmp.write_text(payload)
            os.replace(tmp, STATE_FILE)
        except Exception as e:
            logging.warning("Could not save state to %s: %s", STATE_FILE, e)

    def apply_notification(self, data: bytes) -> bool:
        """Update from a speaker notification. Returns True for a level confirmation."""
        if data in LEVEL_CONFIRMATIONS:
            name, delta = LEVEL_CONFIRMATIONS[data]
            current = getattr(self, name)
            if current is not None:
                setattr(self, name, max(0, min(LEVEL_LIMITS[name], current + delta)))
                self.save()
            return True
        if data in INPUT_NOTIFICATIONS:
            self.input = INPUT_NOTIFICATIONS[data]
            self.save()
        elif data == FACTORY_RESET_CONFIRMED:
            # Levels after a reset are unknown until the next calibration.
            self.volume = self.bass = self.input = None
            self.save()
        return False


class Preferences:
    """Choices the user made in the page, kept on the Mac so every browser sees them."""

    def __init__(self) -> None:
        self.language: str | None = None             # None = not chosen yet
        self.calibration_hint_dismissed = False      # first-run reminder already handled

    def load(self) -> None:
        try:
            data = json.loads(PREFS_FILE.read_text())
        except Exception:
            return
        if not isinstance(data, dict):
            return
        language = data.get("language")
        self.language = language if isinstance(language, str) else None
        self.calibration_hint_dismissed = data.get("calibrationHintDismissed") is True

    def save(self) -> None:
        payload = json.dumps(
            {"language": self.language, "calibrationHintDismissed": self.calibration_hint_dismissed}
        )
        try:
            tmp = PREFS_FILE.with_name(PREFS_FILE.name + ".tmp")
            tmp.write_text(payload)
            os.replace(tmp, PREFS_FILE)
        except Exception as e:
            logging.warning("Could not save preferences to %s: %s", PREFS_FILE, e)


# --- Global runtime state ---
remote_control = None
speaker_state = SpeakerState()
preferences = Preferences()
runtime_config = RuntimeConfig(host="127.0.0.1", port=8765, lan_enabled=False, preferred_input="aux")
connection_state = "starting"
last_error = None
last_error_code = None
busy_task = None            # "calibrating" | "adjusting" | None
_link_changed = None        # asyncio.Event: wakes the connection manager
_background_tasks: list = []
_server_loop = None
_shutdown_event = None
_shutdown_requested = False


def set_link_state(state: str, error: str | None = None, code: str | None = None) -> None:
    global connection_state, last_error, last_error_code
    connection_state = state
    last_error = error
    last_error_code = code if error else None


def _notify_link_changed() -> None:
    if _link_changed is not None:
        _link_changed.set()


def log(message: str) -> None:
    print(message, flush=True)


def configure_terminal_logging(config: RuntimeConfig) -> None:
    if not config.quiet_logs:
        return

    for logger_name in QUIET_LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        logger.disabled = True
        logger.propagate = False


def handle_process_termination(_signum, _frame):
    raise KeyboardInterrupt


def schedule_browser_open(config: RuntimeConfig) -> None:
    """Open the page as soon as the server answers, instead of guessing a delay."""

    def wait_then_open() -> None:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", config.port), timeout=0.3):
                    break
            except OSError:
                time.sleep(0.15)
        else:
            return  # the server never came up; an error is already being shown
        webbrowser.open(config.local_url)

    threading.Thread(target=wait_then_open, daemon=True).start()


# --- Speaker link ---

class DemoDevice:
    address = "demo"
    name = "Z407 (demo)"


class DemoClient:
    """Stands in for BleakClient with --demo: answers like a real Z407 would."""

    _REPLIES = {
        "8405": [b"\xd4\x05\x01"],
        "8400": [b"\xd4\x00\x01", b"\xd4\x00\x03"],
        "8101": [b"\xc1\x01", b"\xcf\x04"],
        "8102": [b"\xc1\x02", b"\xcf\x05"],
        "8103": [b"\xc1\x03", b"\xcf\x06"],
    }

    def __init__(self) -> None:
        self._callback = None

    async def connect(self) -> None:
        await asyncio.sleep(0.4)

    async def disconnect(self) -> None:
        return None

    async def start_notify(self, _uuid, callback) -> None:
        self._callback = callback

    async def write_gatt_char(self, _uuid, data, response=False) -> None:
        command = bytes(data).hex()
        replies = self._REPLIES.get(command)
        if replies is None and command.startswith("8"):
            replies = [bytes.fromhex("c" + command[1:])]
        for reply in replies or []:
            asyncio.get_running_loop().create_task(self._callback(None, bytearray(reply)))


class Z407Remote:
    def __init__(self, device, client=None, state: SpeakerState | None = None):
        self.device = device
        self.address = getattr(device, "address", "unknown")
        self.name = getattr(device, "name", None) or "Logitech Z407"
        self.state = state if state is not None else speaker_state
        self.client = client if client is not None else BleakClient(
            device,
            disconnected_callback=self._handle_disconnect,
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
        self.connected = False
        self.level_confirmations = 0

    def _handle_disconnect(self, _client=None) -> None:
        """Called by bleak when the speaker drops the link (power loss, out of range...)."""
        was_connected = self.connected
        self.connected = False
        if was_connected and remote_control is self:
            set_link_state("disconnected")
            log("Speaker disconnected. Reconnecting in the background...")
        _notify_link_changed()

    async def connect(self):
        log(f"Connecting to {self.name} ({self.address})...")
        set_link_state("connecting")
        try:
            await self.client.connect()
            self.connected = True
            await self.client.start_notify(RESPONSE_UUID, self._receive_data)
            await self._write(HANDSHAKE_INITIATE)
            set_link_state("connected")
        except Exception as e:
            self.connected = False
            set_link_state("error", str(e) or type(e).__name__, "connect_failed")
            log(f"Failed to connect: {e}")
            try:
                await self.client.disconnect()
            except Exception:
                pass

    async def disconnect(self):
        was_connected = self.connected
        self.connected = False
        if was_connected:
            await self.client.disconnect()

    async def _receive_data(self, _sender, data: bytearray):
        data = bytes(data)
        if data == b"\xd4\x05\x01":
            await self._write(HANDSHAKE_ACKNOWLEDGE)
        elif data in (b"\xd4\x00\x01", b"\xd4\x00\x03"):
            self.connected = True
        elif self.state.apply_notification(data):
            self.level_confirmations += 1

    async def _write(self, hex_command: str) -> None:
        try:
            await self.client.write_gatt_char(COMMAND_UUID, bytes.fromhex(hex_command), response=False)
        except Exception as e:
            self.connected = False
            if remote_control is self:
                set_link_state("error", str(e) or type(e).__name__, "write_failed")
            log(f"Error sending command: {e}")
            _notify_link_changed()
            raise

    async def send(self, command: str) -> None:
        if not self.connected:
            raise SpeakerError("not_connected", "Speaker is not connected", 503)
        await self._write(SPEAKER_COMMAND_CODES[command])


async def find_device():
    """Scan until a Z407 shows up (returns early) or the timeout passes."""
    if runtime_config.demo:
        await asyncio.sleep(0.6)
        return DemoDevice()

    set_link_state("scanning")
    try:
        device = await BleakScanner.find_device_by_filter(is_z407_device, timeout=SCAN_TIMEOUT_SECONDS)
    except BleakBluetoothNotAvailableError as e:
        set_link_state("error", str(e) or "Bluetooth is unavailable", "bluetooth_unavailable")
        return None
    except Exception as e:
        set_link_state("error", str(e) or type(e).__name__, "scan_failed")
        log(f"Error during scan: {e}")
        return None

    if device is None:
        set_link_state("not_found", "Speakers not found", "speaker_not_found")
    return device


async def manage_connection():
    """Keep the speaker connected for the whole life of the app.

    Scans and connects, then sleeps until the link drops and starts over.
    """
    global remote_control, _link_changed
    if _link_changed is None:
        _link_changed = asyncio.Event()
    announced = set()

    def announce_once(key: str, message: str) -> None:
        if key not in announced or not runtime_config.quiet_logs:
            log(message)
            announced.add(key)

    log("Starting background connection manager...")

    while True:
        if remote_control is not None and remote_control.connected:
            _link_changed.clear()
            if remote_control.connected:
                await _link_changed.wait()
            continue

        device = await find_device()
        if device is None:
            announce_once("not_found", "Z407 not found yet. The web UI is still available; retrying in the background.")
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            continue

        client = DemoClient() if runtime_config.demo else None
        remote = Z407Remote(device, client=client)
        remote_control = remote
        await remote.connect()
        if remote.connected:
            log(f"Connected to {remote.name} ({remote.address}).")
            announced.clear()
            continue

        announce_once(
            "connect_failed",
            "Z407 was found but connection failed. The web UI is still available; retrying in the background.",
        )
        await asyncio.sleep(RETRY_DELAY_SECONDS)


@app.before_serving
async def startup():
    global _link_changed
    _link_changed = asyncio.Event()
    speaker_state.load()
    preferences.load()
    _background_tasks.append(asyncio.create_task(manage_connection()))


@app.after_serving
async def cleanup():
    for task in _background_tasks:
        task.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    _background_tasks.clear()
    if remote_control is not None:
        try:
            await asyncio.wait_for(remote_control.disconnect(), timeout=3)
        except Exception as e:
            log(f"Could not disconnect cleanly: {e}")


# --- Request guards ---

def _hostname_of(host_header: str) -> str:
    host = (host_header or "").strip().lower()
    if host.startswith("["):  # [::1]:8765
        return host[1:].split("]", 1)[0]
    return host.rsplit(":", 1)[0] if ":" in host else host


def _is_ip_literal(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def is_allowed_host(host_header: str, lan_enabled: bool) -> bool:
    """Reject unexpected Host headers so DNS rebinding cannot reach the API."""
    hostname = _hostname_of(host_header)
    if hostname in LOOPBACK_HOSTNAMES:
        return True
    if not lan_enabled:
        return False
    return _is_ip_literal(hostname) or hostname.endswith(".local")


def is_local_client() -> bool:
    address = request.remote_addr or ""
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


def fail(status: int, code: str, message: str):
    return jsonify(success=False, error=message, code=code), status


@app.before_request
async def guard_request():
    if not is_allowed_host(request.headers.get("Host", ""), runtime_config.lan_enabled):
        return fail(403, "forbidden_host", "Forbidden host")

    if request.method in SAFE_METHODS:
        return None

    origin = request.headers.get("Origin")
    if origin is not None:
        if urlsplit(origin).netloc.lower() != request.headers.get("Host", "").lower():
            return fail(403, "forbidden_origin", "Cross-site requests are not allowed")
    if request.headers.get(CLIENT_HEADER) != "1":
        return fail(403, "missing_client_header", f"Missing {CLIENT_HEADER} header")
    return None


@app.after_request
async def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    # Always revalidate: an updated app must never be driven by a stale cached page.
    response.headers["Cache-Control"] = "no-cache"
    return response


# --- Routes ---

def load_translations() -> dict:
    with open(_asset_path("static", "i18n.json"), encoding="utf-8") as handle:
        return json.load(handle)


TRANSLATIONS = load_translations()

# Everything the page needs is served from this app; nothing may be loaded from elsewhere.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; object-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


def saved_language() -> str:
    """The language chosen in the page, or English until someone chooses."""
    return preferences.language if preferences.language in TRANSLATIONS else DEFAULT_LANGUAGE


@app.route('/')
async def index():
    response = await app.make_response(
        await render_template(
            'index.html',
            version=__version__,
            i18n=TRANSLATIONS,
            language=saved_language(),
        )
    )
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    return response


def status_payload() -> dict:
    connected = bool(remote_control and remote_control.connected)
    return dict(
        app=APP_ID,
        version=__version__,
        connected=connected,
        connectionState="connected" if connected else connection_state,
        volume=speaker_state.volume,
        bass=speaker_state.bass,
        input=speaker_state.input,
        volumeMax=VOLUME_MAX,
        bassMax=BASS_MAX,
        busy=busy_task,
        platform=CURRENT_PLATFORM.key,
        networkMode="lan" if runtime_config.lan_enabled else "local",
        lanUrl=runtime_config.lan_url(get_lan_ip()) if runtime_config.lan_enabled else None,
        localClient=is_local_client(),
        preferredInput=runtime_config.preferred_input,
        demo=runtime_config.demo,
        language=saved_language(),
        calibrationHintDismissed=preferences.calibration_hint_dismissed,
        lastError=None if connected else last_error,
        lastErrorCode=None if connected else last_error_code,
    )


@app.route('/api/status')
async def get_status():
    return jsonify(status_payload())


@app.route("/api/capabilities")
async def capabilities():
    return jsonify(
        get_capabilities(
            CURRENT_PLATFORM,
            preferred_input=runtime_config.preferred_input,
            lan_enabled=runtime_config.lan_enabled,
        )
    )


@app.route('/api/preferences', methods=['POST'])
async def update_preferences():
    """Remember page choices (language, first-run reminder) on the Mac."""
    body = await request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail(400, "bad_request", "Expected a JSON object")

    if "language" in body:
        if body["language"] not in TRANSLATIONS:
            return fail(400, "bad_request", f"language must be one of {sorted(TRANSLATIONS)}")
        preferences.language = body["language"]
    if "calibrationHintDismissed" in body:
        if not isinstance(body["calibrationHintDismissed"], bool):
            return fail(400, "bad_request", "calibrationHintDismissed must be true or false")
        preferences.calibration_hint_dismissed = body["calibrationHintDismissed"]

    preferences.save()
    return jsonify(success=True, **status_payload())


def request_shutdown() -> None:
    """Ask the web server to stop (thread-safe). The app quits once it has."""
    global _shutdown_requested
    _shutdown_requested = True
    if _server_loop is not None and _shutdown_event is not None:
        _server_loop.call_soon_threadsafe(_shutdown_event.set)


@app.route('/api/shutdown', methods=['POST'])
async def shutdown():
    if not is_local_client():
        return fail(403, "local_only", "Only the Mac running the app can quit it")
    log("Shutting down via web request...")
    # Give this response time to reach the browser before the server stops.
    asyncio.get_running_loop().call_later(0.5, request_shutdown)
    return jsonify(success=True, message="Shutting down...")


def _connected_remote():
    if remote_control is None or not remote_control.connected:
        _notify_link_changed()
        raise SpeakerError("not_connected", "Speaker is not connected", 503)
    if busy_task is not None:
        raise SpeakerError("busy", "The speaker is busy, try again in a moment", 409)
    return remote_control


@contextmanager
def _exclusive(task_name: str):
    """Claim the speaker for a multi-step operation; other commands get "busy"."""
    global busy_task
    remote = _connected_remote()   # raises before the flag is taken
    busy_task = task_name
    try:
        yield remote
    finally:
        busy_task = None


async def _step(remote, command: str, count: int) -> None:
    for _ in range(count):
        await remote.send(command)
        await asyncio.sleep(STEP_DELAY_SECONDS)


@app.route('/api/calibrate', methods=['POST'])
async def calibrate():
    """Drive volume and bass to their floor so counting can start from a known 0."""
    try:
        with _exclusive("calibrating") as remote:
            confirmations_before = remote.level_confirmations
            await _step(remote, "vol_down", VOLUME_MAX + CALIBRATION_MARGIN_STEPS)
            await _step(remote, "bass_down", BASS_MAX + CALIBRATION_MARGIN_STEPS)
            await asyncio.sleep(ACK_SETTLE_SECONDS)
            if remote.level_confirmations == confirmations_before:
                # The Z407 ignores level commands while no audio is playing.
                raise SpeakerError(
                    "no_confirmation",
                    "The speaker did not confirm any step. Play some audio and calibrate again.",
                    409,
                )
            speaker_state.volume = 0
            speaker_state.bass = 0
            speaker_state.save()
            if not preferences.calibration_hint_dismissed:
                preferences.calibration_hint_dismissed = True   # first run is done
                preferences.save()
        return jsonify(success=True, **status_payload())
    except SpeakerError as e:
        return fail(e.status, e.code, str(e))
    except Exception as e:
        return fail(500, "command_failed", str(e))


@app.route('/api/set_level', methods=['POST'])
async def set_level():
    """Move volume or bass to an absolute step (needs a calibrated counter)."""
    body = await request.get_json(silent=True) or {}
    target, value = body.get("target"), body.get("value")
    if target not in LEVEL_LIMITS:
        return fail(400, "bad_request", "target must be 'volume' or 'bass'")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= LEVEL_LIMITS[target]:
        return fail(400, "bad_request", f"value must be an integer from 0 to {LEVEL_LIMITS[target]}")

    try:
        with _exclusive("adjusting") as remote:
            current = getattr(speaker_state, target)
            if current is None:
                raise SpeakerError("not_calibrated", "Calibrate first so the current level is known", 409)
            up_command, down_command = LEVEL_COMMANDS[target]
            difference = value - current
            if difference:
                await _step(remote, up_command if difference > 0 else down_command, abs(difference))
                await asyncio.sleep(ACK_SETTLE_SECONDS)
        reached = getattr(speaker_state, target) == value
        return jsonify(success=True, reached=reached, **status_payload())
    except SpeakerError as e:
        return fail(e.status, e.code, str(e))
    except Exception as e:
        return fail(500, "command_failed", str(e))


@app.route('/api/<command>', methods=['POST'])
async def handle_command(command):
    if command not in SUPPORTED_COMMANDS:
        return fail(400, "unknown_command", "Unknown command")

    if command in LOCAL_ONLY_COMMANDS and not is_local_client():
        return fail(403, "local_only", "This action is only allowed from the Mac running the app")

    try:
        if command in HOST_MEDIA_COMMANDS:
            await send_host_media_key(command, CURRENT_PLATFORM)
        else:
            await _connected_remote().send(command)
        return jsonify(success=True)
    except SpeakerError as e:
        return fail(e.status, e.code, str(e))
    except AccessibilityPermissionError as e:
        return fail(403, "accessibility_required", str(e))
    except Exception as e:
        return fail(500, "command_failed", str(e))


# --- Process lifecycle (web server thread + menu bar on the main thread) ---

def _quit_menu_bar_app() -> None:
    try:
        from PyObjCTools import AppHelper
        AppHelper.callAfter(rumps.quit_application)
    except Exception:
        os._exit(0)


def _run_quart_server() -> None:
    # hypercorn installs signal handlers unless given a shutdown_trigger, and signal
    # handlers only work on the main thread (which belongs to the menu bar here).
    async def _serve() -> None:
        global _server_loop, _shutdown_event
        _server_loop = asyncio.get_running_loop()
        _shutdown_event = asyncio.Event()
        if _shutdown_requested:
            return
        await app.run_task(
            host=runtime_config.host,
            port=runtime_config.port,
            shutdown_trigger=_shutdown_event.wait,
        )

    try:
        asyncio.run(_serve())
    except Exception as e:
        log(f"Web server stopped unexpectedly: {e}")
    finally:
        # Whether it stopped on request or crashed, a menu bar icon without a
        # server behind it is useless — take the whole app down.
        _quit_menu_bar_app()


def probe_port(port: int) -> str:
    """What is listening on 127.0.0.1:port? Returns "free", "self" or "other"."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            pass
    except OSError:
        return "free"

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, dict) and payload.get("app") == APP_ID:
            return "self"
    except Exception:
        pass
    return "other"


def show_startup_error(message: str) -> None:
    log("\n" + "!" * 60)
    log(message)
    log("!" * 60)
    if getattr(sys, "frozen", False):
        try:
            rumps.alert(title="Z407 Control", message=message)
        except Exception:
            pass


class Z407MenuBar(rumps.App):
    def __init__(self, config: RuntimeConfig) -> None:
        icon_path = _asset_path("assets", "icon_menubar.png")
        super().__init__(
            "Z407 Control",
            icon=None,   # set manually below so we can control the display size
            template=True,
            quit_button=None,
        )
        self._config = config
        self.menu = ["Open Z407 Control", None, "Quit"]
        # Load the high-res source image and pin its display size to 18pt so the
        # menu bar renders a sharp scaled-down version instead of a huge icon.
        if os.path.exists(icon_path):
            try:
                from AppKit import NSImage, NSSize
                img = NSImage.alloc().initByReferencingFile_(icon_path)
                img.setSize_(NSSize(18, 18))
                img.setTemplate_(True)
                self._status_item.button().setImage_(img)
            except Exception:
                self.icon = icon_path  # fallback: let rumps handle it

    @rumps.clicked("Open Z407 Control")
    def open_web(self, _) -> None:
        webbrowser.open(self._config.local_url)

    @rumps.clicked("Quit")
    def do_quit(self, _) -> None:
        log("Quitting via menu bar...")
        if _server_loop is None:
            rumps.quit_application()
            return
        # Stop the server first so the speaker link is closed cleanly; the server
        # thread then quits the app. The timer is a safety net if that stalls.
        request_shutdown()
        fallback = threading.Timer(4.0, lambda: os._exit(0))
        fallback.daemon = True
        fallback.start()


def main() -> int:
    global runtime_config, STATE_FILE, PREFS_FILE
    runtime_config = build_runtime_config()
    if runtime_config.demo:
        # Never let simulated levels overwrite the real speaker's saved state.
        STATE_FILE = Path(tempfile.gettempdir()) / "z407_control_demo_state.json"
        PREFS_FILE = Path(tempfile.gettempdir()) / "z407_control_demo_prefs.json"
    configure_terminal_logging(runtime_config)
    signal.signal(signal.SIGTERM, handle_process_termination)

    occupant = probe_port(runtime_config.port)
    if occupant == "self":
        log(f"Z407 Control is already running at {runtime_config.local_url}.")
        if runtime_config.open_browser:
            webbrowser.open(runtime_config.local_url)
        return 0
    if occupant == "other":
        show_startup_error(
            f"Port {runtime_config.port} is already used by another program.\n"
            f"Close that program, or start Z407 Control with a different port (--port 9090)."
        )
        return 1

    log("\n" + "#" * 60)
    log(f"   LOGITECH Z407 REMOTE CONTROL  v{__version__}")
    log(f"\n   Local: {runtime_config.local_url}")
    if runtime_config.lan_enabled:
        log(f"   LAN:   {runtime_config.lan_url(get_lan_ip())}")
    else:
        log("   LAN:   disabled. Use --lan to control from a phone on the same Wi-Fi.")
    log(f"   Input: {runtime_config.preferred_input.upper()} recommended")
    if runtime_config.demo:
        log("   Demo mode: simulating a speaker, no Bluetooth is used.")
    log("\n   Quit: click the menu bar icon or press Ctrl+C.")
    log("   Do not use Ctrl+Z; it suspends the app instead of closing it.")
    log("#" * 60 + "\n")

    if runtime_config.open_browser:
        schedule_browser_open(runtime_config)

    server_thread = threading.Thread(target=_run_quart_server, daemon=True)
    server_thread.start()

    try:
        menu_bar = Z407MenuBar(runtime_config)
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyAccessory
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception:
            pass
        menu_bar.run()
    except KeyboardInterrupt:
        pass
    finally:
        # Reached on Ctrl+C: close the speaker link before the process exits.
        request_shutdown()
        server_thread.join(timeout=4)

    log("\nGoodbye!")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        show_startup_error(f"Z407 Control failed to start.\n{e}")
        if sys.stdin is not None and sys.stdin.isatty():
            log("\nPress ENTER to close the window...")
            input()
        sys.exit(1)
