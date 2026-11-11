#!/usr/bin/env python3
"""
TurtleBot3 地圖伺服器（Module A）
  - 訂閱 /map  → 提供原始 / 侵蝕 / 顯示膨脹 / 規劃安全邊距 四種地圖 PNG
  - TF map → base_footprint → 機器人位置與行走軌跡（地圖座標，已含 SLAM 修正）
  - /coverage/start|resume|stop|status → 牛耕式路徑規劃 + move_base 執行，並回傳 cell 分解結果
  - /teleop                     → 手動遙控（與覆蓋執行互斥）
  - /slam/restart               → 重啟 SLAM 重新建圖（本節點負責 SLAM 的生命週期）
  - /explore/start|stop         → 自動建圖：以子行程管理 explore_lite（frontier 探索），
                                  自行判斷完成 → 存地圖 → 開回起點；~auto_explore=true 時啟動後自動開始
路徑規劃核心由 coverage_planner 模組提供。

模式互斥規則：
  覆蓋 cov_status['state'] == 'running'          → 覆蓋執行中
  探索 exp_status['state'] ∈ EXP_BUSY            → 自動建圖中（含倒數、存圖、回起點）
  兩者任一成立時，手動遙控被拒絕，另一個也不能開始（避免兩邊同時對 move_base／/cmd_vel 下指令）。
按下停止、完成、或發生錯誤都會離開上述狀態，自動切回可手動。
"""
import csv, io, json, math, os, signal, socket, subprocess, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from coverage_planner import (plan as plan_coverage, SPACING as COV_SPACING,
                              MARGIN as COV_MARGIN, apply_safety_margin, coverage_ratio,
                              remove_noise, COVER_R as COV_COVER_R, _seg_free, _rdp)

import numpy as np
import rospkg, rospy
from flask import Flask, Response, jsonify, request, send_file
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import OccupancyGrid
from nav_msgs.srv import GetPlan
from rosgraph_msgs.msg import Log
from sensor_msgs.msg import BatteryState, LaserScan
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, binary_dilation, label as nd_label
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
EXP_LOG = os.path.join(PKG, 'data', 'explore_runs.csv')    # 每次自動建圖結束追加一列摘要
EXP_DIR = os.path.join(PKG, 'data', 'explore')             # 每次自動建圖的過程、軌跡、事件、地圖疊圖

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
ESCAPE_CLEAR = 0.18 # 行進方向雷射扇形內最近障礙須大於此值才動（公尺，自雷射量起）。
                    # 原 0.25：2026-11-11 實測車子離牆 0.20 m 時 move_base 不肯轉、脫困也因此不動，兩邊僵住判定受困
BODY_R       = 0.11 # 車身半徑（公尺）：脫困前檢查地圖上會掃過的範圍用

# ── 直線循跡（掃描線、外圈由自己控制，不經 DWA） ──
LINE_V       = 0.12   # 直行速度（m/s）
LINE_V_MIN   = 0.04   # 接近線尾時的最低速度（m/s）
LINE_W_MAX   = 1.2    # 直行時角速度上限（rad/s）
LINE_K_HEAD  = 2.0    # 角速度 = K_HEAD ×（方向誤差 + atan(K_CTE × 側向偏移 / 速度)）
LINE_K_CTE   = 2.5
LINE_TOL     = 0.03   # 線尾到達判定（公尺，沿線方向剩餘距離）
ROT_START    = 0.25   # 方向誤差超過此值（rad，約 14°）先原地轉正再走
ROT_TOL      = 0.05   # 原地轉正到此誤差內（rad，約 3°）
ROT_W_MAX    = 0.9    # 原地旋轉角速度上限（rad/s）
ROT_W_MIN    = 0.25   # 原地旋轉最低角速度（太小馬達轉不動）
FRONT_STOP   = 0.13   # 行進方向 ±20° 雷射最近距離小於此（公尺，自雷射量起）就停下，交給 move_base 處理
TURN_KEEP    = 0.26   # 下一段方向變化小於此（rad，約 15°）時線尾不減速，直接接下一段
NAV_RDP_EPS  = 0.04   # 向 move_base 要來的路線簡化成直線段的容許誤差（公尺）
# COV_SPACING / COV_MARGIN 來自 coverage_planner 模組

# ── 自動建圖（explore_lite） ──
EXPLORE_PARAMS = {                  # 傳給 explore_lite 的私有參數
    'robot_base_frame':      'base_footprint',
    'costmap_topic':         'map',          # 直接讀 SLAM 地圖找邊界
    'costmap_updates_topic': 'map_updates',
    'visualize':             'false',
    'planner_frequency':     '0.33',         # 每 3 秒重新挑一次目標
    'progress_timeout':      '30.0',         # 30 秒沒進展就把該目標列入黑名單
    'potential_scale':       '3.0',          # 越大越在意「近」
    'orientation_scale':     '0.0',
    'gain_scale':            '1.0',          # 越大越在意「大片」
    'transform_tolerance':   '0.3',
    'min_frontier_size':     '0.5',          # 短於此長度（公尺）的邊界不理會
}
EXPLORE_DELAY   = 10.0   # auto_explore：地圖與 move_base 就緒後倒數幾秒才開始（給人反應、可按停止）
EXPLORE_MAX_S   = 600.0  # 最長探索時間（秒），超過就收尾
EXPLORE_IDLE_S  = 90.0   # 已知面積這麼久都沒變大 → 視為完成（避免卡在搆不到的邊界）
EXPLORE_GROW    = 0.05   # 「變大」的門檻（m²）
FRONTIER_MIN    = 0.30   # 網頁顯示用：長度至少這麼長（公尺）的邊界才計入「剩餘邊界」
BATT_MIN        = 10.8   # 電池電壓低於此值（V）就停止探索（Burger 3S 鋰電池）
HOME_TIMEOUT    = 90.0   # 探索完開回起點最多等幾秒

