#!/usr/bin/env python3
"""
TurtleBot3 地圖伺服器（Module A）
  - 訂閱 /map  → 提供原始 / 侵蝕 / 顯示膨脹 / 規劃安全邊距 四種地圖 PNG
  - TF map → base_footprint → 機器人位置與行走軌跡（地圖座標，已含 SLAM 修正）
  - /coverage/start|resume|stop|status → 牛耕式路徑規劃 + move_base 執行，並回傳 cell 分解結果
  - /teleop                     → 手動遙控（與覆蓋執行互斥）
  - /slam/restart               → 重啟 SLAM 重新建圖（本節點負責 SLAM 的生命週期）
路徑規劃核心由 coverage_planner 模組提供。

模式互斥規則（單一真相來源＝cov_status['state']）：
  state == 'running'  → 覆蓋執行中，手動遙控被拒絕
  其他狀態            → 可手動遙控
按下停止、覆蓋完成、或發生錯誤都會離開 running，自動切回可手動。
"""
import csv, io, math, os, signal, socket, subprocess, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from coverage_planner import (plan as plan_coverage, SPACING as COV_SPACING,
                              MARGIN as COV_MARGIN, apply_safety_margin, coverage_ratio)

import numpy as np
import rospkg, rospy
from flask import Flask, Response, jsonify, request, send_file
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import LaserScan
from PIL import Image
from scipy.ndimage import binary_erosion, binary_dilation
import tf2_ros

try:
    import actionlib
    from actionlib_msgs.msg import GoalStatus
    from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
    from std_srvs.srv import Empty
    HAS_MB = True
except ImportError:
    HAS_MB = False

try:
    PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')
except rospkg.ResourceNotFound:
    PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
RUN_LOG = os.path.join(PKG, 'data', 'coverage_runs.csv')   # 每次執行結束追加一列指標

app = Flask(__name__)

str_time = None       # /map 頻率統計（除錯用）
last_prt_time = None
count = 0

# ════════════════════════════════════════════════════════
#  可調參數
# ════════════════════════════════════════════════════════
MORPH_ITER = 2      # 形態學運算次數（侵蝕/膨脹地圖「顯示」用）
CROP_PAD   = 10     # 地圖裁切邊距（格）
V_MAX      = 0.18   # 手動遙控線速度上限（m/s），Burger 規格 0.22
W_MAX      = 1.50   # 手動遙控角速度上限（rad/s），Burger 規格 2.84
TELEOP_TTL = 0.6    # 遙控指令有效期（秒）；逾時未收到新指令就自動停車
STALL_SEC  = 3.0    # 覆蓋執行時停滯這麼久就不再等 move_base，自行判定到達或跳過（秒）
STALL_DIST = 0.03   # 「有進展」門檻：位移超過此值（公尺）
STALL_YAW  = 0.20   # 或原地轉超過此角度（rad）；避免把對準方向的原地旋轉誤判為卡住
GOAL_NEAR  = 0.15   # 未被 move_base 判定到達、但離路點這麼近時視同到達（公尺）
VIA_NEAR   = 0.12   # 掃描線中途點：車子進入此半徑就直接送下一點（公尺）。
                    # 不等 move_base 判定到達，否則 DWA 每個中途點都會減速、停車、對準方向
RETRY_MAX  = 2      # 路點失敗後最多脫困重試幾次，仍失敗才跳過
STUCK_MAX  = 3      # 連續這麼多個路點失敗、且車子幾乎沒移動 → 判定受困，停止任務
STUCK_MOVE = 0.30   # 「幾乎沒移動」的門檻（公尺）
ESCAPE_V     = 0.05 # 脫困直線速度（m/s）
ESCAPE_DIST  = 0.12 # 脫困移動距離（公尺）
ESCAPE_CLEAR = 0.25 # 行進方向雷射扇形內最近障礙須大於此值才動（公尺，自雷射量起）
BODY_R       = 0.11 # 車身半徑（公尺）：脫困前檢查地圖上會掃過的範圍用
# COV_SPACING / COV_MARGIN 來自 coverage_planner 模組

# ════════════════════════════════════════════════════════
#  共享狀態
# ════════════════════════════════════════════════════════
map_lock = threading.Lock()
map_png = map_eroded = map_dilated = map_margin = None
map_meta = {}   # resolution, origin_x/y, r0, c0, crop_h
map_data = {}   # data(np array), h, w, frame_id  ← 供覆蓋規劃用

robot_lock = threading.Lock()
robot_pos  = {'x': None, 'y': None}   # 世界座標
robot_path = []                       # [[wx, wy], ...] 行走軌跡

