#!/usr/bin/env python3
"""
測試工具：假 ROS 模擬——載入真的 map_server.py，用差速車模型（左右輪各 ±3% 誤差＋雜訊）跑完整覆蓋任務。
  python3 test/sim_coverage.py <地圖.pgm> <astar|movebase> [movebase_stall_prob]
         [--slam-sigma 公尺] [--jump 公尺] [--k-cte K] [--corr-max 度] [--seed N]
  例：python3 test/sim_coverage.py ../experiments/robot/maps/explore_20261111_111919.pgm astar
      python3 test/sim_coverage.py <地圖> astar --slam-sigma 0.015 --jump 0.07 --k-cte 1.0 --corr-max 10
SLAM 位置誤差模型（假設，用來比較循跡參數，不是實測的誤差分佈）：
  --slam-sigma  車子每走 0.3 m（gmapping linearUpdate）地圖座標修正一次，修正量 x、y 各 N(0, σ)、朝向 N(0, σ×20°/m)
  --jump        另外每走約 6 m 出現一次這麼大的跳動（11/26 實測 217 秒內 2 次 6～8 cm）
  --latency     速度指令延遲（秒）：/cmd_vel → OpenCR → 馬達的反應時間（假設值）
輸出多一段「循跡誤差」：直線循跡時，車子以為的側偏 vs 真實位置到該段直線的側偏。
movebase 模式：假 move_base 以直線內插開車；給 stall_prob 時，每個目標有該機率「DWA 不肯動」（模擬 11/11 的僵住）。
/scan 一律回傳無障礙（場地內無動態障礙物）。
⚠ 僵住機率是人為設定，只用來驗證「失敗→脫困→重試→跳過→受困停止」的流程，不是 DWA 實際表現的證據；
  「A* 比 DWA 穩」只能用實車數據證明。紀錄寫到系統暫存資料夾，不會動到 data/。
"""
import math, os, random, sys, tempfile, threading, time, types

PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(PKG, 'scripts'))
sys.path.insert(0, os.path.join(PKG, 'test'))
import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument('map'); _ap.add_argument('mode'); _ap.add_argument('stall_p', nargs='?', type=float, default=0.0)
_ap.add_argument('--slam-sigma', type=float, default=0.0)
_ap.add_argument('--jump', type=float, default=0.0)
_ap.add_argument('--k-cte', type=float, default=None)
_ap.add_argument('--corr-max', type=float, default=None, help='度')
_ap.add_argument('--seed', type=int, default=1)
_ap.add_argument('--scan-axis', default='pca', help='pca／map_x')
_ap.add_argument('--goto-home', action='store_true', help='覆蓋後用 /nav/goto 開回起點並轉到 30°，檢查到達誤差')
_ap.add_argument('--latency', type=float, default=0.0, help='速度指令延遲幾秒才生效（模擬通訊與馬達反應）')
ARGS = _ap.parse_args()
MAP, MODE, STALL_P = ARGS.map, ARGS.mode, ARGS.stall_p
random.seed(ARGS.seed)

# ── 模擬時鐘與車子 ──
SIM = {'t': 0.0, 'x': 0.0, 'y': 0.0, 'yaw': 0.0, 'v': 0.0, 'w': 0.0}
OFS = {'x': 0.0, 'y': 0.0, 'yaw': 0.0, 'dist': 0.0, 'jump_at': 6.0, 'n_jump': 0}   # SLAM 位置誤差狀態
L_ERR, R_ERR = 1.03, 0.97
lock = threading.RLock()


CMDQ = []                                                 # 延遲中的速度指令 [(生效時間, v, w)]