# ════════════════════════════════════════════════════════
#  共享狀態
# ════════════════════════════════════════════════════════
map_lock = threading.Lock()
map_png = map_eroded = map_dilated = map_margin = map_noise = None
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
cov_kind   = []   # ['line'/'move', ...] 與 cov_path 等長；到達該點的方式（line＝自己直線循跡、move＝move_base）
cov_rec    = {}   # 本任務紀錄（停止後繼續會接著記）：t_start / events / timeline / path / t_tl
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

map_stats = {'area': 0.0, 'frontiers': 0}   # 已知空地面積（m²）、夠長的邊界段數；map_callback 更新

exp_lock   = threading.Lock()
exp_proc   = None
exp_status = {'state': 'idle', 'msg': '', 't0': None, 'elapsed': 0.0, 'map_file': None,
              'countdown': None}
exp_flags  = {'lite_done': False, 'stop': False, 'run': 0}   # explore_lite 回報結束／使用者按停止／第幾輪
EXP_BUSY   = ('countdown', 'exploring', 'saving', 'returning')
exp_rec    = {}   # 本輪紀錄：task / t_start / t0 / batt0 / area0 / home / events / timeline / path / home_result / reason
battery_v  = {'v': None}


def _exploring():
    with exp_lock:
        return exp_status['state'] in EXP_BUSY


def manual_allowed():
    """手動遙控是否被允許（覆蓋執行中、自動建圖中一律禁止）。"""
    with cov_lock:
        if cov_status['state'] == 'running':
            return False
    return not _exploring()


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
    global map_png, map_eroded, map_dilated, map_margin, map_noise, map_meta, map_data
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

    # 規劃用安全邊距：直接呼叫演算法本身的函式（先去雜點再膨脹），確保畫面與規劃完全一致
    clean, noise = remove_noise(data)
    safe = apply_safety_margin(clean, COV_MARGIN, msg.info.resolution)
    gray_m = np.full((h, w), 128, dtype=np.uint8)
    gray_m[clean == 0] = 255
    gray_m[safe] = 0

    # 被當成雜點、規劃時忽略的格子（黑＝雜點，其餘白），網頁上以黃色標示
    gray_n = np.full((h, w), 255, dtype=np.uint8)
    gray_n[noise] = 0

    r0, r1, c0, c1 = _crop(known, h, w)

    # 自動建圖進度：已知空地面積、邊界段數（空地且上下左右碰到未知；相連的算一段）
    res = msg.info.resolution
    frontier = free & binary_dilation(~known)
    lab, n = nd_label(frontier, structure=np.ones((3, 3), dtype=bool))
    if n:
        sizes = np.bincount(lab.ravel())[1:]
        n = int((sizes * res >= FRONTIER_MIN).sum())
    stats = {'area': round(float(free.sum()) * res * res, 2), 'frontiers': int(n)}

    with map_lock:
        map_stats.update(stats)
        map_png     = _to_png(gray[r0:r1, c0:c1])
        map_eroded  = _to_png(gray_e[r0:r1, c0:c1])
        map_dilated = _to_png(gray_d[r0:r1, c0:c1])
        map_margin  = _to_png(gray_m[r0:r1, c0:c1])
        map_noise   = _to_png(gray_n[r0:r1, c0:c1])
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

    if recording:
        now = time.time()
        with cov_lock:
            if 'path' in cov_rec:
                t = round(now - cov_rec['t_start'], 1)
                cp_ = cov_rec['path']
                if not cp_ or (rx - cp_[-1][1]) ** 2 + (ry - cp_[-1][2]) ** 2 >= 0.0025:
                    cp_.append((t, round(rx, 3), round(ry, 3)))
                if now - cov_rec['t_tl'] >= 1.0:
                    cov_rec['t_tl'] = now
                    cov_rec['timeline'].append((t, cov_status['done'], cov_rec.get('mode', ''),
                                                round(rx, 3), round(ry, 3), round(math.degrees(pose[2]), 1),
                                                battery_v['v'] if battery_v['v'] is not None else ''))

    with exp_lock:
        if exp_status['state'] in ('exploring', 'returning') and 'path' in exp_rec:
            ep = exp_rec['path']
            if not ep or (rx - ep[-1][1]) ** 2 + (ry - ep[-1][2]) ** 2 >= 0.0025:   # 每 5 cm 記一點
                ep.append((round(time.time() - exp_rec['t_start'], 1), round(rx, 3), round(ry, 3)))

    with robot_lock:
        robot_pos.update(x=rx, y=ry)
        if not recording:
            return
        if not robot_path:
            robot_path.append([rx, ry])
        else:
            dx, dy = rx - robot_path[-1][0], ry - robot_path[-1][1]
            if dx*dx + dy*dy >= 0.0025: # 每 5 cm 記一點（網頁「實際掃過範圍」用，太稀疏轉彎處會缺角）
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
    if slam_cfg['method'] == 'gmapping':
        # 本套件的 gmapping 參數（config/gmapping_params.yaml），比官方版不容易留下假障礙
        cmd = ['roslaunch', 'turtlebot3_ccpp', 'slam_gmapping.launch']
    else:
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
#  自動建圖（explore_lite frontier 探索）
#
#  explore_lite 只負責「挑下一個邊界、丟給 move_base」。何時算完成、存圖、回起點由這裡決定：
#    1. explore_lite 在 /rosout 說 "Exploration stopped"（找不到可去的邊界）
#    2. 已知面積 EXPLORE_IDLE_S 秒沒變大（剩下的邊界搆不到）
#    3. 超過 EXPLORE_MAX_S
#    4. 電池低於 BATT_MIN
#  任一成立 → 收掉 explore_lite → 存地圖到 maps/ → 開回起點 → done。
# ════════════════════════════════════════════════════════
def _set_exp(**kw):
    with exp_lock:
        exp_status.update(kw)


