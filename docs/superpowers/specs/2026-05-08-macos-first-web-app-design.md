# macOS-First Web App Design

## Goal

Adapt the existing Logitech Z407 remote control project into a macOS-first web app while keeping Linux support where practical. The app remains browser-based: a local Python/Quart server controls the speaker over BLE, and the user controls it through a web UI.

The first macOS version should be useful from the Mac itself and from a phone on the same Wi-Fi network.

## Non-Goals

- Do not rewrite the app as a native SwiftUI/macOS application.
- Do not remove existing project credits or rebrand the app.
- Do not attempt to guarantee real Z407 BLE behavior without physical-device testing.
- Do not add user accounts, cloud sync, or remote access outside the local network.

## Current Problems

- The app defaults to port `5000`, which conflicts with Apple AirPlay usage on macOS.
- The app defaults to `0.0.0.0`, exposing control endpoints to the local network without an explicit opt-in.
- BLE connection logic stores and reconnects by address only; this is weaker on macOS because CoreBluetooth uses per-machine UUIDs instead of public Bluetooth addresses.
- Linux-specific behavior is embedded in `app.py`, the installer, README, and UI.
- The UI presents Linux-only help (`xdotool`, `setcap`, `rfkill`) and looks dated.
- Dangerous endpoints such as shutdown and factory reset have no backend-side safety distinction.

## Architecture

Keep the current server-rendered web app, but separate responsibilities:

- `app.py` remains the Quart entry point and route layer.
- A platform module owns host/port defaults, browser launch commands, media key simulation, and user-facing capability text.
- The BLE remote class owns Z407 discovery, connection, keepalive, and command sending.
- The UI consumes `/api/status`, `/api/capabilities`, and command endpoints to render platform-appropriate controls and help text.

The implementation can start with small modules rather than a large framework. The goal is clearer boundaries without over-engineering.

## macOS Runtime Behavior

- Default host is `127.0.0.1`.
- Default port is `8765`.
- `--lan` binds to `0.0.0.0` so phones on the same Wi-Fi can open the UI.
- `--ip` and `--port` remain available for manual overrides.
- Console output shows both local and LAN URLs when relevant.
- The app documents that macOS may require Bluetooth permission for the terminal or packaged app, and Accessibility permission for simulated media keys.

## Linux Runtime Behavior

- Linux should continue to work, but macOS becomes the priority for defaults and UI.
- Linux can keep using `xdotool` for host media keys.
- Linux-specific installation scripts may remain, but UI and README should no longer imply the entire project is Linux-only.

## BLE Design

- Discovery should return the full `BLEDevice` object.
- `Z407Remote` should initialize `BleakClient` with the discovered `BLEDevice` rather than only `device.address`.
- Status should include enough diagnostic detail to explain common failures, such as "not found", "connecting", "connected", and "error".
- Connection retries should avoid Linux-only adapter reset behavior on macOS.
- Existing Z407 command hex values remain unchanged.

## Web/API Design

- `/api/status` returns connection state, estimated volume, platform, mode, and last error if available.
- `/api/capabilities` returns platform-specific capabilities and help text.
- Existing command endpoints can remain for compatibility.
- Dangerous commands still require UI confirmation, and backend command handling should keep them explicit rather than relying on arbitrary method lookup.
- Shutdown remains local-app behavior, but the UI should make it clear it closes the server process.

## UI Design

Create a modern single-page control panel without adding a frontend build system.

Visual direction:

- macOS-first, clean, tactile control surface.
- Clear state hierarchy: connection status first, primary speaker controls second, host media controls third, settings/help last.
- Avoid Linux-only labels in the main UI.
- Use CSS variables, responsive layout, and fewer inline styles.
- Keep the UI usable on desktop Safari/Chrome and mobile Safari.

Functional layout:

- Header with app name, connection pill, and active network mode.
- Primary card for speaker play/pause, track controls, volume, and bass.
- Input source segmented control for AUX, USB, and Bluetooth.
- Host media control card labeled according to platform.
- Advanced card for pairing, factory reset, shutdown, and troubleshooting.
- Help panel populated from `/api/capabilities`.

## Security and Network Scope

- Default local-only mode reduces accidental LAN exposure.
- LAN mode is explicit through `--lan`.
- Console output and UI should make the current exposure clear.
- No authentication is required for the first version because the app is local-network only, but the design leaves room for a simple shared token later.

## Build and Run

Add macOS-friendly run/build support:

- `run_macos.sh` creates or reuses a virtual environment, installs dependencies, starts the app on port `8765`, and opens the browser.
- A future `build_macos.sh` can package with PyInstaller, but the first implementation should prioritize reliable source execution.
- README should explain both local-only and LAN modes.

## Testing

Automated checks should cover:

- Python syntax compilation.
- CLI default host/port behavior.
- Platform capability generation.
- Basic API responses where they can be tested without BLE hardware.

Manual checks required on the user's Mac:

- App starts at `http://127.0.0.1:8765`.
- Browser opens correctly.
- macOS prompts or settings allow Bluetooth access.
- Z407 is discovered and connects.
- Speaker commands work.
- Host media keys work after Accessibility permission if needed.
- `--lan` exposes a URL reachable from a phone on the same Wi-Fi.

## Acceptance Criteria

- macOS no longer defaults to port `5000`.
- Local-only and LAN modes both work.
- UI no longer shows Linux-only instructions on macOS.
- UI is visually modernized and responsive.
- BLE connection code is more macOS-compatible by using discovered device objects.
- Existing Linux source-run behavior remains functional where possible.
- Verification output is reported honestly, including any hardware-dependent checks that cannot be completed in this environment.
