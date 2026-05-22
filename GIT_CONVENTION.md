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

### 範疇定義 (對應本專案模組)

| 範疇 | 對應檔案 |
|------|----------|
| `manager` | `ccpp_manager.py` |
| `planner` | `coverage_planner.py` |
| `map` | `map_processor.py` |
| `region` | `region_detector.py` |
| `executor` | `path_executor.py` |
| `web` | `web_server.py` / `app.js` / `index.html` |
| `viz` | `map_visualizer.js` |
| `launch` | `ccpp_web_monitor.launch` |
| `script` | `start_project.sh` |

### 範例

```
feat(web): 新增鍵盤 WASD 遙控功能
fix(planner): 修正掃描線邊界交點重複計算
tune(launch): 調整 scan_overlap 至 0.85
docs: 新增所有模組的行內說明註解
chore: 更新 .gitignore 排除 __pycache__
refactor(manager): 將座標轉換獨立為工具函數
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

## 不可 Commit 的內容

```
scripts/__pycache__/    Python 編譯快取
build/                  catkin 建置產物
devel/
*.log                   執行日誌
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
