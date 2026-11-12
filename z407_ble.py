"""Z407 Bluetooth LE identifiers and discovery helpers shared by the app and the debug scripts.

Protocol reverse engineered by freundTech:
https://github.com/freundTech/logi-z407-reverse-engineering
"""
from __future__ import annotations

SERVICE_UUID = "0000fdc2-0000-1000-8000-00805f9b34fb"
COMMAND_UUID = "c2e758b9-0e78-41e0-b0cb-98a593193fc5"
RESPONSE_UUID = "b84ac9c6-29c5-46d4-bba1-9d534784330f"
Z407_NAME_MARKERS = ("z407", "zs283")


def is_z407_device(device, advertisement=None) -> bool:
    """True when a scan result looks like a Z407 (by name or advertised service)."""
    names = (getattr(device, "name", None), getattr(advertisement, "local_name", None))
    for name in names:
        folded = (name or "").casefold()
        if any(marker in folded for marker in Z407_NAME_MARKERS):
            return True

    service_uuids = getattr(advertisement, "service_uuids", None) or []
    return any(str(uuid).casefold() == SERVICE_UUID for uuid in service_uuids)