cov_lock   = threading.Lock()
cov_status = {'state': 'idle', 'done': 0, 'total': 0, 'msg': ''}
cov_path   = []   # [(wx, wy), ...] 全部路點，世界座標
cov_cells  = []   # [[(wx, wy), ...], ...] 每個 cell 的路點
cov_via    = []   # [bool, ...] 與 cov_path 等長；True = 掃描線上的中途點
cov_info   = {}   # task / plan_ms / plan_cov / plan_len / area / n_runs / n_cells / n_critical / axis_deg / ratio
cov_skips  = []   # [[路點序號, 原因], ...] 被跳過的路點，供網頁標示
cov_grid   = {}   # 規劃當下的 free / res / ox / oy：實際覆蓋率沿用同一張圖算，分母才和規劃覆蓋率一致
cov_clock  = {'elapsed': 0.0, 't0': None}   # 累計執行秒數（停止→繼續會接著算）
cov_cache  = {'n': -1, 'ratio': 0.0}        # 實際覆蓋率快取：軌跡點數沒變就不重算

scan_lock = threading.Lock()
scan_msg  = None   # 最新一筆 LaserScan
tf_buffer = None   # tf2 緩衝（map ← 雷射座標查詢用）

teleop_lock = threading.Lock()
teleop_cmd  = {'v': 0.0, 'w': 0.0, 't': -1e9}
cmd_pub     = None

slam_lock = threading.Lock()
slam_proc = None
slam_cfg  = {'manage': True, 'method': 'gmapping'}


def manual_allowed():
    """手動遙控是否被允許（覆蓋執行中一律禁止）。"""
    with cov_lock:
        return cov_status['state'] != 'running'


# ════════════════════════════════════════════════════════
#  地圖處理
# ════════════════════════════════════════════════════════
def _to_png(arr):
    """地圖處理後轉 PNG bytes（黑白反轉，並上下翻轉）。"""
    buf = io.BytesIO()
    Image.fromarray(np.flipud(arr), 'L').save(buf, format='PNG')
    return buf.getvalue()


def _crop(known, h, w):
    """找出已知格子的最小矩形（加邊距）。"""
    r = np.any(known, axis=1)
    c = np.any(known, axis=0)
    if not r.any():
        return 0, h, 0, w
    r0 = max(np.argmax(r)          - CROP_PAD, 0)
    r1 = min(h - np.argmax(r[::-1]) + CROP_PAD, h)
    c0 = max(np.argmax(c)          - CROP_PAD, 0)
    c1 = min(w - np.argmax(c[::-1]) + CROP_PAD, w)
    return r0, r1, c0, c1


def map_callback(msg):
    global map_png, map_eroded, map_dilated, map_margin, map_meta, map_data
    global str_time, last_prt_time, count

    # /map 接收頻率統計（除錯用）
    if str_time is None:
        str_time = rospy.get_time()
        last_prt_time = str_time
    count += 1
    curr_time = rospy.get_time()
    if curr_time - last_prt_time >= 2.0:
        elapsed = curr_time - str_time
        print(f"收到訊息總數: {count} | 總運行時間: {elapsed:.2f}s | "
              f"平均頻率: {count / elapsed:.2f} Hz")
        print(f"地圖尺寸: {msg.info.width} x {msg.info.height}")
        last_prt_time = curr_time

    w, h = msg.info.width, msg.info.height
    if w == 0 or h == 0:
        return

    data  = np.array(msg.data, dtype=np.int8).reshape((h, w)).astype(np.int16)
    known = data >= 0
    obs   = data == 100
    free  = data == 0
    kern  = np.ones((3, 3), dtype=bool)

    # 原始地圖灰階
    gray = np.full((h, w), 128, dtype=np.uint8)
    gray[known] = np.clip(255 - data[known] * 255 // 100, 0, 255).astype(np.uint8)

    # 侵蝕地圖（障礙縮小，顯示用）
    gray_e = np.full((h, w), 128, dtype=np.uint8)
    gray_e[free] = 255
    gray_e[binary_erosion(obs, kern, MORPH_ITER)] = 0

    # 膨脹地圖（障礙擴大，顯示用）
    gray_d = np.full((h, w), 128, dtype=np.uint8)
    gray_d[free] = 255
    gray_d[binary_dilation(obs, kern, MORPH_ITER)] = 0

    # 規劃用安全邊距：直接呼叫演算法本身的函式，確保畫面與規劃完全一致
    safe = apply_safety_margin(data, COV_MARGIN, msg.info.resolution)
    gray_m = np.full((h, w), 128, dtype=np.uint8)
    gray_m[free] = 255
    gray_m[safe] = 0

    r0, r1, c0, c1 = _crop(known, h, w)

    with map_lock:
        map_png     = _to_png(gray[r0:r1, c0:c1])
        map_eroded  = _to_png(gray_e[r0:r1, c0:c1])
        map_dilated = _to_png(gray_d[r0:r1, c0:c1])
        map_margin  = _to_png(gray_m[r0:r1, c0:c1])
        map_meta = dict(
            resolution = msg.info.resolution,
            origin_x   = msg.info.origin.position.x,
            origin_y   = msg.info.origin.position.y,
            r0=r0, c0=c0, crop_h=r1-r0,
        )
        map_data = dict(
            data     = data,
            h=h, w=w,
            frame_id = msg.header.frame_id or 'map',
        )


def _robot_pose(frame):
    """用 TF 查機器人在 frame 座標下的 (x, y, yaw)；查不到回傳 None。"""
    if tf_buffer is None:
        return None
    try:
        tf = tf_buffer.lookup_transform(frame, 'base_footprint', rospy.Time(0), rospy.Duration(0.05))
    except (tf2_ros.LookupException, tf2_ros.ConnectivityException,
            tf2_ros.ExtrapolationException):
        return None
    t, q = tf.transform.translation, tf.transform.rotation
    return t.x, t.y, math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))


