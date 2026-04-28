import rospy
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import actionlib
import numpy as np

def generate_zigzag_path(poly_pts, resolution, step_size=0.3):
    """
    簡單的 Zig-zag 路徑生成 (Boustrophedon)
    poly_pts: 四邊形頂點 (OpenCV 格式)
    resolution: 地圖解析度
    step_size: 掃描線間距 (米)
    """
    # 這裡實作簡化的 Zig-zag 邏輯
    # 1. 找出外接矩形
    pts = poly_pts.reshape(-1, 2)
    min_x, min_y = np.min(pts, axis=0)
    max_x, max_y = np.max(pts, axis=0)
    
    path = []
    # 將 step_size 轉為像素單位
    pixel_step = int(step_size / resolution)
    if pixel_step < 1: pixel_step = 1
    
    reverse = False
    for y in range(int(min_y), int(max_y), pixel_step):
        line_pts = []
        for x in range(int(min_x), int(max_x)):
            # 檢查像素點是否在多邊形內
            if is_inside(poly_pts, (x, y)):
                line_pts.append((x, y))
        
        if line_pts:
            if reverse:
                line_pts.reverse()
            path.extend([line_pts[0], line_pts[-1]]) # 只取每條線的端點，交給 move_base
            reverse = not reverse
            
    return path

def is_inside(poly, pt):
    import cv2
    return cv2.pointPolygonTest(poly, (float(pt[0]), float(pt[1])), False) >= 0

class CCPPPlanner:
    def __init__(self, map_metadata):
        self.res = map_metadata.resolution
        self.origin = map_metadata.origin.position
        self.height = map_metadata.height
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("Waiting for move_base action server...")
        # self.client.wait_for_server()

    def pixel_to_map(self, px, py):
        # 將 OpenCV 像素轉為 ROS 地圖座標
        # 注意：OpenCV 原點在左上，ROS 地圖原點通常在左下
        map_x = px * self.res + self.origin.x
        map_y = (self.height - py) * self.res + self.origin.y
        return map_x, map_y

    def execute_path(self, path_points):
        for pt in path_points:
            mx, my = self.pixel_to_map(pt[0], pt[1])
            rospy.loginfo("Sending goal: (%.2f, %.2f)", mx, my)
            goal = MoveBaseGoal()
            goal.target_pose.header.frame_id = "map"
            goal.target_pose.header.stamp = rospy.Time.now()
            goal.target_pose.pose.position.x = mx
            goal.target_pose.pose.position.y = my
            goal.target_pose.pose.orientation.w = 1.0
            
            self.client.send_goal(goal)
            self.client.wait_for_result()
            
            if self.client.get_state() != actionlib.GoalStatus.SUCCEEDED:
                rospy.logwarn("Failed to reach goal, skipping to next...")
