# macOS-First Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current Linux-oriented Logitech Z407 web remote into a macOS-first web app that supports local and LAN browser control, AUX-first Mac usage, safer defaults, modern UI, and bilingual documentation.

**Architecture:** Keep the Quart web app and BLE command model, but split platform/config behavior into small testable modules. Use macOS-safe defaults (`127.0.0.1:8765`), explicit `--lan`, BLE clients initialized from discovered `BLEDevice` objects, and a frontend that consumes platform capabilities instead of hardcoded Linux help text.

**Tech Stack:** Python 3, Quart, Bleak, PyAutoGUI, PyInstaller, shell scripts, HTML/CSS/vanilla JavaScript, pytest.

---

## File Structure

- Modify `app.py`: keep the Quart entry point, but route CLI/config/platform calls through helper modules; use `BLEDevice` in `Z407Remote`; expose status and capabilities APIs.
- Create `z407_config.py`: parse runtime defaults and build local/LAN URLs.
- Create `z407_platform.py`: detect OS, provide host media key handling, platform labels, permission/help text, and recommended input.
- Create `tests/test_config.py`: tests for host/port/LAN behavior.
- Create `tests/test_platform.py`: tests for macOS/Linux/unknown capability data.
- Create `tests/test_app_api.py`: tests for `/api/status` and `/api/capabilities` without BLE hardware.
- Modify `templates/index.html`: replace Linux-styled UI with a modern macOS-first responsive single-page control panel.
- Create `run_macos.sh`: source-run helper for macOS that creates a venv, installs dependencies, starts `127.0.0.1:8765`, and opens the browser.
- Modify `requirements.txt`: add `pytest` for local verification.
- Modify `README.md`: rewrite top sections for macOS-first usage while preserving original credits, disclaimer, and donations/support sections.
- Create `README.zh-TW.md`: Traditional Chinese usage guide linked from the English README.

## Task 1: Add Runtime Configuration Module

**Files:**
- Create: `z407_config.py`
- Create: `tests/test_config.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add pytest dependency**

Edit `requirements.txt` to contain exactly:

```txt
quart
bleak
pyinstaller
pyautogui
pytest
```

- [ ] **Step 2: Write failing tests for runtime config**

Create `tests/test_config.py`:

```python
from z407_config import RuntimeConfig, build_runtime_config, get_lan_ip


def test_default_runtime_config_is_macos_safe_local_mode():
    config = build_runtime_config([])

    assert config.host == "127.0.0.1"
    assert config.port == 8765
    assert config.lan_enabled is False
    assert config.preferred_input == "aux"


def test_lan_mode_binds_all_interfaces():
    config = build_runtime_config(["--lan"])

    assert config.host == "0.0.0.0"
    assert config.port == 8765
    assert config.lan_enabled is True


def test_manual_ip_and_port_override_defaults():
    config = build_runtime_config(["--ip", "192.168.1.20", "--port", "9090"])

    assert config.host == "192.168.1.20"
    assert config.port == 9090
    assert config.lan_enabled is True


def test_runtime_urls_include_local_and_lan_when_lan_enabled():
    config = RuntimeConfig(host="0.0.0.0", port=8765, lan_enabled=True, preferred_input="aux")

    assert config.local_url == "http://127.0.0.1:8765"
    assert config.lan_url("192.168.1.8") == "http://192.168.1.8:8765"


def test_get_lan_ip_returns_loopback_fallback_when_socket_fails(monkeypatch):
    class BrokenSocket:
        def connect(self, _target):
            raise OSError("network unavailable")

        def close(self):
            pass

    class BrokenSocketModule:
        AF_INET = 2
        SOCK_DGRAM = 2

        def socket(self, *_args):
            return BrokenSocket()

    monkeypatch.setattr("z407_config.socket", BrokenSocketModule())

    assert get_lan_ip() == "127.0.0.1"
```

- [ ] **Step 3: Run config tests and verify failure**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: fails with `ModuleNotFoundError: No module named 'z407_config'`.

- [ ] **Step 4: Implement `z407_config.py`**

Create `z407_config.py`:

```python
from __future__ import annotations

import argparse
import socket
from dataclasses import dataclass


DEFAULT_HOST = "127.0.0.1"
DEFAULT_LAN_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_PREFERRED_INPUT = "aux"


@dataclass(frozen=True)
class RuntimeConfig:
    host: str
    port: int
    lan_enabled: bool
    preferred_input: str

    @property
    def local_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def lan_url(self, lan_ip: str) -> str:
        return f"http://{lan_ip}:{self.port}"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Logitech Z407 Remote Control Server")
    parser.add_argument("--ip", type=str, default=None, help="Host IP to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind to (default: {DEFAULT_PORT})")
    parser.add_argument("--lan", action="store_true", help="Expose the web app to other devices on the local network")
    parser.add_argument(
        "--preferred-input",
        choices=("aux", "usb", "bluetooth"),
        default=DEFAULT_PREFERRED_INPUT,
        help="Input source to emphasize in the UI",
    )
    return parser


def build_runtime_config(argv: list[str] | None = None) -> RuntimeConfig:
    args = build_arg_parser().parse_args(argv)
    host = args.ip
    lan_enabled = args.lan

    if host is None:
        host = DEFAULT_LAN_HOST if args.lan else DEFAULT_HOST
    elif host not in ("127.0.0.1", "localhost"):
        lan_enabled = True

    return RuntimeConfig(
        host=host,
        port=args.port,
        lan_enabled=lan_enabled,
        preferred_input=args.preferred_input,
    )


def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()
```

- [ ] **Step 5: Run config tests and verify pass**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt z407_config.py tests/test_config.py
git commit -m "Add runtime configuration for macOS defaults"
```

