#!/usr/bin/env python3
import rospy
import actionlib
import math
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib_msgs.msg import GoalStatus
from tf.transformations import quaternion_from_euler
 
class PathExecutor:
    def __init__(self, timeout=20.0): # 縮短超時時間，快速放棄無效點
        self.client  = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        self.timeout = timeout
        self.is_running = False
 
        rospy.loginfo("Waiting for move_base action server...")
        connected = self.client.wait_for_server(rospy.Duration(5.0))
        if connected:
            rospy.loginfo("move_base action server connected.")
 
    def execute_point(self, x, y, yaw=None):
        if not self.is_running:
            return False
 
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id  = "map"
        goal.target_pose.header.stamp     = rospy.Time.now()
        goal.target_pose.pose.position.x  = x
        goal.target_pose.pose.position.y  = y
        
        if yaw is not None:
            q = quaternion_from_euler(0, 0, yaw)
            goal.target_pose.pose.orientation.x = q[0]
            goal.target_pose.pose.orientation.y = q[1]
            goal.target_pose.pose.orientation.z = q[2]
            goal.target_pose.pose.orientation.w = q[3]
        else:
            goal.target_pose.pose.orientation.w = 1.0
 
        self.client.send_goal(goal)
        finished = self.client.wait_for_result(rospy.Duration(self.timeout))
 
        if not finished:
            rospy.logwarn("Goal execution timed out, skipping to next.")
            self.client.cancel_goal()
            return False
 
        state = self.client.get_state()
        if state != GoalStatus.SUCCEEDED:
            rospy.logwarn(f"Goal failed (status {state}), skipping to next.")
            return False
 
        return True
 
    def start(self):
        self.is_running = True
 
    def stop(self):
        self.is_running = False
        self.client.cancel_all_goals()
