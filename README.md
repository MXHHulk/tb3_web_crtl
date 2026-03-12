# TurtleBot3 Web Controller (SLAM & Navigation)

這是一個基於 **ROS Noetic** 與 **Flask** 開發的 TurtleBot3 網頁控制台。透過此系統，使用者可以遠端透過瀏覽器對機器人進行手動遙控（Teleop）、啟動 SLAM 建圖、執行自動探索，並即時下載掃描完成的地圖。

## 🚀 核心功能

* **即時監控**：透過 `ros2djs` 在網頁上即時渲染 SLAM 地圖。
* **矩陣遙控**：直覺的 WASD 3x3 矩陣按鈕控制，支援手機觸控與電腦點擊。
* **一鍵建圖**：遠端啟動 `gmapping` SLAM 演算法，並優化地圖更新頻率以降低網路延遲。
* **自動探索**：整合 `explore_lite` 與 `move_base` 實現自主導航建圖。
* **地圖持久化**：支援一鍵將內存地圖存檔並下載至本地電腦 (`.pgm` & `.yaml`)。
* **系統重置**：具備環境清理機制，可快速重置機器人狀態以進行下一次任務。

## 🛠️ 技術棧 (Tech Stack)

* **Robot OS**: ROS Noetic
* **Backend**: Python 3, Flask
* **Frontend**: HTML5, CSS3, JavaScript
* **ROS Libraries**: roslibjs, ros2djs, easeljs
* **Deployment**: Systemd Service (自動開機啟動)

## 📂 專案結構

```text
tb3_web_crtl/
├── app.py              # Flask 後端，負責處理 ROS 節點生命週期
├── templates/
│   └── index.html      # 網頁控制中心主介面
├── static/
│   ├── js/             # 包含 roslib.min.js 等通訊庫
│   └── current_map.pgm # (自動產生) 儲存的地圖檔案
├── startup_tb3_web.sh  # 一鍵啟動腳本 (包含環境變數配置)
└── README.md
```

## 🔧 安裝與部署

**1. 複製專案**

```text
cd ~/catkin_ws/src
git clone [https://github.com/MXHHulk/tb3_web_crtl.git](https://github.com/MXHHulk/tb3_web_crtl.git)
cd tb3_web_crtl
```

**2. 環境需求** 

```text
# 確保你的 TB3 已經安裝以下套件：
sudo apt-get install ros-noetic-rosbridge-server ros-noetic-tf2-web-republisher ros-noetic-explore-lite
pip3 install flask
```
**3. 設定自動啟動 (Systemd)**

```text
# 將專案內的腳本路徑設定至 /etc/systemd/system/tb3_web.service，並執行：
sudo systemctl daemon-reload
sudo systemctl enable tb3_web.service
sudo systemctl start tb3_web.service
```
```text
#  關閉自動
sudo systemctl disable tb3_web.service
sudo systemctl stop tb3_web.service
```
## 📖 使用指南

1. 開啟瀏覽器訪問 http://<YOUR_TB3_IP>:5000。
2. 點擊 啟動建圖，等待地圖出現在畫面上。
3. 使用 WASD 按鈕手動移動，或點擊 自動探索。
4. 任務完成後，點擊 下載地圖 保存成果。
5. 若需開始新任務，點擊 重置系統 清理環境。


