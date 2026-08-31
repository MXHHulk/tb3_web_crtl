#!/usr/bin/env python3
"""
測試工具：覆蓋規劃離線效果評估（不需要 ROS、不需要機器人）。

用合成地圖直接餵給 scripts/coverage_planner.plan()，量測各種場地形狀下的
覆蓋率、路徑長度、cell 數量與線段合法性，用來回答「這個演算法能跑什麼場地」。

之所以能離線跑，是因為 coverage_planner 刻意做到零 ROS 依賴——
它的輸入只是一個 numpy bool 陣列 + 解析度 + 原點。

用法：
  python3 test/coverage_bench.py             # 跑全部場地，印總表
  python3 test/coverage_bench.py --detail 斜置30  # 印某個場地的逐帶診斷

評估指標（見 docs/01_學習資料/21_測試方法與評估指標.md）：
  cell / run / 臨界   分解結果的規模
  主軸 / λ比          PCA 的輸出（λ比接近 1 代表主軸方向退化）
  覆蓋率              可走格中心離任一「掃描線」<= 0.10 m 的比例
  掃描長 / 轉場長     掃描線總長 vs 換行接駁總長（轉場佔比越高越沒效率）
  穿牆(掃描)          ⚠ 必須為 0，否則演算法有 bug
  穿牆(轉場)          直線接駁穿過障礙的段數，需靠 move_base 繞路
"""
import argparse
import math
import os
import sys
from collections import Counter

import numpy as np
from scipy.ndimage import binary_dilation

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'scripts'))

from coverage_planner import (MARGIN, SPACING, apply_safety_margin,
                              principal_axes, plan, _slice_runs,
                              _link_runs, _build_cells)

RES        = 0.05    # 模擬地圖解析度（與 gmapping 預設一致）
WALL       = 0.15    # 合成牆厚（公尺）
PAD        = 0.4     # 地圖邊界外的未知區留白
COV_RADIUS = 0.10    # 覆蓋半徑（機器人清掃/感測半徑）


# ════════════════════════════════════════════════════════
#  合成地圖
# ════════════════════════════════════════════════════════
def build_map(pred, xr, yr):
    """
    依「室內判定函式」生成 OccupancyGrid 風格的 int16 陣列。

    pred(X, Y) -> bool 陣列，True = 室內可走
    回傳 (data, ox, oy)：0=自由, 100=障礙(牆), -1=未知(牆外)
    """
    ox, oy = xr[0] - PAD, yr[0] - PAD
    W = int((xr[1] - xr[0] + 2 * PAD) / RES)
    H = int((yr[1] - yr[0] + 2 * PAD) / RES)
    X, Y = np.meshgrid(ox + RES * np.arange(W), oy + RES * np.arange(H))

    inside = pred(X, Y)
    data = np.full((H, W), -1, dtype=np.int16)
    data[inside] = 0

    # 室內外邊界往外 WALL 公尺畫成牆，其餘保持未知
    r = max(1, round(WALL / RES))
    near = binary_dilation(inside, np.ones((2 * r + 1, 2 * r + 1), bool))
    data[near & ~inside] = 100
    return data, ox, oy


def _rot(X, Y, deg):
    """把世界座標旋轉 -deg，用來描述斜置的房間。"""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return X * c + Y * s, -X * s + Y * c


