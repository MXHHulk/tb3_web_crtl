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
LINE_SPACING    = 0.25   # 掃描線間距（公尺）；< 機器人直徑以確保重疊覆蓋
ROBOT_RADIUS    = 0.15   # 機器人半徑（公尺），用於與障礙物保持安全距離
REPLAN_INTERVAL = 5.0    # 兩次重新規劃的最短間隔（秒）

_pub        = None
_last_plan  = 0.0


# ── 核心演算法 ────────────────────────────────────────────────────────────────

def boustrophedon(free, res, origin_x, origin_y):
    """
    輸入
      free       : 2-D bool 陣列，True = 可行走（已侵蝕過）
      res        : 地圖解析度（公尺/格）
      origin_x/y : 地圖原點世界座標（公尺）
    輸出
      [(world_x, world_y), ...] 依序走訪的路點列表

    以 PCA 對齊自由空間主軸，避免地圖傾斜時掃線方向與牆面不垂直。
    """
    rows, cols = np.where(free)
    if len(rows) == 0:
        return []

    # 所有可走格的世界座標
    wx_all = origin_x + cols.astype(float) * res
    wy_all = origin_y + rows.astype(float) * res
    pts    = np.column_stack([wx_all, wy_all])

    # PCA：找自由空間的長軸（sweep）與短軸（step）
    center           = pts.mean(axis=0)
    diffs            = pts - center
    eigvals, eigvecs = np.linalg.eigh(np.cov(diffs.T))
    axis_a = eigvecs[:, np.argmax(eigvals)]   # sweep 方向（長軸）
    axis_b = eigvecs[:, np.argmin(eigvals)]   # step  方向（短軸）

    if axis_a[0] < 0:
        axis_a = -axis_a
    if axis_b[1] < 0:
        axis_b = -axis_b

    proj_a = diffs @ axis_a
    proj_b = diffs @ axis_b

    step  = LINE_SPACING
    b_min = proj_b.min()
    b_max = proj_b.max()

    pts_out = []
    l2r = True
    b   = b_min + step / 2

    while b <= b_max + step / 2:
        mask = np.abs(proj_b - b) < step / 2
        if mask.any():
            a_vals  = proj_a[mask]
            p_start = center + a_vals.min() * axis_a + b * axis_b
            p_end   = center + a_vals.max() * axis_a + b * axis_b
            if l2r:
                pts_out += [(p_start[0], p_start[1]), (p_end[0],   p_end[1])]
            else:
                pts_out += [(p_end[0],   p_end[1]),   (p_start[0], p_start[1])]
            l2r = not l2r
        b += step

    return pts_out


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