def step(dt):
    with lock:
        while CMDQ and CMDQ[0][0] <= SIM['t']:
            _, SIM['v'], SIM['w'] = CMDQ.pop(0)
        v, w = SIM['v'], SIM['w']
        vl, vr = (v - w * 0.08) * L_ERR, (v + w * 0.08) * R_ERR
        v2, w2 = (vl + vr) / 2, (vr - vl) / 0.16
        w2 += random.gauss(0, 0.01)
        SIM['yaw'] += w2 * dt
        SIM['x'] += v2 * math.cos(SIM['yaw']) * dt
        SIM['y'] += v2 * math.sin(SIM['yaw']) * dt
        SIM['t'] += dt
        OFS['dist'] += abs(v2) * dt
        if ARGS.slam_sigma > 0 and OFS['dist'] >= 0.3:          # gmapping 每走 0.3 m 修正一次
            OFS['dist'] = 0.0
            OFS['x'] = random.gauss(0, ARGS.slam_sigma)
            OFS['y'] = random.gauss(0, ARGS.slam_sigma)
            OFS['yaw'] = random.gauss(0, math.radians(20) * ARGS.slam_sigma)
        OFS['jump_at'] -= abs(v2) * dt
        if ARGS.jump > 0 and OFS['jump_at'] <= 0:
            OFS['jump_at'] = random.uniform(4.0, 8.0)
            a = random.uniform(0, 2 * math.pi)
            OFS['x'] += ARGS.jump * math.cos(a); OFS['y'] += ARGS.jump * math.sin(a); OFS['n_jump'] += 1
        rp = ms.robot_path
        if not rp or math.hypot(SIM['x'] - rp[-1][0], SIM['y'] - rp[-1][1]) > 0.05:
            rp.append([SIM['x'], SIM['y']])


# ── 假 ROS 模組 ──
def mod(name, **kw):
    m = types.ModuleType(name)
    m.__dict__.update(kw)
    sys.modules[name] = m
    return m


class Rate:
    def __init__(self, hz): self.dt = 1.0 / hz
    def sleep(self): step(self.dt)


class Duration:
    def __init__(self, s=0.0): self.s = s


class Any:
    def __init__(self, *a, **k): pass
    def __getattr__(self, k): return Any()
    def __call__(self, *a, **k): return Any()


class Twist:
    def __init__(self):
        self.linear = types.SimpleNamespace(x=0.0, y=0.0, z=0.0)
        self.angular = types.SimpleNamespace(x=0.0, y=0.0, z=0.0)


log = lambda *a, **k: None
class Time:
    def __init__(self, *a): pass
    @staticmethod
    def now(): return 0


rospy = mod('rospy', Rate=Rate, Duration=Duration, Time=Time, get_time=lambda: SIM['t'],
            is_shutdown=lambda: False, loginfo=log, logwarn=log, logerr=log,
            ROSException=Exception, ServiceException=Exception,
            wait_for_service=lambda *a, **k: None, ServiceProxy=lambda *a, **k: (lambda *x, **y: None),
            Publisher=Any, Subscriber=Any, init_node=log, get_param=lambda k, d=None: d)
mod('rospkg', RosPack=lambda: (_ for _ in ()).throw(sys.modules['rospkg'].ResourceNotFound()),
    ResourceNotFound=type('RNF', (Exception,), {}))
mod('tf2_ros', LookupException=Exception, ConnectivityException=Exception, ExtrapolationException=Exception,
    Buffer=Any, TransformListener=Any)
mod('geometry_msgs'); mod('geometry_msgs.msg', PoseStamped=Any, Twist=Twist)
mod('nav_msgs'); mod('nav_msgs.msg', OccupancyGrid=Any)
mod('rosgraph_msgs'); mod('rosgraph_msgs.msg', Log=Any)
mod('sensor_msgs'); mod('sensor_msgs.msg', BatteryState=Any, LaserScan=Any)
mod('std_srvs'); mod('std_srvs.srv', Empty=Any)
mod('std_msgs'); mod('std_msgs.msg', Empty=Any)
mod('actionlib_msgs'); mod('actionlib_msgs.msg', GoalStatus=types.SimpleNamespace(SUCCEEDED=3))


class Goal:
    def __init__(self):
        p = types.SimpleNamespace(position=types.SimpleNamespace(x=0, y=0),
                                  orientation=types.SimpleNamespace(z=0, w=1))
        self.target_pose = types.SimpleNamespace(header=types.SimpleNamespace(), pose=p)


MB = {'goals': 0, 'stalls': 0}


