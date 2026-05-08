# Logitech Z407 macOS Web Control

**A macOS-first web remote for Logitech Z407 speakers, adapted from the original Linux web app.**

[繁體中文 README](README.zh-TW.md)

This app runs a local web server on your Mac and controls the Logitech Z407 over Bluetooth Low Energy (BLE). It is designed for a common Mac setup: **audio through a 3.5mm AUX cable, control through BLE**.

## Features

- macOS-first defaults: `127.0.0.1:8765`, avoiding macOS AirPlay's common port `5000`.
- Local-only mode by default.
- Optional LAN mode for phone control on the same Wi-Fi.
- Speaker controls: play/pause, speaker volume, bass, input source, pairing, factory reset.
- Mac media controls through simulated media keys.
- Modern responsive web UI for desktop and mobile browsers.

## Recommended macOS Setup: AUX Audio + BLE Control

1. Connect your Mac to the Z407 using a 3.5mm AUX cable.
2. Select `AUX` as the Z407 input source.
3. Run this app on your Mac.
4. Use the web UI to control speaker volume, bass, input source, and Mac playback.

The audio stays wired through AUX. BLE is only used as the remote-control channel.

## Quick Start on macOS

```bash
chmod +x run_macos.sh
./run_macos.sh
```

Open:

```text
http://127.0.0.1:8765
```

The script creates a Python virtual environment, installs dependencies, starts the server, and opens your browser.

## Phone Control on the Same Wi-Fi

Run:

```bash
./run_macos.sh --lan
```

`run_macos.sh` starts LAN mode, and the Python app prints a LAN URL such as:

```text
http://192.168.1.35:8765
```

Open that URL from your phone while it is connected to the same Wi-Fi network.

## macOS Permissions

macOS may ask for:

- **Bluetooth permission** for Terminal, Python, or the packaged app.
- **Accessibility permission** for Mac media keys such as play/pause and volume.

If host media keys do not work, open System Settings and check Privacy & Security permissions.

## Advanced Configuration

```bash
./run_macos.sh --port 9090
./run_macos.sh --lan
./run_macos.sh --lan --port 9090
./run_macos.sh --preferred-input aux
```

Defaults:

- Host: `127.0.0.1`
- Port: `8765`
- Preferred input: `aux`

## Linux Notes

Linux source-run behavior is kept where practical. Host media keys on Linux require `xdotool`, and Bluetooth access may require BlueZ permissions or capabilities.

The original Linux installer scripts remain for reference, but this adaptation focuses on macOS usage.

## Build from Source

Prerequisites:

- Python 3.12+
- `pip`
- `venv`

Install and run:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Repository Name Recommendation

If you publish this adaptation as a separate GitHub repository, recommended names include:

- `logitech-z407-macos-web-control`
- `z407-macos-remote-web`

## Credits & Acknowledgments

**Original Web App:**
Original implementation by **Androrama**.

**macOS-first Adaptation:**
Current adaptation and maintenance by **LCY000**.

**Reverse Engineering:**
Special thanks to **freundTech** for the reverse engineering work that made this possible.
https://github.com/freundTech/logi-z407-reverse-engineering

**Upstream Project:**
This version is adapted from `Androrama/Logitech-Z407-Remote-Control-Web-App---Linux`.

## Disclaimer

This is an **unofficial** project and is not affiliated with, endorsed by, or connected to Logitech in any way.
"Logitech" is a trademark of its respective owner. This software is provided "as is" without warranty of any kind.

## Donations & Support

This project is based on free community work. Please keep supporting and crediting the original author and reverse engineering work.

This project is 100% free. Donations and support help the original author dedicate time and resources to this project and other community work.

Original author support page:
https://androrama.com
