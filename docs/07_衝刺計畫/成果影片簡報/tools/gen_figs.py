#!/usr/bin/env python3
"""
成果影片簡報用圖：直接呼叫 scripts/coverage_planner.plan() 產生「真的規劃輸出」，
不是手畫示意。場地取海報實驗場地尺寸（1.35 × 1.2 m＋25.5 × 15 cm 方形障礙），
並把整個房間斜放 30°，模擬車子開機時沒擺正、SLAM 地圖跟著歪掉的情況。

用法：python tools/gen_figs.py        （輸出到 ../assets/）
"""
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'turtlebot3_ccpp', 'scripts'))
from coverage_planner import MARGIN, apply_safety_margin, plan  # noqa: E402

OUT = os.path.join(HERE, '..', 'assets')
RES = 0.05
NAVY, SKY, PALE, ARROW = '#1F4E79', '#b9dcfc', '#e1f1ff', '#8ABAE6'

ROOM_W, ROOM_H = 1.35, 1.20       # 海報實驗場地
OBS_W, OBS_H = 0.255, 0.15        # 方形障礙
TILT = 30                         # 車子斜放角度


def room_map(tilt_deg, scale=1.0, obstacle=True, size=None, obs_size=None, obs_at=(0.12, -0.05)):
    """回傳 (data, ox, oy, pred)：0 自由、100 牆、-1 未知。scale 用來放大場地讓線條更清楚。"""
    W, H = size if size else (ROOM_W * scale, ROOM_H * scale)
    ow, oh = obs_size if obs_size else (OBS_W * scale, OBS_H * scale)
    t = math.radians(tilt_deg)
    c, s = math.cos(t), math.sin(t)

    def inside(X, Y):
        A, B = X * c + Y * s, -X * s + Y * c          # 轉回房間座標
        room = (np.abs(A) <= W / 2) & (np.abs(B) <= H / 2)
        obs = ((np.abs(A - obs_at[0] * W) <= ow / 2) & (np.abs(B - obs_at[1] * H) <= oh / 2)
               if obstacle else np.zeros_like(A, dtype=bool))
        return room & ~obs, room

    R = math.hypot(W, H) / 2 + 0.25
    ox = oy = -R
    n = int(2 * R / RES)
    X, Y = np.meshgrid(ox + RES * np.arange(n), oy + RES * np.arange(n))
    free, room = inside(X, Y)
    data = np.full(free.shape, -1, dtype=np.int16)
    data[free] = 0
    # 牆與障礙：可走區外一圈
    from scipy.ndimage import binary_dilation
    wall = (binary_dilation(room, iterations=1) & ~room) | (room & ~free)   # 外牆一格＋障礙本體
    data[wall] = 100
    return data, ox, oy, (W, H, t)


def draw(ax, data, ox, oy, r, *, show_axis=True, color=NAVY, lw=2.6, bg=None,
         wall_color=NAVY, free_color=PALE, ring_color=ARROW):
    n = data.shape[0]
    ext = (ox, ox + n * RES, oy, oy + n * RES)
    img = np.zeros((*data.shape, 4))
    def rgba(h, a=1):
        h = h.lstrip('#'); return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [a]
    img[data == 0] = rgba(free_color)
    img[data == 100] = rgba(wall_color)
    ax.imshow(img, origin='lower', extent=ext, interpolation='nearest')
    ring = set(map(tuple, r['perimeter']))
    for (p, q) in r['sweeps']:
        is_ring = tuple(p) in ring and tuple(q) in ring
        ax.plot([p[0], q[0]], [p[1], q[1]], color=ring_color if is_ring else color,
                lw=lw * (0.6 if is_ring else 1), solid_capstyle='round')
    wps = r['waypoints']
    kinds = r['kind']
    stop = (max(i for i, kd in enumerate(kinds) if kd == 'move') if r['perimeter'] else len(wps))
    for k in range(1, stop):        # 外圈另外用淡色畫過，這裡只畫到外圈之前
        p, q = wps[k - 1], wps[k]
        if kinds[k] == 'line':      # 換行銜接（掃描線本身已畫過，這裡補上 U 形轉彎）
            ax.plot([p[0], q[0]], [p[1], q[1]], color=color, lw=lw, solid_capstyle='round')
        else:                       # 需要導航的跨區移動
            ax.plot([p[0], q[0]], [p[1], q[1]], color=color, lw=lw * 0.55, ls=(0, (2, 2)))
    if show_axis and r['axes'] is not None:
        c0, a, b, _ = r['axes']
        L = 1.0
        ax.plot([c0[0] - a[0] * L, c0[0] + a[0] * L], [c0[1] - a[1] * L, c0[1] + a[1] * L],
                color=ARROW, lw=1.6, ls=(0, (6, 4)), zorder=0.5)
    ax.set_aspect('equal'); ax.axis('off')


def main():
    os.makedirs(OUT, exist_ok=True)
    stats = []
    for name, tilt, scale in [('path_tilt30', TILT, 1.0), ('path_tilt0', 0, 1.0),
                              ('path_tilt30_big', TILT, 2.2)]:
        data, ox, oy, _ = room_map(tilt, scale)
        safe = apply_safety_margin(data, MARGIN, RES)
        free = (data == 0) & ~safe
        r = plan(free, RES, ox, oy)
        stats.append((name, len(r['cells']), len(r['sweeps']), len(r['waypoints'])))
        fig = plt.figure(figsize=(8, 8), dpi=200)
        ax = fig.add_axes([0, 0, 1, 1])
        draw(ax, data, ox, oy, r)
        fig.savefig(os.path.join(OUT, f'{name}.png'), transparent=True)
        # 深底版本：路徑淡藍、可走區用半透明
        fig2 = plt.figure(figsize=(8, 8), dpi=200)
        ax2 = fig2.add_axes([0, 0, 1, 1])
        draw(ax2, data, ox, oy, r, color=SKY, wall_color=ARROW, free_color='#2a5f8f', ring_color=ARROW)
        fig2.savefig(os.path.join(OUT, f'{name}_dark.png'), transparent=True)
        plt.close('all')
    for s in stats:
        print('%-18s cells=%d sweeps=%d waypoints=%d' % s)


if __name__ == '__main__':
    main()
