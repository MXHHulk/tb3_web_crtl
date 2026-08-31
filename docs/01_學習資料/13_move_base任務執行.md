# 第 13 章　move_base 任務執行

> **本章目標**：把 `run_coverage()` 這 63 行講透 —— 它是「一串座標」和「機器人真的動起來」之間的橋。
>
> 這一章的重點不是演算法，是**併發控制**：怎麼讓一個跑三十分鐘的背景任務
> 隨時可以被叫停、失敗了不會整組崩、而且進度隨時看得到。

---

## 13.1 ① 問題：一個「會跑很久」的任務

`/coverage/start` 這個 HTTP 請求要做的事：

```
   ① 規劃路徑（~200 ms）
   ② 依序把 300 個路點送給 move_base
   ③ 每個路點要等機器人走到（10~30 秒）
   ④ 全部走完 → 總共 30 分鐘
```

**HTTP 請求不能跑 30 分鐘。** 瀏覽器會逾時，而且使用者需要中途看進度、中途叫停。

---

## 13.2 ② 直覺做法：在路由裡直接跑完

```python
# ❌ 不能這樣寫
@app.route('/coverage/start', methods=['POST'])
def coverage_start():
    path = plan(...)
    for x, y in path:
        goto(x, y)          # 卡 30 秒
    return jsonify({'ok': True})
```

### ③ 撞牆

| 問題 | 後果 |
|---|---|
| **HTTP 逾時** | 瀏覽器等 30 分鐘一定斷線 |
| **無法看進度** | 請求沒回來之前，前端什麼都不知道 |
| **無法叫停** | 這個執行緒卡在 `goto` 裡，沒人能通知它 |
| **佔住 Flask 執行緒** | 其他請求（`/map.png`、`/robot_state`）也會被拖慢 |

---

## 13.3 ④ 現在的做法：路由「起頭」，背景執行緒「跑完」

```
   HTTP POST /coverage/start
        │
        ├─ ① 規劃（同步，~200 ms）
        ├─ ② 把結果寫進共享狀態（cov_path / cov_cells / cov_info）
        ├─ ③ 狀態改成 'running'
        ├─ ④ 開一個背景執行緒跑 run_coverage
        └─ ⑤ 立刻回覆 HTTP（總共不到 300 ms）★

   背景執行緒 run_coverage（跑 30 分鐘）
        │
        ├─ 一個一個送 Action 目標
        ├─ 每 0.5 秒檢查一次「使用者按停止了嗎」
        └─ 更新 cov_status['done']

   HTTP GET /coverage/status（前端每秒問一次）
        └─ 讀共享狀態，回傳進度
```

★ **關鍵是「控制」和「執行」分離**：
路由只負責「啟動」和「改狀態」，真正的工作在背景。
兩者透過**共享狀態 + 一把鎖**溝通。

### 啟動的那一段

```python
# scripts/map_server.py:453-497
@app.route('/coverage/start', methods=['POST'])
def coverage_start():
    with cov_lock:
        if cov_status['state'] == 'running':
            return jsonify({'ok': False, 'msg': '已在執行中'})     # ① 防重複

    with map_lock:
        meta = dict(map_meta)
        raw  = dict(map_data)                                      # ② 複製快照

    if not meta or raw.get('data') is None:
        return jsonify({'ok': False, 'msg': '地圖尚未就緒'})

    teleop_halt()                                  # ③ 交出 /cmd_vel 前先停車

    safe = apply_safety_margin(raw['data'], COV_MARGIN, meta['resolution'])
    free = (raw['data'] == 0) & ~safe

    with robot_lock:
        start = (robot_pos['x'], robot_pos['y']) if robot_pos['x'] is not None else None

    r = plan_coverage(free, meta['resolution'], meta['origin_x'], meta['origin_y'],
                      start=start)                                 # ④ 規劃
    if not r['waypoints']:
        return jsonify({'ok': False, 'msg': '無可走路徑，地圖可能不完整'})

    with robot_lock:
        robot_path.clear()          # ⑤ 先清空，再切 running，軌跡才會從這一刻開始記

    center, axis_a, _, eigvals = r['axes']
    with cov_lock:
        cov_path[:]  = r['waypoints']
        cov_cells[:] = r['cells']
        cov_info.clear()
        cov_info.update(
            n_runs     = r['n_runs'],
            n_cells    = len(r['cells']),
            n_critical = len(r['critical']),
            axis_deg   = round(math.degrees(math.atan2(axis_a[1], axis_a[0])), 1),
            ratio      = round(float(max(eigvals) / min(eigvals)), 2),
        )
        cov_status.update(state='running', done=0, total=len(r['waypoints']), msg='')

    threading.Thread(target=run_coverage, daemon=True).start()     # ⑥ 開背景執行緒
    return jsonify({'ok': True, 'total': len(r['waypoints']), **cov_info})
```

