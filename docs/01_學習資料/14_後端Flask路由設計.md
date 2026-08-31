# 第 14 章　後端 Flask 路由設計

> **本章目標**：把 12 條 HTTP 路由逐條講清楚，
> 以及貫穿全部路由的三條原則：**無狀態、防禦性、後端算完**。

---

## 14.1 ① 問題：ROS 在機器人上，瀏覽器在手機上

```
   機器人（Ubuntu + ROS）              手機 / 筆電
   ┌────────────────────┐             ┌──────────────┐
   │  /map  /odom  /scan│             │   瀏覽器     │
   │  move_base ...     │  ？？？     │              │
   └────────────────────┘             └──────────────┘
```

瀏覽器不會講 ROS。要在中間架一座橋。

第 05 章已經決定了橋的形式：**HTTP + PNG + JSON + 1 Hz 輪詢**
（否決了 rosbridge，理由見 5.4）。本章講這座橋怎麼蓋。

---

## 14.2 ② 直覺做法與撞牆

### 直覺：每個路由自己去拿最新資料

```python
# ❌ 想像的寫法
@app.route('/map.png')
def get_map():
    msg = rospy.wait_for_message('/map', OccupancyGrid)   # 等一則新的
    return to_png(msg)
```

### 撞牆

| 問題 | 後果 |
|---|---|
| **會卡很久** | `/map` 幾 Hz 才一則，最壞要等好幾百毫秒 |
| **重複計算** | 每個請求都重做一次形態學 + PNG 編碼 |
| **多個路由不同步** | `/map.png` 和 `/coverage/status` 拿到不同時刻的地圖 → 路徑畫錯位 |
| **沒有資料時直接掛** | `wait_for_message` 逾時會拋例外 → HTTP 500 |

---

## 14.3 ④ 現在的做法：三條原則

### 原則一：★ 路由是「無狀態的讀取器」

```
   ROS 回呼執行緒               共享狀態              Flask 執行緒
   ─────────────────           ─────────           ─────────────
   map_callback   ──寫──→   map_png, map_meta  ──讀──→  /map.png
   odom_callback  ──寫──→   robot_pos, path    ──讀──→  /robot_state
   scan_callback  ──寫──→   scan_msg           ──讀──→  /scan
   run_coverage   ──寫──→   cov_status         ──讀──→  /coverage/status
```

★ **路由永遠不「等待」ROS 資料，只讀取「最近一次收到的」。**

所有的計算（形態學、PNG 編碼）都在**回呼那一側**做完，
路由只做「拿出來、必要時做一點座標轉換、回傳」。

（例外是 `/scan`，見 14.5。）

### 原則二：★ 防禦性 —— 沒資料時優雅降級，不噴 500

```python
# scripts/map_server.py:362-367
def _serve_png(data):
    if data is None:
        return Response('等待地圖...', status=503)
    resp = send_file(io.BytesIO(data), mimetype='image/png')
    resp.headers['Cache-Control'] = 'no-store'
    return resp
```

四張地圖路由全部走這個函式。

| 情境 | 回什麼 | 前端表現 |
|---|---|---|
| 地圖還沒好 | **503** + 文字 | `loadImg` 的 `onerror` 觸發 → 保留舊圖或顯示「等待地圖資料…」 |
| TF 查不到 | `{'points': []}` | 雷射圖層暫時空白，其他照常 |
| 機器人位置未知 | `{'pos': None, 'path': []}` | 不畫機器人圖示 |
| 沒有 `index.html` | **404** + 文字 | 明確的錯誤訊息 |

★ **絕不讓單一功能的失敗擴散成整頁掛掉。**

### 原則三：★ 座標轉換在後端做完

第 05 章 5.4 和第 07 章 7.4 講過。前端拿到的全部是**圖片像素座標**。

---

## 14.4 路由總表

