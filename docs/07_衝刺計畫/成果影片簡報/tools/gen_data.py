#!/usr/bin/env python3
"""
把各鏡要用的「真實規劃結果」匯出成 JSON，給 scenes/*.html 用 SVG 逐筆畫出來（才能做描線動畫）。
所有路徑都來自專案的 coverage_planner.plan()；只有標明「示意」的（舊版掃描線、沿地圖座標軸的掃描線）
是用同一張可走格地圖、照舊做法算出來的對照。

輸出：../assets/scenes.js（window.SCENES = {...}，用 <script> 載入，file:// 也能開）
     ../assets/mapflip/*.png（6/27 實測 gmapping 快照，放大成清楚的像素圖）
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_figs as gf  # noqa: E402  （順便把 scripts/ 加進 sys.path）
from coverage_planner import MARGIN, SPACING, apply_safety_margin, plan  # noqa: E402

OUT = os.path.join(HERE, '..', 'assets')
RES = gf.RES
r3 = lambda v: round(float(v), 3)
pt = lambda p: [r3(p[0]), r3(p[1])]


def grid_of(data, ox, oy):
    """牆格／障礙格左下角座標（公尺）。障礙＝房間內部的佔據格。"""
    occ = data == 100
    # 外牆：佔據格且鄰接未知區；其餘佔據格視為障礙
    unk = data == -1
    from scipy.ndimage import binary_dilation
    wall = occ & binary_dilation(unk)
    obs = occ & ~wall
    cells = lambda m: [[r3(ox + x * RES), r3(oy + y * RES)] for y, x in zip(*np.where(m))]
    return cells(wall), cells(obs)


def free_of(data):
    return (data == 0) & ~apply_safety_margin(data, MARGIN, RES)


def plan_json(free, ox, oy):
    r = plan(free, RES, ox, oy)
    c, a, b, ev = r['axes']
    ys, xs = np.where(free)
    P = np.column_stack([ox + xs * RES, oy + ys * RES]) - c
    pa, pb = P @ a, P @ b                       # 可走格在長軸、短軸上的投影：軸線畫到房間兩端為止
    return {
        'waypoints': [pt(p) + [k] for p, k in zip(r['waypoints'], r['kind'])],
        'cells': [[pt(p) for p in cell] for cell in r['cells']],
        'perimeter': [pt(p) for p in r['perimeter']],
        'axes': {'c': pt(c), 'a': pt(a), 'b': pt(b), 'ratio': r3(max(ev) / min(ev)),
                 'ext': [r3(pa.min()), r3(pa.max()), r3(pb.min()), r3(pb.max())]},
    }


def axis_lines(free, ox, oy, spacing=SPACING, ignore=None):
    """沿地圖 x 軸切掃描線（示意：不做 PCA）。ignore=障礙遮罩時，線直接穿過障礙（舊版做法）。"""
    m = free | ignore if ignore is not None else free
    rows = np.where(m.any(axis=1))[0]
    y0, y1 = rows.min(), rows.max()
    lines = []
    yy = y0 + spacing / RES / 2
    while yy <= y1:
        row = m[int(round(yy))]
        xs = np.where(row)[0]
        if len(xs):
            # 切出連續區間
            splits = np.where(np.diff(xs) > 1)[0]
            starts = np.r_[xs[0], xs[splits + 1]]
            ends = np.r_[xs[splits], xs[-1]]
            if ignore is not None:          # 舊版：整列從頭掃到尾，不管中間有什麼
                starts, ends = xs[:1], xs[-1:]
            for s, e in zip(starts, ends):
                if e - s >= 2:
                    lines.append([[r3(ox + s * RES), r3(oy + yy * RES)], [r3(ox + e * RES), r3(oy + yy * RES)]])
        yy += spacing / RES
    return lines


def bounds(data, ox, oy):
    ys, xs = np.where(data != -1)
    return [r3(ox + xs.min() * RES), r3(oy + ys.min() * RES),
            r3(ox + (xs.max() + 1) * RES), r3(oy + (ys.max() + 1) * RES)]


def scene(data, ox, oy, extra=None):
    wall, obs = grid_of(data, ox, oy)
    d = {'res': RES, 'bounds': bounds(data, ox, oy), 'wall': wall, 'obs': obs}
    d.update(extra or {})
    return d


def main():
    S = {}
    # 01 開場／07 參考：海報場地放大 2.2 倍、斜放 30°、含障礙
    data, ox, oy, _ = gf.room_map(30, 2.2)
    S['cover'] = scene(data, ox, oy, {'plan': plan_json(free_of(data), ox, oy)})

    # 05／06：同一個房間、不含障礙、斜放 30°
    data, ox, oy, _ = gf.room_map(30, 2.2, obstacle=False)
    free = free_of(data)
    ys, xs = np.where(free)
    sub = (ys % 2 == 0) & (xs % 2 == 0)
    S['tilt'] = scene(data, ox, oy, {
        'plan': plan_json(free, ox, oy),
        'axisLines': axis_lines(free, ox, oy),
        'points': [[r3(ox + x * RES), r3(oy + y * RES)] for y, x in zip(ys[sub], xs[sub])],
    })

    # 07／08：2.0 × 1.0 m 場地（開發日誌 2026-08-16 的場地尺寸）＋中央障礙，擺正
    data, ox, oy, _ = gf.room_map(0, size=(2.0, 1.0), obs_size=(0.36, 0.30), obs_at=(0.0, 0.0))
    free = free_of(data)
    obs_mask = (data == 100)
    from scipy.ndimage import binary_dilation
    unk = data == -1
    obs_only = obs_mask & ~binary_dilation(unk)
    obs_zone = binary_dilation(obs_only, iterations=int(MARGIN / RES)) & ~(data == -1)
    S['field'] = scene(data, ox, oy, {
        'plan': plan_json(free, ox, oy),
        'oldLines': axis_lines(free, ox, oy, spacing=0.16, ignore=obs_zone),   # 舊版：障礙區當作可走，線直接穿過
    })

    with open(os.path.join(OUT, 'scenes.js'), 'w', encoding='utf-8') as f:
        f.write('window.SCENES = ' + json.dumps(S, ensure_ascii=False, separators=(',', ':')) + ';\n')
    for k, v in S.items():
        print(k, 'cells', len(v['plan']['cells']), 'wp', len(v['plan']['waypoints']),
              'old' if 'oldLines' in v else '', len(v.get('oldLines', v.get('axisLines', []))))

    # 04：6/27 實測建圖快照 → 放大 8 倍、上色（自由＝深青、佔據＝黃綠、未知＝透明）
    # 原在 turtlebot3_ccpp/maps/（車上產生、不進版控），2026-11-26 整理後備份於 experiments/robot/maps/
    src = sorted(glob.glob(os.path.join(HERE, '..', '..', '..', '..', 'experiments', 'robot', 'maps',
                                        '20260627_150914', '*.png')))
    dst = os.path.join(OUT, 'mapflip'); os.makedirs(dst, exist_ok=True)
    W = max(Image.open(p).size[0] for p in src); H = max(Image.open(p).size[1] for p in src)
    for i, p in enumerate(src):
        g = np.array(Image.open(p).convert('L'))
        rgba = np.zeros((H, W, 4), np.uint8)
        h, w = g.shape
        tile = np.zeros((h, w, 4), np.uint8)
        tile[g > 240] = (30, 78, 86, 255)        # 自由（gmapping：254 自由、205 未知、0 佔據）
        tile[g < 60] = (218, 255, 60, 255)       # 佔據（牆）
        rgba[:h, :w] = tile
        Image.fromarray(rgba, 'RGBA').resize((W * 8, H * 8), Image.NEAREST).save(
            os.path.join(dst, f'{i:02d}.png'))
    print('mapflip', len(src), (W, H))


if __name__ == '__main__':
    main()
