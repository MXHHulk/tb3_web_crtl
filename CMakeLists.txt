# CMakeLists.txt

cmake_minimum_required(VERSION 3.0.2)
project(turtlebot3_ccpp)

find_package(catkin REQUIRED COMPONENTS
    rospy
    nav_msgs
    std_msgs
)

catkin_package(
    CATKIN_DEPENDS rospy nav_msgs std_msgs
)

include_directories(${catkin_INCLUDE_DIRS})

# 安裝 Python 腳本並賦予執行權限
catkin_install_python(PROGRAMS
    scripts/flask_map_server.py
    DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# 安裝 launch 檔與 web 資源
install(DIRECTORY launch/   DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch)
install(DIRECTORY web_interface/
        DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/web_interface)
