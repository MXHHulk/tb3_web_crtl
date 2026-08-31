# 第 01 章　ROS 基礎速成

> **本章目標**：讓完全沒碰過 ROS 的人，看得懂本專案每一行 `rospy.*` 的程式碼。
> 讀完後你應該能回答：節點是什麼、話題是什麼、`rospy.Subscriber(...)` 那一行到底做了什麼事。
>
> 已經會 ROS 的人可以只看 **1.9 本專案的節點與話題全表**，然後跳到第 02 章。

---

## 1.1 先講問題：機器人軟體為什麼難寫

假設你要從零寫一台會自己走路的機器人，你至少需要同時做這些事：

```
① 每秒 5 次讀光達，拿到 360 個距離值
② 每秒 30 次讀輪子編碼器，推算走了多遠
③ 持續把光達資料拼成地圖
④ 持續算「我在地圖的哪裡」
⑤ 算一條路徑
⑥ 每秒 10 次輸出馬達速度
⑦ 開一個網頁伺服器讓人看
```

### 直覺做法：寫成一支大程式

```python
while True:
    scan = read_lidar()
    odom = read_encoder()
    update_map(scan, odom)
    pose = localize(scan, map)
    path = plan(map, pose)
    v, w = follow(path, pose)
    write_motor(v, w)
```

### 這樣寫會撞到四面牆

| 問題 | 具體症狀 |
|---|---|
| **頻率不一致** | 光達 5 Hz、編碼器 30 Hz、馬達要 10 Hz。硬塞進同一個迴圈，一定有人被拖慢 |
| **一個爆全部爆** | 建圖算太久導致馬達沒收到新指令，機器人直接撞牆 |
| **無法分工** | 三個人要同時改這支檔案，衝突到死 |
| **無法重用** | 別人寫好的 SLAM 想拿來用？他的程式不是這個迴圈的形狀，得整個改寫 |

---

## 1.2 ROS 的解法：拆成很多小程式，用「廣播」溝通

**ROS（Robot Operating System）不是作業系統**，它是一套「讓很多支小程式互相傳資料」的框架 + 一大堆現成的機器人套件。

核心觀念只有三個字：**節點、話題、訊息**。

### 節點（Node）＝ 一支獨立執行的程式

上面那七件事，在 ROS 裡就是七個獨立的行程（process），各跑各的迴圈、各用各的頻率。
一個當掉不會拖垮其他人。

### 話題（Topic）＝ 一個具名的廣播頻道

節點之間**不直接呼叫對方**，而是往「話題」丟資料，或從「話題」收資料。
話題就是一個字串名稱，習慣用斜線開頭，例如 `/scan`、`/odom`、`/map`、`/cmd_vel`。

### 訊息（Message）＝ 話題上流動的資料格式

每個話題只能流一種固定格式的資料。例如：

- `/scan` 上流的是 `sensor_msgs/LaserScan`（含 360 個距離值）
- `/cmd_vel` 上流的是 `geometry_msgs/Twist`（含線速度與角速度）

### 發布者 / 訂閱者（Publisher / Subscriber）

- **Publisher（發布者）**：往話題丟資料的節點
- **Subscriber（訂閱者）**：從話題收資料的節點

```
   ┌──────────┐                                  ┌──────────┐
   │ 光達驅動 │──publish──→ /scan ──subscribe──→│ gmapping │
   │  節點    │                  │               │  節點    │
   └──────────┘                  │               └──────────┘
                                 │
                                 └──subscribe──→┌────────────┐
                                                │ map_server │
                                                └────────────┘
```

**關鍵性質**（這是 ROS 最重要的設計）：

1. **一對多**：一個 publisher 的資料，所有 subscriber 都收得到，發布者根本不知道有誰在聽
2. **多對一**：多個 publisher 可以往同一個話題丟（⚠ 這會出事，見 1.10）
3. **完全解耦**：發布者不需要知道訂閱者存在，反之亦然。
   任何一邊隨時可以關掉、重啟、換成別的實作，另一邊完全不受影響

