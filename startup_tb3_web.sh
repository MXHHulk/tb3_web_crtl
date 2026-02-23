#!/bin/bash

# 1. 網路偵測
IP_ADDR=""
while [ -z "$IP_ADDR" ]; do
    IP_ADDR=$(hostname -I | awk '{print $1}')
    [ -z "$IP_ADDR" ] && sleep 1
done

# 2. 載入環境變數
source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-01
export ROS_IP=$IP_ADDR
export ROS_MASTER_URI=http://$ROS_IP:11311

# 3. 啟動 ROS Master
roscore &
sleep 5

# 4. 啟動底層驅動
roslaunch turtlebot3_bringup turtlebot3_robot.launch &
sleep 15 

# 5. 【核心修正】啟動 SLAM 但關閉 RViz 界面
# 加上 open_rviz:=false 避免因為找不到螢幕而崩潰
roslaunch turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping open_rviz:=false &
sleep 5

# 6. 啟動網頁橋樑
roslaunch rosbridge_server rosbridge_websocket.launch &
sleep 2

# 7. 啟動 Flask
cd /home/ubuntu/catkin_ws/src/tb3_web_crtl
/usr/bin/python3 app.py
