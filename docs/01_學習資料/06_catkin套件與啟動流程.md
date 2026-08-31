# 第 06 章　catkin 套件與啟動流程

> **本章目標**：把「一行 `roslaunch` 之後到底發生了什麼」講清楚，
> 並完整拆解本專案最特別的一個設計 —— **SLAM 生命週期由 `map_server` 自管**。

---

## 6.1 ① 問題：怎麼把一堆東西一次拉起來

系統要跑起來，需要同時啟動：

```
   ① 硬體驅動      turtlebot3_bringup
   ② SLAM          gmapping
   ③ 導航          move_base（還要載入 5 個 yaml 參數檔）
   ④ 我們的節點    map_server.py（還要設 3 個參數）
   ⑤ 環境變數      TURTLEBOT3_MODEL=burger（少了它驅動會抓錯型號）
```

### ② 直覺做法：開五個終端機

```bash
# 終端機 1
export TURTLEBOT3_MODEL=burger
roslaunch turtlebot3_bringup turtlebot3_robot.launch
# 終端機 2
roslaunch turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping
# 終端機 3
roslaunch turtlebot3_navigation move_base.launch
# 終端機 4
python3 scripts/map_server.py _port:=8080
```

### ③ 撞牆

1. **順序有依賴**：`move_base` 啟動時如果 TF 樹還沒建好，它會一直印警告
2. **環境變數要每個終端機都設**，漏一個就抓錯型號
3. **關機要按四次 Ctrl+C**，而且順序錯了會留下殭屍節點
4. **參數打錯不會有人告訴你**，只會出現莫名其妙的行為
5. **無法重現**：三個月後你自己都忘了當初怎麼開的

---

## 6.2 ④ catkin 套件：程式碼要住在哪

在寫 launch 檔之前，先要有「套件」。ROS 的所有東西都必須在套件裡。

### 工作空間的結構

```
   ~/catkin_ws/                     ← 工作空間（workspace）
   ├── src/                         ← 原始碼都放這
   │   └── turtlebot3_ccpp/         ← 我們的套件
   │       ├── package.xml          ← 必備
   │       ├── CMakeLists.txt       ← 必備
   │       ├── launch/
   │       ├── scripts/
   │       ├── web/
   │       └── test/
   ├── build/                       ← catkin_make 產生（不進 git）
   └── devel/                       ← 編譯結果（不進 git）
       └── setup.bash               ← ★ source 它才找得到套件
```

```bash
cd ~/catkin_ws
catkin_make                # 建置
source devel/setup.bash    # ★ 忘了這行，roslaunch 會說「找不到套件」
```

> ⚠ **最常見的新手問題**：`roslaunch turtlebot3_ccpp start.launch` 說找不到套件。
> 99% 是忘了 `source devel/setup.bash`。
> 解法是把它加進 `~/.bashrc`，開新終端機自動生效。

### `package.xml`：宣告「我是誰、我需要誰」

```xml
<?xml version="1.0"?>
<package format="2">
    <name>turtlebot3_ccpp</name>          <!-- ★ 套件名，全域唯一 -->
    <version>0.1.0</version>
    <description>TurtleBot3 Flask 地圖即時監控</description>
    <maintainer email="...">MXHHulk</maintainer>
    <license>MIT</license>

    <buildtool_depend>catkin</buildtool_depend>   <!-- 用什麼工具建置 -->

    <exec_depend>rospy</exec_depend>              <!-- 執行時需要 -->
    <exec_depend>nav_msgs</exec_depend>

    <!--
        pip3 install flask Pillow
        numpy 已隨 ROS 安裝
    -->
</package>
```

三種依賴的差別：

| 標籤 | 什麼時候需要 | 例子 |
|---|---|---|
| `buildtool_depend` | 建置工具本身 | `catkin` |
| `build_depend` | 編譯時需要（C++ 才用得到） | 本專案是純 Python，沒有 |
| `exec_depend` | **執行時需要** | `rospy`、`nav_msgs` |

> ⚠ **注意最後那段註解**：`flask` 和 `Pillow` 要用 `pip3` 裝，
> 因為它們是**純 Python 套件，不在 ROS 的依賴系統裡**。
> `package.xml` 管不到它們，所以只能用註解提醒。
>
> 這是 ROS 1 的一個現實問題：ROS 的依賴管理（rosdep）和 Python 的（pip）是兩套系統。
> 把安裝指令寫在 `package.xml` 的註解裡，是很務實的做法 —— 至少下一個人打開檔案就看得到。

