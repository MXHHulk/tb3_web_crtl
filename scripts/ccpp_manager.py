#!/usr/bin/env python3
import rospy
import numpy as np
import threading
import queue
import cv2
import os
import sys

# Ensure ROS Python paths are correct
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PolygonStamped, Point32, PoseWithCovarianceStamped
from std_msgs.msg import Float32
from std_srvs.srv import Trigger, TriggerResponse
from turtlebot3_ccpp.srv import GetTaskStatus, GetTaskStatusResponse

from map_processor import preprocess_map
from region_detector import detect_regions
from coverage_planner import generate_boustrophedon_path
from path_executor import PathExecutor

class DynamicCCPPManager:
    def __init__(self):
        rospy.init_node('ccpp_manager')
        
        # Parameters
        self.robot_width = rospy.get_param('~robot_width', 0.178)
        self.overlap = rospy.get_param('~scan_overlap', 0.8)
        self.step_size = self.robot_width * self.overlap
        self.map_update_threshold = rospy.get_param('~map_update_threshold', 0.05) # 5% area change
        self.goal_timeout = rospy.get_param('~goal_timeout', 30.0)
        
        # State Variables
        self.state = "IDLE"
        self.map_msg = None
        self.coverage_array = None # Numpy array (uint8)
        self.last_free_area_count = 0
        self.robot_pose = None
        self.goal_queue = queue.Queue()
        self.current_target_pts = []
        self.progress = 0.0
        
        self.lock = threading.Lock()
        self.executor = PathExecutor(timeout=self.goal_timeout)
        
        # Publishers
        self.progress_pub = rospy.Publisher('/ccpp/task_progress', Float32, queue_size=1)
        self.target_pub = rospy.Publisher('/ccpp/target_polygon', PolygonStamped, queue_size=1)
        self.coverage_pub = rospy.Publisher('/ccpp/coverage_map', OccupancyGrid, queue_size=1)
        
        # Subscribers
        rospy.Subscriber('/map', OccupancyGrid, self.map_callback)
        rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, self.pose_callback)
        
        # Services
        rospy.Service('/ccpp/start', Trigger, self.handle_start)
        rospy.Service('/ccpp/stop', Trigger, self.handle_stop)
        rospy.Service('/ccpp/reset_coverage', Trigger, self.handle_reset_coverage)
        rospy.Service('/ccpp/get_task_status', GetTaskStatus, self.handle_status)
        
        # Workers
        self.planning_triggered = threading.Event()
        self.threads = [
            threading.Thread(target=self.planning_loop, daemon=True),
            threading.Thread(target=self.execution_loop, daemon=True)
        ]
        for t in self.threads: t.start()
        
        rospy.loginfo("Dynamic CCPP Manager Initialized.")

    # --- Callbacks ---

    def pose_callback(self, msg):
        self.robot_pose = msg.pose.pose
        self.update_coverage()

    def map_callback(self, msg):
        with self.lock:
            self.map_msg = msg
            # Initialize coverage array if not exists
            if self.coverage_array is None or self.coverage_array.shape != (msg.info.height, msg.info.width):
                self.coverage_array = np.zeros((msg.info.height, msg.info.width), dtype=np.uint8)
            
            # Check for significant changes to trigger planning
            raw_data = np.array(msg.data).reshape((msg.info.height, msg.info.width))
            free_cells = np.count_nonzero(raw_data == 0)
            
            if self.state == "RUNNING":
                change_ratio = abs(free_cells - self.last_free_area_count) / max(1, self.last_free_area_count)
                if change_ratio > self.map_update_threshold or self.last_free_area_count == 0:
                    rospy.loginfo(f"Map change detected ({change_ratio:.2%}), triggering re-plan...")
                    self.planning_triggered.set()
                    self.last_free_area_count = free_cells

    # --- Core Logic ---

    def update_coverage(self):
        if self.coverage_array is None or self.robot_pose is None or self.map_msg is None:
            return
        
        info = self.map_msg.info
        # Convert world pose to map pixel
        mx = int((self.robot_pose.position.x - info.origin.position.x) / info.resolution)
        my = int((self.robot_pose.position.y - info.origin.position.y) / info.resolution)
        
        # Mark robot footprint as covered
        radius = int((self.robot_width / 2.0) / info.resolution)
        cv2.circle(self.coverage_array, (mx, my), radius, 255, -1)
        
        # Periodic publish (e.g., every 1 second or on movement)
        if rospy.Time.now().to_sec() % 2.0 < 0.1:
            self.publish_coverage_map()

    def planning_loop(self):
        while not rospy.is_shutdown():
            self.planning_triggered.wait(timeout=1.0)
            if not self.planning_triggered.is_set() or self.state != "RUNNING":
                continue
            
            with self.lock:
                if self.map_msg is None: continue
                msg = self.map_msg
                cov = self.coverage_array.copy()

            # 1. Preprocess
            binary_img = preprocess_map(msg.data, msg.info.width, msg.info.height)
            
            # 2. Mask out already covered areas
            # binary_img is 255 for free space, cov is 255 for covered
            binary_img[cov > 0] = 0 
            
            # 3. Detect Regions
            regions = detect_regions(binary_img)
            if not regions:
                rospy.loginfo("No new regions to cover.")
                self.planning_triggered.clear()
                continue
            
            # 4. Sort by Distance (Nearest first)
            if self.robot_pose:
                rx, ry = self.robot_pose.position.x, self.robot_pose.position.y
                def dist_to_robot(poly):
                    # Use center of first point as approximation
                    px = poly[0][0][0] * msg.info.resolution + msg.info.origin.position.x
                    py = poly[0][0][1] * msg.info.resolution + msg.info.origin.position.y
                    return (px - rx)**2 + (py - ry)**2
                regions.sort(key=dist_to_robot)

            # 5. Generate paths for discovered regions and queue them
            # We clear the queue and re-populate with fresh plan to avoid stale goals
            with self.goal_queue.mutex:
                self.goal_queue.queue.clear()
            
            for region in regions:
                path = generate_boustrophedon_path(region, self.step_size / msg.info.resolution)
                for pt in path:
                    mx = pt[0] * msg.info.resolution + msg.info.origin.position.x
                    my = pt[1] * msg.info.resolution + msg.info.origin.position.y
                    self.goal_queue.put((mx, my))
            
            self.current_target_pts = regions[0] if regions else []
            self.publish_target_region(self.current_target_pts)
            
            rospy.loginfo(f"Re-planned: {len(regions)} regions found, {self.goal_queue.qsize()} points queued.")
            self.planning_triggered.clear()

    def execution_loop(self):
        while not rospy.is_shutdown():
            if self.state != "RUNNING" or self.goal_queue.empty():
                rospy.sleep(0.5)
                continue
            
            try:
                goal = self.goal_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            mx, my = goal
            self.executor.start()
            success = self.executor.execute_point(mx, my)
            
            # Retry Once if failed
            if not success and self.state == "RUNNING":
                rospy.logwarn(f"Goal ({mx:.2f}, {my:.2f}) failed, retrying once...")
                success = self.executor.execute_point(mx, my)
            
            self.goal_queue.task_done()
            
            # Update Progress
            if self.last_free_area_count > 0:
                covered_count = np.count_nonzero(self.coverage_array)
                # Note: this is a rough estimate since last_free_area_count is in pixels
                self.progress = min(1.0, covered_count / max(1, self.last_free_area_count))
                self.progress_pub.publish(Float32(self.progress))

    # --- Helpers ---

    def publish_coverage_map(self):
        if self.coverage_array is None: return
        msg = OccupancyGrid()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        msg.info = self.map_msg.info
        # Convert 0/255 to ROS occupancy values (0=free, 100=occupied/covered)
        # Here we use 100 to represent 'covered' in the coverage map layer
        data = np.zeros_like(self.coverage_array, dtype=np.int8)
        data[self.coverage_array > 0] = 100
        msg.data = data.flatten().tolist()
        self.coverage_pub.publish(msg)

    def publish_target_region(self, region_pts):
        if not len(region_pts) or self.map_msg is None: return
        
        # 將像素點轉為矩形邊界
        # region_pts 格式通常為 [[[x, y]], [[x, y]], ...] (OpenCV contour)
        pts = np.array(region_pts).reshape(-1, 2)
        x, y, w, h = cv2.boundingRect(pts)
        
        # 建立長方形的四個頂點
        rect_pts = [
            [x, y], [x + w, y], [x + w, y + h], [x, y + h]
        ]
        
        poly = PolygonStamped()
        poly.header.frame_id = "map"
        poly.header.stamp = rospy.Time.now()
        info = self.map_msg.info
        
        for pt in rect_pts:
            p = Point32()
            p.x = pt[0] * info.resolution + info.origin.position.x
            p.y = pt[1] * info.resolution + info.origin.position.y
            poly.polygon.points.append(p)
            
        self.target_pub.publish(poly)

    # --- Service Handlers ---

    def handle_reset_coverage(self, req):
        with self.lock:
            if self.coverage_array is not None:
                self.coverage_array.fill(0)
                rospy.loginfo("Coverage map reset.")
                self.publish_coverage_map()
        return TriggerResponse(success=True, message="Coverage map cleared and reset.")

    def handle_start(self, req):
        if self.state == "RUNNING":
            return TriggerResponse(success=True, message="Already running")
        self.state = "RUNNING"
        self.planning_triggered.set()
        return TriggerResponse(success=True, message="Dynamic CCPP Task Started")

    def handle_stop(self, req):
        self.state = "IDLE"
        self.executor.stop()
        with self.goal_queue.mutex:
            self.goal_queue.queue.clear()
        return TriggerResponse(success=True, message="Task Stopped and Queue Cleared")

    def handle_status(self, req):
        res = GetTaskStatusResponse()
        res.success = True
        # Note: Some fields are simplified for the dynamic version
        # You might want to populate total_regions based on the last planning result
        return GetTaskStatusResponse(success=True) # ROS will automatically pack the response object

if __name__ == '__main__':
    try:
        mgr = DynamicCCPPManager()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
