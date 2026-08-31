# 第 15 章　前端輪詢與 Canvas 繪圖

> **本章目標**：把 `web/index.html` 的 JavaScript 部分（約 370 行）講清楚。
>
> 這個前端有一個很值得學的特性：**它完全沒有數學**（除了一個除法）。
> 所有座標轉換都在後端做完了，前端只做兩件事：**畫圖**和**送指令**。

---

## 15.1 ① 問題：怎麼把後端的資料變成畫面

後端提供的東西：

```
   /map.png          灰階 PNG（黑=障礙、白=空地、灰=未知）
   /map_margin.png   同上，但障礙已膨脹
   /robot_state      { pos: {x, y, wx, wy}, path: [[px,py], ...] }
   /coverage/status  { state, done, total, path_px, cells_px, info, manual }
```

要畫成一張疊了六個圖層的圖，而且每秒更新。

---

## 15.2 ② 直覺做法：用 `<img>` 標籤直接顯示

```html
<!-- ❌ 最直覺 -->
<img src="/map.png">
```

### ③ 撞牆

| 問題 | 為什麼 |
|---|---|
| **只能顯示一張圖** | 六個圖層要疊在一起 |
| **無法在上面畫線** | 路徑、軌跡、cell 都是向量圖形 |
| **無法著色** | 膨脹層要用紅色疊在原始地圖上，但 PNG 是灰階的 |
| **無法縮放對齊** | 圖層之間的像素要精確對齊 |

**結論**：需要 `<canvas>`。

---

## 15.3 ④ 現在的做法：Canvas 疊圖

### 整體結構

```
   每秒一次 refresh()
        │
        ├─ 平行抓：地圖 PNG ×N、/robot_state、/coverage/status
        │           （Promise.allSettled，任何一個失敗都不影響其他）
        ├─ 更新全域變數 robot、cov
        ├─ updateUI()   ← 更新按鈕、進度條、狀態文字、診斷數字
        └─ draw()       ← 重畫整個 canvas
              │
              ├─ ① 清底色
              ├─ ② 畫原始地圖（不透明）
              ├─ ③ 畫其他 map 圖層（colorize 後半透明疊上）
              ├─ ④ drawCells()      cell 分解（每個 cell 一種顏色）
              ├─ ⑤ drawCovPath()    覆蓋路徑（已走實線 / 待走虛線）
              ├─ ⑥ drawTrail()      行走軌跡（漸層淡出）
              └─ ⑦ drawRobot()      機器人圖示
```

### 圖層定義：資料驅動的 UI

```javascript
// web/index.html:216-223
const LAYERS = [
    { id: 'orig',    label: '原始地圖',       color: '#c9d1d9', type: 'map',   url: '/map.png',        on: true },
    { id: 'margin',  label: '安全邊距（膨脹）', color: '#ff7b72', type: 'map',   url: '/map_margin.png', on: true },
    { id: 'cells',   label: 'cell 分解',      color: '#7ee787', type: 'cells', on: true },
    { id: 'covpath', label: '覆蓋路徑',       color: '#c084fc', type: 'path',  on: true },
    { id: 'trail',   label: '行走軌跡',       color: '#e3b341', type: 'trail', on: true },
    { id: 'robot',   label: '機器人',         color: '#3fb950', type: 'robot', on: true },
];
```

★ **這一個陣列同時驅動三件事**：

```javascript
// ① 側欄的圖層開關按鈕（web/index.html:239-246）
$('layers').append(...LAYERS.map(L => {
    const b = document.createElement('button');
    b.className = 'layer-btn' + (L.on ? '' : ' off');
    b.style.setProperty('--sw', L.color);
    b.innerHTML = `<span class="dot"></span>${L.label}`;
    b.onclick = () => { L.on = !L.on; b.classList.toggle('off', !L.on); draw(); };
    return b;
}));

// ② 要抓哪些圖片（web/index.html:560）
LAYERS.filter(l => l.type === 'map' && (l.on || l.id === 'orig'))

// ③ 畫圖的順序與顏色（web/index.html:290-308）
for (const L of LAYERS) { ... }
```

