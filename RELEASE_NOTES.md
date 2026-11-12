# Release Notes for Mac Users

## What's New in 0.3.0

- New interface built around a volume dial. After calibrating once you can drag the ring, or tap a bass segment, to jump to an exact level.
- Hold − / + to keep stepping. Keyboard shortcuts: ↑ ↓ volume, ← → bass, M mute.
- English and Traditional Chinese, switchable in the page. Light and dark themes follow the system.
- The active input is now shown after you switch it.
- The app reconnects on its own when the speaker is powered off and on again. Previously the page kept saying "Connected".
- Calibration now fails with a clear message when the speaker does not respond (it ignores level changes while no audio is playing), instead of silently showing wrong numbers.
- Security: other websites can no longer send commands to the app, and in LAN mode other devices cannot factory reset the speaker or quit the app.
- Opening the app twice no longer starts a second copy, and a busy port is reported instead of failing silently.
- Quitting now disconnects from the speaker cleanly.
- The page opens in English by default; the language you pick is remembered by the app, even in another browser.
- A one-time reminder to calibrate appears on first use.
- Smaller app: media keys are sent through macOS directly, so `pyautogui` and Pillow are no longer bundled.

After updating, calibrate once from **Speaker setup** so the dial shows the right level.

## What to Download

Download the zipped Mac app from GitHub Releases:

```text
Logitech-Z407-Remote-Control-v0.3.0-macOS-arm64.zip
```

This build is for Apple Silicon Macs (M1 and later).

After extracting it, open:

```text
Logitech Z407 Remote Control.app
```

This is the easiest option for most Mac users. They do not need to clone the repository or run Terminal commands.

## First Launch

The app is not notarized, so macOS blocks the first launch. Open it once, then go to System Settings > Privacy & Security and click **Open Anyway**. On macOS 14 or earlier, right-click the app and choose Open instead.

The app may also ask for Bluetooth permission. Bluetooth permission is required because the app controls the Z407 over BLE.

Accessibility permission is only needed if you use the Mac Media Controls buttons. Those buttons send normal computer media keys such as play, pause, volume, and mute.

## Recommended Setup

1. Connect the Z407 to the Mac with a 3.5mm AUX cable.
2. Open the app.
3. Use the browser UI to switch input sources or control the speaker.

Based on local testing, AUX usually sounds better than Bluetooth. Bluetooth may distort at higher volume. USB audio has not been tested yet.

Bass control appears to have 15 adjustment steps based on local testing.

## How to Quit

Use the web UI's `Quit app` button, or the menu bar icon.

If running from Terminal, `Ctrl+C` is also safe.

If the web UI cannot find or reconnect to the Z407 after restarting the app, unplug the speaker power, wait a few seconds, and plug it back in. This can clear stale Bluetooth state on the speaker side.

Avoid `Ctrl+Z` in Terminal. It suspends the app instead of closing it. If you accidentally press it and see a suspended job, close that terminal job before starting the app again.
