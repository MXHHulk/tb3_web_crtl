#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：region_detector.py (空間分割與偵測)
檔案類型：電腦視覺邏輯 / 區域分析

核心功能：
1. 分析二值化地圖中的封閉空地，將其分割為獨立的清掃區域。
2. 對非凸 (concave) 區域執行 Cellular Decomposition：
   利用 convexityDefects 找出最深凹陷點，以水平或垂直切線遞迴分割，
   直到每個子區域的 minAreaRect 面積比 >= 0.85（接近矩形）為止。
3. 以最小外接矩形 (minAreaRect) 描述每個子區域，確保牛耕路徑掃描線等長整齊。
4. 根據距離權重尋找最適合的探索點。

關鍵依賴：
- cv2 (OpenCV): 輪廓偵測、凸缺陷分析、矩計算、最小外接矩形
- numpy: 數據處理

輸入地圖說明：
  接收來自 map_processor.preprocess_map() 的輸出 (pending_map)
  pending_map = 已清理地圖 - 已覆蓋區域 = 純粹「待清理的空地」
"""

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Cellular Decomposition helpers
# ---------------------------------------------------------------------------

def _rect_ratio(contour):
    """Return contour area / minAreaRect area (0~1); 1.0 = perfect rectangle."""
    area = cv2.contourArea(contour)
    rect = cv2.minAreaRect(contour)
    rect_area = rect[1][0] * rect[1][1]
    return area / rect_area if rect_area > 0 else 0.0


def _find_deepest_concave_point(contour):
    """
    Return the pixel coordinate of the deepest convexity-defect point, or None
    if the contour is already convex or too small for defect analysis.

    Uses cv2.convexityDefects which is more reliable than cross-product methods
    for noisy, pixel-level contours from a SLAM occupancy grid.
    """
    if cv2.isContourConvex(contour) or len(contour) < 4:
        return None
    hull_idx = cv2.convexHull(contour, returnPoints=False)
    if hull_idx is None or len(hull_idx) < 3:
        return None
    try:
        defects = cv2.convexityDefects(contour, hull_idx)
    except cv2.error:
        return None
    if defects is None:
        return None
    best_depth, best_pt = 0, None
    for d in defects:
        _s, _e, f, depth = d[0]
        if depth > best_depth:
            best_depth = depth
            best_pt = tuple(contour[f][0])
    return best_pt


def _split_contour_region(binary_img, contour, split_point):
    """
    Attempt to split a region at split_point using both a horizontal line
    (y = split_point[1]) and a vertical line (x = split_point[0]).

    For each candidate axis, the contour mask is cut and the largest sub-
    contour on each side is found.  The split whose combined rectangularity
    score is highest is returned as (cnt_a, cnt_b), or None if no valid
    split was found (e.g. one side would be too small).
    """
    h, w = binary_img.shape
    x0, y0 = int(split_point[0]), int(split_point[1])

    # Build a filled mask of just this contour, clipped to free space
    base = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(base, [contour], 0, 255, -1)
    base = cv2.bitwise_and(base, binary_img)

    best_score, best_pair = -1.0, None

    # Try horizontal split at y0, then vertical split at x0
    for y_cut, x_cut in [(y0, None), (None, x0)]:
        ma, mb = base.copy(), base.copy()
        if y_cut is not None and 0 < y_cut < h:
            ma[y_cut:, :] = 0   # keep top
            mb[:y_cut, :] = 0   # keep bottom
        elif x_cut is not None and 0 < x_cut < w:
            ma[:, x_cut:] = 0   # keep left
            mb[:, :x_cut] = 0   # keep right
        else:
            continue

        cnts_a, _ = cv2.findContours(ma, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts_b, _ = cv2.findContours(mb, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts_a or not cnts_b:
            continue

        ca = max(cnts_a, key=cv2.contourArea)
        cb = max(cnts_b, key=cv2.contourArea)
        # Both halves must be large enough to be worth processing
        if cv2.contourArea(ca) < 200 or cv2.contourArea(cb) < 200:
            continue

        score = _rect_ratio(ca) + _rect_ratio(cb)
        if score > best_score:
            best_score, best_pair = score, (ca, cb)

    return best_pair


def decompose_region(binary_img, contour, min_area=200, max_depth=3):
    """
    Recursively decompose a (possibly concave) region into approximately
    rectangular cells using axis-aligned sweep-line cuts.

    Algorithm:
      1. If rect_ratio >= 0.85 or already convex  → return [contour] as-is.
      2. Find the deepest convexity-defect point (most pronounced concavity).
      3. Try horizontal and vertical cuts at that point; pick the split whose
         combined rectangularity score is higher.
      4. Recurse on each half (up to max_depth levels).

    Args:
        binary_img: pending_map used to clip masks to valid free space
        contour:    contour of the region to decompose (pixel coordinates)
        min_area:   cells smaller than this are dropped
        max_depth:  recursion limit to prevent infinite loops on edge cases

    Returns:
        List of contours — one per rectangular cell
    """
    if max_depth == 0 or cv2.contourArea(contour) < min_area * 2:
        return [contour]

    if _rect_ratio(contour) >= 0.85:
        return [contour]

    split_pt = _find_deepest_concave_point(contour)
    if split_pt is None:
        return [contour]

    pair = _split_contour_region(binary_img, contour, split_pt)
    if pair is None:
        return [contour]

    ca, cb = pair
    cells = []
    cells.extend(decompose_region(binary_img, ca, min_area, max_depth - 1))
    cells.extend(decompose_region(binary_img, cb, min_area, max_depth - 1))
    return cells


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_regions(binary_img, min_area_px=200):
    """
    從地圖中識別並提取各個待清理的封閉區域。

    對每個原始輪廓呼叫 decompose_region()：
    - 若輪廓已接近矩形 (rect_ratio >= 0.85) 則直接使用。
    - 否則以 Cellular Decomposition 遞迴切割為多個子矩形後再分別建立 region dict。

    Args:
        binary_img:   二值化地圖影像 (255=待清理空地, 0=不可走)
        min_area_px:  最小有效面積門檻值 (像素數)，過濾破碎小區域

    Returns:
        regions: 按面積降序排列的區域字典列表，每個字典包含：
                 {contour, rect_box, angle, area, center, is_rect}
    """
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Decompose each raw contour into rectangular cells before building region dicts
    all_cells = []
    for cnt in contours:
        if cv2.contourArea(cnt) < min_area_px:
            continue
        all_cells.extend(decompose_region(binary_img, cnt, min_area=min_area_px))

    regions = []
    for cnt in all_cells:
        area = cv2.contourArea(cnt)
        if area < min_area_px:
            continue

        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        rect_w, rect_h = rect[1]
        rect_area = rect_w * rect_h
        is_rect = (area / rect_area) > 0.75 if rect_area > 0 else False
        angle = rect[2]

        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            cx, cy = int(rect[0][0]), int(rect[0][1])

        regions.append({
            'contour': cnt,
            'rect_box': box,
            'angle': angle,
            'area': area,
            'center': (cx, cy),
            'is_rect': is_rect,
        })

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