## Task 2: Add Platform Capability Module

**Files:**
- Create: `z407_platform.py`
- Create: `tests/test_platform.py`

- [ ] **Step 1: Write failing platform tests**

Create `tests/test_platform.py`:

```python
import pytest

from z407_platform import PlatformInfo, get_capabilities, media_key_name


def test_macos_capabilities_are_aux_first():
    info = PlatformInfo(system="darwin")
    capabilities = get_capabilities(info, preferred_input="aux", lan_enabled=False)

    assert capabilities["platform"] == "macos"
    assert capabilities["preferredInput"] == "aux"
    assert capabilities["networkMode"] == "local"
    assert "AUX audio + BLE control" in capabilities["setupHint"]
    assert "Accessibility" in " ".join(capabilities["permissionNotes"])


def test_linux_capabilities_keep_xdotool_hint():
    info = PlatformInfo(system="linux")
    capabilities = get_capabilities(info, preferred_input="aux", lan_enabled=True)

    assert capabilities["platform"] == "linux"
    assert capabilities["networkMode"] == "lan"
    assert any("xdotool" in note for note in capabilities["permissionNotes"])


def test_unknown_capabilities_do_not_claim_media_keys_supported():
    info = PlatformInfo(system="freebsd")
    capabilities = get_capabilities(info, preferred_input="aux", lan_enabled=False)

    assert capabilities["platform"] == "unknown"
    assert capabilities["hostMediaKeysSupported"] is False


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("next", "nexttrack"),
        ("prev", "prevtrack"),
        ("play_pause_pc", "playpause"),
        ("vol_up_pc", "volumeup"),
        ("vol_down_pc", "volumedown"),
        ("mute_pc", "volumemute"),
    ],
)
def test_media_key_names(command, expected):
    assert media_key_name(command) == expected
```

- [ ] **Step 2: Run platform tests and verify failure**

Run:

```bash
pytest tests/test_platform.py -v
```

Expected: fails with `ModuleNotFoundError: No module named 'z407_platform'`.

- [ ] **Step 3: Implement `z407_platform.py`**

Create `z407_platform.py`:

```python
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

import pyautogui


@dataclass(frozen=True)
class PlatformInfo:
    system: str = sys.platform

    @property
    def key(self) -> str:
        if self.system == "darwin":
            return "macos"
        if self.system.startswith("linux"):
            return "linux"
        if self.system.startswith("win"):
            return "windows"
        return "unknown"


MEDIA_KEY_MAP = {
    "next": "nexttrack",
    "prev": "prevtrack",
    "play_pause_pc": "playpause",
    "vol_up_pc": "volumeup",
    "vol_down_pc": "volumedown",
    "mute_pc": "volumemute",
}

LINUX_XF86_MAP = {
    "next": "XF86AudioNext",
    "prev": "XF86AudioPrev",
    "play_pause_pc": "XF86AudioPlay",
    "vol_up_pc": "XF86AudioRaiseVolume",
    "vol_down_pc": "XF86AudioLowerVolume",
    "mute_pc": "XF86AudioMute",
}


def media_key_name(command: str) -> str:
    return MEDIA_KEY_MAP[command]


async def send_host_media_key(command: str, platform: PlatformInfo | None = None) -> None:
    platform = platform or PlatformInfo()
    if platform.key == "linux":
        key = LINUX_XF86_MAP[command]
        try:
            subprocess.Popen(["xdotool", "key", key])
        except FileNotFoundError as exc:
            raise RuntimeError("Missing xdotool. Install it with: sudo apt install xdotool") from exc
        return

    if platform.key in ("macos", "windows"):
        pyautogui.press(media_key_name(command))
        return

    raise RuntimeError("Host media keys are not supported on this platform.")


def get_capabilities(
    platform: PlatformInfo | None = None,
    *,
    preferred_input: str,
    lan_enabled: bool,
) -> dict:
    platform = platform or PlatformInfo()
    platform_key = platform.key
    network_mode = "lan" if lan_enabled else "local"

    if platform_key == "macos":
        permission_notes = [
            "macOS may ask for Bluetooth permission for Terminal, Python, or the packaged app.",
            "Host media keys may require Accessibility permission in System Settings.",
            "Use AUX on the Z407 when Mac audio is connected through a 3.5mm cable.",
        ]
        setup_hint = "AUX audio + BLE control"
        host_media_supported = True
    elif platform_key == "linux":
        permission_notes = [
            "Bluetooth access may require BlueZ permissions or setcap.",
            "Host media keys require xdotool.",
        ]
        setup_hint = "BLE speaker control"
        host_media_supported = True
    elif platform_key == "windows":
        permission_notes = [
            "Host media keys use PyAutoGUI.",
            "Bluetooth permission depends on Windows device settings.",
        ]
        setup_hint = "BLE speaker control"
        host_media_supported = True
    else:
        permission_notes = ["This platform has not been tested."]
        setup_hint = "Limited platform support"
        host_media_supported = False

    return {
        "platform": platform_key,
        "networkMode": network_mode,
        "preferredInput": preferred_input,
        "setupHint": setup_hint,
        "hostMediaKeysSupported": host_media_supported,
        "permissionNotes": permission_notes,
    }
```

- [ ] **Step 4: Run platform tests and verify pass**

Run:

```bash
pytest tests/test_platform.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add z407_platform.py tests/test_platform.py
git commit -m "Add platform capabilities and media key handling"
```

## Task 3: Refactor App Runtime, Status, Capabilities, and BLE Device Handling

**Files:**
- Modify: `app.py`
- Create: `tests/test_app_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_app_api.py`:

```python
import pytest

import app as z407_app
from z407_config import RuntimeConfig


@pytest.mark.asyncio
async def test_status_includes_platform_runtime_and_error(monkeypatch):
    z407_app.runtime_config = RuntimeConfig(host="127.0.0.1", port=8765, lan_enabled=False, preferred_input="aux")
    z407_app.remote_control = None
    z407_app.connection_state = "not_found"
    z407_app.last_error = "Speakers not found"

    test_client = z407_app.app.test_client()
    response = await test_client.get("/api/status")
    payload = await response.get_json()

    assert response.status_code == 200
    assert payload["connected"] is False
    assert payload["connectionState"] == "not_found"
    assert payload["volume"] == 0
    assert payload["preferredInput"] == "aux"
    assert payload["networkMode"] == "local"
    assert payload["lastError"] == "Speakers not found"


@pytest.mark.asyncio
async def test_capabilities_endpoint_returns_aux_first_macos_data(monkeypatch):
    z407_app.runtime_config = RuntimeConfig(host="127.0.0.1", port=8765, lan_enabled=False, preferred_input="aux")
    monkeypatch.setattr(z407_app, "CURRENT_PLATFORM", z407_app.PlatformInfo(system="darwin"))

    test_client = z407_app.app.test_client()
    response = await test_client.get("/api/capabilities")
    payload = await response.get_json()

    assert response.status_code == 200
    assert payload["platform"] == "macos"
    assert payload["preferredInput"] == "aux"
    assert payload["setupHint"] == "AUX audio + BLE control"


@pytest.mark.asyncio
async def test_unknown_command_returns_400():
    z407_app.remote_control = object()

    test_client = z407_app.app.test_client()
    response = await test_client.post("/api/not_a_command")
    payload = await response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["error"] == "Unknown command"
```

- [ ] **Step 2: Run API tests and capture current failure**

Run:

```bash
pytest tests/test_app_api.py -v
```

Expected: fails because `pytest-asyncio` is missing or because status/capabilities fields do not exist. If it fails with missing async support, continue to Step 3.

- [ ] **Step 3: Add pytest async dependency if needed**

If Step 2 reports async test support missing, add `pytest-asyncio` to `requirements.txt`:

```txt
quart
bleak
pyinstaller
pyautogui
pytest
pytest-asyncio
```

Run:

```bash
pip install -r requirements.txt
pytest tests/test_app_api.py -v
```

Expected: tests still fail because implementation fields/routes are missing.

- [ ] **Step 4: Refactor imports and globals in `app.py`**

At the top of `app.py`, replace config/platform-related imports and globals with:

```python
import sys
import os
import signal
import asyncio

from quart import Quart, render_template, jsonify
from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

from z407_config import RuntimeConfig, build_runtime_config, get_lan_ip
from z407_platform import PlatformInfo, get_capabilities, send_host_media_key


CURRENT_PLATFORM = PlatformInfo()
print(f"--- Running in {CURRENT_PLATFORM.key.upper()} mode ---")
```

Keep the existing credit comment and Z407 UUID constants.

Add these globals near `remote_control = None`:

```python
runtime_config = RuntimeConfig(host="127.0.0.1", port=8765, lan_enabled=False, preferred_input="aux")
connection_state = "starting"
last_error = None
```

- [ ] **Step 5: Update `Z407Remote` to use `BLEDevice`**

Change the class initializer and display helpers:

```python
class Z407Remote:
    def __init__(self, device):
        self.device = device
        self.address = getattr(device, "address", "unknown")
        self.name = getattr(device, "name", "Logitech Z407")
        self.client = BleakClient(device)
        self.connected = False
        self.current_volume = 50
```

Update `connect()` to track state:

```python
    async def connect(self):
        global connection_state, last_error
        print(f"Connecting to {self.name} ({self.address})...")
        connection_state = "connecting"
        try:
            await self.client.connect()
            self.connected = True
            connection_state = "connected"
            last_error = None
            print("Connected!")
            await self.client.start_notify(RESPONSE_UUID, self._receive_data)
            await self._send_command("8405")
        except Exception as e:
            last_error = str(e)
            connection_state = "error"
            print(f"Failed to connect: {e}")
            self.connected = False
```

- [ ] **Step 6: Replace host media methods**

Replace `next_track`, `prev_track`, `toggle_media_pc`, `vol_up_pc`, `vol_down_pc`, and `mute_pc` with:

```python
    async def next_track(self):
        await send_host_media_key("next", CURRENT_PLATFORM)

    async def prev_track(self):
        await send_host_media_key("prev", CURRENT_PLATFORM)

    async def toggle_media_pc(self):
        await send_host_media_key("play_pause_pc", CURRENT_PLATFORM)

    async def vol_up_pc(self):
        await send_host_media_key("vol_up_pc", CURRENT_PLATFORM)

    async def vol_down_pc(self):
        await send_host_media_key("vol_down_pc", CURRENT_PLATFORM)

    async def mute_pc(self):
        await send_host_media_key("mute_pc", CURRENT_PLATFORM)
```

- [ ] **Step 7: Update IP reminder and discovery state**

Replace `print_ip_reminder()` with:

```python
async def print_ip_reminder():
    while True:
        await asyncio.sleep(30)
        lan_ip = get_lan_ip()
        print("\n" + "-" * 50)
        print(f"Local: {runtime_config.local_url}")
        if runtime_config.lan_enabled:
            print(f"LAN:   {runtime_config.lan_url(lan_ip)}")
        print("-" * 50 + "\n")
```

In `find_device()`, set status on errors and no device:

```python
async def find_device():
    global scan_lock, connection_state, last_error
    if scan_lock is None:
        scan_lock = asyncio.Lock()

    async with scan_lock:
        connection_state = "scanning"
        print("Scanning for Z407...")
        scanner_kwargs = {"service_uuids": [SERVICE_UUID]}

        try:
            devices = await BleakScanner.discover(**scanner_kwargs)
            if devices:
                last_error = None
                return devices[0]
            connection_state = "not_found"
            last_error = "Speakers not found"
        except Exception as e:
            connection_state = "error"
            last_error = str(e)
            print(f"Error during scan: {e}")
            if CURRENT_PLATFORM.key == "linux":
                print("Hint: On Linux, you might need to run this script with sudo or check BlueZ permissions.")

        return None
```

- [ ] **Step 8: Remove macOS-hostile adapter reset from connection manager**

In `manage_connection()`, delete the Linux `rfkill` block/unblock commands. Use this loop:

```python
async def manage_connection():
    global remote_control, connection_state
    fail_count = 0

    print("Starting background connection manager...")

    while not remote_control or not remote_control.connected:
        device = await find_device()
        if device:
            print(f"Found Z407 at {getattr(device, 'address', 'unknown')}")
            remote_control = Z407Remote(device)
            await remote_control.connect()
            if remote_control.connected:
                print("Connection successful!")
                break
        else:
            fail_count += 1
            print(f"Device not found. Attempt {fail_count}/5...")
            if fail_count >= 5:
                print("Still searching. Check speaker power, input mode, Bluetooth permissions, and proximity.")
                fail_count = 0
            await asyncio.sleep(3)
```

- [ ] **Step 9: Update status and add capabilities route**

Replace `/api/status` with:

```python
@app.route("/api/status")
async def get_status():
    connected = bool(remote_control and remote_control.connected)
    volume = remote_control.current_volume if remote_control else 0
    return jsonify(
        connected=connected,
        connectionState="connected" if connected else connection_state,
        volume=volume,
        platform=CURRENT_PLATFORM.key,
        networkMode="lan" if runtime_config.lan_enabled else "local",
        preferredInput=runtime_config.preferred_input,
        lastError=last_error,
    )
```

Add:

```python
@app.route("/api/capabilities")
async def capabilities():
    return jsonify(
        get_capabilities(
            CURRENT_PLATFORM,
            preferred_input=runtime_config.preferred_input,
            lan_enabled=runtime_config.lan_enabled,
        )
    )
```

- [ ] **Step 10: Keep command handling explicit and testable**

At the start of `handle_command`, add:

```python
    supported_commands = {
        "vol_up",
        "vol_down",
        "play_pause",
        "play_pause_pc",
        "vol_up_pc",
        "vol_down_pc",
        "mute_pc",
        "input_aux",
        "input_usb",
        "input_bluetooth",
        "bluetooth_pair",
        "factory_reset",
        "next",
        "prev",
        "bass_up",
        "bass_down",
        "next_speaker",
        "prev_speaker",
    }
    if command not in supported_commands:
        return jsonify(success=False, error="Unknown command"), 400
```

Then keep the existing explicit `if/elif` dispatch.

- [ ] **Step 11: Update CLI startup**

Replace the `if __name__ == "__main__":` block with:

```python
if __name__ == "__main__":
    runtime_config = build_runtime_config()
    lan_ip = get_lan_ip()

    try:
        print("\n" + "#" * 60)
        print("   LOGITECH Z407 REMOTE CONTROL")
        print("   macOS-first web app")
        print(f"\n   Local: {runtime_config.local_url}")
        if runtime_config.lan_enabled:
            print(f"   LAN:   {runtime_config.lan_url(lan_ip)}")
        else:
            print("   LAN:   disabled. Use --lan to control from a phone on the same Wi-Fi.")
        print(f"   Input: {runtime_config.preferred_input.upper()} recommended")
        print("#" * 60 + "\n")

        app.run(host=runtime_config.host, port=runtime_config.port, use_reloader=False)
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print("\n\n" + "!" * 60)
        print("CRITICAL ERROR: The app failed to start.")
        print(f"Error details: {e}")
        print("!" * 60)
        print("\nPOSSIBLE CAUSES:")
        print(f"1. Port {runtime_config.port} is occupied by another program.")
        print("2. Missing Bluetooth or Accessibility permissions.")
        print("3. Check if you have another instance running.")
        print("\nPress ENTER to close the window...")
        input()
```

- [ ] **Step 12: Run API and existing tests**

Run:

```bash
pytest tests/test_config.py tests/test_platform.py tests/test_app_api.py -v
python3 -m py_compile app.py z407_config.py z407_platform.py
```

Expected: tests pass and compilation has no output.

- [ ] **Step 13: Commit**

```bash
git add app.py z407_config.py z407_platform.py tests/test_app_api.py requirements.txt
git commit -m "Refactor app for macOS runtime and BLE handling"
```

## Task 4: Modernize the Web UI

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1: Replace `templates/index.html` with modern static UI**

