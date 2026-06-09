#!/usr/bin/env python3
"""
TurtleBot3 地圖伺服器（Module A）
  - 訂閱 /map  → 提供原始 / 侵蝕 / 膨脹地圖 PNG
  - 訂閱 /odom → 提供機器人位置與軌跡
  - /coverage/start|stop|status → 牛耕式路徑規劃 + move_base 執行
路徑規劃核心由 coverage_planner 模組提供。
"""
import io, math, os, socket, sys, threading

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from coverage_planner import boustrophedon, SPACING as COV_SPACING, MARGIN as COV_MARGIN, apply_safety_margin

import numpy as np
import rospkg, rospy
from flask import Flask, Response, jsonify, send_file
from nav_msgs.msg import OccupancyGrid, Odometry
from PIL import Image
from scipy.ndimage import binary_erosion

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

str_time = None
last_prt_time = None
count = 0

# ════════════════════════════════════════════════════════
#  可調參數
# ════════════════════════════════════════════════════════
CROP_PAD = 10     # 地圖裁切邊距（格）
# COV_SPACING / COV_MARGIN 來自 coverage_planner 模組
# 注：侵蝕/膨脹層現已改為動態計算，使用 COV_MARGIN 的核大小以與路徑規劃同步

# ════════════════════════════════════════════════════════
#  共享狀態
# ════════════════════════════════════════════════════════
map_lock = threading.Lock()
map_png = map_eroded = map_dilated = None
map_meta = {}   # resolution, origin_x/y, r0, c0, crop_h
map_data = {}   # data(np array), h, w, frame_id  ← 供覆蓋規劃用

robot_lock = threading.Lock()
robot_pos  = {'x': None, 'y': None}   # 世界座標
robot_path = []   # [[wx, wy], ...]

cov_lock   = threading.Lock()
cov_status = {'state': 'idle', 'done': 0, 'total': 0, 'msg': ''}
cov_path   = []   # [(wx, wy), ...]  世界座標


