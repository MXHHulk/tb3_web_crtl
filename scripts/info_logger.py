#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：info_logger.py (系統狀態提示器)
檔案類型：資訊輸出輔助節點

核心功能：
1. 在工作站控制台顯示顯眼的提示訊息，告知使用者系統已啟動。
2. 指導使用者如何連結至網頁控制介面。
3. 確保所有必要的背景服務 (如 rosbridge) 均被提醒。

使用場景：
  此節點在 ccpp_web_monitor.launch 啟動後自動執行，
  在 ROS 控制台輸出一段操作指南，讓使用者知道下一步要怎麼做。

關鍵依賴：
- rospy: ROS 核心通訊庫
"""

import rospy

if __name__ == '__main__':
    # 初始化名為 info_logger 的 ROS 節點
    rospy.init_node('info_logger')

    # 輸出系統啟動提示橫幅
    # 使用多行 loginfo 讓訊息在控制台清晰可見
    rospy.loginfo("========================================")
    rospy.loginfo("TurtleBot3 CCPP 監控系統現已上線！")
    rospy.loginfo("請在瀏覽器中開啟 web_interface/index.html 以查看地圖。")
    rospy.loginfo("同時請確保 rosbridge_server 已在背景運行以連接 JS。")
    rospy.loginfo("========================================")

    # rospy.spin() 讓節點進入 ROS 事件迴圈並保持存活
    # 若不呼叫此函數，節點會在印完訊息後立刻結束
    rospy.spin()