**六個細節：**

**① 防重複**：已在執行中就直接拒絕。使用者連按兩次開始按鈕不會開出兩個執行緒。

**② 複製快照**：`dict(map_data)` 是**複製**，不是引用。
之後的規劃（200 ms）完全不持鎖，`map_callback` 可以照常更新地圖。

★ **代價**：規劃用的是「按下開始那一刻」的地圖快照。
之後 SLAM 發現新空間也不會反映進去 —— 這是**刻意的**，
規劃必須基於一個固定的地圖，否則路徑會前後矛盾。

**③ `teleop_halt()`**：交出 `/cmd_vel` 控制權之前先把速度歸零。
不然機器人會帶著手動遙控的殘餘速度進入自動模式。

**⑤ 清空軌跡的順序**

```python
with robot_lock:
    robot_path.clear()          # 先清空
...
    cov_status.update(state='running', ...)   # 再切 running
```

★ 順序反了會怎樣？`odom_callback` 只在 `state == 'running'` 時記錄軌跡
（`map_server.py:193-194`）。如果先切 `running` 再清空，
中間可能已經記了幾個點，然後被清掉 —— 或更糟，清空之後又補了幾個舊點進來。

先清空再切狀態，軌跡就**保證從按下開始的那一刻起算**。

**⑥ `daemon=True`**：主程式結束時這個執行緒會被自動殺掉，
不會變成阻止程式退出的殭屍。

---

## 13.4 `run_coverage()` 逐段拆解

### 第 0 段：前置檢查

```python
# scripts/map_server.py:287-298
def run_coverage():
    """依序把路點送給 move_base，可隨時被 stop 中斷。結束時一律離開 running。"""
    if not HAS_MB:
        with cov_lock:
            cov_status.update(state='error', msg='未安裝 move_base_msgs')
        return

    client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    if not client.wait_for_server(rospy.Duration(5.0)):
        with cov_lock:
            cov_status.update(state='error', msg='move_base 未啟動（等待 5 秒逾時）')
        return
```

**`HAS_MB` 是什麼？**

```python
# scripts/map_server.py:32-38
try:
    import actionlib
    from actionlib_msgs.msg import GoalStatus
    from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
    HAS_MB = True
except ImportError:
    HAS_MB = False
```

★ **可選依賴的處理模式**：沒裝 `move_base_msgs` 的話，
其他功能（地圖顯示、手動遙控、SLAM 管理）**照常可用**，只有覆蓋執行不能用。

```python
# scripts/map_server.py:600-601
if not HAS_MB:
    rospy.logwarn('未安裝 move_base_msgs，覆蓋執行功能不可用')
```

啟動時就警告一次，按下開始時再回一次明確的錯誤訊息。

★ **`wait_for_server` 一定要設逾時**（第 03 章 3.5 講過）。
不設的話會**永遠卡住**在背景執行緒裡，網頁顯示「執行中」但機器人一動也不動，
而且完全沒有線索。

### 第 1 段：取快照

```python
# scripts/map_server.py:300-305
with cov_lock:
    path = list(cov_path)                        # ★ 複製
    fid  = map_data.get('frame_id', 'map')
    cov_status.update(state='running', total=len(path), done=0, msg='')

n = len(path)
for i, (x, y) in enumerate(path):
```

`list(cov_path)` 又是一次複製。之後 30 分鐘的迴圈都用本地的 `path`，
不需要一直持鎖。

### 第 2 段：停止檢查（每個路點的開頭）

```python
# scripts/map_server.py:308-313
with cov_lock:
    if cov_status['state'] != 'running':
        client.cancel_all_goals()
        return
    cov_status['done'] = i
```

★ 這是**第一個**停止檢查點。同一把鎖裡順便更新進度。

