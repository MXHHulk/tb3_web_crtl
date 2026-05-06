#!/bin/bash

# 設定 TurtleBot3 模型為 burger
export TURTLEBOT3_MODEL=burger

echo "======================================"
echo "啟動 TurtleBot3 CCPP 專案 (Burger)"
echo "======================================"

# 定義清理函數，當按下 Ctrl+C 時關閉所有背景程序
cleanup() {
    echo ""
    echo "======================================"
    echo "接收到中斷訊號，正在關閉所有 ROS 節點..."
    echo "======================================"
    # 關閉同一個 process group 的所有背景程序
    kill 0
    exit 0
}

# 捕捉 SIGINT (Ctrl+C)
trap cleanup SIGINT

# 0. 啟動 ROS Master (roscore)
echo "[0/4] 正在啟動 ROS Master (roscore)..."
roscore &
# 等待 roscore 完全啟動
sleep 5

# 1. 啟動 bringup
echo "[1/4] 正在啟動 Bringup (turtlebot3_robot.launch)..."
roslaunch --wait turtlebot3_bringup turtlebot3_robot.launch &
sleep 3

# 2. 啟動 SLAM (gmapping)
echo "[2/4] 正在啟動 SLAM Gmapping (turtlebot3_slam.launch)..."
roslaunch --wait turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping open_rviz:=false &
sleep 3

# 3. 啟動 Navigation (move_base)
echo "[3/4] 正在啟動 Navigation (move_base.launch)..."
roslaunch --wait turtlebot3_navigation move_base.launch open_rviz:=false &
sleep 3

# 4. 啟動 CCPP Web Monitor
echo "[4/4] 正在啟動 CCPP Web Monitor (ccpp_web_monitor.launch)..."
roslaunch --wait turtlebot3_ccpp ccpp_web_monitor.launch &

echo "======================================"
echo "所有節點已在背景啟動完成！"
echo "請保持此終端機開啟。"
echo "若要結束所有程序，請按 Ctrl+C。"
echo "======================================"

# 等待所有背景程序
wait
