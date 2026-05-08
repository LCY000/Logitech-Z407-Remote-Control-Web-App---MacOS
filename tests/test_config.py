import pytest

from z407_config import RuntimeConfig, build_runtime_config, get_lan_ip


def test_default_runtime_config_is_macos_safe_local_mode():
    config = build_runtime_config([])

    assert config.host == "127.0.0.1"
    assert config.port == 8765
    assert config.lan_enabled is False
    assert config.preferred_input == "aux"
    assert config.quiet_logs is True


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


def test_manual_ipv4_loopback_does_not_enable_lan():
    config = build_runtime_config(["--ip", "127.0.0.2"])

    assert config.host == "127.0.0.2"
    assert config.lan_enabled is False


def test_manual_ipv4_shorthand_loopback_does_not_enable_lan():
    config = build_runtime_config(["--ip", "127.1"])

    assert config.host == "127.1"
    assert config.lan_enabled is False


def test_manual_ipv6_loopback_does_not_enable_lan():
    config = build_runtime_config(["--ip", "::1"])

    assert config.host == "::1"
    assert config.lan_enabled is False


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


def test_get_lan_ip_returns_loopback_fallback_when_socket_creation_fails(monkeypatch):
    class BrokenSocketModule:
        AF_INET = 2
        SOCK_DGRAM = 2

        def socket(self, *_args):
            raise OSError("socket unavailable")

    monkeypatch.setattr("z407_config.socket", BrokenSocketModule())

    assert get_lan_ip() == "127.0.0.1"


def test_invalid_preferred_input_rejects():
    with pytest.raises(SystemExit):
        build_runtime_config(["--preferred-input", "line-in"])


def test_packaging_scripts_exist():
    from pathlib import Path

    assert Path("Launch Logitech Z407 Web Control.command").exists()
    assert Path("build_macos_app.sh").exists()
    assert Path("Logitech_Z407_MacOS.spec").exists()
