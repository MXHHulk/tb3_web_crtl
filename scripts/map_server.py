#!/usr/bin/env python3
import io
import os
import socket
import threading

import numpy as np
import rospkg
import rospy
from flask import Flask, Response, send_file
from nav_msgs.msg import OccupancyGrid
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion

# ── 找到 package 根目錄 ─────────────────────────────────────────────────────
try:
    PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')
except rospkg.ResourceNotFound:
    PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

app = Flask(__name__)

# ── 三張地圖的 PNG bytes，用 Lock 保護多執行緒存取 ───────────────────────────
map_png     = None   # 原始地圖
map_eroded  = None   # 侵蝕後地圖（障礙物縮小）
map_dilated = None   # 膨脹後地圖（障礙物擴大）
map_lock    = threading.Lock()

# 形態學運算的結構元素（3×3 方形 kernel）
STRUCT = np.ones((3, 3), dtype=bool)
MORPH_ITER = 3   # 運算次數，越大效果越明顯


def _to_png(gray):
    """numpy 灰階陣列 → PNG bytes（含上下翻轉）。"""
    buf = io.BytesIO()
    Image.fromarray(np.flipud(gray), 'L').save(buf, format='PNG')
    return buf.getvalue()


def map_callback(msg):
    """ROS /map 回調：產生原始、侵蝕、膨脹三張地圖。"""
    global map_png, map_eroded, map_dilated

    w, h = msg.info.width, msg.info.height
    if w == 0 or h == 0:
        return

    data = np.array(msg.data, dtype=np.int8).reshape((h, w)).astype(np.int16)

    # ── 原始地圖 ─────────────────────────────────────────────────────────────
    gray = np.full((h, w), 128, dtype=np.uint8)   # 預設灰（未知）
    known = data >= 0
    gray[known] = np.clip(255 - data[known] * 255 // 100, 0, 255).astype(np.uint8)

    # ── 形態學運算用的遮罩 ────────────────────────────────────────────────────
    obstacle = (data == 100)   # True = 障礙物格子
    free     = (data == 0)     # True = 空地格子

    # ── 侵蝕（障礙物縮小）────────────────────────────────────────────────────
    # binary_erosion：把 obstacle 區域向內縮，邊緣的障礙物格子會消失
    eroded_obstacle = binary_erosion(obstacle, structure=STRUCT, iterations=MORPH_ITER)
    gray_e = np.full((h, w), 128, dtype=np.uint8)
    gray_e[free]            = 255   # 空地白色
    gray_e[eroded_obstacle] = 0     # 縮小後的障礙物黑色

    # ── 膨脹（障礙物擴大）────────────────────────────────────────────────────
    # binary_dilation：把 obstacle 區域向外擴，障礙物周圍的空地格子也變成障礙
    dilated_obstacle = binary_dilation(obstacle, structure=STRUCT, iterations=MORPH_ITER)
    gray_d = np.full((h, w), 128, dtype=np.uint8)
    gray_d[free]             = 255   # 空地白色
    gray_d[dilated_obstacle] = 0     # 膨脹後的障礙物黑色

    with map_lock:
        map_png     = _to_png(gray)
        map_eroded  = _to_png(gray_e)
        map_dilated = _to_png(gray_d)


# ── Flask 路由 ────────────────────────────────────────────────────────────────

def _serve(png_bytes):
    """共用：把 PNG bytes 包成 HTTP 回應。"""
    if png_bytes is None:
        return Response('等待地圖資料...', status=503)
    resp = send_file(io.BytesIO(png_bytes), mimetype='image/png')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp


@app.route('/')
def index():
    index_path = os.path.join(PKG, 'web', 'index.html')
    if not os.path.exists(index_path):
        return '<h3>找不到 web/index.html</h3>', 404
    with open(index_path, encoding='utf-8') as f:
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


# ── 主函式 ────────────────────────────────────────────────────────────────────

def main():
    rospy.init_node('map_server')
    port = rospy.get_param('~port', 8080)

    rospy.Subscriber('/map', OccupancyGrid, map_callback, queue_size=1)

    try:
        ip = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        ip = '127.0.0.1'

    rospy.loginfo(f'地圖伺服器已啟動 → http://{ip}:{port}')

    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port,
                               threaded=True, use_reloader=False),
        daemon=True
    ).start()

    rospy.spin()


if __name__ == '__main__':
    main()
