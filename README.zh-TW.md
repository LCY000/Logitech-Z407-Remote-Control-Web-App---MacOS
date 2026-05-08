# Logitech Z407 macOS 網頁控制器

**針對 macOS 優化的 Logitech Z407 網頁遙控器，改寫自原本的 Linux 網頁版專案。**

[English README](README.md)

這個 app 會在 Mac 上啟動本機網頁伺服器，並透過 Bluetooth Low Energy（BLE）控制 Logitech Z407。它可以切換 Z407 的 `AUX`、`USB`、`Bluetooth` 三種輸入。常見 Mac 使用情境是：**Mac 音訊走 3.5mm AUX 音源線，控制指令走 BLE**。

## 功能

- macOS-first 預設值：`127.0.0.1:8765`，避開 macOS AirPlay 常用的 `5000` port。
- 預設只允許本機控制。
- 可選 LAN 模式，讓同 Wi-Fi 的手機開網頁控制。
- 音響控制：靜音/取消靜音、音響本體音量、Bass、輸入來源、藍牙配對、恢復原廠設定。
- Mac 媒體鍵控制：播放/暫停、上一首、下一首、Mac 電腦音量、靜音。這是一般電腦控制，不是 Z407 喇叭本體音量。
- 現代化 responsive 網頁介面，支援桌面與手機瀏覽器。

## 建議 macOS 使用方式：AUX 音訊 + BLE 控制

1. 用 3.5mm AUX 音源線把 Mac 接到 Z407。
2. 把 Z407 輸入來源切到 `AUX`。
3. 在 Mac 上啟動這個 app。
4. 用網頁介面控制音響音量、Bass、輸入來源與 Mac 播放。

音訊會繼續走 AUX 線。BLE 只負責遙控指令。依目前本機實測，AUX 音質通常比 Bluetooth 好，Bluetooth 在音量較大時可能會爆音或破音；USB 音訊尚未實測。

網頁仍然可以切換 Z407 的 `AUX`、`USB`、`Bluetooth` 三種輸入；AUX 只是 Mac 接音源線時的建議設定。

## macOS 快速開始

```bash
chmod +x run_macos.sh
./run_macos.sh
```

開啟：

```text
http://127.0.0.1:8765
```

這個腳本會建立 Python virtual environment、安裝依賴、啟動 server，並開啟瀏覽器。

## 正確退出

請使用網頁上的 **Quit App** 按鈕，或在終端機按 `Ctrl+C`。

不要用 `Ctrl+Z`。`Ctrl+Z` 只是暫停程式，不是關閉程式，可能讓本機 server 或 Bluetooth 狀態殘留。如果不小心按到 `Ctrl+Z`，可以先執行 `jobs`，再用 `kill %1` 關掉被暫停的 job。

## 用手機在同 Wi-Fi 控制

執行：

```bash
./run_macos.sh --lan
```

`run_macos.sh` 會啟動 LAN 模式，Python app 會顯示類似這樣的 LAN URL：

```text
http://192.168.1.35:8765
```

手機連到同一個 Wi-Fi 後，用瀏覽器打開這個網址。

## macOS 權限

macOS 可能會要求：

- **Bluetooth 權限**：給 Terminal、Python 或封裝後的 app。
- **輔助使用 Accessibility 權限**：讓 app 可以模擬 Mac 媒體鍵，例如播放/暫停與電腦音量。

如果 Mac Media Controls 無效，請到系統設定的隱私權與安全性檢查權限。你也可以直接用 Mac 鍵盤、選單列或控制中心調整電腦播放與音量，不一定要透過網頁。

## 進階設定

```bash
./run_macos.sh --port 9090
./run_macos.sh --lan
./run_macos.sh --lan --port 9090
./run_macos.sh --preferred-input aux
./run_macos.sh --verbose
./run_macos.sh --debug-scan --duration 8
```

預設值：

- Host：`127.0.0.1`
- Port：`8765`
- 建議輸入來源：`aux`
- 終端機 log：預設安靜模式。需要 HTTP access log 和重複掃描訊息時可加 `--verbose`。

如果 app 找不到 Z407，可以用 `--debug-scan` 列出 macOS 目前掃得到的 BLE 裝置，並標記可能的 Z407 裝置。

## Linux 說明

Linux source-run 行為會盡量保留。Linux 的電腦媒體鍵需要 `xdotool`，Bluetooth 存取可能需要 BlueZ 權限或 capability 設定。

原本的 Linux installer scripts 會保留作為參考，但這個改寫版會以 macOS 使用體驗為優先。

## 從原始碼建置

需求：

- Python 3.12+
- `pip`
- `venv`

安裝並執行：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## GitHub Repo 名稱建議

如果你要把這個改寫版發成獨立 GitHub repository，建議名稱：

- `logitech-z407-macos-web-control`
- `z407-macos-remote-web`

## Credits & Acknowledgments

**原始 Web App：**
原始實作作者為 **Androrama**。

**macOS-first 改寫：**
目前 macOS-first adaptation 與維護者為 **LCY000**。

**Reverse Engineering：**
特別感謝 **freundTech** 的 reverse engineering 工作。
https://github.com/freundTech/logi-z407-reverse-engineering

**上游專案：**
這個版本改寫自 `Androrama/Logitech-Z407-Remote-Control-Web-App---Linux`。

## Disclaimer

這是 **非官方** 專案，與 Logitech 無關，未受 Logitech 背書或授權。
「Logitech」是其權利人的商標。本軟體以現狀提供，不附任何保證。

## Donations & Support

這個專案建立在免費的社群工作上。請保留並尊重原作者與 reverse engineering 的貢獻。

This project is 100% free。本專案完全免費。使用它、分享它，並保留原始 attribution，本身就已經是在幫助這個專案。

如果你想提供額外支持，任何捐款都能幫助原作者投入更多時間與資源，繼續維護這個專案與其他社群作品。也感謝所有已經支持過這個專案的人。

原作者支持頁面：
https://androrama.com
