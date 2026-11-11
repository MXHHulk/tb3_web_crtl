#!/usr/bin/env python3
"""
TurtleBot3 CCPP 車上控制台（常駐，開機由 systemd 啟動）

不依賴 ROS master：車子一開機就能用手機瀏覽器連進來，
  - 啟動／停止整套專案（roslaunch turtlebot3_ccpp start.launch）
  - 看執行狀態：roslaunch 行程、地圖網頁是否就緒、ROS 節點、覆蓋任務進度、電池、溫度、負載
  - 看 roslaunch 輸出日誌
  - 安全關機／重新開機（拔電前先關機，SD 卡才不會壞）
  - 轉接 map_server（8080）的地圖／覆蓋／遙控 API，手機只要開本頁一個網址就能操作全部功能

網址：http://<車子 IP>:8000   （手機開熱點時，車子 IP 在熱點的「已連線裝置」可查）
電腦版寬螢幕頁面仍在 http://<車子 IP>:8080 。

ROS 網路變數在「每次按啟動」時依車子當下的 IP 設定，
所以換了熱點、IP 變了也不用改 ~/.bashrc。
"""
import json, os, signal, socket, subprocess, threading, time, urllib.error, urllib.request
from collections import deque

from flask import Flask, Response, abort, jsonify, request, send_file

# ════════════════════════════════════════════════════════
#  設定
# ════════════════════════════════════════════════════════
PORT      = int(os.environ.get('CCPP_LAUNCHER_PORT', 8000))
MAP_PORT  = 8080                                   # start.launch 裡 map_server 的 port
PKG_DIR   = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
PAGE      = os.path.join(PKG_DIR, 'web', 'launcher.html')
LOG_DIR   = os.path.expanduser('~/.ros/ccpp_launcher')
ROS_SETUP = ('source /opt/ros/noetic/setup.bash && '
             'source ~/catkin_ws/devel/setup.bash')
LAUNCH_PATTERN = 'roslaunch turtlebot3_ccpp start.launch'
MODELS    = ('burger', 'waffle', 'waffle_pi')
STOP_WAIT = 20.0    # 送 SIGINT 後等 roslaunch 自己收尾的秒數，逾時才 SIGTERM / SIGKILL
LOG_KEEP  = 20      # 最多保留幾份 roslaunch 日誌

app = Flask(__name__)

lock  = threading.Lock()
run   = {                       # 由本控制台啟動的那一次執行
    'proc': None, 'state': 'idle', 'model': None, 't0': None,
    'ip': None, 'log': None, 'exit_code': None, 'msg': '',
}
cache = {                       # 背景輪詢結果（狀態 API 直接回傳，不在請求中做慢動作）
    'web_ready': False, 'nodes': [], 'battery': None, 'coverage': None,
    't_nodes': 0.0,
}
T_BOOT = time.time()


# ════════════════════════════════════════════════════════
#  小工具
# ════════════════════════════════════════════════════════
def host_ips():
    """車子目前的 IPv4（排除 127.x）。"""
    try:
        out = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=2).stdout
        ips = [a for a in out.split() if '.' in a and not a.startswith('127.')]
    except Exception:
        ips = []
    return ips


def ros_env(ip):
    env = dict(os.environ)
    env.update({
        'ROS_MASTER_URI': f'http://{ip}:11311',
        'ROS_HOSTNAME':   ip,
        'TURTLEBOT3_MODEL': run['model'] or 'burger',
        'LDS_MODEL':      env.get('LDS_MODEL', 'LDS-01'),
        'PYTHONUNBUFFERED': '1',
    })
    return env


