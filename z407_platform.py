from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformInfo:
    system: str = sys.platform

    @property
    def key(self) -> str:
        if self.system == "darwin":
            return "macos"
        if self.system.startswith("linux"):
            return "linux"
        if self.system.startswith("win"):
            return "windows"
        return "unknown"


MEDIA_KEY_MAP = {
    "next": "nexttrack",
    "prev": "prevtrack",
    "play_pause_pc": "playpause",
    "vol_up_pc": "volumeup",
    "vol_down_pc": "volumedown",
    "mute_pc": "volumemute",
}

LINUX_XF86_MAP = {
    "next": "XF86AudioNext",
    "prev": "XF86AudioPrev",
    "play_pause_pc": "XF86AudioPlay",
    "vol_up_pc": "XF86AudioRaiseVolume",
    "vol_down_pc": "XF86AudioLowerVolume",
    "mute_pc": "XF86AudioMute",
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
    if platform.key == "linux":
        key = _lookup_media_key(LINUX_XF86_MAP, command)
        try:
            subprocess.Popen(["xdotool", "key", key])
        except FileNotFoundError as exc:
            raise RuntimeError("Missing xdotool. Install it with: sudo apt install xdotool") from exc
        return

    if platform.key in ("macos", "windows"):
        import pyautogui

        pyautogui.press(media_key_name(command))
        return

    raise RuntimeError("Host media keys are not supported on this platform.")


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
            "Host media keys may require Accessibility permission in System Settings.",
            "Use AUX on the Z407 when Mac audio is connected through a 3.5mm cable.",
        ]
        setup_hint = "AUX audio + BLE control"
        host_media_supported = True
    elif platform_key == "linux":
        permission_notes = [
            "Bluetooth access may require BlueZ permissions or setcap.",
            "Host media keys require xdotool.",
        ]
        setup_hint = "BLE speaker control"
        host_media_supported = True
    elif platform_key == "windows":
        permission_notes = [
            "Host media keys use PyAutoGUI.",
            "Bluetooth permission depends on Windows device settings.",
        ]
        setup_hint = "BLE speaker control"
        host_media_supported = True
    else:
        permission_notes = ["This platform has not been tested."]
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
