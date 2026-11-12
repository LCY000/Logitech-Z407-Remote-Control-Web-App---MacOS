import pytest

import app as z407_app
from z407_config import RuntimeConfig

CLIENT_HEADERS = {z407_app.CLIENT_HEADER: "1"}

_GLOBALS = (
    "runtime_config",
    "remote_control",
    "connection_state",
    "last_error",
    "last_error_code",
    "busy_task",
    "CURRENT_PLATFORM",
    "_link_changed",
    "_shutdown_requested",
)


@pytest.fixture(autouse=True)
def isolated_app(tmp_path, monkeypatch):
    """Fresh globals for every test, and never touch the real ~/.z407 state file."""
    snapshot = {name: getattr(z407_app, name) for name in _GLOBALS}
    monkeypatch.setattr(z407_app, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(z407_app, "PREFS_FILE", tmp_path / "prefs.json")
    monkeypatch.setattr(z407_app, "speaker_state", z407_app.SpeakerState())
    monkeypatch.setattr(z407_app, "preferences", z407_app.Preferences())
    monkeypatch.setattr(z407_app, "is_local_client", lambda: True)
    monkeypatch.setattr(z407_app, "STEP_DELAY_SECONDS", 0)
    monkeypatch.setattr(z407_app, "ACK_SETTLE_SECONDS", 0)
    z407_app.runtime_config = RuntimeConfig(host="127.0.0.1", port=8765, lan_enabled=False, preferred_input="aux")
    z407_app.remote_control = None
    z407_app.busy_task = None
    z407_app._link_changed = None
    yield
    for name, value in snapshot.items():
        setattr(z407_app, name, value)


@pytest.fixture
def client():
    return z407_app.app.test_client()


@pytest.fixture
def post(client):
    async def _post(path, **kwargs):
        headers = {**CLIENT_HEADERS, **kwargs.pop("headers", {})}
        return await client.post(path, headers=headers, **kwargs)

    return _post


class FakeClient:
    """A BLE client that records writes and answers like a Z407 (when `respond`)."""

    def __init__(self, respond=True, fail_writes=False):
        self.respond = respond
        self.fail_writes = fail_writes
        self.writes = []
        self.callback = None
        self.disconnected = False

    async def connect(self):
        return None

    async def disconnect(self):
        self.disconnected = True

    async def start_notify(self, _uuid, callback):
        self.callback = callback

    async def write_gatt_char(self, _uuid, data, response=False):
        if self.fail_writes:
            raise RuntimeError("write failed")
        command = bytes(data).hex()
        self.writes.append(command)
        if self.respond and self.callback and command.startswith("80"):
            await self.callback(None, bytearray(bytes.fromhex("c0" + command[2:])))


@pytest.fixture
def connected_remote():
    """Install a connected Z407Remote backed by a FakeClient."""

    def _make(respond=True, fail_writes=False):
        fake = FakeClient(respond=respond, fail_writes=fail_writes)
        remote = z407_app.Z407Remote(z407_app.DemoDevice(), client=fake)
        remote.connected = True
        fake.callback = remote._receive_data
        z407_app.remote_control = remote
        z407_app.connection_state = "connected"
        return remote, fake

    return _make
