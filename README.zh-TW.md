# Logitech Z407 Remote Control Web App for macOS

**針對 macOS 優化的 Logitech Z407 網頁遙控器。**

[English README](README.md)

如果你覺得原本的無線控制器不太好用、在桌上佔空間，或是已經弄丟了，這個app 就很適合你。以我自己的使用情境來說，平常喇叭都用 AUX 接著 Mac，實體控制撥盤大多都是收起來的，一般音量調整也直接在 Mac 上調整。真正麻煩的是偶爾想調 Bass 或切換輸入來源時，沒有把撥盤放在手邊就很不方便。這個 app 要解決的，就是這種「平常不需要撥盤，但偶爾又需要那些控制」的情況。  

這個 app 會在 Mac 上啟動本機網頁伺服器，模仿原廠無線控制器。app 會透過 Bluetooth Low Energy（BLE）控制 Logitech Z407。它針對常見的 Mac 使用情境優化：音訊走 3.5mm AUX 音源線，BLE 只負責遙控指令。  

## 功能

- macOS-first 預設值：`127.0.0.1:8765`，避開 AirPlay 常用的 `5000` port
- 預設只允許本機控制，也可選 LAN 模式讓同 Wi-Fi 的手機控制
- Z407 音響控制：靜音、音量、Bass、輸入切換、藍牙配對、恢復原廠設定
- Mac 媒體控制：播放/暫停、上一首、下一首、電腦音量、靜音
- 即時音量與 Bass 追蹤：每次 BLE 指令確認後同步更新步數計數器（音量共 32 級、Bass 共 15 級），網頁上顯示目前的數值；附「校正」按鈕，一鍵將兩者歸零，確保顯示正確
- 跨次啟動狀態保留：音量與 Bass 計數在重新啟動後仍保留，校正一次即可長期使用
- macOS 選單列圖示：關閉瀏覽器分頁後伺服器仍在背景持續運作，隨時可從選單列重新開啟網頁介面或退出
- BLE debug scan 模式，可檢查 macOS 當前掃到哪些 BLE 裝置
- 支援桌面與手機瀏覽器的 responsive 網頁介面

## 建議使用方式

1. 用 3.5mm AUX 音源線把 Z407 接到 Mac 上。
2. 在 Mac 上啟動這個 app。
3. 用網頁介面控制音響或切換輸入來源。

依目前本機實測，AUX 音質通常比 Bluetooth 好；Bluetooth 在音量較大時可能會爆音或破音；USB 音訊尚未實測。

## 快速開始

在 Terminal 執行：

```bash
chmod +x run_macos.sh
./run_macos.sh
```

或直接在 Finder 裡雙擊：

```text
Launch Logitech Z407 Web Control.command
```

然後開啟：

```text
http://127.0.0.1:8765
```

`run_macos.sh` 會在需要時建立本機 virtual environment、安裝執行所需套件、啟動 server，並開啟瀏覽器。

## Mac App 下載與使用

從 [GitHub Releases 頁面](../../releases) 下載最新版本，解壓縮後直接雙擊 `Logitech Z407 Remote Control.app`，不需要 Python 或 Terminal。

可以把 app 拖到「**應用程式**」資料夾，之後就能像一般 Mac app 一樣從那裡啟動。

第一次啟動時 macOS 會出現安全性提示，解決方式：

1. 在 app 上按右鍵（或 Control + 點一下）→ **打開**
2. 在跳出的對話框再點一次 **打開**

啟動後，選單列會出現圖示。點一下可重新開啟網頁介面或退出 app。

若要自己從原始碼打包：

```bash
./build_macos_app.sh
```

打包後的 app 會出現在：

```text
release/Logitech Z407 Remote Control.app
```

## 安全退出

請使用網頁上的 `Quit` 按鈕，或在終端機按 `Ctrl+C`。

如果之前關閉 server 後，下一次重開時網頁無法掃描或連接到 Z407，可以先試著把音響電源拔掉，等幾秒後再重新接上。這通常可以清掉音響端卡住的 Bluetooth 狀態。

在 Terminal 裡請避免使用 `Ctrl+Z`。`Ctrl+Z` 是暫停程式，不是關閉程式。如果不小心按到並看到 suspended job，重新啟動 app 前要先把那個 terminal job 關掉。

## 手機控制

如果要讓同一個 Wi-Fi 下的手機控制：

```bash
./run_macos.sh --lan
```

程式會顯示類似這樣的區網網址：

```text
http://192.168.1.35:8765
```

手機連上同一個 Wi-Fi 後，用瀏覽器打開這個網址即可。

## macOS 權限

macOS 可能會要求：

- **Bluetooth 權限**：給 Terminal、Python 或封裝後的 app
- **輔助使用 Accessibility 權限**：在你使用 Mac Media Controls 按鈕時才可能需要

如果 Mac Media Controls 沒有作用，請到 **系統設定 > 隱私權與安全性** 檢查權限。

## 進階用法

範例：

```bash
./run_macos.sh --port 9090
./run_macos.sh --lan --port 9090
./run_macos.sh --preferred-input aux
./run_macos.sh --verbose
./run_macos.sh --debug-scan --duration 8
```

預設值：

- Host：`127.0.0.1`
- Port：`8765`
- 建議輸入來源：`aux`
- Log：預設安靜模式

如果偵測不到 Z407，可以執行：

```bash
./run_macos.sh --debug-scan --duration 10 --rounds 3 --pause 3
```

這會列出 macOS 當前看得到的 BLE 裝置，並標記可能的 Z407 候選裝置。

## 從原始碼執行

執行時需求：

- Python 3.12+
- `pip`
- `venv`

從原始碼執行：

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

開發工具：

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

## Credits & Acknowledgments

**macOS 版本：**
macOS 改寫、目前維護，以及這個 macOS-first 版本由 **LCY000** 完成。這個版本是從原本的 Linux Web App 開發成針對 macOS 使用的版本。

**原始 Linux Web App：**
原始實作作者為 **Androrama**。

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

本專案完全免費。使用它、分享它，並保留原始 attribution，本身就已經是在幫助這個專案。

如果你想提供額外支持，任何捐款都能幫助原作者投入更多時間與資源，繼續維護這個專案與其他社群作品。也感謝所有已經支持過這個專案的人。

原作者支持頁面：
https://androrama.com