| 方法 | 路徑 | 回什麼 | 行號 |
|---|---|---|---|
| GET | `/` | 網頁本體（HTML 文字） | 370-373 |
| GET | `/map.png` | 原始地圖 PNG | 376-379 |
| GET | `/map_eroded.png` | 侵蝕圖層 PNG（顯示用） | 382-385 |
| GET | `/map_dilated.png` | 膨脹圖層 PNG（顯示用） | 388-391 |
| GET | `/map_margin.png` | ★ 安全邊距 PNG（規劃用，所見即所算） | 394-398 |
| GET | `/robot_state` | 位置 + 軌跡（像素座標）JSON | 401-417 |
| GET | `/scan` | 即時雷射點（像素座標）JSON | 420-450 |
| POST | `/coverage/start` | 規劃 + 啟動，回診斷資訊 | 453-497 |
| POST | `/coverage/stop` | 停止 | 500-506 |
| GET | `/coverage/status` | 進度 + cell + 診斷 JSON | 509-528 |
| POST | `/teleop` | 手動速度 | 531-548 |
| POST | `/slam/restart` | 重啟 SLAM | 551-587 |

★ **前端每秒輪詢的只有 3 條**（`/coverage/status`、`/robot_state`、
加上開啟中的地圖圖層）。其他都是使用者動作觸發的。

---

## 14.5 逐條拆解

### `GET /` — 網頁本體

```python
# scripts/map_server.py:370-373
@app.route('/')
def index():
    p = os.path.join(PKG, 'web', 'index.html')
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ('找不到 index.html', 404)
```

★ **每次請求都重新讀檔**，不快取。

> 💡 開發時的價值：改一行 `index.html`，**重新整理瀏覽器就看得到**，
> 不用重啟節點、不用 `catkin_make`。
>
> 代價是每次請求多一次磁碟 I/O（23 KB，微秒級）。
> 而且這條路由一次連線只會被叫一次，完全不是熱點。

### `GET /map*.png` — 四張地圖

```python
# scripts/map_server.py:376-398
@app.route('/map.png')
def get_map():
    with map_lock: d = map_png
    return _serve_png(d)
# （其他三條結構完全相同）
```

★ **鎖裡只有一行賦值**。`map_png` 是 `bytes`（不可變物件），
拿到引用之後就算 `map_callback` 換掉全域變數，我們手上這份也不會變。

**`Cache-Control: no-store` 為什麼必要？**

地圖一直在變，但網址永遠是 `/map.png`。
沒有這個標頭的話，瀏覽器會快取住第一張圖，之後永遠不再請求 —— 地圖看起來凍結了。

★ 前端還加了第二道保險：

```javascript
// web/index.html:553
img.src = url + '?t=' + Date.now();     // 每次都是不同的網址
```

**兩道保險都做**，因為不同瀏覽器 / 代理伺服器對快取標頭的處理不一致。

### `GET /robot_state` — 位置與軌跡

```python
# scripts/map_server.py:401-417
@app.route('/robot_state')
def get_robot_state():
    with map_lock:   meta = dict(map_meta)
    with robot_lock: pos  = dict(robot_pos); path_w = list(robot_path)

    if not meta or pos['x'] is None:
        return jsonify({'pos': None, 'path': [], 'resolution': 0.05})

    px, py = world_to_px(pos['x'], pos['y'], meta)
    return jsonify({
        'pos': {
            'x': px, 'y': py,                              # 像素（畫圖用）
            'wx': round(pos['x'], 2), 'wy': round(pos['y'], 2),   # 世界（顯示用）
        },
        'path':       [list(world_to_px(p[0], p[1], meta)) for p in path_w],
        'resolution': meta['resolution'],
    })
```

**三個細節：**

**① 同時回像素座標和世界座標**

- `x`, `y`（像素）→ 給 Canvas 畫圖用
- `wx`, `wy`（公尺）→ 顯示在頂列時鐘旁邊給人看

```javascript
// web/index.html:578-580
const p = robot.pos;
const t = new Date().toLocaleTimeString('zh-TW');
$('clock').textContent = p ? `${t}　(${p.wx}, ${p.wy}) m` : `${t}　等待機器人`;
```

**② 回傳 `resolution`**

前端唯一用到的地方是畫機器人圖示的半徑：

```javascript
// web/index.html:391
const r = Math.max(1, 0.105 / (robot.resolution || 0.05));
```

`0.105` 是 Burger 的半徑（公尺），除以解析度就是**幾個像素**。
這樣圖示的大小會隨著地圖縮放正確變化。

