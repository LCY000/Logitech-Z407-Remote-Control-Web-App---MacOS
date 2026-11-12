# Logitech Z407 Remote Control Web App for macOS

**A macOS-first web remote for Logitech Z407 speakers.**

[繁體中文 README](README.zh-TW.md)

If the original wireless control dial feels awkward, takes up desk space, or has already gone missing, this app can be useful. My own setup is simple: the Z407 stays connected to the Mac over AUX, the physical dial is usually put away, and normal volume changes are handled directly on the Mac. The inconvenience only shows up when I occasionally want to adjust bass or switch input sources without keeping the dial on the desk. This app is meant for that exact situation: you usually do not need the dial, but you still have quick access to the controls it provides.

The app runs a local web server on your Mac and mimics the original wireless control dial. It controls the Logitech Z407 over Bluetooth Low Energy (BLE). It is optimized for a common Mac setup where audio stays on a 3.5mm AUX cable and BLE is only used for remote-control commands.

## Features

- Full Z407 speaker control: mute, volume, bass, input switching (AUX / USB / Bluetooth), Bluetooth pairing, and factory reset
- A volume dial you can drag: after one calibration the app knows the level (volume: 32 steps, bass: 15 steps), so you can drag the ring or tap a bass segment to jump straight to a level
- Hold − / + to keep stepping, or use the keyboard (↑ ↓ volume, ← → bass, M mute)
- Shows which input is active, and remembers volume, bass and input across restarts
- Reconnects on its own when the speaker is switched off and on again
- English and Traditional Chinese interface, switchable in the page, with light and dark themes
- macOS menu bar icon: close the browser tab and the app keeps running quietly; reopen the page from the menu bar any time
- Control from your phone: enable LAN mode to open the same page from a phone on the same Wi-Fi
- Mac media keys: play/pause, previous/next, volume, and mute from the same page
- Runs entirely on your Mac — no internet access required, no data leaves your machine

## Screenshots

<p align="center">
  <img src="assets/photo_1.png" alt="Z407 Control Web UI" width="640">
</p>

## Quick Start

### Mac App

Download `Logitech Z407 Remote Control.app` from the [Releases page](../../releases), unzip, and open it. You can drag it to your **Applications** folder for easy access.

The download is built for Apple Silicon Macs (M1 and later). On an Intel Mac, run it from Terminal or build it from source as described below.

The app is not notarized by Apple, so macOS blocks the first launch. To allow it:

1. Open the app once and dismiss the warning.
2. Go to **System Settings > Privacy & Security**, scroll down, and click **Open Anyway**.

On macOS 14 or earlier you can instead right-click the app and choose **Open**. If macOS says the app is damaged, run `xattr -cr "/Applications/Logitech Z407 Remote Control.app"` in Terminal and open it again.

The app places an icon in the macOS menu bar. Click it to reopen the browser UI or quit the app.

### Terminal

```bash
chmod +x run_macos.sh
./run_macos.sh
```

Then open `http://127.0.0.1:8765` in your browser. `run_macos.sh` creates a virtual environment if needed, installs dependencies the first time (and again only when `requirements.txt` changes), and starts the app.

### Build from Source

```bash
./build_macos_app.sh
```

The script runs the tests, then writes the app to `release/Logitech Z407 Remote Control.app` together with a versioned zip for sharing. The app is built for the architecture of the Mac you build on.

## Recommended Setup

Connect your Mac to the Z407 using a 3.5mm AUX cable. AUX usually sounds better than Bluetooth and avoids distortion at higher volumes.

## Safer Exit

Click **Quit app** in the web UI, or click the menu bar icon and choose **Quit**. Either method closes the app cleanly and disconnects from the speaker.

Opening the app a second time does not start a second copy — it just opens the page of the one already running.

If running from Terminal, press `Ctrl+C`. Avoid `Ctrl+Z` — it suspends the process instead of closing it.

If the app cannot reconnect to the Z407 after a restart, try unplugging the speaker power for a few seconds. This clears stale Bluetooth state on the speaker side.

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

You can add the page to your phone's home screen to use it like an app.

> **Note:** LAN mode has not been personally tested in all environments. It may require adjusting your Mac's firewall settings to allow incoming connections on port 8765.

## Security

- By default the app only listens on `127.0.0.1`, so nothing outside your Mac can reach it.
- Other websites cannot control your speaker: the app rejects requests that do not come from its own page.
- In LAN mode there is no password. Anyone on the same network can change volume, bass and input, and press the Mac media keys. Use it only on a network you trust. Factory reset and quit are never available to other devices — only to the Mac running the app.

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
./run_macos.sh --no-browser
./run_macos.sh --demo
./run_macos.sh --debug-scan --duration 8
```

- `--no-browser` starts the app without opening a browser tab.
- `--demo` simulates a speaker, so you can try or develop the interface without a Z407 or Bluetooth.
- Add `?lang=en` or `?lang=zh-TW` to the address to open the page in a specific language.

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

Project layout:

- `app.py` — web server, speaker connection and menu bar app
- `z407_ble.py`, `z407_config.py`, `z407_platform.py` — Bluetooth identifiers, command-line options, Mac media keys
- `templates/index.html`, `static/app.css`, `static/app.js` — the web page
- `static/i18n.json` — all interface text. To add a language, add a block with the same keys; the tests check that no key is missing.

Use `python app.py --demo` to work on the interface without a speaker.

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

## License

The code in this repository is released under the [MIT License](LICENSE).

This project started as a fork of Androrama's Linux web app, which is published as free to use and share with attribution but without a formal license file, and it relies on freundTech's protocol documentation. Credit for that work belongs to its authors; please keep the attribution above when you reuse this project.

## Disclaimer

This is an **unofficial** project and is not affiliated with, endorsed by, or connected to Logitech in any way.
"Logitech" is a trademark of its respective owner. This software is provided "as is" without warranty of any kind.

## Donations & Support

This project is 100% free. Using it, sharing it, and keeping attribution intact already helps.

If you find it useful, consider supporting **LCY000** (the macOS maintainer) — any support helps dedicate more time to this project and future improvements.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/cyouuu)
