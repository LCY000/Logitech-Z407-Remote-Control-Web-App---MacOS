# Logitech Z407 Remote Control Web App 🎵

**A modern, cross-platform web application to control your Logitech Z407 Bluetooth speakers from any device.**

![Status](https://img.shields.io/badge/Status-Active-success) ![Platform](https://img.shields.io/badge/Platform-Linux-blue) ![License](https://img.shields.io/badge/License-Free-green)

This application creates a local web server that connects to your Z407 speakers via Bluetooth Low Energy (BLE). It allows you to control the speakers and your PC's media playback directly from your smartphone, tablet, or another computer on the network.

---

## ✨ Features

**🎛️ Full Speaker Control:** Play/Pause, Volume Control (with visual feedback).

**💻 PC Media Interface:** Simulate multimedia keys on the host computer (Next/Prev Tack, Mute, System Volume) via the web interface.

**📱 Mobile First Design:** Responsive Material Design interface that works perfectly on iOS and Android.

**🐧 Linux Portable:** Ready-to-run application for **Linux**. No installation or setup required. (A Windows version is also available).

---

## 🚀 How to Use (Standalone)

### 🐧 Linux
1.  Download the **`Z407_Control_Linux`** executable (from the `dist` folder).
2.  Open a terminal and run the app:
    ```bash
    ./Z407_Control_Linux
    ```
3.  **Permissions Note:** Linux restricts Bluetooth access. To run without `sudo`, apply this permission once:
    ```bash
    sudo setcap 'cap_net_raw,cap_net_admin+eip' Z407_Control_Linux
    ```
4.  **Media Keys Note:** To control PC media (Spotify, YouTube, etc.), install `xdotool`:
    ```bash
    sudo apt install xdotool
    ```



---

---

## 🔧 Advanced Configuration (Manual IP/Port)

By default, the app listens on all interfaces `0.0.0.0` at port `5000`. You can override this using command line arguments if you need a specific setup (e.g., for Docker or specific network interfaces).

**Usage:**
```bash
# General Syntax
python app.py --ip <IP_ADDRESS> --port <PORT_NUMBER>

# Example: Listen only on localhost at port 8080
python app.py --ip 127.0.0.1 --port 8080

# Example: Listen on a specific LAN IP
python app.py --ip 192.168.1.50 --port 9090
```

---

## 📱 Connecting from Mobile

1.  Run the application on your PC provided above.
2.  The console will display your local IP address, e.g., `http://192.168.1.35:5000`.
3.  Open that URL in your phone's browser (Safari/Chrome).

### ⚠️ "Not Secure" Warning
Since this app runs locally on your network without an SSL certificate (HTTP instead of HTTPS), browsers might warn you that the connection is not secure. This is expected for local apps.

*   **Chrome / Brave / Edge:** Click **"Advanced"** or **"Details"** → **"Proceed to ... (unsafe)"**.
*   **Safari:** You might see "This Connection Is Not Private". Click **"Show Details"** → **"visit this website"**.
*   **Firefox:** Click **"Advanced"** → **"Accept the Risk and Continue"**.

---

## 🛠️ Build from Source

If you want to modify the code or build the executables yourself:

### Prerequisites
*   Python 3.12+
*   `pip` and `venv`

### Setup and Build
1.  Clone the repository.
2.  Run the build script for your OS:

**Linux:**
```bash
chmod +x build_linux.sh
./build_linux.sh
```
*This will create a virtual environment, install dependencies (`quart`, `bleak`, etc.), and compile the binary to `dist/`.*



---

## 🤝 Credits & Acknowledgments

**Reverse Engineering:**
Special thanks to **freundTech** for the reverse engineering work that made this possible.
🔗 [https://github.com/freundTech/logi-z407-reverse-engineering](https://github.com/freundTech/logi-z407-reverse-engineering)

**Author:**
Original Web App implementation by **Androrama**.

---

## ⚠️ Disclaimer

This is an **unofficial** project and is not affiliated with, endorsed by, or connected to Logitech in any way.
"Logitech" is a trademark of its respective owner. This software is provided "as is" without warranty of any kind.

---

## ❤️ Donations & Support

**This project is 100% free.**

Any donation (no matter how small) helps me dedicate more time and resources to this and other projects. Infinite thanks to those who have already collaborated! ❤️

→ [https://androrama.com](https://androrama.com)

And to those who haven't, thank you for using the project even if you don't donate, that already makes me very happy 😊
