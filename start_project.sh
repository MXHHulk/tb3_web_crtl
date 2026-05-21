#!/bin/bash
# -*- coding: utf-8 -*-

# 檔案名稱：start_project.sh (專案啟動自動化腳本)
# 檔案類型：Shell Script / 部署腳本
#
# 核心功能：
# 1. 自動化啟動 TurtleBot3 CCPP 任務所需的所有 ROS 節點。
# 2. 管理程序生命週期：包含 ROS Master、Bringup、SLAM、Navigation 與 Web UI。
# 3. 實作優雅關閉 (Graceful Shutdown) 機制，確保 Ctrl+C 時能清理背景程序。
#
# 啟動順序 (有依賴關係，不可亂序)：
#   roscore → bringup → slam → navigation → ccpp_web_monitor
#
# 使用方式：
#   chmod +x start_project.sh   (首次使用前賦予執行權限)
#   ./start_project.sh
#
# 關鍵指令：
# - roslaunch: 啟動 ROS 複合配置。
# - roscore:   啟動 ROS 核心通訊。
# - pkill:     清理殘留程序。
# - rosparam:  設定 ROS 參數服務器的參數值。

# 設定 TurtleBot3 模型為 burger (可根據硬體更改為 waffle/waffle_pi)
# 此環境變數會被所有子程序繼承，影響 launch 檔的 URDF 模型選擇
export TURTLEBOT3_MODEL=burger

echo "======================================"
echo "啟動 TurtleBot3 CCPP 專案 (Burger)"
echo "======================================"

# ============================================================================
# 優雅關閉函數 (Graceful Shutdown)
# 當使用者按下 Ctrl+C (SIGINT) 時觸發此函數
# ============================================================================
cleanup() {
    echo ""
    echo "======================================"
    echo "接收到中斷訊號，正在關閉所有 ROS 節點..."
    echo "======================================"
    # `kill 0` 向當前 process group 中的所有程序發送 SIGTERM 信號
    # 這確保所有由此腳本以 & 啟動的背景子程序都能被一起終止
    # 不使用 kill <PID> 是因為背景程序可能又各自 fork 出子程序
    kill 0
    exit 0
}

# 捕捉 SIGINT 信號 (Ctrl+C) 並執行 cleanup 函數
# trap <函數名稱> <信號名稱>
trap cleanup SIGINT

# ============================================================================
# 系統重置：清除舊程序
# 確保重新啟動時不會因為殘留程序佔用通訊埠或衝突而失敗
# `|| true` 表示即使 pkill 找不到對應程序 (返回 1)，也不讓腳本因 set -e 而中止
# ============================================================================
echo "正在清理舊的 ROS 程序以進行重新啟動..."
pkill -f ros      || true  # 清理所有包含 "ros" 的程序 (roscore, roslaunch 等)
pkill -f ccpp     || true  # 清理殘留的 ccpp_manager 程序
pkill -f move_base || true  # 清理殘留的 move_base 程序
pkill -f gmapping  || true  # 清理殘留的 gmapping 程序
sleep 2  # 等待 OS 完成程序清理，釋放佔用的通訊埠

# ============================================================================
# [0/4] 啟動 ROS Master (roscore)
# 這是整個 ROS 系統的核心，提供：
# - Parameter Server (參數服務器)
# - rosout 日誌聚合節點
# - Master API (節點間的連線協調)
# 所有 ROS 節點都必須在 roscore 啟動後才能初始化
# ============================================================================
echo "[0/4] 正在啟動 ROS Master (roscore)..."
roscore &
# 等待 5 秒讓 roscore 完全初始化，確保後續節點能成功連線到 Master
sleep 5

