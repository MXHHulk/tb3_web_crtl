#!/usr/bin/env python3
import io
import math
import os
import socket
import threading

import numpy as np
import rospkg
import rospy
from flask import Flask, Response, jsonify, send_file
from nav_msgs.msg import OccupancyGrid, Odometry
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion

try:
    import actionlib
    from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
    _HAS_MB = True
except ImportError:
    _HAS_MB = False

try:
    PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')
except rospkg.ResourceNotFound:
    PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

app = Flask(__name__)

# ── 地圖 PNG bytes ────────────────────────────────────────────────────────────
map_png     = None
map_eroded  = None
map_dilated = None
map_lock    = threading.Lock()
map_meta    = {}   # resolution, origin_x/y, r0, c0, crop_h, crop_w

# ── 機器人狀態（世界座標儲存，轉換時才換成像素）────────────────────────────────
robot_lock       = threading.Lock()
robot_pos_world  = {'x': None, 'y': None, 'yaw': 0.0}
robot_path_world = []          # list of [world_x, world_y]
MAX_PATH_PTS     = 10000
MIN_DIST_SQ      = 0.01        # 點與點最小間距 0.1 m

STRUCT     = np.ones((3, 3), dtype=bool)
MORPH_ITER = 3
CROP_PAD   = 10

# ── 覆蓋路徑相關 ──────────────────────────────────────────────────────────────
COV_LINE = 0.3    # 掃描線間距（公尺）= 機器人直徑
COV_EROD = 0.15   # 侵蝕半徑（公尺）= 機器人半徑

cov_lock   = threading.Lock()
cov_status = {'state': 'idle', 'done': 0, 'total': 0, 'msg': ''}
cov_path_w = []          # 覆蓋路徑（世界座標）
cov_thread = None
map_raw    = None        # 最新地圖原始資料（供規劃用）


def _to_png(arr):
    buf = io.BytesIO()
    Image.fromarray(np.flipud(arr), 'L').save(buf, format='PNG')
    return buf.getvalue()


def _crop_box(known, h, w):
    rows = np.any(known, axis=1)
    cols = np.any(known, axis=0)
    if not rows.any():
        return 0, h, 0, w
    r0 = max(np.argmax(rows) - CROP_PAD, 0)
    r1 = min(h - np.argmax(rows[::-1]) + CROP_PAD, h)
    c0 = max(np.argmax(cols) - CROP_PAD, 0)
    c1 = min(w - np.argmax(cols[::-1]) + CROP_PAD, w)
    return r0, r1, c0, c1


