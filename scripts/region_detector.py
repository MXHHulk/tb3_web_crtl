#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：region_detector.py (空間分割與偵測)
檔案類型：電腦視覺邏輯 / 區域分析

核心功能：
1. 分析二值化地圖中的封閉空地，將其分割為獨立的清掃區域。
2. 對區域邊界進行多邊形簡化 (Polygon Approximation)，用於後續路徑規劃。
3. 根據距離權重尋找最適合的探索點。

關鍵依賴：
- cv2 (OpenCV): 用於輪廓偵測與矩計算 (Moments)
- numpy: 用於數據處理

輸入地圖說明：
  接收來自 map_processor.preprocess_map() 的輸出 (pending_map)
  pending_map = 已清理地圖 - 已覆蓋區域 = 純粹「待清理的空地」
"""

import cv2
import numpy as np


def detect_regions(binary_img, min_area_px=200):
    """
    從地圖中識別並提取各個待清理的封閉區域。

    使用 OpenCV 的輪廓偵測找出白色連通區域，並為每個區域計算：
    - 邊界輪廓 (用於 boustrophedon 路徑生成)
    - 簡化多邊形 (用於可視化與區域判斷)
    - 質心座標 (用於距離排序)

    Args:
        binary_img:   二值化地圖影像 (255=待清理空地, 0=不可走)
        min_area_px:  最小有效面積門檻值 (像素數)，過濾破碎小區域

    Returns:
        regions: 按面積降序排列的區域字典列表，每個字典包含：
                 {contour, approx, area, center, is_quad}
    """
    # --- 輪廓偵測 ---
    # RETR_EXTERNAL：只找最外層輪廓，不追蹤巢狀輪廓 (避免重複處理同一區域)
    # CHAIN_APPROX_SIMPLE：壓縮水平/垂直直線段，只儲存端點，節省記憶體
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for cnt in contours:
        # --- 面積過濾 ---
        # 計算輪廓圍繞的像素面積
        # 過濾掉 SLAM 建圖雜訊產生的破碎小白點，避免浪費導航資源
        area = cv2.contourArea(cnt)
        if area < min_area_px:
            continue

        # --- 凸包處理 ---
        # 計算輪廓的凸包 (Convex Hull)：去除輪廓上向內凹陷的部分
        # 目的：確保區域邊界是向外凸出的，讓牛耕式路徑計算的交點更穩定
        # 凹陷的角落容易造成掃描線交點計算異常
        hull = cv2.convexHull(cnt)

        # --- Douglas-Peucker 多邊形簡化 ---
        # 將凸包頂點數量精簡，移除不必要的中間點
        # epsilon = 周長的 2%：容許偏差越大，簡化越激進 (頂點越少)
        # 簡化後的頂點數決定 is_quad 判斷，也使視覺化邊框更簡潔
        epsilon = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)

        # --- 質心計算 (幾何矩) ---
        # 使用 OpenCV 的影像矩 (Image Moments) 計算區域的重心座標
        # m00 = 面積，m10/m01 = 分別對 x 和 y 的一階矩
        # 質心公式：cx = m10/m00，cy = m01/m00
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            # 面積極小或退化輪廓時 m00 為 0，改用第一個頂點作為參考點
            cx, cy = approx[0][0]

        # --- 打包區域資訊 ---
        regions.append({
            'contour': cnt,           # 原始像素輪廓 → 傳給 generate_boustrophedon_path()
            'approx': approx,         # 簡化後的多邊形頂點 → 傳給 publish_target_region()
            'area': area,             # 像素面積 → 用於排序優先順序
            'center': (cx, cy),       # 質心像素座標 → 可用於距離計算
            'is_quad': 4 <= len(approx) <= 6  # True 表示近似矩形/六邊形，形狀規則性較高
        })

    # 按面積由大到小排序，確保 main_loop 優先清理最大的主要房間
    # regions[0] 永遠是面積最大的待清理區域
    regions.sort(key=lambda x: x['area'], reverse=True)

    return regions


def find_best_frontier(frontier_img, robot_px_pos):
    """
    從 Frontier 地圖中找到距離機器人最近的探索目標點。

    策略：選擇距離機器人最近的 Frontier 塊的質心作為下一個導航目標。
    選擇最近點（而非最大點）的原因：減少長途空跑，讓探索更有效率。

    Args:
        frontier_img:  由 map_processor.get_frontier_map() 產生的二值化前沿圖
        robot_px_pos:  機器人目前在像素座標系中的位置 (px_x, px_y)

    Returns:
        best_pt: 最近 Frontier 塊的質心像素座標 (cx, cy)，若無則回傳 None
    """
    # 偵測所有前沿「塊」的輪廓，每個連通的白色區域就是一個 Frontier cluster
    contours, _ = cv2.findContours(frontier_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_pt = None
    min_dist = float('inf')  # 初始為無限大，方便後續比較

    for cnt in contours:
        # 忽略面積極小 (< 5px) 的雜訊塊
        # 這類點可能是 SLAM 邊緣的單個像素擾動，不值得為此導航
        if cv2.contourArea(cnt) < 5:
            continue

        # 用幾何矩計算 Frontier 塊的質心作為導航目標
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue  # 防禦性判斷，避免除以零
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        # 計算質心與機器人當前位置的歐氏距離平方
        # 使用平方距離 (不開根號) 可節省一次 sqrt 運算，比較時結果一致
        dist = (cx - robot_px_pos[0]) ** 2 + (cy - robot_px_pos[1]) ** 2
        if dist < min_dist:
            min_dist = dist
            best_pt = (cx, cy)  # 更新最近的 Frontier 目標點

    return best_pt
