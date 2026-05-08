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


MEDIA_KEY_MAP = {
    "next": "nexttrack",
    "prev": "prevtrack",
    "play_pause_pc": "playpause",
    "vol_up_pc": "volumeup",
    "vol_down_pc": "volumedown",
    "mute_pc": "volumemute",
}

def _lookup_media_key(mapping: dict[str, str], command: str) -> str:
    try:
        return mapping[command]
    except KeyError as exc:
        raise ValueError(f"Unknown media command: {command}") from exc


def media_key_name(command: str) -> str:
    return _lookup_media_key(MEDIA_KEY_MAP, command)


async def send_host_media_key(command: str, platform: PlatformInfo | None = None) -> None:
    platform = platform or PlatformInfo()
    if platform.key == "macos":
        import pyautogui

        pyautogui.press(media_key_name(command))
        return

    raise RuntimeError("Host media keys are only supported on macOS in this branch.")


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