> 💡 **這個「解耦」性質是本專案很多設計的根源。**
> 例如第 06 章會講到，網頁上按「重啟 SLAM」可以把整個 gmapping 節點殺掉重開，
> 而 `map_server` 完全不用改動 —— 它只是暫時收不到 `/map` 而已。

---

## 1.3 訂閱：`rospy.Subscriber` 逐字拆解

打開 `scripts/map_server.py:608`：

```python
rospy.Subscriber('/map', OccupancyGrid, map_callback, queue_size=1)
#                 └─①    └─②           └─③           └─④
```

| | 意思 |
|---|---|
| ① `'/map'` | 要訂閱的話題名稱 |
| ② `OccupancyGrid` | 這個話題的訊息型別（要先 `from nav_msgs.msg import OccupancyGrid`） |
| ③ `map_callback` | **回呼函式**：每次收到一則訊息，ROS 就自動呼叫它一次，把訊息當參數傳進去 |
| ④ `queue_size=1` | 佇列長度。處理不及時，最多積 1 則，舊的直接丟掉 |

**「回呼」是關鍵觀念。** 你不用寫迴圈去「拿」資料，是資料來了 ROS「推」給你。
所以 `map_callback` 這個函式在程式裡沒有任何一行呼叫它 —— 它是被 ROS 呼叫的。

```python
# scripts/map_server.py:121
def map_callback(msg):
    #            └── msg 就是一則 OccupancyGrid 訊息
    w, h = msg.info.width, msg.info.height
    ...
```

### `queue_size` 該設多少？

看你「漏掉舊資料會不會怎樣」：

```python
# scripts/map_server.py:608-610
rospy.Subscriber('/map',  OccupancyGrid, map_callback,  queue_size=1)   # 地圖：只要最新的
rospy.Subscriber('/odom', Odometry,      odom_callback, queue_size=10)  # 里程：要畫軌跡，漏了會斷線
rospy.Subscriber('/scan', LaserScan,     scan_callback, queue_size=1)   # 雷射：只要最新的
```

- **地圖**只要最新的那張，舊的沒有價值 → `1`
- **里程計**要拿來畫「走過的軌跡」，漏掉中間幾點軌跡就斷了 → `10`
- **雷射**只要最新的那圈，用來畫即時掃描圖 → `1`

---

## 1.4 發布：`rospy.Publisher` 逐字拆解

打開 `test/boustrophedon.py:77`：

```python
_pub = rospy.Publisher('/coverage_path', Path, queue_size=1, latch=True)
#                       └─①             └─②   └─③           └─④
```

| | 意思 |
|---|---|
| ① `'/coverage_path'` | 要發布的話題名稱 |
| ② `Path` | 訊息型別 |
| ③ `queue_size=1` | 送出佇列長度 |
| ④ `latch=True` | **鎖存**：把最後一則訊息記住，之後有新訂閱者連上來，立刻補送一份給他 |

`latch=True` 在這裡很重要：覆蓋路徑 5 秒才重算一次，
如果你晚一步才打開 RViz，沒有 latch 就要乾等 5 秒才看得到路徑。

發布資料本身很單純：

```python
# test/boustrophedon.py:64-69
path                 = Path()
path.header.stamp    = rospy.Time.now()
path.header.frame_id = msg.header.frame_id or 'map'
path.poses           = [_make_pose(x, y, path.header.frame_id) for x, y in pts]
_pub.publish(path)     # ← 丟出去
```

### 訊息物件怎麼建？

ROS 的訊息型別就是普通的 Python 類別，欄位預設值都是 0 / 空字串，你要哪個就填哪個：

```python
# scripts/map_server.py:232-235（手動遙控送速度）
tw = Twist()
tw.linear.x  = v       # 前進速度 m/s
tw.angular.z = w       # 轉向速度 rad/s
cmd_pub.publish(tw)
```

`Twist` 其實有 6 個欄位（`linear.x/y/z` + `angular.x/y/z`），
但 TurtleBot3 是**差速輪**機器人，只能前進/後退和原地轉，所以只用得到 `linear.x` 和 `angular.z`。

