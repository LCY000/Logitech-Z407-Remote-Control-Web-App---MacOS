from __future__ import annotations

import argparse
import asyncio

from collections import Counter

from bleak import BleakScanner, BleakClient
from bleak.exc import BleakBluetoothNotAvailableError, BleakError
from bleak.backends.characteristic import BleakGATTCharacteristic


SERVICE_UUID = "0000fdc2-0000-1000-8000-00805f9b34fb"
COMMAND_UUID = "c2e758b9-0e78-41e0-b0cb-98a593193fc5"
RESPONSE_UUID = "b84ac9c6-29c5-46d4-bba1-9d534784330f"
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


async def scan_once(duration: float) -> tuple[list, list]:
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
        raise
    except BleakError as exc:
        print(f"BLE scan failed: {exc}")
        raise

    return filtered, devices


async def scan(duration: float, rounds: int, pause: float) -> int:
    all_filtered = []
    all_devices = []

    for round_number in range(1, rounds + 1):
        if rounds > 1:
            print(f"\n=== Round {round_number}/{rounds} ===")

        try:
            filtered, devices = await scan_once(duration)
        except BleakBluetoothNotAvailableError:
            return 3
        except BleakError:
            return 4
        all_filtered.extend(filtered)
        all_devices.extend(devices)

        if round_number < rounds:
            await asyncio.sleep(pause)

    candidates = [device for device in [*all_filtered, *all_devices] if is_z407_like(device)]
    print(f"\nZ407 candidates: {len(candidates)}")
    for device in candidates:
        print(describe_device(device))

    seen_addresses = Counter(getattr(device, "address", "unknown") for device in [*all_filtered, *all_devices])
    repeated = [address for address, count in seen_addresses.items() if count > 1]
    if repeated:
        print("\nRepeated BLE addresses across passes:")
        for address in repeated:
            print(f"- {address}: {seen_addresses[address]} times")

    return 0 if candidates else 2


async def boundary_test(duration: float) -> int:
    """Connect to the Z407 and probe vol_down/bass_down at the boundary.

    Sends 25 vol_down commands, then 25 bass_down commands.
    Prints every BLE notification received so any boundary-specific
    packet is visible in the output.
    """
    print(f"Scanning for Z407 ({duration:g}s)...")
    try:
        devices = await BleakScanner.discover(timeout=duration, service_uuids=[SERVICE_UUID])
        if not devices:
            devices = await BleakScanner.discover(timeout=duration)
        candidates = [d for d in devices if is_z407_like(d)]
    except BleakError as exc:
        print(f"Scan failed: {exc}")
        return 4

    if not candidates:
        print("No Z407 found. Make sure the speaker is on and not connected to another device.")
        return 2

    device = candidates[0]
    print(f"Found: {device.name!r} ({device.address})")

    received: list[tuple[int, bytes]] = []   # (step, raw_bytes)

    async def on_notify(sender: BleakGATTCharacteristic, data: bytearray) -> None:
        step = getattr(on_notify, "_step", "?")
        label = getattr(on_notify, "_label", "")
        hex_data = data.hex()
        print(f"  [{label} step {step:>2}] notification: {hex_data}")
        received.append((step, bytes(data)))

    async with BleakClient(device) as client:
        await client.start_notify(RESPONSE_UUID, on_notify)

        # Handshake
        await client.write_gatt_char(COMMAND_UUID, bytes.fromhex("8405"), response=False)
        await asyncio.sleep(0.3)
        await client.write_gatt_char(COMMAND_UUID, bytes.fromhex("8400"), response=False)
        await asyncio.sleep(0.3)
        print("Connected. Starting boundary test...\n")

        # Phase 1: vol_down × 25
        print("--- Phase 1: vol_down × 25 ---")
        on_notify._label = "vol_down"
        for step in range(1, 26):
            on_notify._step = step
            await client.write_gatt_char(COMMAND_UUID, bytes.fromhex("8003"), response=False)
            await asyncio.sleep(0.15)

        await asyncio.sleep(0.5)

        # Phase 2: bass_down × 25
        print("\n--- Phase 2: bass_down × 25 ---")
        on_notify._label = "bass_down"
        for step in range(1, 26):
            on_notify._step = step
            await client.write_gatt_char(COMMAND_UUID, bytes.fromhex("8001"), response=False)
            await asyncio.sleep(0.15)

        await asyncio.sleep(0.5)

    print("\n--- Summary: unique notification bytes ---")
    seen: dict[bytes, list[int]] = {}
    for step, raw in received:
        seen.setdefault(raw, []).append(step)
    for raw, steps in sorted(seen.items()):
        print(f"  {raw.hex():<12}  at steps: {steps}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug macOS BLE discovery for Logitech Z407.")
    parser.add_argument("--duration", type=float, default=8.0, help="Scan duration per pass in seconds")
    parser.add_argument("--rounds", type=int, default=1, help="Number of filtered/unfiltered scan rounds")
    parser.add_argument("--pause", type=float, default=2.0, help="Pause between rounds in seconds")
    parser.add_argument("--boundary-test", action="store_true",
                        help="Connect and probe vol/bass boundaries, logging all BLE notifications")
    args = parser.parse_args()

    if args.boundary_test:
        return asyncio.run(boundary_test(args.duration))
    return asyncio.run(scan(args.duration, args.rounds, args.pause))


if __name__ == "__main__":
    raise SystemExit(main())