> 💡 **要新增一個圖層，只要在這個陣列加一筆。**
> 按鈕、抓取、繪製全部自動處理。
> （2026-08-17 那次「移除雷射與侵蝕圖層」的改動，主要就是刪掉兩筆而已。）

★ 注意 `(l.on || l.id === 'orig')` —— **原始地圖一律載入**，即使圖層關掉了。
因為 canvas 的尺寸靠它決定（`web/index.html:284-285`）。

### `colorize()`：把灰階 PNG 變成半透明色層

```javascript
// web/index.html:262-278
function colorize(img, hex) {
    const c = document.createElement('canvas');
    c.width = img.naturalWidth; c.height = img.naturalHeight;
    const cx = c.getContext('2d');
    cx.drawImage(img, 0, 0);
    const id = cx.getImageData(0, 0, c.width, c.height), d = id.data;
    const [r, g, b] = hexToRgb(hex);
    for (let i = 0; i < d.length; i += 4) {
        const v = d[i];
        if      (v < 80)  { d[i]=r; d[i+1]=g; d[i+2]=b; d[i+3]=200; }   // 障礙 → 著色
        else if (v > 180) { d[i+3] = 0; }                                // 空地 → 透明
        else              { d[i]=55; d[i+1]=55; d[i+2]=75; d[i+3]=40; } // 未知 → 淡灰
    }
    cx.putImageData(id, 0, 0);
    return c;
}
```

**逐像素改寫 RGBA**：

```
   灰階值 v          原本代表        改成
   ─────────────────────────────────────────────
   v < 80            障礙（黑）      指定顏色，alpha=200（不透明）
   v > 180           空地（白）      ★ alpha=0（完全透明，讓底下的原始地圖露出來）
   80 <= v <= 180    未知（128 灰）  暗藍灰，alpha=40（很淡）
```

★ **關鍵是「空地要變透明」**。
如果不做，膨脹圖層會把整張原始地圖蓋掉，看不到底下的細節。

**`d` 是一個 `Uint8ClampedArray`**，每 4 個元素是一個像素的 `[R, G, B, A]`：

```
   d = [R₀,G₀,B₀,A₀, R₁,G₁,B₁,A₁, R₂,G₂,B₂,A₂, ...]
        └─像素 0──┘  └─像素 1──┘  └─像素 2──┘
```

所以迴圈是 `i += 4`，而 `d[i]` 就是紅色通道（灰階圖三個通道值相同，取一個就好）。

> ⚠ **效能**：一張 100×60 的圖是 6,000 個像素 = 24,000 次陣列存取，
> 每秒做一次（每個開啟的非原始圖層各一次）。
> 現代瀏覽器完全無感，但如果地圖變成 800×600（48 萬像素），就會開始掉幀。
>
> **改進方向**：把 `colorize` 的結果快取起來，只在圖片真的換了才重算。
> 目前圖片每秒都換，所以快取沒有意義。

### `draw()`：疊圖的順序

```javascript
// web/index.html:280-309
function draw() {
    const orig = imgCache['orig'];
    if (!orig) return;                                    // ① 沒有底圖就不畫

    const W = orig.naturalWidth, H = orig.naturalHeight;
    if (canvas.width !== W || canvas.height !== H) {       // ② 尺寸變了才重設
        canvas.width = W; canvas.height = H; fitCanvas();
    }

    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, W, H);                              // ③ 清底

    for (const L of LAYERS) {                              // ④ 地圖類圖層
        if (L.type !== 'map' || !L.on || !imgCache[L.id]) continue;
        if (L.id === 'orig') {
            ctx.globalAlpha = 1;
            ctx.drawImage(imgCache[L.id], 0, 0, W, H);     // 原始圖：不透明
        } else {
            ctx.globalAlpha = 0.8;
            ctx.drawImage(colorize(imgCache[L.id], L.color), 0, 0, W, H);
            ctx.globalAlpha = 1;
        }
    }

    if (layerOn('cells')   && cov.cells_px.length)  drawCells(cov.cells_px);
    if (layerOn('covpath') && cov.path_px.length > 1) drawCovPath(...);
    if (layerOn('trail')   && robot.path.length > 1)  drawTrail(...);
    if (layerOn('robot')   && robot.pos)              drawRobot(...);
}
```

