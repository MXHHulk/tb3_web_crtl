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


def _world_to_px(wx, wy, meta):
    """世界座標 → 裁切後圖片像素座標（Y 已翻轉，對應 canvas 座標系）。"""
    px = (wx - meta['origin_x']) / meta['resolution'] - meta['c0']
    py = meta['crop_h'] - ((wy - meta['origin_y']) / meta['resolution'] - meta['r0'])
    return round(px, 1), round(py, 1)


def map_callback(msg):
    global map_png, map_eroded, map_dilated, map_meta

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
        'path': path_px,
    })


# ── 主函式 ────────────────────────────────────────────────────────────────────

def main():
    rospy.init_node('map_server')
    port = rospy.get_param('~port', 8080)

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