**注意 `!= 'running'` 而不是 `== 'stopped'`**：
不管狀態被改成什麼（`stopped`、`idle`、`error`），一律退出。
這讓「重啟 SLAM」（會把狀態改成 `stopped`）也能中斷任務。

### 第 3 段：朝向計算

```python
# scripts/map_server.py:315-321
# 朝向：面向下一個路點（最後一點保持原方向）
if i + 1 < n:
    nx, ny = path[i + 1]
    yaw = math.atan2(ny - y, nx - x)
else:
    yaw = 0.0
qz, qw = _yaw_to_quat(yaw)
```

**為什麼要指定朝向？**

`MoveBaseGoal` 的目標是一個**位姿**（位置 + 朝向），不只是位置。
如果不指定，預設朝向是 0°（面向地圖的 +x 方向）。

★ **後果**：機器人每到一個路點都要**原地轉到 0°**，然後才走下一段。
一條掃描線有兩個端點、300 個路點 = **300 次無意義的原地轉圈**。

**現在的做法**：讓它面向**下一個路點的方向**，走到就已經對準了，直接繼續。

```
   ●────────────→●          走到終點時已經面向右
                  ╲
                   ↘        下一個路點在右下 → 目標朝向設成右下
                    ●
```

```python
# scripts/map_server.py:282-284
def _yaw_to_quat(yaw):
    """偏航角 → 四元數 (z, w)。"""
    return math.sin(yaw / 2), math.cos(yaw / 2)
```

（第 02 章 2.3 講過：只繞 z 軸旋轉時，四元數只有 z 和 w 非零。）

> ⚠ **最後一點設 `yaw = 0.0` 是一個小瑕疵**。
> docstring 寫「保持原方向」，但實際上是設成絕對角度 0°，
> 所以機器人走完最後一個路點還是會轉一次。
> 影響很小（只有一次），但嚴格說 docstring 和行為不完全一致。

### 第 4 段：送目標

```python
# scripts/map_server.py:323-330
goal = MoveBaseGoal()
goal.target_pose.header.frame_id    = fid          # ★ 'map'，不是 'odom'
goal.target_pose.header.stamp       = rospy.Time.now()
goal.target_pose.pose.position.x    = x
goal.target_pose.pose.position.y    = y
goal.target_pose.pose.orientation.z = qz
goal.target_pose.pose.orientation.w = qw
client.send_goal(goal)
```

★ `frame_id` 取自 `/map` 訊息的 header（`map_server.py:302`），不是寫死的字串。
理由見第 03 章 3.9 的 Q5。

### 第 5 段：可中斷的等待 ★

```python
# scripts/map_server.py:332-339
# 等待到達，每 0.5 秒檢查一次停止訊號
while not rospy.is_shutdown():
    with cov_lock:
        if cov_status['state'] != 'running':
            client.cancel_all_goals()
            return
    if client.wait_for_result(rospy.Duration(0.5)):
        break
```

★ **這是本章最重要的模式：把長時間等待切成可中斷的小段。**

```
   ❌ client.wait_for_result()           卡 30 秒，期間無法反應
   ✅ 迴圈 { 檢查停止; 等 0.5 秒 }       最多 0.5 秒就能反應
```

`wait_for_result(Duration(0.5))` 的回傳值是「這 0.5 秒內有沒有拿到結果」：
- `True` → 到了（或失敗了）→ `break` 出去
- `False` → 還沒到 → 回到迴圈頂端再檢查一次停止訊號

**`rospy.is_shutdown()`** 讓 Ctrl+C 也能中斷這個迴圈。

### 第 6 段：失敗容錯

```python
# scripts/map_server.py:341-345
# 失敗容錯：未成功到達則記錄並繼續下一點
if client.get_state() != GoalStatus.SUCCEEDED:
    rospy.logwarn(f'[coverage] 路點 {i+1}/{n} 跳過（move_base 狀態碼 {client.get_state()}）')
    with cov_lock:
        cov_status['msg'] = f'路點 {i+1}/{n} 跳過（無法到達）'
    # ★ 沒有 return，繼續下一個路點
```

第 03 章 3.5 詳細討論過這個取捨。快速回顧：

- **選擇**：跳過繼續，不中止整趟
- **理由**：300 個路點裡有一兩個到不了是正常的
- ⚠ **代價**：覆蓋率悄悄下降，而且最後仍顯示「完成」

### 第 7 段：收尾