def ros_cmd(cmd, timeout):
    """在 ROS 環境下跑一條短指令，回傳 stdout；失敗回傳 None。"""
    ip = run['ip'] or (host_ips() or ['127.0.0.1'])[0]
    try:
        r = subprocess.run(['bash', '-c', f'{ROS_SETUP} && {cmd}'], env=ros_env(ip),
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0


def external_pids():
    """不是本控制台開的、但正在跑的 start.launch（例如從終端機手動 roslaunch）。"""
    try:
        out = subprocess.run(['pgrep', '-f', LAUNCH_PATTERN], capture_output=True,
                             text=True, timeout=2).stdout
        pids = [int(p) for p in out.split()]
    except Exception:
        return []
    own = run['proc'].pid if run['proc'] and run['proc'].poll() is None else None
    return [p for p in pids if p != own and p != os.getpid()]


def read_file(path, default=None):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def system_info():
    temp = read_file('/sys/class/thermal/thermal_zone0/temp')
    mem = {}
    for line in (read_file('/proc/meminfo', '') or '').splitlines():
        k, _, v = line.partition(':')
        mem[k] = int(v.split()[0]) if v.split() else 0
    st = os.statvfs('/')
    disk_used = 1 - st.f_bavail / st.f_blocks if st.f_blocks else None
    return {
        'hostname':  socket.gethostname(),
        'ips':       host_ips(),
        'cpu_temp':  round(int(temp) / 1000, 1) if temp and temp.isdigit() else None,
        'load1':     round(os.getloadavg()[0], 2),
        'mem_used':  round(1 - mem.get('MemAvailable', 0) / mem['MemTotal'], 3) if mem.get('MemTotal') else None,
        'disk_used': round(disk_used, 3) if disk_used is not None else None,
        'disk_free_gb': round(st.f_bavail * st.f_frsize / 1e9, 1),
        'uptime_s':  int(float((read_file('/proc/uptime', '0') or '0').split()[0])),
    }


# ════════════════════════════════════════════════════════
#  啟動／停止
# ════════════════════════════════════════════════════════
def _prune_logs():
    try:
        logs = sorted(f for f in os.listdir(LOG_DIR) if f.endswith('.log'))
        for f in logs[:-LOG_KEEP]:
            os.remove(os.path.join(LOG_DIR, f))
    except OSError:
        pass


def start(model):
    with lock:
        if run['proc'] is not None and run['proc'].poll() is None:
            return False, '已經在執行中'
        if external_pids():
            return False, '偵測到另一個 start.launch 正在執行（可能是從終端機手動開的），請先停止'
        ips = host_ips()
        if not ips:
            return False, '車子目前沒有網路 IP，無法設定 ROS_MASTER_URI'
        os.makedirs(LOG_DIR, exist_ok=True)
        _prune_logs()
        log_path = os.path.join(LOG_DIR, time.strftime('%Y%m%d_%H%M%S') + '.log')
        run.update(model=model, ip=ips[0], log=log_path, exit_code=None, t0=time.time(),
                   state='running', msg=f'以 {ips[0]} 啟動')
        logf = open(log_path, 'w', buffering=1)
        logf.write(f'# ccpp launcher: model={model} ROS_MASTER_URI=http://{ips[0]}:11311\n')
        run['proc'] = subprocess.Popen(
            ['bash', '-c', f'{ROS_SETUP} && exec roslaunch turtlebot3_ccpp start.launch model:={model}'],
            stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            env=ros_env(ips[0]), preexec_fn=os.setsid)
        logf.close()            # 子行程已繼承檔案描述子
    threading.Thread(target=_watch, args=(run['proc'],), daemon=True).start()
    return True, '已送出啟動，硬體與 SLAM 約需 20～40 秒才會就緒'


def _watch(proc):
    code = proc.wait()
    with lock:
        if run['proc'] is proc:
            run['exit_code'] = code
            if run['state'] != 'stopping':
                run['msg'] = f'roslaunch 自行結束（代碼 {code}），請看日誌'
            run['state'] = 'exited' if run['state'] != 'stopping' else 'idle'
            run['proc'] = None


def _signal_all(sig):
    """對本控制台開的行程群組與外部 start.launch 送訊號，並收掉殘留的 SLAM roslaunch。"""
    proc = run['proc']
    if proc is not None and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except ProcessLookupError:
            pass
    for pid in external_pids():
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass


def _alive():
    proc = run['proc']
    return (proc is not None and proc.poll() is None) or bool(external_pids())


def _stop_worker():
    # SIGINT = 和終端機按 Ctrl+C 一樣，讓 roslaunch／map_server 正常收尾（含停車、關 SLAM）
    for sig, wait in ((signal.SIGINT, STOP_WAIT), (signal.SIGTERM, 5.0), (signal.SIGKILL, 3.0)):
        _signal_all(sig)
        t_end = time.time() + wait
        while time.time() < t_end and _alive():
            time.sleep(0.3)
        if not _alive():
            break
    # map_server 以獨立行程群組管理 SLAM，正常會隨它收掉；保險起見再清一次
    subprocess.run(['pkill', '-INT', '-f', 'turtlebot3_slam.launch'], capture_output=True)
    with lock:
        if run['proc'] is not None and run['proc'].poll() is not None:
            run['proc'] = None
        run['state'] = 'idle' if not _alive() else 'running'
        run['msg'] = '已停止' if not _alive() else '停止失敗，仍有行程存活'


def stop():
    with lock:
        if not _alive():
            run['state'] = 'idle'
            return False, '目前沒有在執行'
        if run['state'] == 'stopping':
            return False, '正在停止中'
        run['state'], run['msg'] = 'stopping', '停止中…'
    threading.Thread(target=_stop_worker, daemon=True).start()
    return True, '已送出停止'


# ════════════════════════════════════════════════════════
#  背景輪詢（慢的東西都在這裡做，狀態 API 只讀快取）
# ════════════════════════════════════════════════════════
def _coverage_summary():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{MAP_PORT}/coverage/status', timeout=1.5) as r:
            st = json.load(r)
    except Exception:
        return None
    keep = ('state', 'done', 'total', 'msg')
    out = {k: st.get(k) for k in keep}
    m = st.get('metrics') or {}
    out.update({k: m.get(k) for k in ('task', 'completion', 'actual_cov', 'plan_cov',
                                      'skipped', 'exec_s', 'actual_len', 'plan_len')})
    return out


def _poller():
    while True:
        try:
            alive = _alive()
            web = alive and port_open(MAP_PORT)
            now = time.time()
            upd = {'web_ready': web, 'coverage': _coverage_summary() if web else None}
            if not alive:
                upd.update(nodes=[])
            elif now - cache['t_nodes'] > 6:
                out = ros_cmd('rosnode list', timeout=8)
                upd.update(nodes=out.split() if out else [], t_nodes=now)
            with lock:
                cache.update(upd)
        except Exception as e:      # 輪詢絕不能死
            print('[poller]', e, flush=True)
        time.sleep(2.0)


def _battery_poller():
    """電池電壓獨立一條執行緒：rostopic 在樹莓派上光啟動就要 4～7 秒，不能卡住主輪詢。"""
    while True:
        if not _alive():
            with lock:
                cache['battery'] = None
            time.sleep(3.0)
            continue
        out = ros_cmd('rostopic echo -n 1 /battery_state/voltage', timeout=20)
        try:
            volt = round(float(out.split()[0]), 2) if out else None
        except (ValueError, IndexError):
            volt = None
        with lock:
            cache['battery'] = volt if volt is not None or not _alive() else cache['battery']
        time.sleep(20.0)


# ════════════════════════════════════════════════════════
#  路由
# ════════════════════════════════════════════════════════
@app.route('/')
def index():
    resp = send_file(PAGE)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/api/status')
def api_status():
    ext = external_pids()
    with lock:
        proc = run['proc']
        state = run['state']
        if state in ('idle', 'exited') and ext:
            state = 'external'
        out = {
            'state':     state,
            'pid':       proc.pid if proc is not None and proc.poll() is None else (ext[0] if ext else None),
            'model':     run['model'],
            'ros_ip':    run['ip'],
            'uptime_s':  int(time.time() - run['t0']) if run['t0'] and state == 'running' else None,
            'exit_code': run['exit_code'],
            'msg':       run['msg'],
            'web_ready': cache['web_ready'],
            'map_port':  MAP_PORT,
            'nodes':     cache['nodes'],
            'battery':   cache['battery'],
            'coverage':  cache['coverage'],
            'models':    MODELS,
        }
    out['system'] = system_info()
    out['launcher_uptime_s'] = int(time.time() - T_BOOT)
    return jsonify(out)


@app.route('/api/start', methods=['POST'])
def api_start():
    model = (request.get_json(silent=True) or {}).get('model', 'burger')
    if model not in MODELS:
        return jsonify(ok=False, msg=f'不支援的型號：{model}'), 400
    ok, msg = start(model)
    return jsonify(ok=ok, msg=msg), (200 if ok else 409)


@app.route('/api/stop', methods=['POST'])
def api_stop():
    ok, msg = stop()
    return jsonify(ok=ok, msg=msg), (200 if ok else 409)


@app.route('/api/log')
def api_log():
    n = min(int(request.args.get('lines', 200)), 1000)
    path = run['log']
    if not path:
        try:
            logs = sorted(f for f in os.listdir(LOG_DIR) if f.endswith('.log'))
            path = os.path.join(LOG_DIR, logs[-1]) if logs else None
        except OSError:
            path = None
    if not path or not os.path.exists(path):
        return jsonify(file=None, lines=[])
    with open(path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - 128 * 1024))
        text = f.read().decode('utf-8', 'replace')
    return jsonify(file=os.path.basename(path), lines=list(deque(text.splitlines(), maxlen=n)))