def pose_tick(_evt):
    """
    10 Hz 以 TF 查機器人在地圖座標的位置，更新位置與行走軌跡。

    不用 /odom：odom 座標會累積漂移，畫在地圖上會和覆蓋路徑對不上；
    map → base_footprint 已含 SLAM 的修正，和地圖、路點同一個座標系。
    """
    with map_lock:
        fid = map_data.get('frame_id', 'map')
    pose = _robot_pose(fid)
    if pose is None:
        return
    rx, ry = pose[0], pose[1]

    # 行走軌跡只在覆蓋執行中記錄；手動移動不留痕，執行結束後保留該次結果供檢視
    with cov_lock:
        recording = cov_status['state'] == 'running'

    with robot_lock:
        robot_pos.update(x=rx, y=ry)
        if not recording:
            return
        if not robot_path:
            robot_path.append([rx, ry])
        else:
            dx, dy = rx - robot_path[-1][0], ry - robot_path[-1][1]
            if dx*dx + dy*dy >= 0.01:   # 每 0.1 m 記一點
                robot_path.append([rx, ry])
                if len(robot_path) > 10000:
                    robot_path.pop(0)


def scan_callback(msg):
    """收到 /scan 時僅保存最新一筆，轉換到地圖座標延後到 /scan 路由處理。"""
    global scan_msg
    with scan_lock:
        scan_msg = msg


# ════════════════════════════════════════════════════════
#  手動遙控
# ════════════════════════════════════════════════════════
def teleop_tick(_evt):
    """10 Hz 送出手動速度指令；指令過期或非手動模式一律送 0。"""
    if cmd_pub is None:
        return
    if not manual_allowed():
        return                                   # 覆蓋執行中，/cmd_vel 交給 move_base

    with teleop_lock:
        v, w, t = teleop_cmd['v'], teleop_cmd['w'], teleop_cmd['t']
    if rospy.get_time() - t > TELEOP_TTL:        # 網頁沒有續傳 → 自動停車
        v = w = 0.0

    tw = Twist()
    tw.linear.x  = v
    tw.angular.z = w
    cmd_pub.publish(tw)


def teleop_halt():
    """立刻把速度歸零（切換模式或重啟 SLAM 前呼叫）。"""
    with teleop_lock:
        teleop_cmd.update(v=0.0, w=0.0, t=-1e9)
    if cmd_pub is not None:
        cmd_pub.publish(Twist())


# ════════════════════════════════════════════════════════
#  SLAM 生命週期
# ════════════════════════════════════════════════════════
def slam_launch():
    """以子行程啟動 SLAM（獨立行程群組，方便整組收掉）。"""
    global slam_proc
    cmd = ['roslaunch', 'turtlebot3_slam', 'turtlebot3_slam.launch',
           f"slam_methods:={slam_cfg['method']}", 'open_rviz:=false']
    rospy.loginfo('[slam] 啟動：%s', ' '.join(cmd))
    slam_proc = subprocess.Popen(cmd, preexec_fn=os.setsid)


def slam_kill(timeout=10.0):
    """對整個行程群組送 SIGINT，讓 roslaunch 正常收尾。"""
    global slam_proc
    if slam_proc is None:
        return
    try:
        os.killpg(os.getpgid(slam_proc.pid), signal.SIGINT)
        slam_proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        rospy.logwarn('[slam] SIGINT 逾時，改送 SIGKILL')
        try:
            os.killpg(os.getpgid(slam_proc.pid), signal.SIGKILL)
            slam_proc.wait(timeout=5.0)
        except Exception as e:
            rospy.logerr('[slam] 強制結束失敗：%s', e)
    except Exception as e:
        rospy.logerr('[slam] 結束失敗：%s', e)
    finally:
        slam_proc = None


# ════════════════════════════════════════════════════════
#  move_base 執行執行緒
# ════════════════════════════════════════════════════════
def _yaw_to_quat(yaw):
    """偏航角 → 四元數 (z, w)。"""
    return math.sin(yaw / 2), math.cos(yaw / 2)