```python
# scripts/map_server.py:347-349
with cov_lock:
    if cov_status['state'] == 'running':
        cov_status.update(state='done', done=n)
```

★ **`if state == 'running'` 這個檢查很重要**。

如果使用者在最後一個路點按了停止，狀態已經是 `stopped`，
這時不該把它改成 `done`（那會顯示「覆蓋完成 ✓」，但其實是被中斷的）。

---

## 13.5 ★ 狀態機

```
                  ┌──────────┐
        ┌────────→│   idle   │←──────────┐
        │         └────┬─────┘           │
        │              │ POST            │ POST /slam/restart
        │              │ /coverage/start │
        │              ↓                 │
        │         ┌──────────┐           │
        │    ┌────│ running  │────┐      │
        │    │    └────┬─────┘    │      │
        │    │         │          │      │
   POST │    │ 全部走完 │    找不到 move_base
   /stop│    │         │          │ 或未安裝
        │    ↓         ↓          ↓      │
   ┌────┴────┐   ┌──────────┐  ┌───────┐ │
   │ stopped │   │   done   │  │ error │─┘
   └─────────┘   └──────────┘  └───────┘
        │             │            │
        └─────────────┴────────────┴──→ 都可以再按 start 回到 running
```

| 狀態 | 意思 | 可手動遙控 | 網頁顯示 |
|---|---|---|---|
| `idle` | 閒置 | ✅ | 手動模式 |
| `running` | 執行中 | ❌ | 覆蓋執行中 |
| `stopped` | 被中斷 | ✅ | 已結束（手動模式） |
| `done` | 正常完成 | ✅ | 覆蓋完成（手動模式） |
| `error` | 出錯 | ✅ | 錯誤 |

```python
# scripts/map_server.py:92-95
def manual_allowed():
    """手動遙控是否被允許（覆蓋執行中一律禁止）。"""
    with cov_lock:
        return cov_status['state'] != 'running'
```

★ **只有 `running` 禁止遙控，其他狀態一律允許。**
這個「白名單只有一項」的寫法是刻意的 ——
未來加新狀態時，預設是「可以遙控」，這是比較安全的預設值
（機器人卡住時，使用者總是能手動把它救出來）。

★ **`run_coverage` 的每一條退出路徑都會離開 `running`**：
- 未安裝 / 找不到 server → `error`
- 停止訊號 → 呼叫方已經改成 `stopped`
- 正常走完 → `done`

**沒有任何一條路徑會讓狀態卡在 `running`** —— 這保證了「按了停止一定能解鎖手動」。

---

## 13.6 ⑤ 設計決策

| 決策 | 選了 | 否決了 | 理由 |
|---|---|---|---|
| 執行方式 | 背景執行緒 | 在路由裡跑完 | HTTP 會逾時、無法叫停 |
| 進度回報 | 前端輪詢 `/coverage/status` | Server-Sent Events / WebSocket | 1 Hz 夠用，實作簡單（第 05 章） |
| 停止機制 | 改共享狀態，執行緒自己檢查 | `thread.kill()` | Python 沒有安全的殺執行緒方法 |
| 等待方式 | 0.5 秒一段的迴圈 | 無限 `wait_for_result()` | 要能及時響應停止 |
| 路點失敗 | 記錄後繼續 | 中止整趟 / 重試 | ⚠ 見第 03 章 3.5 與 3.9 Q4 |
| 朝向 | 面向下一個路點 | 不指定（預設 0°） | 避免 300 次無意義的原地轉圈 |
| 規劃時機 | 按下開始時算一次 | 邊走邊重新規劃 | 路徑要固定，否則前後矛盾 |

---

## 13.7 ⚠ 已知問題

**① 規劃是一次性快照**

按下開始之後，SLAM 就算發現新空間也不會重新規劃。
如果一開始地圖不完整，就會出現「走完了但還有一大塊沒去」（第 19 章）。

**② 跳過的路點沒有統計**

`cov_status['msg']` 只保留**最後一則**跳過訊息，前面的會被覆寫。
沒有 `skipped` 計數，最後也不會回報。

**③ `daemon=True` 的執行緒不會被等待**

程式結束時如果任務還在跑，執行緒會被直接殺掉，
`client.cancel_all_goals()` 不會被呼叫 —— `move_base` 可能還在走最後一個目標。

