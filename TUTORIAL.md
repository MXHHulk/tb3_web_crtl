# TurtleBot3 CCPP 專案下載與使用教學

本教學將引導您如何從 GitHub 下載本專案程式碼，並在您的 ROS Noetic 環境中完成編譯與執行。

---

## 步驟一：環境準備

本專案基於 **ROS Noetic** 與 **Ubuntu 20.04** 開發，請確保您的系統已安裝 ROS。

此外，專案的網頁監控介面依賴以下 ROS 套件，請開啟終端機並執行安裝指令：

```bash
sudo apt update
sudo apt install ros-noetic-rosbridge-server ros-noetic-web-video-server
```

## 步驟二：下載專案程式碼

請將本專案下載至您的 ROS 工作區 (Workspace) 中的 `src` 目錄下。假設您的工作區名稱為 `catkin_ws`：

```bash
# 1. 進入工作區的 src 目錄
cd ~/catkin_ws/src

# 2. 複製專案程式碼 (若您已將專案上傳，請替換為您實際的 GitHub 網址)
git clone https://github.com/您的帳號/turtlebot3_ccpp.git
```

## 步驟三：編譯專案

下載完成後，回到工作區根目錄進行編譯：

```bash
# 1. 回到工作區根目錄
cd ~/catkin_ws

# 2. 進行編譯
catkin_make

# 3. 載入環境變數 (建議將此指令加入 ~/.bashrc)
source devel/setup.bash
```

## 步驟四：一鍵啟動專案

為了簡化啟動流程，專案內附帶了一個自動化腳本 `start_project.sh`。

```bash
# 1. 進入專案目錄
cd ~/catkin_ws/src/turtlebot3_ccpp

# 2. 賦予腳本執行權限 (只需設定一次)
chmod +x start_project.sh

# 3. 執行腳本
./start_project.sh
```

此腳本會在背景依序啟動 `roscore`、TurtleBot3 硬體模型 (Bringup)、SLAM 建圖、導航系統 (Navigation) 以及本專案的 CCPP 核心邏輯與網頁伺服器。

## 步驟五：開啟網頁監控介面

待終端機提示所有節點啟動完成後，開啟您的網頁瀏覽器 (推薦使用 Chrome 等現代瀏覽器)，並輸入以下網址：

```text
http://localhost:8000
```
*(註：若您是在另一台電腦上監控，請將 localhost 替換為執行 ROS 該台主機的 IP 位址)*

在網頁介面中，您可以：
1. 點擊介面上的按鈕開始覆蓋任務。
2. 即時觀看機器人建圖狀態、位置與生成的牛耕式覆蓋路徑。

## 步驟六：安全結束專案

若要結束執行，請回到剛剛執行腳本的終端機視窗，直接按下鍵盤的 `Ctrl + C`。腳本會捕捉此中斷訊號，並自動、安全地關閉所有背景運行的 ROS 節點與程序。
