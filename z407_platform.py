from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformInfo:
    system: str = sys.platform

    @property
    def key(self) -> str:
        if self.system == "darwin":
            return "macos"
        return "unknown"


class AccessibilityPermissionError(RuntimeError):
    """macOS has not granted this app permission to post keyboard events."""


# NX_KEYTYPE_* constants from IOKit/hidsystem/ev_keymap.h
MEDIA_KEY_CODES = {
    "vol_up_pc": 0,       # NX_KEYTYPE_SOUND_UP
    "vol_down_pc": 1,     # NX_KEYTYPE_SOUND_DOWN
    "mute_pc": 7,         # NX_KEYTYPE_MUTE
    "play_pause_pc": 16,  # NX_KEYTYPE_PLAY
    "next": 17,           # NX_KEYTYPE_NEXT
    "prev": 18,           # NX_KEYTYPE_PREVIOUS
}

_NS_EVENT_TYPE_SYSTEM_DEFINED = 14
_NS_EVENT_SUBTYPE_AUX_CONTROL_BUTTONS = 8
_KEY_DOWN = 0xA
_KEY_UP = 0xB


def media_key_code(command: str) -> int:
    try:
        return MEDIA_KEY_CODES[command]
    except KeyError as exc:
        raise ValueError(f"Unknown media command: {command}") from exc


def _post_media_key(key_code: int) -> None:
    """Post a media key press + release through Quartz (the same thing a keyboard does)."""
    import Quartz
    from AppKit import NSEvent

    preflight = getattr(Quartz, "CGPreflightPostEventAccess", None)
    if preflight is not None and not preflight():
        request_access = getattr(Quartz, "CGRequestPostEventAccess", None)
        if request_access is not None:
            request_access()  # shows the macOS permission prompt once
        raise AccessibilityPermissionError(
            "macOS blocked the media key. Allow this app under "
            "System Settings > Privacy & Security > Accessibility, then try again."
        )

    for key_state in (_KEY_DOWN, _KEY_UP):
        event = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
            _NS_EVENT_TYPE_SYSTEM_DEFINED,
            (0, 0),
            key_state << 8,
            0,
            0,
            None,
            _NS_EVENT_SUBTYPE_AUX_CONTROL_BUTTONS,
            (key_code << 16) | (key_state << 8),
            -1,
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event.CGEvent())


async def send_host_media_key(command: str, platform: PlatformInfo | None = None) -> None:
    platform = platform or PlatformInfo()
    key_code = media_key_code(command)
    if platform.key != "macos":
        raise RuntimeError("Host media keys are only supported on macOS in this branch.")
    _post_media_key(key_code)


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
            "Mac Media Controls use normal computer media keys and may require Accessibility permission in System Settings when you use those buttons.",
            "Choose AUX, USB, or Bluetooth from the web UI to switch the Z407 input source.",
        ]
        setup_hint = "Choose the Z407 input below. AUX is recommended when your Mac is connected by cable."
        host_media_supported = True
    else:
        permission_notes = ["This platform has not been tested on this macOS-first branch."]
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