★ **這是前端唯一一處「數學」**，而且只是一個除法。

**③ 兩把鎖，分別取**

```python
with map_lock:   meta = dict(map_meta)
with robot_lock: pos = dict(robot_pos); path_w = list(robot_path)
```

★ **不能寫成巢狀 `with map_lock: with robot_lock:`** ——
那會製造死鎖的可能（如果別處以相反順序取這兩把鎖）。

分開取的代價：`meta` 和 `pos` 可能來自不同時刻。
但 `/map` 只有幾 Hz、裁切偏移只在建圖初期變動，
實務上這個誤差看不出來（第 07 章 7.8 Q5 討論過）。

### `GET /scan` — 唯一在路由裡做計算的

```python
# scripts/map_server.py:420-450
@app.route('/scan')
def get_scan():
    """把最新一筆 /scan 透過 TF 轉到 map 座標，再換算成裁切後圖片像素回傳。"""
    with map_lock:  meta = dict(map_meta)
    with scan_lock: msg = scan_msg
    ...
    for r in msg.ranges:                      # ★ 360 次三角函數
        if rmin <= r <= rmax:
            lx, ly = r * math.cos(ang), r * math.sin(ang)
            wx = t.x + cos_y * lx - sin_y * ly
            wy = t.y + sin_y * lx + cos_y * ly
            pts.append(list(world_to_px(wx, wy, meta)))
        ang += inc
    return jsonify({'points': pts})
```

★ **這是唯一違反「原則一」的路由** —— 計算在路由裡做，不在回呼裡。

```python
# scripts/map_server.py:210-214
def scan_callback(msg):
    """收到 /scan 時僅保存最新一筆，轉換到地圖座標延後到 /scan 路由處理。"""
    global scan_msg
    with scan_lock:
        scan_msg = msg
```

**為什麼刻意這樣設計？**

| | 在回呼算 | 在路由算（現在） |
|---|---|---|
| 計算頻率 | **5 Hz**（`/scan` 的頻率） | **只在有人請求時** |
| 沒人開網頁時 | 每秒白算 5 次 × 360 點 | **完全不算** |
| 對 ROS 回呼的影響 | 拖慢 `/scan` 的接收 | 無 |

★ **判準是「消費頻率 vs 產生頻率」**：

- **地圖**：產生 ~3 Hz，消費 1 Hz → 差不多，在回呼算（而且結果可以被四個路由共用）
- **雷射**：產生 5 Hz，消費 **0~1 Hz**（圖層預設是關的！）→ 在路由算

> ⚠ 注意 `LAYERS` 裡**沒有雷射圖層**（`web/index.html:216-223`），
> 它在 2026-08-17 被移除了（開發日志有記錄：「雷射點在畫面上只是雜訊」）。
> 所以 `/scan` 這條路由目前**沒有任何前端在呼叫**，是保留給 `test/` 和未來用的。

### `GET /coverage/status` — 前端的主要資料來源

```python
# scripts/map_server.py:509-528
@app.route('/coverage/status')
def coverage_status():
    with cov_lock:
        st     = dict(cov_status)
        path_w = list(cov_path)
        cells  = [list(c) for c in cov_cells]
        info   = dict(cov_info)
    with map_lock:
        meta = dict(map_meta)

    if meta:
        st['path_px']  = [list(world_to_px(x, y, meta)) for x, y in path_w]
        st['cells_px'] = [[list(world_to_px(x, y, meta)) for x, y in c] for c in cells]
    else:
        st['path_px'] = st['cells_px'] = []

    st['info']   = info
    st['manual'] = st['state'] != 'running'          # ★ 派生欄位
    st['slam_managed'] = slam_cfg['manage']
    return jsonify(st)
```

**回傳的完整結構：**

```json
{
  "state": "running",              // idle/running/stopped/done/error
  "done": 42, "total": 300,        // 進度
  "msg": "路點 17/300 跳過（無法到達）",
  "path_px": [[12.3, 45.6], ...],  // 全部路點（像素）
  "cells_px": [[[..],[..]], ...],  // 每個 cell 的路點（像素）
  "info": {                        // 演算法診斷
    "n_runs": 14, "n_cells": 4, "n_critical": 2,
    "axis_deg": 0.0, "ratio": 4.64
  },
  "manual": false,                 // ★ 派生：能不能手動遙控
  "slam_managed": true             // 重啟 SLAM 按鈕能不能用
}
```

