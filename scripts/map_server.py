#!/usr/bin/env python3
"""
TurtleBot3 地圖伺服器（Module A）
  - 訂閱 /map  → 提供原始 / 侵蝕 / 顯示膨脹 / 規劃安全邊距 四種地圖 PNG
  - 訂閱 /odom → 提供機器人位置與行走軌跡
  - /coverage/start|stop|status → 牛耕式路徑規劃 + move_base 執行，並回傳 cell 分解結果
  - /teleop                     → 手動遙控（與覆蓋執行互斥）
  - /slam/restart               → 重啟 SLAM 重新建圖（本節點負責 SLAM 的生命週期）
路徑規劃核心由 coverage_planner 模組提供。

模式互斥規則（單一真相來源＝cov_status['state']）：
  state == 'running'  → 覆蓋執行中，手動遙控被拒絕
  其他狀態            → 可手動遙控
按下停止、覆蓋完成、或發生錯誤都會離開 running，自動切回可手動。
"""
import io, math, os, signal, socket, subprocess, sys, threading

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from coverage_planner import (plan as plan_coverage, SPACING as COV_SPACING,
                              MARGIN as COV_MARGIN, apply_safety_margin)

import numpy as np
import rospkg, rospy
from flask import Flask, Response, jsonify, request, send_file
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from sensor_msgs.msg import LaserScan
from PIL import Image
from scipy.ndimage import binary_erosion, binary_dilation
import tf2_ros

try:
    import actionlib
    from actionlib_msgs.msg import GoalStatus
    from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
    HAS_MB = True
except ImportError:
    HAS_MB = False

try:
    PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')
except rospkg.ResourceNotFound:
    PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

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
cov_info   = {}   # n_runs / n_cells / n_critical / axis_deg / ratio

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


def odom_callback(msg):
    rx = msg.pose.pose.position.x
    ry = msg.pose.pose.position.y

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


def run_coverage():
    """依序把路點送給 move_base，可隨時被 stop 中斷。結束時一律離開 running。"""
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
        fid  = map_data.get('frame_id', 'map')
        cov_status.update(state='running', total=len(path), done=0, msg='')

    n = len(path)
    for i, (x, y) in enumerate(path):

        # 停止檢查
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
        qz, qw = _yaw_to_quat(yaw)

        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id    = fid
        goal.target_pose.header.stamp       = rospy.Time.now()
        goal.target_pose.pose.position.x    = x
        goal.target_pose.pose.position.y    = y
        goal.target_pose.pose.orientation.z = qz
        goal.target_pose.pose.orientation.w = qw
        client.send_goal(goal)

        # 等待到達，每 0.5 秒檢查一次停止訊號
        while not rospy.is_shutdown():
            with cov_lock:
                if cov_status['state'] != 'running':
                    client.cancel_all_goals()
                    return
            if client.wait_for_result(rospy.Duration(0.5)):
                break

        # 失敗容錯：未成功到達則記錄並繼續下一點
        if client.get_state() != GoalStatus.SUCCEEDED:
            rospy.logwarn(f'[coverage] 路點 {i+1}/{n} 跳過（move_base 狀態碼 {client.get_state()}）')
            with cov_lock:
                cov_status['msg'] = f'路點 {i+1}/{n} 跳過（無法到達）'

    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status.update(state='done', done=n)


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

    safe = apply_safety_margin(raw['data'], COV_MARGIN, meta['resolution'])
    free = (raw['data'] == 0) & ~safe

    with robot_lock:
        start = (robot_pos['x'], robot_pos['y']) if robot_pos['x'] is not None else None

    r = plan_coverage(free, meta['resolution'], meta['origin_x'], meta['origin_y'],
                      start=start)
    if not r['waypoints']:
        return jsonify({'ok': False, 'msg': '無可走路徑，地圖可能不完整'})

    with robot_lock:
        robot_path.clear()          # 先清空，再切 running，軌跡才會從這一刻開始記

    center, axis_a, _, eigvals = r['axes']
    with cov_lock:
        cov_path[:]  = r['waypoints']
        cov_cells[:] = r['cells']
        cov_info.clear()
        cov_info.update(
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


@app.route('/coverage/status')
def coverage_status():
    with cov_lock:
        st     = dict(cov_status)
        path_w = list(cov_path)
        cells  = [list(c) for c in cov_cells]
        info   = dict(cov_info)
    with map_lock:
        meta = dict(map_meta)

    if meta:
        st['path_px']  = [list(world_to_px(x, y, meta)) for x, y in path_w]
        st['cells_px'] = [[list(world_to_px(x, y, meta)) for x, y in c] for c in cells]
    else:
        st['path_px'] = st['cells_px'] = []

    st['info']   = info
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
            cov_cells[:] = []
            cov_info.clear()
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
    rospy.Subscriber('/odom', Odometry,      odom_callback, queue_size=10)
    rospy.Subscriber('/scan', LaserScan,     scan_callback, queue_size=1)

    if slam_cfg['manage']:
        rospy.on_shutdown(slam_kill)
        slam_launch()
    else:
        rospy.loginfo('[slam] manage_slam=false，SLAM 由外部負責，/slam/restart 停用')

    rospy.Timer(rospy.Duration(0.1), teleop_tick)   # 10 Hz 遙控心跳

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
