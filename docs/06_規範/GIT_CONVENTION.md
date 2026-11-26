# TurtleBot3 CCPP 版本控制規範

## 分支結構

```
main
 │  永遠是可在 TB3 實體上正常執行的穩定版本
 │  每個合併點打一個版本 tag
 │
 ├── feature/功能名稱     新功能開發
 └── fix/問題名稱         Bug 修正
```

### 分支命名規則

| 類型 | 格式 | 範例 |
|------|------|------|
| 新功能 | `feature/簡短描述` | `feature/web-teleop` |
| 修 Bug | `fix/簡短描述` | `fix/frontier-detection` |

> 使用小寫英文與連字號，不使用底線或空格。

---

## Commit Message 格式

```
類型(範疇): 簡短描述
```

### 類型定義

| 類型 | 使用時機 |
|------|----------|
| `feat` | 新增功能 |
| `fix` | 修正 Bug |
| `refactor` | 重構程式，不改變行為 |
| `docs` | 只修改註解或說明文件 |
| `chore` | 環境、設定、相依套件調整 |
| `tune` | 調整 ROS 參數或演算法數值 |
| `data` | 新增實驗紀錄（`experiments/`），不改程式 |

### 範疇定義 (對應本專案模組，2026-11-26 更新)

| 範疇 | 對應檔案／內容 |
|------|----------|
| `coverage` | `scripts/coverage_planner.py`、`map_server.py` 的覆蓋執行 |
| `nav` | `map_server.py` 的跨區移動、A*、循跡控制 |
| `explore` | `map_server.py` 的自動建圖（explore_lite 管理） |
| `launcher` | `scripts/launcher.py`（車上控制台 :8000） |
| `web` | `web/launcher.html`、`web/index.html` |
| `launch` | `launch/*.launch` |
| `slam` | `config/gmapping_params.yaml`、`launch/slam_gmapping.launch` |
| `tools` | `tools/*`（同步、備份、開機服務）、`test/*` |
| `exp` | `experiments/`（實驗紀錄） |
| `docs` | `docs/**`（學習資料／論文／海報／簡報／日志／規範／計畫） |

### 範例

```
feat(web): 新增地圖 SSE 即時推送
fix(web): 修正圖片快取導致地圖不更新
tune(launch): 調整預設 port 至 8080
docs: 更新 docs/01_學習資料/coverage_algorithm.md
chore: 更新 .gitignore 排除 __pycache__
```

---

## 版本號規則

格式：`v主版本.功能版本.修補版本`

| 版次變動 | 時機 |
|----------|------|
| 主版本 +1 | 系統架構重大變更或整體功能完整 |
| 功能版本 +1 | 新增完整功能並合回 main |
| 修補版本 +1 | 修正 Bug 後合回 main |

### 里程碑規劃

```
v0.1.0  基礎架構：可建圖、網頁可看到即時地圖
v0.2.0  Frontier 自主探索上線
v0.3.0  牛耕式覆蓋路徑執行完整
v0.3.1  ...Bug 修正
v1.0.0  系統穩定、文件齊全、可重複部署
```

### 目前的 tag

| tag | commit | 說明 |
|-----|--------|------|
| `v1.0.0` | fcf4941 | 改導航前的基準版本（直線循跡實測 97.7%）。2026-11-26 由 `v1.0-baseline` 改名 |
| `v1.1.0` | feature/astar-nav 合併點 | 自寫 A* 導航＋nav_mode（astar／movebase 對照）、規劃與 20 Hz 循跡紀錄、循跡 K_CTE 1.0／上限 10°、紀錄版本＝程式啟動時。A* vs DWA 證明數據用此版 |
| `v1.2.0` | feature/auto-experiment 合併點 | 自動實驗腳本、scan_axis（PCA／沿地圖軸）、MIN_RUN 0.20、MARGIN 0.13、轉向防撞、碰牆指標。正式 12 輪用此版 |

### 打 Tag 指令

```bash
git tag -a v0.1.0 -m "v0.1.0: 簡短描述這個版本做了什麼"
```