@app.route('/api/power', methods=['POST'])
def api_power():
    action = (request.get_json(silent=True) or {}).get('action')
    if action not in ('shutdown', 'reboot'):
        return jsonify(ok=False, msg='action 只能是 shutdown 或 reboot'), 400

    def worker():
        if _alive():
            _stop_worker()      # 先讓車子停下、roslaunch 收尾
        subprocess.run(['sudo', '-n', 'systemctl', 'poweroff' if action == 'shutdown' else 'reboot'])
    threading.Thread(target=worker, daemon=True).start()
    word = '關機' if action == 'shutdown' else '重新開機'
    return jsonify(ok=True, msg=f'正在停止專案並{word}，綠燈不再閃爍後再關電源')


# ── 轉接 map_server（8080）：手機只開 8000 一個網址，同源呼叫，不必處理跨來源 ──
PROXY_GET  = {'map.png', 'map_margin.png', 'map_eroded.png', 'map_dilated.png',
              'robot_state', 'scan', 'coverage/status', 'coverage/runs.csv'}
PROXY_POST = {'coverage/start', 'coverage/stop', 'coverage/resume', 'teleop', 'slam/restart'}


@app.route('/<path:p>', methods=['GET', 'POST'])
def proxy(p):
    if p not in (PROXY_POST if request.method == 'POST' else PROXY_GET):
        abort(404)
    url = f'http://127.0.0.1:{MAP_PORT}/{p}'
    if request.query_string:
        url += '?' + request.query_string.decode()
    data = request.get_data() if request.method == 'POST' else None
    req = urllib.request.Request(url, data=data, method=request.method,
                                 headers={'Content-Type': request.content_type or 'application/json'})
    # 開始覆蓋要規劃路徑、重啟 SLAM 要等舊的收掉，給長一點
    timeout = 40 if p in ('coverage/start', 'slam/restart') else 5
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body, status, headers = r.read(), r.status, r.headers
    except urllib.error.HTTPError as e:
        body, status, headers = e.read(), e.code, e.headers
    except Exception:
        return jsonify(ok=False, msg='系統未啟動，或地圖服務還沒就緒'), 502
    resp = Response(body, status=status)
    resp.headers['Content-Type'] = headers.get('Content-Type', 'application/octet-stream')
    if headers.get('Content-Disposition'):
        resp.headers['Content-Disposition'] = headers['Content-Disposition']
    resp.headers['Cache-Control'] = 'no-store'
    return resp


def main():
    threading.Thread(target=_poller, daemon=True).start()
    threading.Thread(target=_battery_poller, daemon=True).start()
    print(f'[launcher] http://{(host_ips() or ["127.0.0.1"])[0]}:{PORT}', flush=True)
    app.run(host='0.0.0.0', port=PORT, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