Replace the full file with this HTML:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Logitech Z407 Web Control</title>
    <meta name="theme-color" content="#101820">
    <style>
        :root {
            --bg: #101820;
            --bg-soft: #17242f;
            --panel: rgba(255, 255, 255, 0.08);
            --panel-strong: rgba(255, 255, 255, 0.13);
            --text: #f4efe6;
            --muted: #aeb8bd;
            --line: rgba(255, 255, 255, 0.15);
            --accent: #f2b84b;
            --accent-ink: #241604;
            --good: #72d391;
            --bad: #ff7b7b;
            --warn: #f2b84b;
            --shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
        }

        * { box-sizing: border-box; }

        body {
            min-height: 100vh;
            margin: 0;
            font-family: Avenir Next, Futura, Trebuchet MS, sans-serif;
            color: var(--text);
            background:
                radial-gradient(circle at 12% 12%, rgba(242, 184, 75, 0.18), transparent 30%),
                radial-gradient(circle at 80% 0%, rgba(94, 151, 246, 0.16), transparent 34%),
                linear-gradient(145deg, #0c1218 0%, var(--bg) 48%, #1c2b32 100%);
            padding: 28px;
        }

        .shell {
            width: min(1080px, 100%);
            margin: 0 auto;
        }

        .hero {
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            gap: 18px;
            align-items: stretch;
            margin-bottom: 18px;
        }

        .card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 28px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
            padding: 22px;
        }

        h1, h2, p { margin: 0; }

        h1 {
            font-size: clamp(2.2rem, 7vw, 5rem);
            line-height: 0.95;
            letter-spacing: -0.08em;
        }

        h2 {
            color: var(--muted);
            font-size: 0.76rem;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            margin-bottom: 14px;
        }

        .subtitle {
            color: var(--muted);
            max-width: 620px;
            margin-top: 18px;
            font-size: 1.02rem;
            line-height: 1.6;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 20px;
        }

        .pill {
            border: 1px solid var(--line);
            border-radius: 999px;
            color: var(--muted);
            padding: 8px 12px;
            font-size: 0.84rem;
            background: rgba(0, 0, 0, 0.16);
        }

        .pill.good { color: var(--good); }
        .pill.bad { color: var(--bad); }
        .pill.warn { color: var(--warn); }

        .grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 18px;
        }

        .span-7 { grid-column: span 7; }
        .span-5 { grid-column: span 5; }
        .span-12 { grid-column: span 12; }

        .control-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }

        button {
            border: 0;
            border-radius: 18px;
            cursor: pointer;
            font: inherit;
            color: var(--text);
            background: var(--panel-strong);
            min-height: 58px;
            transition: transform 140ms ease, background 140ms ease, box-shadow 140ms ease;
            -webkit-tap-highlight-color: transparent;
        }

        button:active {
            transform: translateY(2px) scale(0.98);
        }

        .primary {
            min-height: 132px;
            background: var(--accent);
            color: var(--accent-ink);
            font-size: 1.3rem;
            font-weight: 800;
            grid-column: span 3;
        }

        .btn-label {
            display: block;
            font-size: 0.76rem;
            color: var(--muted);
            margin-top: 5px;
        }

        .primary .btn-label {
            color: rgba(36, 22, 4, 0.72);
        }

        .slider-card {
            display: grid;
            gap: 12px;
        }

        .meter {
            height: 12px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.12);
            overflow: hidden;
        }

        .meter-fill {
            width: 50%;
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, #f2b84b, #ffe2a4);
            transition: width 220ms ease;
        }

        .segmented {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }

        .segmented button.recommended {
            outline: 2px solid var(--accent);
            color: var(--accent);
        }

        .advanced {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
        }

        .danger {
            color: #ffd2d2;
            background: rgba(255, 77, 77, 0.16);
        }

        .status-line {
            min-height: 24px;
            color: var(--muted);
            margin-top: 14px;
            line-height: 1.5;
        }

        .help-list {
            display: grid;
            gap: 10px;
            color: var(--muted);
            line-height: 1.5;
            padding-left: 18px;
        }

        @media (max-width: 820px) {
            body { padding: 16px; }
            .hero, .grid { grid-template-columns: 1fr; }
            .span-7, .span-5, .span-12 { grid-column: span 1; }
            .advanced { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <main class="shell">
        <section class="hero">
            <div class="card">
                <h1>Z407 Control</h1>
                <p class="subtitle" id="setupHint">AUX audio + BLE control. Keep your Mac wired to the speaker and use this page as the remote.</p>
                <div class="pill-row">
                    <span class="pill bad" id="connectionStatus">Disconnected</span>
                    <span class="pill" id="networkMode">Local</span>
                    <span class="pill warn" id="preferredInput">AUX recommended</span>
                </div>
                <p class="status-line" id="statusText">Starting speaker scan...</p>
            </div>
            <div class="card slider-card">
                <h2>Estimated Speaker Volume</h2>
                <div class="meter"><div class="meter-fill" id="volBar"></div></div>
                <p><strong id="volText">50%</strong></p>
                <p class="status-line">This is estimated because the Z407 remote protocol reports limited volume state.</p>
            </div>
        </section>

        <section class="grid">
            <div class="card span-7">
                <h2>Speaker Remote</h2>
                <div class="control-grid">
                    <button onclick="sendCommand('prev_speaker')">Previous<span class="btn-label">Speaker</span></button>
                    <button onclick="sendCommand('play_pause')" class="primary">Play / Pause<span class="btn-label">Z407 command</span></button>
                    <button onclick="sendCommand('next_speaker')">Next<span class="btn-label">Speaker</span></button>
                    <button onclick="sendCommand('vol_down')">Volume -<span class="btn-label">Speaker</span></button>
                    <button onclick="sendCommand('bass_down')">Bass -<span class="btn-label">Speaker</span></button>
                    <button onclick="sendCommand('bass_up')">Bass +<span class="btn-label">Speaker</span></button>
                    <button onclick="sendCommand('vol_up')">Volume +<span class="btn-label">Speaker</span></button>
                </div>
            </div>

            <div class="card span-5">
                <h2>Input Source</h2>
                <div class="segmented">
                    <button id="inputAux" onclick="sendCommand('input_aux')">AUX</button>
                    <button id="inputUsb" onclick="sendCommand('input_usb')">USB</button>
                    <button id="inputBluetooth" onclick="sendCommand('input_bluetooth')">Bluetooth</button>
                </div>
                <p class="status-line">For your Mac setup, use AUX for audio and BLE for remote control.</p>
            </div>

            <div class="card span-7">
                <h2 id="hostMediaTitle">Mac Media</h2>
                <div class="control-grid">
                    <button onclick="sendCommand('prev')">Previous<span class="btn-label">Mac</span></button>
                    <button onclick="sendCommand('play_pause_pc')">Play / Pause<span class="btn-label">Mac</span></button>
                    <button onclick="sendCommand('next')">Next<span class="btn-label">Mac</span></button>
                    <button onclick="sendCommand('vol_down_pc')">Mac Vol -</button>
                    <button onclick="sendCommand('mute_pc')">Mute</button>
                    <button onclick="sendCommand('vol_up_pc')">Mac Vol +</button>
                </div>
            </div>

            <div class="card span-5">
                <h2>Advanced</h2>
                <div class="advanced">
                    <button onclick="confirmAction('bluetooth_pair', 'Activate Bluetooth pairing mode?')">Pair</button>
                    <button class="danger" onclick="confirmAction('factory_reset', 'Factory reset the Z407? This can erase paired devices.')">Reset</button>
                    <button onclick="window.location.reload()">Refresh</button>
                    <button class="danger" onclick="shutdownApp()">Quit</button>
                </div>
            </div>

            <div class="card span-12">
                <h2>Setup Notes</h2>
                <ul class="help-list" id="helpList">
                    <li>Loading platform notes...</li>
                </ul>
            </div>
        </section>
    </main>

    <script>
        const statusText = document.getElementById('statusText');
        const connectionStatus = document.getElementById('connectionStatus');
        const networkMode = document.getElementById('networkMode');
        const preferredInput = document.getElementById('preferredInput');
        const setupHint = document.getElementById('setupHint');
        const hostMediaTitle = document.getElementById('hostMediaTitle');
        const volBar = document.getElementById('volBar');
        const volText = document.getElementById('volText');
        const helpList = document.getElementById('helpList');

        function sendCommand(command) {
            fetch(`/api/${command}`, { method: 'POST' })
                .then(response => response.json().then(data => ({ ok: response.ok, data })))
                .then(({ ok, data }) => {
                    if (ok && data.success) {
                        statusText.innerText = `Command sent: ${command}`;
                        statusText.style.color = 'var(--good)';
                        setTimeout(updateStatus, 350);
                    } else {
                        statusText.innerText = `Error: ${data.error || 'Command failed'}`;
                        statusText.style.color = 'var(--bad)';
                    }
                })
                .catch(() => {
                    statusText.innerText = 'Network error. Is the local server still running?';
                    statusText.style.color = 'var(--bad)';
                });
        }

        function confirmAction(command, message) {
            if (confirm(message)) sendCommand(command);
        }

        function markPreferredInput(input) {
            document.querySelectorAll('.segmented button').forEach(button => button.classList.remove('recommended'));
            const target = {
                aux: document.getElementById('inputAux'),
                usb: document.getElementById('inputUsb'),
                bluetooth: document.getElementById('inputBluetooth')
            }[input];
            if (target) target.classList.add('recommended');
        }

        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    connectionStatus.innerText = data.connected ? 'Connected' : data.connectionState || 'Disconnected';
                    connectionStatus.className = `pill ${data.connected ? 'good' : 'bad'}`;
                    networkMode.innerText = data.networkMode === 'lan' ? 'LAN enabled' : 'Local only';
                    preferredInput.innerText = `${(data.preferredInput || 'aux').toUpperCase()} recommended`;
                    markPreferredInput(data.preferredInput || 'aux');

                    if (data.volume !== undefined) {
                        volBar.style.width = `${data.volume}%`;
                        volText.innerText = `${data.volume}%`;
                    }

                    if (!data.connected && data.lastError) {
                        statusText.innerText = data.lastError;
                        statusText.style.color = 'var(--warn)';
                    }
                })
                .catch(() => {
                    connectionStatus.innerText = 'Offline';
                    connectionStatus.className = 'pill bad';
                });
        }

        function loadCapabilities() {
            fetch('/api/capabilities')
                .then(response => response.json())
                .then(data => {
                    setupHint.innerText = data.setupHint || setupHint.innerText;
                    hostMediaTitle.innerText = data.platform === 'macos' ? 'Mac Media' : 'Host Media';
                    helpList.innerHTML = '';
                    (data.permissionNotes || []).forEach(note => {
                        const item = document.createElement('li');
                        item.innerText = note;
                        helpList.appendChild(item);
                    });
                    markPreferredInput(data.preferredInput || 'aux');
                })
                .catch(() => {
                    helpList.innerHTML = '<li>Could not load platform notes.</li>';
                });
        }

        function shutdownApp() {
            if (!confirm('Close the Z407 web server? This browser page will stop working.')) return;
            fetch('/api/shutdown', { method: 'POST' })
                .then(() => {
                    document.body.innerHTML = '<main class="shell"><section class="card"><h1>Server closed</h1><p class="subtitle">You can close this tab now.</p></section></main>';
                })
                .catch(err => alert(`Error shutting down: ${err}`));
        }

        loadCapabilities();
        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