---

## 1.5 每個節點的起手式與事件迴圈

```python
# test/boustrophedon.py:73-80
def main():
    rospy.init_node('boustrophedon_planner')    # ① 註冊節點，取一個全域唯一的名字
    _pub = rospy.Publisher(...)                 # ② 宣告我要發什麼
    rospy.Subscriber(...)                       # ③ 宣告我要收什麼
    rospy.loginfo('[boustrophedon] 節點已啟動') # ④ 印 log（會帶時間戳與節點名）
    rospy.spin()                                # ⑤ 卡在這裡，讓回呼一直被呼叫
```

**`rospy.spin()` 是什麼？** 它就是「不要結束，一直等訊息進來」。
沒有這一行，`main()` 跑完程式就退出了，回呼一次都不會被觸發。

⚠ 本專案的 `map_server.py` **沒有**呼叫 `rospy.spin()`，因為它最後是去跑 Flask 伺服器
（`app.run(...)` 本身就是個無限迴圈），ROS 的回呼在背景執行緒裡跑。這個細節在第 17 章詳談。

### log 的四個等級

```python
rospy.loginfo('一般資訊')     # 白色
rospy.logwarn('警告')         # 黃色  ← map_server.py:340 路點跳過時用這個
rospy.logerr('錯誤')          # 紅色  ← map_server.py:275 SLAM 收不掉時用這個
rospy.logdebug('除錯')        # 預設不顯示
```

---

## 1.6 參數（Parameter）：不改程式就能換設定

有些設定希望啟動時才決定（網頁埠號、要不要自己管 SLAM），
寫死在程式裡很不方便。ROS 提供**參數伺服器**。

```python
# scripts/map_server.py:596-598
port = rospy.get_param('~port', 8080)
#                       └─①    └─②
slam_cfg['manage'] = bool(rospy.get_param('~manage_slam', True))
slam_cfg['method'] = str(rospy.get_param('~slam_methods', 'gmapping'))
```

- ① `~port` 開頭的 `~` 代表**私有參數**，實際完整名稱是 `/map_server/port`
  （`map_server` 是節點名）。加 `~` 是為了避免和別的節點撞名。
- ② `8080` 是**預設值**：沒人設定時就用這個。

參數在 launch 檔裡設定（第 06 章詳講）：

```xml
<!-- launch/start.launch:60-64 -->
<node pkg="turtlebot3_ccpp" type="map_server.py" name="map_server" output="screen">
    <param name="port"         value="$(arg port)" />
    <param name="manage_slam"  value="true"        />
    <param name="slam_methods" value="gmapping"    />
</node>
```

---

## 1.7 套件（Package）：ROS 的程式碼組織單位

ROS 裡所有程式碼都必須放在**套件**裡。一個套件 = 一個資料夾 + 兩個必備檔案：

```
turtlebot3_ccpp/          ← 套件名（要全域唯一）
├── package.xml           ← 必備：宣告套件名、版本、依賴哪些套件
├── CMakeLists.txt        ← 必備：怎麼建置、哪些檔案要安裝
└── ...
```

`package.xml` 看一眼就懂：

```xml
<name>turtlebot3_ccpp</name>
<exec_depend>rospy</exec_depend>       <!-- 執行時需要 rospy -->
<exec_depend>nav_msgs</exec_depend>    <!-- 執行時需要 nav_msgs 的訊息定義 -->
```

有了套件，就可以用**套件相對路徑**引用檔案，不用寫死絕對路徑：

```xml
<!-- launch/start.launch:12 -->
<include file="$(find turtlebot3_bringup)/launch/turtlebot3_robot.launch" />
<!--            └── 「去找 turtlebot3_bringup 這個套件裝在哪」 -->
```

```python
# scripts/map_server.py:41
PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')   # Python 版的 $(find ...)
```

第 06 章會完整拆解 `package.xml` 與 `CMakeLists.txt`。

---

