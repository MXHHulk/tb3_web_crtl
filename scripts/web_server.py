#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案名稱：web_server.py (網頁介面伺服器)
檔案類型：HTTP Server / 後端入口節點

核心功能：
1. 建立一個輕量級 HTTP 伺服器，託管網頁控制介面 (HTML/JS/CSS)。
2. 提供網頁載入所需的靜態檔案目錄路徑。
3. 自動偵測本機 IP，方便使用者在手機或 PC 瀏覽器端遠端遙控。

架構說明：
  此伺服器只負責「提供靜態網頁檔案」，不處理任何 ROS 資料。
  實際的機器人通訊是由瀏覽器端的 roslib.js 透過 WebSocket:9090 (rosbridge) 完成。
  因此本節點非常輕量，不需要複雜的路由或 API 處理。

關鍵依賴：
- http.server & socketserver: Python 內建的網路服務模組
- rospkg: 用於動態尋找 ROS Package 的路徑
- socket: 用於查詢系統 IP 位址
"""

import rospy
import http.server
import socketserver
import os
import rospkg
import socket


# 繼承 ThreadingMixIn：讓伺服器能同時處理多個瀏覽器連線
# 若不使用 ThreadingMixIn，第二個連線請求需等第一個完全結束才能處理
class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def main():
    # 初始化 ROS 節點，使 rospy.loginfo 等日誌工具可用
    rospy.init_node('web_server')

    # 從 ROS 參數伺服器讀取埠號，預設值 8000
    # 可在 launch 檔中透過 <param name="port" value="8080"/> 覆寫
    port = rospy.get_param('~port', 8000)

    # 使用 rospkg 動態定位 package 路徑，避免硬寫絕對路徑
    # 這樣無論 package 安裝在哪個 catkin workspace 都能正確找到
    rospack = rospkg.RosPack()
    pkg_path = rospack.get_path('turtlebot3_ccpp')

    # 組合出 web_interface 目錄的完整路徑
    web_dir = os.path.join(pkg_path, 'web_interface')

    # 切換工作目錄至 web_interface 資料夾
    # Python 的 SimpleHTTPRequestHandler 預設服務「當前工作目錄」的檔案
    # 因此必須先 chdir，才能正確提供 index.html、js/、css/ 等資源
    os.chdir(web_dir)

    # 使用 Python 內建的靜態檔案處理器
    # 它會根據請求路徑自動回傳對應的檔案，並設定正確的 MIME Type
    Handler = http.server.SimpleHTTPRequestHandler

    # 允許地址重用：當節點重啟時，OS 可能仍保留舊的 TCP 連線狀態 (TIME_WAIT)
    # 設定 allow_reuse_address = True 讓伺服器能立刻重新綁定同一個埠號，避免 "Address already in use" 錯誤
    ThreadingSimpleServer.allow_reuse_address = True

    try:
        # 綁定所有網路介面 ("" 等同 "0.0.0.0")，讓區域網路內的任何裝置都能連線
        with ThreadingSimpleServer(("", port), Handler) as httpd:
            # 獲取本機的 hostname 與對應的 IP 位址，印出方便使用者直接複製
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            rospy.loginfo("========================================")
            rospy.loginfo(f"網頁伺服器已成功啟動！")
            rospy.loginfo(f"請在相同網域的瀏覽器中打開以下網址：")
            rospy.loginfo(f"http://{local_ip}:{port}")
            rospy.loginfo(f"或者 http://<TB3_IP_ADDRESS>:{port}")
            rospy.loginfo("========================================")

            # serve_forever() 進入無限迴圈，持續監聽並回應 HTTP 請求
            # 當 ROS 節點被關閉時，with 區塊退出並自動呼叫 httpd.shutdown()
            httpd.serve_forever()

    except Exception as e:
        rospy.logerr(f"啟動網頁伺服器失敗: {e}")


if __name__ == '__main__':
    main()