def _go_to(client, fid, x, y, yaw, near=None):
    """
    送出單一目標並等待，回傳：
      'ok'      move_base 回報到達；或給了 near 且車子已進入該半徑（目標不取消，
                直接送下一個目標時 move_base 會無縫接手，車子不必停）
      'failed'  move_base 回報失敗（規劃不出路線，或它自己放棄）
      'stalled' 位移與轉角都沒進展超過 STALL_SEC，已取消目標
      'stopped' 使用者按下停止
    """
    with cov_lock:
        if cov_status['state'] != 'running':
            return 'stopped'

    qz, qw = _yaw_to_quat(yaw)
    goal = MoveBaseGoal()
    goal.target_pose.header.frame_id    = fid
    goal.target_pose.header.stamp       = rospy.Time.now()
    goal.target_pose.pose.position.x    = x
    goal.target_pose.pose.position.y    = y
    goal.target_pose.pose.orientation.z = qz
    goal.target_pose.pose.orientation.w = qw
    client.send_goal(goal)

    # 每 0.2 秒檢查一次停止訊號、是否已靠近中途點與是否停滯
    anchor, anchor_t = None, 0.0
    while not rospy.is_shutdown():
        with cov_lock:
            if cov_status['state'] != 'running':
                client.cancel_all_goals()
                return 'stopped'
        if client.wait_for_result(rospy.Duration(0.2)):
            return 'ok' if client.get_state() == GoalStatus.SUCCEEDED else 'failed'

        # 停滯偵測：車身壓到 costmap 障礙區時 DWA 找不到可行軌跡而停車，
        # move_base 會乾等 controller_patience 再做它的自救；這裡不等，交給 _escape
        pose, now = _robot_pose(fid), rospy.get_time()
        if pose is None:
            continue
        if near is not None and math.hypot(pose[0] - x, pose[1] - y) < near:
            return 'ok'
        if (anchor is None
                or math.hypot(pose[0] - anchor[0], pose[1] - anchor[1]) > STALL_DIST
                or abs(math.atan2(math.sin(pose[2] - anchor[2]),
                                  math.cos(pose[2] - anchor[2]))) > STALL_YAW):
            anchor, anchor_t = pose, now
        elif now - anchor_t > STALL_SEC:
            client.cancel_goal()
            client.wait_for_result(rospy.Duration(1.0))   # 等 move_base 確實停車
            return 'stalled'
    return 'stopped'


def _scan_min(heading, half_width=math.radians(35)):
    """
    最新 /scan 在 heading（車身座標，0＝車頭、π＝車尾）±half_width 扇形內的最近有效距離；
    扇形內沒有有效讀值回傳 inf，還沒收到 /scan 回傳 None。
    假設雷射座標與車身同向（TB3 的 base_scan 沒有旋轉）。
    """
    with scan_lock:
        msg = scan_msg
    if msg is None:
        return None
    rng = np.asarray(msg.ranges, dtype=float)
    ang = msg.angle_min + msg.angle_increment * np.arange(len(rng))
    off = np.abs(np.arctan2(np.sin(ang - heading), np.cos(ang - heading)))
    ok  = (off < half_width) & np.isfinite(rng) & (rng > msg.range_min) & (rng < msg.range_max)
    return float(rng[ok].min()) if ok.any() else float('inf')


def _map_clear(pose, sign, dist):
    """
    SLAM 地圖上，車子沿車頭（sign=+1）或車尾（sign=-1）直線移動 dist 公尺會掃過的長條區
    是否全是自由格。從車身中心量到車緣外 dist + 3 cm，寬度為車身兩側各 BODY_R。
    雷射在 0.12 m 內量不到東西，貼著車身的牆只能靠地圖檢查。
    """
    with map_lock:
        data = map_data.get('data')
        res  = map_meta.get('resolution')
        ox, oy = map_meta.get('origin_x'), map_meta.get('origin_y')
    if data is None or res is None:
        return False
    x, y, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    A, S = np.meshgrid(np.arange(0.0, BODY_R + dist + 0.03, res / 2),
                       np.arange(-BODY_R, BODY_R + 1e-9, res / 2))
    cols = np.round((x + sign * A * c - S * s - ox) / res).astype(int)
    rows = np.round((y + sign * A * s + S * c - oy) / res).astype(int)
    H, W = data.shape
    if rows.min() < 0 or rows.max() >= H or cols.min() < 0 or cols.max() >= W:
        return False
    return bool((data[rows, cols] == 0).all())


def _clear_costmaps():
    """清掉 move_base costmap 上殘留的障礙標記（真的牆會被雷射立刻重新標上）。"""
    try:
        rospy.wait_for_service('/move_base/clear_costmaps', timeout=1.0)
        rospy.ServiceProxy('/move_base/clear_costmaps', Empty)()
    except (rospy.ROSException, rospy.ServiceException) as e:
        rospy.logwarn('[coverage] 清除 costmap 失敗：%s', e)


