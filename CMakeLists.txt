# 檔案名稱：CMakeLists.txt (專案編譯配置)
# 檔案類型：CMake / 建構描述檔
# 核心功能：定義專案依賴、自定義服務編譯以及 Python 節點安裝規則。

cmake_minimum_required(VERSION 3.0.2)
project(turtlebot3_ccpp)

# 尋找並載入必要的 ROS 組件
find_package(catkin REQUIRED COMPONENTS
  rospy
  nav_msgs
  geometry_msgs
  visualization_msgs
  actionlib
  move_base_msgs
  std_srvs
  std_msgs
  message_generation # 用於生成自定義服務訊息
)

# 定義自定義服務文件 (.srv)
add_service_files(
  FILES
  GetTaskStatus.srv
)

# 根據依賴生成訊息/服務的標頭檔與 Python 腳本
generate_messages(
  DEPENDENCIES
  std_msgs
  geometry_msgs
)

# 定義導出的編譯依賴
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
  message_runtime # 運行時訊息支援
)

# 包含標頭檔路徑
include_directories(
  ${catkin_INCLUDE_DIRS}
)

# 安裝 Python 腳本並確保其具備執行權限 (程式碼入口)
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
