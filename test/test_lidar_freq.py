#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import LaserScan
import time

class LidarFreqTester:
    def __init__(self):
        rospy.init_node('lidar_freq_tester', anonymous=True)
        
        self.count = 0
        self.start_time = None
        self.last_log_time = None
        
        # 訂閱光達資料
        self.sub = rospy.Subscriber('/scan', LaserScan, self.callback)
        
        rospy.loginfo("光達頻率測試節點已啟動，等待 /scan 訊息...")
        
    def callback(self, msg):
        current_time = time.time()
        
        if self.start_time is None:
            self.start_time = current_time
            self.last_log_time = current_time
            return
            
        self.count += 1
        
        # 每隔 2 秒計算並輸出一次平均頻率
        if current_time - self.last_log_time >= 2.0:
            elapsed = current_time - self.start_time
            avg_freq = self.count / elapsed
            
            # 計算當前瞬時頻率 (最近 2 秒)
            # 這裡為了簡單，只顯示總平均
            rospy.loginfo(f"收到訊息總數: {self.count} | 總運行時間: {elapsed:.2f}s | 平均頻率: {avg_freq:.2f} Hz")
            
            self.last_log_time = current_time

if __name__ == '__main__':
    try:
        tester = LidarFreqTester()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