★ **② `canvas.width = W` 這行有副作用**：設定 canvas 的 width/height 屬性會
**清空整個畫布並重設所有繪圖狀態**。所以只在尺寸真的變了才做
（不然每次都會多做一次清空）。

★ **繪製順序 = 疊圖順序**，後畫的蓋在上面。機器人最後畫，永遠在最上層。

### `fitCanvas()`：縮放但不失真

```javascript
// web/index.html:251-257
function fitCanvas() {
    if (!canvas.width) return;
    const s = Math.min((mainEl.clientWidth - 20) / canvas.width,
                       (mainEl.clientHeight - 20) / canvas.height);
    canvas.style.width  = Math.round(canvas.width  * s) + 'px';
    canvas.style.height = Math.round(canvas.height * s) + 'px';
}
```

★ **關鍵區別**：
- **`canvas.width`（屬性）** = 畫布的實際像素數，繪圖座標用這個
- **`canvas.style.width`（CSS）** = 顯示大小，瀏覽器負責縮放

所以**繪圖永遠用地圖的原始像素座標**（後端傳來的就是這個），
顯示大小由 CSS 控制。前端完全不需要處理縮放。

搭配 CSS：

```css
/* web/index.html:61 */
#canvas { display: block; image-rendering: pixelated; }
```

`image-rendering: pixelated` 讓放大時保持方格邊緣清晰，
而不是模糊的雙線性插值 —— 對格子地圖來說看得更清楚。

---

## 15.4 四個繪製函式

### `drawCells()`：cell 分解視覺化

```javascript
// web/index.html:312-349
function drawCells(cells) {
    ctx.save();
    cells.forEach((wps, ci) => {
        const color = CELL_COLORS[ci % CELL_COLORS.length];   // ① 輪用配色

        // ② cell 內換行接駁（細虛線）
        ctx.strokeStyle = color; ctx.globalAlpha = 0.35;
        ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
        for (let i = 1; i + 1 < wps.length; i += 2) { ... }    // ★ 奇數起

        // ③ 掃描線本身（粗實線）
        ctx.setLineDash([]); ctx.globalAlpha = 0.9;
        ctx.lineWidth = 2.4; ctx.lineCap = 'round';
        for (let i = 0; i + 1 < wps.length; i += 2) { ... }    // ★ 偶數起

        // ④ 走訪順序標籤（放在該 cell 的重心）
        const cx = wps.reduce((s, p) => s + p[0], 0) / wps.length;
        const cy = wps.reduce((s, p) => s + p[1], 0) / wps.length;
        ctx.strokeText(String.fromCharCode(65 + ci), cx, cy);  // 黑色描邊
        ctx.fillText(String.fromCharCode(65 + ci), cx, cy);    // 彩色填充
    });
    ctx.restore();
}
```

★ **② 和 ③ 用的正是第 12 章講的路點結構約定**：

```
   index:  0    1    2    3    4    5
           ●────●    ●────●    ●────●        偶數→奇數 = 掃描線（粗實線）
                └────┘    └────┘             奇數→偶數 = 換行接駁（細虛線）
```

**視覺效果**：一眼就能分辨「哪些是真正在掃的」和「哪些是空跑的接駁」。

★ **④ 的 `String.fromCharCode(65 + ci)`** 把 cell 索引變成 `A`, `B`, `C`...
放在 cell 的重心，**直接顯示走訪順序**（`cells_px` 已經是排序後的）。

**先 `strokeText`（黑色描邊）再 `fillText`（彩色）** 是文字在複雜背景上的標準做法，
不然淺色字在白色空地上會看不見。

```javascript
// web/index.html:226-227
const CELL_COLORS = ['#7ee787', '#79c0ff', '#ffa657', '#d2a8ff',
                     '#f778ba', '#56d4dd', '#e3b341', '#ff7b72'];
```

8 種顏色輪用（`ci % 8`），讓相鄰 cell 明顯不同色。

> ⚠ 第 22 章的斜置 30° 會分解出 **23 個 cell**，顏色會重複 3 輪 ——
> 這時畫面會變得很花，而那正是「出問題了」的視覺訊號。