### `CMakeLists.txt`：怎麼建置、什麼要安裝

```cmake
cmake_minimum_required(VERSION 3.0.2)
project(turtlebot3_ccpp)

find_package(catkin REQUIRED COMPONENTS rospy nav_msgs std_msgs)

catkin_package()

catkin_install_python(PROGRAMS          # ★ Python 腳本的安裝
    scripts/coverage_planner.py
    scripts/map_server.py
    DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch/ DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch)
install(DIRECTORY web/    DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/web)
```

★ **`catkin_install_python` 做兩件事**：
1. 把腳本複製到安裝目錄
2. **自動加上執行權限，並修正 shebang**（`#!/usr/bin/env python3`）

這就是為什麼可以用 `rosrun turtlebot3_ccpp map_server.py` 直接執行。

> 💡 **注意 `test/` 不在安裝清單裡**。這是刻意的 ——
> `test/` 底下是量測工具，不屬於執行路徑，用 `python3 test/xxx.py` 直接跑就好。
> 這個「不安裝」本身就是一種文件：**它在說「這些東西不是產品的一部分」**。

### 為什麼 `web/` 要安裝？

因為 `map_server.py` 要讀它：

```python
# scripts/map_server.py:370-373
@app.route('/')
def index():
    p = os.path.join(PKG, 'web', 'index.html')
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ('找不到 index.html', 404)
```

```python
# scripts/map_server.py:39-42
try:
    PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')
except rospkg.ResourceNotFound:
    PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
```

★ **這個 try/except 讓程式有兩種運作模式**：
- **裝好的套件**：`RosPack` 找得到，用安裝路徑
- **直接從原始碼跑**（`python3 scripts/map_server.py`）：`RosPack` 找不到，
  退回「這個檔案的上上層目錄」

第二種模式對開發很重要 —— 改一行前端不用重新 `catkin_make`。

---

## 6.3 ★ `start.launch` 逐段拆解

整份檔案只有 75 行，但每一段都有理由。

### 第 0 段：可覆寫的參數（第 5~9 行）

```xml
<arg name="model"  default="burger" />
<arg name="port"   default="8080"   />

<!-- 設定 TB3 型號環境變數 -->
<env name="TURTLEBOT3_MODEL" value="$(arg model)" />
```

```bash
roslaunch turtlebot3_ccpp start.launch                      # 預設
roslaunch turtlebot3_ccpp start.launch model:=waffle        # 換型號
roslaunch turtlebot3_ccpp start.launch port:=9000           # 換埠號
```

★ **`<env>` 解決了 6.1 撞牆點 ②**：型號環境變數由 launch 檔統一設定，
不會有「某個終端機忘了 export」的問題。

`$(arg model)` 後面會用在三個地方，全部保證一致：
- 環境變數 `TURTLEBOT3_MODEL`
- `costmap_common_params_$(arg model).yaml`
- `dwa_local_planner_params_$(arg model).yaml`

### 第 1 段：硬體驅動（第 11~12 行）

```xml
<!-- 1. 硬體驅動 -->
<include file="$(find turtlebot3_bringup)/launch/turtlebot3_robot.launch" />
```

啟動後會有：發布 `/scan`、發布 `/odom`、訂閱 `/cmd_vel`、
發布 `odom → base_footprint → base_link → base_scan` 的 TF。

### 第 2 段：SLAM（第 14~25 行）★ 只有註解，沒有程式

```xml
<!-- 2. SLAM 建圖（gmapping 同時發布 /map 與 map→odom TF，供 move_base 定位用）

     注意：SLAM 不在這裡啟動，改由 map_server 以子行程管理（見下方第 4 節）。
     這樣網頁上的「重啟 SLAM」才能收掉舊的 gmapping、重新開一個乾淨的地圖，
     不必整包 roslaunch 重跑。若要改回由本檔啟動，把下面 map_server 的
     manage_slam 設為 false，並取消這段註解：

     <include file="$(find turtlebot3_slam)/launch/turtlebot3_slam.launch">
         <arg name="slam_methods" value="gmapping" />
         <arg name="open_rviz"    value="false"    />
     </include>
-->
```

★ **這是全專案最值得學的一段註解。** 它做到三件事：

