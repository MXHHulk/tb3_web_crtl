#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：coverage_planner.py (全覆蓋路徑生成模組)
檔案類型：演算法工具類 / 邏輯運算單元

核心功能：
1. 針對指定的多邊形區域生成「牛耕式 (Boustrophedon)」路徑。
2. 自動計算區域的最長邊作為掃描主方向，以減少機器人轉向次數。
3. 生成 Z 字型的連續導航點，確保區域內的高覆蓋率。

Boustrophedon (牛耕式) 演算法概念：
  模仿農夫耕田的方式，沿著平行線來回掃描整個區域：
  → → → → → → (第一行：從左到右)
  ← ← ← ← ← (第二行：從右到左)
  → → → → → → (第三行：重複)
  每行的間距 = step_size_px (依機器人寬度與重疊率計算)

關鍵依賴：
- numpy: 矩陣運算與向量計算
- cv2 (OpenCV): 處理多邊形頂點與幾何變換
"""

import numpy as np
import cv2


def generate_boustrophedon_path(poly_pts, step_size_px):
    """
    輸入多邊形輪廓頂點與步進像素，生成完整的牛耕式覆蓋路徑點序列。

    處理流程：
      1. 找最長邊方向 → 決定「掃描主方向」
      2. 旋轉座標系讓主方向對齊 X 軸
      3. 在旋轉後的 Y 方向以 step_size 間距生成水平掃描線
      4. 計算每條掃描線與多邊形邊界的交點，取最左最右端點
      5. 交替正反方向串接所有線段端點
      6. 旋轉回原始座標系

    Args:
        poly_pts:      多邊形輪廓頂點 (來自 cv2.findContours，shape: Nx1x2 或 Nx2)
        step_size_px:  掃描線間距 (像素)，由 step_size / resolution 計算而來

    Returns:
        list of [x, y]: 路徑點的像素座標列表，依照執行順序排列
                        空列表表示多邊形太小無法生成路徑
    """
    # --- Step 1: 找出多邊形的最長邊方向 ---
    # 將輸入的輪廓點壓縮成 (N, 2) 的形狀，移除 OpenCV 多餘的維度
    pts = poly_pts.reshape(-1, 2)

    max_dist = 0
    best_vec = (1, 0)  # 預設方向：正 X 軸

    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]  # 循環取下一個頂點 (最後一點連回第一點)
        dist = np.linalg.norm(p1 - p2)  # 計算這條邊的歐氏距離 (像素長度)
        if dist > max_dist:
            max_dist = dist
            # 計算這條邊的單位向量 (長度=1)，代表最長邊的方向
            best_vec = (p2 - p1) / dist

    # --- Step 2: 建立旋轉矩陣，將最長邊方向對齊 X 軸 ---
    # angle：最長邊相對於 X 軸的角度 (弧度)
    # 旋轉矩陣 R 以 -angle 旋轉，讓最長邊方向變成水平
    angle = np.arctan2(best_vec[1], best_vec[0])
    cos_a, sin_a = np.cos(-angle), np.sin(-angle)
    # 2D 旋轉矩陣：[[cos, -sin], [sin, cos]]
    R = np.array([[cos_a, -sin_a], [sin_a, cos_a]])

    # 將所有頂點投影至旋轉後的座標系
    # np.dot(pts, R.T) 等同對每個點做矩陣乘法 R @ pt
    rotated_pts = np.dot(pts, R.T)

    # 找旋轉後座標系的邊界框
    min_x, min_y = np.min(rotated_pts, axis=0)
    max_x, max_y = np.max(rotated_pts, axis=0)

    # --- Step 3: 生成掃描線並求交點 (Zig-Zag) ---
    path_rotated = []
    reverse = False  # 掃描方向旗標：False=左→右，True=右→左

    # 邊距緩衝：路徑起始不從邊緣開始，留出半個步進的間距
    # 避免規劃出緊貼多邊形邊界的路徑點，防止機器人碰到牆壁
    padding = step_size_px * 0.5

    # 沿旋轉後的 Y 軸方向，以 step_size_px 為間距逐行掃描
    for y in np.arange(min_y + padding, max_y - padding, step_size_px):
        # 計算當前掃描線 y 與多邊形每條邊的交點
        intersections = []
        for i in range(len(rotated_pts)):
            p1 = rotated_pts[i]
            p2 = rotated_pts[(i + 1) % len(rotated_pts)]

            # 判斷掃描線是否穿過這條邊 (y 值落在 p1.y 和 p2.y 之間)
            # 使用嚴格小於避免在頂點處重複計算
            if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
                # 線性插值求掃描線 y 與邊段的 X 交點
                # 公式：x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                x_int = p1[0] + (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                intersections.append(x_int)

        # 至少要有兩個交點 (一入一出) 才能形成有效的掃描線段
        if len(intersections) >= 2:
            intersections.sort()  # 排序確保 [0] 是最左，[-1] 是最右
            # 取最左和最右的交點作為這行掃描線的起點與終點
            line = [(intersections[0], y), (intersections[-1], y)]

            # 交替反轉方向，實現 Z 字型的「牛耕式」路徑
            if reverse:
                line.reverse()  # 這行從右掃到左
            path_rotated.extend(line)  # 將兩個端點加入路徑序列
            reverse = not reverse  # 下一行切換方向

    # --- Step 4: 路徑點逆旋轉回原始座標系 ---
    if not path_rotated:
        return []  # 多邊形太小或形狀異常，無法生成路徑

    # 逆旋轉矩陣：R 的轉置即其逆矩陣 (正交矩陣的性質)
    R_inv = np.array([[cos_a, sin_a], [-sin_a, cos_a]])
    # 將所有路徑點從旋轉座標系轉回原始像素座標系
    final_path = np.dot(path_rotated, R_inv.T)

    return final_path.tolist()
