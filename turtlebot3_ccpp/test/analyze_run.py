#!/usr/bin/env python3
"""
測試工具：分析一次覆蓋任務的實車紀錄（不需要 ROS）。

讀 data/coverage/<task>_{plan.json, grid.npz, track.csv, path.csv, events.txt}（2026-11-26 之後的任務才有 plan／grid／track），回答：
  1. 直線走得直不直：直線循跡時「車子以為的側偏」、方向誤差、修正角的分佈，以及偏移最大的幾段
  2. 位置有沒有跳：相鄰兩個控制週期（約 50 ms）位置變了 3 cm 以上，就是 SLAM 修正造成的跳動
  3. 有沒有擦撞風險：軌跡上車子中心到「規劃當下地圖」最近障礙格的距離（車身半寬 0.089 m＋半格 0.025 m ≈ 0.114 m 以內就可能碰到）

用法：
  python3 test/analyze_run.py 20261126-113553                       # 預設讀 ../experiments/robot/data/coverage/
  python3 test/analyze_run.py <task> --dir <coverage 紀錄資料夾>
"""
import argparse
import csv
import json
import math
import os

import numpy as np
from scipy.ndimage import distance_transform_edt

HERE = os.path.dirname(os.path.realpath(__file__))
DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'experiments', 'robot', 'data', 'coverage')
TOUCH = 0.089 + 0.025      # 車身半寬＋半格：車中心離障礙格中心小於此值就可能碰到
JUMP_D = 0.03              # 單一控制週期（約 50 ms）位置變化超過此值（公尺）＝0.6 m/s，車子最快 0.12 m/s → SLAM 跳動
                           # （不用速度門檻：t_s 只到 0.01 s，兩列太近時算出的速度會虛高）
CLUSTER = 0.10             # 近障礙點以此距離（公尺）內合併成同一處