def _escape(fid):
    """
    停滯時自行脫困：直線退開（不行就前進）一小段，再清空 costmap。回傳是否有移動。

    move_base 內建的自救（清 costmap、原地旋轉）在車身已貼到障礙時轉不了身，救不回來。
    差速車只能沿車頭方向進退，所以先試後退（通常是剛走過來的路），再試前進；
    該方向要同時通過地圖（靜態牆）與雷射（地圖上沒有的障礙）檢查才會動。
    """
    pose, moved = _robot_pose(fid), False
    for sign in ((-1, 1) if pose is not None and cmd_pub is not None else ()):
        heading = 0.0 if sign > 0 else math.pi
        near = _scan_min(heading)
        if near is None or near < ESCAPE_CLEAR or not _map_clear(pose, sign, ESCAPE_DIST):
            continue

        tw = Twist()
        tw.linear.x = sign * ESCAPE_V
        t_end, rate = rospy.get_time() + 2 * ESCAPE_DIST / ESCAPE_V, rospy.Rate(10)
        while not rospy.is_shutdown() and rospy.get_time() < t_end:
            with cov_lock:
                if cov_status['state'] != 'running':
                    break
            p = _robot_pose(fid)
            if p is not None and math.hypot(p[0] - pose[0], p[1] - pose[1]) >= ESCAPE_DIST:
                break
            near = _scan_min(heading)
            if near is None or near < ESCAPE_CLEAR - ESCAPE_DIST:   # 行進中有東西靠近
                break
            cmd_pub.publish(tw)
            rate.sleep()
        cmd_pub.publish(Twist())
        moved = True
        break

    _clear_costmaps()
    return moved


def run_coverage(start_idx=0):
    """執行緒進入點：計時並在結束時（完成、停止、錯誤皆然）把本次指標寫進 RUN_LOG。"""
    with cov_lock:
        cov_clock['t0'] = time.time()
    try:
        _run_coverage(start_idx)
    finally:
        with cov_lock:
            if cov_clock['t0'] is not None:
                cov_clock['elapsed'] += time.time() - cov_clock['t0']
                cov_clock['t0'] = None
        _log_run()


def _run_coverage(start_idx=0):
    """
    從第 start_idx 個路點起依序送給 move_base，可隨時被 stop 中斷。結束時一律離開 running。

    路點失敗（停滯或 move_base 放棄）時：已貼在路點旁就算到；否則脫困後重送同一點，
    重試 RETRY_MAX 次仍失敗才跳過。連續 STUCK_MAX 個路點失敗且車子幾乎沒移動，
    代表車被困住、脫困也救不回來——這時停止任務、把進度退回第一個失敗的路點，
    讓使用者手動移車後按「從中斷處繼續」，而不是把剩下的路點全部跳光。
    """
    if not HAS_MB:
        with cov_lock:
            cov_status.update(state='error', msg='未安裝 move_base_msgs')
        return

    client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    if not client.wait_for_server(rospy.Duration(5.0)):
        with cov_lock:
            cov_status.update(state='error', msg='move_base 未啟動（等待 5 秒逾時）')
        return

    with cov_lock:
        path = list(cov_path)
        via  = list(cov_via) if len(cov_via) == len(cov_path) else [False] * len(cov_path)
        fid  = map_data.get('frame_id', 'map')
        cov_status.update(state='running', total=len(path), done=start_idx, msg='')

    n = len(path)
    fails, fail_pose = 0, None     # 連續失敗的路點數、這串失敗開始時車子的位置
    for i in range(start_idx, n):
        x, y = path[i]
        with cov_lock:
            if cov_status['state'] != 'running':
                client.cancel_all_goals()
                return
            cov_status['done'] = i

        # 朝向：面向下一個路點（最後一點保持原方向）
        if i + 1 < n:
            nx, ny = path[i + 1]
            yaw = math.atan2(ny - y, nx - x)
        else:
            yaw = 0.0

        reached = False
        for attempt in range(RETRY_MAX + 1):
            result = _go_to(client, fid, x, y, yaw, near=VIA_NEAR if via[i] else None)
            if result == 'stopped':
                return
            pose = _robot_pose(fid)
            if result == 'ok' or (pose is not None
                                  and math.hypot(pose[0] - x, pose[1] - y) < GOAL_NEAR):
                reached = True
                break
            why = '停滯' if result == 'stalled' else '無法到達'
            if attempt < RETRY_MAX:
                rospy.logwarn(f'[coverage] 路點 {i+1}/{n} {why}，脫困後重試 {attempt+1}/{RETRY_MAX}')
                with cov_lock:
                    cov_status['msg'] = f'路點 {i+1}/{n} {why}，脫困重試 {attempt+1}/{RETRY_MAX}'
                _escape(fid)

        if reached:
            fails, fail_pose = 0, None
            continue

        rospy.logwarn(f'[coverage] 路點 {i+1}/{n} 跳過（{why}）')
        with cov_lock:
            cov_status['msg'] = f'路點 {i+1}/{n} 跳過（{why}）'
            cov_skips.append([i, why])

        pose = _robot_pose(fid)
        if fails == 0:
            fail_pose = pose
        fails += 1
        if fails < STUCK_MAX:
            continue
        if (pose is not None and fail_pose is not None
                and math.hypot(pose[0] - fail_pose[0], pose[1] - fail_pose[1]) >= STUCK_MOVE):
            fails, fail_pose = 0, None          # 車子有在動，只是這幾點真的到不了
            continue

        first = i - fails + 1
        rospy.logerr(f'[coverage] 連續 {fails} 個路點失敗且車子幾乎沒動，判定受困，停止於路點 {first+1}')
        with cov_lock:
            del cov_skips[-fails:]              # 受困期間的跳過不算數，繼續時從 first 重走
            cov_status.update(state='error', done=first,
                              msg=f'機器人受困（連續 {fails} 個路點失敗且幾乎沒移動），'
                                  '請手動把車移到空曠處後按「從中斷處繼續」')
        client.cancel_all_goals()
        return

    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status.update(state='done', done=n)


