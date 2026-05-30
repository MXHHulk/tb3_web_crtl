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

# ── 找到 package 根目錄（用 rospkg，不用寫死路徑）────────────────────────────
try:
    PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')
except rospkg.ResourceNotFound:
    PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

app = Flask(__name__)

# ── 最新地圖的 PNG bytes，用 Lock 保護多執行緒存取 ───────────────────────────
map_png  = None
map_lock = threading.Lock()


def map_callback(msg):
    """ROS /map 回調：把 OccupancyGrid 轉成 PNG 存進 map_png。"""
    global map_png

    w, h = msg.info.width, msg.info.height
    if w == 0 or h == 0:
        return

    # OccupancyGrid 值：-1 未知 / 0 空地 / 100 障礙物
    # 對應灰階：128 灰 / 255 白 / 0 黑
    data = np.array(msg.data, dtype=np.int8).reshape((h, w)).astype(np.int16)
    gray = np.full((h, w), 128, dtype=np.uint8)
    known = data >= 0
    gray[known] = np.clip(255 - data[known] * 255 // 100, 0, 255).astype(np.uint8)

    # ROS 地圖原點在左下角，圖片原點在左上角，翻轉修正
    gray = np.flipud(gray)

    buf = io.BytesIO()
    Image.fromarray(gray, 'L').save(buf, format='PNG')

    with map_lock:
        map_png = buf.getvalue()


@app.route('/')
def index():
    """回傳監控頁面。"""
    with open(os.path.join(PKG, 'web', 'index.html'), encoding='utf-8') as f:
        return f.read()


@app.route('/map.png')
def get_map():
    """回傳最新地圖 PNG；尚無地圖時回傳 503。"""
    with map_lock:
        if map_png is None:
            return Response('等待地圖資料...', status=503)
        data = map_png

    resp = send_file(io.BytesIO(data), mimetype='image/png')
    resp.headers['Cache-Control'] = 'no-store'
    return resp


def main():
    rospy.init_node('map_server')
    port = rospy.get_param('~port', 8080)

    rospy.Subscriber('/map', OccupancyGrid, map_callback, queue_size=1)

    try:
        ip = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        ip = '127.0.0.1'

    rospy.loginfo(f'地圖伺服器已啟動 → http://{ip}:{port}')

    # Flask 跑在獨立執行緒，主執行緒留給 rospy.spin()
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port,
                               threaded=True, use_reloader=False),
        daemon=True
    ).start()

    rospy.spin()


if __name__ == '__main__':
    main()
