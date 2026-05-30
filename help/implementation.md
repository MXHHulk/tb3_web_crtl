# Flask 地圖監控系統 — 實作說明

## 目錄

1. [架構概覽](#架構概覽)
2. [資料流程](#資料流程)
3. [核心元件說明](#核心元件說明)
4. [地圖轉換邏輯](#地圖轉換邏輯)
5. [Server-Sent Events 機制](#server-sent-events-機制)
6. [如何啟動](#如何啟動)
7. [為什麼選擇這個架構](#為什麼選擇這個架構)
8. [檔案結構](#檔案結構)

---

## 架構概覽

```
TurtleBot3 ROS
    │
    │  /map (nav_msgs/OccupancyGrid)
    ▼
flask_map_server.py       ← ROS 節點 + Flask HTTP 伺服器
    │
    ├── GET /              → index.html（監控頁面）
    ├── GET /static/*      → CSS / JS 靜態資源
    ├── GET /api/map/image → 當前地圖 PNG
    ├── GET /api/map/info  → 地圖元數據（JSON）
    └── GET /api/events    → SSE 事件流（推送更新通知）
              │
              ▼ 瀏覽器（同網域任何設備）
              ├── 建立 SSE 長連線
              ├── 收到 map_update 事件
              └── 請求 /api/map/image?v=N → 顯示最新地圖
```

**不需要 rosbridge**。所有 ROS 資料都在伺服器端處理，瀏覽器只需要支援基本 HTTP 的即可。

---

## 資料流程

### 完整流程（含時序）

```
TB3 SLAM              Flask 後端                     瀏覽器
─────────             ─────────                     ───────
                      啟動節點
                      訂閱 /map
                      啟動 Flask（port 8080）

                                              開啟頁面 → GET /
                                              載入 index.html
                                              連線 GET /api/events（SSE 長連線）
                      queue 建立（此客戶端）
                      傳送心跳 (:heartbeat)

發佈 /map ──────────► _map_callback()
                      OccupancyGrid → PNG
                      _map_version += 1
                      push 到所有 client queue

                      SSE generator 讀 queue ──────► 收到 map_update 事件
                                              updateMap(version, meta)
                                              背景預載 /api/map/image?v=N
                                              載入完成 → 替換 <img src>
                                              更新資訊面板
```

---

## 核心元件說明

### `scripts/flask_map_server.py`

| 元素 | 說明 |
|------|------|
| `_map_lock` | `threading.Lock`，保護 `_map_png` / `_map_meta` / `_map_version` 的讀寫 |
| `_client_queues` | 每個 SSE 連線對應一個 `queue.Queue`，新地圖到達時廣播 |
| `_map_callback()` | ROS subscriber callback，轉換地圖並通知瀏覽器 |
| `event_stream()` | SSE 端點，每個請求建立獨立佇列，`finally` 確保清理 |
| `flask_thread` | Flask 在 daemon thread 中運行，主執行緒保留給 `rospy.spin()` |

### `web_interface/static/js/map_client.js`

| 函式 | 說明 |
|------|------|
| `connectSSE()` | 建立 `EventSource` 連線，自動重連（3 秒） |
| `updateMap(version, meta)` | 預載新圖（`new Image()`），載入完成再替換，避免閃爍 |
| `es.onmessage` | 解析 SSE 事件，觸發地圖更新與資訊面板刷新 |

---

## 地圖轉換邏輯

ROS 的 `nav_msgs/OccupancyGrid` 使用整數表示每格的佔用機率：

| 值 | 意義 | 轉換後顏色 |
|----|------|-----------|
| `-1` | 未知（未探索） | 128（灰色） |
| `0` | 可通行（空地） | 255（白色） |
| `1–99` | 佔用機率（漸進） | 255 → 0（淺灰至黑） |
| `100` | 障礙物 | 0（黑色） |

**轉換公式：**

```python
gray[known] = clip(255 - (data[known] * 255 // 100), 0, 255)
```

**座標翻轉：**  
ROS 地圖的原點 `(0,0)` 在左下角（Y 軸向上），PNG 圖片的原點在左上角（Y 軸向下），因此需要 `np.flipud()` 上下翻轉。

**輸出格式：**  
灰階陣列 → PIL Image（'L' 模式） → 轉 RGB → PNG bytes 存入記憶體快取。

---

## Server-Sent Events 機制

### 為什麼用 SSE 而非 HTTP 輪詢

| 比較項目 | HTTP 輪詢（每 N 秒） | SSE（本系統） |
|----------|---------------------|--------------|
| 通訊方式 | 瀏覽器主動請求 | 伺服器主動推送 |
| 地圖無更新時 | 浪費頻寬（空請求） | 無封包傳送 |
| 地圖更新延遲 | 最多 N 秒 | 近即時（毫秒級） |
| 實作複雜度 | 低 | 低（瀏覽器原生支援） |

### SSE vs WebSocket

SSE 是 HTTP 單向長連線，瀏覽器原生支援 `EventSource` API，不需要額外函式庫（roslib.js / socket.io）。對於「只需要伺服器→瀏覽器」的地圖推送場景，SSE 比 WebSocket 更簡單。

### 多客戶端廣播

```
新地圖到達
    │
    ▼ _map_callback()
    for q in _client_queues:
        q.put_nowait(event_json)   ← 推入每個客戶端的佇列

每個 SSE 連線（獨立 thread）:
    while True:
        evt = client_q.get(timeout=25)  ← 阻塞等待
        yield f'data: {evt}\n\n'        ← 推送給瀏覽器
```

### SSE 訊息格式

```
data: {"type":"map_update","version":42,"width":384,"height":384,"resolution":0.05}

```

每筆訊息以兩個換行結尾（`\n\n`）。心跳行以 `: ` 開頭，瀏覽器不會觸發 `onmessage`。

---

## 如何啟動

### 1. 安裝 Python 依賴

```bash
pip3 install flask>=2.0 Pillow>=9.0
```

### 2. 編譯 ROS Package

```bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

### 3. 啟動 SLAM（在另一個終端）

```bash
# 模擬器
roslaunch turtlebot3_gazebo turtlebot3_world.launch

# 實機
roslaunch turtlebot3_bringup turtlebot3_robot.launch
```

```bash
# SLAM（任一終端）
roslaunch turtlebot3_slam turtlebot3_slam.launch
```

### 4. 啟動 Flask 地圖伺服器

```bash
roslaunch turtlebot3_ccpp flask_web_monitor.launch
# 或指定埠號：
roslaunch turtlebot3_ccpp flask_web_monitor.launch port:=8080
```

### 5. 開啟瀏覽器

終端會顯示：
```
Flask 地圖伺服器已啟動！
本機存取：http://localhost:8080
區域網路：http://192.168.x.x:8080
```

**同網域的其他設備**（手機、平板、其他電腦）直接輸入區域網路 URL 即可看到地圖。

---

## 為什麼選擇這個架構

### 與 master 分支（rosbridge 架構）的比較

| 項目 | master（rosbridge） | rebuild（Flask） |
|------|---------------------|-----------------|
| 瀏覽器連線方式 | WebSocket → rosbridge → ROS | HTTP → Flask → ROS |
| 額外依賴 | `rosbridge_suite` ROS 套件 | `flask`, `Pillow`（pip） |
| 地圖格式 | OccupancyGrid JSON（原始資料）| PNG 圖片（已處理） |
| 頻寬消耗 | 高（傳送所有格點數值） | 低（PNG 壓縮後） |
| 前端複雜度 | 高（需 roslib.js + Canvas 渲染）| 低（`<img>` 標籤即可） |
| 安全性 | rosbridge 開放 ROS 完整控制權 | Flask 只暴露定義的端點 |

### Flask 作為 ROS 節點的優點

1. **統一入口**：一個 port 提供所有服務，不需要同時開 8000（HTTP）和 9090（WebSocket）。
2. **伺服器端預處理**：地圖轉換（OccupancyGrid→PNG）在伺服器完成，瀏覽器效能要求低。
3. **可擴充性**：未來可輕易新增 REST API 端點（如機器人控制、任務狀態），不依賴 rosbridge 的 service call 機制。

---

## 檔案結構

```
turtlebot3_ccpp/
├── scripts/
│   └── flask_map_server.py      ← 主程式（ROS 節點 + Flask）
├── web_interface/
│   ├── templates/
│   │   └── index.html           ← Jinja2 模板（首頁）
│   └── static/
│       ├── css/
│       │   └── style.css        ← 介面樣式
│       └── js/
│           └── map_client.js    ← 前端邏輯（SSE + 地圖更新）
├── launch/
│   └── flask_web_monitor.launch ← ROS launch 設定
├── help/
│   └── implementation.md        ← 本說明文件
├── CMakeLists.txt
└── package.xml
```
