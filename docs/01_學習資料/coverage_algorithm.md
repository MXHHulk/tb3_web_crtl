# 覆蓋演算法：機器人如何走遍四邊形空間並即時呈現在網頁

> 說明本專案的「牛耕式（boustrophedon）覆蓋路徑規劃」是怎麼實作的，
> 以及規劃 → 執行 → 網頁即時呈現這三件事怎麼流暢地串在一起。
> 演算法核心程式：`scripts/coverage_planner.py`（**無 ROS 依賴**，可被多個節點共用）。

---

## 一、為什麼能「走遍任意方向的四邊形」——PCA 對齊是關鍵

一般牛耕式（來回掃描，像牛耕田）最大的問題是：**掃描線該朝哪個方向？**
如果固定沿著地圖格子的水平/垂直方向掃，遇到「斜的」四邊形房間就會切出很多
零碎短線、邊角掃不乾淨。

本專案的解法是用 **PCA（主成分分析）自動找出自由空間的主軸**：

- **長軸（axis_a）** → 當作「掃描方向（sweep）」：沿著空間最長的方向來回走，線最少最順。
- **短軸（axis_b）** → 當作「換行方向（step）」：每掃完一條線，往短軸方向平移一點點。

因為軸是「從自由空間的形狀算出來的」，所以不管四邊形相對地圖是正的還是斜的，
掃描線都會自動貼齊它的長邊 → 這就是能「走遍任意方向四邊形」的原因。

```
固定水平掃（笨）              PCA 對齊掃（本專案）
┌───────────┐               ┌───────────┐
│ ─ ─ ─ ─   │  斜房間切出    │ ╲ ╲ ╲ ╲   │ 掃描線貼齊
│─ ─ ─ ─    │  很多短線、     │  ╲ ╲ ╲ ╲  │ 房間長軸，
│ ─ ─ ─ ─   │  邊角漏掃       │ ╲ ╲ ╲ ╲   │ 完整又順
└───────────┘               └───────────┘
```

---

## 二、演算法逐步拆解（`coverage_planner.py`）

### 步驟 0：輸入
`/map` 佔據柵格：`0 = 自由`、`100 = 障礙`、`-1 = 未知`，加上解析度 `res`、原點 `ox, oy`。

### 步驟 1：安全邊距膨脹 `apply_safety_margin()`
機器人有體積（直徑約 0.20 m），路徑不能貼牆走。所以先把障礙「膨脹」機器人半徑：

```python
obs  = data == 100
r    = max(1, round(margin / resolution))      # margin=0.10m, res=0.05m → r≈2 格
kern = np.ones((2*r+1, 2*r+1), bool)
return binary_dilation(obs, structure=kern)    # 障礙向外長胖 r 格
```

回到規劃端組出「真正可走的格子」：

```python
safe_obs = apply_safety_margin(data, MARGIN, res)
free     = (data == 0) & ~safe_obs             # 是自由格、且不在膨脹後障礙內
```

### 步驟 2：PCA 找主軸 `boustrophedon()`
把所有可走格的座標轉成世界座標，算共變異數矩陣的特徵向量：

```python
rows, cols = np.where(free)                    # 所有可走格
pts        = 世界座標(cols, rows)
center     = pts.mean(axis=0)
diffs      = pts - center
eigvals, eigvecs = np.linalg.eigh(np.cov(diffs.T))
axis_a = eigvecs[:, argmax(eigvals)]           # 長軸 = 掃描方向
axis_b = eigvecs[:, argmin(eigvals)]           # 短軸 = 換行方向
```

（再做符號正規化 `axis_a[0]<0 → 反向`，讓走向一致、可預期。）

### 步驟 3：把每個點投影到兩軸上
```python
proj_a = diffs @ axis_a     # 每個可走格「沿長軸」的位置
proj_b = diffs @ axis_b     # 每個可走格「沿短軸」的位置
```
之後就只在這個「旋轉過的座標系」裡思考，不必管地圖是不是斜的。

### 步驟 4：牛耕式來回掃描（產生路點）
沿短軸每隔 `spacing`（0.18 m）切一條「帶」，每條帶取長軸上的最小/最大投影，
就是這條掃描線的兩端；**方向逐條交替**（`l2r` 翻轉），形成連續的蛇行路線：

```python
b   = b_min + spacing/2              # 第一條線內縮半格，兩端對稱覆蓋
l2r = True
while b <= b_max + spacing/2:
    mask = np.abs(proj_b - b) < spacing/2       # 落在這條帶裡的格
    if mask.any():
        a_vals  = proj_a[mask]
        p_start = center + a_vals.min()*axis_a + b*axis_b   # 線的一端
        p_end   = center + a_vals.max()*axis_a + b*axis_b   # 另一端
        if l2r: waypoints += [p_start, p_end]
        else:   waypoints += [p_end, p_start]   # 反向 → 走完直接接下一條
        l2r = not l2r
    b += spacing
```

