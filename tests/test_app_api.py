import pytest

import app as z407_app
from z407_config import RuntimeConfig


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
async def test_unknown_command_returns_400():
    z407_app.remote_control = object()

    test_client = z407_app.app.test_client()
    response = await test_client.post("/api/not_a_command")
    payload = await response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["error"] == "Unknown command"
