#!/usr/bin/env python3
import rospy

if __name__ == '__main__':
    rospy.init_node('info_logger')
    rospy.loginfo("========================================")
    rospy.loginfo("TurtleBot3 CCPP Monitor is now LIVE!")
    rospy.loginfo("Please open web_interface/index.html in your browser.")
    rospy.loginfo("Make sure rosbridge_server is running.")
    rospy.loginfo("========================================")
    rospy.spin()
