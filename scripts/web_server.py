#!/usr/bin/env python3
import rospy
import http.server
import socketserver
import os
import rospkg
import socket

class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def main():
    rospy.init_node('web_server')
    port = rospy.get_param('~port', 8000)
    
    # 找到 web_interface 的資料夾路徑
    rospack = rospkg.RosPack()
    pkg_path = rospack.get_path('turtlebot3_ccpp')
    web_dir = os.path.join(pkg_path, 'web_interface')
    
    os.chdir(web_dir)
    
    # 啟動 Web Server
    Handler = http.server.SimpleHTTPRequestHandler
    
    # 允許重複使用 Port 避免重啟報錯
    ThreadingSimpleServer.allow_reuse_address = True
    
    try:
        with ThreadingSimpleServer(("", port), Handler) as httpd:
            # 取得本機 IP 以顯示提示
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            rospy.loginfo("========================================")
            rospy.loginfo(f"Web Server is Running!")
            rospy.loginfo(f"Please open http://{local_ip}:{port} or http://<TB3_IP>:{port}")
            rospy.loginfo(f"on your phone or PC in the same network.")
            rospy.loginfo("========================================")
            
            httpd.serve_forever()
    except Exception as e:
        rospy.logerr(f"Failed to start web server: {e}")

if __name__ == '__main__':
    main()