## 1.8 launch 檔：一次啟動一整包節點

一個機器人系統動輒 10 個節點，一個個開太累。`.launch` 是 XML 檔，
描述「要啟動哪些節點、每個節點帶什麼參數」，用一行指令全部拉起來：

```bash
roslaunch turtlebot3_ccpp start.launch
#          └─ 套件名        └─ launch 檔名
```

三個最常用的標籤：

```xml
<node .../>       啟動一個節點
<include .../>    把另一個 launch 檔整包包進來
<param .../>      設定參數
<arg .../>        定義可從命令列覆寫的變數
```

`<arg>` 讓 launch 檔可以帶參數：

```xml
<!-- launch/start.launch:5-6 -->
<arg name="model"  default="burger" />
<arg name="port"   default="8080"   />
```

```bash
roslaunch turtlebot3_ccpp start.launch model:=waffle port:=9000
```

---

## 1.9 ★ 本專案的節點與話題全表

這是本章最該記住的一張表。

### 節點（誰在跑）

| 節點名 | 來源 | 職責 |
|---|---|---|
| `turtlebot3_core` 等 | `turtlebot3_bringup`（現成） | 讀硬體、發 `/scan` `/odom`、收 `/cmd_vel` |
| `slam_gmapping` | `gmapping`（現成） | SLAM：發 `/map` 與 `map→odom` 座標轉換 |
| `move_base` | `move_base`（現成） | 導航：收目標點，算路徑，發 `/cmd_vel` |
| **`map_server`** | **本專案 `scripts/map_server.py`** | 地圖處理 + 覆蓋規劃 + Flask 網頁 + 遙控 + SLAM 生命週期 |
| `boustrophedon_planner` | 本專案 `test/boustrophedon.py` | ⚠ 測試工具，**不隨 launch 啟動** |

⚠ 注意 `map_server` 這個節點名和 ROS 官方的 `map_server` 套件同名但**完全無關**，
官方那個是讀 `.yaml` 地圖檔的工具，本專案這個是自己寫的 Flask 伺服器。

### 我們的節點收發了什麼

```
                    ┌──────────────────────────────────┐
   /map ───────────→│                                  │
   （OccupancyGrid）│                                  │
                    │                                  │
   /odom ──────────→│      map_server（本專案）        │──→ /cmd_vel
   （Odometry）     │                                  │   （Twist，僅手動模式）
                    │                                  │
   /scan ──────────→│                                  │
   （LaserScan）    │                                  │
                    │                                  │
   /tf, /tf_static →│                                  │
   （由 tf2 內部訂閱）└─────────────┬───────────────────┘
                                    │
                                    │ actionlib（不是 topic）
                                    ↓
                              move_base 目標點
```

| 方向 | 話題 | 型別 | 用途 | 程式位置 |
|---|---|---|---|---|
| 訂閱 | `/map` | `nav_msgs/OccupancyGrid` | 產生四種地圖圖層 + 供規劃 | `map_server.py:608` |
| 訂閱 | `/odom` | `nav_msgs/Odometry` | 機器人位置 + 行走軌跡 | `map_server.py:609` |
| 訂閱 | `/scan` | `sensor_msgs/LaserScan` | 網頁上的即時雷射圖層 | `map_server.py:610` |
| 訂閱 | `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | 把雷射點轉到地圖座標 | `map_server.py:603-604` |
| 發布 | `/cmd_vel` | `geometry_msgs/Twist` | 手動遙控速度 | `map_server.py:606` |

### 1.10 ⚠ `/cmd_vel` 的多寫入者問題

注意上表：`/cmd_vel` 有**兩個**發布者 —— `move_base` 和我們的 `map_server`。

```
   move_base ────publish───┐
                           ├──→ /cmd_vel ──→ 馬達驅動
   map_server ──publish────┘
