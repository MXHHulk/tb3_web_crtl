#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：path_executor.py (MoveBase 動作封裝器)
檔案類型：ROS Actionlib 客戶端介面

核心功能：
1. 作為與導航堆疊 (Navigation Stack) 通訊的橋樑，負責發送目標點給 move_base。
2. 管理導航點的超時處理與狀態追蹤，確保機器人在遇到卡頓時能快速切換下一點。
3. 封裝歐拉角 (Euler) 轉四元數 (Quaternion) 的座標換算。

ROS Actionlib 概念：
  move_base 採用 Action Server/Client 模式 (非普通的 Service)，
  因為導航是「長時間非同步任務」：
    - Client 發送目標 (Goal)
    - Server 回報進度 (Feedback)
    - Server 最終回傳結果 (Result：SUCCEEDED / ABORTED / PREEMPTED)
  使用 wait_for_result() 等待結果，並設有 timeout 防止永久卡住。

關鍵依賴：
- actionlib: ROS 異步動作通訊庫
- move_base_msgs: 導航目標訊息定義
- tf.transformations: 角度變換工具
"""

import rospy
import actionlib
import math
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib_msgs.msg import GoalStatus
from tf.transformations import quaternion_from_euler


class PathExecutor:
    def __init__(self, timeout=20.0):
        """
        初始化導航客戶端，並等待 move_base Action Server 上線。

        Args:
            timeout: 單個點位導航的最大等待時間 (秒)。
                     設定為 20 秒是考慮到 TB3 在複雜環境可能需要繞路，
                     但若超過通常代表機器人被困住，應跳過此點。
        """
        # 建立 SimpleActionClient 連結 move_base 伺服器
        # 'move_base' 是 ROS Navigation Stack 的預設 Action 名稱
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        self.timeout = timeout

        # 執行器開關：False=停止狀態，不接受新目標；True=運行狀態
        # ccpp_manager 透過 start()/stop() 控制此開關
        self.is_running = False

        rospy.loginfo("正在等待 move_base 行動伺服器...")
        # 最多等待 5 秒確認 move_base 伺服器是否有響應
        # 若系統剛啟動而 navigation stack 尚未就緒，會在此短暫阻塞
        connected = self.client.wait_for_server(rospy.Duration(5.0))
        if connected:
            rospy.loginfo("move_base 伺服器連線成功。")

    def execute_point(self, x, y, yaw=None):
        """
        發送單個導航目標點，並同步等待結果。

        此函數會「阻塞」直到導航完成、失敗或超時，
        因此 ccpp_manager 的 execute_coverage() 是逐點串行執行的。

        Args:
            x, y: 物理世界座標 (公尺)，使用 map 座標系
            yaw:  機器人到達目標點後的朝向角度 (弧度)
                  None 表示不指定朝向 (讓 move_base 自行決定)

        Returns:
            True  → 導航成功抵達目標點
            False → 導航失敗 (超時/路徑規劃失敗/被障礙物阻擋)
        """
        # 若執行器開關關閉 (STOP 狀態)，直接拒絕新目標
        if not self.is_running:
            return False

        # --- 建立 MoveBase 目標訊息 ---
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"       # 使用全域地圖座標系
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        # position.z 保持預設 0.0，TB3 是平面機器人

        # --- 朝向設定 ---
        if yaw is not None:
            # 將尤拉角 Yaw (繞 Z 軸旋轉) 轉換為 ROS 標準的四元數格式
            # quaternion_from_euler(roll=0, pitch=0, yaw) → (x, y, z, w)
            # TB3 只需設定 yaw，roll 和 pitch 固定為 0
            q = quaternion_from_euler(0, 0, yaw)
            goal.target_pose.pose.orientation.x = q[0]
            goal.target_pose.pose.orientation.y = q[1]
            goal.target_pose.pose.orientation.z = q[2]
            goal.target_pose.pose.orientation.w = q[3]
        else:
            # 無朝向要求時使用單位四元數 (w=1 代表無旋轉)
            goal.target_pose.pose.orientation.w = 1.0

        # --- 發送目標並等待結果 ---
        self.client.send_goal(goal)
        # wait_for_result 阻塞直到 move_base 回報結果或超時
        finished = self.client.wait_for_result(rospy.Duration(self.timeout))

        # --- 超時處理 ---
        if not finished:
            # 超過 timeout 秒仍未到達，主動取消導航目標
            # 常見原因：機器人被困住、路徑被動態障礙物阻擋
            rospy.logwarn("導航執行超時，跳轉至下一個點。")
            self.client.cancel_goal()
            return False

        # --- 結果狀態判斷 ---
        state = self.client.get_state()
        if state != GoalStatus.SUCCEEDED:
            # 常見失敗狀態：
            #   ABORTED (3)   = move_base 規劃失敗或多次重試後放棄
            #   PREEMPTED (2) = 目標被新目標取代 (通常不會在此發生)
            rospy.logwarn(f"導航失敗 (狀態碼 {state})，跳轉至下一個點。")
            return False

        return True  # GoalStatus.SUCCEEDED = 成功抵達

    def start(self):
        """
        啟動執行器，允許接受並執行新的導航目標。
        由 ccpp_manager.handle_start() 在收到啟動服務呼叫時觸發。
        """
        self.is_running = True

    def stop(self):
        """
        停止執行器，並取消所有正在進行的導航目標。
        由 ccpp_manager.handle_stop() 在收到停止服務呼叫時觸發。
        cancel_all_goals() 會立即中斷 move_base 正在執行的導航動作。
        """
        self.is_running = False
        self.client.cancel_all_goals()  # 傳送取消指令給 move_base Action Server