★ **`manual` 是一個「派生欄位」**：後端從 `state` 算出來，前端直接用。

```javascript
// web/index.html:515-521
$('btn-start').disabled = !cov.manual;
$('btn-stop').disabled  = cov.manual;
for (const b of $('pad').children) b.disabled = !cov.manual;
```

★ **為什麼不讓前端自己判斷 `state !== 'running'`？**

因為那會**把規則複製到兩個地方**。哪天加一個新狀態
（例如 `paused`，也該禁止遙控），後端改了前端忘了改，兩邊就不一致了。

**規則只寫一次，寫在有權威的那一邊。** 這和第 05 章「所見即所算」是同一個思路。

### `POST /coverage/start|stop`

第 13 章詳細講過。這裡只補一個對照：

```python
# start（複雜）：規劃 200 ms + 開執行緒
# stop（極簡）：改一個字串
@app.route('/coverage/stop', methods=['POST'])
def coverage_stop():
    with cov_lock:
        if cov_status['state'] == 'running':
            cov_status['state'] = 'stopped'
    teleop_halt()
    return jsonify({'ok': True})
```

★ **停止一個 30 分鐘的任務，只需要改一個字串** ——
這是「共享狀態放在同一個行程」的紅利（第 04 章 4.4）。

★ `if state == 'running'` 的檢查避免把 `done` 或 `error` 覆寫成 `stopped`。

### `POST /teleop` 與 `POST /slam/restart`

分別在第 16 章和第 06 章詳講。

---

## 14.6 ⑤ 設計決策

| 決策 | 選了 | 否決了 | 理由 |
|---|---|---|---|
| 資料取得 | 讀共享狀態 | `rospy.wait_for_message` | 會卡、會重算、不同步 |
| 計算位置 | 回呼（地圖）/ 路由（雷射） | 統一一邊 | 依「消費頻率 vs 產生頻率」決定 |
| 沒資料 | 503 / 空陣列 | 拋例外 | 優雅降級，不讓整頁掛掉 |
| 座標 | 後端轉成像素 | 前端自己算 | 第 05 章 5.4 |
| `manual` | 後端派生 | 前端判斷 `state` | 規則只寫一次 |
| `index.html` | 每次讀檔 | 啟動時讀進記憶體 | 開發時免重啟 |
| 快取控制 | `no-store` + 網址加時戳 | 只做一種 | 各家瀏覽器行為不一致 |

---

## 14.7 ⚠ 已知問題

**① 多個請求之間可能不同步**

前端一次發 4~6 個請求（`Promise.allSettled`），
如果地圖剛好在中間更新，圖片和座標會來自不同時刻。

**影響**：路徑可能偏移幾個像素。因為 `/map` 更新慢、裁切只在建圖初期變，實務上看不出來。

**改法**：加一個 `map_version` 欄位，前端比對；不一致就丟掉重來。
目前不值得做。

**② `/coverage/status` 每次都重算所有座標轉換**

300 個路點 + 所有 cell，每秒重算一次。
路點在執行期間**完全不變**（`cov_path` 只在 start 時寫），所以這是純浪費。

**改法**：在 `coverage_start` 時就算好 `path_px` 存起來。
但 `meta` 會變（地圖長大時裁切偏移改變），所以要處理失效邏輯。
以 300 個點來說每次幾百微秒，不值得。

**③ 沒有任何認證**

`0.0.0.0:8080` 對整個區域網路開放，任何人都能控制機器人。
實驗室環境可接受，但**不能用在開放網路**。

---

## 14.8 ⑥ 本章重點回顧

1. ★ **路由是無狀態的讀取器**：永遠不等 ROS 資料，只讀「最近一次收到的」。
   計算在回呼那一側做完。
