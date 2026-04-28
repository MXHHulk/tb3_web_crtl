#!/usr/bin/env python3
import rospy
import actionlib
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib_msgs.msg import GoalStatus
 
class PathExecutor:
    def __init__(self, timeout=30.0):
        self.client  = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        self.timeout = timeout
        self.is_running = False
 
        rospy.loginfo("Waiting for move_base action server...")
        # [修正 1] 加入 timeout 避免永久卡住（等待最多 30 秒）
        connected = self.client.wait_for_server(rospy.Duration(30.0))
        if connected:
            rospy.loginfo("move_base action server connected.")
        else:
            rospy.logwarn("move_base action server not available within 30s. "
                          "Goals will be sent when server comes online.")
 
    def execute_point(self, x, y):
        if not self.is_running:
            return False
 
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id  = "map"
        goal.target_pose.header.stamp     = rospy.Time.now()
        goal.target_pose.pose.position.x  = x
        goal.target_pose.pose.position.y  = y
        goal.target_pose.pose.orientation.w = 1.0
 
        self.client.send_goal(goal)
        finished = self.client.wait_for_result(rospy.Duration(self.timeout))
 
        if not finished:
            rospy.logwarn("Goal (%.2f, %.2f) timed out after %.1fs.", x, y, self.timeout)
            self.client.cancel_goal()
            return False
 
        state = self.client.get_state()
        if state != GoalStatus.SUCCEEDED:
            rospy.logwarn("Goal (%.2f, %.2f) failed with state: %d", x, y, state)
            return False
 
        return True
 
    def start(self):
        self.is_running = True
 
    def stop(self):
        self.is_running = False
        self.client.cancel_all_goals()