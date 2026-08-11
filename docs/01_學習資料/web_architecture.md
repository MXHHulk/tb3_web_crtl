# `/web` 如何把節點資料呈現在網頁上

> 說明本專案怎麼把 ROS 節點（`/map`、`/odom`、`/scan` 等）的資料，透過
> `scripts/map_server.py`（後端）＋ `web/index.html`（前端）呈現在瀏覽器上。

---

## 一、整體架構（一句話）

`map_server` 這個 ROS 節點**同時扮演兩個角色**：

1. **ROS 訂閱者** —— 收 `/map`、`/odom`、`/scan`、`/tf`，把資料存進記憶體變數。
2. **Flask 網頁伺服器** —— 開一個 HTTP 服務（預設 `:8080`），瀏覽器來要資料時，
   把記憶體裡的最新資料轉成 PNG 圖片或 JSON 回傳。

前端 `web/index.html` 是純網頁（HTML + Canvas + JS），**定時輪詢**後端這些網址，
拿到資料後畫在 `<canvas>` 上。

```
 ROS 世界                          map_server.py                       瀏覽器
┌──────────┐  /map            ┌────────────────────────┐        ┌──────────────┐
│ gmapping │ ───────────────▶ │ Subscriber callback     │        │ index.html   │
│ bringup  │  /odom /scan     │  → 存進全域變數          │        │              │
│ (TF)     │ ───────────────▶ │    (map_png, robot_pos, │  HTTP  │ 每秒 refresh │
└──────────┘                  │     scan_msg ...)        │◀──────▶│ 每200ms scan │
                              │                          │  輪詢   │              │
                              │ Flask 路由                │  回傳   │ 畫到 canvas  │
                              │  /map.png /robot_state   │ PNG/JSON│              │
                              │  /scan /coverage/*        │        │              │
                              └────────────────────────┘        └──────────────┘
```

兩個角色跑在同一個行程裡：`main()` 註冊完 ROS 訂閱後，用
**另一條執行緒**啟動 Flask（`threading.Thread(target=app.run ...)`），
主執行緒繼續跑 `rospy.spin()` 處理 ROS 回呼。共享的記憶體變數用 `Lock` 保護
（`map_lock`、`robot_lock`、`scan_lock`、`cov_lock`）避免兩邊同時讀寫衝突。

---

## 二、資料流：從節點到畫面（三步）

### 步驟 1：ROS 回呼把資料存進記憶體
（詳見 [`ros_topics_nodes.md`](./ros_topics_nodes.md) 四之一）

| 訂閱 topic | callback | 存到哪個變數 |
|-----------|----------|-------------|
| `/map` | `map_callback` | `map_png` / `map_eroded` / `map_dilated`（PNG bytes）、`map_meta`、`map_data` |
| `/odom` | `odom_callback` | `robot_pos`（目前位置）、`robot_path`（軌跡點） |
| `/scan` | `scan_callback` | `scan_msg`（只存最新一筆原始掃描） |
| `/tf` | tf2 listener | `tf_buffer`（座標轉換樹） |

### 步驟 2：Flask 路由把記憶體資料轉成 HTTP 回應

| 網址（route） | 回傳格式 | 內容 | 對應程式 |
|--------------|----------|------|----------|
| `/` | HTML | 直接讀 `web/index.html` 回傳 | `index()` (274) |
| `/map.png` | PNG 圖片 | 原始灰階地圖 | `get_map()` (278) |
| `/map_eroded.png` | PNG 圖片 | 侵蝕圖層（障礙縮小） | `get_map_eroded()` (283) |
| `/map_dilated.png` | PNG 圖片 | 膨脹圖層（障礙擴大） | `get_map_dilated()` (288) |
| `/robot_state` | JSON | 機器人像素/世界座標 + 軌跡 + 解析度 | `get_robot_state()` (294) |
| `/scan` | JSON | 雷射點雲（已轉成圖片像素座標） | `get_scan()` (313) |
| `/coverage/start` | JSON | 觸發覆蓋路徑執行 | `coverage_start()` (347) |
| `/coverage/stop` | JSON | 中止覆蓋執行 | `coverage_stop()` (377) |
| `/coverage/status` | JSON | 覆蓋進度 + 路徑像素座標 | `coverage_status()` (385) |