### `drawCovPath()`：已走實線 / 待走虛線

```javascript
// web/index.html:351-367
function drawCovPath(pts, color, done) {
    ctx.save();
    if (done > 1) {                                   // 已走：實線
        ctx.globalAlpha = 0.85; ctx.lineWidth = 1.8; ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
        for (let i = 1; i < Math.min(done, pts.length); i++) ctx.lineTo(pts[i][0], pts[i][1]);
        ctx.stroke();
    }
    const from = Math.max(0, done - 1);               // 待走：虛線
    ctx.globalAlpha = 0.25; ctx.lineWidth = 1.2; ctx.setLineDash([4, 5]);
    ctx.beginPath(); ctx.moveTo(pts[from][0], pts[from][1]);
    for (let i = from + 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.stroke();
    ctx.setLineDash([]); ctx.restore();
}
```

★ **`from = done - 1` 而不是 `done`**：讓虛線從**已走的最後一點**開始，
兩段線才會接在一起，不會有一個缺口。

`done` 來自 `cov_status['done']`（`map_server.py:313`），是「正在走第幾個路點」。

### `drawTrail()`：漸層淡出的軌跡

```javascript
// web/index.html:369-388
function drawTrail(path, color) {
    const FADE = 300, n = path.length, f = Math.max(0, n - FADE);
    ctx.save(); ctx.lineJoin = 'round';
    if (f > 1) {                          // ① 老舊的部分：一次畫完，固定淡
        ctx.globalAlpha = 0.22; ctx.lineWidth = 1.5;
        ctx.moveTo(path[0][0], path[0][1]);
        for (let i = 1; i <= f; i++) ctx.lineTo(path[i][0], path[i][1]);
        ctx.stroke();
    }
    for (let i = Math.max(f, 1); i < n; i++) {   // ② 最近 300 點：逐段漸層
        ctx.beginPath();
        ctx.globalAlpha = 0.22 + 0.78 * ((i - f) / Math.max(FADE, 1));
        ctx.lineWidth = 2;
        ctx.moveTo(path[i-1][0], path[i-1][1]);
        ctx.lineTo(path[i][0],   path[i][1]);
        ctx.stroke();
    }
    ctx.restore();
}
```

★ **效能與美觀的取捨**：

- **最近 300 點**：**每一段都是獨立的 `beginPath`/`stroke`**（因為每段透明度不同）
  → 300 次繪製呼叫
- **更早的部分**：全部用同一個透明度，**一次 `stroke` 畫完**
  → 1 次繪製呼叫

軌跡上限是 10,000 點（`map_server.py:206-207`）。
如果每一段都獨立畫，就是 10,000 次繪製呼叫 —— 每秒做一次，畫面會卡。

**視覺效果**：越近走過的越亮，越舊的越淡，一眼看出機器人的行進方向。

### `drawRobot()`：按實際尺寸畫

```javascript
// web/index.html:390-397
function drawRobot(px, py, color) {
    const r = Math.max(1, 0.105 / (robot.resolution || 0.05));   // ★ 唯一的數學
    ctx.save();
    ctx.shadowColor = color; ctx.shadowBlur = 6;
    ctx.fillStyle = color;
    ctx.beginPath(); ctx.arc(px, py, r, 0, 2*Math.PI); ctx.fill();
    ctx.restore();
}
```

`0.105`（機器人半徑，公尺）÷ `resolution`（公尺/格）= **半徑幾個像素**。

★ 這樣機器人圖示的大小是**真實比例**的 —— 你可以直接從畫面上判斷
「這個縫隙機器人過不過得去」。用固定像素半徑就沒有這個資訊。

---

## 15.5 ★ 輪詢：`refresh()`

