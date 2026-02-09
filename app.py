from flask import Flask, render_template, jsonify, send_file
import subprocess
import os
import signal

app = Flask(__name__)
slam_process = None
explore_process = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_slam')
def start_slam():
    global slam_process
    if slam_process is None:
        # 強制只抓 IPv4 的指令
        cmd = "bash -c 'source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash; " \
              "export TURTLEBOT3_MODEL=burger; export LDS_MODEL=LDS-01; " \
              "export MY_IP=$(hostname -I | tr \" \" \"\\n\" | grep -m 1 -E \"^[0-9.]+\$\"); " \
              "export ROS_IP=$MY_IP; export ROS_MASTER_URI=http://\$MY_IP:11311; " \
              "roslaunch turtlebot3_slam turtlebot3_slam.launch open_rviz:=false map_update_interval:=5.0'"
        slam_process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
        return jsonify({"status": "SLAM 已修正 IP 並啟動"})
    return jsonify({"status": "SLAM 運行中"})

@app.route('/start_explore')
def start_explore():
    global explore_process
    if explore_process is None:
        # 自動探索必須依賴 move_base (導航)，所以在這裡一併啟動
        cmd = "bash -c 'source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash; " \
              "export TURTLEBOT3_MODEL=burger; " \
              "roslaunch turtlebot3_navigation move_base.launch & sleep 5; " \
              "roslaunch explore_lite explore.launch'"
        explore_process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
        return jsonify({"status": "自動探索與導航已開啟"})
    return jsonify({"status": "探索運行中"})

@app.route('/stop_all')
def stop_all():
    global slam_process, explore_process
    # 殺掉所有相關進程，確保 /cmd_vel 回歸乾淨
    for proc in [slam_process, explore_process]:
        if proc:
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
    slam_process = None
    explore_process = None
    return jsonify({"status": "系統已重置，現在可嘗試手動操作"})

@app.route('/download_map')
def download_map():
    try:
        # 1. 使用 map_server 將地圖儲存到本地 (產生地圖檔 map.pgm 和 map.yaml)
        save_cmd = "bash -c 'source /opt/ros/noetic/setup.bash; " \
                   "cd /home/ubuntu/catkin_ws/src/tb3_web_crtl/static; " \
                   "rosrun map_server map_saver -f my_map'"
        subprocess.run(save_cmd, shell=True, check=True)
        
        # 2. 回傳產生的地圖圖檔給使用者下載
        map_path = "/home/ubuntu/catkin_ws/src/tb3_web_crtl/static/my_map.pgm"
        return send_file(map_path, as_attachment=True)
    except Exception as e:
        return jsonify({"status": f"儲存地圖失敗: {str(e)}"})

@app.route('/reset_system')
def reset_system():
    global slam_process, explore_process
    try:
        # 1. 停止 Flask 管理的進程
        for proc in [slam_process, explore_process]:
            if proc:
                os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        
        # 2. 強力清理所有 ROS 殘留節點 (包含 bringup 和 rosbridge)
        reset_cmd = "ps -ef | grep -E 'ros|python' | grep -v grep | awk '{print $2}' | xargs -r sudo kill -9"
        subprocess.run(reset_cmd, shell=True)
        
        slam_process = None
        explore_process = None
        
        return jsonify({"status": "環境已重置，請等待 5 秒後重新啟動"})
    except Exception as e:
        return jsonify({"status": f"重置失敗: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