2. ★ **防禦性**：地圖沒好回 **503**、TF 查不到回**空陣列**、位置未知回 `null`
   —— 絕不讓單一功能的失敗擴散成整頁掛掉。
3. ★ **`/scan` 是唯一的例外**（在路由裡算），
   判準是**「消費頻率 vs 產生頻率」**：產生 5 Hz、消費 0~1 Hz，在路由算才不浪費。
4. **`Cache-Control: no-store` + 網址加時戳**，兩道保險，
   因為各家瀏覽器對快取標頭的處理不一致。
5. ★ **`manual` 是後端派生的欄位**，不讓前端自己判斷 `state`
   —— **規則只寫一次，寫在有權威的那一邊**。
6. **`/coverage/stop` 只改一個字串**就能停掉 30 分鐘的任務
   —— 共享狀態同行程的紅利。
7. ⚠ **沒有任何認證**，只適合封閉的實驗室網路。

---

## 14.9 ⑦ 自我檢核題

**Q1. 為什麼路由不用 `rospy.wait_for_message('/map', ...)` 拿最新地圖？**

<details>
<summary>參考答案</summary>

四個理由：

1. **會卡住**：`/map` 只有幾 Hz，最壞要等好幾百毫秒。
   前端每秒輪詢 4 張圖，每張都等 → 畫面更新變成每 2~3 秒一次。
2. **重複計算**：四張地圖圖層需要 3 次形態學 + 4 次 PNG 編碼。
   每個請求各做一次，等於做四遍同樣的事。
3. **不同步**：`/map.png` 和 `/map_margin.png` 會 `wait_for_message` 到**不同的兩則**訊息，
   兩張圖來自不同時刻 → 疊圖時邊界對不上。
   更糟的是 `/coverage/status` 用的 `meta` 又是第三個時刻的 → 路徑畫錯位。
4. **沒資料會拋例外**：`wait_for_message` 逾時會 raise → HTTP 500 → 前端整個圖層失敗。

**現在的做法**：`map_callback` 一次算好四張圖 + meta + data，
**在同一把鎖裡一起換掉**。所有路由讀到的必定是同一張地圖的產物。
</details>

**Q2. `/scan` 為什麼把座標轉換放在路由裡，而地圖處理放在回呼裡？判準是什麼？**

<details>
<summary>參考答案</summary>

★ **判準是「消費頻率 vs 產生頻率」**。

| | 產生頻率 | 消費頻率 | 決定 |
|---|---|---|---|
| 地圖 | `/map` ~3 Hz | 前端 1 Hz × 4 個圖層 | 在**回呼**算（一次算好，四個路由共用） |
| 雷射 | `/scan` **5 Hz** | 前端 **0~1 Hz**（圖層已移除，目前是 0） | 在**路由**算 |

**如果雷射也在回呼算**：每秒白做 5 次 × 360 個點的三角函數 + TF 查詢，
而且沒有人在看的時候也一直做。更糟的是它會**拖慢 `/scan` 的接收**，
影響 SLAM 和 `move_base`（它們也訂閱 `/scan`）。

★ 註解把這個決定寫得很清楚：

```python
def scan_callback(msg):
    """收到 /scan 時僅保存最新一筆，轉換到地圖座標延後到 /scan 路由處理。"""
```

**一般原則**：**把計算放在頻率較低的那一側。**
如果消費比產生慢 → 在消費端算（lazy）；如果消費比產生快、或多人共用 → 在產生端算（eager）。
</details>

**Q3. `st['manual'] = st['state'] != 'running'` 這一行，
為什麼不讓前端自己寫 `cov.state !== 'running'`？**

<details>
<summary>參考答案</summary>

因為那會讓**同一條規則存在於兩個地方**。

現在的規則是「只有 `running` 禁止手動遙控」。它出現在：
- 後端 `manual_allowed()`（`map_server.py:92-95`）—— 決定要不要接受 `/teleop`
- 後端 `/coverage/status` 的 `manual` 欄位 —— 決定前端 UI 要不要鎖

**兩處都在後端，而且第二處是從第一處的同一個 `state` 派生的。**

如果讓前端自己判斷，規則就跑到第三個地方（而且是不同語言、不同檔案）。