SCENES = {
    '長方形4x2':  (lambda X, Y: (0 <= X) & (X <= 4) & (0 <= Y) & (Y <= 2),
                   (0, 4), (0, 2)),
    '細長6x1.5':  (lambda X, Y: (0 <= X) & (X <= 6) & (0 <= Y) & (Y <= 1.5),
                   (0, 6), (0, 1.5)),
    '正方形3x3':  (lambda X, Y: (0 <= X) & (X <= 3) & (0 <= Y) & (Y <= 3),
                   (0, 3), (0, 3)),
    '含柱4x2':    (lambda X, Y: ((0 <= X) & (X <= 4) & (0 <= Y) & (Y <= 2)
                                 & ~((1.7 < X) & (X < 2.3) & (0.7 < Y) & (Y < 1.3))),
                   (0, 4), (0, 2)),
    '雙柱4x2':    (lambda X, Y: ((0 <= X) & (X <= 4) & (0 <= Y) & (Y <= 2)
                                 & ~((1.0 < X) & (X < 1.5) & (0.6 < Y) & (Y < 1.4))
                                 & ~((2.6 < X) & (X < 3.1) & (0.6 < Y) & (Y < 1.4))),
                   (0, 4), (0, 2)),
    'L形4x4':     (lambda X, Y: (((0 <= X) & (X <= 4) & (0 <= Y) & (Y <= 4))
                                 & ~((X > 2) & (Y > 2))),
                   (0, 4), (0, 4)),
    'L形扁平':    (lambda X, Y: (((0 <= X) & (X <= 5) & (0 <= Y) & (Y <= 3))
                                 & ~((X > 2) & (Y > 1.2))),
                   (0, 5), (0, 3)),
    'U形':        (lambda X, Y: (((0 <= X) & (X <= 4) & (0 <= Y) & (Y <= 3))
                                 & ~((1.2 < X) & (X < 2.8) & (Y > 1.0))),
                   (0, 4), (0, 3)),
    '雙房間走廊': (lambda X, Y: (((0 <= X) & (X <= 2) & (0 <= Y) & (Y <= 2))
                                 | ((3.5 <= X) & (X <= 5.5) & (0 <= Y) & (Y <= 2))
                                 | ((2 <= X) & (X <= 3.5) & (0.7 <= Y) & (Y <= 1.3))),
                   (0, 5.5), (0, 2)),
    '斜置15度':   (lambda X, Y: (lambda A, B: (np.abs(A) <= 2) & (np.abs(B) <= 1))(*_rot(X, Y, 15)),
                   (-3, 3), (-2, 2)),
    '斜置30度':   (lambda X, Y: (lambda A, B: (np.abs(A) <= 2) & (np.abs(B) <= 1))(*_rot(X, Y, 30)),
                   (-3, 3), (-2, 2)),
    '斜置45度':   (lambda X, Y: (lambda A, B: (np.abs(A) <= 2) & (np.abs(B) <= 1))(*_rot(X, Y, 45)),
                   (-3, 3), (-3, 3)),
    '窄通道0.5m': (lambda X, Y: (((0 <= X) & (X <= 2) & (0 <= Y) & (Y <= 2))
                                 | ((3.5 <= X) & (X <= 5.5) & (0 <= Y) & (Y <= 2))
                                 | ((2 <= X) & (X <= 3.5) & (0.75 <= Y) & (Y <= 1.25))),
                   (0, 5.5), (0, 2)),
}

# 未探索場地另外處理：室內有一塊仍是 -1（SLAM 還沒看到），
# 用來量化「假完成」——演算法只覆蓋已知格，未知格完全不進規劃。
UNKNOWN_SCENE = ('未探索4x2',
                 lambda X, Y: (0 <= X) & (X <= 4) & (0 <= Y) & (Y <= 2),
                 lambda X, Y: (X > 2.8),          # 這塊維持未知
                 (0, 4), (0, 2))


# ════════════════════════════════════════════════════════
#  評估指標
# ════════════════════════════════════════════════════════
def seg_is_free(free, ox, oy, p, q):
    """線段 p→q 是否整條都落在可走格上（沿線以 res/4 取樣檢查）。"""
    H, W = free.shape
    d = math.hypot(q[0] - p[0], q[1] - p[1])
    n = max(2, int(d / (RES / 4)) + 1)
    for i in range(n + 1):
        t = i / n
        x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
        c, r = round((x - ox) / RES), round((y - oy) / RES)
        if not (0 <= r < H and 0 <= c < W and free[r, c]):
            return False
    return True


def coverage_ratio(free, ox, oy, wps):
    """可走格中心離任一「掃描線」<= COV_RADIUS 的比例。轉場線不計入覆蓋。"""
    rows, cols = np.where(free)
    if not len(rows):
        return 0.0
    px, py = ox + cols * RES, oy + rows * RES
    covered = np.zeros(len(rows), bool)
    for i in range(0, len(wps) - 1, 2):              # 偶數 index 起 = 掃描線
        a, b = np.asarray(wps[i]), np.asarray(wps[i + 1])
        ab = b - a
        L2 = float(ab @ ab)
        if L2 == 0:
            continue
        t = np.clip(((px - a[0]) * ab[0] + (py - a[1]) * ab[1]) / L2, 0, 1)
        dx, dy = px - (a[0] + t * ab[0]), py - (a[1] + t * ab[1])
        covered |= (dx * dx + dy * dy) <= COV_RADIUS ** 2
    return float(covered.mean())


