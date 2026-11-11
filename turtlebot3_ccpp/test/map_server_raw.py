#!/usr/bin/env python3
"""
測試工具：網頁只顯示「未經處理」的原始地圖（/map）。

相對於完整的 scripts/map_server.py 刻意精簡：
  - 只訂閱 /map，直接把 OccupancyGrid 轉成灰階 PNG
  - 不做侵蝕 / 膨脹 / 裁切等任何形態學或裁剪處理
  - 不含 odom 軌跡、覆蓋路徑規劃、move_base 執行
網頁與 /map.png 由 Flask 提供，每秒自動刷新一次。

用法：
  rosrun turtlebot3_ccpp map_server_raw.py            # 或直接 python3 此檔
  rosrun turtlebot3_ccpp map_server_raw.py _port:=9000
然後瀏覽器開 http://<機器人IP>:8080
"""
import io
import socket
import threading

import numpy as np
import rospy
from flask import Flask, Response
from nav_msgs.msg import OccupancyGrid
from PIL import Image

app = Flask(__name__)

# 共享狀態：最新一張原始地圖的 PNG bytes
map_lock = threading.Lock()
map_png = None

# 內嵌的極簡網頁：一張圖 + 每秒刷新
PAGE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>原始地圖（測試）</title>
  <style>
    body { background:#222; color:#eee; font-family:sans-serif; text-align:center; margin-top:24px; }
    img  { image-rendering:pixelated; border:1px solid #555; max-width:90vw; background:#444; }
    #info { color:#9bd; font-size:14px; }
  </style>
</head>
<body>
  <h2>原始地圖 /map（完全未翻譯）</h2>
  <p style="font-size:13px;color:#c99">空地=黑、障礙=中灰、未知=白（黑白與一般地圖相反，這是正常的）</p>
  <img id="map" alt="等待地圖…">
  <p id="info">等待 /map …</p>
  <script>
    const img  = document.getElementById('map');
    const info = document.getElementById('info');
    function refresh() {
      img.src = '/map.png?t=' + Date.now();   // 加時間戳，避免瀏覽器快取舊圖
    }
    img.onload  = () => { info.textContent = '更新時間：' + new Date().toLocaleTimeString(); };
    img.onerror = () => { info.textContent = '地圖尚未就緒…'; };
    setInterval(refresh, 1000);
    refresh();
  </script>
</body>
</html>"""


def map_callback(msg):
    """/map 回呼：完全不翻譯，直接把原始值轉成 uint8 顯示。

    刻意「不做任何數值翻譯」——直接把 OccupancyGrid 的原始值丟給 PIL，
    結果會反直覺（因為 int8 的 -1 轉 uint8 會變 255）：
      空地 0   → 0   黑（和一般地圖相反）
      障礙 100 → 100 中灰
      未知 -1  → 255 白（整片背景變白）
    """
    global map_png
    w, h = msg.info.width, msg.info.height
    if w == 0 or h == 0:
        return

    data = np.array(msg.data, dtype=np.int8).reshape((h, w))
    gray = data.astype(np.uint8)   # 直接轉型，不縮放、不翻轉黑白

    # flipud：影像 Y 向下、世界 Y 向上，需上下翻轉才方向正確
    buf = io.BytesIO()
    Image.fromarray(np.flipud(gray), 'L').save(buf, format='PNG')
    with map_lock:
        map_png = buf.getvalue()


@app.route('/')
def index():
    return Response(PAGE, mimetype='text/html')


@app.route('/map.png')
def get_map():
    with map_lock:
        d = map_png
    if d is None:
        return '地圖尚未就緒', 503
    return Response(d, mimetype='image/png')


def main():
    rospy.init_node('map_server_raw')
    port = rospy.get_param('~port', 8080)

    rospy.Subscriber('/map', OccupancyGrid, map_callback, queue_size=1)

    try:
        ip = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        ip = '127.0.0.1'
    rospy.loginfo(f'[map_server_raw] 原始地圖伺服器 → http://{ip}:{port}')

    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False),
        daemon=True,
    ).start()
    rospy.spin()


if __name__ == '__main__':
    main()
