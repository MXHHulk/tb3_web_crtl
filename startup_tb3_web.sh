#!/bin/bash

# 1. 讓系統冷靜一下，等待網路完全分配 IP
sleep 15

# 2. 加載 ROS 與專案環境
source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash

# 3. 自動抓取當前 IPv4 (解決開機抓不到地圖的核心)
export TURTLEBOT3_MODEL=burger
export ROS_IP=$(hostname -I | awk '{print $1}')
export ROS_MASTER_URI=http://$ROS_IP:11311

# 4. 清理舊 Log，騰出空間給地圖
rosclean purge -y

# 5. 啟動 Flask 後端
# 注意：這裡使用絕對路徑執行 app.py，確保在 Service 模式下不會迷路
cd /home/ubuntu/catkin_ws/src/tb3_web_crtl
/usr/bin/python3 app.py
