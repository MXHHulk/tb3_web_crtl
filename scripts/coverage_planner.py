#!/usr/bin/env python3
import numpy as np
import cv2

def generate_boustrophedon_path(poly_pts, step_size_px):
    """
    poly_pts: 多邊形頂點 (像素座標)
    step_size_px: 掃描線間距 (像素)
    """
    # 1. 找出最長邊的方向作為掃描方向
    pts = poly_pts.reshape(-1, 2)
    max_dist = 0
    best_vec = (1, 0)
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i+1)%len(pts)]
        dist = np.linalg.norm(p1 - p2)
        if dist > max_dist:
            max_dist = dist
            best_vec = (p2 - p1) / dist
            
    # 2. 計算旋轉矩陣將多邊形對齊 X 軸
    angle = np.arctan2(best_vec[1], best_vec[0])
    cos_a, sin_a = np.cos(-angle), np.sin(-angle)
    R = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
    
    rotated_pts = np.dot(pts, R.T)
    min_x, min_y = np.min(rotated_pts, axis=0)
    max_x, max_y = np.max(rotated_pts, axis=0)
    
    # 3. 生成掃描線
    path_rotated = []
    reverse = False
    
    # 稍微縮減邊界避免撞牆
    padding = step_size_px * 0.5
    
    for y in np.arange(min_y + padding, max_y - padding, step_size_px):
        # 找掃描線 y 與旋轉後多邊形的交點
        intersections = []
        for i in range(len(rotated_pts)):
            p1 = rotated_pts[i]
            p2 = rotated_pts[(i+1)%len(rotated_pts)]
            
            if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
                x_int = p1[0] + (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                intersections.append(x_int)
        
        if len(intersections) >= 2:
            intersections.sort()
            line = [(intersections[0], y), (intersections[-1], y)]
            if reverse:
                line.reverse()
            path_rotated.extend(line)
            reverse = not reverse
            
    # 4. 轉回原始座標
    if not path_rotated:
        return []
        
    R_inv = np.array([[cos_a, sin_a], [-sin_a, cos_a]])
    final_path = np.dot(path_rotated, R_inv.T)
    
    return final_path.tolist()
