#!/usr/bin/env python3
"""
牛耕式覆蓋路徑規劃核心演算法（無 ROS 依賴，可被多個節點共用）
"""
import numpy as np

SPACING = 0.25   # 掃描線間距（公尺）；< 機器人直徑以確保重疊覆蓋
MARGIN  = 0.15   # 障礙物安全邊距（公尺） ≈ 機器人半徑


def boustrophedon(free, res, ox, oy, spacing=SPACING):
    """
    在可走格（free=True）上計算牛耕路點，以 PCA 自動對齊空間主軸。

    輸入
      free    : 2-D bool 陣列，True = 可行走
      res     : 地圖解析度（公尺/格）
      ox, oy  : 地圖原點世界座標（公尺）
      spacing : 掃描線間距（公尺），預設 SPACING
    輸出
      [(world_x, world_y), ...] 依序走訪的路點列表
    """
    rows, cols = np.where(free)
    if len(rows) == 0:
        return []

    wx_all = ox + cols.astype(float) * res
    wy_all = oy + rows.astype(float) * res
    pts    = np.column_stack([wx_all, wy_all])

    # PCA：找自由空間的長軸（sweep）與短軸（step）
    center           = pts.mean(axis=0)
    diffs            = pts - center
    eigvals, eigvecs = np.linalg.eigh(np.cov(diffs.T))
    axis_a = eigvecs[:, np.argmax(eigvals)]   # sweep 方向（長軸）
    axis_b = eigvecs[:, np.argmin(eigvals)]   # step  方向（短軸）

    if axis_a[0] < 0:
        axis_a = -axis_a
    if axis_b[1] < 0:
        axis_b = -axis_b

    proj_a = diffs @ axis_a
    proj_b = diffs @ axis_b

    b_min = proj_b.min()
    b_max = proj_b.max()

    waypoints = []
    l2r = True
    b   = b_min + spacing / 2   # 第一條掃線從邊界內縮 spacing/2，兩端對稱覆蓋

    while b <= b_max + spacing / 2:
        mask = np.abs(proj_b - b) < spacing / 2
        if mask.any():
            a_vals  = proj_a[mask]
            p_start = center + a_vals.min() * axis_a + b * axis_b
            p_end   = center + a_vals.max() * axis_a + b * axis_b
            if l2r:
                waypoints += [(p_start[0], p_start[1]), (p_end[0],   p_end[1])]
            else:
                waypoints += [(p_end[0],   p_end[1]),   (p_start[0], p_start[1])]
            l2r = not l2r
        b += spacing

    return waypoints
