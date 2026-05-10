# Logitech Z407 Remote Control Web App for macOS

**A macOS-first web remote for Logitech Z407 speakers.**

[繁體中文 README](README.zh-TW.md)

If the original wireless control dial feels awkward, takes up desk space, or has already gone missing, this app can be useful. My own setup is simple: the Z407 stays connected to the Mac over AUX, the physical dial is usually put away, and normal volume changes are handled directly on the Mac. The inconvenience only shows up when I occasionally want to adjust bass or switch input sources without keeping the dial on the desk. This app is meant for that exact situation: you usually do not need the dial, but you still have quick access to the controls it provides.

The app runs a local web server on your Mac and mimics the original wireless control dial. It controls the Logitech Z407 over Bluetooth Low Energy (BLE). It is optimized for a common Mac setup where audio stays on a 3.5mm AUX cable and BLE is only used for remote-control commands.

## Features

- macOS-first defaults with `127.0.0.1:8765`, avoiding AirPlay's common port `5000`
- Local-only mode by default, with optional LAN mode for phone control on the same Wi-Fi
- Z407 speaker controls for mute, volume, bass, input switching, pairing, and factory reset
- Mac media controls for play/pause, previous/next, volume, and mute
- Real-time volume and bass tracking: step counters update on every confirmed BLE response (volume: 32 steps, bass: 15 steps), with a Calibrate button that drives both to zero so the display stays accurate across sessions
- Persistent state: volume and bass counters survive app restarts so you only need to calibrate once
- macOS menu bar icon — the server keeps running after you close the browser tab; reopen from the menu bar at any time
- BLE debug scan mode for diagnosing discovery issues on macOS
- Responsive browser UI for desktop and mobile

## Recommended Setup

1. Connect your Mac to the Z407 using a 3.5mm AUX cable.
2. Run the app on your Mac.
3. Use the browser UI to control the speaker or switch input sources.

Based on local testing, AUX usually sounds better than Bluetooth. Bluetooth may distort at higher volume. USB audio has not been tested yet.

## Quick Start

Run from Terminal:

```bash
chmod +x run_macos.sh
./run_macos.sh
```

Or double-click:

```text
Launch Logitech Z407 Web Control.command
```

Then open:

```text
http://127.0.0.1:8765
```

`run_macos.sh` creates a local virtual environment if needed, installs runtime dependencies, starts the server, and opens your browser.

## Mac App

Download the latest release from the [GitHub Releases page](../../releases), unzip, and double-click `Logitech Z407 Remote Control.app`. No Python or Terminal needed.

You can drag the app to your **Applications** folder so it is easy to find and launch like any other Mac app.

macOS will show a security prompt the first time. To open it:

1. Right-click (or Control-click) the app → **Open**
2. Click **Open** again in the dialog

The app places an icon in the macOS menu bar. Click it to reopen the browser UI or quit the app.

To build the app yourself from source:

```bash
./build_macos_app.sh
```

The packaged app will be created at:

```text
release/Logitech Z407 Remote Control.app
```

## Safer Exit

Use the web UI's `Quit` button or press `Ctrl+C` in the terminal.

If the web UI cannot find or reconnect to the Z407 after restarting the app, try unplugging the speaker power, wait a few seconds, and plug it back in. This can clear stale Bluetooth state on the speaker side.

Avoid `Ctrl+Z` in Terminal. It suspends the app instead of closing it. If you accidentally press it and see a suspended job, close that terminal job before starting the app again.

## Phone Control

To expose the app on your local network:

```bash
./run_macos.sh --lan
```

The app will print a LAN URL such as:

```text
http://192.168.1.35:8765
```

Open that address from a phone on the same Wi-Fi network.

## macOS Permissions

macOS may ask for:

- **Bluetooth permission** for Terminal, Python, or a packaged app
- **Accessibility permission** when you use the Mac Media Controls buttons

If Mac Media Controls do not work, check **System Settings > Privacy & Security**.

## Advanced Usage

Examples:

```bash
./run_macos.sh --port 9090
./run_macos.sh --lan --port 9090
./run_macos.sh --preferred-input aux
./run_macos.sh --verbose
./run_macos.sh --debug-scan --duration 8
```

Defaults:

- Host: `127.0.0.1`
- Port: `8765`
- Preferred input: `aux`
- Logs: quiet by default

If discovery fails, use:

```bash
./run_macos.sh --debug-scan --duration 10 --rounds 3 --pause 3
```

That command lists BLE devices visible to macOS and highlights likely Z407 candidates.

## Build From Source

Runtime requirements:

- Python 3.12+
- `pip`
- `venv`

Run from source:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Development tools:

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

## Credits & Acknowledgments

**macOS Version:**
macOS adaptation, current maintenance, and this macOS-first version by **LCY000**. This version was developed from the original Linux web app into a macOS-focused app.

**Original Linux Web App:**
Original implementation by **Androrama**.

**Reverse Engineering:**
Special thanks to **freundTech** for the reverse engineering work that made this possible.
https://github.com/freundTech/logi-z407-reverse-engineering

**Upstream Project:**
This version was adapted from `Androrama/Logitech-Z407-Remote-Control-Web-App---Linux`.

## Disclaimer

This is an **unofficial** project and is not affiliated with, endorsed by, or connected to Logitech in any way.
"Logitech" is a trademark of its respective owner. This software is provided "as is" without warranty of any kind.

## Donations & Support

This project is based on free community work. Please keep supporting and crediting the original author and reverse engineering work.

This project is 100% free. Using it, sharing it, and keeping attribution intact already helps.

If you want to give additional support, any donation helps the original author dedicate more time and resources to this project and other community work. Thanks to everyone who has already supported the project.

Original author support page:
https://androrama.com