class Client:
    """假 move_base：轉向目標→直線開過去；stall 時原地不動（DWA 判定會撞）。"""
    def __init__(self, *a): self.goal = None; self.state = 0; self.stall = False
    def wait_for_server(self, *a): return True
    def send_goal(self, g):
        self.goal = (g.target_pose.pose.position.x, g.target_pose.pose.position.y)
        self.state = 1
        self.stall = random.random() < STALL_P
        MB['goals'] += 1; MB['stalls'] += self.stall
    def cancel_all_goals(self):
        self.goal = None
        with lock: SIM['v'] = SIM['w'] = 0.0
    cancel_goal = cancel_all_goals
    def get_state(self): return self.state
    def wait_for_result(self, d):
        t_end = SIM['t'] + d.s
        while SIM['t'] < t_end:
            if self.goal is None:
                return True
            if self.stall:
                with lock: SIM['v'] = SIM['w'] = 0.0
                step(0.05); continue
            gx, gy = self.goal
            dx, dy = gx - SIM['x'], gy - SIM['y']
            if math.hypot(dx, dy) < 0.05:
                with lock: SIM['v'] = SIM['w'] = 0.0
                self.state, self.goal = 3, None
                return True
            e = math.atan2(math.sin(math.atan2(dy, dx) - SIM['yaw']), math.cos(math.atan2(dy, dx) - SIM['yaw']))
            with lock:
                SIM['w'] = max(-1.0, min(1.0, 2.0 * e))
                SIM['v'] = 0.0 if abs(e) > 0.5 else min(0.15, math.hypot(dx, dy))
            step(0.05)
        return False


mod('actionlib', SimpleActionClient=Client)
mod('move_base_msgs'); mod('move_base_msgs.msg', MoveBaseAction=Any, MoveBaseGoal=Goal)

import map_server as ms                                   # noqa: E402
from astar_bench import load_pgm                          # noqa: E402

OUT = tempfile.mkdtemp(prefix='ccpp_sim_')
ms.RUN_LOG = os.path.join(OUT, 'sim_runs.csv')
ms.PKG = OUT                                              # 紀錄寫到暫存資料夾
print('紀錄資料夾：', os.path.join(OUT, 'data', 'coverage'))
ms._robot_pose = lambda fid: (SIM['x'] + OFS['x'], SIM['y'] + OFS['y'], SIM['yaw'] + OFS['yaw'])
TRUE_LINE = []                                            # (以為的側偏 m, 真實側偏 m, 方向誤差°, 修正角°)
_track_orig = ms._track


def _track_spy(phase, pose, cte, eh, corr, v, w, seg):
    _track_orig(phase, pose, cte, eh, corr, v, w, seg)
    if phase == 'line':
        a, b = seg.split('>')
        x0, y0 = map(float, a.split(',')); x1, y1 = map(float, b.split(','))
        L = math.hypot(x1 - x0, y1 - y0) or 1e-9
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        tc = -(SIM['x'] - x0) * uy + (SIM['y'] - y0) * ux
        TRUE_LINE.append((cte, tc, math.degrees(eh), math.degrees(corr)))


ms._track = _track_spy
if ARGS.k_cte is not None:
    ms.LINE_K_CTE = ARGS.k_cte
if ARGS.corr_max is not None:
    ms.LINE_CORR_MAX = math.radians(ARGS.corr_max)
ms._scan_min = lambda heading, half_width=0: float('inf')


class Pub:
    def publish(self, tw):
        with lock:
            if ARGS.latency > 0:
                CMDQ.append((SIM['t'] + ARGS.latency, tw.linear.x, tw.angular.z))
            else:
                SIM['v'], SIM['w'] = tw.linear.x, tw.angular.z


ms.cmd_pub = Pub()

data, res, ox, oy = load_pgm(MAP)
import numpy as np                                        # noqa: E402
free0 = np.argwhere(data == 0)
cy, cx = free0.mean(axis=0)
SIM['x'], SIM['y'] = ox + cx * res, oy + cy * res        # 起點：可走區重心附近
with ms.map_lock:
    ms.map_meta.update(resolution=res, origin_x=ox, origin_y=oy, r0=0, c0=0, crop_h=data.shape[0])
    ms.map_data.update(data=data, h=data.shape[0], w=data.shape[1], frame_id='map')
