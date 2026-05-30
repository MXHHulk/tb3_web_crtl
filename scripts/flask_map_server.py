#!/usr/bin/env python3
"""
flask_map_server.py — ROS 節點 + Flask HTTP 伺服器

職責：
  1. 訂閱 /map (nav_msgs/OccupancyGrid)，將地圖資料轉成 PNG 圖片並快取。
  2. 啟動 Flask HTTP 伺服器，提供靜態頁面與地圖 API。
  3. 透過 Server-Sent Events (SSE) 主動推送地圖更新通知給所有瀏覽器。

端點：
  GET /                  → 監控首頁 (index.html)
  GET /static/*          → 靜態資源 (CSS/JS)
  GET /api/map/image     → 當前地圖的 PNG 圖片
  GET /api/map/info      → 地圖元數據 (JSON)
  GET /api/events        → SSE 事件流 (地圖更新通知)

相依套件（pip3）：
  flask>=2.0
  Pillow>=9.0
  numpy（通常已隨 ROS 安裝）
"""

import io
import json
import os
import queue
import socket
import threading

import numpy as np
import rospkg
import rospy
from flask import Flask, Response, jsonify, render_template, send_file
from nav_msgs.msg import OccupancyGrid
from PIL import Image

# ── 路徑解析 ─────────────────────────────────────────────────────────────────
# 優先用 rospkg 取得 package 根目錄，確保 catkin install 後符號連結也能正確解析。
try:
    _PKG_DIR = rospkg.RosPack().get_path('turtlebot3_ccpp')
except rospkg.ResourceNotFound:
    # 備案：scripts/ 的上一層就是 package 根目錄
    _PKG_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

_TEMPLATE_DIR = os.path.join(_PKG_DIR, 'web_interface', 'templates')
_STATIC_DIR   = os.path.join(_PKG_DIR, 'web_interface', 'static')

# ── Flask app（模組層級建立，路由裝飾器才能正常套用）────────────────────────
app = Flask(__name__, template_folder=_TEMPLATE_DIR, static_folder=_STATIC_DIR)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0   # 關閉靜態檔案快取，方便開發測試

# ── 共享狀態（讀寫都要持有 _map_lock）────────────────────────────────────────
_map_lock    = threading.Lock()
_map_png     = None   # bytes：PNG 編碼的地圖圖片
_map_meta    = {}     # dict：地圖元數據
_map_version = 0      # int：每次收到新地圖遞增，用於快取破壞

# SSE 客戶端佇列清單：每個瀏覽器連線對應一個 queue.Queue
_client_queues      = []
_client_queues_lock = threading.Lock()


# ── ROS 回調 ─────────────────────────────────────────────────────────────────

def _map_callback(msg):
    """將 OccupancyGrid 轉為 PNG，更新快取並通知所有 SSE 客戶端。"""
    global _map_png, _map_meta, _map_version

    w, h = msg.info.width, msg.info.height
    if w == 0 or h == 0:
        return

    # OccupancyGrid 值域：-1 未知 / 0 可通行 / 1-100 佔用機率
    # 轉為灰階：未知→128(灰)、可通行→255(白)、障礙物→0(黑)
    data = np.array(msg.data, dtype=np.int8).reshape((h, w)).astype(np.int16)
    gray = np.full((h, w), 128, dtype=np.uint8)           # 預設：未知（灰）

    known = data >= 0
    # known 區域：值越大代表越可能是障礙，0→255 白，100→0 黑
    gray[known] = np.clip(255 - (data[known] * 255 // 100), 0, 255).astype(np.uint8)

    # ROS 地圖原點在左下角，圖片原點在左上角，需上下翻轉
    gray = np.flipud(gray)

    buf = io.BytesIO()
    Image.fromarray(gray, 'L').convert('RGB').save(buf, format='PNG')

    resolution = float(msg.info.resolution)
    with _map_lock:
        _map_png     = buf.getvalue()
        _map_version += 1
        version      = _map_version           # 在 lock 內捕捉，避免 race condition
        _map_meta    = {
            'width':      w,
            'height':     h,
            'resolution': resolution,
            'version':    version,
        }

    # 將更新事件推入所有 SSE 客戶端的佇列
    evt = json.dumps({'type':       'map_update',
                      'version':    version,
                      'width':      w,
                      'height':     h,
                      'resolution': resolution})
    with _client_queues_lock:
        for q in list(_client_queues):
            try:
                q.put_nowait(evt)
            except queue.Full:
                pass   # 客戶端太慢，跳過本次更新


# ── Flask 路由 ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/map/image')
def map_image():
    """回傳當前地圖的 PNG 圖片；無地圖時回傳 503。"""
    with _map_lock:
        if _map_png is None:
            return Response('尚無地圖資料，請確認 SLAM 節點已啟動', status=503)
        data = _map_png

    response = send_file(io.BytesIO(data), mimetype='image/png')
    # 防止瀏覽器快取舊圖片
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma']        = 'no-cache'
    return response


@app.route('/api/map/info')
def map_info():
    """回傳地圖元數據（尺寸、解析度、版本號）。"""
    with _map_lock:
        return jsonify(_map_meta)


@app.route('/api/events')
def event_stream():
    """
    Server-Sent Events 端點。

    每個瀏覽器連線在此建立一個專屬佇列；當新地圖到達時，_map_callback
    會把事件字串推入所有佇列，各連線的 generate() 再從佇列讀出並回傳。
    客戶端斷線後，finally 區塊負責清理佇列，避免記憶體洩漏。
    """
    client_q = queue.Queue(maxsize=5)
    with _client_queues_lock:
        _client_queues.append(client_q)

    def generate():
        try:
            while True:
                try:
                    evt = client_q.get(timeout=25)
                    yield f'data: {evt}\n\n'
                except queue.Empty:
                    # 定時心跳，防止代理伺服器因長時間沉默而關閉連線
                    yield ': heartbeat\n\n'
        finally:
            with _client_queues_lock:
                if client_q in _client_queues:
                    _client_queues.remove(client_q)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no',    # 關閉 Nginx 緩衝，確保事件即時送達
        }
    )


# ── 主函式 ────────────────────────────────────────────────────────────────────

def main():
    rospy.init_node('flask_map_server')
    port = rospy.get_param('~port', 8080)

    rospy.Subscriber('/map', OccupancyGrid, _map_callback, queue_size=1)

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = '127.0.0.1'

    rospy.loginfo('=' * 50)
    rospy.loginfo('Flask 地圖伺服器已啟動！')
    rospy.loginfo(f'本機存取：http://localhost:{port}')
    rospy.loginfo(f'區域網路：http://{local_ip}:{port}')
    rospy.loginfo('=' * 50)

    # Flask 在獨立 daemon thread 中運行，主執行緒留給 rospy.spin()
    # use_reloader=False：防止 Flask 嘗試重啟自身，干擾 ROS 節點生命週期
    flask_thread = threading.Thread(
        target=lambda: app.run(
            host='0.0.0.0',
            port=port,
            threaded=True,
            use_reloader=False,
            debug=False,
        ),
        daemon=True,
        name='flask-server',
    )
    flask_thread.start()
    rospy.spin()


if __name__ == '__main__':
    main()