1. **保留了原本的程式碼**（註解掉，不是刪掉）—— 要退回去只要取消註解
2. **說明為什麼不用它**（要支援網頁重新建圖）
3. **說明怎麼退回去**（把 `manage_slam` 設成 `false`）

> 💡 一個「這裡刻意什麼都沒做」的位置，如果不寫註解，
> 下一個人（包括三個月後的你）看到 launch 檔裡沒有 SLAM，
> 第一反應一定是「啊，忘了寫」，然後就加回去了 —— 然後重啟功能就壞了。
>
> **註解要解釋的是「為什麼」，特別是「為什麼沒有做某件事」。**

### 第 3 段：move_base（第 27~55 行）

```xml
<node pkg="move_base" type="move_base" name="move_base"
      respawn="false" output="screen">
    <param name="base_local_planner" value="dwa_local_planner/DWAPlannerROS" />

    <!-- 障礙物偵測共用參數（分別套用到全域與局部 costmap）-->
    <rosparam file="$(find turtlebot3_navigation)/param/costmap_common_params_$(arg model).yaml"
              command="load" ns="global_costmap" />
    <rosparam file="$(find turtlebot3_navigation)/param/costmap_common_params_$(arg model).yaml"
              command="load" ns="local_costmap" />
    ...
</node>
```

五個 yaml 檔的分工：

| 檔案 | 管什麼 | 為什麼要載 |
|---|---|---|
| `costmap_common_params_<model>.yaml` | 機器人尺寸、感測器來源、膨脹半徑 | 全域和局部都要，所以載兩次 |
| `global_costmap_params.yaml` | 全域地圖設定（`static_map: true` → 訂閱 `/map`） | 全域規劃用 |
| `local_costmap_params.yaml` | 局部視窗大小、更新頻率 | DWA 用 |
| `move_base_params.yaml` | 到達容差、恢復行為、規劃頻率 | 協調層 |
| `dwa_local_planner_params_<model>.yaml` | 速度、加速度上限 | DWA 用 |

★ **注意 `ns="global_costmap"` / `ns="local_costmap"`**：
同一個 yaml 載入兩次，但放進不同的**命名空間**。
這樣 `robot_radius` 這個參數會同時出現在 `/move_base/global_costmap/robot_radius`
和 `/move_base/local_costmap/robot_radius`，兩張 costmap 各取各的。

> 💡 **設計決策：全部沿用 `turtlebot3_navigation` 的官方參數，一個都不自己調。**
> 理由：這些參數是原廠針對 Burger/Waffle 調過的，
> 自己亂調很容易讓避障變差，而且調參不是本專案的貢獻。
> `respawn="false"` 也是刻意的 —— `move_base` 掛掉就是掛掉，
> 自動重啟只會掩蓋問題，讓你以為系統正常。

### 第 4 段：我們的節點（第 57~64 行）

```xml
<!-- 4. Flask 地圖網頁伺服器 + 覆蓋路徑執行 + SLAM 生命週期管理
     manage_slam=true 時，本節點會自己啟動 turtlebot3_slam.launch，
     並提供 /slam/restart 讓網頁能重新建圖。 -->
<node pkg="turtlebot3_ccpp" type="map_server.py" name="map_server" output="screen">
    <param name="port"         value="$(arg port)" />
    <param name="manage_slam"  value="true"        />
    <param name="slam_methods" value="gmapping"    />
</node>
```

`output="screen"` 讓 `rospy.loginfo` 和 `print` 的輸出顯示在終端機。
沒有這個屬性的話，輸出會被導到 log 檔裡，你會以為節點沒在動。

### 第 5 段：測試工具的說明（第 66~73 行）

```xml
<!-- 註：test/ 底下皆為測量／檢視工具，非專案執行路徑，不掛在此 launch。
     需要時單獨執行：
       python3 test/map_recorder.py            # 錄製 /map 每張地圖為 PNG
       python3 test/boustrophedon.py           # 發布 /coverage_path 供 RViz 檢視
       ... -->
```

同樣是「說明為什麼沒有」的註解。

---

## 6.4 ★ SLAM 生命週期的完整實作

第 05 章講了為什麼要自管，這裡看完整流程。

### 啟動時（節點初始化）

```python
# scripts/map_server.py:612-616
if slam_cfg['manage']:
    rospy.on_shutdown(slam_kill)     # ★ 註冊「我死之前先收掉 SLAM」
    slam_launch()
else:
    rospy.loginfo('[slam] manage_slam=false，SLAM 由外部負責，/slam/restart 停用')
```