**會出什麼事**：假設未來加一個 `paused` 狀態（暫停但保留路徑）。
- 後端 `manual_allowed()` 改成 `state not in ('running', 'paused')`
- ⚠ 前端忘了改 → UI 上遙控按鈕是**啟用**的，
  使用者按下去卻收到 HTTP 409 —— 按鈕看起來能按但沒反應，最糟的 UX

★ **通用原則：規則只寫一次，寫在有權威的那一邊，其他人透過資料取得結論。**

這和第 05 章「`/map_margin.png` 直接呼叫 `apply_safety_margin`」是完全相同的思路
—— 不要讓「顯示的邏輯」和「執行的邏輯」變成兩份會走鐘的實作。
</details>

**Q4. `_serve_png` 為什麼回 503 而不是 404 或空圖片？**

<details>
<summary>參考答案</summary>

**HTTP 狀態碼有語意**，選對了前端和維運都受益：

| 碼 | 語意 | 適不適合 |
|---|---|---|
| **503 Service Unavailable** | 「服務暫時不可用，**待會再試**」 | ✅ 正是這個情況 |
| 404 Not Found | 「這個資源不存在」 | ❌ 誤導：`/map.png` 是存在的，只是還沒準備好 |
| 200 + 空圖片 | 「成功，這是圖」 | ❌ 說謊；前端無法區分「還沒好」和「地圖真的是空的」 |
| 500 Internal Error | 「伺服器出錯了」 | ❌ 這不是錯誤，是正常的啟動階段 |

**前端的配合**：

```javascript
// web/index.html:549-555
function loadImg(url) {
    return new Promise((ok, fail) => {
        const img = new Image();
        img.onload = () => ok(img); img.onerror = fail;    // ← 503 觸發 onerror
        img.src = url + '?t=' + Date.now();
    });
}
```

```javascript
// web/index.html:560-562
try { imgCache[L.id] = await loadImg(L.url); } catch {}   // ← 失敗就跳過
```

★ 失敗時 `imgCache[L.id]` **保持不變**（上一張圖還在），
所以「地圖暫時取不到」不會讓畫面閃爍成黑屏。
一開始完全沒圖時 `imgCache['orig']` 是 undefined，
`draw()` 直接 return，畫面停在「等待地圖資料…」。
</details>

**Q5. 這 12 條路由完全沒有認證。這在什麼情況下會出問題？如果要加，你會怎麼加？**

<details>
<summary>參考答案</summary>

**風險**：`app.run(host='0.0.0.0', port=8080)` 對**整個區域網路**開放。
同一個 Wi-Fi 上的任何人都可以：
- `POST /teleop` 開走機器人
- `POST /coverage/start` 啟動任務
- `POST /slam/restart` 清掉辛苦建的地圖

**什麼情況會出問題**：
- 校園 / 公司的共用 Wi-Fi（很多人在同一個網段）
- 機器人接上有對外 NAT 的網路
- 展場、比賽場地

**在封閉實驗室網路是可接受的** —— 而且加認證會讓 demo 變麻煩。

**如果要加，由簡到繁：**

1. **綁定介面**：`host='127.0.0.1'` + SSH 通道轉發。
   最安全，但手機就連不上了。
2. **共享密碼**（最務實）：Flask 的 `before_request` 檢查一個 token，
   網址帶 `?key=xxx`，或用 HTTP Basic Auth。**十行程式碼**。
3. **只保護寫入操作**：GET（看）開放，POST（控制）要密碼。
   兼顧「隨手給人看」和「不被亂控制」。★ 對本專案最合適。
4. **完整的 session / HTTPS**：對一個專題來說過度設計。

★ **另外一個更重要的防線**：`V_MAX = 0.18`、`W_MAX = 1.50`（`map_server.py:56-57`）
限制了最壞情況的破壞力，`TELEOP_TTL = 0.6` 保證斷線就停車（第 16 章）。
**就算被亂控，機器人也不會高速失控。**
</details>

---

**← 上一章** [第 13 章　move_base 任務執行](13_move_base任務執行.md)
**下一章 →** [第 15 章　前端輪詢與 Canvas 繪圖](15_前端輪詢與Canvas繪圖.md)