```

ROS **完全允許**這種多對一，而且不會報錯。後果是馬達會交替收到兩邊的指令，
表現出來就是「機器人一頓一頓、方向亂跳」。

本專案的解法：**自己在應用層做互斥**。

```python
# scripts/map_server.py:92
def manual_allowed():
    """手動遙控是否被允許（覆蓋執行中一律禁止）。"""
    with cov_lock:
        return cov_status['state'] != 'running'
```

```python
# scripts/map_server.py:220-227
def teleop_tick(_evt):
    if not manual_allowed():
        return          # ← 覆蓋執行中，/cmd_vel 交給 move_base，我們一句話都不發
```

> 💡 這是 ROS 新手最常踩的坑之一：**話題沒有「所有權」概念**，
> 誰都能發，衝突要自己管。詳見第 16 章。

---

## 1.11 除了話題，還有兩種通訊方式

話題是「廣播、單向、不等回應」，但有些情境需要別的：

| 方式 | 特性 | 適合 | 本專案有用嗎 |
|---|---|---|---|
| **Topic（話題）** | 單向、持續串流、不等回應 | 感測資料、狀態廣播 | ✅ 大量使用 |
| **Service（服務）** | 一問一答、同步阻塞 | 短查詢、開關切換 | ❌ 沒用到（改用 HTTP 路由） |
| **Action（動作）** | 一問一答但**耗時**，中途可查進度、可取消 | 「走到某個點」這種要花幾十秒的任務 | ✅ 用在 `move_base` |

Action 是本專案執行層的核心機制：

```python
# scripts/map_server.py:294
client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
```

「走到 (3.2, 1.5)」這件事可能要 20 秒，中途你想知道到了沒、想中途取消 ——
這正是 Action 設計出來要解決的。完整說明在第 03 章與第 13 章。

---

## 1.12 除錯用的指令（口試很可能被問）

系統跑起來後，這些指令讓你「看見」ROS 內部：

```bash
rosnode list                    # 現在有哪些節點在跑
rosnode info /map_server        # 這個節點收發什麼

rostopic list                   # 現在有哪些話題
rostopic info /map              # 這個話題的型別、誰發、誰收
rostopic echo /odom             # 把話題內容印出來看
rostopic hz /scan               # 量這個話題的實際頻率 ★

rosmsg show nav_msgs/OccupancyGrid   # 這個訊息型別有哪些欄位

rosparam list                   # 現在有哪些參數
rosparam get /map_server/port   # 看某個參數的值

