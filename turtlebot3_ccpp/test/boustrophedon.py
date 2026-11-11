#!/usr/bin/env python3
"""
測試工具：牛耕式路徑規劃 ROS 節點（供 RViz 檢視覆蓋路徑用）。

訂閱 /map，計算覆蓋路點後以 nav_msgs/Path 發布到 /coverage_path。
非專案執行路徑的一部分——正式的覆蓋路徑由 scripts/map_server.py 自行計算並
顯示於網頁，此節點只是把同一份規劃結果另外發成 topic 給 RViz 看，
機器人不會依它行走，故不掛在 launch/start.launch。

路徑規劃核心共用 scripts/coverage_planner.py。

用法（需先 roslaunch 啟動 SLAM，讓 /map 有資料）：
  python3 test/boustrophedon.py
"""
import os, sys
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'scripts'))

import numpy as np
import rospy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid, Path

from coverage_planner import boustrophedon, SPACING, MARGIN, apply_safety_margin

REPLAN_INTERVAL = 5.0   # 兩次重新規劃的最短間隔（秒）

_pub       = None
_last_plan = 0.0


def _make_pose(x, y, frame_id):
    """把世界座標 (x, y) 包成指定座標系的 PoseStamped。"""
    p = PoseStamped()
    p.header.frame_id    = frame_id
    p.pose.position.x    = x
    p.pose.position.y    = y
    p.pose.orientation.w = 1.0
    return p


def map_callback(msg):
    """收到 /map 時重新規劃覆蓋路徑並發布到 /coverage_path（至少間隔 REPLAN_INTERVAL 秒）。"""
    global _last_plan
    now = rospy.get_time()
    if now - _last_plan < REPLAN_INTERVAL:
        return
    _last_plan = now

    res  = msg.info.resolution
    ox   = msg.info.origin.position.x
    oy   = msg.info.origin.position.y
    w, h = msg.info.width, msg.info.height

    data = np.array(msg.data, dtype=np.int8).reshape((h, w))
    safe_obs = apply_safety_margin(data, MARGIN, res)
    free = (data == 0) & ~safe_obs

    pts = boustrophedon(free, res, ox, oy)
    if not pts:
        rospy.logwarn('[boustrophedon] 找不到可走路徑，地圖是否已完成？')
        return

    path                 = Path()
    path.header.stamp    = rospy.Time.now()
    path.header.frame_id = msg.header.frame_id or 'map'
    path.poses           = [_make_pose(x, y, path.header.frame_id) for x, y in pts]

    _pub.publish(path)
    rospy.loginfo(f'[boustrophedon] 已發布 {len(pts)} 個路點（間距 {SPACING} m）')


def main():
    """初始化節點，建立 /coverage_path 發布者與 /map 訂閱者後進入事件迴圈。"""
    global _pub
    rospy.init_node('boustrophedon_planner')
    _pub = rospy.Publisher('/coverage_path', Path, queue_size=1, latch=True)
    rospy.Subscriber('/map', OccupancyGrid, map_callback, queue_size=1)
    rospy.loginfo('[boustrophedon] 節點已啟動，等待 /map …')
    rospy.spin()


if __name__ == '__main__':
    main()
