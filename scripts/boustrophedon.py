#!/usr/bin/env python3
"""
牛耕式（Boustrophedon）覆蓋路徑規劃節點

訂閱 /map，把地圖切成平行掃描線，計算「來回耕地」路點後
以 nav_msgs/Path 發布到 /coverage_path（latch，RViz 可直接顯示）。
"""
import numpy as np
import rospy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid, Path
from scipy.ndimage import binary_erosion

# ── 可調參數 ──────────────────────────────────────────────────────────────────
LINE_SPACING    = 0.3    # 掃描線間距（公尺），通常 = 機器人直徑
ROBOT_RADIUS    = 0.15   # 機器人半徑（公尺），用於與障礙物保持安全距離
REPLAN_INTERVAL = 5.0    # 兩次重新規劃的最短間隔（秒）

_pub        = None
_last_plan  = 0.0


# ── 核心演算法 ────────────────────────────────────────────────────────────────

def boustrophedon(free, res, origin_x, origin_y):
    """
    輸入
      free     : 2-D bool 陣列，True = 可行走（已侵蝕過）
      res      : 地圖解析度（公尺/格）
      origin_x/y: 地圖原點世界座標（公尺）
    輸出
      [(world_x, world_y), ...] 依序走訪的路點列表
    """
    h, w  = free.shape
    step  = max(1, round(LINE_SPACING / res))   # 掃描線格距
    pts   = []
    l2r   = True   # 當前行掃描方向：True=左→右，False=右→左

    for row in range(step // 2, h, step):
        # ── 找出這一行的連續可走區段 [(起始格, 結束格), ...] ────────────────
        segs, start = [], None
        for col in range(w):
            if free[row, col] and start is None:
                start = col
            elif not free[row, col] and start is not None:
                segs.append((start, col - 1))
                start = None
        if start is not None:
            segs.append((start, w - 1))

        if not segs:
            continue

        # ── 依掃描方向決定走法（反向時區段本身也要反轉）──────────────────────
        if not l2r:
            segs = [(e, s) for s, e in reversed(segs)]

        # 每段只需寫入兩端點（機器人會直線掃過中間）
        for s, e in segs:
            for col in ([s, e] if s != e else [s]):
                pts.append((origin_x + col * res,
                             origin_y + row * res))

        l2r = not l2r   # 下一行換方向

    return pts


# ── ROS 介面 ──────────────────────────────────────────────────────────────────

def _make_pose(x, y, frame_id):
    p = PoseStamped()
    p.header.frame_id    = frame_id
    p.pose.position.x    = x
    p.pose.position.y    = y
    p.pose.orientation.w = 1.0
    return p


def map_callback(msg):
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
    free = data == 0   # 空地格

    # 侵蝕：讓機器人遠離障礙物邊緣
    r    = max(1, round(ROBOT_RADIUS / res))
    kern = np.ones((2 * r + 1, 2 * r + 1), dtype=bool)
    free = binary_erosion(free, structure=kern)

    pts = boustrophedon(free, res, ox, oy)
    if not pts:
        rospy.logwarn('[boustrophedon] 找不到可走路徑，地圖是否已完成？')
        return

    path                 = Path()
    path.header.stamp    = rospy.Time.now()
    path.header.frame_id = msg.header.frame_id or 'map'
    path.poses           = [_make_pose(x, y, path.header.frame_id) for x, y in pts]

    _pub.publish(path)
    rospy.loginfo(f'[boustrophedon] 已發布 {len(pts)} 個路點'
                  f'（掃描線間距 {LINE_SPACING} m，安全距離 {ROBOT_RADIUS} m）')


def main():
    global _pub
    rospy.init_node('boustrophedon_planner')
    _pub = rospy.Publisher('/coverage_path', Path, queue_size=1, latch=True)
    rospy.Subscriber('/map', OccupancyGrid, map_callback, queue_size=1)
    rospy.loginfo('[boustrophedon] 節點已啟動，等待 /map …')
    rospy.spin()


if __name__ == '__main__':
    main()