def evaluate(name):
    if name == UNKNOWN_SCENE[0]:
        _, pred, unk, xr, yr = UNKNOWN_SCENE
        data, ox, oy = build_map(pred, xr, yr)
        X, Y = np.meshgrid(ox + RES * np.arange(data.shape[1]),
                           oy + RES * np.arange(data.shape[0]))
        data[(data == 0) & unk(X, Y)] = -1        # 把右側 1.2 m 打回未知
    else:
        pred, xr, yr = SCENES[name]
        data, ox, oy = build_map(pred, xr, yr)
    safe = apply_safety_margin(data, MARGIN, RES)
    free = (data == 0) & ~safe

    r = plan(free, RES, ox, oy)
    wps = r['waypoints']
    if not wps:
        return dict(name=name, ok=False)

    sweep_len = sum(math.dist(wps[i], wps[i + 1]) for i in range(0, len(wps) - 1, 2))
    link_len  = sum(math.dist(wps[i], wps[i + 1]) for i in range(1, len(wps) - 1, 2))
    bad_sweep = sum(not seg_is_free(free, ox, oy, wps[i], wps[i + 1])
                    for i in range(0, len(wps) - 1, 2))
    bad_link  = sum(not seg_is_free(free, ox, oy, wps[i], wps[i + 1])
                    for i in range(1, len(wps) - 1, 2))

    _, axis_a, _, eigvals = r['axes']
    area = float(free.sum()) * RES * RES
    return dict(
        name      = name, ok=True,
        area      = area,
        cells     = len(r['cells']),
        runs      = r['n_runs'],
        crit      = len(r['critical']),
        axis      = math.degrees(math.atan2(axis_a[1], axis_a[0])),
        ratio     = float(max(eigvals) / min(eigvals)),
        cov       = coverage_ratio(free, ox, oy, wps),
        sweep     = sweep_len,
        link      = link_len,
        bad_sweep = bad_sweep,
        bad_link  = bad_link,
        n_wp      = len(wps),
    )


def detail(name):
    """單一場地的逐掃描帶診斷（用來看 run 碎裂在哪一帶）。"""
    pred, xr, yr = SCENES[name]
    data, ox, oy = build_map(pred, xr, yr)
    safe = apply_safety_margin(data, MARGIN, RES)
    free = (data == 0) & ~safe

    rows, cols = np.where(free)
    pts = np.column_stack([ox + cols * RES, oy + rows * RES])
    center, aa, ab, ev = principal_axes(pts)
    pa, pb = (pts - center) @ aa, (pts - center) @ ab
    nb = int(np.floor((pb.max() - pb.min()) / SPACING)) + 1
    bc = pb.min() + SPACING / 2 + SPACING * np.arange(max(1, nb))

    runs = _slice_runs(free, RES, ox, oy, center, aa, ab,
                       (pa.min(), pa.max()), bc, min_len=RES)
    print(f'\n=== {name} 逐帶診斷 ===')
    print(f'主軸 {math.degrees(math.atan2(aa[1], aa[0])):.2f}°   '
          f'λ比 {max(ev)/min(ev):.2f}   帶數 {nb}   run 總數 {len(runs)}')
    cnt = Counter(x['band'] for x in runs)
    for k in range(nb):
        rr = [x for x in runs if x['band'] == k]
        flag = '  ⚠ 碎裂' if len(rr) > 4 else ''
        segs = ' '.join(f'[{x["a0"]:+.2f},{x["a1"]:+.2f}]' for x in rr[:6])
        more = f' …共 {len(rr)} 段' if len(rr) > 6 else ''
        print(f'  band {k:2d} b={bc[k]:+.3f} runs={len(rr):3d} {segs}{more}{flag}')

    succ, pre = _link_runs(runs)
    cells, crit = _build_cells(runs, succ, pre)
    print(f'cells={len(cells)}  臨界點={crit}')
    print(f'cell 內 run 數分布: {sorted(len(c) for c in cells)}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--detail', metavar='場地名', help='印某個場地的逐帶診斷')
    args = ap.parse_args()

    if args.detail:
        if args.detail not in SCENES:
            print('可用場地：', '、'.join(SCENES))
            return
        detail(args.detail)
        return

    hdr = (f'{"場地":<12}{"面積":>6}{"cell":>5}{"run":>5}{"臨界":>5}'
           f'{"主軸":>8}{"λ比":>7}{"覆蓋率":>8}{"掃描長":>8}{"轉場長":>8}'
           f'{"轉場%":>7}{"穿牆掃":>7}{"穿牆轉":>7}')
    print(hdr)
    print('─' * 96)
    for name in list(SCENES) + [UNKNOWN_SCENE[0]]:
        d = evaluate(name)
        if not d['ok']:
            print(f'{name:<12}  無可走路徑')
            continue
        total = d['sweep'] + d['link']
        print(f'{d["name"]:<12}{d["area"]:>6.1f}{d["cells"]:>5d}{d["runs"]:>5d}'
              f'{d["crit"]:>5d}{d["axis"]:>8.1f}{d["ratio"]:>7.2f}'
              f'{d["cov"]*100:>7.1f}%{d["sweep"]:>8.1f}{d["link"]:>8.1f}'
              f'{d["link"]/total*100:>6.1f}%{d["bad_sweep"]:>7d}{d["bad_link"]:>7d}')


if __name__ == '__main__':
    main()
