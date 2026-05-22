# TurtleBot3 CCPP (Complete Coverage Path Planning) Web Monitor

本專案實作了 TurtleBot3 的**全覆蓋路徑規劃 (CCPP)** 演算法，並結合了**網頁即時監控介面**。使用者可以透過網頁一鍵啟動任務、監控地圖建置與路徑執行狀態。

---

## 🚀 核心功能

*   **全覆蓋路徑規劃 (CCPP)**：基於「牛耕式 (Boustrophedon)」分解演算法，確保機器人走遍地圖中所有可達區域。
*   **網頁監控介面**：即時顯示 SLAM 地圖、機器人位置、規劃路徑與任務狀態。
*   **一鍵啟動腳本**：自動處理 `Bringup`、`SLAM`、`Navigation` 與 `CCPP 核心` 的啟動順序與依賴。
*   **優雅關閉機制**：按下 `Ctrl+C` 時自動清理所有背景 ROS 程序。

---

## 🏗️ 系統架構

系統由多個 ROS 節點組成，並透過 `rosbridge` 與 Web 端通訊：

```text
[ 硬體驅動 ] <--> [ SLAM (Gmapping) ] <--> [ Navigation (move_base) ]
                                                    ^
                                                    |
[ 網頁介面 (JS) ] <--> [ Rosbridge (WS) ] <--> [ CCPP Manager (Python) ]
                                                    |
                                          [ 各種處理節點 (Planner/Executor...) ]
```

### 主要節點說明：
*   **ccpp_manager.py**: 任務大腦，負責狀態切換與節點協調。
*   **coverage_planner.py**: 負責生成全覆蓋的「掃描線」路徑。
*   **path_executor.py**: 接收路徑點並發送給 `move_base` 執行導航。
*   **web_server.py**: 提供 HTTP 靜態網頁服務 (Port 8000)。

---

## 📦 安裝需求

此專案開發於 **ROS Noetic** 環境下。

### 必要依賴：
```bash
sudo apt update
sudo apt install ros-noetic-rosbridge-server ros-noetic-web-video-server
```

### 編譯專案：
將此儲存庫放到您的 `catkin_ws/src/` 下：
```bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

---

## 🛠️ 如何使用

### 1. 快速啟動 (推薦)
我們提供了一個整合腳本，會自動啟動所有必要的節點：
```bash
chmod +x start_project.sh
./start_project.sh
```
啟動順序：`roscore` -> `Bringup` -> `SLAM` -> `Navigation` -> `CCPP Web Monitor`。

### 2. 訪問網頁介面
啟動成功後，開啟瀏覽器並輸入：
`http://<您的機器人IP>:8000`

在網頁上您可以看到：
*   **Real-time Map**: 即時 SLAM 地圖與機器人路徑。
*   **Task Control**: 開始/停止覆蓋任務。
*   **System Logs**: 顯示目前的任務進度與狀態。

### 3. 結束任務
在終端機按下 `Ctrl + C`，腳本會自動清理所有背景程序。

---

## ⚙️ 關鍵參數設定

您可以透過修改 `launch/ccpp_web_monitor.launch` 來調整演算法表現：

*   `robot_width`: 機器人的有效覆蓋寬度 (預設 0.16m)。
*   `scan_overlap`: 掃描線重疊率 (預設 0.85)，值越高覆蓋越細緻但耗時越長。

---

## 📝 開發規範

為了保持程式碼品質與團隊協作，請參考以下文件：
*   [**GIT_CONVENTION.md**](./GIT_CONVENTION.md): 包含分支命名、Commit Message 格式與版本號規則。
*   [**TUTORIAL.md**](./TUTORIAL.md): 包含 GitHub 上傳流程與腳本運作細節。

---

## 📁 資料夾結構

```text
turtlebot3_ccpp_local/
├── launch/             # ROS 啟動檔 (ccpp_web_monitor.launch)
├── scripts/            # Python 核心邏輯節點
├── srv/                # 自定義 ROS Service 定義
├── web_interface/      # 網頁前端原始碼 (HTML/CSS/JS)
├── start_project.sh    # 一鍵啟動腳本
└── README.md           # 本說明文件
```

---

## 📄 授權
本專案採用 **MIT License**。
