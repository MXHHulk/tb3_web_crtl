cmake_minimum_required(VERSION 3.0.2)
project(turtlebot3_ccpp)

find_package(catkin REQUIRED COMPONENTS
  rospy
  nav_msgs
  geometry_msgs
  visualization_msgs
  actionlib
  move_base_msgs
  std_srvs
  std_msgs
  message_generation
)

add_service_files(
  FILES
  GetTaskStatus.srv
)

generate_messages(
  DEPENDENCIES
  std_msgs
  geometry_msgs
)

catkin_package(
  CATKIN_DEPENDS 
  rospy 
  nav_msgs 
  geometry_msgs 
  visualization_msgs 
  actionlib 
  move_base_msgs 
  std_srvs 
  std_msgs 
  message_runtime
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)

catkin_install_python(PROGRAMS
  scripts/ccpp_manager.py
  scripts/map_processor.py
  scripts/path_planner.py
  scripts/region_detector.py
  scripts/coverage_planner.py
  scripts/path_executor.py
  scripts/info_logger.py
  scripts/web_server.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