★ **`rospy.on_shutdown(slam_kill)` 一定要有**。
沒有它的話，你 Ctrl+C 停掉 `map_server`，gmapping 會變成孤兒繼續跑。

### 重啟時（`/slam/restart`）

```python
# scripts/map_server.py:551-587
@app.route('/slam/restart', methods=['POST'])
def slam_restart():
    """重啟 SLAM 重新建圖：停覆蓋 → 停車 → 收掉 SLAM → 清空狀態 → 重新啟動。"""
    global map_png, map_eroded, map_dilated, map_margin

    # ① 這個功能有沒有開
    if not slam_cfg['manage']:
        return jsonify({'ok': False,
                        'msg': 'SLAM 不由本節點管理（manage_slam=false），請手動重啟'}), 400

    # ② 先停任務
    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status['state'] = 'stopped'
    # ③ 再停車
    teleop_halt()

    with slam_lock:
        slam_kill()                    # ④ 收掉舊的 SLAM

        # ⑤ 清空所有和舊地圖相關的狀態
        with map_lock:
            map_png = map_eroded = map_dilated = map_margin = None
            map_meta.clear()
            map_data.clear()
        with robot_lock:
            robot_path.clear()
            robot_pos.update(x=None, y=None)
        with cov_lock:
            cov_path[:]  = []
            cov_cells[:] = []
            cov_info.clear()
            cov_status.update(state='idle', done=0, total=0, msg='')

        try:
            slam_launch()              # ⑥ 開新的
        except Exception as e:
            rospy.logerr('[slam] 重啟失敗：%s', e)
            return jsonify({'ok': False, 'msg': f'重啟失敗：{e}'}), 500

    return jsonify({'ok': True, 'msg': 'SLAM 已重啟，請等待新地圖'})
```

**六個步驟的順序全部有意義：**

```
   ① 檢查功能開關     ← 不開就早退，不要做一半
   ② 停任務           ← 讓 run_coverage 執行緒自己收尾
   ③ 停車             ← 交出 /cmd_vel 前先歸零，避免機器人保持速度
   ④ 收掉 SLAM        ← 這時 /map 停止發布
   ⑤ 清空狀態         ← ★ 順序關鍵，見下
   ⑥ 開新的 SLAM
```

★ **為什麼「清空狀態」一定要在「收掉 SLAM」之後？**

如果順序反過來（先清空再 kill），會有一個時間窗口：
清空之後、kill 之前，舊的 gmapping 還在發 `/map`，
`map_callback` 會立刻把舊地圖再寫回去 —— **清了等於沒清**。

先 kill 就沒有這個問題：`/map` 已經停了，清空之後不會有人再寫。

★ **為什麼整段包在 `with slam_lock` 裡？**

防止兩個並發的 `/slam/restart` 請求交錯執行
（使用者連按兩次按鈕、或網路重送）。
沒有這把鎖的話，可能出現「A 剛 kill 完，B 也 kill（kill 到 None）→
A 啟動 → B 啟動」= 兩個 gmapping。

### 前端配合

```javascript
// web/index.html:415-429
$('btn-slam').onclick = async () => {
    if (!confirm('重啟 SLAM 會清空目前的地圖、軌跡與規劃結果，確定要重新建圖嗎？')) return;
    $('btn-slam').disabled = true;
    try {
        const d = await (await fetch('/slam/restart', { method: 'POST' })).json();
        if (!d.ok) alert('重啟失敗：' + d.msg);
        else {
            for (const k in imgCache) delete imgCache[k];   // ★ 清掉圖片快取
            canvas.style.display = 'none';
            $('waiting').style.display = '';
            $('waiting').textContent = 'SLAM 重啟中，等待新地圖…';
        }
    } catch (e) { alert('連線失敗：' + e); }
    setTimeout(() => { $('btn-slam').disabled = false; }, 3000);
};
```

三個細節：

1. **`confirm()` 二次確認** —— 這是不可逆的破壞性操作
2. **`delete imgCache[k]`** —— 不清快取的話，畫面會繼續顯示舊地圖直到新圖載入
3. **`setTimeout(..., 3000)`** —— 按鈕鎖 3 秒，防止連點造成上面說的競態

---

## 6.5 ⑥ 完整啟動流程與操作

### 前置安裝

