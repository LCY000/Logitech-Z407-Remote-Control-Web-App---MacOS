import asyncio
import pytest

import z407_platform
from z407_platform import PlatformInfo, get_capabilities, media_key_code, send_host_media_key


def test_macos_capabilities_are_aux_first():
    info = PlatformInfo(system="darwin")
    capabilities = get_capabilities(info, preferred_input="aux", lan_enabled=False)

    assert capabilities["platform"] == "macos"
    assert capabilities["preferredInput"] == "aux"
    assert capabilities["networkMode"] == "local"
    assert "Choose the Z407 input below" in capabilities["setupHint"]
    assert any("Accessibility permission" in note for note in capabilities["permissionNotes"])
    assert any("Mac Media Controls use normal computer media keys" in note for note in capabilities["permissionNotes"])


def test_non_macos_capabilities_do_not_claim_media_keys_supported():
    info = PlatformInfo(system="freebsd")
    capabilities = get_capabilities(info, preferred_input="aux", lan_enabled=True)

    assert capabilities["platform"] == "unknown"
    assert capabilities["networkMode"] == "lan"
    assert capabilities["hostMediaKeysSupported"] is False
    assert capabilities["permissionNotes"] == ["This platform has not been tested on this macOS-first branch."]


def test_unknown_capabilities_do_not_claim_media_keys_supported():
    info = PlatformInfo(system="freebsd")
    capabilities = get_capabilities(info, preferred_input="aux", lan_enabled=False)

    assert capabilities["platform"] == "unknown"
    assert capabilities["hostMediaKeysSupported"] is False


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("vol_up_pc", 0),
        ("vol_down_pc", 1),
        ("mute_pc", 7),
        ("play_pause_pc", 16),
        ("next", 17),
        ("prev", 18),
    ],
)
def test_media_key_codes(command, expected):
    assert media_key_code(command) == expected


def test_non_macos_send_host_media_key_is_unsupported():
    with pytest.raises(RuntimeError, match="only supported on macOS in this branch"):
        asyncio.run(send_host_media_key("next", PlatformInfo(system="freebsd")))


def test_macos_send_host_media_key_posts_the_key_code(monkeypatch):
    posted = []
    monkeypatch.setattr(z407_platform, "_post_media_key", posted.append)

    asyncio.run(send_host_media_key("play_pause_pc", PlatformInfo(system="darwin")))

    assert posted == [16]


def test_missing_accessibility_permission_raises_and_posts_nothing(monkeypatch):
    import Quartz

    posted = []
    requested = []
    monkeypatch.setattr(Quartz, "CGPreflightPostEventAccess", lambda: False)
    monkeypatch.setattr(Quartz, "CGRequestPostEventAccess", lambda: requested.append(True))
    monkeypatch.setattr(Quartz, "CGEventPost", lambda *args: posted.append(args))

    with pytest.raises(z407_platform.AccessibilityPermissionError):
        z407_platform._post_media_key(16)

    assert requested == [True]
    assert posted == []


def test_media_key_posts_key_down_then_key_up(monkeypatch):
    import Quartz

    posted = []
    monkeypatch.setattr(Quartz, "CGPreflightPostEventAccess", lambda: True)
    monkeypatch.setattr(Quartz, "CGEventPost", lambda tap, event: posted.append(tap))

    z407_platform._post_media_key(16)

    assert len(posted) == 2


def test_unknown_media_key_command_has_clear_error():
    with pytest.raises(ValueError, match="Unknown media command: not_real"):
        media_key_code("not_real")