def _path_len(pts):
    return float(sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)))


def cov_metrics():
    """
    覆蓋任務的量化指標（給網頁與 RUN_LOG）：
      plan_ms / plan_cov / plan_len / area  規劃當下算好，存在 cov_info
      actual_cov   實際行走軌跡掃過可達區的比例（與 plan_cov 同一張圖、同一覆蓋半徑）
      reached      成功到達的路點數（已處理 − 跳過）；completion = reached / total
      exec_s       累計執行秒數；actual_len 實際行走長度
    """
    with cov_lock:
        st, info, grid = dict(cov_status), dict(cov_info), dict(cov_grid)
        n_skip  = len(cov_skips)
        exec_s  = cov_clock['elapsed'] + (time.time() - cov_clock['t0']
                                          if cov_clock['t0'] is not None else 0.0)
    with robot_lock:
        path = [tuple(p) for p in robot_path]

    if grid and path and len(path) != cov_cache['n']:
        segs = list(zip(path[:-1], path[1:])) or [(path[0], path[0])]
        cov_cache.update(n=len(path), ratio=coverage_ratio(
            grid['free'], grid['res'], grid['ox'], grid['oy'], segs))
    actual = cov_cache['ratio'] if grid and path else 0.0

    total   = st['total']
    reached = max(0, st['done'] - n_skip)
    return {
        'task':       info.get('task'),
        'state':      st['state'],
        'area':       info.get('area'),
        'plan_ms':    info.get('plan_ms'),
        'plan_cov':   info.get('plan_cov'),
        'actual_cov': round(actual, 4),
        'total':      total,
        'reached':    reached,
        'skipped':    n_skip,
        'completion': round(reached / total, 4) if total else None,
        'exec_s':     round(exec_s, 1),
        'plan_len':   info.get('plan_len'),
        'actual_len': round(_path_len(path), 2),
        'n_cells':    info.get('n_cells'),
        'n_critical': info.get('n_critical'),
        'axis_deg':   info.get('axis_deg'),
        'ratio':      info.get('ratio'),
    }


def _log_run():
    """把本次執行的指標追加到 RUN_LOG（utf-8-sig，Excel 直接開不會亂碼）。"""
    m = cov_metrics()
    if not m['task']:
        return
    row = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), **m}
    try:
        os.makedirs(os.path.dirname(RUN_LOG), exist_ok=True)
        new = not os.path.exists(RUN_LOG)
        with open(RUN_LOG, 'a', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)
    except OSError as e:
        rospy.logwarn('[coverage] 寫入 %s 失敗：%s', RUN_LOG, e)


def world_to_px(wx, wy, meta):
    """座標轉換（世界 → 裁切後圖片像素）"""
    px = (wx - meta['origin_x']) / meta['resolution'] - meta['c0']
    py = meta['crop_h'] - ((wy - meta['origin_y']) / meta['resolution'] - meta['r0'])
    return round(px, 1), round(py, 1)


# ════════════════════════════════════════════════════════
#  Flask 路由
# ════════════════════════════════════════════════════════
def _serve_png(data):
    if data is None:
        return Response('等待地圖...', status=503)
    resp = send_file(io.BytesIO(data), mimetype='image/png')
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/')
def index():
    p = os.path.join(PKG, 'web', 'index.html')
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ('找不到 index.html', 404)


@app.route('/map.png')
def get_map():
    with map_lock: d = map_png
    return _serve_png(d)


@app.route('/map_eroded.png')
def get_map_eroded():
    with map_lock: d = map_eroded
    return _serve_png(d)


@app.route('/map_dilated.png')
def get_map_dilated():
    with map_lock: d = map_dilated
    return _serve_png(d)


@app.route('/map_margin.png')
def get_map_margin():
    """規劃用安全邊距膨脹（與 coverage_planner 使用的完全相同）。"""
    with map_lock: d = map_margin
    return _serve_png(d)


@app.route('/robot_state')
def get_robot_state():
    with map_lock:   meta = dict(map_meta)
    with robot_lock: pos  = dict(robot_pos); path_w = list(robot_path)

    if not meta or pos['x'] is None:
        return jsonify({'pos': None, 'path': [], 'resolution': 0.05})

    px, py = world_to_px(pos['x'], pos['y'], meta)
    return jsonify({
        'pos': {
            'x': px, 'y': py,
            'wx': round(pos['x'], 2), 'wy': round(pos['y'], 2),
        },
        'path':       [list(world_to_px(p[0], p[1], meta)) for p in path_w],
        'resolution': meta['resolution'],
    })