def explore_launch():
    global exp_proc
    cmd = ['rosrun', 'explore_lite', 'explore', '__name:=explore']
    cmd += [f'_{k}:={v}' for k, v in EXPLORE_PARAMS.items()]
    rospy.loginfo('[explore] 啟動 explore_lite')
    exp_proc = subprocess.Popen(cmd, preexec_fn=os.setsid)


def explore_kill(timeout=8.0):
    global exp_proc
    proc, exp_proc = exp_proc, None
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait(timeout=3.0)
        except Exception as e:
            rospy.logerr('[explore] 強制結束失敗：%s', e)
    except Exception as e:
        rospy.logerr('[explore] 結束失敗：%s', e)


def rosout_callback(msg):
    """explore_lite 找不到可去的邊界時會印 "Exploration stopped."，視為它認為探索完成。"""
    if not msg.name.endswith('/explore'):
        return
    if 'Exploration stopped' in msg.msg:
        exp_flags['lite_done'] = True
    if msg.level >= Log.INFO:
        _ev('explore_lite: ' + msg.msg.strip())


def battery_callback(msg):
    battery_v['v'] = msg.voltage


_mb = {'client': None}


def _mb_client(timeout=5.0):
    """自動建圖共用同一個 move_base action client：按停止時才能立刻取消（新建的 client 還沒連上，取消訊息會掉）。"""
    if not HAS_MB:
        return None
    if _mb['client'] is None:
        _mb['client'] = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    return _mb['client'] if _mb['client'].wait_for_server(rospy.Duration(timeout)) else None


def explore_start(delay=0.0):
    """開始自動建圖（delay > 0 時先倒數）。回傳 (ok, msg)。"""
    with cov_lock:
        if cov_status['state'] == 'running':
            return False, '自動覆蓋執行中，請先按結束'
    with map_lock:
        if map_data.get('data') is None:
            return False, '地圖尚未就緒，請等 SLAM 啟動'
    with exp_lock:
        if exp_status['state'] in EXP_BUSY:
            return False, '已在自動建圖中'
        exp_status.update(state='countdown' if delay > 0 else 'exploring', msg='',
                          t0=None, elapsed=0.0, map_file=None,
                          countdown=round(delay) if delay > 0 else None)
    exp_flags.update(lite_done=False, stop=False, run=exp_flags['run'] + 1)
    with exp_lock, map_lock:
        exp_rec.clear()
        exp_rec.update(task=time.strftime('%Y%m%d-%H%M%S'), t_start=time.time(), t0=None,
                       batt0=battery_v['v'], area0=map_stats['area'], home=None,
                       events=[], timeline=[], path=[], home_result=None, reason=None)
    _ev(f'開始（倒數 {round(delay)} 秒）' if delay > 0 else '開始')
    teleop_halt()
    threading.Thread(target=_explore_run, args=(delay, exp_flags['run']), daemon=True).start()
    return True, f'{round(delay)} 秒後開始自動建圖' if delay > 0 else '開始自動建圖'


def explore_stop(msg='已停止'):
    """使用者按停止（或重啟 SLAM）：停在當下，不存圖、不回起點。"""
    with exp_lock:
        busy = exp_status['state'] in EXP_BUSY
    if busy:
        _ev('停止：' + msg)
    exp_flags['stop'] = True
    if _mb['client'] is not None:
        _mb['client'].cancel_all_goals()            # 先取消目標讓車停下，再收 explore_lite
    explore_kill()
    if _mb['client'] is not None:
        _mb['client'].cancel_all_goals()            # explore_lite 收尾前可能又送了一個
    teleop_halt()
    if busy:
        _set_exp(state='stopped', msg=msg, countdown=None)


def _explore_run(delay, rid):
    try:
        _explore_body(delay, rid)
    except Exception as e:
        rospy.logerr('[explore] 例外：%s', e)
        _ev(f'例外：{e}')
        explore_kill()
        _set_exp(state='error', msg=f'自動建圖發生錯誤：{e}', countdown=None)
    finally:
        time.sleep(0.5)                 # 讓按停止的那一方先把狀態寫成 stopped
        try:
            _explore_write_log(rid)
        except Exception as e:
            rospy.logerr('[explore] 寫紀錄失敗：%s', e)


