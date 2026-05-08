#!/usr/bin/env python3
import cv2
import numpy as np

def preprocess_map(grid_data, width, height, kernel_size=5):
    """
    更穩健的地圖預處理：
    1. 二值化
    2. 移除噪點
    3. 加入較大的膨脹空間，防止路徑點離牆太近導致 DWA Planner 報警
    """
    raw_img = np.array(grid_data).reshape((height, width))
    
    # 255: 空地, 0: 障礙
    binary_img = np.zeros((height, width), dtype=np.uint8)
    binary_img[raw_img == 0] = 255
    
    # 移除毛邊與噪點
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    opened = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel)
    
    # 核心優化：更激進的侵蝕空地 (相當於更厚的障礙物牆壁)
    # 增加為 2 次迭代，讓路徑點更遠離牆壁，解決 "DWA planner failed" 問題
    safety_margin_kernel = np.ones((3, 3), np.uint8)
    eroded = cv2.erode(opened, safety_margin_kernel, iterations=2)
    
    return eroded

def get_frontier_map(grid_data, width, height):
    """偵測邊界"""
    raw_img = np.array(grid_data).reshape((height, width))
    free_mask = np.zeros((height, width), dtype=np.uint8)
    free_mask[raw_img == 0] = 255
    unknown_mask = np.zeros((height, width), dtype=np.uint8)
    unknown_mask[raw_img == -1] = 255
    
    dilated_free = cv2.dilate(free_mask, np.ones((3,3), np.uint8))
    frontiers = cv2.bitwise_and(dilated_free, unknown_mask)
    frontiers = cv2.morphologyEx(frontiers, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
    return frontiers
