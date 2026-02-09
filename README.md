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


## 🔧 安裝與部署 (Installation & Deployment)

本專案建議部署於運行 Ubuntu 20.04 (ROS Noetic) 的 Raspberry Pi 4。

### 1. 複製專案與權限設定
首先將專案複製到你的 catkin 工作空間，並確保啟動腳本具備執行權限：
```bash
cd ~/catkin_ws/src
git clone [https://github.com/MXHHulk/tb3_web_crtl.git](https://github.com/MXHHulk/tb3_web_crtl.git)
cd tb3_web_crtl
chmod +x startup_tb3_web.sh

# 安裝通訊橋樑與座標轉發器
sudo apt-get update
sudo apt-get install -y ros-noetic-rosbridge-server \
                       ros-noetic-tf2-web-republisher \
                       ros-noetic-map-server \
                       ros-noetic-explore-lite

# 安裝 Flask 後端伺服器
pip3 install flask