```javascript
// web/index.html:557-584
async function refresh() {
    const [, robotRes, covRes] = await Promise.allSettled([
        // orig 一律載入：canvas 的尺寸靠它決定，關掉圖層也還是要有
        Promise.all(LAYERS.filter(l => l.type === 'map' && (l.on || l.id === 'orig')).map(async L => {
            try { imgCache[L.id] = await loadImg(L.url); } catch {}
        })),
        fetch('/robot_state').then(r => r.json()),
        fetch('/coverage/status').then(r => r.json()),
    ]);

    if (robotRes.status === 'fulfilled') robot = robotRes.value;
    if (covRes.status   === 'fulfilled') cov   = covRes.value;
    ...
    updateUI();
    draw();
    ...
}

refresh();                      // 立刻跑一次，不要等第一秒
setInterval(refresh, 1000);     // 之後每秒一次
```

### ★ `Promise.allSettled` vs `Promise.all`

| | 行為 |
|---|---|
| `Promise.all` | **任何一個失敗，整個 reject** —— 其他成功的結果也拿不到 |
| `Promise.allSettled` | **等全部有結果**，每個各自回報 `fulfilled` / `rejected` |

★ **為什麼一定要用 `allSettled`**：

系統啟動時，`/map.png` 會回 503（地圖還沒好），但 `/coverage/status` 是正常的。
用 `Promise.all` 的話，圖片失敗會讓整個 `refresh` 拋例外 →
**狀態列、按鈕、進度全部停止更新**，畫面完全凍結。

用 `allSettled` 之後：圖片失敗就失敗，狀態照常更新，
使用者至少看得到「手動模式」和時鐘在跳。

### 三層防禦

```javascript
// ① 每張圖片自己的 try/catch
try { imgCache[L.id] = await loadImg(L.url); } catch {}

// ② allSettled 讓三組請求互不影響

// ③ 只在成功時才覆蓋全域變數
if (robotRes.status === 'fulfilled') robot = robotRes.value;
```

★ **③ 很重要**：失敗時 `robot` **保持上一次的值**，
所以機器人圖示不會閃爍消失，只是暫時不更新。

### 為什麼是 1 Hz？

- 機器人最高 **0.22 m/s** → 一秒最多移動 22 公分
- 地圖 `/map` 本身也只有幾 Hz
- **每秒 4~6 個 HTTP 請求**，對 Wi-Fi 和樹莓派都很輕鬆

★ 對照：遙控的續傳是 **150 ms**（第 16 章）——
**因為那個需要即時反應，這個只是監看。不同需求給不同頻率。**

---

## 15.6 `updateUI()`：狀態驅動介面

```javascript
// web/index.html:499-544
const STATE_LABEL = {
    idle:    ['手動模式', 'manual'],
    running: ['覆蓋執行中', 'running'],
    stopped: ['已結束（手動模式）', 'manual'],
    done:    ['覆蓋完成（手動模式）', 'manual'],
    error:   ['錯誤', 'error'],
};

function updateUI() {
    const [label, cls] = STATE_LABEL[cov.state] ?? [cov.state, 'manual'];  // ① 未知狀態的退路
    $('mode-badge').textContent = label;
    $('mode-badge').className = 'badge ' + cls;

    $('btn-start').disabled = !cov.manual;        // ② 用後端派生的 manual
    $('btn-stop').disabled  = cov.manual;
    // btn-slam 的 disabled 由它自己的點擊處理器管理，這裡不要覆蓋  ★

    for (const b of $('pad').children) b.disabled = !cov.manual;
    $('speed').disabled = !cov.manual;
    ...
    if (wasManual && !cov.manual) teleopRelease();   // ③ 剛被鎖住 → 清掉續傳
    wasManual = cov.manual;

    const I = cov.info || {};                        // ④ 演算法診斷
    $('i-runs').textContent  = I.n_runs     ?? '—';
    $('i-crit').textContent  = I.n_critical ?? '—';
    $('i-cells').textContent = I.n_cells    ?? '—';
    $('i-axis').textContent  = I.axis_deg !== undefined ? I.axis_deg + '°' : '—';
    $('i-ratio').textContent = I.ratio      ?? '—';
}
```

**① `?? [cov.state, 'manual']`**：後端如果回一個前端不認得的狀態，
就直接顯示那個字串，而不是變成 `undefined`。**向前相容**。

**② 用 `cov.manual`，不自己判斷 `state`**（第 14 章 14.9 Q3 講過）。

