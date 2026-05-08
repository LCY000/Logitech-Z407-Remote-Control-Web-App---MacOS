# Release Notes for Mac Users

## What to Download

Download the zipped Mac app from GitHub Releases:

```text
Logitech-Z407-Remote-Control-Web-App-MacOS.zip
```

After extracting it, open:

```text
Logitech Z407 Remote Control.app
```

This is the easiest option for most Mac users. They do not need to clone the repository or run Terminal commands.

## First Launch

macOS may warn that the app was downloaded from the internet. If that happens, use right-click > Open for the first launch.

The app may also ask for Bluetooth permission. Bluetooth permission is required because the app controls the Z407 over BLE.

Accessibility permission is only needed if you use the Mac Media Controls buttons. Those buttons send normal computer media keys such as play, pause, volume, and mute.

## Recommended Setup

1. Connect the Z407 to the Mac with a 3.5mm AUX cable.
2. Open the app.
3. Use the browser UI to switch input sources or control the speaker.

Based on local testing, AUX usually sounds better than Bluetooth. Bluetooth may distort at higher volume. USB audio has not been tested yet.

Bass control appears to have 15 adjustment steps based on local testing.

## How to Quit

Use the web UI's `Quit` button.

If running from Terminal, `Ctrl+C` is also safe.

If the web UI cannot find or reconnect to the Z407 after restarting the app, unplug the speaker power, wait a few seconds, and plug it back in. This can clear stale Bluetooth state on the speaker side.

Avoid `Ctrl+Z` in Terminal. It suspends the app instead of closing it. If you accidentally press it and see a suspended job, close that terminal job before starting the app again.