**關鍵：座標轉換**
ROS 用「世界座標（公尺）」，網頁 canvas 用「圖片像素」。後端用
`world_to_px()` 把世界座標換成**裁切後圖片的像素座標**，前端就能直接畫，
不必自己算原點與解析度。所以 `/robot_state`、`/scan`、`/coverage/status`
回傳的都是「已經算好的像素座標」。

### 步驟 3：前端輪詢並畫到 Canvas

前端有**兩個獨立輪詢迴圈**（因為各資料更新速度不同）：

| 迴圈 | 週期 | 抓什麼 | 程式 |
|------|------|--------|------|
| `refresh()` | **1 秒** | 3 張地圖 PNG + `/robot_state` + `/coverage/status` | `setInterval(refresh, 1000)` |
| `refreshScan()` | **200 ms（~5 Hz）** | `/scan` | `setInterval(refreshScan, 200)` |

> 為什麼分兩個？`/map` 由 gmapping 出圖很慢（~0.33 Hz），但 `/scan` 是 ~5 Hz
> 的即時雷達。若全部綁 1 秒，雷射點看起來會「卡卡的」。分開後：地圖慢慢長、
> 雷射點即時跳動，能直觀看到「掃描 → 建圖」的過程。

拿到資料後統一由 `draw()` 依圖層順序畫到同一個 `<canvas>`：
地圖（原始/侵蝕/膨脹）→ 覆蓋路徑 → 行走軌跡 → 雷射點 → 機器人。
每個圖層都可用頂部按鈕即時開關（`LAYERS` 陣列的 `on` 旗標）。

---

## 三、前端呈現的細節

- **地圖疊圖**：原始圖直接畫；侵蝕/膨脹圖經 `colorize()` 把灰階轉成半透明彩色
  （藍/紅），障礙著色、空地透明，才能疊在原圖上比較。
- **防快取**：圖片網址後面加 `?t=時間戳`（`loadImg`），後端也回
  `Cache-Control: no-store`，確保每次拿到的是最新地圖而非瀏覽器快取。
- **Canvas 自適應**：`fitCanvas()` 依視窗大小等比縮放，`image-rendering: pixelated`
  讓地圖放大時保持格子感不模糊。
- **覆蓋路徑動態**：`/coverage/status` 回傳 `done`（已完成路點數），前端把已走
  部分畫實線、待走部分畫虛線。

---

## 四、覆蓋執行的雙向互動（不只是看，還能控制）

前端按鈕 → 後端動作，是唯一「網頁反向控制 ROS」的路徑：

```
[▶ 開始覆蓋] ─POST /coverage/start─▶ 後端用目前地圖算牛耕路徑
                                     → 開執行緒 run_coverage()
                                     → 透過 move_base action client
                                       把路點一個個送去導航
[■ 停止]     ─POST /coverage/stop──▶ 設 cov_status['state']='stopped'
                                     → run_coverage() 取消 move_base 目標
每秒         ─GET  /coverage/status─▶ 回傳進度，前端更新「執行中 3/20」與路徑線
```

> 注意：這裡不是發布 ROS topic，而是後端用 `SimpleActionClient('move_base', ...)`
> 把路點送給 move_base 導航（詳見 [`ros_topics_nodes.md`](./ros_topics_nodes.md) 第三節備註）。

---

## 五、一頁總結

1. `map_server.py` 一個節點身兼「ROS 訂閱者」與「Flask 伺服器」，跑在同行程不同執行緒。
2. ROS 回呼把 `/map`、`/odom`、`/scan` 資料存進記憶體變數（用 Lock 保護）。
3. Flask 路由把這些資料轉成 **PNG（地圖）** 或 **JSON（座標/狀態）**，並事先用
   `world_to_px()` 換算成圖片像素座標。
4. 前端 `index.html` 用 **1 秒**（地圖/機器人/覆蓋）＋ **200ms**（雷射）兩個輪詢，
   把資料畫到 Canvas 的多個可切換圖層。
5. 「開始/停止覆蓋」按鈕透過 POST 路由反向觸發後端 move_base 導航。

---

*本文件依 `scripts/map_server.py`（Flask 路由）與 `web/index.html`（前端輪詢/繪製）之原始碼統整。*