@app.route('/scan')
def get_scan():
    """把最新一筆 /scan 透過 TF 轉到 map 座標，再換算成裁切後圖片像素回傳。"""
    with map_lock:  meta = dict(map_meta)
    with scan_lock: msg = scan_msg

    if not meta or msg is None or tf_buffer is None:
        return jsonify({'points': []})

    frame = msg.header.frame_id or 'base_scan'
    try:
        tf = tf_buffer.lookup_transform('map', frame, rospy.Time(0), rospy.Duration(0.05))
    except (tf2_ros.LookupException, tf2_ros.ConnectivityException,
            tf2_ros.ExtrapolationException):
        return jsonify({'points': []})

    t, q = tf.transform.translation, tf.transform.rotation
    yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)

    rmin, rmax = msg.range_min, msg.range_max
    ang, inc   = msg.angle_min, msg.angle_increment
    pts = []
    for r in msg.ranges:
        if rmin <= r <= rmax:                      # 同時排除 inf / nan
            lx, ly = r * math.cos(ang), r * math.sin(ang)
            wx = t.x + cos_y * lx - sin_y * ly
            wy = t.y + sin_y * lx + cos_y * ly
            pts.append(list(world_to_px(wx, wy, meta)))
        ang += inc
    return jsonify({'points': pts})


@app.route('/coverage/start', methods=['POST'])
def coverage_start():
    with cov_lock:
        if cov_status['state'] == 'running':
            return jsonify({'ok': False, 'msg': '已在執行中'})

    with map_lock:
        meta = dict(map_meta)
        raw  = dict(map_data)

    if not meta or raw.get('data') is None:
        return jsonify({'ok': False, 'msg': '地圖尚未就緒'})

    teleop_halt()                                  # 交出 /cmd_vel 控制權前先停車

    t_plan = time.perf_counter()                   # 規劃時間含安全邊距膨脹
    safe = apply_safety_margin(raw['data'], COV_MARGIN, meta['resolution'])
    free = (raw['data'] == 0) & ~safe

    with robot_lock:
        start = (robot_pos['x'], robot_pos['y']) if robot_pos['x'] is not None else None

    r = plan_coverage(free, meta['resolution'], meta['origin_x'], meta['origin_y'],
                      start=start)
    plan_ms = (time.perf_counter() - t_plan) * 1000.0
    if not r['waypoints']:
        return jsonify({'ok': False, 'msg': '無可走路徑，地圖可能不完整'})

    with robot_lock:
        robot_path.clear()          # 先清空，再切 running，軌跡才會從這一刻開始記

    center, axis_a, _, eigvals = r['axes']
    with cov_lock:
        cov_path[:]  = r['waypoints']
        cov_via[:]   = r['via']
        cov_cells[:] = r['cells']
        cov_skips.clear()
        cov_grid.update(free=free, res=meta['resolution'],
                        ox=meta['origin_x'], oy=meta['origin_y'])
        cov_clock.update(elapsed=0.0, t0=None)
        cov_cache.update(n=-1, ratio=0.0)
        cov_info.clear()
        cov_info.update(
            task       = time.strftime('%Y%m%d-%H%M%S'),
            plan_ms    = round(plan_ms, 1),
            plan_cov   = round(coverage_ratio(free, meta['resolution'], meta['origin_x'],
                                              meta['origin_y'], r['sweeps']), 4),
            plan_len   = round(_path_len(r['waypoints']), 2),
            area       = round(float(free.sum()) * meta['resolution'] ** 2, 2),
            n_runs     = r['n_runs'],
            n_cells    = len(r['cells']),
            n_critical = len(r['critical']),
            axis_deg   = round(math.degrees(math.atan2(axis_a[1], axis_a[0])), 1),
            ratio      = round(float(max(eigvals) / min(eigvals)), 2),
        )
        cov_status.update(state='running', done=0, total=len(r['waypoints']), msg='')

    threading.Thread(target=run_coverage, daemon=True).start()
    return jsonify({'ok': True, 'total': len(r['waypoints']), **cov_info})


@app.route('/coverage/stop', methods=['POST'])
def coverage_stop():
    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status['state'] = 'stopped'
    teleop_halt()
    return jsonify({'ok': True})


@app.route('/coverage/resume', methods=['POST'])
def coverage_resume():
    """沿用同一條路徑，從中斷處（cov_status['done']）接著走，不重新規劃。"""
    teleop_halt()                                  # 交出 /cmd_vel 控制權前先停車
    with cov_lock:
        if cov_status['state'] == 'running':
            return jsonify({'ok': False, 'msg': '已在執行中'})
        start = cov_status['done']
        if cov_status['state'] not in ('stopped', 'error') or start >= len(cov_path):
            return jsonify({'ok': False, 'msg': '沒有可接續的任務，請按「開始執行」重新規劃'})
        cov_status.update(state='running', msg='')

    threading.Thread(target=run_coverage, args=(start,), daemon=True).start()
    return jsonify({'ok': True, 'start': start})