def _explore_body(delay, rid):
    halted = lambda: exp_flags['stop'] or exp_flags['run'] != rid   # 停止，或已有新一輪開始
    # 倒數（可被停止中斷）
    t_end = time.time() + delay
    while time.time() < t_end:
        if halted():
            return
        _set_exp(countdown=max(0, round(t_end - time.time())))
        time.sleep(0.2)

    client = _mb_client()
    if client is None:
        _set_exp(state='error', msg='move_base 未啟動（等待 5 秒逾時）', countdown=None)
        return
    with map_lock:
        fid = map_data.get('frame_id', 'map')
    home = _robot_pose(fid)

    t0 = time.time()
    with exp_lock:
        exp_rec.update(t0=t0, home=home)
    _set_exp(state='exploring', t0=t0, countdown=None, msg='')
    _ev('起點 ' + (f'({home[0]:.2f}, {home[1]:.2f}) 朝向 {math.degrees(home[2]):.0f}°' if home else '未知（TF 查不到）'))
    explore_launch()

    with map_lock:
        last_area = map_stats['area']
    last_grow, reason = t0, None
    while not rospy.is_shutdown():
        time.sleep(1.0)
        if halted():
            return
        now = time.time()
        with map_lock:
            area = map_stats['area']
        if area > last_area + EXPLORE_GROW:
            last_area, last_grow = area, now
        _set_exp(elapsed=round(now - t0, 1))
        _timeline_tick('exploring', fid)

        if exp_proc is None or exp_proc.poll() is not None:
            reason = 'explore_lite 意外結束，已存下目前地圖'
        elif exp_flags['lite_done']:
            reason = '已找不到可探索的邊界'
        elif now - last_grow > EXPLORE_IDLE_S:
            reason = f'地圖 {int(EXPLORE_IDLE_S)} 秒沒有變大，剩下的邊界到不了'
        elif now - t0 > EXPLORE_MAX_S:
            reason = f'達到最長探索時間 {int(EXPLORE_MAX_S // 60)} 分鐘'
        elif battery_v['v'] is not None and 5.0 < battery_v['v'] < BATT_MIN:
            reason = f'電池電壓過低（{battery_v["v"]:.2f} V），請充電'
        if reason:
            break
    else:
        return

    # 收尾：停探索 → 存圖 → 回起點
    with exp_lock:
        exp_rec['reason'] = reason
    _ev('結束探索：' + reason)
    _set_exp(state='saving', msg=reason)
    explore_kill()
    client.cancel_all_goals()
    teleop_halt()
    path = _save_map()
    _set_exp(map_file=os.path.basename(path) if path else None)
    _ev('地圖已存：' + os.path.basename(path) if path else '存地圖失敗')

    if home is not None and not halted():
        _set_exp(state='returning')
        _ev('開回起點')
        res = _go_home(client, fid, home, halted)
        with exp_lock:
            exp_rec['home_result'] = res
        _ev('回起點結果：' + res)
    if halted():
        return
    with exp_lock:
        exp_status['elapsed'] = round(time.time() - t0, 1)
        saved = '，地圖已存成 ' + exp_status['map_file'] if exp_status['map_file'] else '，但存地圖失敗'
    _set_exp(state='done', msg=reason + saved)
    rospy.loginfo('[explore] 完成：%s', reason)


def _save_map():
    """用 ROS 官方 map_server 套件的 map_saver 把目前 /map 存成 .pgm + .yaml，回傳路徑（不含副檔名）。"""
    out_dir = os.path.join(PKG, 'maps')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'explore_' + time.strftime('%Y%m%d_%H%M%S'))
    try:
        r = subprocess.run(['rosrun', 'map_server', 'map_saver', '-f', path, '__name:=ccpp_map_saver'],
                           capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and os.path.exists(path + '.yaml'):
            rospy.loginfo('[explore] 地圖已存：%s', path)
            return path
        rospy.logerr('[explore] map_saver 失敗：%s', r.stderr[-300:])
    except Exception as e:
        rospy.logerr('[explore] map_saver 例外：%s', e)
    return None


def _go_home(client, fid, home, halted):
    """開回探索起點（朝向也轉回去）。可被停止中斷，逾時就放棄、停在原地。"""
    qz, qw = _yaw_to_quat(home[2])
    goal = MoveBaseGoal()
    goal.target_pose.header.frame_id    = fid
    goal.target_pose.header.stamp       = rospy.Time.now()
    goal.target_pose.pose.position.x    = home[0]
    goal.target_pose.pose.position.y    = home[1]
    goal.target_pose.pose.orientation.z = qz
    goal.target_pose.pose.orientation.w = qw
    client.send_goal(goal)
    t_end, last_tl = time.time() + HOME_TIMEOUT, 0.0
    while time.time() < t_end and not rospy.is_shutdown():
        if halted():
            client.cancel_all_goals()
            return 'stopped'
        if client.wait_for_result(rospy.Duration(0.5)):
            return 'reached' if client.get_state() == GoalStatus.SUCCEEDED else 'failed'
        if time.time() - last_tl >= 1.0:
            _timeline_tick('returning', fid)
            last_tl = time.time()
    client.cancel_all_goals()
    return 'timeout'


# ── 自動建圖紀錄：給事後分析實際成效用 ──
def _ev(text):
    """記一筆事件（相對開始的秒數）。"""
    with exp_lock:
        if 'events' not in exp_rec or len(exp_rec['events']) >= 500:
            return
        exp_rec['events'].append((round(time.time() - exp_rec['t_start'], 1), text))
    rospy.loginfo('[explore] %s', text)


def _path_dist(pts):
    return sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(pts, pts[1:]))


def _timeline_tick(state, fid):
    """每秒一列：已知面積、邊界數、車子位置、累計行走距離、電池。"""
    pose = _robot_pose(fid)
    with map_lock:
        area, front = map_stats['area'], map_stats['frontiers']
    with exp_lock:
        if 'timeline' not in exp_rec:
            return
        exp_rec['timeline'].append((
            round(time.time() - exp_rec['t_start'], 1), state, area, front,
            round(pose[0], 3) if pose else '', round(pose[1], 3) if pose else '',
            round(math.degrees(pose[2]), 1) if pose else '',
            round(_path_dist(exp_rec['path']), 2),
            battery_v['v'] if battery_v['v'] is not None else ''))


