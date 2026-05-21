# TurtleBot3 CCPP 專案整合與 GitHub 上傳教學

這份教學報告將引導您完成兩個主要目標：
1. 將本地的 `turtlebot3_ccpp` 專案上傳至 GitHub 進行版本控制。
2. 整合多個啟動指令，讓您能「一鍵啟動」整個專案，不再需要手動開啟多個終端機。

---

## 第一部分：將專案上傳至 GitHub

將程式碼推送到 GitHub 是一個好習慣，可以保護您的程式碼並方便在不同裝置（例如您的電腦與樹莓派之間）同步。

### 步驟 1：建立 GitHub 儲存庫 (Repository)
1. 登入您的 [GitHub 帳號](https://github.com/)。
2. 點擊右上角的 `+` 號，選擇 **New repository**。
3. 填寫儲存庫名稱（例如：`turtlebot3_ccpp`）。
4. 設定為 **Public** (公開) 或 **Private** (私有)。
5. **重要：請勿勾選 "Add a README file"、".gitignore" 或 "license"**（因為我們本地已經有這些檔案，直接推送才不會產生衝突）。
6. 點擊底部的 **Create repository**。

### 步驟 2：在本地終端機推送專案
請在您的專案根目錄（也就是包含 `package.xml` 和 `CMakeLists.txt` 的這個資料夾）中開啟終端機，然後依序輸入以下指令：

```bash
# 1. 將所有變更加入 Git 暫存區
git add .   

# 2. 提交這些變更並加上註解
git commit -m "feat: 完成 TurtleBot3 CCPP Web Monitor 專案與整合腳本"

# 3. 將當前分支名稱設為 main
git branch -M main

# 4. 將本地專案連結到 GitHub (請將下面的 URL 換成您的 GitHub 儲存庫網址)
git remote add origin https://github.com/您的帳號/turtlebot3_ccpp.git

# 5. 將程式碼推送到 GitHub 上
git push -u origin main
```
*註：如果這是您第一次使用 Git，可能會需要先設定您的信箱與名稱 (`git config --global user.email "you@example.com"`, `git config --global user.name "Your Name"`)。*

---

## 第二部分：指令整合 (一鍵啟動腳本)

原本您需要開啟四個不同的終端機，並且在啟動前手動輸入 `export TURTLEBOT3_MODEL=burger`。為了簡化流程，我已經在專案根目錄下為您建立了一個名為 **`start_project.sh`** 的 bash 腳本。

### `start_project.sh` 的運作原理
此腳本採用了 **背景執行 (Background Execution)** 的方式來管理多個 ROS Launch 檔案：
1. 自動設定 `export TURTLEBOT3_MODEL=burger` 環境變數。
2. 使用 `&` 符號將 `bringup`, `slam`, `navigation`, `ccpp` 等 launch 檔案放到背景並行執行。
3. 在每個指令之間加上 `sleep` 延遲，確保前一個節點 (例如 bringup) 已經就緒，再啟動下一個。
4. 設定了 `trap` 監聽器，當您在終端機按下 `Ctrl+C` 時，它會自動發送 `kill` 訊號關閉所有背景啟動的 ROS 程序，不會留下佔用資源的僵屍程序 (Zombie processes)。

### 如何使用這個腳本

1. **賦予執行權限 (只需執行一次)**
   在終端機中，賦予該腳本可執行權限：
   ```bash
   chmod +x start_project.sh
   ```

2. **啟動專案**
   以後每次要跑專案，只需要開**一個**終端機並執行：
   ```bash
   ./start_project.sh
   ```
   您會看到系統依序印出啟動日誌，並提示所有節點已啟動。

3. **結束專案**
   在跑著腳本的該終端機視窗，直接按下鍵盤的 `Ctrl+C`，腳本就會自動將四個 roslaunch 程序一併安全關閉。

---
有了這個整合腳本和 GitHub 儲存庫，您的開發與測試流程將會變得更乾淨、更有效率！