@app.route('/coverage/runs.csv')
def coverage_runs_csv():
    """下載歷次執行指標（RUN_LOG）。"""
    if not os.path.exists(RUN_LOG):
        return Response('尚無執行紀錄', status=404, mimetype='text/plain; charset=utf-8')
    with open(RUN_LOG, 'rb') as f:                 # 不用 send_file：Noetic 的 Flask 1.x 沒有 download_name
        body = f.read()
    return Response(body, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=coverage_runs.csv'})


@app.route('/coverage/status')
def coverage_status():
    with cov_lock:
        st     = dict(cov_status)
        path_w = list(cov_path)
        cells  = [list(c) for c in cov_cells]
        info   = dict(cov_info)
        skips  = [list(s) for s in cov_skips]
    with map_lock:
        meta = dict(map_meta)

    st['skipped'] = skips    # 序號對應 path_px 的索引
    if meta:
        st['path_px']  = [list(world_to_px(x, y, meta)) for x, y in path_w]
        st['cells_px'] = [[list(world_to_px(x, y, meta)) for x, y in c] for c in cells]
    else:
        st['path_px'] = st['cells_px'] = []

    st['info']    = info
    st['metrics'] = cov_metrics()
    st['manual'] = st['state'] != 'running'
    st['slam_managed'] = slam_cfg['manage']
    return jsonify(st)


@app.route('/teleop', methods=['POST'])
def teleop():
    """手動遙控。body: {v: -1..1, w: -1..1}（比例值，後端乘上速度上限）。"""
    if not manual_allowed():
        return jsonify({'ok': False, 'msg': '覆蓋執行中，請先按結束'}), 409

    body = request.get_json(silent=True) or {}
    try:
        v = float(body.get('v', 0.0))
        w = float(body.get('w', 0.0))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'msg': '速度格式錯誤'}), 400

    v = max(-1.0, min(1.0, v)) * V_MAX
    w = max(-1.0, min(1.0, w)) * W_MAX
    with teleop_lock:
        teleop_cmd.update(v=v, w=w, t=rospy.get_time())
    return jsonify({'ok': True, 'v': round(v, 3), 'w': round(w, 3)})


@app.route('/slam/restart', methods=['POST'])
def slam_restart():
    """重啟 SLAM 重新建圖：停覆蓋 → 停車 → 收掉 SLAM → 清空狀態 → 重新啟動。"""
    global map_png, map_eroded, map_dilated, map_margin

    if not slam_cfg['manage']:
        return jsonify({'ok': False,
                        'msg': 'SLAM 不由本節點管理（manage_slam=false），請手動重啟'}), 400

    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status['state'] = 'stopped'
    teleop_halt()

    with slam_lock:
        slam_kill()

        with map_lock:
            map_png = map_eroded = map_dilated = map_margin = None
            map_meta.clear()
            map_data.clear()
        with robot_lock:
            robot_path.clear()
            robot_pos.update(x=None, y=None)
        with cov_lock:
            cov_path[:]  = []
            cov_via[:]   = []
            cov_cells[:] = []
            cov_skips.clear()
            cov_info.clear()
            cov_grid.clear()
            cov_clock.update(elapsed=0.0, t0=None)
            cov_cache.update(n=-1, ratio=0.0)
            cov_status.update(state='idle', done=0, total=0, msg='')

        try:
            slam_launch()
        except Exception as e:
            rospy.logerr('[slam] 重啟失敗：%s', e)
            return jsonify({'ok': False, 'msg': f'重啟失敗：{e}'}), 500

    return jsonify({'ok': True, 'msg': 'SLAM 已重啟，請等待新地圖'})


# ════════════════════════════════════════════════════════
#  主函式
# ════════════════════════════════════════════════════════
def main():
    global tf_buffer, cmd_pub
    rospy.init_node('map_server')
    port = rospy.get_param('~port', 8080)
    slam_cfg['manage'] = bool(rospy.get_param('~manage_slam', True))
    slam_cfg['method'] = str(rospy.get_param('~slam_methods', 'gmapping'))

    if not HAS_MB:
        rospy.logwarn('未安裝 move_base_msgs，覆蓋執行功能不可用')

    tf_buffer = tf2_ros.Buffer()
    tf2_ros.TransformListener(tf_buffer)

    cmd_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)

    rospy.Subscriber('/map',  OccupancyGrid, map_callback,  queue_size=1)
    rospy.Subscriber('/scan', LaserScan,     scan_callback, queue_size=1)

    if slam_cfg['manage']:
        rospy.on_shutdown(slam_kill)
        slam_launch()
    else:
        rospy.loginfo('[slam] manage_slam=false，SLAM 由外部負責，/slam/restart 停用')

    rospy.Timer(rospy.Duration(0.1), teleop_tick)   # 10 Hz 遙控心跳
    rospy.Timer(rospy.Duration(0.1), pose_tick)     # 10 Hz 以 TF 追蹤機器人位置（地圖座標）

    try:
        ip = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        ip = '127.0.0.1'
    rospy.loginfo(f'地圖伺服器 → http://{ip}:{port}')

    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False),
        daemon=True,
    ).start()
    rospy.spin()


if __name__ == '__main__':
    main()
