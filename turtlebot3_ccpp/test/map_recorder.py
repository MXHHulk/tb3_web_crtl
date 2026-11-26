#!/usr/bin/env python3
"""
地圖錄製節點（獨立於 map_server）
  - 訂閱 /map，每次 callback 把「原始灰階地圖」存成 PNG。
  - 啟動時以時間戳建立一個 session 資料夾，當次所有 PNG 都存進去。
  - 轉圖邏輯與 map_server 的 /map.png 一致（裁切 + 上下翻轉 + 灰階反轉），
    確保存下來的圖與網頁顯示相同。

參數（~private）：
  ~out_dir   PNG 根目錄，預設 <pkg>/maps
  ~crop_pad  裁切邊距（格），預設 10；設 -1 則不裁切（存完整地圖）
  ~min_period 兩次存檔最小間隔秒數，預設 0（每次 callback 都存）；
              /map 更新很快時可調大避免存太多張。
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import numpy as np
import rospkg
import rospy
from nav_msgs.msg import OccupancyGrid
from PIL import Image

try:
    PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')
except rospkg.ResourceNotFound:
    PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def crop_bbox(known, h, w, pad):
    """找出已知格子的最小矩形（加邊距）。pad < 0 表示不裁切。"""
    if pad < 0:
        return 0, h, 0, w
    r = np.any(known, axis=1)
    c = np.any(known, axis=0)
    if not r.any():
        return 0, h, 0, w
    r0 = max(np.argmax(r)          - pad, 0)
    r1 = min(h - np.argmax(r[::-1]) + pad, h)
    c0 = max(np.argmax(c)          - pad, 0)
    c1 = min(w - np.argmax(c[::-1]) + pad, w)
    return r0, r1, c0, c1


class MapRecorder:
    def __init__(self):
        root = rospy.get_param('~out_dir', os.path.join(PKG, 'maps'))
        self.crop_pad   = rospy.get_param('~crop_pad', 10)
        self.min_period = rospy.get_param('~min_period', 0.0)

        # 以啟動時間建立當次 session 資料夾
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_dir = os.path.join(root, stamp)
        os.makedirs(self.session_dir, exist_ok=True)

        self.count = 0
        self.last_save = None
        rospy.loginfo(f'[map_recorder] 存圖目錄：{self.session_dir}')

        rospy.Subscriber('/map', OccupancyGrid, self.map_callback, queue_size=1)

    def map_callback(self, msg):
        # 節流：距上次存檔不足 min_period 秒就跳過
        now = rospy.get_time()
        if self.min_period > 0 and self.last_save is not None \
                and now - self.last_save < self.min_period:
            return

        w, h = msg.info.width, msg.info.height
        if w == 0 or h == 0:
            return

        data  = np.array(msg.data, dtype=np.int8).reshape((h, w)).astype(np.int16)
        known = data >= 0

        # 原始地圖灰階：未知=128，其餘由佔據機率反轉成黑白
        gray = np.full((h, w), 128, dtype=np.uint8)
        gray[known] = np.clip(255 - data[known] * 255 // 100, 0, 255).astype(np.uint8)

        r0, r1, c0, c1 = crop_bbox(known, h, w, self.crop_pad)
        arr = np.flipud(gray[r0:r1, c0:c1])   # 上下翻轉與網頁顯示一致

        self.count += 1
        self.last_save = now
        # 檔名：序號 + 收到地圖時間戳，方便排序與對時間
        ts = datetime.now().strftime('%H%M%S_%f')[:-3]
        path = os.path.join(self.session_dir, f'map_{self.count:06d}_{ts}.png')
        Image.fromarray(arr, 'L').save(path)

        if self.count % 10 == 0:
            rospy.loginfo(f'[map_recorder] 已存 {self.count} 張（最新 {os.path.basename(path)}）')


def main():
    rospy.init_node('map_recorder')
    MapRecorder()
    rospy.spin()


if __name__ == '__main__':
    main()
