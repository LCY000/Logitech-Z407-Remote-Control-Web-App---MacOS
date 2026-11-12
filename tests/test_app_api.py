import asyncio
import json
from pathlib import Path

import pytest

import app as z407_app
from z407_config import RuntimeConfig


# --- Request guards (CSRF / DNS rebinding / LAN) ---

@pytest.mark.asyncio
async def test_post_without_client_header_is_rejected(client, connected_remote):
    _remote, fake = connected_remote()

    response = await client.post("/api/factory_reset")

    assert response.status_code == 403
    assert (await response.get_json())["code"] == "missing_client_header"
    assert fake.writes == []


@pytest.mark.asyncio
async def test_cross_site_post_is_rejected_even_with_header(post, connected_remote):
    _remote, fake = connected_remote()

    response = await post("/api/vol_up", headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert (await response.get_json())["code"] == "forbidden_origin"
    assert fake.writes == []


@pytest.mark.asyncio
async def test_same_origin_post_is_accepted(post, connected_remote):
    _remote, fake = connected_remote()

    response = await post(
        "/api/vol_up",
        headers={"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"},
    )

    assert response.status_code == 200
    assert fake.writes == ["8002"]


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["evil.example", "evil.example:8765", "192.168.1.20:8765"])
async def test_unexpected_host_header_is_rejected_in_local_mode(client, host):
    response = await client.get("/api/status", headers={"Host": host})

    assert response.status_code == 403
    assert (await response.get_json())["code"] == "forbidden_host"


@pytest.mark.parametrize(
    ("host", "lan", "allowed"),
    [
        ("127.0.0.1:8765", False, True),
        ("localhost:8765", False, True),
        ("[::1]:8765", False, True),
        ("localhost", False, True),
        ("192.168.1.20:8765", True, True),
        ("my-mac.local:8765", True, True),
        ("my-mac.local:8765", False, False),
        ("evil.example:8765", True, False),
        ("", True, False),
    ],
)
def test_is_allowed_host(host, lan, allowed):
    assert z407_app.is_allowed_host(host, lan) is allowed


@pytest.mark.asyncio
async def test_factory_reset_and_quit_are_blocked_for_lan_clients(post, connected_remote, monkeypatch):
    _remote, fake = connected_remote()
    monkeypatch.setattr(z407_app, "is_local_client", lambda: False)
    monkeypatch.setattr(z407_app, "request_shutdown", lambda: pytest.fail("must not shut down"))

    reset = await post("/api/factory_reset")
    quit_ = await post("/api/shutdown")
    volume = await post("/api/vol_up")

    assert reset.status_code == 403
    assert (await reset.get_json())["code"] == "local_only"
    assert quit_.status_code == 403
    assert volume.status_code == 200
    assert fake.writes == ["8002"]


@pytest.mark.asyncio
async def test_shutdown_from_local_client_requests_server_stop(post, monkeypatch):
    calls = []
    monkeypatch.setattr(z407_app, "is_local_client", lambda: True)
    monkeypatch.setattr(z407_app, "request_shutdown", lambda: calls.append("stop"))

    class ImmediateLoop:
        def call_later(self, _delay, callback):
            callback()

    monkeypatch.setattr(z407_app.asyncio, "get_running_loop", lambda: ImmediateLoop())

    response = await post("/api/shutdown")

    assert response.status_code == 200
    assert calls == ["stop"]


# --- Status ---

@pytest.mark.asyncio
async def test_status_reports_runtime_and_error(client):
    z407_app.set_link_state("not_found", "Speakers not found", "speaker_not_found")

    payload = await (await client.get("/api/status")).get_json()

    assert payload["app"] == z407_app.APP_ID
    assert payload["version"] == z407_app.__version__
    assert payload["connected"] is False
    assert payload["connectionState"] == "not_found"
    assert payload["volume"] is None and payload["bass"] is None and payload["input"] is None
    assert payload["volumeMax"] == 32 and payload["bassMax"] == 15
    assert payload["preferredInput"] == "aux"
    assert payload["networkMode"] == "local"
    assert payload["lanUrl"] is None
    assert payload["lastError"] == "Speakers not found"
    assert payload["lastErrorCode"] == "speaker_not_found"


@pytest.mark.asyncio
async def test_status_shows_levels_and_hides_stale_error_when_connected(client, connected_remote):
    connected_remote()
    z407_app.last_error = "old failure"
    z407_app.speaker_state.volume = 7
    z407_app.speaker_state.bass = 3
    z407_app.speaker_state.input = "usb"

    payload = await (await client.get("/api/status")).get_json()

    assert payload["connected"] is True
    assert payload["connectionState"] == "connected"
    assert (payload["volume"], payload["bass"], payload["input"]) == (7, 3, "usb")
    assert payload["lastError"] is None


