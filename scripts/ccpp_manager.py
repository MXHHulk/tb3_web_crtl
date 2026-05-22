#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：ccpp_manager.py (TB3 核心覆蓋任務管理器)
檔案類型：ROS 核心控制節點 / Python 邏輯腳本

核心功能：
1. 作為整個系統的「大腦」，負責調度「地圖處理」、「區域偵測」與「路徑執行」。
2. 實現動態全覆蓋路徑規劃 (CCPP)，當偵測到未清理區域時執行牛耕式 (Boustrophedon) 清掃。
3. 當區域清理完畢後，自動切換至探索模式 (Frontier Exploration) 尋找未知空間。

狀態機設計：
  IDLE      → 系統閒置，等待啟動指令
  EXPLORING → 無大型待清理區域，前往 Frontier 點擴張地圖
  COVERING  → 發現待清理區域，執行牛耕式掃描路徑

關鍵依賴：
- rospy: ROS Python 客戶端庫
- numpy & cv2: 用於地圖處理與電腦視覺計算
- tf: 座標轉換庫，負責機器人位姿追蹤
- nav_msgs & geometry_msgs: ROS 標準導航與幾何訊息格式

通訊介面：
- 發布 (Pub):
    - /ccpp/task_progress [std_msgs/Float32]: 任務進度百分比
    - /ccpp/target_polygon [geometry_msgs/PolygonStamped]: 當前正在清理的目標區域邊界
    - /ccpp/coverage_map [nav_msgs/OccupancyGrid]: 視覺化顯示已走過的清掃軌跡
    - /ccpp/processed_map [nav_msgs/OccupancyGrid]: 經過去雜訊處理後的演算法專用地圖
    - /ccpp/robot_pose [geometry_msgs/PoseStamped]: 機器人在 map 座標系下的即時位置
- 訂閱 (Sub):
    - /map [nav_msgs/OccupancyGrid]: 訂閱由 SLAM 產生的即時地圖
- 服務 (Service):
    - /ccpp/start: 開始執行任務
    - /ccpp/stop: 暫停任務
    - /ccpp/reset_coverage: 重置清掃紀錄並重啟系統
    - /ccpp/get_task_status: 獲取任務狀態