---

## 日常開發流程

### 開始新功能

```bash
git checkout main
git checkout -b feature/功能名稱
```

### 開發中途儲存進度

```bash
git add 修改的檔案
git commit -m "feat(範疇): 描述"
```

### 功能完成，合回 main

```bash
git checkout main
git merge --no-ff feature/功能名稱
git tag -a vX.Y.Z -m "vX.Y.Z: 描述"
git branch -d feature/功能名稱
```

### 修 Bug

```bash
git checkout main
git checkout -b fix/問題描述
# ... 修正 ...
git commit -m "fix(範疇): 描述修了什麼"
git checkout main
git merge --no-ff fix/問題描述
git tag -a vX.Y.Z+1 -m "vX.Y.Z+1: 修正 xxx"
git branch -d fix/問題描述
```

---

## 三地同步規則（2026-11-26）

| 位置 | 角色 | 規則 |
|------|------|------|
| 電腦（本 repo） | 唯一改程式的地方 | 不在車上、不在 GitHub 網頁直接改程式 |
| GitHub | 正式版本與備份 | `main`＝可在車上正常執行的版本；開發在 `feature/*`、`fix/*` |
| TB3 | 只執行 | 只能用 `tools/sync_to_robot.sh` 更新；開工前先跑 `--check` |

```bash
bash turtlebot3_ccpp/tools/sync_to_robot.sh --check   # 車上是否與 HEAD 逐檔一致
bash turtlebot3_ccpp/tools/sync_to_robot.sh           # 同步已 commit 的程式（可同步 feature 分支做測試）
bash turtlebot3_ccpp/tools/pull_from_robot.sh         # 車上 data/、maps/ 備份到 experiments/robot/
```

---

## 實驗規則（作為證明用的數據）

1. **只用打了 tag 的版本。** feature 分支可以上車測試，但測試數據不能當證據。
   開始實驗前跑 `sync_to_robot.sh --check`，確認車上 `.synced_commit` 等於該 tag 的 commit。
2. **每次實驗後馬上備份並提交**：`pull_from_robot.sh` → `git commit`，類型 `data`，
   訊息寫明版本、模式、場地、車子擺放角度、第幾次，例如：
   `data(exp): v1.1.0 nav_mode=astar 場地A 0° 第2次`
3. **對照實驗只改一個變因**：同一版本、同一場地、同一擺放角度，只切換要比較的模式（例如 `nav_mode`）。
4. **場地內不得有動態障礙物**（人、寵物、移動物體）；實驗中有人進入場地，該次作廢並在 commit 訊息註明。
5. **每組至少 3 次**；結果不論好壞都保留，不得刪除不利的紀錄。
6. 自動實驗腳本 `tools/run_experiments.py` 依上述規則排程（同一版本、組內 ABBA 交替、每輪重建地圖）；每輪結果在 `data/experiments/<編號>/trials.csv`。

| 證明 | 比較 | 主要指標 |
|------|------|----------|
| A* 比 DWA 穩 | `nav_mode=movebase` vs `nav_mode=astar` | 受困次數、實際覆蓋率 |
| PCA 優於沿地圖軸 | PCA 主軸 vs 固定地圖 x 軸，房間斜放多個角度 | 轉彎次數 |

---

## 不可 Commit 的內容

```
__pycache__/            Python 編譯快取
build/ devel/           catkin 建置產物
*.log                   執行日誌
turtlebot3_ccpp/maps/   車上產生（備份在 experiments/robot/）
turtlebot3_ccpp/data/
*.bag  media/           大型實驗檔與影片素材（放雲端硬碟）
.claude/                Claude Code 本機設定與技能
```

以上均已列入 `.gitignore`，若意外被追蹤請執行：

```bash
git rm -r --cached <檔案或目錄>
```

---

## 常用指令速查

```bash
# 查看分支圖
git log --oneline --graph --all --decorate

# 查看目前狀態
git status --short

# 查看所有 tag
git tag -l

# 切換至某個 tag 的狀態 (唯讀查看)
git checkout v0.1.0
```