@pytest.mark.asyncio
async def test_status_includes_lan_url_in_lan_mode(client):
    z407_app.runtime_config = RuntimeConfig(host="0.0.0.0", port=9090, lan_enabled=True, preferred_input="aux")

    payload = await (await client.get("/api/status")).get_json()

    assert payload["networkMode"] == "lan"
    assert payload["lanUrl"].startswith("http://") and payload["lanUrl"].endswith(":9090")


@pytest.mark.asyncio
async def test_capabilities_endpoint_returns_aux_first_macos_data(client, monkeypatch):
    monkeypatch.setattr(z407_app, "CURRENT_PLATFORM", z407_app.PlatformInfo(system="darwin"))

    payload = await (await client.get("/api/capabilities")).get_json()

    assert payload["platform"] == "macos"
    assert payload["preferredInput"] == "aux"


@pytest.mark.asyncio
async def test_index_and_static_assets_are_served(client):
    page = await client.get("/")
    icon = await client.get("/static/favicon.svg")
    manifest = await client.get("/static/manifest.webmanifest")

    assert page.status_code == 200
    assert z407_app.__version__ in (await page.get_data(as_text=True))
    assert page.headers["X-Frame-Options"] == "DENY"
    assert icon.status_code == 200
    assert manifest.status_code == 200
    assert json.loads(await manifest.get_data(as_text=True))["name"]


# --- Preferences (language, first-run reminder) ---

@pytest.mark.asyncio
async def test_language_defaults_to_english_until_chosen(client):
    payload = await (await client.get("/api/status")).get_json()
    page = await (await client.get("/")).get_data(as_text=True)

    assert payload["language"] == "en"
    assert payload["calibrationHintDismissed"] is False
    assert '<html lang="en" data-saved-lang="en">' in page


@pytest.mark.asyncio
async def test_chosen_language_is_remembered_across_restarts(post, client):
    response = await post("/api/preferences", json={"language": "zh-TW"})
    assert response.status_code == 200

    restarted = z407_app.Preferences()
    restarted.load()
    z407_app.preferences = restarted          # what a relaunch of the app would see

    payload = await (await client.get("/api/status")).get_json()
    page = await (await client.get("/")).get_data(as_text=True)
    assert payload["language"] == "zh-TW"
    assert 'data-saved-lang="zh-TW"' in page


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [{"language": "klingon"}, {"language": 5}, {"calibrationHintDismissed": "yes"}, ["en"]],
)
async def test_preferences_reject_bad_values(post, body):
    response = await post("/api/preferences", json=body)

    assert response.status_code == 400
    assert z407_app.preferences.language is None
    assert z407_app.preferences.calibration_hint_dismissed is False


@pytest.mark.asyncio
async def test_first_run_reminder_can_be_dismissed_for_good(post):
    payload = await (await post("/api/preferences", json={"calibrationHintDismissed": True})).get_json()
    assert payload["calibrationHintDismissed"] is True

    restarted = z407_app.Preferences()
    restarted.load()
    assert restarted.calibration_hint_dismissed is True
    assert restarted.language is None          # untouched fields stay as they were


@pytest.mark.asyncio
async def test_successful_calibration_retires_the_first_run_reminder(post, connected_remote):
    connected_remote()

    payload = await (await post("/api/calibrate")).get_json()

    assert payload["calibrationHintDismissed"] is True
    assert z407_app.preferences.calibration_hint_dismissed is True


@pytest.mark.asyncio
async def test_failed_calibration_keeps_the_first_run_reminder(post, connected_remote):
    connected_remote(respond=False)

    await post("/api/calibrate")

    assert z407_app.preferences.calibration_hint_dismissed is False


def test_corrupt_preferences_file_is_ignored():
    z407_app.PREFS_FILE.write_text("{broken")
    prefs = z407_app.Preferences()
    prefs.load()
    assert prefs.language is None and prefs.calibration_hint_dismissed is False


# --- Commands ---

@pytest.mark.asyncio
async def test_unknown_command_returns_400(post):
    response = await post("/api/not_a_command")
    payload = await response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["error"] == "Unknown command"


@pytest.mark.asyncio
@pytest.mark.parametrize(("command", "code"), sorted(z407_app.SPEAKER_COMMAND_CODES.items()))
async def test_every_speaker_command_writes_its_code(post, connected_remote, command, code):
    _remote, fake = connected_remote()

    response = await post(f"/api/{command}")

    assert response.status_code == 200
    assert fake.writes == [code]


