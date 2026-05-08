#!/usr/bin/env python3
import rospy
import numpy as np
import threading
import queue
import cv2
import os
import sys
import tf
import math

# Ensure ROS Python paths are correct
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PolygonStamped, Point32, PoseStamped
from std_msgs.msg import Float32
from std_srvs.srv import Trigger, TriggerResponse
from turtlebot3_ccpp.srv import GetTaskStatus, GetTaskStatusResponse

from map_processor import preprocess_map, get_frontier_map
from region_detector import detect_regions, find_best_frontier
from coverage_planner import generate_boustrophedon_path
from path_executor import PathExecutor

class DynamicCCPPManager:
    def __init__(self):
        rospy.init_node('ccpp_manager')
        
        # --- Parameters ---
        self.robot_width = rospy.get_param('~robot_width', 0.178)
        self.overlap = rospy.get_param('~scan_overlap', 0.8)
        self.step_size = self.robot_width * self.overlap
        
        # --- State Variables ---
        self.state = "IDLE" # IDLE, EXPLORING, COVERING
        self.map_msg = None
        self.coverage_array = None # Numpy array (uint8) 紀錄已走過的地方
        self.robot_pose = None
        self.progress = 0.0
        
        self.lock = threading.Lock()
        self.executor = PathExecutor()
        
        # --- ROS Communication ---
        self.progress_pub = rospy.Publisher('/ccpp/task_progress', Float32, queue_size=1)
        self.target_pub = rospy.Publisher('/ccpp/target_polygon', PolygonStamped, queue_size=1)
        self.coverage_pub = rospy.Publisher('/ccpp/coverage_map', OccupancyGrid, queue_size=1)
        self.processed_map_pub = rospy.Publisher('/ccpp/processed_map', OccupancyGrid, queue_size=1, latch=True)
        self.robot_pose_pub = rospy.Publisher('/ccpp/robot_pose', PoseStamped, queue_size=1)
        
        self.tf_listener = tf.TransformListener()
        rospy.Subscriber('/map', OccupancyGrid, self.map_callback)
        rospy.Timer(rospy.Duration(0.1), self.pose_timer_callback)
        
        # --- Services ---
        rospy.Service('/ccpp/start', Trigger, self.handle_start)
        rospy.Service('/ccpp/stop', Trigger, self.handle_stop)
        rospy.Service('/ccpp/reset_coverage', Trigger, self.handle_reset_coverage)
        rospy.Service('/ccpp/get_task_status', GetTaskStatus, self.handle_status)
        
        # --- Threads ---
        self.main_thread = threading.Thread(target=self.main_loop, daemon=True)
        self.main_thread.start()
        
        rospy.loginfo("Robust Auto CCPP Manager Initialized.")

    # --- Callbacks ---

    def pose_timer_callback(self, event):
        try:
            self.tf_listener.waitForTransform('/map', '/base_footprint', rospy.Time(0), rospy.Duration(0.2))
            (trans, rot) = self.tf_listener.lookupTransform('/map', '/base_footprint', rospy.Time(0))
            
            pose_msg = PoseStamped()
            pose_msg.header.frame_id = 'map'
            pose_msg.header.stamp = rospy.Time.now()
            pose_msg.pose.position.x = trans[0]
            pose_msg.pose.position.y = trans[1]
            pose_msg.pose.orientation.x = rot[0]
            pose_msg.pose.orientation.y = rot[1]
            pose_msg.pose.orientation.z = rot[2]
            pose_msg.pose.orientation.w = rot[3]
            self.robot_pose_pub.publish(pose_msg)
            
            self.robot_pose = pose_msg.pose
            self.update_coverage()
        except Exception:
            pass

    def map_callback(self, msg):
        with self.lock:
            self.map_msg = msg
            if self.coverage_array is None or self.coverage_array.shape != (msg.info.height, msg.info.width):
                self.coverage_array = np.zeros((msg.info.height, msg.info.width), dtype=np.uint8)
            
            # 發佈去毛邊後的「演算法視角」地圖
            self.publish_processed_map()

    def publish_processed_map(self):
        if self.map_msg is None: return
        
        cleaned = preprocess_map(self.map_msg.data, self.map_msg.info.width, self.map_msg.info.height)
        
        msg = OccupancyGrid()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        msg.info = self.map_msg.info
        
        # 轉換 0/255 為 ROS Occupancy Grid 標準 (0=空地, 100=障礙物)
        data = np.zeros_like(cleaned, dtype=np.int8)
        data[cleaned == 0] = 100 # 障礙物
        data[cleaned == 255] = 0 # 空地
        
        msg.data = data.flatten().tolist()
        self.processed_map_pub.publish(msg)

    # --- Core Logic ---

    def update_coverage(self):
        if self.coverage_array is None or self.robot_pose is None or self.map_msg is None:
            return
        info = self.map_msg.info
        mx = int((self.robot_pose.position.x - info.origin.position.x) / info.resolution)
        my = int((self.robot_pose.position.y - info.origin.position.y) / info.resolution)
        radius = int((self.robot_width / 2.0) / info.resolution)
        cv2.circle(self.coverage_array, (mx, my), radius, 255, -1)
        
        if rospy.Time.now().to_sec() % 2.0 < 0.1:
            self.publish_coverage_map()

    def main_loop(self):
        while not rospy.is_shutdown():
            if self.state == "IDLE" or self.map_msg is None or self.robot_pose is None:
                rospy.sleep(1.0)
                continue
            
            # 1. 預處理地圖 (使用較大的安全邊距)
            cleaned_map = preprocess_map(self.map_msg.data, self.map_msg.info.width, self.map_msg.info.height)
            
            # 2. 扣除已覆蓋區域
            pending_map = cleaned_map.copy()
            pending_map[self.coverage_array > 0] = 0
            
            # 3. 偵測區域
            regions = detect_regions(pending_map)
            
            if regions and regions[0]['area'] > 400:
                self.state = "COVERING"
                # 執行覆蓋
                self.execute_coverage(regions[0])
            else:
                # 4. 探索新空間
                frontier_map = get_frontier_map(self.map_msg.data, self.map_msg.info.width, self.map_msg.info.height)
                robot_px = self.world_to_pixel(self.robot_pose.position.x, self.robot_pose.position.y)
                target_frontier = find_best_frontier(frontier_map, robot_px)
                
                if target_frontier:
                    self.state = "EXPLORING"
                    target_world = self.pixel_to_world(target_frontier[0], target_frontier[1])
                    yaw = math.atan2(target_world[1] - self.robot_pose.position.y, target_world[0] - self.robot_pose.position.x)
                    # 執行點位，如果失敗則跳過
                    self.executor.execute_point(target_world[0], target_world[1], yaw=yaw)
                else:
                    rospy.loginfo("All reachable space covered. Mission Complete.")
                    self.state = "IDLE"
            
            rospy.sleep(1.0)

    def execute_coverage(self, region_info):
        self.publish_target_region(region_info['approx'])
        
        step_px = self.step_size / self.map_msg.info.resolution
        path_px = generate_boustrophedon_path(region_info['contour'], step_px)
        
        failed_count = 0
        for i in range(len(path_px)):
            if self.state == "IDLE": break
            
            pt = path_px[i]
            world_pt = self.pixel_to_world(pt[0], pt[1])
            
            # 距離檢查
            dist = math.sqrt((world_pt[0] - self.robot_pose.position.x)**2 + (world_pt[1] - self.robot_pose.position.y)**2)
            if dist < 0.2: continue # 稍微加大門檻，減少密集點位的衝突
            
            # 計算朝向
            yaw = None
            if i + 1 < len(path_px):
                next_pt = self.pixel_to_world(path_px[i+1][0], path_px[i+1][1])
                yaw = math.atan2(next_pt[1] - world_pt[1], next_pt[0] - world_pt[0])
            
            success = self.executor.execute_point(world_pt[0], world_pt[1], yaw=yaw)
            
            if not success:
                failed_count += 1
                rospy.logwarn(f"Goal failed ({failed_count}). Moving to next point.")
                if failed_count > 3: # 連續失敗次數過多則跳出此區域
                    rospy.logerr("Too many navigation failures in this region. Re-evaluating map...")
                    break
            else:
                failed_count = 0 # 成功則重置失敗計數
            
        rospy.loginfo("Region coverage step finished.")

    # --- Utils ---

    def world_to_pixel(self, x, y):
        info = self.map_msg.info
        px = int((x - info.origin.position.x) / info.resolution)
        py = int((y - info.origin.position.y) / info.resolution)
        return (px, py)

    def pixel_to_world(self, px, py):
        info = self.map_msg.info
        wx = px * info.resolution + info.origin.position.x
        wy = py * info.resolution + info.origin.position.y
        return (wx, wy)

    def publish_coverage_map(self):
        if self.coverage_array is None: return
        msg = OccupancyGrid()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        msg.info = self.map_msg.info
        data = np.zeros_like(self.coverage_array, dtype=np.int8)
        data[self.coverage_array > 0] = 100
        msg.data = data.flatten().tolist()
        self.coverage_pub.publish(msg)

    def publish_target_region(self, approx_pts):
        if not len(approx_pts) or self.map_msg is None: return
        poly = PolygonStamped()
        poly.header.frame_id = "map"
        poly.header.stamp = rospy.Time.now()
        for pt in approx_pts:
            p = Point32()
            world_pt = self.pixel_to_world(pt[0][0], pt[0][1])
            p.x, p.y = world_pt[0], world_pt[1]
            poly.polygon.points.append(p)
        self.target_pub.publish(poly)

    # --- Service Handlers ---

    def handle_reset_coverage(self, req):
        with self.lock:
            self.state = "IDLE"
            self.executor.stop()
            try:
                import subprocess
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "start_project.sh"))
                subprocess.Popen(["setsid", "bash", "-c", f"sleep 1 && /bin/bash {script_path}"])
            except Exception as e:
                return TriggerResponse(success=False, message=str(e))
        return TriggerResponse(success=True, message="System Restarting...")

    def handle_start(self, req):
        self.state = "EXPLORING"
        self.executor.start()
        return TriggerResponse(success=True, message="Auto Mission Started")

    def handle_stop(self, req):
        self.state = "IDLE"
        self.executor.stop()
        return TriggerResponse(success=True, message="Mission Stopped")

    def handle_status(self, req):
        res = GetTaskStatusResponse()
        if hasattr(res, 'task_state'): res.task_state = self.state
        res.overall_progress = self.progress
        res.success = True
        return res

if __name__ == '__main__':
    mgr = DynamicCCPPManager()
    rospy.spin()