**★ 註解提醒不要覆蓋 `btn-slam`**：那個按鈕有自己的 3 秒冷卻邏輯
（`web/index.html:428`）。如果 `updateUI` 每秒把它設成 `disabled = false`，
冷卻機制就失效了。**這個註解防止未來有人「順手」加一行。**

**③ `wasManual` 的邊緣觸發**：只在「從可手動變成不可手動」的**那一刻**
呼叫 `teleopRelease()`，清掉可能還在跑的 150 ms 續傳計時器。
每秒都呼叫的話會一直送 `(0,0)` 給後端，沒必要。

**④ 演算法診斷面板**：這就是第 05 章「讓演算法可觀察」的最終呈現。

```
   連通區間   14      ← n_runs
   臨界點      2      ← n_critical
   分解 cell   4      ← n_cells
   掃描主軸  0.0°     ← axis_deg
   λ1 / λ2  4.64     ← ratio（★ 接近 1 代表主軸退化）
```

---

## 15.7 ⑤ 設計決策

| 決策 | 選了 | 否決了 | 理由 |
|---|---|---|---|
| 顯示方式 | Canvas 疊圖 | `<img>` | 要疊六層、要畫向量、要著色 |
| 通訊 | 1 Hz HTTP 輪詢 | WebSocket / SSE | 監看不需要即時；實作簡單（第 05 章） |
| 並行請求 | `Promise.allSettled` | `Promise.all` | 一個失敗不能拖垮全部 |
| 座標 | 後端算好的像素 | 前端自己轉 | 第 05 章 5.4 |
| 縮放 | CSS（`style.width`） | 重繪到不同尺寸 | 繪圖座標保持原始像素，前端零數學 |
| 圖層開關 | 資料驅動（`LAYERS` 陣列） | 每個圖層寫一段程式 | 加圖層只要加一筆 |
| 軌跡漸層 | 最近 300 點逐段、其餘一次畫 | 全部逐段 | 10,000 段會卡 |
| 前端框架 | **無**（原生 JS） | React / Vue | 一個檔案、無建置流程、無 CDN 依賴 |

★ **最後一項值得展開**：前端刻意不用任何框架，
整個網頁是**一個 587 行的 `index.html`**（HTML + CSS + JS 全在裡面）。

好處：
- **零建置流程** —— 改完存檔重新整理就好
- **零外部依賴** —— 機器人可能沒有網路，CDN 載不到就整個掛掉
- **`catkin` 安裝簡單** —— 一個 `install(DIRECTORY web/ ...)` 就完成

代價：狀態管理靠全域變數（`robot`、`cov`、`imgCache`），
規模再大就會難以維護。但這個規模剛剛好。

---

## 15.8 ⚠ 已知問題

**① 每秒重新載入所有圖片**

即使地圖沒變（機器人靜止時 `/map` 可能好幾秒才更新一次），
前端每秒還是重抓 4 張 PNG。

**改進**：後端加 `ETag` / `Last-Modified`，讓瀏覽器用 304 Not Modified。
但那需要拿掉網址上的 `?t=` 時戳，跟現在的快取破除策略衝突。

**② `colorize` 每次都重算**

同一張圖片如果沒變，著色結果也不會變。可以快取，
但因為 ① 導致圖片物件每次都是新的，快取判斷不了。兩個問題要一起修。

**③ 沒有錯誤提示**

`catch {}` 把所有錯誤吞掉了。網路斷線時，畫面只是停止更新，
沒有任何「連線中斷」的提示。

**改進**：記錄連續失敗次數，超過 3 次就在頂列顯示警告。

**④ `alert()` / `confirm()` 是阻塞式的**

`web/index.html:406, 416, 420, 427` 用了原生對話框。
它們會**凍結整個頁面**（包括 `setInterval`），使用者不按掉就不會更新。

對「重啟 SLAM」的二次確認來說這是**優點**（強迫使用者停下來想一下），
對錯誤提示來說就比較粗糙。

---

## 15.9 ⑥ 本章重點回顧

1. ★ **前端只做兩件事：畫圖、送指令。整份 JS 只有一處數學**
   （`0.105 / resolution` 算機器人圖示半徑）。
2. **`LAYERS` 陣列驅動三件事**：側欄按鈕、要抓哪些圖、繪製順序。
   加圖層只要加一筆。