@pytest.mark.asyncio
async def test_speaker_command_without_connection_returns_503_without_scanning(post, monkeypatch):
    async def fail_if_called():
        raise AssertionError("find_device should not be called from a request")

    monkeypatch.setattr(z407_app, "find_device", fail_if_called)

    response = await post("/api/vol_up")

    assert response.status_code == 503
    assert (await response.get_json())["code"] == "not_connected"


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["play_pause_pc", "vol_up_pc"])
async def test_host_media_commands_do_not_need_the_speaker(post, monkeypatch, command):
    calls = []

    async def fake_send_host_media_key(key, platform):
        calls.append((key, platform.key))

    monkeypatch.setattr(z407_app, "send_host_media_key", fake_send_host_media_key)

    response = await post(f"/api/{command}")

    assert response.status_code == 200
    assert calls == [(command, z407_app.CURRENT_PLATFORM.key)]


@pytest.mark.asyncio
async def test_missing_accessibility_permission_is_reported_with_a_code(post, monkeypatch):
    async def blocked(_key, _platform):
        raise z407_app.AccessibilityPermissionError("blocked")

    monkeypatch.setattr(z407_app, "send_host_media_key", blocked)

    response = await post("/api/mute_pc")

    assert response.status_code == 403
    assert (await response.get_json())["code"] == "accessibility_required"


@pytest.mark.asyncio
async def test_write_failure_marks_link_down_and_reports_error(post, client, connected_remote):
    remote, _fake = connected_remote(fail_writes=True)

    response = await post("/api/vol_up")
    status = await (await client.get("/api/status")).get_json()

    assert response.status_code == 500
    assert remote.connected is False
    assert status["connected"] is False
    assert status["connectionState"] == "error"
    assert status["lastError"] == "write failed"


# --- Notifications and state ---

@pytest.mark.asyncio
async def test_level_confirmations_move_counters_and_clamp(connected_remote):
    remote, _fake = connected_remote()
    state = z407_app.speaker_state
    state.volume, state.bass = 31, 1

    for packet in (b"\xc0\x02", b"\xc0\x02", b"\xc0\x01", b"\xc0\x01"):
        await remote._receive_data(None, bytearray(packet))

    assert (state.volume, state.bass) == (32, 0)
    assert remote.level_confirmations == 4
    assert json.loads(z407_app.STATE_FILE.read_text())["volume"] == 32


@pytest.mark.asyncio
async def test_level_confirmations_do_not_invent_a_level_when_uncalibrated(connected_remote):
    remote, _fake = connected_remote()

    await remote._receive_data(None, bytearray(b"\xc0\x02"))
    await remote._receive_data(None, bytearray(b"\xc0\x00"))

    assert z407_app.speaker_state.volume is None
    assert z407_app.speaker_state.bass is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("packet", "expected"),
    [(b"\xc1\x02", "aux"), (b"\xcf\x06", "usb"), (b"\xcf\x04", "bluetooth")],
)
async def test_input_notifications_track_the_active_input(connected_remote, packet, expected):
    remote, _fake = connected_remote()

    await remote._receive_data(None, bytearray(packet))

    assert z407_app.speaker_state.input == expected


@pytest.mark.asyncio
async def test_factory_reset_confirmation_forgets_levels(connected_remote):
    remote, _fake = connected_remote()
    state = z407_app.speaker_state
    state.volume, state.bass, state.input = 9, 4, "aux"

    await remote._receive_data(None, bytearray(b"\xc3\x00"))

    assert (state.volume, state.bass, state.input) == (None, None, None)


@pytest.mark.asyncio
async def test_handshake_packets(connected_remote):
    remote, fake = connected_remote()
    remote.connected = True

    await remote._receive_data(None, bytearray(b"\xd4\x05\x01"))
    assert fake.writes == ["8400"]

    remote.connected = False
    await remote._receive_data(None, bytearray(b"\xd4\x00\x03"))
    assert remote.connected is True


def test_state_survives_restart_and_ignores_garbage():
    state = z407_app.SpeakerState()
    state.volume, state.bass, state.input = 12, 5, "usb"
    state.save()

    restored = z407_app.SpeakerState()
    restored.load()
    assert (restored.volume, restored.bass, restored.input) == (12, 5, "usb")

    z407_app.STATE_FILE.write_text('{"volume": 999, "bass": "loud", "input": "hdmi"}')
    restored.load()
    assert (restored.volume, restored.bass, restored.input) == (32, None, None)

    z407_app.STATE_FILE.write_text("not json")
    untouched = z407_app.SpeakerState()
    untouched.load()
    assert untouched.volume is None


# --- Calibration and absolute levels ---

