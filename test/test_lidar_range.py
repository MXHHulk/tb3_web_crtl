#!/usr/bin/env python3
"""
測試工具：證明光達的有效量測距離（約 3 公尺）。

原理：/scan (sensor_msgs/LaserScan) 有兩種資訊
  1. 驅動「宣告」的上下限 range_min / range_max —— 規格書寫的值
  2. 「實際」量到的 ranges[] —— 超出有效距離的光束會回傳 inf（無效）
本工具把兩者一起印出，並統計每個視窗內「實際量到的最遠有效距離」，
那個數值就是真正的有效距離證據。

用法（先讓 /scan 有資料，例如 roslaunch 已啟動硬體驅動）：
  rosrun turtlebot3_ccpp test_lidar_range.py
建議搭配實驗：把機器人正對一面牆，逐步把牆/目標物往後移，
觀察「正前方距離」何時從有限值跳成 inf —— 跳掉的那一刻就是有效上限。
"""
import math
import numpy as np
import rospy
from sensor_msgs.msg import LaserScan


class LidarRangeTester:
    def __init__(self):
        rospy.init_node('lidar_range_tester', anonymous=True)
        self.declared_printed = False
        self.last_log = rospy.get_time()
        self.max_seen = 0.0          # 跨整段時間觀察到的最遠有效距離
        self.sub = rospy.Subscriber('/scan', LaserScan, self.callback)
        rospy.loginfo('光達有效距離測試節點已啟動，等待 /scan …')

    def callback(self, msg):
        # ① 只印一次：驅動宣告的規格
        if not self.declared_printed:
            rospy.loginfo('—— 驅動宣告值（規格）——')
            rospy.loginfo(f'  range_min = {msg.range_min:.3f} m')
            rospy.loginfo(f'  range_max = {msg.range_max:.3f} m   ← 驅動聲稱的最大有效距離')
            rospy.loginfo(f'  光束數    = {len(msg.ranges)}')
            self.declared_printed = True

        ranges = np.array(msg.ranges, dtype=np.float32)

        # 有效讀數：是有限數、且落在宣告上下限內（排除 inf / nan / 0）
        valid = np.isfinite(ranges) & (ranges >= msg.range_min) & (ranges <= msg.range_max)
        valid_vals = ranges[valid]

        # 正前方那一束（index 0 通常是機器人正前方）
        front = ranges[0]
        front_str = f'{front:.3f} m' if math.isfinite(front) else 'inf（超出有效距離）'

        if valid_vals.size:
            cur_max = float(valid_vals.max())
            self.max_seen = max(self.max_seen, cur_max)
        else:
            cur_max = 0.0

        # 每 2 秒輸出一次統計
        now = rospy.get_time()
        if now - self.last_log >= 2.0:
            total = ranges.size
            n_valid = int(valid.sum())
            n_inf = int(np.isinf(ranges).sum())
            rospy.loginfo('—— 實際量測 ——')
            rospy.loginfo(f'  正前方(0°)           : {front_str}')
            rospy.loginfo(f'  本視窗最遠有效距離   : {cur_max:.3f} m')
            rospy.loginfo(f'  歷來最遠有效距離     : {self.max_seen:.3f} m   ← 有效距離的證據')
            rospy.loginfo(f'  有效光束 / 總光束     : {n_valid}/{total}（inf 無效 {n_inf} 束）')
            self.last_log = now


if __name__ == '__main__':
    try:
        LidarRangeTester()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