def read_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else float('nan')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('task')
    ap.add_argument('--dir', default=DEFAULT_DIR)
    args = ap.parse_args()
    base = os.path.join(args.dir, args.task)

    with open(base + '_events.txt', encoding='utf-8') as f:
        txt = f.read()
    m = json.loads(txt[:txt.index('\n}\n') + 2])
    print(f"任務 {args.task}  nav_mode={m.get('nav_mode')}  版本={m.get('synced')}  狀態={m['state']}")
    print(f"  路點 {m['reached']}/{m['total']}  跳過 {m['skipped']}  受困 {m.get('n_stuck')}  脫困 {m.get('n_escape')}  "
          f"實際覆蓋 {m['actual_cov']*100:.1f}%  時間 {m['exec_s']:.0f}s")

    plan = None
    if os.path.exists(base + '_plan.json'):
        with open(base + '_plan.json', encoding='utf-8') as f:
            plan = json.load(f)
        p = plan['params']
        print(f"  循跡參數：速度 {p['line_v']} m/s、K_HEAD {p['k_head']}、K_CTE {p['k_cte']}、修正角上限 {p['corr_max_deg']}°")

    # 1. 直線循跡品質
    if os.path.exists(base + '_track.csv'):
        tr = read_csv(base + '_track.csv')
        line = [r for r in tr if r['phase'] == 'line']
        cte = np.abs([float(r['cte_cm']) for r in line])
        he = np.abs([float(r['head_err_deg']) for r in line])
        co = np.abs([float(r['corr_deg']) for r in line])
        print(f"\n1. 直線循跡（{len(line)} 個控制週期，約 {len(line)/20:.0f} 秒）")
        print(f"  車子以為的側偏：中位 {np.median(cte):.1f} cm、95% {pct(cte, 95):.1f} cm、最大 {cte.max():.1f} cm")
        print(f"  方向誤差：中位 {np.median(he):.1f}°、90% {pct(he, 90):.1f}°、最大 {he.max():.1f}°")
        print(f"  修正角：中位 {np.median(co):.1f}°、90% {pct(co, 90):.1f}°")
        seg_worst = {}
        for r in line:
            seg_worst[r['segment']] = max(seg_worst.get(r['segment'], 0.0), abs(float(r['cte_cm'])))
        worst = sorted(seg_worst.items(), key=lambda kv: -kv[1])[:5]
        print('  側偏最大的段：' + '；'.join(f'{k}（{v:.1f} cm）' for k, v in worst))

        # 2. 位置跳動
        jumps = []
        for a, b in zip(tr, tr[1:]):
            dt = float(b['t_s']) - float(a['t_s'])
            d = math.hypot(float(b['x']) - float(a['x']), float(b['y']) - float(a['y']))
            if 0 <= dt < 0.5 and d > JUMP_D:
                jumps.append((float(b['t_s']), d * 100))
        ds = np.array([d for _, d in jumps])
        print(f"\n2. 位置跳動（單一控制週期 > {JUMP_D*100:.0f} cm）：{len(jumps)} 次" +
              (f"，中位 {np.median(ds):.1f} cm、最大 {ds.max():.1f} cm；最大幾次："
               + '、'.join(f'{t:.1f}s {d:.1f}cm' for t, d in sorted(jumps, key=lambda j: -j[1])[:6]) if jumps else ''))
    else:
        jumps = []
        print('\n（沒有 _track.csv：2026-11-26 之前的版本未記錄循跡）')

    # 3. 擦撞風險
    if os.path.exists(base + '_grid.npz'):
        g = np.load(base + '_grid.npz')
        clean, res, ox, oy = g['clean'], float(g['res']), float(g['ox']), float(g['oy'])
        occ = distance_transform_edt(clean != 100) * res
        H, W = occ.shape
        # 位置來源：循跡紀錄（20 Hz，只有直線循跡期間）＋行走軌跡（每 5 cm，全程）
        pts = [(float(r['t_s']), float(r['x']), float(r['y']), r['phase']) for r in tr] if os.path.exists(base + '_track.csv') else []
        pts += [(float(r['t_s']), float(r['x']), float(r['y']), 'path') for r in read_csv(base + '_path.csv')]
        dist = []
        for t, x, y, src in pts:
            c, rr = int(round((x - ox) / res)), int(round((y - oy) / res))
            dist.append(occ[rr, c] if 0 <= rr < H and 0 <= c < W else 0.0)
        near = [(p, d) for p, d in zip(pts, dist) if d < TOUCH]
        print(f"\n3. 擦撞風險（規劃當下地圖，{len(pts)} 個位置點）：最近障礙 "
              f"{min(dist) if dist else float('nan'):.3f} m；< {TOUCH:.3f} m 的點 {len(near)} 個")
        spots = []                                   # 依位置合併：[x, y, 最近距離, t 最小, t 最大, {來源}]
        for (t, x, y, src), d in near:
            for sp in spots:
                if math.hypot(x - sp[0], y - sp[1]) < CLUSTER and t - sp[4] < 2.0:   # 同一處、同一次經過
                    sp[2] = min(sp[2], d); sp[3] = min(sp[3], t); sp[4] = max(sp[4], t); sp[5].add(src)
                    break
            else:
                spots.append([x, y, d, t, t, {src}])
        print(f"  共 {len(spots)} 次（{CLUSTER*100:.0f} cm 內、間隔 < 2 秒合併）：")
        for x, y, d, t0, t1, src in sorted(spots, key=lambda s: s[2]):
            jn = [f'{jt:.1f}s {jd:.1f}cm' for jt, jd in jumps if t0 - 1.0 <= jt <= t1 + 1.0]
            print(f"  ({x:+.2f}, {y:+.2f}) 最近 {d:.3f} m，t={t0:.1f}～{t1:.1f}s，{'/'.join(sorted(src))}"
                  + (f"；前後 1 秒內有位置跳動 {', '.join(jn)} → 可能是定位誤差，不一定真的貼近" if jn else ''))
    else:
        print('\n（沒有 _grid.npz：無法用規劃當下的地圖算擦撞風險）')


if __name__ == '__main__':
    main()
