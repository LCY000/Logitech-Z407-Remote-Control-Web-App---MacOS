import asyncio
import sys
from types import SimpleNamespace

import pytest

import z407_platform
from z407_platform import PlatformInfo, get_capabilities, media_key_name, send_host_media_key


def test_macos_capabilities_are_aux_first():
    info = PlatformInfo(system="darwin")
    capabilities = get_capabilities(info, preferred_input="aux", lan_enabled=False)

    assert capabilities["platform"] == "macos"
    assert capabilities["preferredInput"] == "aux"
    assert capabilities["networkMode"] == "local"
    assert "Choose the Z407 input below" in capabilities["setupHint"]
    assert any("Accessibility permission" in note for note in capabilities["permissionNotes"])
    assert any("Mac Media Controls use normal computer media keys" in note for note in capabilities["permissionNotes"])


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


def test_linux_send_host_media_key_uses_xdotool(monkeypatch):
    calls = []

    def fake_popen(args):
        calls.append(args)

    monkeypatch.setattr(z407_platform.subprocess, "Popen", fake_popen)

    asyncio.run(send_host_media_key("next", PlatformInfo(system="linux")))

    assert calls == [["xdotool", "key", "XF86AudioNext"]]


def test_linux_send_host_media_key_missing_xdotool_has_install_hint(monkeypatch):
    def fake_popen(args):
        raise FileNotFoundError

    monkeypatch.setattr(z407_platform.subprocess, "Popen", fake_popen)

    with pytest.raises(RuntimeError, match="sudo apt install xdotool"):
        asyncio.run(send_host_media_key("next", PlatformInfo(system="linux")))


def test_macos_send_host_media_key_lazy_imports_pyautogui(monkeypatch):
    presses = []
    fake_pyautogui = SimpleNamespace(press=lambda key: presses.append(key))

    monkeypatch.delattr(z407_platform, "pyautogui", raising=False)
    monkeypatch.setitem(sys.modules, "pyautogui", fake_pyautogui)

    asyncio.run(send_host_media_key("play_pause_pc", PlatformInfo(system="darwin")))

    assert presses == ["playpause"]


def test_unknown_media_key_command_has_clear_error():
    with pytest.raises(ValueError, match="Unknown media command: not_real"):
        media_key_name("not_real")