# ============================================================================
# 設定導航相關 ROS 參數
# 在 move_base 啟動之前設定，確保節點初始化時能讀取到這些值
# DWA (Dynamic Window Approach) Local Planner 的速度限制參數
# ============================================================================
echo "正在注入速度限制參數以優化 SLAM 品質..."
# max_vel_x：最大前進線速度 (m/s)，降低至 0.15 使 SLAM 有足夠時間建圖
rosparam set /move_base/DWALocalPlannerROS/max_vel_x 0.15
# min_vel_x：最小前進線速度，0.0 允許機器人原地靜止
rosparam set /move_base/DWALocalPlannerROS/min_vel_x 0.0
# max/min_vel_theta：最大/最小角速度 (rad/s)，控制轉彎速度
rosparam set /move_base/DWALocalPlannerROS/max_vel_theta 1.2
rosparam set /move_base/DWALocalPlannerROS/min_vel_theta -1.2

# ============================================================================
# [1/4] 啟動 Bringup (硬體驅動層)
# 負責與實體 TB3 機器人的微控制器 (OpenCR) 通訊：
# - 讀取 IMU、編碼器數據
# - 發布 /odom (里程計) 與 TF (base_link → odom)
# - 接收 /cmd_vel 並驅動馬達
# - 橋接 LiDAR 感測器數據
# --wait：等待所有 launch 檔中的節點都成功啟動後才返回
# ============================================================================
echo "[1/4] 正在啟動 Bringup (turtlebot3_robot.launch)..."
roslaunch --wait turtlebot3_bringup turtlebot3_robot.launch &
sleep 3  # 等待硬體通訊建立穩定

# ============================================================================
# [2/4] 啟動 SLAM (同時定位與建圖)
# 使用 gmapping 演算法，結合 LiDAR 掃描與里程計數據建立佔據網格地圖：
# - 訂閱 /scan (LiDAR) 和 /odom (里程計)
# - 發布 /map (nav_msgs/OccupancyGrid)
# - 提供 map → odom 的 TF 座標變換
# slam_methods:=gmapping：指定使用 GMapping 粒子濾波 SLAM 演算法
# open_rviz:=false：不開啟 RViz 視覺化，節省計算資源 (使用我們自己的網頁介面)
# ============================================================================
echo "[2/4] 正在啟動 SLAM Gmapping (turtlebot3_slam.launch)..."
roslaunch --wait turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping open_rviz:=false &
sleep 3  # 等待 SLAM 初始化並接收第一幀 LiDAR 資料

# ============================================================================
# [3/4] 啟動 Navigation Stack (路徑規劃層)
# 提供 move_base 動作伺服器，讓機器人具備自主導航能力：
# - Global Planner：基於完整地圖規劃最優路徑 (A* 演算法)
# - Local Planner：即時閃避動態障礙物 (DWA 演算法)
# - 代價地圖 (Costmap)：整合地圖與感測器數據建立可行走區域
# open_rviz:=false：同樣不開啟 RViz
# ============================================================================
echo "[3/4] 正在啟動 Navigation (move_base.launch)..."
roslaunch --wait turtlebot3_navigation move_base.launch open_rviz:=false &
sleep 3  # 等待 move_base 與 costmap 初始化完成

# ============================================================================
# [4/4] 啟動 CCPP Web Monitor (專案核心邏輯與網頁介面)
# 此 launch 檔啟動三個子節點 (詳見 ccpp_web_monitor.launch)：
# - rosbridge_server (port 9090)：WebSocket 橋樑
# - web_server.py   (port 8000)：HTTP 靜態檔案伺服器
# - ccpp_manager.py            ：全覆蓋路徑規劃大腦
# ============================================================================
echo "[4/4] 正在啟動 CCPP Web Monitor (ccpp_web_monitor.launch)..."
roslaunch --wait turtlebot3_ccpp ccpp_web_monitor.launch &

echo "======================================"
echo "所有節點已在背景啟動完成！"
echo "請保持此終端機開啟。"
echo "若要結束所有程序，請按 Ctrl+C。"
echo "======================================"

# `wait` 讓此腳本阻塞並持續存活，直到使用者按下 Ctrl+C 觸發 cleanup
# 若不加 wait，腳本執行完就結束，但 trap cleanup SIGINT 仍會保持有效
wait