3. ★ **`colorize` 的關鍵是「空地變透明」**（`alpha = 0`），
   否則上層圖會蓋掉底下的原始地圖。
4. ★ **`canvas.width`（繪圖像素）和 `canvas.style.width`（顯示大小）是兩件事** ——
   繪圖永遠用原始像素座標，縮放交給 CSS。
5. ★ **必須用 `Promise.allSettled` 不能用 `Promise.all`**：
   啟動時圖片會 503，用 `all` 會讓整個畫面凍結。
6. **`drawCells` 用「偶數 index = 掃描線、奇數 index = 換行」的約定**
   分別畫粗實線和細虛線（第 12 章的路點結構）。
7. **軌跡：最近 300 點逐段漸層、更早的一次畫完** —— 10,000 段全部逐段會卡。
8. **前端零框架、零外部依賴、單一檔案** —— 機器人可能沒網路，CDN 載不到就全掛。

---

## 15.10 ⑦ 自我檢核題

**Q1. 如果把 `Promise.allSettled` 改成 `Promise.all`，系統剛啟動時會發生什麼？**

<details>
<summary>參考答案</summary>

**整個畫面會完全凍結，直到地圖準備好為止。**

啟動流程：
1. `map_server` 啟動，但 `/map` 還沒收到 → `map_png` 是 `None`
2. `/map.png` 回 **503**（`map_server.py:363-364`）
3. `loadImg` 的 `img.onerror` 觸發 → Promise reject
4. ⚠ `Promise.all` 看到有一個 reject → **整個 await 拋例外**
5. `refresh()` 的後半段（`updateUI()`、`draw()`、時鐘更新）**完全不會執行**

**症狀**：頁面停在「等待地圖資料…」，狀態列不動、時鐘不跳、按鈕沒反應。
使用者會以為是網頁壞了或伺服器沒開。

而事實上 `/coverage/status` 和 `/robot_state` **都是正常的**，
只是它們的結果被一起丟掉了。

**`allSettled` 的行為**：等三組全部有結果，各自回報成敗。
圖片失敗 → `imgCache` 保持空的 → `draw()` 第一行 `if (!orig) return`；
但 `updateUI()` 照常執行，時鐘照常跳 —— 使用者看得出系統活著。
</details>

**Q2. `colorize()` 裡如果拿掉 `else if (v > 180) { d[i+3] = 0; }` 這一行會怎樣？**

<details>
<summary>參考答案</summary>

**空地不會變透明，安全邊距圖層會把整張原始地圖蓋掉。**

`draw()` 畫圖層時用 `ctx.globalAlpha = 0.8`，所以不會完全蓋死，
但空地區域會變成「80% 不透明的紅色」（`#ff7b72`），整張圖變成一片紅。

**看不到的東西**：
- 原始地圖的牆在哪（都被紅色蓋住）
- 未知區和空地的分別
- 底下的細節

★ **這一行是「圖層」這個概念能成立的關鍵**：
上層圖只保留「有意義的部分」（障礙 + 膨脹區），其餘完全透明，
讓底層透出來。這就是圖像處理裡的 **alpha 遮罩**。

三段判斷的完整語意：
- `v < 80`（障礙）→ **著色，不透明**（這是我要強調的）
- `v > 180`（空地）→ **完全透明**（這裡沒有我要說的事）
- 中間（未知）→ **極淡的暗藍灰**（給一點視覺提示，但不搶戲）
</details>

**Q3. `drawTrail` 為什麼把軌跡分成「最近 300 點」和「更早的部分」兩段畫？**

<details>
<summary>參考答案</summary>

**因為透明度漸層需要每段獨立繪製，而獨立繪製很貴。**

Canvas 的 `globalAlpha` 是繪圖狀態，一次 `stroke()` 只能用一個值。
要做「越舊越淡」的漸層，就必須**每一小段呼叫一次 `beginPath` + `stroke`**。

軌跡上限是 **10,000 點**（`map_server.py:206-207`）。
全部逐段畫 = **10,000 次繪製呼叫，每秒一次** → 畫面明顯掉幀。