rqt_graph                       # 畫出「誰發給誰」的圖形化節點關係圖 ★
rosrun tf view_frames           # 畫出 TF 座標樹（第 02 章）
```

> `rostopic hz /scan` 和本專案 `test/test_lidar_freq.py` 做的是同一件事 ——
> 後者是為了在報告裡留下可重現的量測證據才自己寫一份。

---

## 1.13 本章重點回顧

1. **節點 = 一支獨立的程式**，各跑各的、各用各的頻率，一個當掉不影響其他人。
2. **話題 = 具名廣播頻道**，節點透過 publish / subscribe 溝通，**雙方完全解耦**、互不知道對方存在。
3. **訂閱是回呼式的**：`rospy.Subscriber(話題, 型別, 回呼函式, queue_size)`，
   資料來了 ROS 自動呼叫你的函式，你不用寫迴圈去拿。
4. `queue_size` 依「漏掉舊資料會不會怎樣」決定：地圖/雷射用 `1`，里程計用 `10`（要畫連續軌跡）。
5. ⚠ **話題允許多個發布者且不會報錯**。`/cmd_vel` 同時有 `move_base` 和 `map_server` 兩個來源，
   必須自己在應用層做互斥。
6. **耗時任務用 Action 不用 Topic**：`move_base` 的「走到某點」可查進度、可取消。

---

## 1.14 自我檢核題

**Q1. `rospy.Subscriber('/odom', Odometry, odom_callback, queue_size=10)` 這一行做了什麼事？
`odom_callback` 什麼時候會被呼叫？**

<details>
<summary>參考答案</summary>

這一行向 ROS **註冊**：「我要訂閱 `/odom` 話題，它的訊息型別是 `Odometry`，
每收到一則就呼叫 `odom_callback` 並把訊息傳進去，最多幫我暫存 10 則。」

`odom_callback` 由 ROS 在**背景執行緒**中呼叫，程式碼裡不會有任何一行主動呼叫它。
呼叫的時機完全由 `/odom` 的發布者（`turtlebot3_bringup`）決定，本專案控制不了頻率。

這正是「回呼裡不該做重運算」的原因 —— 你不知道下一則什麼時候來，做太久就會塞車。
</details>

**Q2. 為什麼 `/map` 的 `queue_size` 是 1，而 `/odom` 是 10？**

<details>
<summary>參考答案</summary>

`queue_size` 是「處理不及時最多積幾則」，超過就丟掉最舊的。

- `/map` 每則都是**完整的一整張地圖**，新的一則完全取代舊的一則，
  舊地圖沒有任何保留價值 → 積 1 則就夠，而且地圖訊息很大，積多了浪費記憶體。
- `/odom` 用來累積**行走軌跡**（`map_server.py:188` 的 `odom_callback` 會把點加進 `robot_path`）。
  每一則都是軌跡上的一個點，漏掉中間幾則，畫出來的軌跡就會有跳躍或斷線 → 給多一點緩衝。

判準是：**這則訊息的價值是「取代式」還是「累積式」**。
</details>

**Q3. 一個話題可以有幾個發布者？幾個訂閱者？本專案有因此出過什麼問題？**

<details>
<summary>參考答案</summary>

**都可以有任意多個**，ROS 完全不限制，也不會警告。

本專案的 `/cmd_vel` 就有兩個發布者：`move_base`（自動導航時）和 `map_server`（手動遙控時）。
如果兩者同時發布，馬達會交替收到互相矛盾的速度指令，機器人行為變得不可預測。

解法是在應用層做互斥 —— `manual_allowed()`（`map_server.py:92`）
以 `cov_status['state']` 為單一真相來源，只要在 `running` 狀態就完全不發 `/cmd_vel`。
</details>

**Q4. `latch=True` 是什麼？`test/boustrophedon.py` 為什麼要用它？**

<details>
<summary>參考答案</summary>

`latch=True` 讓發布者**記住最後一則訊息**，之後只要有新的訂閱者連上這個話題，
ROS 就立刻把那則舊訊息補送給他一份。

`test/boustrophedon.py:26` 設定 `REPLAN_INTERVAL = 5.0`，也就是覆蓋路徑最快 5 秒才重算一次。
如果沒有 latch，你打開 RViz 的那一刻剛好錯過發布，就要盯著空白畫面等最多 5 秒。
有了 latch，RViz 一連上就馬上看到現有路徑。

**判準**：資料更新很慢、而且「最新一則永遠有效」的話題，就適合 latch
（地圖、靜態座標轉換、規劃結果）。高頻串流資料（雷射、里程計）不需要。
</details>

**Q5. 如果你想確認「`map_server` 到底有沒有收到 `/map`」，你會下哪些指令？**

<details>
<summary>參考答案</summary>

由粗到細：

```bash
rosnode list                # ① map_server 有在跑嗎
rostopic list               # ② /map 這個話題存在嗎（存在代表有人在發）
rostopic hz /map            # ③ /map 真的有資料在流嗎、多快
rostopic info /map          # ④ 訂閱者清單裡有沒有 /map_server
rqt_graph                   # ⑤ 圖形化確認連線關係
```

第 ④ 步是關鍵：`rostopic info` 會列出這個話題的 Publishers 和 Subscribers，
如果 `/map_server` 不在 Subscribers 裡，代表訂閱根本沒建立成功（通常是節點掛了或名稱打錯）。

另外本專案的 `map_callback` 每 2 秒會自己印一次接收統計
（`map_server.py:129-136`），直接看終端機輸出也行。
</details>

---

**← 上一章** [第 00 章　總覽與閱讀指南](00_總覽與閱讀指南.md)
**下一章 →** [第 02 章　感測與定位](02_感測與定位.md)