```

- [ ] **Step 2: Verify template has no Markdown fence**

Run:

```bash
tail -n 5 templates/index.html
```

Expected: output ends with `</html>` and no triple backticks.

- [ ] **Step 3: Smoke-check app import**

Run:

```bash
python3 -m py_compile app.py
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add templates/index.html
git commit -m "Modernize web control UI"
```

## Task 5: Add macOS Run Script

**Files:**
- Create: `run_macos.sh`

- [ ] **Step 1: Create `run_macos.sh`**

Create `run_macos.sh`:

```bash
#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

PORT="${Z407_PORT:-8765}"
URL="http://127.0.0.1:${PORT}"

echo "Starting Logitech Z407 Web Control for macOS..."
echo "Local URL: ${URL}"
echo "Use ./run_macos.sh --lan to allow phone access on the same Wi-Fi."

if command -v open >/dev/null 2>&1; then
    (sleep 2 && open "${URL}") &
fi

python app.py --port "${PORT}" "$@"
```

- [ ] **Step 2: Make script executable**

Run:

```bash
chmod +x run_macos.sh
```

- [ ] **Step 3: Verify shell syntax**

Run:

```bash
bash -n run_macos.sh
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add run_macos.sh
git commit -m "Add macOS run helper"
```

## Task 6: Update English README and Add Traditional Chinese README

**Files:**
- Modify: `README.md`
- Create: `README.zh-TW.md`

- [ ] **Step 1: Rewrite English README while preserving required sections**

Replace `README.md` with:

```markdown
# Logitech Z407 macOS Web Control

