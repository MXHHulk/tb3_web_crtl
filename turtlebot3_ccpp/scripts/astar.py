#!/usr/bin/env python3
"""
自寫 A* 全域路徑規劃（零 ROS 依賴，可離線測試，見 test/astar_bench.py）。

用途：覆蓋任務 nav_mode='astar' 時的跨區移動——在「去雜點＋安全邊距後的可走區」（與覆蓋規劃同一張
free 圖）上算一條繞開障礙的路線，再交給 map_server 的直線循跡逐段開過去，完全不經 move_base／DWA。

演算法
  1. 起點／終點若落在可走區外（定位誤差、車子剛貼牆停下），吸附到 SNAP_MAX 內最近的可走格。
  2. 8 鄰格 A*：直走成本 1、斜走 √2（以格為單位）；斜走時兩側直鄰格都要可走，不准切牆角。
     每格再乘上「離牆懲罰」1 + W_CLEAR ×（CLEAR_PREF − 離牆距離）/ CLEAR_PREF（只在離牆 < CLEAR_PREF 時），
     讓路線盡量走在通道中間，車子轉身時不會擦牆（2026-11-11 唯一一次受困就是離牆 0.20 m 轉不了身）。
     啟發函數用 octile 距離；懲罰只會讓成本變大，所以啟發函數仍然不高估，A* 找到的是最佳解。
  3. 路線用 RDP 簡化成少數轉折點，且每一段都要整段落在可走區內（不行就保留原折點）。
"""
import heapq
import math

import numpy as np
from scipy.ndimage import distance_transform_edt

from coverage_planner import _rdp, _seg_free

SNAP_MAX   = 0.30   # 起終點不在可走區時，往外找最近可走格的最大距離（公尺）
CLEAR_PREF = 0.15   # 離「不可走區」小於此距離（公尺）就加懲罰（可走區本身已扣掉 0.10 m 安全邊距）
W_CLEAR    = 3.0    # 離牆懲罰權重：0＝純最短路徑
RDP_EPS    = 0.04   # 路線簡化容許誤差（公尺）

_NBR = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _to_cell(p, res, ox, oy):
    return int(round((p[1] - oy) / res)), int(round((p[0] - ox) / res))


def _to_world(rc, res, ox, oy):
    return (ox + rc[1] * res, oy + rc[0] * res)


def _snap(free, rc, near_idx, dist_out, res):
    """rc 不可走時，回傳最近的可走格（距離超過 SNAP_MAX 回傳 None）。"""
    H, W = free.shape
    r, c = rc
    if not (0 <= r < H and 0 <= c < W):
        return None
    if free[r, c]:
        return rc
    if dist_out[r, c] * res > SNAP_MAX:
        return None
    return int(near_idx[0][r, c]), int(near_idx[1][r, c])


def plan_path(free, res, ox, oy, start, goal):
    """
    在 free（2-D bool，True＝可走）上規劃 start → goal（世界座標）。
    回傳 dict：
      path      [(x, y), ...] 簡化後的折線，第一點＝start、最後一點＝goal；規劃失敗為 None
      raw_len   A* 原始格點路線長（公尺）
      expanded  展開的格數（衡量計算量）
      why       失敗原因：'start_blocked' / 'goal_blocked' / 'no_path'；成功為 ''
    """
    free = np.asarray(free, dtype=bool)
    H, W = free.shape
    # 不可走格 → 最近可走格（吸附用）；可走格 → 離最近不可走格的距離（懲罰用）
    dist_out, near_idx = distance_transform_edt(~free, return_indices=True)
    clear = distance_transform_edt(free) * res

    s = _snap(free, _to_cell(start, res, ox, oy), near_idx, dist_out, res)
    g = _snap(free, _to_cell(goal, res, ox, oy), near_idx, dist_out, res)
    if s is None:
        return {'path': None, 'raw_len': 0.0, 'expanded': 0, 'why': 'start_blocked'}
    if g is None:
        return {'path': None, 'raw_len': 0.0, 'expanded': 0, 'why': 'goal_blocked'}

    pen = 1.0 + W_CLEAR * np.clip((CLEAR_PREF - clear) / CLEAR_PREF, 0.0, None)

    def h(rc):
        dr, dc = abs(rc[0] - g[0]), abs(rc[1] - g[1])
        return (dr + dc) + (math.sqrt(2) - 2) * min(dr, dc)

    best = {s: 0.0}
    parent = {s: None}
    heap = [(h(s), 0.0, s)]
    closed = set()
    expanded = 0
    while heap:
        _, cost, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        closed.add(cur)
        expanded += 1
        if cur == g:
            break
        r, c = cur
        for dr, dc in _NBR:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < H and 0 <= nc < W) or not free[nr, nc] or (nr, nc) in closed:
                continue
            if dr and dc and not (free[r, nc] and free[nr, c]):   # 不切牆角
                continue
            step = (math.sqrt(2) if dr and dc else 1.0) * pen[nr, nc]
            nxt = cost + step
            if nxt < best.get((nr, nc), math.inf):
                best[(nr, nc)] = nxt
                parent[(nr, nc)] = cur
                heapq.heappush(heap, (nxt + h((nr, nc)), nxt, (nr, nc)))
    if g not in closed:
        return {'path': None, 'raw_len': 0.0, 'expanded': expanded, 'why': 'no_path'}

    cells = []
    cur = g
    while cur is not None:
        cells.append(cur)
        cur = parent[cur]
    cells.reverse()
    pts = np.array([_to_world(rc, res, ox, oy) for rc in cells], dtype=float)
    raw_len = float(np.sum(np.hypot(*np.diff(pts, axis=0).T))) if len(pts) > 1 else 0.0

    # RDP 簡化；簡化後某段若切出可走區，就把那段換回原始格點
    simp = [tuple(p) for p in _rdp(pts, RDP_EPS)] if len(pts) > 2 else [tuple(p) for p in pts]
    out = [simp[0]]
    for q in simp[1:]:
        if _seg_free(free, res, ox, oy, out[-1], q):
            out.append(q)
            continue
        i0 = int(np.argmin(np.hypot(*(pts - np.array(out[-1])).T)))
        i1 = int(np.argmin(np.hypot(*(pts - np.array(q)).T)))
        out.extend(tuple(p) for p in pts[i0 + 1:i1 + 1])
    out = [(float(x), float(y)) for x, y in out]

    # 頭尾接上真正的起終點：離格點中心很近就直接取代；吸附過（離很遠）就多接一小段，
    # 讓車子先從可走區外直線開回吸附點，而不是斜切過不可走區直奔下一個轉折點
    sp, gp = (float(start[0]), float(start[1])), (float(goal[0]), float(goal[1]))
    if math.dist(sp, out[0]) <= res:
        out[0] = sp
    else:
        out.insert(0, sp)
    if len(out) > 1 and math.dist(gp, out[-1]) <= res:
        out[-1] = gp
    else:
        out.append(gp)
    return {'path': out, 'raw_len': raw_len, 'expanded': expanded, 'why': ''}