（實務上 `rospy.on_shutdown(slam_kill)` 會把 SLAM 收掉，
`move_base` 失去 `/map` 和 TF 之後也會停，所以不會失控。）

**④ 只有一個 Action Client，每次執行都重建**

`run_coverage` 每次被呼叫都 `SimpleActionClient(...)` + `wait_for_server(5)`。
連續啟停時，每次都要重新等 5 秒（如果 server 剛好忙）。可以快取，但不是瓶頸。

---

## 13.8 ⑥ 本章重點回顧

1. ★ **控制與執行分離**：HTTP 路由只負責「啟動 + 改狀態」（<300 ms 就回覆），
   真正的工作在背景執行緒，兩者透過**共享狀態 + 一把鎖**溝通。
2. **`dict(map_data)` / `list(cov_path)` 都是複製**：取完快照就放鎖，
   之後的長時間運算完全不持鎖。
3. ★ **停止機制不能用 `thread.kill()`**（Python 沒有安全的做法），
   必須改共享狀態、讓執行緒**自己主動檢查**。
4. ★ **長時間等待要切成可中斷的小段**：`wait_for_result(Duration(0.5))` 放在迴圈裡，
   反應延遲壓在 0.5 秒內。
5. **朝向設成「面向下一個路點」**，避免 300 次無意義的原地轉圈。
6. ★ **`run_coverage` 的每一條退出路徑都會離開 `running`**，
   保證「按停止一定能解鎖手動遙控」。收尾時的 `if state == 'running'`
   避免把「被中斷」誤標成「完成」。
7. **`HAS_MB` 是可選依賴的處理模式**：缺套件時只讓該功能不可用，其他照常。

---

## 13.9 ⑦ 自我檢核題

**Q1. 為什麼不能用 `thread.kill()` 來停止覆蓋任務？**

<details>
<summary>參考答案</summary>

**Python 沒有提供安全的「從外部殺死執行緒」的方法。**

（`threading` 模組刻意不提供 `kill()`；有些 hack 用 `ctypes` 注入例外，但不可靠。）

**根本原因**：執行緒被強制中止時，它可能正在：
- **持有一把鎖** → 鎖永遠不會被釋放 → **整個程式死鎖**
- 寫到一半的共享狀態 → 資料不一致
- 持有 Action Client 的內部狀態 → `move_base` 那邊還以為有個目標在跑

**正確的模式（本專案採用）**：**協作式取消（cooperative cancellation）**

```python
# 呼叫方：只是設一個旗標
with cov_lock:
    cov_status['state'] = 'stopped'

# 執行方：在安全的地方主動檢查
with cov_lock:
    if cov_status['state'] != 'running':
        client.cancel_all_goals()      # 自己做好收尾
        return                          # 自己乾淨地退出
```

★ 執行緒**自己決定在哪裡退出**，所以它一定是在一個安全的點退出，
而且有機會做收尾（取消 Action 目標）。

代價是「反應不是瞬間的」—— 本專案把這個延遲壓在 0.5 秒內。
</details>

**Q2. 如果把 `client.wait_for_result(rospy.Duration(0.5))` 改成
`client.wait_for_result()`（無限等待），使用者按停止會發生什麼？**

<details>
<summary>參考答案</summary>

**按下停止之後，機器人會繼續走完當前這個路點才停。**

流程：
1. 使用者按停止 → `/coverage/stop` 把 `cov_status['state']` 改成 `'stopped'`
2. 但 `run_coverage` 執行緒**卡在 `wait_for_result()` 裡面**，看不到這個改變
3. 要等 `move_base` 回報結果（走到、或失敗）才會回到迴圈頂端
4. 這時才發現狀態變了 → 退出

**延遲多久**：一個路點可能要走 10~30 秒。如果那個路點剛好到不了，
`move_base` 會試各種恢復行為（原地轉圈、清 costmap、後退），可能要**一兩分鐘**才放棄。

**使用者體感**：按了停止，機器人繼續動、網頁還顯示「執行中」——
和當機沒兩樣，很可能會去按第二次、第三次，或直接拔電源。

**現在的寫法**：迴圈每 0.5 秒醒來一次檢查，反應延遲 **≤ 0.5 秒**。
</details>

**Q3. 為什麼要在 `run_coverage` 的最後檢查 `if cov_status['state'] == 'running'`
才改成 `done`？**

<details>
<summary>參考答案</summary>