# ════════════════════════════════════════════════════════
#  地圖處理
# ════════════════════════════════════════════════════════
def _to_png(arr):
    """把灰階陣列上下翻轉後編碼成 PNG bytes（翻轉是為了配合影像 Y 軸向下）。"""
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
    """收到 /map 時轉出原始/侵蝕/膨脹三種圖層、裁切至已知區域並更新共享狀態。"""
    global map_png, map_eroded, map_dilated, map_meta, map_data


    global str_time, last_prt_time, count

    if str_time is None:
        str_time = rospy.get_time()
        last_prt_time = str_time

    count += 1
    curr_time = rospy.get_time()

    if curr_time - last_prt_time >= 2.0:
        elapsed = curr_time - str_time
        avg_freq = count / elapsed
        print(f"收到訊息總數: {count} | 總運行時間: {elapsed:.2f}s | 平均頻率: {avg_freq:.2f} Hz")
        print (f"地圖尺寸: {msg.info.width} x {msg.info.height}")
        last_prt_time = curr_time



    w, h = msg.info.width, msg.info.height
    if w == 0 or h == 0:
        return

    res = msg.info.resolution
    data  = np.array(msg.data, dtype=np.int8).reshape((h, w)).astype(np.int16)
    known = data >= 0
    obs   = data == 100
    free  = data == 0

    # 安全邊距：膨脹層直接用路徑規劃的同一函式 apply_safety_margin，
    # 保證「網頁看到的膨脹」= 機器人實際避開的區域（單一真相來源）。
    safe_obs = apply_safety_margin(data, COV_MARGIN, res)
    # 侵蝕層用相同尺寸的核（純視覺化參考，路徑規劃無對應物）
    r_safety    = max(1, round(COV_MARGIN / res))
    kern_safety = np.ones((2 * r_safety + 1, 2 * r_safety + 1), dtype=bool)

    # 原始地圖灰階
    gray = np.full((h, w), 128, dtype=np.uint8)
    gray[known] = np.clip(255 - data[known] * 255 // 100, 0, 255).astype(np.uint8)

    # 侵蝕地圖（障礙縮小）
    gray_e = np.full((h, w), 128, dtype=np.uint8)
    gray_e[free] = 255
    gray_e[binary_erosion(obs, kern_safety, 1)] = 0

    # 膨脹地圖 = 路徑規劃實際避開的安全邊距區（與規劃同步）
    gray_d = np.full((h, w), 128, dtype=np.uint8)
    gray_d[free] = 255
    gray_d[safe_obs] = 0

    r0, r1, c0, c1 = _crop(known, h, w)

    with map_lock:
        map_png     = _to_png(gray[r0:r1, c0:c1])
        map_eroded  = _to_png(gray_e[r0:r1, c0:c1])
        map_dilated = _to_png(gray_d[r0:r1, c0:c1])
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
    """收到 /odom 時更新機器人位置，並每移動 0.1 m 記錄一個軌跡點。"""
    rx = msg.pose.pose.position.x
    ry = msg.pose.pose.position.y

    with robot_lock:
        robot_pos.update(x=rx, y=ry)
        if not robot_path:
            robot_path.append([rx, ry])
        else:
            dx, dy = rx - robot_path[-1][0], ry - robot_path[-1][1]
            if dx*dx + dy*dy >= 0.01:   # 每 0.1 m 記一點
                robot_path.append([rx, ry])
                if len(robot_path) > 10000:
                    robot_path.pop(0)


# ════════════════════════════════════════════════════════
#  move_base 執行執行緒
# ════════════════════════════════════════════════════════
def _yaw_to_quat(yaw):
    """偏航角 → 四元數 (z, w)。"""
    return math.sin(yaw / 2), math.cos(yaw / 2)


def run_coverage():
    """依序把路點送給 move_base，可隨時被 stop 中斷。"""
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
        path  = list(cov_path)
        fid   = map_data.get('frame_id', 'map')
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

        # 送出目標
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
    """把 PNG bytes 包成不快取的 HTTP 回應；無資料則回 503。"""
    if data is None:
        return Response('等待地圖...', status=503)
    resp = send_file(io.BytesIO(data), mimetype='image/png')
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/')
def index():
    """回傳前端網頁 index.html。"""
    p = os.path.join(PKG, 'web', 'index.html')
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ('找不到 index.html', 404)

@app.route('/map.png')
def get_map():
    """提供原始地圖 PNG。"""
    with map_lock: d = map_png
    return _serve_png(d)

@app.route('/map_eroded.png')
def get_map_eroded():
    """提供侵蝕地圖 PNG（障礙縮小）。"""
    with map_lock: d = map_eroded
    return _serve_png(d)

@app.route('/map_dilated.png')
def get_map_dilated():
    """提供膨脹地圖 PNG（障礙放大）。"""
    with map_lock: d = map_dilated
    return _serve_png(d)


@app.route('/robot_state')
def get_robot_state():
    """回傳機器人當前位置與行走軌跡（換算為裁切後圖片像素座標）。"""
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


@app.route('/coverage/start', methods=['POST'])
def coverage_start():
    """規劃覆蓋路徑並啟動背景執行緒開始執行；已在執行或地圖未就緒則拒絕。"""
    global cov_path

    with cov_lock:
        if cov_status['state'] == 'running':
            return jsonify({'ok': False, 'msg': '已在執行中'})

    with map_lock:
        meta = dict(map_meta)
        raw  = dict(map_data)

    if not meta or raw.get('data') is None:
        return jsonify({'ok': False, 'msg': '地圖尚未就緒'})

    safe_obs = apply_safety_margin(raw['data'], COV_MARGIN, meta['resolution'])
    free     = (raw['data'] == 0) & ~safe_obs

    pts = boustrophedon(free, meta['resolution'], meta['origin_x'], meta['origin_y'])
    if not pts:
        return jsonify({'ok': False, 'msg': '無可走路徑，地圖可能不完整'})

    with cov_lock:
        cov_path[:] = pts
        cov_status.update(state='idle', done=0, total=len(pts), msg='')

    threading.Thread(target=run_coverage, daemon=True).start()
    return jsonify({'ok': True, 'total': len(pts)})


@app.route('/coverage/stop', methods=['POST'])
def coverage_stop():
    """請求停止覆蓋任務（合作式取消，由執行緒下一輪檢查時生效）。"""
    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status['state'] = 'stopped'
    return jsonify({'ok': True})


@app.route('/coverage/status')
def coverage_status():
    """回傳覆蓋任務狀態與路徑（換算為圖片像素座標）。"""
    with cov_lock:   st = dict(cov_status); path_w = list(cov_path)
    with map_lock:   meta = dict(map_meta)

    st['path_px'] = [list(world_to_px(x, y, meta)) for x, y in path_w] if meta else []
    return jsonify(st)


# ════════════════════════════════════════════════════════
#  主函式
# ════════════════════════════════════════════════════════
def main():
    """初始化節點、訂閱 /map 與 /odom，並在背景啟動 Flask 網頁伺服器。"""
    rospy.init_node('map_server')
    port = rospy.get_param('~port', 8080)

    if not HAS_MB:
        rospy.logwarn('未安裝 move_base_msgs，覆蓋執行功能不可用')

    rospy.Subscriber('/map',  OccupancyGrid, map_callback,  queue_size=1)
    rospy.Subscriber('/odom', Odometry,      odom_callback, queue_size=10)

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
