"""
Probe whether the Z407 reports its current volume/bass state at connection time.

Usage:
    python probe_state.py

Connects to the speaker, waits 3 seconds for all handshake packets, then
disconnects. Run this at known volume/bass levels to see if any packet
changes value.

Test procedure:
    1. Calibrate in the web app (both vol and bass → 0)
    2. Set a known state, e.g.: vol_up × 5, bass_up × 3
    3. Run this script and record the output
    4. Repeat at different known values
    5. If a packet's second byte matches your step count → we have state reporting
"""
from __future__ import annotations

import asyncio
import sys

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakBluetoothNotAvailableError, BleakError

SERVICE_UUID  = "0000fdc2-0000-1000-8000-00805f9b34fb"
COMMAND_UUID  = "c2e758b9-0e78-41e0-b0cb-98a593193fc5"
RESPONSE_UUID = "b84ac9c6-29c5-46d4-bba1-9d534784330f"

Z407_NAME_MARKERS = ("z407", "zs283")


def is_z407_like(device) -> bool:
    name = (getattr(device, "name", "") or "").casefold()
    if any(m in name for m in Z407_NAME_MARKERS):
        return True
    metadata = getattr(device, "metadata", {}) or {}
    uuids = metadata.get("uuids", []) or metadata.get("service_uuids", [])
    return any(str(u).casefold() == SERVICE_UUID for u in uuids)


async def probe(scan_duration: float = 8.0, listen_seconds: float = 4.0) -> int:
    print(f"Scanning for Z407 ({scan_duration:g}s)...")
    try:
        devices = await BleakScanner.discover(timeout=scan_duration, service_uuids=[SERVICE_UUID])
        if not devices:
            devices = await BleakScanner.discover(timeout=scan_duration)
        candidates = [d for d in devices if is_z407_like(d)]
    except BleakBluetoothNotAvailableError as exc:
        print(f"Bluetooth unavailable: {exc}")
        return 3
    except BleakError as exc:
        print(f"Scan failed: {exc}")
        return 4

    if not candidates:
        print("No Z407 found.")
        return 2

    device = candidates[0]
    print(f"Found: {device.name!r} ({device.address})\n")

    received: list[tuple[str, bytes]] = []  # (phase, raw)

    def on_notify(sender: BleakGATTCharacteristic, data: bytearray) -> None:
        raw = bytes(data)
        hex_str = data.hex()
        dec_values = " ".join(str(b) for b in data)
        received.append(("notify", raw))
        print(f"  packet: {hex_str:<14}  bytes(dec): [{dec_values}]")

    try:
        async with BleakClient(device) as client:
            await client.start_notify(RESPONSE_UUID, on_notify)

            print("--- Handshake ---")
            await client.write_gatt_char(COMMAND_UUID, bytes.fromhex("8405"), response=False)
            await asyncio.sleep(0.3)
            await client.write_gatt_char(COMMAND_UUID, bytes.fromhex("8400"), response=False)

            print(f"\nListening for {listen_seconds}s (no commands sent)...\n")
            await asyncio.sleep(listen_seconds)

    except BleakError as exc:
        print(f"\nConnection error: {exc}")
        return 4

    print("\n--- All packets received ---")
    seen: dict[bytes, int] = {}
    for _, raw in received:
        seen[raw] = seen.get(raw, 0) + 1

    for raw, count in sorted(seen.items()):
        hex_str = raw.hex()
        dec_values = " ".join(str(b) for b in raw)
        print(f"  {hex_str:<14}  (×{count})  bytes(dec): [{dec_values}]")

    print("\n--- Interpretation hints ---")
    for raw in seen:
        if raw[0] == 0xcf:
            print(f"  cf-prefix packet: {raw.hex()}")
            print(f"    byte[1] = {raw[1]} (dec)  ← could be volume level")
            if len(raw) > 2:
                print(f"    byte[2] = {raw[2]} (dec)  ← could be bass level")
        elif raw[0] == 0xd4 and len(raw) >= 3 and raw[2] not in (0x01, 0x03):
            print(f"  d4-prefix unknown: {raw.hex()}  ({[b for b in raw]})")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(probe()))