**折衷**：
- **最近 300 點**：逐段畫，有漸層（這是使用者真正在看的部分）
  → 300 次呼叫
- **更早的部分**：全部用同一個透明度 `0.22`，**一次 `stroke` 畫完**
  → 1 次呼叫

繪製呼叫從 10,000 降到 **301**，視覺上幾乎看不出差別
（超過 300 點以前的軌跡本來就已經淡到快看不見了）。

★ **這是「感知重要性」驅動的最佳化**：
把計算資源花在使用者真正會注意的地方。
</details>

**Q4. `updateUI()` 裡有一行註解說「btn-slam 的 disabled 由它自己的點擊處理器管理，
這裡不要覆蓋」。如果有人「順手」加了 `$('btn-slam').disabled = !cov.manual;` 會怎樣？**

<details>
<summary>參考答案</summary>

**「重啟 SLAM」按鈕的 3 秒冷卻機制會失效。**

原本的邏輯：

```javascript
// web/index.html:415-429
$('btn-slam').onclick = async () => {
    if (!confirm(...)) return;
    $('btn-slam').disabled = true;              // ① 立刻鎖住
    ... await fetch('/slam/restart', ...) ...
    setTimeout(() => { $('btn-slam').disabled = false; }, 3000);   // ② 3 秒後解鎖
};
```

如果 `updateUI()` 也去設它：
1. 使用者按下按鈕 → `disabled = true`
2. **最多 1 秒後** `refresh()` 觸發 `updateUI()` → `disabled = !cov.manual`
3. 此時 `cov.manual` 是 `true`（重啟後狀態變回 `idle`）→ **按鈕重新啟用**
4. 冷卻只維持了不到 1 秒，而不是 3 秒

**後果**：使用者可以在 1 秒內連按第二次 → 兩個 `/slam/restart` 請求 →
第 06 章 6.4 講的競態（雖然有 `slam_lock` 保護，但至少會白白多殺開一次 SLAM）。

★ **這個註解的價值在於它防止的是「合理的順手改動」**。
如果沒有註解，任何人看到 `updateUI` 裡管了 `btn-start`、`btn-stop`、
遙控盤，都會覺得「怎麼漏了 `btn-slam`」，然後好心加上去。

**通用原則：當程式碼裡「刻意缺少某一行」時，一定要寫註解說明。**
（和第 06 章 6.3 的「launch 檔第 2 段只有註解」是同一個道理。）
</details>

**Q5. 前端刻意不用 React / Vue，也不引用任何 CDN。這個決定的理由是什麼？
什麼情況下你會改變這個決定？**

<details>
<summary>參考答案</summary>

**理由：**

1. ★ **機器人可能沒有對外網路**。實驗室的機器人常常只接內網、或用手機熱點。
   如果 HTML 裡有 `<script src="https://cdn.../vue.js">`，
   **CDN 載不到 = 整個網頁一片空白**。而這件事只會在 demo 當天發生。
2. **零建置流程**：改一行存檔、重新整理就看得到（配合 `/` 路由每次讀檔）。
   有 npm / webpack 的話，每次改動都要 `npm run build`。
3. **catkin 安裝簡單**：`install(DIRECTORY web/ ...)` 一行搞定，
   不用處理 `node_modules`、不用把建置產物 commit 進 git。
4. **規模剛好**：370 行 JS、6 個圖層、一個狀態物件。
   全域變數 + 每秒重畫的模型完全夠用。

**什麼情況會改變決定：**

- **狀態變複雜**：例如加入「多機器人」「歷史回放」「參數即時調整」，
  手動同步 DOM 會開始出錯 → 值得引入框架的響應式綁定
- **需要離線快取 / PWA**：那本來就需要建置流程
- **多人協作前端**：單一 587 行檔案會有嚴重的 git 衝突

★ 但即使引入框架，**也應該把它 bundle 進本地檔案而不是用 CDN** ——
「機器人沒網路」這個限制不會消失。
</details>

---

**← 上一章** [第 14 章　後端 Flask 路由設計](14_後端Flask路由設計.md)
**下一章 →** [第 16 章　遙控與模式互斥](16_遙控與模式互斥.md)