def _explore_write_log(rid):
    """
    一輪自動建圖結束（完成、停止、錯誤皆然）後寫出：
      data/explore_runs.csv                 每輪一列摘要（utf-8-sig，Excel 可直接開）
      data/explore/<task>_timeline.csv      每秒一列過程
      data/explore/<task>_path.csv          行走軌跡（每 5 cm 一點）
      data/explore/<task>_events.txt        摘要＋事件（含 explore_lite 自己印的訊息）
      data/explore/<task>_map.png           最後的地圖疊上軌跡（綠＝起點、藍＝終點）
    """
    with exp_lock:
        if not exp_rec or exp_flags['run'] != rid:
            return
        rec = {k: (list(v) if isinstance(v, list) else v) for k, v in exp_rec.items()}
        st = dict(exp_status)
    result = st['state']
    if exp_flags['stop'] or result in EXP_BUSY:
        result = 'stopped'
    task = rec['task']
    os.makedirs(EXP_DIR, exist_ok=True)
    base = os.path.join(EXP_DIR, task)

    with map_lock:
        fid = map_data.get('frame_id', 'map')
        area_end, front_end = map_stats['area'], map_stats['frontiers']
        png, meta = map_png, dict(map_meta)
    pose = _robot_pose(fid)
    home = rec.get('home')
    home_err = (round(math.hypot(pose[0] - home[0], pose[1] - home[1]), 3)
                if pose is not None and home is not None else '')
    t0 = rec.get('t0')
    summary = {
        'task':          task,
        'start':         time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(rec['t_start'])),
        'result':        result,
        'reason':        rec.get('reason') or st.get('msg') or '',
        'total_s':       round(time.time() - rec['t_start'], 1),
        'explore_s':     round(time.time() - t0, 1) if t0 else 0.0,
        'area_start_m2': rec.get('area0'),
        'area_end_m2':   area_end,
        'frontiers_end': front_end,
        'path_len_m':    round(_path_dist(rec['path']), 2),
        'home_result':   rec.get('home_result') or '',
        'home_err_m':    home_err,
        'batt_start_v':  rec['batt0'] if rec.get('batt0') is not None else '',
        'batt_end_v':    battery_v['v'] if battery_v['v'] is not None else '',
        'map_file':      st.get('map_file') or '',
        'params':        json.dumps({**EXPLORE_PARAMS, 'EXPLORE_IDLE_S': EXPLORE_IDLE_S,
                                     'EXPLORE_MAX_S': EXPLORE_MAX_S}, ensure_ascii=False),
    }
    new = not os.path.exists(EXP_LOG)
    with open(EXP_LOG, 'a', newline='', encoding='utf-8-sig' if new else 'utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(summary))
        if new:
            w.writeheader()
        w.writerow(summary)

    with open(base + '_timeline.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['t_s', 'state', 'area_m2', 'frontiers', 'x', 'y', 'yaw_deg', 'dist_m', 'battery_v'])
        w.writerows(rec['timeline'])
    with open(base + '_path.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['t_s', 'x', 'y'])
        w.writerows(rec['path'])
    with open(base + '_events.txt', 'w', encoding='utf-8') as f:
        f.write(json.dumps(summary, ensure_ascii=False, indent=2) + '\n\n')
        f.writelines(f'{t:7.1f}s  {txt}\n' for t, txt in rec['events'])

    if png and meta:
        K = 8
        img = Image.open(io.BytesIO(png)).convert('RGB')
        img = img.resize((img.width * K, img.height * K), Image.NEAREST)
        d = ImageDraw.Draw(img)
        pts = [tuple(c * K for c in world_to_px(x, y, meta)) for _, x, y in rec['path']]
        if len(pts) > 1:
            d.line(pts, fill=(220, 40, 40), width=3)
        for sel, col in ((pts[:1], (30, 170, 60)), (pts[-1:], (40, 90, 220))):
            for x, y in sel:
                d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=col, width=3)
        img.save(base + '_map.png')
    rospy.loginfo('[explore] 紀錄已寫入 %s_*', base)


def auto_explore_waiter():
    """~auto_explore=true：等地圖、車子位置、move_base 都就緒，再以倒數方式開始自動建圖。"""
    while not rospy.is_shutdown():
        with map_lock:
            ready = map_data.get('data') is not None
        with robot_lock:
            ready = ready and robot_pos['x'] is not None
        if ready and _mb_client(2.0) is not None:
            break
        time.sleep(1.0)
    ok, msg = explore_start(delay=EXPLORE_DELAY)
    rospy.loginfo('[explore] 自動建圖：%s', msg)


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


def _cov_ev(text):
    """覆蓋任務事件（相對任務開始秒數），寫進紀錄檔。"""
    with cov_lock:
        if 'events' in cov_rec and len(cov_rec['events']) < 3000:
            cov_rec['events'].append((round(time.time() - cov_rec['t_start'], 1), text))


def _wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def _drive(v, w):
    tw = Twist()
    tw.linear.x, tw.angular.z = v, w
    cmd_pub.publish(tw)


def _follow_line(fid, p0, p1, stop_at_end=True):
    """
    自己控制車子從 p0 沿直線開到 p1（不經 move_base／DWA），回傳 'ok' / 'blocked' / 'stalled' / 'stopped'。

    1. 方向誤差大於 ROT_START 先原地轉正（轉到 ROT_TOL 內）
    2. 直行：角速度 = K_HEAD ×（方向誤差 + atan(K_CTE × 側向偏移 / 速度)），把車拉回線上（Stanley 式）
       接近線尾減速；stop_at_end=False（下一段幾乎同方向）時不減速、到了直接交棒
    3. 行進方向雷射太近 → 'blocked'；位移與轉角都沒進展超過 STALL_SEC → 'stalled'
    掃描線、外圈都在去雜點＋安全邊距後的可走區內，所以直線本身不會撞牆；雷射檢查是防地圖上沒有的東西。
    """
    if cmd_pub is None:
        return 'stalled'
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1e-3:
        return 'ok'
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    heading = math.atan2(uy, ux)
    rate = rospy.Rate(20)
    anchor, anchor_t = None, rospy.get_time()
    rotating = None
    t_limit = rospy.get_time() + L / LINE_V_MIN + 15.0

    def running():
        with cov_lock:
            return cov_status['state'] == 'running'

    try:
        while not rospy.is_shutdown():
            if not running():
                return 'stopped'
            pose = _robot_pose(fid)
            now = rospy.get_time()
            if pose is None:
                _drive(0.0, 0.0)
                rate.sleep()
                continue
            px, py, yaw = pose
            s_along = (px - x0) * ux + (py - y0) * uy        # 沿線已走距離
            cte = -(px - x0) * uy + (py - y0) * ux           # 側向偏移（車在線左側為正）
            remain = L - s_along
            eh = _wrap(heading - yaw)

            if remain <= (LINE_TOL if stop_at_end else 0.05):
                return 'ok'

            # 停滯偵測（同 _go_to）
            if (anchor is None or math.hypot(px - anchor[0], py - anchor[1]) > STALL_DIST
                    or abs(_wrap(yaw - anchor[2])) > STALL_YAW):
                anchor, anchor_t = pose, now
            elif now - anchor_t > STALL_SEC:
                return 'stalled'
            if now > t_limit:
                return 'stalled'

            # 1. 原地轉正
            if rotating is None:
                rotating = abs(eh) > ROT_START
            if rotating:
                if abs(eh) < ROT_TOL:
                    rotating = False
                else:
                    w = max(ROT_W_MIN, min(ROT_W_MAX, 1.5 * abs(eh)))
                    _drive(0.0, math.copysign(w, eh))
                    rate.sleep()
                    continue

            # 2. 直行
            near = _scan_min(0.0, math.radians(20))
            if near is not None and near < FRONT_STOP:
                return 'blocked'
            v = LINE_V if not stop_at_end else max(LINE_V_MIN, min(LINE_V, 1.2 * remain))
            steer = eh - math.atan2(LINE_K_CTE * cte, v + 0.05)
            w = max(-LINE_W_MAX, min(LINE_W_MAX, LINE_K_HEAD * steer))
            if abs(eh) > 0.6:                                # 偏太多：先別往前衝
                v = 0.0
            _drive(v, w)
            rate.sleep()
        return 'stopped'
    finally:
        if stop_at_end:
            _drive(0.0, 0.0)


def _nav_plan(fid, start, goal):
    """
    只借用 move_base 的全域規劃器（/move_base/make_plan，依全域 costmap 繞開障礙）算路線，
    不讓它開車。回傳簡化後的折線 [(x, y), ...]，失敗回傳 None。
    """
    try:
        rospy.wait_for_service('/move_base/make_plan', timeout=2.0)
        srv = rospy.ServiceProxy('/move_base/make_plan', GetPlan)
        req = []
        for (px, py) in (start, goal):
            ps = PoseStamped()
            ps.header.frame_id = fid
            ps.header.stamp = rospy.Time(0)
            ps.pose.position.x, ps.pose.position.y = px, py
            ps.pose.orientation.w = 1.0
            req.append(ps)
        resp = srv(start=req[0], goal=req[1], tolerance=0.1)
    except Exception as e:
        rospy.logwarn('[coverage] make_plan 失敗：%s', e)
        return None
    pts = np.array([(p.pose.position.x, p.pose.position.y) for p in resp.plan.poses], dtype=float)
    if len(pts) < 2:
        return None
    simp = _rdp(pts, NAV_RDP_EPS)
    out = [(float(a), float(b)) for a, b in simp]
    out[-1] = (float(goal[0]), float(goal[1]))          # make_plan 有容許誤差，終點用真正的路點
    return out


def _drive_to(fid, x, y):
    """
    自己開到 (x, y)，不經 DWA：
      1. 從目前位置到目標的直線整段都在規劃用可走區內 → 直接直線循跡
      2. 否則向 move_base 要一條繞開障礙的路線，逐段直線循跡
    回傳 'ok' / 'blocked' / 'stalled' / 'failed'（要不到路線）/ 'stopped'。
    """
    pose = _robot_pose(fid)
    if pose is None:
        return 'stalled'
    start = (pose[0], pose[1])
    with cov_lock:
        g = dict(cov_grid)
    if g and _seg_free(g['free'], g['res'], g['ox'], g['oy'], start, (x, y)):
        pts = [start, (x, y)]
    else:
        pts = _nav_plan(fid, start, (x, y))
        if not pts:
            return 'failed'
        pts[0] = start
    for k in range(1, len(pts)):
        keep = False
        if k + 1 < len(pts):
            h0 = math.atan2(pts[k][1] - pts[k - 1][1], pts[k][0] - pts[k - 1][0])
            h1 = math.atan2(pts[k + 1][1] - pts[k][1], pts[k + 1][0] - pts[k][0])
            keep = abs(_wrap(h1 - h0)) < TURN_KEEP
        r = _follow_line(fid, pts[k - 1], pts[k], stop_at_end=not keep)
        if r != 'ok':
            return r
    return 'ok'


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
        if cmd_pub is not None:
            cmd_pub.publish(Twist())                   # 直線循跡中被中斷也要停車
        _log_run()
        try:
            _cov_write_log()
        except Exception as e:
            rospy.logerr('[coverage] 寫紀錄失敗：%s', e)


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
        kind = list(cov_kind) if len(cov_kind) == len(cov_path) else ['move'] * len(cov_path)
        fid  = map_data.get('frame_id', 'map')
        cov_status.update(state='running', total=len(path), done=start_idx, msg='')
    _cov_ev(f'開始執行（從路點 {start_idx + 1}/{len(path)}）')

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

        # 直線循跡的條件：這段是 line、而且車子就在上一個路點附近（剛跳過的點後面接 line 不算）
        pose = _robot_pose(fid)
        use_line = (kind[i] == 'line' and i > 0 and pose is not None
                    and math.hypot(pose[0] - path[i - 1][0], pose[1] - path[i - 1][1]) < 0.20)
        if use_line:
            nxt_line = i + 1 < n and kind[i + 1] == 'line'
            keep = nxt_line and abs(_wrap(math.atan2(path[i + 1][1] - y, path[i + 1][0] - x)
                                          - math.atan2(y - path[i - 1][1], x - path[i - 1][0]))) < TURN_KEEP
        t_wp = time.time()

        # 依序嘗試（前一種失敗才換下一種）：
        #   line      沿規劃的掃描線直行（只有 kind=line 且車子就在上一點旁）
        #   own_nav   自己開：直線可走就直走，否則借 move_base 算路線、自己照著開（不經 DWA）
        #   move_base 交給 move_base（含 DWA）開；第二次以後先脫困
        # 2026-11-11 實測：跨區段交給 move_base 時，車子離牆 0.20 m 就被 DWA 判定「轉身會撞」而僵住，
        # 所以把 move_base 退到備援。
        methods = (['line'] if use_line else []) + ['own_nav'] + ['move_base'] * RETRY_MAX
        reached, method, why = False, '', ''
        for attempt, method in enumerate(methods):
            if method in ('line', 'own_nav'):
                client.cancel_all_goals()                # 確保 move_base 沒有在同時開車
            with cov_lock:
                cov_rec['mode'] = method
            if method == 'line':
                result = _follow_line(fid, path[i - 1], (x, y), stop_at_end=not keep)
            elif method == 'own_nav':
                result = _drive_to(fid, x, y)
            else:
                if methods[attempt - 1] == 'move_base':  # move_base 已失敗過一次 → 先脫困
                    with cov_lock:
                        cov_status['msg'] = f'路點 {i+1}/{n} {why}，脫困後重試'
                    _escape(fid)
                result = _go_to(client, fid, x, y, yaw, near=VIA_NEAR if via[i] else None)
            if result == 'stopped':
                return
            pose = _robot_pose(fid)
            if result == 'ok' or (pose is not None
                                  and math.hypot(pose[0] - x, pose[1] - y) < GOAL_NEAR):
                reached = True
                break
            why = {'stalled': '停滯', 'blocked': '前方有障礙', 'failed': '無法規劃路線'}.get(result, '無法到達')
            if attempt + 1 < len(methods):
                nxt = methods[attempt + 1]
                _cov_ev(f'路點 {i+1}/{n} {method} {why}，改用 {nxt}')
                rospy.logwarn(f'[coverage] 路點 {i+1}/{n} {method} {why}，改用 {nxt}')

        if reached:
            fails, fail_pose = 0, None
            _cov_ev(f'到達 {i+1}/{n}（{method}，{time.time() - t_wp:.1f}s）')
            continue

        _cov_ev(f'跳過 {i+1}/{n}（{why}）')
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
        _cov_ev(f'受困停止於路點 {first+1}/{n}')
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
    _cov_ev('全部路點完成')


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
        'n_noise':    info.get('n_noise'),
    }


def _log_run():
    """把本次執行的指標追加到 RUN_LOG（utf-8-sig，Excel 直接開不會亂碼）。"""
    m = cov_metrics()
    if not m['task']:
        return
    row = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), **m}
    try:
        os.makedirs(os.path.dirname(RUN_LOG), exist_ok=True)
        if os.path.exists(RUN_LOG):
            with open(RUN_LOG, encoding='utf-8-sig') as f:
                header = f.readline().strip().split(',')
            if header != list(row):                # 欄位改過：舊檔改名保留，另開新檔
                os.replace(RUN_LOG, RUN_LOG.replace('.csv', time.strftime('_old_%Y%m%d%H%M%S.csv')))
        new = not os.path.exists(RUN_LOG)
        with open(RUN_LOG, 'a', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)
    except OSError as e:
        rospy.logwarn('[coverage] 寫入 %s 失敗：%s', RUN_LOG, e)


