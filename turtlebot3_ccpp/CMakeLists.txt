cmake_minimum_required(VERSION 3.0.2)
project(turtlebot3_ccpp)

find_package(catkin REQUIRED COMPONENTS rospy nav_msgs std_msgs)

catkin_package()

catkin_install_python(PROGRAMS
    scripts/coverage_planner.py
    scripts/map_server.py
    DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch/ DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch)
install(DIRECTORY web/    DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/web)
