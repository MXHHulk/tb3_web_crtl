#!/usr/bin/env python3
"""
測試工具：PCA 主軸 vs 沿地圖 x 軸（對照組）的離線比較（不需要 ROS）。

同一張地圖、同一組參數，只換掃描方向（coverage_planner.plan 的 scan_axis），比較：
  覆蓋率   以車身半寬 COVER_R 計，掃描線＋外圈掃過可走區的比例
  路徑長   所有路點依序連起來的長度（公尺）
  轉彎數   路點之間方向改變 > 30° 的次數（中途點已去掉，只看真正的轉彎）
  cell     分解出的 cell 數

地圖來源
  合成：長方形房間＋置中方形障礙，房間斜置 0/15/30/45°（＝車子開機時沒擺正的角度）
  實測：experiments/robot/data/coverage/*_grid.npz（規劃當下存的可走區）

用法：
  python3 test/pca_vs_axis.py                     # 預設 min_run
  python3 test/pca_vs_axis.py --min-run 0.15      # 比較不同的最短區間
  python3 test/pca_vs_axis.py --sweep-min-run     # 掃 min_run，選碎裂消失且覆蓋率不掉的值
"""
import argparse
import glob
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.realpath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PKG, 'scripts'))
sys.path.insert(0, HERE)

import coverage_planner as cp                     # noqa: E402
from coverage_bench import build_map, _rot        # noqa: E402

RES = 0.05
REPO = os.path.dirname(PKG)
GRID_GLOB = os.path.join(REPO, 'experiments', 'robot', 'data', 'coverage', '*_grid.npz')
ROOMS = [('海報場地1.35x1.2+障礙', 1.35, 1.20, (0.255, 0.15)),
         ('11/11場地1.47x1.06', 1.47, 1.06, None),
         ('長場地2.0x1.0+障礙', 2.0, 1.0, (0.3, 0.2))]
TILTS = (0, 15, 30, 45)


def room(L, W, deg, obs):
    def pred(X, Y):
        A, B = _rot(X, Y, deg)
        m = (np.abs(A) <= L / 2) & (np.abs(B) <= W / 2)
        if obs:
            m &= ~((np.abs(A) < obs[0] / 2) & (np.abs(B) < obs[1] / 2))
        return m
    r = math.hypot(L, W) / 2 + 0.05
    return pred, (-r, r), (-r, r)


def turns(wps, thr=30):
    """路點序列的轉彎數：先去掉共線的中途點，再數方向變化 > thr 度的次數。"""
    n = 0
    for i in range(1, len(wps) - 1):
        h1 = math.atan2(wps[i][1] - wps[i - 1][1], wps[i][0] - wps[i - 1][0])
        h2 = math.atan2(wps[i + 1][1] - wps[i][1], wps[i + 1][0] - wps[i][0])
        if abs(math.degrees((h2 - h1 + math.pi) % (2 * math.pi) - math.pi)) > thr:
            n += 1
    return n


def metrics(free, res, ox, oy, axis, min_run, start):
    r = cp.plan(free, res, ox, oy, start=start, scan_axis=axis, min_run=min_run)
    w = r['waypoints']
    if not w:
        return None
    return {'cov': cp.coverage_ratio(free, res, ox, oy, r['sweeps']),
            'len': sum(math.dist(w[i], w[i + 1]) for i in range(len(w) - 1)),
            'turns': turns(w), 'cells': len(r['cells'])}


def maps():
    for name, L, W, obs in ROOMS:
        for deg in TILTS:
            data, ox, oy = build_map(*room(L, W, deg, obs))
            free = (data == 0) & ~cp.apply_safety_margin(data, cp.MARGIN, RES)
            yield f'{name} 斜{deg}°', free, RES, ox, oy, None
    for g in sorted(glob.glob(GRID_GLOB)):
        z = np.load(g)
        yield 'Real ' + os.path.basename(g)[:15], z['free'], float(z['res']), float(z['ox']), float(z['oy']), None


def run(min_run, verbose=True):
    rows = []
    for name, free, res, ox, oy, start in maps():
        a = metrics(free, res, ox, oy, 'pca', min_run, start)
        b = metrics(free, res, ox, oy, 'map_x', min_run, start)
        if a and b:
            rows.append((name, a, b))
    if verbose:
        print(f'min_run = {min_run} m')
        print(f'{"地圖":<30}| {"PCA 覆蓋/長/轉彎/cell":>26} | {"沿地圖軸 覆蓋/長/轉彎/cell":>26}')
        f = lambda m: f'{m["cov"]*100:5.1f}% {m["len"]:5.2f}m {m["turns"]:3d} {m["cells"]:3d}'
        for name, a, b in rows:
            print(f'{name:<30}| {f(a):>26} | {f(b):>26}')
    return rows


def summary(rows, label):
    tilted = [(a, b) for n, a, b in rows if '斜0°' not in n]
    win = sum(a['turns'] < b['turns'] for a, b in tilted)
    tie = sum(a['turns'] == b['turns'] for a, b in tilted)
    cov_a = np.mean([a['cov'] for _, a, _ in rows]); cov_b = np.mean([b['cov'] for _, _, b in rows])
    frag = max(a['cells'] for _, a, _ in rows)
    print(f'{label}: 斜置／實測 {len(tilted)} 張中 PCA 轉彎較少 {win}、相同 {tie}、較多 {len(tilted) - win - tie}；'
          f'平均覆蓋 PCA {cov_a*100:.1f}% / 軸向 {cov_b*100:.1f}%；PCA 最多 cell {frag}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-run', type=float, default=None)
    ap.add_argument('--sweep-min-run', action='store_true')
    args = ap.parse_args()
    if args.sweep_min_run:
        for mr in (0.05, 0.10, 0.15, 0.20, 0.25):
            summary(run(mr, verbose=False), f'min_run={mr:.2f}')
    else:
        rows = run(args.min_run)
        summary(rows, '\n總結')


if __name__ == '__main__':
    main()