**掃描間距的巧思**：`SPACING = 0.18 m`，而機器人覆蓋寬度約 `0.20 m`，
刻意讓間距略小於寬度 → **留約 10% 重疊**，確保相鄰兩條掃描線之間不留縫、全覆蓋。

### 步驟 5：輸出
回傳 `[(world_x, world_y), ...]` 依序走訪的世界座標路點。

> **設計亮點**：整段幾乎全是 numpy 向量化運算（`np.where`、投影、遮罩），
> 沒有逐格 Python 迴圈，所以就算地圖上萬格也能瞬間算完 —— 這是「每次收到新地圖
> 都能即時重算路徑」而不卡頓的基礎。

---

## 三、規劃核心被「兩個地方」共用（低耦合設計）

`coverage_planner.py` 完全不 import rospy，是純函式模組，因此同一份演算法被兩處呼叫：

| 使用者 | 用途 | 輸出去向 |
|--------|------|----------|
| `test/boustrophedon.py`（測試工具，不隨 launch 啟動） | 收到 `/map` 就重算 | 發布 `nav_msgs/Path` 到 `/coverage_path`（給 RViz 看） |
| `map_server.py`（主節點） | 網頁按「開始覆蓋」時算一次 | 交給 move_base 導航 + 網頁畫線 |

好處：演算法只有一份、可單獨測試、換 UI（RViz / 網頁）不用改演算法。

---

## 四、從「路點」到「機器人真的走」——執行（`map_server.py`）

網頁按下「▶ 開始覆蓋」→ `POST /coverage/start`：

1. 用**當下最新地圖**跑一次 `apply_safety_margin` + `boustrophedon` 得到路點。
2. 開一條 daemon 執行緒跑 `run_coverage()`，把路點**一個一個**送給 move_base：

```python
client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
for i, (x, y) in enumerate(path):
    if 收到停止訊號: client.cancel_all_goals(); return   # 隨時可中斷
    yaw = 面向下一個路點的角度                            # 走向自然、不原地打轉
    goal = MoveBaseGoal(... x, y, yaw ...)
    client.send_goal(goal)
    while not 到達: 每 0.5 秒檢查一次停止訊號
    if 沒到達: 記錄並跳過，繼續下一點                     # 容錯：單點失敗不中斷全程
    cov_status['done'] = i                               # 更新進度給網頁
```

三個關鍵設計讓執行「流暢」：
- **朝向下一點**：每個目標的朝向設成面向下一路點，機器人走起來連貫不頓挫。
- **可隨時停**：每 0.5 秒檢查 `cov_status['state']`，按「停止」立即取消 move_base 目標。
- **容錯**：某點到不了（move_base 逾時/失敗）就記錄並跳過，不讓整趟覆蓋卡死。

避障與局部路徑交給 move_base（DWA local planner）處理，本專案只負責「給對的目標順序」。

---

## 五、為什麼能「同時即時呈現在網頁上」——三執行緒解耦

流暢的秘密是**規劃、執行、呈現三件事互不阻塞**，各跑各的：

```
主執行緒        ┌ rospy.spin()：處理 /map /odom /scan 回呼，更新記憶體
map_server ────┤
（一個節點）    ├ Flask 執行緒：回應網頁 HTTP 要求（PNG / JSON）
               └ 覆蓋執行緒：run_coverage() 送 move_base、更新 done
```

- 共享狀態（地圖、機器人位置、覆蓋進度）用 `Lock` 保護，三方安全讀寫。
- 網頁**每秒**輪詢 `/coverage/status`，後端回傳 `done`（已完成第幾點）與整條路徑的
  **像素座標**（後端先用 `world_to_px()` 換算好）。
- 前端 `drawCovPath()` 據此把**已走部分畫實線、待走部分畫虛線**，
  搭配 `/odom` 的機器人位置與軌跡、`/scan` 的即時雷射點，就成了「機器人正沿著
  規劃路徑一格格走遍空間」的即時畫面。

> 資料怎麼從節點送到網頁的完整機制，見 [`web_architecture.md`](./web_architecture.md)。
> 各 topic 收發與用途見 [`ros_topics_nodes.md`](./ros_topics_nodes.md)。

---

## 六、一頁總結：流暢的四個支柱

1. **演算法會「對齊空間」**：PCA 找主軸 → 掃描線貼齊四邊形長邊，任意方向都掃得乾淨。
2. **演算法「算得快」**：純 numpy 向量化、無 ROS 依賴 → 收到新地圖能即時重算。
3. **執行「連貫又穩」**：朝向下一點、可隨時停、單點失敗容錯，避障交給 move_base。
4. **三件事「不互相卡」**：ROS 回呼 / Flask / 覆蓋執行分三執行緒，網頁輪詢即時反映進度。

---

*本文件依 `scripts/coverage_planner.py`（演算法）、`scripts/map_server.py`（執行 + 網頁）、
`test/boustrophedon.py`（共用範例）之原始碼統整。*