因為**有可能任務不是「正常走完」的**。

考慮這個時序：

```
   T1: 機器人走到最後一個路點
   T2: 使用者按下停止 → state = 'stopped'
   T3: 迴圈跑完，執行到收尾程式碼
```

如果收尾無條件寫 `cov_status.update(state='done')`：
- 網頁會顯示「**覆蓋完成 ✓　共 N 個路點**」（`web/index.html:532`）
- 但使用者明明按了停止，而且中間可能還有路點沒走

★ **這會讓使用者誤以為任務成功完成**，而實際上是被中斷的。

加了 `if state == 'running'` 之後：
- 正常走完 → 那時狀態還是 `running` → 改成 `done` ✓
- 被停止 → 狀態已經是 `stopped` → **保持 `stopped`** ✓
- 出錯 → 狀態是 `error` → 保持 `error` ✓

★ **通用原則：狀態機的終態轉移要檢查「我是從預期的狀態來的嗎」**，
不能無條件覆寫 —— 否則會把別人設好的狀態蓋掉。
</details>

**Q4. `goal.target_pose.pose.orientation` 如果完全不設（保持預設），
機器人的行為會有什麼不同？**

<details>
<summary>參考答案</summary>

四元數的預設值是 `(x,y,z,w) = (0,0,0,0)`。

★ 這其實是一個**無效的四元數**（模長為 0）。`move_base` 通常會拒絕這種目標
（回 `REJECTED`）或印警告。如果是 `w=1` 的預設（單位四元數），代表朝向 **0°**
（面向地圖的 +x 方向）。

假設是後者，行為會變成：

```
   ●────────────→●     走到終點
                 ↻     原地轉到 0°（因為目標朝向是 0°）
                 ↓
   ●←────────────●     再往回走 → 又要轉 180°
                 ↻
```

**每個路點都要原地轉一次**。300 個路點 = **300 次原地轉圈**。

以 Burger 的角速度 1.5 rad/s 估算，轉半圈約 2 秒，
300 次就是 **10 分鐘的純轉圈時間** —— 而且完全沒有覆蓋價值。

**現在的做法**：朝向設成 `atan2(下一點 - 這一點)`，
機器人走到終點時**已經對準下一段的方向**，可以直接繼續走。
</details>

**Q5. `/coverage/start` 用 `dict(map_data)` 取快照。
如果改成直接用 `map_data`（不複製）會有什麼風險？**

<details>
<summary>參考答案</summary>

**`map_data` 是一個全域 dict，`map_callback` 隨時會整個換掉它**：

```python
# scripts/map_server.py:181-185
with map_lock:
    ...
    map_data = dict(data=data, h=h, w=w, frame_id=...)   # ★ 重新綁定
```

不複製的話：

```python
with map_lock:
    raw = map_data          # ❌ 只是拿到同一個 dict 的引用
# 鎖已放開

safe = apply_safety_margin(raw['data'], ...)   # ← 這裡 raw 可能已經是舊物件
free = (raw['data'] == 0) & ~safe              # ← 或者中間被換掉了
```

**具體風險**：

1. **兩次 `raw['data']` 拿到不同的陣列**：
   雖然 `map_data` 被重新綁定時 `raw` 仍指向舊的 dict（Python 的重新綁定不影響已存在的引用），
   所以這個特定情況其實**是安全的** —— 但這是靠「剛好重新綁定而不是原地修改」的巧合。

2. ⚠ **如果哪天有人把 `map_callback` 改成原地更新**（`map_data['data'] = ...`
   而不是 `map_data = dict(...)`），這段程式碼就會**立刻出現競態**，
   而且是那種「跑一百次才錯一次」的競態。

3. **同樣的問題出現在 `meta`**：`map_meta` 和 `map_data` 必須是同一時刻的
   （解析度、原點要對應同一張地圖）。分別取引用的話就沒有這個保證。

★ **`dict(...)` 複製的真正價值是「解除對未來修改方式的依賴」**：
不管 `map_callback` 以後怎麼改，這裡拿到的都是一份不會變的快照。

這種「防禦性複製」的成本很低（一個小 dict），換來的是**不會被別人的改動咬到**。
</details>

---

**← 上一章** [第 12 章　路徑生成與排序](12_路徑生成與排序.md)
**下一章 →** [第 14 章　後端 Flask 路由設計](14_後端Flask路由設計.md)
