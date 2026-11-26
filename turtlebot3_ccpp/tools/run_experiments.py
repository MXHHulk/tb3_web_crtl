#!/usr/bin/env python3
"""
自動實驗：把車子放在場地裡，自己重複「回起點 → 轉到指定斜角 → 重設里程計＋清空地圖 → 自動建圖 → 覆蓋」，
依設定檔跑完所有條件（PCA vs 沿地圖軸、A* vs DWA），每一輪寫一列到實驗總表。

在車上執行（只用標準函式庫，透過 HTTP 呼叫 map_server :8080）：
  python3 tools/run_experiments.py                              # 用 tools/experiments.json，新開一個實驗
  python3 tools/run_experiments.py --config my.json
  python3 tools/run_experiments.py --resume 20261127-0930       # 換電池／中途停止後從未完成的那一輪接著跑
                                                                 # （先把車放回起點、車頭對齊長邊：接續時以當下位姿為準）
  nohup python3 tools/run_experiments.py > /dev/null 2>&1 &     # 背景執行，筆電斷線也繼續

開始前：
  1. 手機「系統」頁啟動系統（或加 --start-system）。
  2. 車子放在場地中央較空曠處，**車頭對齊場地長邊**——這個朝向是「斜角 0°」的參考，也是每一輪的起點。

每一輪
  1. 用自寫 A*（/nav/goto）開回起點，原地轉到「房間方向＋本輪斜角」。
  2. /slam/restart（reset_odom）：停 SLAM → 重設里程計 → 重啟 SLAM。
     gmapping 的地圖方向＝里程計原點方向，所以新地圖的 x 軸＝車子現在的朝向 → 房間在地圖上斜了「本輪斜角」。
     等地圖長出來（已知面積 ≥ AREA_MIN），20 秒內沒有就再重啟一次（光達偶爾啟動後沒資料，見 2026-11-26 日志）。
  3. /explore/start 自動建圖（explore_lite），完成後它會開回起點。
  4. /coverage/start（nav_mode、scan_axis）並等它結束（完成／受困／逾時）。
  5. 記錄：條件、目標斜角、實際斜角（PCA 量出房間在地圖上的角度）、建圖與覆蓋任務編號、結果、轉彎數、電壓。
     下一輪的「房間方向」用這一輪 PCA 量到的值，避免里程計累積誤差。
受困：記為該輪結果（這就是數據），下一輪開始時嘗試開回起點；回不去就停止整個實驗並保存進度。
電壓低於 batt_min：停在起點、保存進度，換電池後用 --resume 接著跑。

輸出：data/experiments/<實驗編號>/{config.json, trials.csv, log.txt, state.json}
（各輪的建圖、覆蓋原始紀錄仍在 data/explore/、data/coverage/，用 trials.csv 的任務編號對應）
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
PKG = os.path.dirname(HERE)
API = os.environ.get('CCPP_API', 'http://127.0.0.1:8080')          # 測試時可指向假伺服器
LAUNCHER = os.environ.get('CCPP_LAUNCHER', 'http://127.0.0.1:8000')

AREA_MIN = 0.3          # 重啟 SLAM 後已知面積至少這麼大（m²）才算光達正常
MAP_WAIT = 20.0         # 等地圖長出來的秒數
SLAM_TRIES = 3          # 地圖沒長出來時重啟 SLAM 的次數上限
EXPLORE_TIMEOUT = 900   # 自動建圖最長等待（秒，含回起點）
COVER_TIMEOUT = 1200    # 覆蓋最長等待（秒）
NAV_TIMEOUT = 120       # 回起點＋轉向最長等待（秒）

FIELDS = ['trial', 'group', 'rep', 'nav_mode', 'scan_axis', 'tilt_target_deg', 'room_axis_in_map_deg',
          'tilt_actual_deg', 'explore_task', 'explore_state', 'explore_area_m2', 'coverage_task',
          'coverage_state', 'reached', 'total', 'skipped', 'n_stuck', 'n_escape', 'n_turns', 'actual_cov',
          'plan_cov', 'exec_s', 'actual_len', 'plan_len', 'n_cells', 'batt_start_v', 'batt_end_v',
          'version', 'started', 'note']


# ── HTTP ──
def call(path, body=None, base=API, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method='POST' if body is not None else 'GET',
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode() or '{}')
        except ValueError:
            return {'ok': False, 'msg': f'HTTP {e.code}'}


def status():
    return call('/coverage/status')


def wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def axis_deg(a):
    """長軸方向（±180° 等價）正規化到 (-90, 90]。"""
    a = wrap_deg(a)
    if a > 90:
        a -= 180
    elif a <= -90:
        a += 180
    return a


class Runner:
    def __init__(self, cfg, out_dir, state):
        self.cfg, self.out, self.state = cfg, out_dir, state

    # ── 紀錄 ──
    def log(self, msg):
        line = f"{time.strftime('%H:%M:%S')}  {msg}"
        print(line, flush=True)
        with open(os.path.join(self.out, 'log.txt'), 'a', encoding='utf-8') as f:
            f.write(line + '\n')

    def save_state(self):
        with open(os.path.join(self.out, 'state.json'), 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def write_row(self, row):
        path = os.path.join(self.out, 'trials.csv')
        new = not os.path.exists(path)
        with open(path, 'a', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow({k: row.get(k, '') for k in FIELDS})

    # ── 等待 ──
    def wait(self, cond, timeout, period=2.0):
        t_end = time.time() + timeout
        while time.time() < t_end:
            st = status()
            if st and cond(st):
                return st
            time.sleep(period)
        return None

    # ── 步驟 ──
    def goto(self, x, y, yaw_deg):
        r = call('/nav/goto', {'x': x, 'y': y, 'yaw_deg': yaw_deg})
        if not r.get('ok'):
            return False, r.get('msg', '')
        st = self.wait(lambda s: s.get('nav', {}).get('state') != 'running', NAV_TIMEOUT, 1.0)
        if st is None:
            call('/nav/stop', {})
            return False, '逾時'
        nav = st['nav']
        return nav['state'] == 'done', nav.get('msg', '')

    def restart_slam(self):
        for k in range(SLAM_TRIES):
            r = call('/slam/restart', {'reset_odom': True}, timeout=60)
            if not r.get('ok'):
                self.log(f'  SLAM 重啟失敗：{r.get("msg")}')
                time.sleep(5)
                continue
            time.sleep(3)                            # 等舊地圖狀態清掉（map_server 會把面積歸零）
            st = self.wait(lambda s: s.get('pose') is not None
                           and (s.get('explore') or {}).get('area', 0) >= AREA_MIN, MAP_WAIT + 15, 1.0)
            if st is not None:
                pose = st.get('pose')
                self.log(f'  地圖已長出（{st["explore"]["area"]:.2f} m²），里程計重設後位置 {pose}')
                return True
            self.log(f'  ⚠ 第 {k + 1} 次重啟後 {MAP_WAIT:.0f} 秒內地圖沒長出來（光達可能沒資料），再重啟')
        return False

    def explore(self):
        for _ in range(10):                          # 地圖剛出來時可能還沒就緒，等一下再試
            r = call('/explore/start', {})
            if r.get('ok'):
                break
            time.sleep(3)
        if not r.get('ok'):
            return None, f'無法開始建圖：{r.get("msg")}'
        time.sleep(3)
        st = self.wait(lambda s: not (s.get('explore') or {}).get('busy'), EXPLORE_TIMEOUT, 3.0)
        if st is None:
            call('/explore/stop', {})
            return None, '建圖逾時'
        return st['explore'], ''

    def coverage(self, nav_mode, scan_axis):
        for _ in range(5):
            r = call('/coverage/start', {'nav_mode': nav_mode, 'scan_axis': scan_axis}, timeout=60)
            if r.get('ok'):
                break
            time.sleep(3)
        if not r.get('ok'):
            return None, f'無法開始覆蓋：{r.get("msg")}'
        time.sleep(3)
        st = self.wait(lambda s: s.get('state') != 'running', COVER_TIMEOUT, 3.0)
        if st is None:
            call('/coverage/stop', {})
            time.sleep(3)
            st = status()
            return st, '覆蓋逾時，已停止'
        return st, ''

    # ── 一輪 ──
    def trial(self, t):
        S = self.state
        st = status()
        batt = st.get('battery_v')
        row = {'trial': t['trial'], 'group': t['group'], 'rep': t['rep'], 'nav_mode': t['nav_mode'],
               'scan_axis': t['scan_axis'], 'tilt_target_deg': t['tilt_deg'], 'batt_start_v': batt,
               'started': time.strftime('%Y-%m-%d %H:%M:%S')}
        self.log(f"── 第 {t['trial']}/{len(S['schedule'])} 輪：{t['group']} 第 {t['rep']} 次  "
                 f"nav={t['nav_mode']} axis={t['scan_axis']} 斜角={t['tilt_deg']}°  電壓 {batt}")

        # 1. 回起點、轉到「房間方向＋斜角」（兩個等價方向選離目前朝向近的）
        home, room = S['home'], S['room_dir_deg']
        cur = (st.get('pose') or [0, 0, 0])[2]
        target = room + t['tilt_deg']
        if abs(wrap_deg(target + 180 - cur)) < abs(wrap_deg(target - cur)):
            target += 180
        ok, why = self.goto(home[0], home[1], wrap_deg(target))
        if not ok:
            self.log(f'  ✗ 開回起點／轉向失敗：{why} → 停止實驗（請把車移回起點、對齊後用 --resume 接著跑）')
            return 'abort'
        self.log(f'  已在起點 {home}，朝向 {wrap_deg(target):.1f}°')

        # 2. 重設里程計＋清空地圖
        if not self.restart_slam():
            self.log('  ✗ 光達／地圖異常，停止實驗')
            return 'abort'
        S['home'] = [0.0, 0.0]                      # 里程計重設後，起點＝新地圖原點

        # 3. 自動建圖
        ex, why = self.explore()
        if ex is None:
            row.update(explore_state='failed', note=why)
            self.log(f'  ✗ {why}')
            self.write_row(row)
            return 'abort'
        row.update(explore_task=ex.get('task'), explore_state=ex.get('state'),
                   explore_area_m2=ex.get('area'))
        self.log(f"  建圖結束：{ex.get('state')} {ex.get('msg', '')}  面積 {ex.get('area')} m²  回起點 {ex.get('home_result')}")

        # 4. 覆蓋
        st, why = self.coverage(t['nav_mode'], t['scan_axis'])
        if st is None:
            row.update(coverage_state='failed', note=why)
            self.log(f'  ✗ {why}')
            self.write_row(row)
            return 'continue'
        m = st.get('metrics') or {}
        pa = m.get('pca_axis_deg')
        row.update(coverage_task=m.get('task'), coverage_state=m.get('state'), reached=m.get('reached'),
                   total=m.get('total'), skipped=m.get('skipped'), n_stuck=m.get('n_stuck'),
                   n_escape=m.get('n_escape'), n_turns=m.get('n_turns'), actual_cov=m.get('actual_cov'),
                   plan_cov=m.get('plan_cov'), exec_s=m.get('exec_s'), actual_len=m.get('actual_len'),
                   plan_len=m.get('plan_len'), n_cells=m.get('n_cells'), version=m.get('synced'),
                   batt_end_v=st.get('battery_v'), note=why)
        if pa is not None:
            row['room_axis_in_map_deg'] = pa
            row['tilt_actual_deg'] = round(-axis_deg(pa), 1)    # 地圖 x 軸相對房間長邊的角度
            S['room_dir_deg'] = axis_deg(pa)                    # 下一輪以實測的房間方向為準
        self.log(f"  覆蓋結束：{m.get('state')}  {m.get('reached')}/{m.get('total')}  受困 {m.get('n_stuck')}  "
                 f"覆蓋 {m.get('actual_cov')}  轉彎 {m.get('n_turns')}  實際斜角 {row.get('tilt_actual_deg')}°  {why}")
        self.write_row(row)
        return 'continue'

    def run(self):
        S = self.state
        while S['next'] < len(S['schedule']):
            st = status()
            batt = st.get('battery_v') if st else None
            if batt is not None and 5.0 < batt < self.cfg['batt_min']:
                self.log(f'電壓 {batt:.2f} V 低於 {self.cfg["batt_min"]} V：停止，換電池後用 --resume {S["session"]} 接著跑')
                return
            res = self.trial(S['schedule'][S['next']])
            if res == 'abort':
                self.save_state()
                return
            S['next'] += 1
            self.save_state()
        self.log('全部完成')
        self.goto(S['home'][0], S['home'][1], None)


def build_schedule(cfg):
    """每組 repeats 次；組內條件依 ABBA 順序交替（第奇數次反過來），讓電量、時間的影響平均分到各條件。"""
    out, n = [], 0
    for g in cfg['groups']:
        conds = g['conditions']
        for rep in range(1, cfg['repeats'] + 1):
            order = conds if rep % 2 == 1 else list(reversed(conds))
            for c in order:
                n += 1
                out.append({'trial': n, 'group': g['name'], 'rep': rep, 'tilt_deg': g['tilt_deg'],
                            'nav_mode': c.get('nav_mode', 'astar'), 'scan_axis': c.get('scan_axis', 'pca')})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default=os.path.join(HERE, 'experiments.json'))
    ap.add_argument('--resume', metavar='實驗編號')
    ap.add_argument('--start-system', action='store_true', help='先透過控制台啟動系統')
    args = ap.parse_args()

    if args.start_system:
        call('/api/start', {'model': 'burger', 'auto_explore': False}, base=LAUNCHER)
        print('已送出啟動，等系統就緒…', flush=True)
        time.sleep(40)

    st = status()
    if not st or 'state' not in st:
        sys.exit('map_server（:8080）沒有回應：請先在手機啟動系統，或加 --start-system')

    root = os.path.join(PKG, 'data', 'experiments')
    if args.resume:
        out = os.path.join(root, args.resume)
        with open(os.path.join(out, 'state.json'), encoding='utf-8') as f:
            state = json.load(f)
        with open(os.path.join(out, 'config.json'), encoding='utf-8') as f:
            cfg = json.load(f)
        pose = st.get('pose')
        if pose is None:
            sys.exit('查不到機器人位置：請等地圖就緒再執行')
        # 中途停止或換電池後，車子已由人放回起點並對齊長邊（重開系統後舊座標也失效）→ 以現在的位姿為準
        state['home'], state['room_dir_deg'] = [pose[0], pose[1]], pose[2]
        r = Runner(cfg, out, state)
        r.log(f'== 接續實驗 {args.resume}，從第 {state["next"] + 1} 輪開始；起點 {state["home"]}、房間方向（車頭）{pose[2]}° ==')
    else:
        with open(args.config, encoding='utf-8') as f:
            cfg = json.load(f)
        session = time.strftime('%Y%m%d-%H%M')
        out = os.path.join(root, session)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        pose = st.get('pose')
        if pose is None:
            sys.exit('查不到機器人位置：請等地圖就緒再執行')
        state = {'session': session, 'next': 0, 'schedule': build_schedule(cfg),
                 'home': [pose[0], pose[1]], 'room_dir_deg': pose[2]}
        r = Runner(cfg, out, state)
        r.save_state()
        r.log(f'== 新實驗 {session}：共 {len(state["schedule"])} 輪；起點 {state["home"]}、房間方向（車頭）{pose[2]}° ==')
    r.run()


if __name__ == '__main__':
    main()
