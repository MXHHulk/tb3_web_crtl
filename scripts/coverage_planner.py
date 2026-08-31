#!/usr/bin/env python3
"""
牛耕式覆蓋路徑規劃核心演算法（無 ROS 依賴，可被多個節點共用）

流程：
  1. apply_safety_margin  障礙物形態學膨脹，得到可走格
  2. principal_axes       對可走格做 PCA，取長軸（掃描方向）與短軸（換行方向）
  3. _slice_runs          沿短軸切掃描帶，對每條帶的中心線取樣，切出連續可走區間
  4. _build_cells         區間數改變處即為臨界點，把空間分解成數個 cell
  5. plan                 每個 cell 各自蛇行，再以貪婪最近鄰決定 cell 走訪順序
"""
import numpy as np
from scipy.ndimage import binary_dilation

SPACING = 0.18   # 掃描線間距（公尺）；覆蓋寬度 ≈ 0.20 m，留 10% 重疊
MARGIN  = 0.10   # 障礙物安全邊距（公尺） ≈ 機器人半徑（直徑 0.20 m）


def apply_safety_margin(data, margin, resolution):
    """
    對障礙物套用安全邊距膨脹，確保路徑遠離牆面。

    輸入
      data       : OccupancyGrid 陣列（0=自由, 100=障礙, -1=未知）
      margin     : 安全邊距（公尺）
      resolution : 地圖解析度（公尺/格）
    輸出
      bool 陣列，True = 膨脹後的障礙（含安全邊距）
    """
    obs = data == 100
    r = max(1, round(margin / resolution))
    kern = np.ones((2 * r + 1, 2 * r + 1), dtype=bool)
    return binary_dilation(obs, structure=kern)


def principal_axes(pts):
    """
    對點集做 PCA，回傳 (重心, 長軸, 短軸, 特徵值)。

    共變異數矩陣為實對稱半正定，由譜定理保證特徵向量正交，
    因此長軸（掃描方向）與短軸（換行方向）天生垂直，不必額外正交化。
    特徵向量的正負號不唯一（v 與 −v 等價），固定長軸 x 分量、短軸 y 分量為正，
    讓同一張地圖每次規劃都得到完全相同的結果。
    """
    center = pts.mean(axis=0)
    diffs  = pts - center
    eigvals, eigvecs = np.linalg.eigh(np.cov(diffs.T))
    axis_a = eigvecs[:, np.argmax(eigvals)]   # sweep 方向（長軸）
    axis_b = eigvecs[:, np.argmin(eigvals)]   # step  方向（短軸）
    if axis_a[0] < 0:
        axis_a = -axis_a
    if axis_b[1] < 0:
        axis_b = -axis_b
    return center, axis_a, axis_b, eigvals


def _true_runs(flags):
    """把布林序列切成連續 True 的區塊，回傳 [(起始索引, 結束索引), ...]（含端點）。"""
    out, s = [], None
    for i, v in enumerate(flags):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s, i - 1))
            s = None
    if s is not None:
        out.append((s, len(flags) - 1))
    return out


def _slice_runs(free, res, ox, oy, center, axis_a, axis_b,
                a_range, b_centers, min_len):
    """
    對每條掃描帶的中心線取樣，切出「連續可走區間」（run）。

    這是牛耕式分解的關鍵一步。舊版只取整條帶的投影極值當兩端，等於假設帶內永遠連通，
    房間有障礙物時就會畫出橫跨障礙的線段；改成沿中心線取樣後，
    區間端點必定落在可走格上，線段也必定整條位於可走區內。

    輸出 runs：[{'band': 帶序號, 'a0': 起點沿長軸座標, 'a1': 終點沿長軸座標,
                 'p0': 起點世界座標, 'p1': 終點世界座標}, ...]
    """
    H, W = free.shape
    # 取樣步長取 1/8 格（≈6 mm）。步長接近一格時，斜向掃描線會從障礙格的角落
    # 「跨」過去而沒被偵測到；實測 res/2 會漏掉約 11 mm 的切角，res/8 則不會。
    # （曾試過「四個包夾格全可走」的保守判定，雖然完全杜絕切角，但會把只有兩格寬
    #   的窄通道整條刪掉，平均覆蓋率從 99% 掉到 89%，代價過大，故不採用。）
    step = res / 8.0
    a_lo, a_hi = a_range
    n = int(np.ceil((a_hi - a_lo) / step)) + 1
    a_s = a_lo + step * np.arange(n)

    runs = []
    for k, b in enumerate(b_centers):
        # 中心線上每個取樣點的世界座標 → 最近的格
        pl = center + a_s[:, None] * axis_a + b * axis_b
        c = np.round((pl[:, 0] - ox) / res).astype(int)
        r = np.round((pl[:, 1] - oy) / res).astype(int)
        inb = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        ok = np.zeros(n, dtype=bool)
        ok[inb] = free[r[inb], c[inb]]

        for i0, i1 in _true_runs(ok):
            if a_s[i1] - a_s[i0] < min_len:       # 太短的碎片不值得跑一趟
                continue
            runs.append({'band': k, 'a0': a_s[i0], 'a1': a_s[i1],
                         'p0': center + a_s[i0] * axis_a + b * axis_b,
                         'p1': center + a_s[i1] * axis_a + b * axis_b})
    return runs


def _link_runs(runs):
    """
    相鄰兩條掃描帶之間，沿長軸投影範圍有重疊的區間視為相接。

    這是牛耕式分解的標準連通判準：掃描線掃過時，區間一分為二即為分裂臨界點，
    二合為一即為合併臨界點。
    """
    succ = [set() for _ in runs]
    pred = [set() for _ in runs]
    for i, ri in enumerate(runs):
        for j, rj in enumerate(runs):
            if rj['band'] != ri['band'] + 1:
                continue
            if ri['a0'] <= rj['a1'] and rj['a0'] <= ri['a1']:
                succ[i].add(j)
                pred[j].add(i)
    return succ, pred


