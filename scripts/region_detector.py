#!/usr/bin/env python3
import cv2
import numpy as np

def detect_regions(binary_img, min_area_px=100):
    """
    偵測地圖中的四邊形區域
    """
    # 找輪廓
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    detected_polygons = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area_px:
            continue
            
        # 計算凸包
        hull = cv2.convexHull(cnt)
        
        # 多邊形近似
        epsilon = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)
        
        # 我們希望是四邊形，但如果環境稍微複雜，放寬到 3~6 邊形並視為一個作業區
        if 3 <= len(approx) <= 6:
            detected_polygons.append(approx)
            
    # 依面積排序 (由大到小)
    detected_polygons.sort(key=cv2.contourArea, reverse=True)
    
    return detected_polygons
