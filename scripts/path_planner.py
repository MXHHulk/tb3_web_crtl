#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：path_planner.py (輔助路徑規劃模組)
檔案類型：演算法邏輯類 / 座標變換工具

核心功能：
1. 提供簡易的 Zig-zag (Boustrophedon) 路徑生成演算法。
2. 封裝像素座標與 ROS 地圖物理座標之間的雙向轉換邏輯。
3. 支援多邊形內部區域判定，確保路徑不超出邊界。

關鍵依賴：
- actionlib: 用於發送導航動作
- move_base_msgs: 導航訊息格式
- cv2: 用於多邊形區域測試
- numpy: 矩陣運算
"""

import rospy
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import actionlib
import numpy as np
import cv2

def generate_zigzag_path(poly_pts, resolution, step_size=0.3):
    """
    簡易 Z 字型路徑生成。
    poly_pts: 多邊形頂點 (像素單位)
    resolution: 地圖解析度 (公尺/像素)
    step_size: 掃描線間距 (公尺)
    """
    # 1. 獲取多邊形的外接矩形邊界
    pts = poly_pts.reshape(-1, 2)
    min_x, min_y = np.min(pts, axis=0)
    max_x, max_y = np.max(pts, axis=0)
    
    path = []
    # 將公尺間距轉換為像素間距
    pixel_step = int(step_size / resolution)
    if pixel_step < 1: pixel_step = 1
    
    reverse = False # 控制折返方向
    # 沿著外接矩形的 Y 軸方向進行掃描
    for y in range(int(min_y), int(max_y), pixel_step):
        line_pts = []
        # 遍歷 X 軸尋找在多邊形內部的點
        for x in range(int(min_x), int(max_x)):
            # 使用 OpenCV 函數檢查像素 (x, y) 是否在多邊形內
            if is_inside(poly_pts, (x, y)):
                line_pts.append((x, y))
        
        # 如果該行有交點，則提取端點
        if line_pts:
            if reverse:
                line_pts.reverse()
            # 只提取每條掃描線的起點與終點，由 move_base 處理直線路徑
            path.extend([line_pts[0], line_pts[-1]]) 
            reverse = not reverse
            
    return path

def is_inside(poly, pt):
    """
    檢查點是否在多邊形內。
    poly: OpenCV 格式輪廓
    pt: (x, y) 座標元組
    """
    # pointPolygonTest 返回值 >= 0 表示點在多邊形內部或邊界上
    return cv2.pointPolygonTest(poly, (float(pt[0]), float(pt[1])), False) >= 0

class CCPPPlanner:
    """
    路徑規劃執行類別，封裝導航點的發送與座標轉換。
    """
    def __init__(self, map_metadata):
        """
        初始化規劃器。
        map_metadata: 包含 resolution, origin 等地圖元數據
        """
        self.res = map_metadata.resolution
        self.origin = map_metadata.origin.position
        self.height = map_metadata.height
        # 初始化 move_base 客戶端
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("正在等待 move_base 行動伺服器...")
        # 注意：實際使用時需呼叫 self.client.wait_for_server()

    def pixel_to_map(self, px, py):
        """
        將 OpenCV 像素座標轉換為 ROS 物理地圖座標。
        物理座標 = (像素座標 * 解析度) + 原點座標
        """
        map_x = px * self.res + self.origin.x
        # 注意：某些地圖框架中 Y 軸可能是反向的，此處依照標準 ROS 矩陣轉換
        map_y = (self.height - py) * self.res + self.origin.y
        return map_x, map_y

    def execute_path(self, path_points):
        """
        遍歷路徑點並逐一發送導航任務。
        path_points: 像素座標點集合
        """
        for pt in path_points:
            mx, my = self.pixel_to_map(pt[0], pt[1])
            rospy.loginfo("發送導航目標：(%.2f, %.2f)", mx, my)
            
            goal = MoveBaseGoal()
            goal.target_pose.header.frame_id = "map"
            goal.target_pose.header.stamp = rospy.Time.now()
            goal.target_pose.pose.position.x = mx
            goal.target_pose.pose.position.y = my
            # 預設目標朝向為正前方 (單位四元數)
            goal.target_pose.pose.orientation.w = 1.0
            
            # 發送並阻塞等待結果
            self.client.send_goal(goal)
            self.client.wait_for_result()
            
            # 檢查執行結果
            if self.client.get_state() != actionlib.GoalStatus.SUCCEEDED:
                rospy.logwarn("未能抵達目標點，跳轉至下一點...")