```bash
sudo apt install ros-noetic-turtlebot3 ros-noetic-turtlebot3-msgs \
                 ros-noetic-gmapping ros-noetic-dwa-local-planner
pip3 install flask Pillow
```

### 建置

```bash
cd ~/catkin_ws && catkin_make && source devel/setup.bash
```

### 啟動（在機器人上，或用 SSH 連過去）

```bash
roslaunch turtlebot3_ccpp start.launch
# 換型號： roslaunch turtlebot3_ccpp start.launch model:=waffle
# 換埠號： roslaunch turtlebot3_ccpp start.launch port:=9000
```

終端機會印出網址：

```
[INFO] 地圖伺服器 → http://192.168.x.x:8080
```

### 操作流程

```
   ① 手機/電腦連同一個 Wi-Fi，瀏覽器開上面那個網址
   ② 用網頁上的方向鍵（或鍵盤 WASD）把機器人推著繞一圈，把房間建完整
        ★ 這步很重要：地圖不完整 → 未知格不會被覆蓋（第 19 章）
   ③ 確認「安全邊距」圖層看起來合理（沒有把通道封死）
   ④ 按「▶ 開始執行」
   ⑤ 看進度條與 cell 上色；要停就按「■ 結束」
   ⑥ 換場地後按「⟳ 重啟 SLAM 重新建圖」
```

### 單獨看某張地圖（除錯用）

```
   http://<ip>:8080/map.png           原始
   http://<ip>:8080/map_margin.png    ★ 規劃真正用的膨脹
   http://<ip>:8080/coverage/status   JSON 狀態
```

---

## 6.6 ⚠ 啟動時的常見問題

| 症狀 | 原因 | 解法 |
|---|---|---|
| `roslaunch` 說找不到套件 | 忘了 `source devel/setup.bash` | 加進 `~/.bashrc` |
| 網頁打得開但一直「等待地圖資料」 | SLAM 沒起來或還沒收到雷射 | 看終端機有沒有 gmapping 的輸出；`rostopic hz /map` |
| 按開始說「地圖尚未就緒」 | `/map` 還沒收到過 | 等一下，或先手動推著走一段 |
| 按開始說「move_base 未啟動」 | `move_base` 掛了或還在初始化 | `rosnode list` 確認；等 5 秒再試 |
| 按開始說「無可走路徑」 | 地圖太小或安全邊距把空間封死 | 看 `/map_margin.png`，或縮小 `MARGIN` |
| 機器人不動但顯示執行中 | `move_base` 收不到 TF | `rosrun tf view_frames` 看 `map→odom` 在不在 |
| 重啟 SLAM 後地圖閃爍 | 有孤兒 gmapping | `rosnode list \| grep gmapping`，`rosnode kill` 掉多的 |

---

## 6.7 本章重點回顧

1. **catkin 套件 = 資料夾 + `package.xml` + `CMakeLists.txt`**；
   ⚠ 忘記 `source devel/setup.bash` 是最常見的新手問題。
2. **`package.xml` 管不到 pip 套件**（flask、Pillow），本專案用註解提醒安裝指令。
3. **`catkin_install_python` 會自動加執行權限並修正 shebang**；
   `test/` 刻意不安裝，本身就是「這不是產品的一部分」的宣告。
4. **`PKG` 的 try/except 讓程式同時支援「裝好的套件」和「直接跑原始碼」兩種模式。**
5. ★ **launch 檔第 2 段只有註解沒有程式**，並且說明了為什麼、怎麼退回去 ——
   「為什麼沒有做某件事」比「做了什麼」更需要註解。
6. ★ **`/slam/restart` 的六步順序都有理由**，其中最關鍵的是
   **「先 kill SLAM，再清空狀態」**（反過來會被舊的 `/map` 立刻寫回去），
   以及**整段包在 `slam_lock` 裡**防止並發重啟造成雙 gmapping。

---

## 6.8 自我檢核題

**Q1. `start.launch` 第 2 段（SLAM）整段被註解掉。如果有人把註解拿掉會發生什麼事？**

<details>
<summary>參考答案</summary>

**會有兩個 gmapping 同時跑。**

因為 `map_server` 的 `manage_slam` 參數還是 `true`（第 62 行），
它啟動時仍然會用 `subprocess` 開一個自己的 `turtlebot3_slam.launch`。

兩個 gmapping 同時訂閱 `/scan`、同時發布 `/map` 和 `map → odom` TF，症狀是：