@pytest.mark.asyncio
async def test_calibrate_sets_both_counters_to_zero(post, connected_remote):
    _remote, fake = connected_remote()

    response = await post("/api/calibrate")
    payload = await response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert fake.writes.count("8003") == z407_app.VOLUME_MAX + z407_app.CALIBRATION_MARGIN_STEPS
    assert fake.writes.count("8001") == z407_app.BASS_MAX + z407_app.CALIBRATION_MARGIN_STEPS
    assert (payload["volume"], payload["bass"]) == (0, 0)
    assert z407_app.busy_task is None


@pytest.mark.asyncio
async def test_calibrate_fails_when_speaker_confirms_nothing(post, connected_remote):
    connected_remote(respond=False)
    z407_app.speaker_state.volume = 14

    response = await post("/api/calibrate")

    assert response.status_code == 409
    assert (await response.get_json())["code"] == "no_confirmation"
    assert z407_app.speaker_state.volume == 14  # untouched
    assert z407_app.busy_task is None


@pytest.mark.asyncio
async def test_calibrate_returns_503_when_not_connected(post):
    response = await post("/api/calibrate")

    assert response.status_code == 503
    assert (await response.get_json())["success"] is False


@pytest.mark.asyncio
async def test_commands_are_refused_while_busy(post, connected_remote):
    _remote, fake = connected_remote()
    z407_app.busy_task = "calibrating"

    for path in ("/api/vol_up", "/api/calibrate"):
        response = await post(path)
        assert response.status_code == 409
        assert (await response.get_json())["code"] == "busy"

    assert fake.writes == []
    assert z407_app.busy_task == "calibrating"  # a refused request must not clear it


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("target", "start", "value", "expected_writes"),
    [
        ("volume", 5, 9, ["8002"] * 4),
        ("volume", 9, 6, ["8003"] * 3),
        ("bass", 2, 0, ["8001"] * 2),
        ("bass", 7, 7, []),
    ],
)
async def test_set_level_steps_to_the_target(post, connected_remote, target, start, value, expected_writes):
    _remote, fake = connected_remote()
    setattr(z407_app.speaker_state, target, start)

    response = await post("/api/set_level", json={"target": target, "value": value})
    payload = await response.get_json()

    assert response.status_code == 200
    assert payload["reached"] is True
    assert payload[target] == value
    assert fake.writes == expected_writes
    assert z407_app.busy_task is None


@pytest.mark.asyncio
async def test_set_level_reports_when_speaker_ignores_steps(post, connected_remote):
    connected_remote(respond=False)
    z407_app.speaker_state.volume = 5

    payload = await (await post("/api/set_level", json={"target": "volume", "value": 8})).get_json()

    assert payload["reached"] is False
    assert payload["volume"] == 5


@pytest.mark.asyncio
async def test_set_level_needs_calibration(post, connected_remote):
    connected_remote()

    response = await post("/api/set_level", json={"target": "volume", "value": 8})

    assert response.status_code == 409
    assert (await response.get_json())["code"] == "not_calibrated"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"target": "treble", "value": 1},
        {"target": "volume", "value": 33},
        {"target": "volume", "value": -1},
        {"target": "bass", "value": 16},
        {"target": "volume", "value": "5"},
        {"target": "volume", "value": True},
        {},
    ],
)
async def test_set_level_validates_input(post, connected_remote, body):
    _remote, fake = connected_remote()
    z407_app.speaker_state.volume = 5

    response = await post("/api/set_level", json=body)

    assert response.status_code == 400
    assert fake.writes == []


# --- Discovery and connection manager ---

def test_is_z407_device_matches_name_or_advertised_service():
    class Device:
        def __init__(self, name):
            self.name = name

    class Advertisement:
        def __init__(self, local_name=None, service_uuids=()):
            self.local_name = local_name
            self.service_uuids = list(service_uuids)

    assert z407_app.is_z407_device(Device("ZS283A_develop_ot"), Advertisement())
    assert z407_app.is_z407_device(Device(None), Advertisement(local_name="Logi Z407"))
    assert z407_app.is_z407_device(Device(None), Advertisement(service_uuids=[z407_app.SERVICE_UUID.upper()]))
    assert not z407_app.is_z407_device(Device("AirPods"), Advertisement(service_uuids=["180f"]))


@pytest.mark.asyncio
async def test_find_device_reports_not_found(monkeypatch):
    calls = []

    async def fake_find(filterfunc, timeout):
        calls.append((filterfunc, timeout))
        return None

    monkeypatch.setattr(z407_app.BleakScanner, "find_device_by_filter", fake_find)

    assert await z407_app.find_device() is None
    assert calls == [(z407_app.is_z407_device, z407_app.SCAN_TIMEOUT_SECONDS)]
    assert z407_app.connection_state == "not_found"
    assert z407_app.last_error_code == "speaker_not_found"