ms.robot_pos.update(x=SIM['x'], y=SIM['y'])

c = ms.app.test_client()
r = c.post('/coverage/start', json={'nav_mode': MODE, 'scan_axis': ARGS.scan_axis}).get_json()
HOME = (SIM['x'], SIM['y'])
assert r['ok'], r
wall0 = time.time()
while True:
    time.sleep(0.2)
    st = c.get('/coverage/status').get_json()
    if st['state'] != 'running' and time.time() - wall0 > 1:
        break
    if time.time() - wall0 > 600:
        print('模擬逾時'); break
time.sleep(0.5)
M = st['metrics']
ev = [t for _, t in ms.cov_rec['events']]
cnt = lambda k: sum(k in e for e in ev)
print(f"{os.path.basename(MAP)}  mode={MODE}  stall_p={STALL_P}  state={M['state']}")
print(f"  路點 {M['reached']}/{M['total']}  跳過 {M['skipped']}  受困 {M['n_stuck']}  脫困 {M['n_escape']}"
      f"  實際覆蓋 {M['actual_cov']*100:.1f}%（規劃 {M['plan_cov']*100:.1f}%）  模擬時間 {M['exec_s']:.0f}s(牆鐘)/{SIM['t']:.0f}s(模擬)")
print(f"  A* 規劃 {cnt('A* 路線')} 次、A* 失敗 {cnt('A* 算不出')} 次；move_base 目標 {MB['goals']}（僵住 {MB['stalls']}）")
modes = {}
for _, wp, m, *_ in ms.cov_rec['timeline']:
    modes[m] = modes.get(m, 0) + 1
print('  timeline 控制方式：', modes, ' synced=', M.get('synced'))

# ── 循跡誤差：直線循跡每個控制週期，比較「車子以為的側偏」與「真實側偏」 ──
line_rows = [r for r in TRUE_LINE]
seen = np.abs(np.array([r[0] for r in line_rows] or [0.0]))
true = np.abs(np.array([r[1] for r in line_rows] or [0.0]))
head = np.abs(np.array([r[2] for r in line_rows] or [0.0]))
corr = np.abs(np.array([r[3] for r in line_rows] or [0.0]))
print(f"  SLAM 誤差 σ={ARGS.slam_sigma} m、跳動 {OFS['n_jump']} 次（{ARGS.jump} m）；K_CTE={ms.LINE_K_CTE} 修正角上限={math.degrees(ms.LINE_CORR_MAX):.0f}°")
print(f"  直行 {len(line_rows)} 個控制週期｜車子以為的側偏 中位 {np.median(seen)*100:.1f} / 95% {np.percentile(seen,95)*100:.1f} cm"
      f"｜真實側偏 中位 {np.median(true)*100:.1f} / 95% {np.percentile(true,95)*100:.1f} / 最大 {true.max()*100:.1f} cm")
print(f"  方向誤差 中位 {np.median(head):.1f}° / 90% {np.percentile(head,90):.1f}°｜修正角 90% {np.percentile(corr,90):.1f}°")

print(f"  scan_axis={M.get('scan_axis')}  房間主軸（PCA）={M.get('pca_axis_deg')}°  轉彎數={M.get('n_turns')}  cell={M.get('n_cells')}")
if ARGS.goto_home:
    r = c.post('/nav/goto', json={'x': HOME[0], 'y': HOME[1], 'yaw_deg': 30}).get_json()
    assert r['ok'], r
    while c.get('/coverage/status').get_json()['nav']['state'] == 'running':
        time.sleep(0.2)
    nav = c.get('/coverage/status').get_json()['nav']
    err = math.hypot(SIM['x'] + OFS['x'] - HOME[0], SIM['y'] + OFS['y'] - HOME[1])
    yaw_e = math.degrees(math.atan2(math.sin(SIM['yaw'] + OFS['yaw'] - math.radians(30)), math.cos(SIM['yaw'] + OFS['yaw'] - math.radians(30))))
    print(f"  /nav/goto 回起點：{nav['state']} {nav.get('msg','')}  位置誤差 {err*100:.1f} cm、朝向誤差 {yaw_e:.1f}°")