def _boustrophedon(free, res, ox, oy):
    """牛耕式掃描：回傳世界座標路點列表 [(x,y), ...]。"""
    h, w  = free.shape
    step  = max(1, round(COV_LINE / res))
    pts, l2r = [], True

    for row in range(step // 2, h, step):
        segs, s0 = [], None
        for c in range(w):
            if free[row, c] and s0 is None:
                s0 = c
            elif not free[row, c] and s0 is not None:
                segs.append((s0, c - 1)); s0 = None
        if s0 is not None:
            segs.append((s0, w - 1))
        if not segs:
            continue
        if not l2r:
            segs = [(e, s) for s, e in reversed(segs)]
        for s, e in segs:
            for c in ([s, e] if s != e else [s]):
                pts.append((ox + c * res, oy + row * res))
        l2r = not l2r
    return pts


def _run_coverage():
    """在獨立執行緒中依序把路點送給 move_base。"""
    global cov_status

    if not _HAS_MB:
        with cov_lock:
            cov_status.update(state='error', msg='缺少 move_base_msgs，請安裝')
        return

    client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    if not client.wait_for_server(rospy.Duration(5.0)):
        with cov_lock:
            cov_status.update(state='error', msg='move_base 未回應（逾時 5 秒）')
        return

    with cov_lock:
        path = list(cov_path_w)
        fid  = map_raw['frame_id'] if map_raw else 'map'
        cov_status.update(state='running', total=len(path), done=0, msg='')

    for i, (x, y) in enumerate(path):
        with cov_lock:
            if cov_status['state'] != 'running':
                client.cancel_goal()
                return
            cov_status['done'] = i

        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = fid
        goal.target_pose.header.stamp    = rospy.Time.now()
        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        goal.target_pose.pose.orientation.w = 1.0

        client.send_goal(goal)
        while not rospy.is_shutdown():
            with cov_lock:
                if cov_status['state'] != 'running':
                    client.cancel_goal()
                    return
            if client.wait_for_result(rospy.Duration(0.5)):
                break   # 到達目標，繼續下一個

    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status.update(state='done', done=len(path))


def _world_to_px(wx, wy, meta):
    """世界座標 → 裁切後圖片像素座標（Y 已翻轉，對應 canvas 座標系）。"""
    px = (wx - meta['origin_x']) / meta['resolution'] - meta['c0']
    py = meta['crop_h'] - ((wy - meta['origin_y']) / meta['resolution'] - meta['r0'])
    return round(px, 1), round(py, 1)


def map_callback(msg):
    global map_png, map_eroded, map_dilated, map_meta, map_raw

    w, h = msg.info.width, msg.info.height
    if w == 0 or h == 0:
        return

    data = np.array(msg.data, dtype=np.int8).reshape((h, w)).astype(np.int16)

    known    = data >= 0
    obstacle = data == 100
    free     = data == 0

    gray = np.full((h, w), 128, dtype=np.uint8)
    gray[known] = np.clip(255 - data[known] * 255 // 100, 0, 255).astype(np.uint8)

    eroded_obs  = binary_erosion(obstacle,  structure=STRUCT, iterations=MORPH_ITER)
    dilated_obs = binary_dilation(obstacle, structure=STRUCT, iterations=MORPH_ITER)

    gray_e = np.full((h, w), 128, dtype=np.uint8)
    gray_e[free]       = 255
    gray_e[eroded_obs] = 0

    gray_d = np.full((h, w), 128, dtype=np.uint8)
    gray_d[free]        = 255
    gray_d[dilated_obs] = 0

    r0, r1, c0, c1 = _crop_box(known, h, w)

    with map_lock:
        map_png     = _to_png(gray[r0:r1, c0:c1])
        map_eroded  = _to_png(gray_e[r0:r1, c0:c1])
        map_dilated = _to_png(gray_d[r0:r1, c0:c1])
        map_meta = {
            'resolution': msg.info.resolution,
            'origin_x':   msg.info.origin.position.x,
            'origin_y':   msg.info.origin.position.y,
            'r0': r0, 'c0': c0,
            'crop_h': r1 - r0,
            'crop_w': c1 - c0,
        }
        map_raw = {
            'data':     data,          # int16 (h, w)，供覆蓋規劃使用
            'h': h, 'w': w,
            'frame_id': msg.header.frame_id or 'map',
        }


def odom_callback(msg):
    global robot_pos_world, robot_path_world

    rx  = msg.pose.pose.position.x
    ry  = msg.pose.pose.position.y
    q   = msg.pose.pose.orientation
    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                     1 - 2 * (q.y * q.y + q.z * q.z))

    with robot_lock:
        robot_pos_world.update(x=rx, y=ry, yaw=yaw)
        path = robot_path_world
        if not path:
            path.append([rx, ry])
        else:
            dx, dy = rx - path[-1][0], ry - path[-1][1]
            if dx * dx + dy * dy >= MIN_DIST_SQ:
                path.append([rx, ry])
                if len(path) > MAX_PATH_PTS:
                    path.pop(0)


# ── Flask 路由 ────────────────────────────────────────────────────────────────

def _serve(png_bytes):
    if png_bytes is None:
        return Response('等待地圖資料...', status=503)
    resp = send_file(io.BytesIO(png_bytes), mimetype='image/png')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp


@app.route('/')
def index():
    p = os.path.join(PKG, 'web', 'index.html')
    if not os.path.exists(p):
        return '<h3>找不到 web/index.html</h3>', 404
    with open(p, encoding='utf-8') as f:
        return f.read()


@app.route('/map.png')
def get_map():
    with map_lock:
        data = map_png
    return _serve(data)


@app.route('/map_eroded.png')
def get_map_eroded():
    with map_lock:
        data = map_eroded
    return _serve(data)


@app.route('/map_dilated.png')
def get_map_dilated():
    with map_lock:
        data = map_dilated
    return _serve(data)


@app.route('/robot_state')
def get_robot_state():
    with map_lock:
        meta = dict(map_meta)
    with robot_lock:
        pos_w  = dict(robot_pos_world)
        path_w = list(robot_path_world)

    if not meta or pos_w['x'] is None:
        return jsonify({'pos': None, 'path': []})

    px, py    = _world_to_px(pos_w['x'], pos_w['y'], meta)
    img_angle = -pos_w['yaw']   # canvas Y 軸反向，所以角度也要取反

    path_px = [list(_world_to_px(p[0], p[1], meta)) for p in path_w]

    return jsonify({
        'pos': {
            'x': px, 'y': py, 'angle': img_angle,
            'wx': round(pos_w['x'], 2),
            'wy': round(pos_w['y'], 2),
            'yaw_deg': round(math.degrees(pos_w['yaw']), 1),
        },
        'path':       path_px,
        'resolution': meta['resolution'],   # 前端換算點大小用
    })


@app.route('/coverage/start', methods=['POST'])
def coverage_start():
    global cov_thread, cov_path_w, cov_status

    with cov_lock:
        if cov_status['state'] == 'running':
            return jsonify({'ok': False, 'msg': '已在執行中'})

    with map_lock:
        meta = dict(map_meta)
        raw  = dict(map_raw) if map_raw else None

    if raw is None or not meta:
        return jsonify({'ok': False, 'msg': '地圖尚未就緒'})

    # 侵蝕可走區域，保持安全距離
    free = raw['data'] == 0
    r    = max(1, round(COV_EROD / meta['resolution']))
    free = binary_erosion(free, structure=np.ones((2*r+1, 2*r+1), dtype=bool))

    pts = _boustrophedon(free, meta['resolution'], meta['origin_x'], meta['origin_y'])
    if not pts:
        return jsonify({'ok': False, 'msg': '無法規劃路徑，地圖可能尚未完成'})

    with cov_lock:
        cov_path_w[:] = pts
        cov_status.update(state='idle', done=0, total=len(pts), msg='')

    cov_thread = threading.Thread(target=_run_coverage, daemon=True)
    cov_thread.start()
    return jsonify({'ok': True, 'total': len(pts)})


@app.route('/coverage/stop', methods=['POST'])
def coverage_stop():
    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status['state'] = 'stopped'
    return jsonify({'ok': True})


@app.route('/coverage/status')
def coverage_status_route():
    with cov_lock:
        st   = dict(cov_status)
        path = list(cov_path_w)

    with map_lock:
        meta = dict(map_meta)

    st['path_px'] = (
        [list(_world_to_px(x, y, meta)) for x, y in path] if meta else []
    )
    return jsonify(st)


# ── 主函式 ────────────────────────────────────────────────────────────────────

def main():
    rospy.init_node('map_server')
    port = rospy.get_param('~port', 8080)

    if not _HAS_MB:
        rospy.logwarn('move_base_msgs 未安裝，/coverage/start 功能停用')

    rospy.Subscriber('/map',  OccupancyGrid, map_callback,  queue_size=1)
    rospy.Subscriber('/odom', Odometry,      odom_callback, queue_size=10)

    try:
        ip = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        ip = '127.0.0.1'

    rospy.loginfo(f'地圖伺服器已啟動 → http://{ip}:{port}')

    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port,
                               threaded=True, use_reloader=False),
        daemon=True,
    ).start()

    rospy.spin()


if __name__ == '__main__':
    main()