**A macOS-first web remote for Logitech Z407 speakers, adapted from the original Linux web app.**

[繁體中文 README](README.zh-TW.md)

This app runs a local web server on your Mac and controls the Logitech Z407 over Bluetooth Low Energy (BLE). It is designed for a common Mac setup: **audio through a 3.5mm AUX cable, control through BLE**.

## Features

- macOS-first defaults: `127.0.0.1:8765`, avoiding macOS AirPlay's common port `5000`.
- Local-only mode by default.
- Optional LAN mode for phone control on the same Wi-Fi.
- Speaker controls: play/pause, speaker volume, bass, input source, pairing, factory reset.
- Mac media controls through simulated media keys.
- Modern responsive web UI for desktop and mobile browsers.

## Recommended macOS Setup: AUX Audio + BLE Control

1. Connect your Mac to the Z407 using a 3.5mm AUX cable.
2. Select `AUX` as the Z407 input source.
3. Run this app on your Mac.
4. Use the web UI to control speaker volume, bass, input source, and Mac playback.

The audio stays wired through AUX. BLE is only used as the remote-control channel.

## Quick Start on macOS

```bash
chmod +x run_macos.sh
./run_macos.sh
```

Open:

```text
http://127.0.0.1:8765
```

The script creates a Python virtual environment, installs dependencies, starts the server, and opens your browser.

## Phone Control on the Same Wi-Fi

Run:

```bash
./run_macos.sh --lan
```

The terminal will print a LAN URL such as:

```text
http://192.168.1.35:8765
```

Open that URL from your phone while it is connected to the same Wi-Fi network.

## macOS Permissions

macOS may ask for:

- **Bluetooth permission** for Terminal, Python, or the packaged app.
- **Accessibility permission** for Mac media keys such as play/pause and volume.

If host media keys do not work, open System Settings and check Privacy & Security permissions.

## Advanced Configuration

```bash
python app.py --port 9090
python app.py --lan
python app.py --ip 192.168.1.50 --port 9090
python app.py --preferred-input aux
```

Defaults:

- Host: `127.0.0.1`
- Port: `8765`
- Preferred input: `aux`

## Linux Notes

Linux source-run behavior is kept where practical. Host media keys on Linux require `xdotool`, and Bluetooth access may require BlueZ permissions or capabilities.

The original Linux installer scripts remain for reference, but this adaptation focuses on macOS usage.

## Build from Source

Prerequisites:

- Python 3.12+
- `pip`
- `venv`

Install and run:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Repository Name Recommendation

If you publish this adaptation as a separate GitHub repository, recommended names include:

- `logitech-z407-macos-web-control`
- `z407-macos-remote-web`

## Credits & Acknowledgments

**Original Web App:**
Original implementation by **Androrama**.

**macOS-first Adaptation:**
Current adaptation and maintenance by **LCY000**.

**Reverse Engineering:**
Special thanks to **freundTech** for the reverse engineering work that made this possible.
https://github.com/freundTech/logi-z407-reverse-engineering

**Upstream Project:**
This version is adapted from `Androrama/Logitech-Z407-Remote-Control-Web-App---Linux`.

## Disclaimer

This is an **unofficial** project and is not affiliated with, endorsed by, or connected to Logitech in any way.
"Logitech" is a trademark of its respective owner. This software is provided "as is" without warranty of any kind.

## Donations & Support

This project is based on free community work. Please keep supporting and crediting the original author and reverse engineering work.

Original author support page:
https://androrama.com
```

- [ ] **Step 2: Create Traditional Chinese README**

Create `README.zh-TW.md`:

```markdown
# Logitech Z407 macOS 網頁控制器

**針對 macOS 優化的 Logitech Z407 網頁遙控器，改寫自原本的 Linux 網頁版專案。**

[English README](README.md)

這個 app 會在 Mac 上啟動本機網頁伺服器，並透過 Bluetooth Low Energy（BLE）控制 Logitech Z407。主要使用情境是：**Mac 音訊走 3.5mm AUX 音源線，控制指令走 BLE**。

## 功能

- macOS-first 預設值：`127.0.0.1:8765`，避開 macOS AirPlay 常用的 `5000` port。
- 預設只允許本機控制。
- 可選 LAN 模式，讓同 Wi-Fi 的手機開網頁控制。
- 音響控制：播放/暫停、音響音量、Bass、輸入來源、藍牙配對、恢復原廠設定。
- Mac 媒體鍵控制：播放/暫停、上一首、下一首、Mac 音量、靜音。
- 現代化 responsive 網頁介面，支援桌面與手機瀏覽器。

