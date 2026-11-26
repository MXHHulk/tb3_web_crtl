#!/usr/bin/env python3
"""
測試工具：假 ROS 模擬——載入真的 map_server.py，用差速車模型（左右輪各 ±3% 誤差＋雜訊）跑完整覆蓋任務。
  python3 test/sim_coverage.py <地圖.pgm> <astar|movebase> [movebase_stall_prob]
  例：python3 test/sim_coverage.py ../experiments/robot/maps/explore_20261111_111919.pgm astar
movebase 模式：假 move_base 以直線內插開車；給 stall_prob 時，每個目標有該機率「DWA 不肯動」（模擬 11/11 的僵住）。
/scan 一律回傳無障礙（場地內無動態障礙物）。
⚠ 僵住機率是人為設定，只用來驗證「失敗→脫困→重試→跳過→受困停止」的流程，不是 DWA 實際表現的證據；
  「A* 比 DWA 穩」只能用實車數據證明。紀錄寫到系統暫存資料夾，不會動到 data/。
"""
import math, os, random, sys, tempfile, threading, time, types

PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(PKG, 'scripts'))
sys.path.insert(0, os.path.join(PKG, 'test'))
MAP, MODE = sys.argv[1], sys.argv[2]
STALL_P = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
random.seed(1)

# ── 模擬時鐘與車子 ──
SIM = {'t': 0.0, 'x': 0.0, 'y': 0.0, 'yaw': 0.0, 'v': 0.0, 'w': 0.0}
L_ERR, R_ERR = 1.03, 0.97
lock = threading.RLock()


def step(dt):
    with lock:
        v, w = SIM['v'], SIM['w']
        vl, vr = (v - w * 0.08) * L_ERR, (v + w * 0.08) * R_ERR
        v2, w2 = (vl + vr) / 2, (vr - vl) / 0.16
        w2 += random.gauss(0, 0.01)
        SIM['yaw'] += w2 * dt
        SIM['x'] += v2 * math.cos(SIM['yaw']) * dt
        SIM['y'] += v2 * math.sin(SIM['yaw']) * dt
        SIM['t'] += dt
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
ms._robot_pose = lambda fid: (SIM['x'], SIM['y'], SIM['yaw'])
ms._scan_min = lambda heading, half_width=0: float('inf')


class Pub:
    def publish(self, tw):
        with lock:
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
r = c.post('/coverage/start', json={'nav_mode': MODE}).get_json()
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