- **地圖在兩張之間瘋狂閃爍**（兩個 SLAM 的粒子濾波結果不同）
- **TF 樹有兩個 `map → odom` 的發布者** → `move_base` 定位混亂、機器人亂走
- ⚠ 而且**不會有任何錯誤訊息**，ROS 完全允許這件事（第 01 章 1.10 的多發布者問題）

正確的做法是：拿掉註解的**同時**，把 `manage_slam` 改成 `false`
（註解裡就是這樣寫的）。此時 `/slam/restart` 會回 HTTP 400 並說明原因
（`map_server.py:556-558`），不會默默失效。
</details>

**Q2. `/slam/restart` 為什麼要「先 kill SLAM，再清空狀態」？順序反過來會怎樣？**

<details>
<summary>參考答案</summary>

反過來（先清空、再 kill）會有一個**時間窗口**：

```
   時刻 T1：清空 map_png / map_meta / map_data
   時刻 T2：舊的 gmapping 還活著，發了一則 /map
   時刻 T3：map_callback 被觸發，把舊地圖完整寫回去   ← 清了等於沒清
   時刻 T4：才 kill 掉 SLAM
```

結果就是「按了重啟，畫面上還是舊地圖」，而且是**間歇性**的
（要看 `/map` 剛好在那個窗口內有沒有發布），極難重現、極難除錯。

先 kill 就沒有這個問題 —— `/map` 已經停止發布，
清空之後不會有任何人再寫進去，直到新的 gmapping 產出第一張圖。

**通用原則：清理共享狀態之前，先把「會寫入它的來源」關掉。**
</details>

**Q3. 為什麼 `move_base` 的 `respawn` 設成 `false`？設成 `true` 有什麼好處和壞處？**

<details>
<summary>參考答案</summary>

`respawn="true"` 會讓 `roslaunch` 在節點死掉時自動重啟它。

**好處**：偶發性崩潰能自動恢復，系統看起來比較穩。

**壞處（本專案選 false 的理由）**：

1. **掩蓋問題**：`move_base` 崩潰通常代表參數有問題、地圖有問題、或 TF 有問題。
   自動重啟會讓你以為系統正常，實際上它每 30 秒死一次。
2. **重啟期間狀態不一致**：`run_coverage` 執行緒的 `SimpleActionClient` 連的是舊的 server，
   重啟後 action 連線會斷，當前目標的結果永遠等不到 ——
   雖然有 `wait_for_result(0.5)` 的迴圈保護不會死鎖，但那個路點會被判定失敗跳過。
3. **對專題不利**：口試時如果被問「你怎麼知道 `move_base` 沒問題」，
   `respawn=false` 才能回答「它從頭到尾沒死過」。

**判準**：`respawn` 適合「掛掉也無所謂、重啟就好」的節點（例如純顯示工具）。
對於在關鍵路徑上、而且崩潰代表有 bug 的節點，讓它死掉並被發現才是對的。
</details>

**Q4. `PKG` 那段 try/except（`map_server.py:39-42`）為什麼要寫？直接寫死路徑不行嗎？**

<details>
<summary>參考答案</summary>

```python
try:
    PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')
except rospkg.ResourceNotFound:
    PKG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
```

它讓程式支援**兩種運作模式**：

1. **當作已安裝的套件跑**（`rosrun` / `roslaunch`）：
   `RosPack` 回傳安裝路徑，`web/index.html` 從那裡讀。
2. **直接跑原始碼**（`python3 scripts/map_server.py`）：
   如果工作空間沒建置或沒 source，`RosPack` 會拋 `ResourceNotFound`，
   這時退回「本檔案的上上層目錄」，也就是專案根目錄。

**寫死路徑不行**，因為安裝路徑（`~/catkin_ws/install/share/turtlebot3_ccpp/`）
和開發路徑（`~/catkin_ws/src/turtlebot3_ccpp/`）不一樣，
而且換一台電腦就變了。

**第二種模式對開發特別重要**：改一行 `web/index.html` 之後，
不用 `catkin_make`、不用重新 source，直接重跑就看得到效果。
沒有這個 fallback，前端開發的迭代速度會慢好幾倍。
</details>

---

**← 上一章** [第 05 章　模組介面設計](05_模組介面設計.md)
**下一章 →** [第 07 章　地圖資料處理](07_地圖資料處理.md)
