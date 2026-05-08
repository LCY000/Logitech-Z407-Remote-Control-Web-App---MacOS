# Logitech Z407 Remote Control Web App for macOS

**A macOS-first web remote for Logitech Z407 speakers.**

[繁體中文 README](README.zh-TW.md)

The app runs a local web server on your Mac and controls the Logitech Z407 over Bluetooth Low Energy (BLE). It is optimized for a common setup where audio stays on a 3.5mm AUX cable and BLE is only used for remote-control commands.

This app is useful when the original wireless control dial is inconvenient, takes up desk space, or has simply gone missing. My own setup is straightforward: the speaker stays connected to the Mac over AUX, the physical dial is usually put away, and day-to-day volume changes happen directly on the Mac. The annoyance only shows up when I occasionally want to adjust bass or switch inputs. This app is designed for exactly that situation: it gives you quick access to the controls that are awkward to reach once the dial is no longer on the desk.

## Features

- macOS-first defaults with `127.0.0.1:8765`, avoiding AirPlay's common port `5000`
- Local-only mode by default, with optional LAN mode for phone control on the same Wi-Fi
- Z407 speaker controls for mute, volume, bass, input switching, pairing, and factory reset
- Mac media controls for play/pause, previous/next, volume, and mute
- BLE debug scan mode for diagnosing discovery issues on macOS
- Responsive browser UI for desktop and mobile

## Recommended Setup

1. Connect your Mac to the Z407 using a 3.5mm AUX cable.
2. Set the Z407 input to `AUX`.
3. Run the app on your Mac.
4. Use the browser UI to switch inputs or control the speaker.

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

## Sharing With Other Mac Users

For source-based use, share this repository and have people launch either:

- `Launch Logitech Z407 Web Control.command`
- `./run_macos.sh`

For a more user-friendly standalone app, build:

```bash
./build_macos_app.sh
```

The packaged app will be created at:

```text
release/Logitech Z407 Remote Control.app
```

Quitting the app should stop the bundled local server as well.

## Safer Exit

Use the web UI's `Quit` button or press `Ctrl+C` in the terminal.

Do not use `Ctrl+Z`. It suspends the process instead of closing it and can leave the local server or BLE state stale. If you accidentally suspend it, run `jobs` and then `kill %1`.

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

**Original Web App:**
Original implementation by **Androrama**.

**macOS-first Adaptation:**
Current adaptation and maintenance by **LCY000**.

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