## 建議 macOS 使用方式：AUX 音訊 + BLE 控制

1. 用 3.5mm AUX 音源線把 Mac 接到 Z407。
2. 把 Z407 輸入來源切到 `AUX`。
3. 在 Mac 上啟動這個 app。
4. 用網頁介面控制音響音量、Bass、輸入來源與 Mac 播放。

音訊會繼續走 AUX 線。BLE 只負責遙控指令。

## macOS 快速開始

```bash
chmod +x run_macos.sh
./run_macos.sh
```

開啟：

```text
http://127.0.0.1:8765
```

這個腳本會建立 Python virtual environment、安裝依賴、啟動 server，並開啟瀏覽器。

## 用手機在同 Wi-Fi 控制

執行：

```bash
./run_macos.sh --lan
```

終端機會顯示類似這樣的 LAN URL：

```text
http://192.168.1.35:8765
```

手機連到同一個 Wi-Fi 後，用瀏覽器打開這個網址。

## macOS 權限

macOS 可能會要求：

- **Bluetooth 權限**：給 Terminal、Python 或封裝後的 app。
- **輔助使用 Accessibility 權限**：讓 app 可以模擬 Mac 媒體鍵。

如果 Mac 媒體鍵控制無效，請到系統設定的隱私權與安全性檢查權限。

## 進階設定

```bash
python app.py --port 9090
python app.py --lan
python app.py --ip 192.168.1.50 --port 9090
python app.py --preferred-input aux
```

預設值：

- Host：`127.0.0.1`
- Port：`8765`
- 建議輸入來源：`aux`

## Linux 說明

Linux source-run 行為會盡量保留。Linux 的電腦媒體鍵需要 `xdotool`，Bluetooth 存取可能需要 BlueZ 權限或 capability 設定。

原本的 Linux installer scripts 會保留作為參考，但這個改寫版會以 macOS 使用體驗為優先。

## GitHub Repo 名稱建議

如果你要把這個改寫版發成獨立 GitHub repository，建議名稱：

- `logitech-z407-macos-web-control`
- `z407-macos-remote-web`

## Credits & Acknowledgments

**原始 Web App：**
原始實作作者為 **Androrama**。

**macOS-first 改寫：**
目前 macOS-first adaptation 與維護者為 **LCY000**。

**Reverse Engineering：**
特別感謝 **freundTech** 的 reverse engineering 工作。
https://github.com/freundTech/logi-z407-reverse-engineering

**上游專案：**
這個版本改寫自 `Androrama/Logitech-Z407-Remote-Control-Web-App---Linux`。

## Disclaimer

這是 **非官方** 專案，與 Logitech 無關，未受 Logitech 背書或授權。
「Logitech」是其權利人的商標。本軟體以現狀提供，不附任何保證。

## Donations & Support

這個專案建立在免費的社群工作上。請保留並尊重原作者與 reverse engineering 的貢獻。

原作者支持頁面：
https://androrama.com
```

- [ ] **Step 3: Verify author username and links**

Run:

```bash
rg -n "LCY000|Androrama|freundTech|README.zh-TW|8765|AUX" README.md README.zh-TW.md
```

Expected: output includes all searched attribution and macOS usage terms.

- [ ] **Step 4: Commit**

```bash
git add README.md README.zh-TW.md
git commit -m "Update README for macOS adaptation"
```

## Task 7: Full Verification

**Files:**
- No edits expected unless verification fails.

- [ ] **Step 1: Run all automated tests**

Run:

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Compile Python files**

Run:

```bash
python3 -m py_compile app.py z407_config.py z407_platform.py
```

Expected: no output.

- [ ] **Step 3: Check shell scripts**

Run:

```bash
bash -n run_macos.sh
bash -n build_linux.sh
bash -n install_linux.sh
bash -n uninstall_linux.sh
```

Expected: no output.

- [ ] **Step 4: Smoke-run server without BLE validation**

Run:

```bash
python app.py --port 8765
```

Expected: server starts and prints local URL `http://127.0.0.1:8765`. Stop with `Ctrl+C`. Do not claim speaker control works until tested with physical Z407 hardware.

- [ ] **Step 5: Manual macOS hardware checks**

On the target Mac with Z407 nearby:

```bash
./run_macos.sh
```

Verify:

- Browser opens `http://127.0.0.1:8765`.
- UI shows AUX recommended.
- macOS Bluetooth permission is granted if prompted.
- Z407 is discovered and status changes to connected.
- Speaker volume and bass commands work.
- Mac media keys work after Accessibility permission if needed.

- [ ] **Step 6: Manual LAN check**

Run:

```bash
./run_macos.sh --lan
```

Verify:

- Terminal prints a LAN URL.
- Phone on same Wi-Fi can open the LAN URL.
- Phone can send a harmless command such as speaker volume down.

- [ ] **Step 7: Final status**

Run:

```bash
git status --short
```

Expected: clean working tree.

## Self-Review

- Spec coverage: macOS-safe port, local/LAN modes, AUX-first usage, BLEDevice handling, platform capabilities, modern UI, English README preservation, Chinese README, and repo naming recommendation are all mapped to tasks.
- Placeholder scan: no implementation steps rely on placeholder tokens or unspecified edge handling.
- Type consistency: `RuntimeConfig`, `PlatformInfo`, `get_capabilities`, `send_host_media_key`, `runtime_config`, `connection_state`, and `last_error` are defined before later tasks use them.