def _build_cells(runs, succ, pred):
    """
    把區間串成 cell：只有「前後一對一」才繼續延伸，一分為多或多合為一即為臨界點。

    輸出
      cells    : [[run 序號, ...], ...]，每個 cell 內的區間依掃描帶順序排列
      critical : [(run 序號, 'split'/'merge'), ...]
    """
    critical = []
    for i in range(len(runs)):
        if len(succ[i]) > 1:
            critical.append((i, 'split'))
        if len(pred[i]) > 1:
            critical.append((i, 'merge'))

    cells, taken = [], [False] * len(runs)
    for i in range(len(runs)):                    # runs 已依帶序號遞增排列
        if taken[i]:
            continue
        # 若自己是某個前段的唯一後繼，代表會被那條鏈接走，不另起新 cell
        if len(pred[i]) == 1:
            p = next(iter(pred[i]))
            if len(succ[p]) == 1:
                continue

        chain, cur = [i], i
        taken[i] = True
        while len(succ[cur]) == 1:
            nxt = next(iter(succ[cur]))
            if len(pred[nxt]) != 1 or taken[nxt]:
                break
            chain.append(nxt)
            taken[nxt] = True
            cur = nxt
        cells.append(chain)

    return cells, critical


def _cell_waypoints(chain, runs, reverse, flip):
    """
    產生單一 cell 的蛇行路點。

    reverse : 帶的走訪方向反過來（從最後一條帶往回掃）
    flip    : 第一條掃描線從哪一側開始
    交替旗標每產生一條線就翻轉，確保是蛇行而不是每條都從同一側重新開始。
    """
    order = chain[::-1] if reverse else chain
    wps, l2r = [], not flip
    for i in order:
        r = runs[i]
        p0, p1 = (r['p0'], r['p1']) if l2r else (r['p1'], r['p0'])
        wps += [(float(p0[0]), float(p0[1])), (float(p1[0]), float(p1[1]))]
        l2r = not l2r
    return wps


def plan(free, res, ox, oy, spacing=SPACING, start=None):
    """
    完整的覆蓋路徑規劃，回傳含診斷資訊的 dict。

    輸入
      free    : 2-D bool 陣列，True = 可行走
      res     : 地圖解析度（公尺/格）
      ox, oy  : 地圖原點世界座標（公尺）
      spacing : 掃描線間距（公尺）
      start   : (x, y) 機器人起點世界座標；None 則從短軸投影最小的一端開始
    輸出 dict
      waypoints : [(x, y), ...] 依序走訪的路點
      cells     : [[(x, y), ...], ...] 各 cell 的路點，已依走訪順序排列
      axes      : (重心, 長軸, 短軸, 特徵值)
      n_runs    : 連續可走區間總數
      critical  : 臨界點清單 [(run 序號, 'split'/'merge'), ...]
    """
    empty = {'waypoints': [], 'cells': [], 'axes': None,
             'n_runs': 0, 'critical': []}

    rows, cols = np.where(free)
    if len(rows) < 3:
        return empty

    pts = np.column_stack([ox + cols.astype(float) * res,
                           oy + rows.astype(float) * res])

    # ── 1. PCA：由環境自己決定掃描方向 ────────────────
    center, axis_a, axis_b, eigvals = principal_axes(pts)
    diffs  = pts - center
    proj_a = diffs @ axis_a
    proj_b = diffs @ axis_b

    # ── 2. 切帶並沿中心線取樣，得到連續可走區間 ───────
    b_min, b_max = proj_b.min(), proj_b.max()
    n_bands   = int(np.floor((b_max - b_min) / spacing)) + 1
    b_centers = b_min + spacing / 2 + spacing * np.arange(max(1, n_bands))

    runs = _slice_runs(free, res, ox, oy, center, axis_a, axis_b,
                       (proj_a.min(), proj_a.max()), b_centers, min_len=res)
    if not runs:
        return empty

    # ── 3. 區間數變化處即為臨界點，串成 cell ──────────
    succ, pred      = _link_runs(runs)
    cells, critical = _build_cells(runs, succ, pred)

    # ── 4. 貪婪最近鄰決定 cell 走訪順序與進入方向 ─────
    cur = (np.asarray(start, dtype=float) if start is not None
           else pts[np.lexsort((proj_a, proj_b))[0]])

    remaining, ordered, waypoints = set(range(len(cells))), [], []
    while remaining:
        best, best_d = None, None
        for ci in remaining:
            for reverse in (False, True):
                for flip in (False, True):
                    wps = _cell_waypoints(cells[ci], runs, reverse, flip)
                    d = float(np.hypot(*(np.asarray(wps[0]) - cur)))
                    if best_d is None or d < best_d:
                        best, best_d = (ci, wps), d
        ci, wps = best
        remaining.discard(ci)
        ordered.append(wps)
        waypoints += wps
        cur = np.asarray(wps[-1], dtype=float)

    return {'waypoints': waypoints,
            'cells': ordered,
            'axes': (center, axis_a, axis_b, eigvals),
            'n_runs': len(runs),
            'critical': critical}


def boustrophedon(free, res, ox, oy, spacing=SPACING, start=None):
    """
    在可走格（free=True）上計算牛耕路點，以 PCA 自動對齊空間主軸，
    並依掃描帶連通性把空間分解成數個 cell 後逐一覆蓋。

    輸出
      [(world_x, world_y), ...] 依序走訪的路點列表
    """
    return plan(free, res, ox, oy, spacing=spacing, start=start)['waypoints']
