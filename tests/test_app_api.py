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
    assert payload["setupHint"] == "AUX audio + BLE control"


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
