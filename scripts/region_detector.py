#!/usr/bin/env python3
import cv2
import numpy as np

def detect_regions(binary_img, min_area_px=200):
    """
    偵測地圖中的有效區域：
    1. 找輪廓
    2. 過濾掉太小的碎片區域
    3. 對大區域進行多邊形簡化 (主要尋找四邊形)
    """
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    regions = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area_px:
            continue
            
        # 取得凸包以簡化邊緣
        hull = cv2.convexHull(cnt)
        
        # 多邊形近似 (尋找幾何特徵)
        epsilon = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)
        
        # 紀錄區域資訊：形狀、面積、質心
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            cx, cy = approx[0][0]

        regions.append({
            'contour': cnt,
            'approx': approx,
            'area': area,
            'center': (cx, cy),
            'is_quad': 4 <= len(approx) <= 6 # 視為廣義的四邊形區域
        })
            
    # 按面積由大到小排序
    regions.sort(key=lambda x: x['area'], reverse=True)
    
    return regions

def find_best_frontier(frontier_img, robot_px_pos):
    """
    從邊界圖中找到最值得去探索的點 (最近的邊界質心)
    """
    contours, _ = cv2.findContours(frontier_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_pt = None
    min_dist = float('inf')
    
    for cnt in contours:
        if cv2.contourArea(cnt) < 5: continue # 忽略太小的雜點
        
        M = cv2.moments(cnt)
        if M["m00"] == 0: continue
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        
        dist = (cx - robot_px_pos[0])**2 + (cy - robot_px_pos[1])**2
        if dist < min_dist:
            min_dist = dist
            best_pt = (cx, cy)
            
    return best_pt
