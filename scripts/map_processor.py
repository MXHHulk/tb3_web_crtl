#!/usr/bin/env python3
import cv2
import numpy as np

def preprocess_map(grid_data, width, height, kernel_size=5):
    """
    對 OccupancyGrid 進行形態學處理：
    1. 轉為二值化影像
    2. 開運算 (去毛邊)
    3. 閉運算 (補洞)
    4. 高斯模糊 + 重新二值化 (平滑邊緣)
    """
    # 將數據轉為 numpy array
    raw_img = np.array(grid_data).reshape((height, width)).astype(np.int8)
    
    # 建立二值地圖：0=空地, 100=牆壁, -1=未知
    # 我們只關注空地 (0)
    binary_img = np.zeros((height, width), dtype=np.uint8)
    binary_img[raw_img == 0] = 255
    
    # 形態學運算
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    
    # 開運算 (去小噪點/毛邊)
    opened = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel)
    
    # 閉運算 (補地圖上的小洞)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    
    # 平滑處理
    blurred = cv2.GaussianBlur(closed, (5, 5), 0)
    _, final_thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
    
    return final_thresh