"""

import rospy
import numpy as np
import threading
import queue
import cv2
import os
import sys
import tf
import math

# 確保 ROS 能正確找到同目錄下的自定義模組
# 因為 ROS 節點的執行路徑不固定，必須手動加入腳本目錄到 Python 路徑
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PolygonStamped, Point32, PoseStamped
from std_msgs.msg import Float32
from std_srvs.srv import Trigger, TriggerResponse
from turtlebot3_ccpp.srv import GetTaskStatus, GetTaskStatusResponse

# 匯入自定義的地圖處理與規劃工具 (同目錄下)
from map_processor import preprocess_map, get_frontier_map
from region_detector import detect_regions, find_best_frontier
from coverage_planner import generate_boustrophedon_path
from path_executor import PathExecutor


class DynamicCCPPManager:
    def __init__(self):
        """
        初始化管理器類別，設定 ROS 參數、變數與通訊介面。
        此函數在節點啟動時只執行一次。
        """
        # 初始化 ROS 節點，名稱為 ccpp_manager
        rospy.init_node('ccpp_manager')

        # =====================================================================
        # 參數設定 (從 launch 檔或 rosparam 讀取)
        # =====================================================================
        # 機器人有效清掃寬度 (m)，TB3 Burger 實際寬度約 0.178m
        # 設定較小的值可增加路徑重疊度，補償 SLAM 的定位誤差
        self.robot_width = rospy.get_param('~robot_width', 0.178)

        # 掃描線重疊率 (0~1)：0.8 表示相鄰掃描線重疊 80%
        # 重疊率越高，路徑越密集，清掃越徹底但效率越低
        self.overlap = rospy.get_param('~scan_overlap', 0.8)

        # 實際步進距離：重疊率越高，間距越小
        # 例如：overlap=0.8 → 間距 = 0.178 × (1-0.8) = 0.0356m，每條掃描線間距約 3.6cm
        self.step_size = self.robot_width * (1.0 - self.overlap)

        # =====================================================================
        # 狀態變數
        # =====================================================================
        # 系統狀態機，三種狀態：IDLE / EXPLORING / COVERING
        self.state = "IDLE"

        # 儲存最新的 SLAM 地圖訊息 (由 map_callback 更新)
        self.map_msg = None

        # 覆蓋紀錄陣列：與地圖等大的 2D 矩陣
        # 255 = 機器人已走過的格子，0 = 尚未清理的格子
        self.coverage_array = None

        # 機器人當前位姿 (由 TF 查詢取得，由 pose_timer_callback 更新)
        self.robot_pose = None

        # 整體任務進度百分比 (0.0 ~ 1.0)
        self.progress = 0.0

        # 線程鎖：map_callback 與 main_loop 在不同執行緒中存取 map_msg
        # 使用 Lock 防止數據競爭 (Race Condition)
        self.lock = threading.Lock()

        # 初始化路徑執行器 (封裝 move_base Action Client)
        self.executor = PathExecutor()

        # =====================================================================
        # ROS 通訊發布者
        # =====================================================================
        # 任務進度 (0.0~1.0) → 網頁進度條
        self.progress_pub = rospy.Publisher('/ccpp/task_progress', Float32, queue_size=1)

        # 當前清掃目標的多邊形邊界 → 網頁綠色框線
        self.target_pub = rospy.Publisher('/ccpp/target_polygon', PolygonStamped, queue_size=1)

        # 已清掃軌跡地圖 → 網頁藍色覆蓋層
        self.coverage_pub = rospy.Publisher('/ccpp/coverage_map', OccupancyGrid, queue_size=1)

        # 預處理後的演算法專用地圖 → 網頁橘色圖層 (latch=True: 新訂閱者立刻收到最新值)
        self.processed_map_pub = rospy.Publisher('/ccpp/processed_map', OccupancyGrid, queue_size=1, latch=True)

        # 機器人位姿 → 網頁黃色機器人圖示
        self.robot_pose_pub = rospy.Publisher('/ccpp/robot_pose', PoseStamped, queue_size=1)

        # =====================================================================
        # TF 座標變換監聽器
        # =====================================================================
        # TF 是 ROS 的座標系統管理框架
        # 查詢 map → base_footprint 的轉換可得到機器人在地圖中的位置與朝向
        self.tf_listener = tf.TransformListener()

        # =====================================================================
        # ROS 訂閱者
        # =====================================================================
        # 訂閱 SLAM 產生的即時地圖，每次地圖更新都觸發 map_callback
        rospy.Subscriber('/map', OccupancyGrid, self.map_callback)

        # =====================================================================
        # 定時器
        # =====================================================================
        # 每 0.1 秒 (10Hz) 執行一次 pose_timer_callback
        # 負責：① 更新機器人位姿 ② 更新清掃覆蓋記錄 ③ 發布機器人位置訊息
        rospy.Timer(rospy.Duration(0.1), self.pose_timer_callback)

        # =====================================================================
        # ROS 服務伺服端
        # =====================================================================
        # 網頁按鈕透過 rosbridge → WebSocket 呼叫這些服務
        rospy.Service('/ccpp/start', Trigger, self.handle_start)
        rospy.Service('/ccpp/stop', Trigger, self.handle_stop)
        rospy.Service('/ccpp/reset_coverage', Trigger, self.handle_reset_coverage)
        rospy.Service('/ccpp/get_task_status', GetTaskStatus, self.handle_status)

        # =====================================================================
        # 主邏輯背景執行緒
        # =====================================================================
        # daemon=True：主程式結束時此執行緒自動終止，不會造成孤兒執行緒
        # 使用獨立執行緒執行 main_loop 是為了不阻塞 ROS 的回呼函數排程器
        self.main_thread = threading.Thread(target=self.main_loop, daemon=True)
        self.main_thread.start()

        rospy.loginfo("Robust Auto CCPP Manager 成功啟動。")

    # =========================================================================
    # 回呼函數區塊 (Callbacks)
    # =========================================================================

    def pose_timer_callback(self, event):
        """
        定時 (10Hz) 從 TF 獲取機器人位姿，並更新覆蓋紀錄與發布位置。

        TF 查詢說明：
          lookupTransform(target_frame, source_frame, time)
          查詢「從 source_frame 到 target_frame」的座標轉換
          這裡查詢 map → base_footprint，結果就是機器人在地圖中的 (x, y, 旋轉)
        """
        try:
            # 等待 TF 樹中有 map → base_footprint 的轉換關係 (最多等 0.2 秒)
            self.tf_listener.waitForTransform('/map', '/base_footprint', rospy.Time(0), rospy.Duration(0.2))
            # 查詢最新的座標轉換
            # trans = (x, y, z) 平移向量 (m)
            # rot   = (x, y, z, w) 四元數旋轉
            (trans, rot) = self.tf_listener.lookupTransform('/map', '/base_footprint', rospy.Time(0))

            # 封裝成 PoseStamped 訊息，供網頁介面繪製機器人圖示使用
            pose_msg = PoseStamped()
            pose_msg.header.frame_id = 'map'
            pose_msg.header.stamp = rospy.Time.now()
            pose_msg.pose.position.x = trans[0]
            pose_msg.pose.position.y = trans[1]
            # trans[2] (z) 忽略，TB3 是平面機器人
            pose_msg.pose.orientation.x = rot[0]
            pose_msg.pose.orientation.y = rot[1]
            pose_msg.pose.orientation.z = rot[2]
            pose_msg.pose.orientation.w = rot[3]

            # 透過 ROS Topic 發布位置 → 經 rosbridge → 瀏覽器
            self.robot_pose_pub.publish(pose_msg)

            # 更新類別成員變數，供 main_loop 使用
            self.robot_pose = pose_msg.pose

            # 根據目前位置在覆蓋紀錄陣列上標記已清掃區域
            self.update_coverage()

        except Exception:
            # 系統剛啟動時 TF 樹尚未建立，或 SLAM 還在初始化，查詢會失敗
            # 使用 pass 靜默忽略，等待下一個計時器觸發
            pass

    def map_callback(self, msg):
        """
        接收並儲存 SLAM (/map) 傳來的最新地圖數據。

        每當 gmapping 更新地圖 (通常每 0.5~1 秒一次) 就會觸發此回呼。
        同時負責初始化覆蓋記錄陣列，並重新發布處理後的地圖。
        """
        with self.lock:
            self.map_msg = msg  # 儲存最新地圖，覆蓋舊版本

            # 當地圖尺寸改變時 (SLAM 動態擴張地圖邊界)，重新建立覆蓋記錄陣列
            # shape 比對確保陣列永遠與地圖大小一致
            if self.coverage_array is None or self.coverage_array.shape != (msg.info.height, msg.info.width):
                self.coverage_array = np.zeros((msg.info.height, msg.info.width), dtype=np.uint8)

            # 每次地圖更新後立即重新發布處理後的地圖 (供網頁視覺化)
            self.publish_processed_map()

    def publish_processed_map(self):
        """
        對 SLAM 原始地圖進行形態學預處理後，以新的 OccupancyGrid 格式重新發布。

        此地圖主要用途：
        1. 供 main_loop 的演算法使用 (去除雜訊後更穩定)
        2. 供網頁前端顯示「橘色障礙物層」，幫助使用者了解演算法視角
        """
        if self.map_msg is None:
            return

        # 呼叫 map_processor 的核心處理函數
        # 輸出：255=安全空地, 0=障礙/未知/安全邊距
        cleaned = preprocess_map(self.map_msg.data, self.map_msg.info.width, self.map_msg.info.height)

        # 建立新的 OccupancyGrid 訊息，複用原地圖的 info (尺寸、解析度、原點)
        msg = OccupancyGrid()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        msg.info = self.map_msg.info

        # 將 OpenCV 像素值 (0 or 255) 轉換回 ROS OccupancyGrid 標準值 (0, 100)
        # 目的：讓發布的地圖符合 ROS 慣例，其他節點也能正確解讀
        data = np.zeros_like(cleaned, dtype=np.int8)
        data[cleaned == 0] = 100    # 障礙物/不可走區域 → ROS 值 100
        data[cleaned == 255] = 0    # 可行走空地 → ROS 值 0

        msg.data = data.flatten().tolist()  # 轉為一維列表符合 ROS 訊息格式
        self.processed_map_pub.publish(msg)

    # =========================================================================
    # 核心邏輯區塊 (Core Logic)
    # =========================================================================

    def update_coverage(self):
        """
        根據機器人目前在世界座標的位置，在覆蓋紀錄陣列中標記已清掃區域。

        使用 cv2.circle 在機器人位置畫一個實心圓，圓的半徑對應機器人的清掃寬度。
        這個陣列後續在 main_loop 中被扣除，得到「尚未清理的待清掃地圖」。
        """
        if self.coverage_array is None or self.robot_pose is None or self.map_msg is None:
            return

        info = self.map_msg.info

        # 世界座標 (m) → 像素座標轉換公式
        # px = (world_x - map_origin_x) / resolution
        mx = int((self.robot_pose.position.x - info.origin.position.x) / info.resolution)
        my = int((self.robot_pose.position.y - info.origin.position.y) / info.resolution)

        # 機器人清掃半徑：實體寬度的一半轉換為像素單位
        radius = int((self.robot_width / 2.0) / info.resolution)

        # 在覆蓋記錄陣列上畫實心圓 (255 = 已清理)
        # -1 表示 filled (實心)，這樣整個機器人寬度範圍都被標記
        cv2.circle(self.coverage_array, (mx, my), radius, 255, -1)

        # 限制發布頻率：約每 2 秒發布一次覆蓋地圖至網頁
        # 避免高頻發布大型地圖數據造成 rosbridge 壅塞
        if rospy.Time.now().to_sec() % 2.0 < 0.1:
            self.publish_coverage_map()

    def main_loop(self):
        """
        核心決策循環：在背景執行緒中持續運行，判斷當前應執行清掃還是探索。

        決策優先順序：
          1. 若有面積 > 400px 的待清理區域 → COVERING (牛耕式清掃)
          2. 若無待清理區域但有 Frontier   → EXPLORING (前往邊界探索)
          3. 若兩者皆無                     → IDLE (任務完成)
        """
        while not rospy.is_shutdown():
            # 系統在 IDLE 狀態、或地圖/位置資料尚未就緒時，持續等待
            if self.state == "IDLE" or self.map_msg is None or self.robot_pose is None:
                rospy.sleep(1.0)
                continue

            # ---- Step 1: 獲取最新的預處理地圖 ----
            # 每次迭代都重新處理，確保使用最新的 SLAM 地圖
            cleaned_map = preprocess_map(self.map_msg.data, self.map_msg.info.width, self.map_msg.info.height)

            # ---- Step 2: 計算「待清理地圖」----
            # 將已覆蓋的區域從乾淨地圖中「扣除」
            # coverage_array > 0 的像素設為 0 (黑)，只剩下還沒走過的空白
            pending_map = cleaned_map.copy()
            pending_map[self.coverage_array > 0] = 0

            # ---- Step 3: 偵測待清理的封閉區域 ----
            regions = detect_regions(pending_map)

            # ---- 分支判斷 ----
            if regions and regions[0]['area'] > 400:
                # 發現有足夠大的待清理區域 (> 400px，依解析度約 1m²)
                # 切換至 COVERING 狀態並執行牛耕路徑
                self.state = "COVERING"
                self.execute_coverage(regions[0])  # 傳入面積最大的區域
            else:
                # 無待清理區域，嘗試探索未知空間 (Frontier Exploration)
                frontier_map = get_frontier_map(self.map_msg.data, self.map_msg.info.width, self.map_msg.info.height)
                # 將機器人世界座標轉換為像素座標，用於計算與 Frontier 的距離
                robot_px = self.world_to_pixel(self.robot_pose.position.x, self.robot_pose.position.y)
                target_frontier = find_best_frontier(frontier_map, robot_px)

                if target_frontier:
                    self.state = "EXPLORING"
                    # 將 Frontier 像素座標轉回世界座標以作為導航目標
                    target_world = self.pixel_to_world(target_frontier[0], target_frontier[1])
                    # 計算朝向目標點的角度 (讓機器人面向前進方向)
                    yaw = math.atan2(
                        target_world[1] - self.robot_pose.position.y,
                        target_world[0] - self.robot_pose.position.x
                    )
                    self.executor.execute_point(target_world[0], target_world[1], yaw=yaw)
                else:
                    # 地圖已全數清掃且無未知邊界，表示任務完成
                    rospy.loginfo("所有可達空間已覆蓋完畢，任務結束。")
                    self.state = "IDLE"

            # 每次決策後短暫休眠，避免 CPU 高佔用
            rospy.sleep(1.0)

    def execute_coverage(self, region_info):
        """
        針對特定區域生成牛耕式路徑並驅動機器人逐點執行。

        包含連續失敗的容錯機制：若同一區域連續失敗 3 次以上，
        則放棄此次區域，返回 main_loop 重新評估地圖，避免機器人被卡住。

        Args:
            region_info: 來自 detect_regions() 的區域資訊字典
                         {contour, approx, area, center, is_quad}
        """
        # 發布最小外接矩形邊界至網頁，顯示綠色框線
        self.publish_target_region(region_info['rect_box'])

        # 將世界座標的步進距離轉換為像素單位
        # 例如：step_size=0.14m, resolution=0.05m/px → step_px=2.8px
        step_px = self.step_size / self.map_msg.info.resolution

        # 以矩形頂點生成牛耕式路徑：矩形的規則邊界確保掃描線等長、路徑平行
        path_px = generate_boustrophedon_path(region_info['rect_box'], step_px)

        failed_count = 0  # 連續失敗計數器

        for i in range(len(path_px)):
            # 若任務被 stop 服務中斷 (state 被設回 IDLE)，立即停止執行
            if self.state == "IDLE":
                break

            # 依已完成點位比例更新整體進度，供網頁進度條即時顯示
            self.progress = (i + 1) / len(path_px)

            pt = path_px[i]
            world_pt = self.pixel_to_world(pt[0], pt[1])  # 像素座標 → 世界座標

            # 距離過濾：若目標點距機器人太近 (< 0.2m)，跳過此點
            # 避免 move_base 為幾公分的距離進行無謂的規劃，造成機器人原地抖動
            dist = math.sqrt(
                (world_pt[0] - self.robot_pose.position.x) ** 2 +
                (world_pt[1] - self.robot_pose.position.y) ** 2
            )
            # 門檻降至 0.05m，避免跳過間距僅約 0.035m 的相鄰掃描線起點
            if dist < 0.05:
                continue

            # 計算朝向：讓機器人在前往當前點時，面朝下一個路徑點的方向
            # 這使機器人移動更流暢，減少到達後再轉向的動作
            yaw = None
            if i + 1 < len(path_px):
                next_pt = self.pixel_to_world(path_px[i + 1][0], path_px[i + 1][1])
                yaw = math.atan2(next_pt[1] - world_pt[1], next_pt[0] - world_pt[0])

            # 發送單個導航目標點，並等待結果 (阻塞式)
            success = self.executor.execute_point(world_pt[0], world_pt[1], yaw=yaw)

            if not success:
                failed_count += 1
                rospy.logwarn(f"導航點失敗 ({failed_count})，跳轉至下一點。")
                # 連續失敗超過 3 次：可能地圖變動劇烈或機器人被困
                # 跳出此區域的執行，讓 main_loop 重新評估整張地圖
                if failed_count > 3:
                    rospy.logerr("該區域失敗次數過多，重新掃描地圖中...")
                    break
            else:
                failed_count = 0  # 成功則重置連續失敗計數

        rospy.loginfo("區域覆蓋步進完成。")

    # =========================================================================
    # 座標轉換工具函數 (Utils)
    # =========================================================================

    def world_to_pixel(self, x, y):
        """
        將物理世界座標 (m) 轉換為地圖像素座標。

        公式：pixel = (world - map_origin) / resolution
        map_origin 是 OccupancyGrid.info.origin，即地圖左下角的世界座標

        Args:
            x, y: 世界座標 (公尺)
        Returns:
            (px, py): 像素座標 (整數)
        """
        info = self.map_msg.info
        px = int((x - info.origin.position.x) / info.resolution)
        py = int((y - info.origin.position.y) / info.resolution)
        return (px, py)

    def pixel_to_world(self, px, py):
        """
        將地圖像素座標轉換為物理世界座標 (m)。

        公式：world = pixel * resolution + map_origin

        Args:
            px, py: 像素座標
        Returns:
            (wx, wy): 世界座標 (公尺)
        """
        info = self.map_msg.info
        wx = px * info.resolution + info.origin.position.x
        wy = py * info.resolution + info.origin.position.y
        return (wx, wy)

    def publish_coverage_map(self):
        """
        將已清掃紀錄陣列轉換為 ROS OccupancyGrid 格式並發布至 /ccpp/coverage_map。
        網頁前端訂閱此 Topic 後，會將 value=100 的像素以藍色半透明顯示。
        """
        if self.coverage_array is None:
            return

        msg = OccupancyGrid()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        msg.info = self.map_msg.info  # 複用原地圖的解析度與座標系資訊

        # 將覆蓋記錄陣列 (0 or 255) 轉換為 ROS 格式 (0 or 100)
        # 已走過 (255) → 標記為 100 (障礙物色塊)，讓網頁以顏色區分
        data = np.zeros_like(self.coverage_array, dtype=np.int8)
        data[self.coverage_array > 0] = 100

        msg.data = data.flatten().tolist()
        self.coverage_pub.publish(msg)

    def publish_target_region(self, box_pts):
        """
        將待清理區域的矩形頂點 (像素座標) 轉換為 ROS 訊息格式並發布。
        網頁前端訂閱後，會在地圖上以綠色外框顯示當前清掃區域。

        Args:
            box_pts: 最小外接矩形的四個頂點，來自 cv2.boxPoints，形狀為 (4, 2)
        """
        if not len(box_pts) or self.map_msg is None:
            return

        poly = PolygonStamped()
        poly.header.frame_id = "map"
        poly.header.stamp = rospy.Time.now()

        # boxPoints 輸出的結構是 (4, 2)，每個 pt 直接是 [x, y]
        for pt in box_pts:
            p = Point32()
            world_pt = self.pixel_to_world(int(pt[0]), int(pt[1]))
            p.x, p.y = world_pt[0], world_pt[1]
            poly.polygon.points.append(p)

        self.target_pub.publish(poly)

    # =========================================================================
    # 服務處理區塊 (Service Handlers)
    # =========================================================================

    def handle_reset_coverage(self, req):
        """
        重置服務：停止當前任務並觸發整個系統重啟。
        透過 subprocess 呼叫 start_project.sh，完全重置 ROS 環境與地圖。

        使用 setsid 是為了讓子程序在新的 session group 中執行，
        防止父程序 (此 ROS 節點) 終止時子程序也被殺死。
        """
        with self.lock:
            self.state = "IDLE"
            self.executor.stop()
            try:
                import subprocess
                # 找到 start_project.sh 的絕對路徑 (位於 package 根目錄)
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "start_project.sh"))
                # sleep 1：給當前節點時間回傳服務響應後再啟動重啟腳本
                subprocess.Popen(["setsid", "bash", "-c", f"sleep 1 && /bin/bash {script_path}"])
            except Exception as e:
                return TriggerResponse(success=False, message=str(e))
        return TriggerResponse(success=True, message="系統正在重啟...")

    def handle_start(self, req):
        """
        啟動服務：將狀態設為 EXPLORING，並啟動 PathExecutor 的執行開關。
        main_loop 在偵測到狀態非 IDLE 後會自動開始決策。
        """
        self.state = "EXPLORING"
        self.executor.start()  # 打開 PathExecutor 的 is_running 開關
        return TriggerResponse(success=True, message="自動化覆蓋任務已啟動")

    def handle_stop(self, req):
        """
        停止服務：將狀態設回 IDLE，並立即取消所有 move_base 導航目標。
        execute_coverage 的 for 迴圈在每次迭代都會檢查 state，因此會即時終止。
        """
        self.state = "IDLE"
        self.executor.stop()  # 取消 move_base 目標並關閉 is_running 開關
        return TriggerResponse(success=True, message="任務已停止")

    def handle_status(self, req):
        """
        狀態查詢服務：回傳當前的任務狀態與整體進度。
        網頁前端每秒輪詢此服務以更新 UI 的狀態標籤。
        """
        res = GetTaskStatusResponse()
        if hasattr(res, 'task_state'):
            res.task_state = self.state  # "IDLE" / "EXPLORING" / "COVERING"
        res.overall_progress = self.progress  # 0.0 ~ 1.0
        res.success = True
        return res


if __name__ == '__main__':
    # 建立管理器實體 (初始化所有 ROS 介面與執行緒)
    mgr = DynamicCCPPManager()
    # rospy.spin() 進入 ROS 事件循環，持續處理回呼函數與服務請求，直到節點關閉
    rospy.spin()
