#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：map_processor.py (地圖影像處理模組)
檔案類型：影像處理工具類 / OpenCV 實作

核心功能：
1. 預處理 SLAM 產生的 OccupancyGrid，移除噪點並對障礙物進行膨脹處理。
2. 偵測地圖中的「未知區域邊界 (Frontiers)」，用於實現自主探索。
3. 透過侵蝕運算生成安全邊距，防止路徑規劃過於靠近牆壁。

關鍵依賴：
- cv2 (OpenCV): 核心影像運算處理
- numpy: 用於處理地圖矩陣數據
"""

import cv2
import numpy as np

def preprocess_map(grid_data, width, height, kernel_size=5):
    """
    將 ROS 地圖數據轉換為 OpenCV 影像並進行形態學優化。
    grid_data: 原始 Occupancy Grid 數據 (-1, 0, 100)
    width, height: 地圖解析寬高
    """
    # 將數據重塑為 2D 矩陣 (由一維陣列轉換為 HxW 矩陣)
    raw_img = np.array(grid_data).reshape((height, width))
    
    # 初始化二值化影像 (255: 空地, 0: 障礙物或未知)
    binary_img = np.zeros((height, width), dtype=np.uint8)
    binary_img[raw_img == 0] = 255
    
    # 形態學「開運算」(先侵蝕後膨脹)：用於移除細小的噪點與毛邊
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    opened = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel)
    
    # 安全空間優化：對「空地」進行侵蝕 (Erosion)
    # 物理意義：這會讓地圖上的「白區 (空地)」縮小，相對讓「黑區 (障礙物)」變厚
    # 解決機器人太靠近牆壁導致 DWA Planner 回報路徑失敗的問題
    safety_margin_kernel = np.ones((3, 3), np.uint8)
    eroded = cv2.erode(opened, safety_margin_kernel, iterations=2)
    
    return eroded

def get_frontier_map(grid_data, width, height):
    """
    偵測地圖中的探索前沿點 (即空地與未知區域的交界處)。
    """
    # 將地圖數據重塑為矩陣
    raw_img = np.array(grid_data).reshape((height, width))
    
    # 建立空地遮罩 (Free space, ROS 地圖值為 0)
    free_mask = np.zeros((height, width), dtype=np.uint8)
    free_mask[raw_img == 0] = 255
    
    # 建立未知遮罩 (Unknown space, ROS 地圖值為 -1)
    unknown_mask = np.zeros((height, width), dtype=np.uint8)
    unknown_mask[raw_img == -1] = 255
    
    # 膨脹空地區域，尋找其與未知區域的鄰接點
    dilated_free = cv2.dilate(free_mask, np.ones((3,3), np.uint8))
    # 取交集：既是擴展後的空地又是原本的未知區域，這就是機器人可以去探索的「邊緣」
    frontiers = cv2.bitwise_and(dilated_free, unknown_mask)
    
    # 使用開運算過濾細小雜訊點，使導航目標更穩定
    frontiers = cv2.morphologyEx(frontiers, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
    return frontiers
