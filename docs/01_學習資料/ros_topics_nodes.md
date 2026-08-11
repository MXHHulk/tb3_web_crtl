# ROS 節點 / Topic / Publisher / Subscriber 統整

> 本專案為 **ROS1**（`rospy` / `roslaunch`）。
> 本文件只統計「本專案自己程式碼」所建立的節點與收發，並標註每一項出自哪一隻程式。
> 由 `launch/start.launch` 引入的外部套件（bringup 驅動、gmapping、move_base）另外於下方「外部套件」段落說明。

---

## 一、總數統計（本專案程式碼）

| 類別 | 總數 | 說明 |
|------|:----:|------|
| **Node（節點）** | **2** | `map_server`、`boustrophedon_planner`（後者為 `test/` 工具，不隨 launch 啟動） |
| **Publisher（發布者）** | **1** | 另有 1 個 move_base action client（非 `rospy.Publisher`，見備註） |
| **Subscriber（訂閱者）** | **5** | 含 tf2 的 TransformListener（訂閱 `/tf`、`/tf_static`） |
| **Topic（話題）** | **5** | `/map`、`/odom`、`/scan`、`/coverage_path`、`/tf`(+`/tf_static`) |

---

## 二、Node（節點）一覽

| 節點名稱 | 出自程式 | 建立位置 | 狀態 |
|----------|----------|----------|------|
| `map_server` | `scripts/map_server.py` | `rospy.init_node('map_server')`（第 399 行） | 啟用（`start.launch` 掛載） |
| `boustrophedon_planner` | `test/boustrophedon.py` | `rospy.init_node('boustrophedon_planner')`（第 76 行） | **不隨 launch 啟動**（測試工具，功能與網頁重複；需要時 `python3 test/boustrophedon.py`） |

---

## 三、Publisher（發布者）一覽

| Topic | 訊息型別 | 出自程式 | 位置 | 備註 |
|-------|----------|----------|------|------|
| `/coverage_path` | `nav_msgs/Path` | `test/boustrophedon.py` | 第 77 行 `rospy.Publisher('/coverage_path', Path, queue_size=1, latch=True)` | latch 發布，僅供 RViz 顯示覆蓋路徑 |

### 備註：move_base Action Client（非傳統 Publisher）

`scripts/map_server.py` 第 196 行使用：

```python
client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
```

它並非 `rospy.Publisher`，但底層會**發布** `/move_base/goal`、`/move_base/cancel`，並**訂閱** `/move_base/feedback`、`/move_base/status`、`/move_base/result`。用途是把覆蓋路徑的每個路點依序送給 move_base 導航執行（`run_coverage()`）。

---

## 四、Subscriber（訂閱者）一覽

| Topic | 訊息型別 | Callback | 出自程式 | 位置 |
|-------|----------|----------|----------|------|
| `/map` | `nav_msgs/OccupancyGrid` | `map_callback` | `scripts/map_server.py` | 第 408 行 |
| `/odom` | `nav_msgs/Odometry` | `odom_callback` | `scripts/map_server.py` | 第 409 行 |
| `/scan` | `sensor_msgs/LaserScan` | `scan_callback` | `scripts/map_server.py` | 第 410 行 |
| `/tf` + `/tf_static` | `tf2_msgs/TFMessage` | （tf2 內部） | `scripts/map_server.py` | 第 406 行 `tf2_ros.TransformListener(tf_buffer)` |
| `/map` | `nav_msgs/OccupancyGrid` | `map_callback` | `test/boustrophedon.py` | 第 78 行（**測試工具，不隨 launch 啟動**） |

> 註：`tf2_ros.TransformListener` 會自動訂閱 `/tf` 與 `/tf_static` 兩個 topic，故訂閱者計為 5。

---

## 四之一、各 Subscriber 訂閱的 Topic 是用來做什麼

### `scripts/map_server.py`

#### `/map`（`OccupancyGrid`）→ `map_callback`
把 SLAM（gmapping）建好的佔據柵格地圖轉成網頁能顯示的圖片，是整個網頁地圖的資料來源。每次收到 `/map` 會：
- 統計收圖頻率（每 2 秒印一次「訊息總數 / 運行時間 / 平均 Hz」與地圖尺寸）。
- 把柵格值轉成**灰階原始地圖** PNG（未知=灰、空地=白、障礙=黑）。
- 額外產生**侵蝕圖**（障礙縮小，`binary_erosion`）與**膨脹圖**（障礙擴大，`binary_dilation`）兩個圖層，供網頁切換檢視。
- 自動**裁切**到有效範圍（`_crop`），並記錄座標換算所需的 meta（解析度、原點、裁切偏移）。
- 保存 `map_data`（原始柵格陣列、`frame_id`）供覆蓋路徑規劃與座標轉換使用。