def _cov_write_log():
    """
    覆蓋任務每次結束（完成、停止、受困皆然）覆寫同一任務的紀錄（停止後繼續會累積）：
      data/coverage/<task>_path.csv      行走軌跡（每 5 cm）
      data/coverage/<task>_timeline.csv  每秒：路點進度、控制方式（line/move）、位置朝向、電壓
      data/coverage/<task>_events.txt    指標摘要＋事件（到達、改用 move_base、跳過、受困…）
      data/coverage/<task>_map.png       地圖＋規劃路線（紫細線）＋實際掃過範圍（綠，車身寬）＋軌跡（紅）＋跳過（✕）
    """
    with cov_lock:
        if 'task' not in cov_rec:
            return
        rec = {k: (list(v) if isinstance(v, list) else v) for k, v in cov_rec.items()}
        plan_w, skips = list(cov_path), [list(x) for x in cov_skips]
    out_dir = os.path.join(PKG, 'data', 'coverage')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, rec['task'])
    m = cov_metrics()

    with open(base + '_path.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['t_s', 'x', 'y'])
        w.writerows(rec['path'])
    with open(base + '_timeline.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['t_s', 'waypoint', 'mode', 'x', 'y', 'yaw_deg', 'battery_v'])
        w.writerows(rec['timeline'])
    with open(base + '_events.txt', 'w', encoding='utf-8') as f:
        f.write(json.dumps(m, ensure_ascii=False, indent=2) + '\n\n')
        f.writelines(f'{t:7.1f}s  {txt}\n' for t, txt in rec['events'])

    with map_lock:
        png, meta = map_png, dict(map_meta)
    if not (png and meta):
        return
    K = 8
    img = Image.open(io.BytesIO(png)).convert('RGB')
    img = img.resize((img.width * K, img.height * K), Image.NEAREST)
    over = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    to_px = lambda x, y: tuple(c * K for c in world_to_px(x, y, meta))
    pts = [to_px(x, y) for _, x, y in rec['path']]
    sw = max(1, round(2 * COV_COVER_R / meta['resolution'] * K))
    if len(pts) > 1:
        d.line(pts, fill=(40, 180, 80, 110), width=sw, joint='curve')
    plan_px = [to_px(x, y) for x, y in plan_w]
    if len(plan_px) > 1:
        d.line(plan_px, fill=(170, 60, 220, 200), width=1)
    if len(pts) > 1:
        d.line(pts, fill=(220, 40, 40, 255), width=2)
    for idx, _why in skips:
        if 0 <= idx < len(plan_px):
            x, y = plan_px[idx]
            d.line((x - 6, y - 6, x + 6, y + 6), fill=(255, 140, 0, 255), width=3)
            d.line((x - 6, y + 6, x + 6, y - 6), fill=(255, 140, 0, 255), width=3)
    Image.alpha_composite(img.convert('RGBA'), over).convert('RGB').save(base + '_map.png')
    rospy.loginfo('[coverage] 紀錄已寫入 %s_*', base)


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


@app.route('/map_noise.png')
def get_map_noise():
    """規劃時被當成雜點忽略的格子（黑＝雜點）。"""
    with map_lock: d = map_noise
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
    if _exploring():
        return jsonify({'ok': False, 'msg': '自動建圖中，請等建圖完成或先按停止'})
    with cov_lock:
        if cov_status['state'] == 'running':
            return jsonify({'ok': False, 'msg': '已在執行中'})

    with map_lock:
        meta = dict(map_meta)
        raw  = dict(map_data)

    if not meta or raw.get('data') is None:
        return jsonify({'ok': False, 'msg': '地圖尚未就緒'})

    teleop_halt()                                  # 交出 /cmd_vel 控制權前先停車

    t_plan = time.perf_counter()                   # 規劃時間含去雜點與安全邊距膨脹
    clean, noise = remove_noise(raw['data'])       # SLAM 留下的零星假障礙不列入規劃
    safe = apply_safety_margin(clean, COV_MARGIN, meta['resolution'])
    free = (clean == 0) & ~safe

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
        cov_kind[:]  = r['kind']
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
            n_noise    = int(noise.sum()),
        )
        cov_status.update(state='running', done=0, total=len(r['waypoints']), msg='')
        cov_rec.clear()
        cov_rec.update(task=cov_info['task'], t_start=time.time(), t_tl=0.0, mode='',
                       events=[], timeline=[], path=[])
    _cov_ev(f"規劃完成：路點 {len(r['waypoints'])}（直線 {r['kind'].count('line')}、導航 {r['kind'].count('move')}），"
            f"外圈頂點 {len(r['perimeter'])}，雜點 {int(noise.sum())} 格")

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
    if _exploring():
        return jsonify({'ok': False, 'msg': '自動建圖中，請等建圖完成或先按停止'})
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
    st['manual'] = manual_allowed()
    st['slam_managed'] = slam_cfg['manage']
    st['explore'] = explore_snapshot()
    st['cover_r'] = COV_COVER_R
    return jsonify(st)


def explore_snapshot():
    with exp_lock:
        ex = {k: v for k, v in exp_status.items() if k != 't0'}
        if exp_status['state'] == 'exploring' and exp_status['t0']:
            ex['elapsed'] = round(time.time() - exp_status['t0'], 1)
    with map_lock:
        ex.update(area=map_stats['area'], frontiers=map_stats['frontiers'])
    ex['busy'] = ex['state'] in EXP_BUSY
    ex['max_s'] = EXPLORE_MAX_S
    return ex


@app.route('/explore/start', methods=['POST'])
def explore_start_route():
    ok, msg = explore_start()
    return jsonify({'ok': ok, 'msg': msg}), (200 if ok else 409)


@app.route('/explore/stop', methods=['POST'])
def explore_stop_route():
    explore_stop()
    return jsonify({'ok': True, 'msg': '已停止自動建圖'})


@app.route('/teleop', methods=['POST'])
def teleop():
    """手動遙控。body: {v: -1..1, w: -1..1}（比例值，後端乘上速度上限）。"""
    if not manual_allowed():
        return jsonify({'ok': False, 'msg': '自動執行中（覆蓋或建圖），請先按結束／停止'}), 409

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
    global map_png, map_eroded, map_dilated, map_margin, map_noise

    if not slam_cfg['manage']:
        return jsonify({'ok': False,
                        'msg': 'SLAM 不由本節點管理（manage_slam=false），請手動重啟'}), 400

    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status['state'] = 'stopped'
    explore_stop('重新建圖，自動建圖已停止')
    teleop_halt()

    with slam_lock:
        slam_kill()

        with map_lock:
            map_png = map_eroded = map_dilated = map_margin = map_noise = None
            map_meta.clear()
            map_data.clear()
        with robot_lock:
            robot_path.clear()
            robot_pos.update(x=None, y=None)
        with cov_lock:
            cov_path[:]  = []
            cov_via[:]   = []
            cov_kind[:]  = []
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
    auto_explore = bool(rospy.get_param('~auto_explore', False))

    if not HAS_MB:
        rospy.logwarn('未安裝 move_base_msgs，覆蓋執行功能不可用')

    tf_buffer = tf2_ros.Buffer()
    tf2_ros.TransformListener(tf_buffer)

    cmd_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)

    rospy.Subscriber('/map',  OccupancyGrid, map_callback,  queue_size=1)
    rospy.Subscriber('/scan', LaserScan,     scan_callback, queue_size=1)
    rospy.Subscriber('/rosout_agg', Log,          rosout_callback,  queue_size=50)
    rospy.Subscriber('/battery_state', BatteryState, battery_callback, queue_size=1)
    rospy.on_shutdown(explore_kill)

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
    if auto_explore:
        rospy.loginfo('[explore] auto_explore=true：地圖與 move_base 就緒後自動開始建圖')
        threading.Thread(target=auto_explore_waiter, daemon=True).start()
    rospy.spin()


if __name__ == '__main__':
    main()
