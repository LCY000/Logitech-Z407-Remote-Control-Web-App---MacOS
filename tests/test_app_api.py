import asyncio
from pathlib import Path

import pytest

import app as z407_app
from z407_config import RuntimeConfig


@pytest.fixture(autouse=True)
def restore_app_globals():
    snapshot = {
        "runtime_config": z407_app.runtime_config,
        "remote_control": z407_app.remote_control,
        "connection_state": z407_app.connection_state,
        "last_error": z407_app.last_error,
        "CURRENT_PLATFORM": z407_app.CURRENT_PLATFORM,
    }
    yield
    for name, value in snapshot.items():
        setattr(z407_app, name, value)


@pytest.mark.asyncio
async def test_status_includes_platform_runtime_and_error(monkeypatch):
    z407_app.runtime_config = RuntimeConfig(
        host="127.0.0.1",
        port=8765,
        lan_enabled=False,
        preferred_input="aux",
    )
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
    z407_app.runtime_config = RuntimeConfig(
        host="127.0.0.1",
        port=8765,
        lan_enabled=False,
        preferred_input="aux",
    )
    monkeypatch.setattr(z407_app, "CURRENT_PLATFORM", z407_app.PlatformInfo(system="darwin"))

    test_client = z407_app.app.test_client()
    response = await test_client.get("/api/capabilities")
    payload = await response.get_json()

    assert response.status_code == 200
    assert payload["platform"] == "macos"
    assert payload["preferredInput"] == "aux"
    assert payload["setupHint"] == "Choose the Z407 input below. AUX is recommended when your Mac is connected by cable."


@pytest.mark.asyncio
async def test_unknown_command_returns_400_without_scanning(monkeypatch):
    async def fail_if_called():
        raise AssertionError("find_device should not be called")

    z407_app.remote_control = None
    monkeypatch.setattr(z407_app, "find_device", fail_if_called)

    test_client = z407_app.app.test_client()
    response = await test_client.post("/api/not_a_command")
    payload = await response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["error"] == "Unknown command"


@pytest.mark.asyncio
async def test_find_device_falls_back_to_unfiltered_name_scan(monkeypatch):
    calls = []

    class Device:
        name = "ZS283A_develop_ot"
        address = "test-address"
        metadata = {}

    async def fake_discover(**kwargs):
        calls.append(kwargs)
        if kwargs.get("service_uuids"):
            return []
        return [Device()]

    monkeypatch.setattr(z407_app.BleakScanner, "discover", fake_discover)

    device = await z407_app.find_device()

    assert device.name == "ZS283A_develop_ot"
    assert calls == [
        {"timeout": z407_app.SCAN_TIMEOUT_SECONDS, "service_uuids": [z407_app.SERVICE_UUID]},
        {"timeout": z407_app.SCAN_TIMEOUT_SECONDS},
    ]
    assert z407_app.connection_state == "scanning"
    assert z407_app.last_error is None


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["play_pause_pc", "vol_up_pc"])
async def test_host_media_commands_do_not_require_ble_discovery(monkeypatch, command):
    calls = []

    async def fail_if_called():
        raise AssertionError("find_device should not be called")

    async def fake_send_host_media_key(key, platform):
        calls.append((key, platform.key))

    z407_app.remote_control = None
    monkeypatch.setattr(z407_app, "find_device", fail_if_called)
    monkeypatch.setattr(z407_app, "send_host_media_key", fake_send_host_media_key)

    test_client = z407_app.app.test_client()
    response = await test_client.post(f"/api/{command}")
    payload = await response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert calls == [(command, z407_app.CURRENT_PLATFORM.key)]


@pytest.mark.asyncio
async def test_manage_connection_sleeps_after_failed_connect(monkeypatch):
    class Device:
        address = "00:11:22:33"

    class FailingRemote:
        connected = False

        def __init__(self, device):
            self.device = device

        async def connect(self):
            self.connected = False

    sleeps = []
    find_calls = 0

    async def fake_find_device():
        nonlocal find_calls
        find_calls += 1
        if find_calls > 1:
            raise asyncio.CancelledError()
        return Device()

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    z407_app.remote_control = None
    monkeypatch.setattr(z407_app, "find_device", fake_find_device)
    monkeypatch.setattr(z407_app, "Z407Remote", FailingRemote)
    monkeypatch.setattr(z407_app.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await z407_app.manage_connection()

    assert sleeps == [3]


@pytest.mark.asyncio
async def test_manage_connection_quiet_mode_prints_not_found_once(monkeypatch, capsys):
    attempts = 0
    sleeps = []

    async def fake_find_device():
        nonlocal attempts
        attempts += 1
        if attempts > 6:
            raise asyncio.CancelledError()
        return None

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(z407_app, "find_device", fake_find_device)
    monkeypatch.setattr(z407_app.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await z407_app.manage_connection()

    output = capsys.readouterr().out
    assert output.count("Z407 not found yet") == 1
    assert "Still searching" not in output
    assert sleeps == [3, 3, 3, 3, 3, 3]


@pytest.mark.asyncio
async def test_send_command_failure_raises_and_updates_status():
    class FailingClient:
        async def write_gatt_char(self, uuid, data, response=False):
            raise RuntimeError("write failed")

    remote = z407_app.Z407Remote.__new__(z407_app.Z407Remote)
    remote.client = FailingClient()
    remote.connected = True
    remote.current_volume = 50
    z407_app.remote_control = remote
    z407_app.connection_state = "connected"
    z407_app.last_error = None

    with pytest.raises(RuntimeError, match="write failed"):
        await remote.volume_up()

    assert remote.connected is False
    assert remote.current_volume == 50

    test_client = z407_app.app.test_client()
    response = await test_client.get("/api/status")
    payload = await response.get_json()

    assert response.status_code == 200
    assert payload["connected"] is False
    assert payload["connectionState"] == "error"
    assert payload["lastError"] == "write failed"


def test_ui_labels_distinguish_speaker_and_mac_controls():
    html = Path("templates/index.html").read_text()

    assert "Mute / Unmute" in html
    assert "speaker-skip-row" in html
    assert html.index("speaker-skip-row") < html.index("Speaker volume")
    assert "Speaker volume" in html
    assert "Subwoofer bass" in html
    assert "Mac Media Controls" in html
    assert "These are normal computer media controls" in html
    assert "AUX usually sounds better than Bluetooth" in html
    assert "Session Volume Estimate" in html
    assert "Only tracks changes made from this page" in html
    assert "Use Quit App or Ctrl+C to exit safely" in html
    assert "Avoid Ctrl+Z" in html
    assert "hero-actions" not in html
    assert "quit-button" not in html


def test_startup_banner_mentions_safe_exit():
    source = Path("app.py").read_text()

    assert "Quit safely: use the Quit App button or press Ctrl+C." in source
    assert "Do not use Ctrl+Z; it suspends the app instead of closing it." in source


def test_terminal_logging_is_quiet_by_default():
    assert z407_app.runtime_config.quiet_logs is True
    assert "hypercorn.access" in z407_app.QUIET_LOGGER_NAMES