#### `/odom`（`Odometry`）→ `odom_callback`
取得機器人即時位置，用來在網頁上畫出**機器人目前位置**與**行走軌跡**。每次收到會：
- 更新 `robot_pos`（目前 x, y）。
- 機器人每移動約 **0.1 m** 就在 `robot_path` 記一個點（畫成軌跡線）。
- 軌跡點數上限 10000，超過就丟最舊的（避免記憶體無限成長）。

#### `/scan`（`LaserScan`）→ `scan_callback`
取得雷射雷達即時掃描，用來在網頁上疊加**即時雷射點雲圖層**（紅點），直觀呈現「掃描 → 建圖」的過程。callback 本身**只保存最新一筆** `scan_msg`；真正的座標轉換（用 tf2 查 `map ← 雷射座標`、再換算成裁切後像素）延後到網頁 `/scan` 路由被輪詢時才做，避免每筆掃描都計算。

#### `/tf` + `/tf_static`（`TFMessage`）→ tf2 內部
不是自己寫的 callback，而是 `tf2_ros.TransformListener` 自動訂閱。用途是維護座標轉換樹，讓 `/scan` 的雷射點能從**雷射座標系轉換到地圖座標系**（`map ← base_scan`），雷射點才能正確疊在地圖上對齊。

### `test/boustrophedon.py`（測試工具，不隨 launch 啟動）

#### `/map`（`OccupancyGrid`）→ `map_callback`
拿 SLAM 地圖來**重新規劃牛耕式覆蓋路徑**並發布到 `/coverage_path`。每次收到會：
- 節流：距上次規劃需超過 `REPLAN_INTERVAL` 秒才重算。
- 對障礙做**安全膨脹**（`apply_safety_margin`，留出機器人半徑餘裕），得到可通行的空地遮罩。
- 用 `boustrophedon()` 產生來回掃描（牛耕）路點，包成 `nav_msgs/Path` 發布，供 RViz 顯示。

---

## 五、Topic（話題）一覽

| Topic | 訊息型別 | 由誰發布 | 由誰訂閱（本專案） |
|-------|----------|----------|----------|
| `/map` | `nav_msgs/OccupancyGrid` | gmapping（外部） | `scripts/map_server.py`、`test/boustrophedon.py` |
| `/odom` | `nav_msgs/Odometry` | bringup 驅動（外部） | `map_server.py` |
| `/scan` | `sensor_msgs/LaserScan` | bringup 驅動（外部） | `map_server.py` |
| `/coverage_path` | `nav_msgs/Path` | `test/boustrophedon.py` | RViz（外部顯示用） |
| `/tf`、`/tf_static` | `tf2_msgs/TFMessage` | gmapping / bringup（外部） | `map_server.py`（tf2 listener） |

---

## 六、外部套件節點（由 `launch/start.launch` 引入，非本專案程式碼）

這些節點提供上表中本專案訂閱的 topic，列出以便理解資料來源：

| 節點 / 套件 | 來源 | 提供的主要 topic |
|-------------|------|------------------|
| `turtlebot3_robot`（bringup 驅動） | `turtlebot3_bringup/launch/turtlebot3_robot.launch` | `/scan`、`/odom`、`/cmd_vel` |
| `gmapping`（SLAM 建圖） | `turtlebot3_slam/launch/turtlebot3_slam.launch` | `/map`、`map→odom` 的 TF |
| `move_base`（導航規劃） | `move_base` 套件 | `/move_base/*` action、`/cmd_vel` |

---

## 七、每隻程式的收發總覽

### `scripts/map_server.py`（節點：`map_server`）
- **Subscriber ×4**：`/map`、`/odom`、`/scan`、`/tf`(+`/tf_static`)
- **Publisher ×0**（改用 move_base action client：發 `/move_base/goal`、`/move_base/cancel`）
- 額外功能：內建 Flask 網頁伺服器（HTTP，非 ROS topic）

### `test/boustrophedon.py`（節點：`boustrophedon_planner`，不隨 launch 啟動）
- **Subscriber ×1**：`/map`
- **Publisher ×1**：`/coverage_path`（latch）

---

*本文件依 `scripts/map_server.py`、`test/boustrophedon.py`、`launch/start.launch` 之原始碼統整而成。*
