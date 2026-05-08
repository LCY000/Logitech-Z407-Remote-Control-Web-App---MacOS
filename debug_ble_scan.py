from __future__ import annotations

import argparse
import asyncio

from bleak import BleakScanner
from bleak.exc import BleakBluetoothNotAvailableError, BleakError


SERVICE_UUID = "0000fdc2-0000-1000-8000-00805f9b34fb"
Z407_NAME_MARKERS = ("z407", "zs283")


def is_z407_like(device) -> bool:
    name = (getattr(device, "name", "") or "").casefold()
    if any(marker in name for marker in Z407_NAME_MARKERS):
        return True

    metadata = getattr(device, "metadata", {}) or {}
    uuids = metadata.get("uuids", []) or metadata.get("service_uuids", [])
    return any(str(uuid).casefold() == SERVICE_UUID for uuid in uuids)


def describe_device(device) -> str:
    name = getattr(device, "name", None) or "(no name)"
    address = getattr(device, "address", "unknown")
    rssi = getattr(device, "rssi", None)
    metadata = getattr(device, "metadata", {}) or {}
    marker = " <== Z407 candidate" if is_z407_like(device) else ""
    return f"- name={name!r} address={address!r} rssi={rssi!r} metadata={metadata!r}{marker}"


async def scan(duration: float) -> int:
    try:
        print(f"Scanning BLE devices for {duration:g}s...")
        print("First pass: Z407 service UUID filter")
        filtered = await BleakScanner.discover(timeout=duration, service_uuids=[SERVICE_UUID])
        print(f"Filtered devices: {len(filtered)}")
        for device in filtered:
            print(describe_device(device))

        print("\nSecond pass: unfiltered scan")
        devices = await BleakScanner.discover(timeout=duration)
        print(f"All devices: {len(devices)}")
        for device in devices:
            print(describe_device(device))
    except BleakBluetoothNotAvailableError as exc:
        print(f"Bluetooth unavailable to Python/CoreBluetooth: {exc}")
        print("Check macOS Bluetooth is on and Terminal/Python has Bluetooth permission.")
        return 3
    except BleakError as exc:
        print(f"BLE scan failed: {exc}")
        return 4

    candidates = [device for device in [*filtered, *devices] if is_z407_like(device)]
    print(f"\nZ407 candidates: {len(candidates)}")
    for device in candidates:
        print(describe_device(device))

    return 0 if candidates else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug macOS BLE discovery for Logitech Z407.")
    parser.add_argument("--duration", type=float, default=8.0, help="Scan duration per pass in seconds")
    args = parser.parse_args()
    return asyncio.run(scan(args.duration))


if __name__ == "__main__":
    raise SystemExit(main())
