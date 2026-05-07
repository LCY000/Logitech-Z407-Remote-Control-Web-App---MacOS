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
