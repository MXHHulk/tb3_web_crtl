#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：region_detector.py (空間分割與偵測)
檔案類型：電腦視覺邏輯 / 區域分析

核心功能：
1. 分析二值化地圖中的封閉空地，將其分割為獨立的清掃區域。
2. 以最小外接矩形 (Minimum Area Rectangle) 描述區域邊界，取代凸包逼近，
   使牛耕式路徑生成的掃描線長度一致、視覺上呈現整齊的平行 Z 字型。
3. 根據距離權重尋找最適合的探索點。

關鍵依賴：
- cv2 (OpenCV): 用於輪廓偵測、矩計算 (Moments) 與最小外接矩形
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

    使用 OpenCV 的輪廓偵測找出白色連通區域，並以最小外接矩形 (Minimum Area
    Rectangle) 描述每個區域，取代原本的凸包 + 多邊形逼近做法。矩形頂點傳入
    boustrophedon 路徑生成器後，可確保每條掃描線等長、路徑呈現整齊 Z 字型。

    Args:
        binary_img:   二值化地圖影像 (255=待清理空地, 0=不可走)
        min_area_px:  最小有效面積門檻值 (像素數)，過濾破碎小區域

    Returns:
        regions: 按面積降序排列的區域字典列表，每個字典包含：
                 {contour, rect_box, angle, area, center, is_rect}
    """
    # --- 輪廓偵測 ---
    # RETR_EXTERNAL：只找最外層輪廓，不追蹤巢狀輪廓 (避免重複處理同一區域)
    # CHAIN_APPROX_SIMPLE：壓縮水平/垂直直線段，只儲存端點，節省記憶體
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for cnt in contours:
        # --- 面積過濾 ---
        area = cv2.contourArea(cnt)
        if area < min_area_px:
            continue

        # --- 最小外接矩形 (Minimum Area Rectangle) ---
        # rect = ((cx, cy), (w, h), angle)
        #   (cx, cy) : 矩形中心的像素座標
        #   (w, h)   : 矩形的寬與高 (w 對應 angle 方向的邊)
        #   angle    : 矩形主軸與 X 軸的夾角 (度)，範圍 (-90, 0]
        # cv2.boxPoints 將上述參數轉換為四個角點座標 (4x2 float32)
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int0(box)  # 轉為整數像素座標

        rect_w, rect_h = rect[1]
        rect_area = rect_w * rect_h

        # --- 矩形相似度判斷 ---
        # 比較輪廓實際面積與最小外接矩形面積的比值
        # 比值接近 1.0 表示原始形狀已非常接近矩形；低於 0.75 表示有明顯凹陷
        is_rect = (area / rect_area) > 0.75 if rect_area > 0 else False

        # --- 主軸角度 ---
        # 直接取用 minAreaRect 輸出的角度，供路徑規劃器決定掃描方向
        angle = rect[2]

        # --- 質心計算 (幾何矩) ---
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            # 退化輪廓時改用矩形中心
            cx, cy = int(rect[0][0]), int(rect[0][1])

        # --- 打包區域資訊 ---
        regions.append({
            'contour': cnt,      # 原始像素輪廓 (保留供面積計算等用途)
            'rect_box': box,     # 最小外接矩形的四個頂點 (4x2) → 傳給路徑規劃與可視化
            'angle': angle,      # 矩形主軸偏角 (度) → 可供路徑規劃器直接使用
            'area': area,        # 輪廓實際像素面積 → 用於排序與門檻判斷
            'center': (cx, cy),  # 質心像素座標 → 可用於距離計算
            'is_rect': is_rect,  # True 表示形狀接近矩形 (面積比 > 0.75)
        })

    # 按面積由大到小排序，確保 main_loop 優先清理最大的主要房間
    regions.sort(key=lambda x: x['area'], reverse=True)

    return regions


def find_best_frontier(frontier_img, robot_px_pos):
    """
    從 Frontier 地圖中找到距離機器人最近的探索目標點。

    策略：選擇距離機器人最近的 Frontier 塊的質心作為下一個導航目標。
    選擇最近點（而非最大點）的原因：減少長途空跑，讓探索更有效率。

    目標點安全處理：對 Frontier 圖進行侵蝕 (Erode) 後再偵測輪廓，
    確保回傳的質心落在已知空地內部，而非剛好在空地與未知區域的交界線上，
    防止機器人衝入 SLAM 尚未建圖的黑色/灰色區域。

    Args:
        frontier_img:  由 map_processor.get_frontier_map() 產生的二值化前沿圖
        robot_px_pos:  機器人目前在像素座標系中的位置 (px_x, px_y)

    Returns:
        best_pt: 最近 Frontier 塊的質心像素座標 (cx, cy)，若無則回傳 None
    """
    # 侵蝕 Frontier 圖使目標點向內縮，遠離空地與未知區域的邊界
    # iterations=2 搭配 3x3 核心 ≈ 向內縮約 3px (依 0.05m/px 解析度約 15cm)
    kernel = np.ones((3, 3), np.uint8)
    safe_frontier = cv2.erode(frontier_img, kernel, iterations=2)

    # 偵測所有前沿「塊」的輪廓，每個連通的白色區域就是一個 Frontier cluster
    contours, _ = cv2.findContours(safe_frontier, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

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