@pytest.mark.asyncio
async def test_find_device_reports_bluetooth_unavailable(monkeypatch):
    async def fake_find(filterfunc, timeout):
        raise z407_app.BleakBluetoothNotAvailableError("Bluetooth is off", None)

    monkeypatch.setattr(z407_app.BleakScanner, "find_device_by_filter", fake_find)

    assert await z407_app.find_device() is None
    assert z407_app.connection_state == "error"
    assert z407_app.last_error_code == "bluetooth_unavailable"


@pytest.mark.asyncio
async def test_manage_connection_retries_quietly_until_found(monkeypatch, capsys):
    attempts = 0
    sleeps = []

    async def fake_find_device():
        nonlocal attempts
        attempts += 1
        if attempts > 4:
            raise asyncio.CancelledError()
        return None

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(z407_app, "find_device", fake_find_device)
    monkeypatch.setattr(z407_app.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await z407_app.manage_connection()

    assert capsys.readouterr().out.count("Z407 not found yet") == 1
    assert sleeps == [z407_app.RETRY_DELAY_SECONDS] * 4


@pytest.mark.asyncio
async def test_manage_connection_reconnects_after_the_speaker_drops(monkeypatch):
    """The old manager stopped after the first connect; a power cycle left the UI stuck."""
    made = []

    async def fake_find_device():
        return z407_app.DemoDevice()

    real_remote = z407_app.Z407Remote

    def make_remote(device, client=None):
        from conftest import FakeClient

        remote = real_remote(device, client=FakeClient())
        made.append(remote)
        return remote

    monkeypatch.setattr(z407_app, "find_device", fake_find_device)
    monkeypatch.setattr(z407_app, "Z407Remote", make_remote)

    task = asyncio.create_task(z407_app.manage_connection())
    try:
        await asyncio.sleep(0.05)
        assert len(made) == 1 and made[0].connected
        assert z407_app.connection_state == "connected"

        made[0]._handle_disconnect()          # speaker loses power
        assert z407_app.connection_state == "disconnected"

        await asyncio.sleep(0.05)
        assert len(made) == 2 and made[1].connected
        assert z407_app.remote_control is made[1]
        assert z407_app.connection_state == "connected"
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_failed_connect_is_reported_and_cleaned_up():
    from conftest import FakeClient

    class RefusingClient(FakeClient):
        async def connect(self):
            raise RuntimeError("peer removed pairing")

    fake = RefusingClient()
    remote = z407_app.Z407Remote(z407_app.DemoDevice(), client=fake)
    z407_app.remote_control = remote

    await remote.connect()

    assert remote.connected is False
    assert fake.disconnected is True
    assert z407_app.connection_state == "error"
    assert z407_app.last_error == "peer removed pairing"


@pytest.mark.asyncio
async def test_demo_client_behaves_like_a_speaker():
    remote = z407_app.Z407Remote(z407_app.DemoDevice(), client=z407_app.DemoClient())
    z407_app.remote_control = remote
    z407_app.speaker_state.volume = 3

    await remote.connect()
    await remote.send("vol_up")
    await remote.send("input_usb")
    await asyncio.sleep(0.01)

    assert remote.connected is True
    assert z407_app.speaker_state.volume == 4
    assert z407_app.speaker_state.input == "usb"


# --- Startup helpers ---

def test_probe_port_distinguishes_free_self_and_other(monkeypatch):
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    assert z407_app.probe_port(free_port) == "free"

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(16)
        port = listener.getsockname()[1]

        class Response:
            def __init__(self, body):
                self.body = body

            def read(self):
                return self.body

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        monkeypatch.setattr(
            z407_app.urllib.request, "urlopen", lambda *a, **k: Response(b'{"app": "z407-control"}')
        )
        assert z407_app.probe_port(port) == "self"

        monkeypatch.setattr(z407_app.urllib.request, "urlopen", lambda *a, **k: Response(b"<html>"))
        assert z407_app.probe_port(port) == "other"


def test_startup_banner_mentions_safe_exit():
    source = Path("app.py").read_text()

    assert "Quit: click the menu bar icon or press Ctrl+C." in source
    assert "Do not use Ctrl+Z; it suspends the app instead of closing it." in source


def test_terminal_logging_is_quiet_by_default():
    assert z407_app.runtime_config.quiet_logs is True
    assert "hypercorn.access" in z407_app.QUIET_LOGGER_NAMES
