#!/usr/bin/env python3
"""
測試工具：自寫 A*（scripts/astar.py）離線驗證（不需要 ROS、不需要機器人）。

地圖：experiments/robot/maps/ 裡的實測地圖（explore_*.pgm/.yaml）＋合成場地（含方形障礙、需要繞路）。
可走區的算法與 map_server 開始覆蓋時相同：去雜點 → 安全邊距 → free。

每張圖在可走區內隨機取 N 組起終點（固定亂數種子，可重現），檢查：
  找到率     同一連通區內的起終點都必須找到路線（⚠ 必須 100%）
  穿牆段     簡化後的路線段整段落在可走區內（頭尾吸附段除外）（⚠ 必須為 0）
  中段離障礙 路線中段（離起終點各 0.15 m 以外）車子中心到最近障礙格的距離：最小值與中位數。
             可走區已扣 0.10 m 安全邊距，所以最小值 ≥ 約 0.10 m；越大越不容易擦牆
  繞路比     路線長 / 直線距離
  耗時       每次規劃的毫秒數（樹莓派大約再慢 5～10 倍）

用法：
  python3 test/astar_bench.py
  python3 test/astar_bench.py --n 200
"""
import argparse
import glob
import math
import os
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt, label

HERE = os.path.dirname(os.path.realpath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PKG, 'scripts'))

from astar import plan_path                                           # noqa: E402
from coverage_planner import MARGIN, apply_safety_margin, remove_noise, _seg_free   # noqa: E402

REPO = os.path.dirname(PKG)
MAP_DIR = os.path.join(REPO, 'experiments', 'robot', 'maps')


def load_pgm(path):
    """map_saver 的 pgm/yaml → (OccupancyGrid 風格 int16 陣列, res, ox, oy)。第 0 列＝y 最小。"""
    meta = {}
    with open(path[:-4] + '.yaml', encoding='utf-8') as f:
        for line in f:
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
    res = float(meta['resolution'])
    ox, oy = [float(t) for t in meta['origin'].strip('[]').split(',')[:2]]
    with open(path, 'rb') as f:
        assert f.readline().strip() == b'P5'
        line = f.readline()
        while line.startswith(b'#'):
            line = f.readline()
        w, h = map(int, line.split())
        int(f.readline())
        img = np.frombuffer(f.read(w * h), dtype=np.uint8).reshape(h, w)
    img = np.flipud(img)
    data = np.full(img.shape, -1, dtype=np.int16)
    data[img >= 250] = 0
    data[img <= 50] = 100
    return data, res, ox, oy


def synth(name):
    """合成場地（解析度 0.05 m）：牆外一圈障礙，中間方形障礙。"""
    res = 0.05
    if name == '海報場地1.35x1.2+障礙':
        W, H, obs = 1.35, 1.20, [(0.55, 0.52, 0.255, 0.15)]
    elif name == '長廊2.0x1.0+雙障礙':
        W, H, obs = 2.0, 1.0, [(0.6, 0.0, 0.2, 0.65), (1.2, 0.35, 0.2, 0.65)]   # 交錯，強迫 S 形繞路
    else:
        raise KeyError(name)
    pad = 0.3
    nx, ny = int((W + 2 * pad) / res), int((H + 2 * pad) / res)
    X, Y = np.meshgrid(-pad + res * np.arange(nx), -pad + res * np.arange(ny))
    inside = (X >= 0) & (X <= W) & (Y >= 0) & (Y <= H)
    for x0, y0, w, h in obs:
        inside &= ~((X >= x0) & (X <= x0 + w) & (Y >= y0) & (Y <= y0 + h))
    data = np.where(inside, 0, 100).astype(np.int16)
    return data, res, -pad, -pad


def evaluate(name, data, res, ox, oy, n, rng):
    clean, _ = remove_noise(data)
    free = (clean == 0) & ~apply_safety_margin(clean, MARGIN, res)
    lab, _ = label(free, structure=np.ones((3, 3)))
    rows, cols = np.where(free)
    obs_d = distance_transform_edt(clean == 0) * res     # 到最近障礙／未知格的距離
    world = lambda r, c: (ox + c * res, oy + r * res)

    found = need = bad = 0
    detours, mins, ms = [], [], []
    for _ in range(n):
        i, j = rng.integers(len(rows), size=2)
        s, g = world(rows[i], cols[i]), world(rows[j], cols[j])
        same = lab[rows[i], cols[i]] == lab[rows[j], cols[j]]
        t0 = time.perf_counter()
        r = plan_path(free, res, ox, oy, s, g)
        ms.append((time.perf_counter() - t0) * 1000)
        need += same
        if r['path'] is None:
            continue
        found += same
        p = r['path']
        bad += sum(not _seg_free(free, res, ox, oy, p[k], p[k + 1]) for k in range(len(p) - 1))
        L = sum(math.dist(p[k], p[k + 1]) for k in range(len(p) - 1))
        d = math.dist(s, g)
        if d > 0.2:
            detours.append(L / d)
        # 沿路線每 1 cm 取樣，量中段（離起終點 > 0.15 m）車子中心到最近障礙的距離
        for k in range(len(p) - 1):
            a, b = np.array(p[k]), np.array(p[k + 1])
            for t in np.linspace(0, 1, max(2, int(math.dist(p[k], p[k + 1]) / 0.01))):
                q = a + t * (b - a)
                if min(math.dist(q, s), math.dist(q, g)) <= 0.15:
                    continue
                rr, cc = int(round((q[1] - oy) / res)), int(round((q[0] - ox) / res))
                mins.append(obs_d[rr, cc])
    area = free.sum() * res * res
    print(f'{name:<26}{area:>6.2f}{n:>6}{(found / need * 100 if need else 100):>8.1f}%{bad:>6}'
          f'{(min(mins) if mins else float("nan")):>9.3f}{(np.median(mins) if mins else float("nan")):>9.3f}'
          f'{(np.median(detours) if detours else float("nan")):>8.2f}{(max(detours) if detours else float("nan")):>8.2f}'
          f'{np.median(ms):>8.1f}{max(ms):>8.1f}')
    return found == need and bad == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=100, help='每張圖隨機起終點組數')
    args = ap.parse_args()
    rng = np.random.default_rng(0)

    print(f'{"地圖":<24}{"面積m²":>6}{"組數":>5}{"找到率":>8}{"穿牆":>5}'
          f'{"中段離障礙min":>7}{"中位":>6}{"繞路中位":>5}{"繞路最大":>5}{"ms中位":>6}{"ms最大":>5}')
    print('─' * 104)
    ok = True
    for name in ('海報場地1.35x1.2+障礙', '長廊2.0x1.0+雙障礙'):
        ok &= evaluate(name, *synth(name), args.n, rng)
    for path in sorted(glob.glob(os.path.join(MAP_DIR, 'explore_*.pgm'))):
        ok &= evaluate(os.path.basename(path)[:-4], *load_pgm(path), args.n, rng)
    print('\n' + ('✓ 全部通過：同連通區都找得到路線、無穿牆段' if ok else '✗ 有失敗項目'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
