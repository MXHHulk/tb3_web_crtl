# 第 5 階段：初步縮放審查（Initial Zoom Out）報告

- **目標**：`README.md`（第 1–53 行，整份當作功能說明審；沒有實作計畫段落，第 9 階段不適用）
- **背景檔案**：`docs/專案架構說明.html`、`docs/05_開發日志/CHANGELOG.md`
- **審查員**：`egm-zoom-out`（範圍與簡化）、`egm-inventive-catalyst`（矛盾與替代做法）
- **標準**：`zoom-out-standard.md`

## 總覽

| # | 來源 | 嚴重度 | 一句話 |
|---|---|---|---|
| Z1 | zoom-out | 🟡 Major | README 沒有系統概述與前提條件；入口只指向在 git 網頁上看不了的 .html |
| Z2 / C3 | 兩位都提 | 🟡 Major | 「目前狀態」、待辦、流程在 README／CHANGELOG／HTML 各寫一份，已經出現不一致 |
| C1 | catalyst | 🟡 Major | 改成自己開車繞過了「不縮 footprint＝不允許撞牆」的原則，安全靠人眼看；`ESCAPE_CLEAR` 是照單次實測值調的 |
| C2 | catalyst | 🟡 Major | 「改 launch／參數要手動重啟才生效」只靠人記，`.synced_commit` 會顯示新版但其實跑舊參數 |
| Z3 | zoom-out | 🟢 Nit | README 寫到調參數值的層級（`ESCAPE_CLEAR`、`LINE_K_HEAD`、`LINE_V`），很快就過時 |
| Z4 | zoom-out | 🟢 Nit | 第 9 行把熱點 IP 寫死，第 53 行又用 `<車子 IP>`，前後不一致 |
| Z5 | zoom-out | 🟢 Nit | `turtlebot3_ccpp/.synced_commit` 看起來像本地路徑，實際上只存在車上 |
| Z6 | zoom-out | 🟢 Nit | 資料夾樹和 HTML 第 3 章重複 |
| C4 | catalyst | 🟢 Nit | 下一步建議一次改一個參數上車試；其實可以先用現有的假 ROS 模擬掃參數 |

**主持人核對**：`map_server.py:80` 確實是 `ESCAPE_CLEAR = 0.18`，`map_server.py:95` 的 `FRONT_STOP = 0.13` 只看行進方向 ±20°，和 C1 的描述一致。C1、C2、C4 討論的是系統設計，不只是 README 的寫法。這次審查的對象是 README，所以這三項比較適合記進未來規劃（架構說明第 12 章），不一定要在 README 裡解決。

---

## A. egm-zoom-out 報告

**結論：有條件通過（無 Blocker，2 項 Major、4 項 Nit）。** 目標、資料夾配置、改程式流程和下一步都看得懂，可以接手。主要的結構問題有兩個：README 沒有自成一體的系統概述；同一份狀態和流程在三份文件各寫一次。

已讀檔案：persona、標準、README 全文、`專案架構說明.html`（第 1–5、9–12 章）、CHANGELOG 最上面 4 筆。核對結果：`turtlebot3_ccpp/tools/sync_to_robot.sh` 存在；本地沒有 `turtlebot3_ccpp/.synced_commit`。

### Z1（Major）第 1–4、51–53 行：缺系統概述與前提條件
README 只有一行標題，就直接進入交接狀態。主流程沒有寫出來：gmapping＋explore_lite 建圖 → 規劃牛耕路線 → map_server 自己控制執行 → 全程用手機控制台操作。前提條件也沒寫：Burger、Noetic、move_base、explore_lite。整體說明全部放在 `docs/專案架構說明.html`，但 .html 在 GitHub 上點開看到的是原始碼，所以「先讀架構說明」這個入口在最常用的閱讀方式下等於失效。
**建議**：標題下補 3–5 行白話概述（可改寫 HTML 第 1 章那句介紹）和前提條件；HTML 連結註明要下載後用瀏覽器開；「使用」一節補上最短流程：上電 → 啟動系統 → 自動建圖 → 開始覆蓋。

### Z2（Major）第 6–20、38–49 行：同一份內容有三份正本
README「目前狀態」、CHANGELOG 最上面一筆的待辦、HTML 第 12 章和頁尾的版本號，已經對不上：
- README 第 20 行的未來規劃少了「學習資料講義同步」「正方形場地限制」，多了「光達無資料偵測」，但這項在第 12 章算已知問題。
- README 的改程式流程少了 HTML 第 11 章的兩步：先用 `coverage_bench.py` 離線測、實車跑完取回 `data/` 再補 devlog。
- 第 8 行「與本地 HEAD 的程式一致」，每多一個 commit 就要重新確認。

**建議**：每種資訊只放一處正本。README 只留「下次從這裡開始」的 1–3 個行動，加連結到 CHANGELOG 最新一筆；版本和待辦只放在 CHANGELOG 或 HTML 第 12 章其中一處；流程也只放一處，另一處改成連結。

### Z3（Nit）第 12–13、17–19 行：細節放得太高層
`ESCAPE_CLEAR` 0.25 → 0.18、「路點 14～16，離牆 0.20 m」、`LINE_K_HEAD` 2.0 → 1.5、`LINE_V` 0.12 → 0.10，這些屬於 CHANGELOG 和 HTML 第 10 章的參數表。
**建議**：README 只寫目的，例如「確認 own_nav 在實車上不再受困」「掃描線擺動就調直線循跡增益」，數值改成連結。

### Z4（Nit）第 9 行 vs 第 53 行：IP 寫法不一致
`172.20.10.5` 是手機熱點分配的位址，換熱點就會變。
**建議**：一律寫 `<車子 IP>`，並附一句查法，例如看熱點的已連線裝置清單。

### Z5（Nit）第 8 行：`.synced_commit` 路徑容易誤會
**建議**：改寫成「車上 `~/catkin_ws/src/turtlebot3_ccpp/.synced_commit`（由 `sync_to_robot.sh` 寫入）」。

### Z6（Nit）第 22–36 行：資料夾樹與 HTML 第 3 章重複
**建議**：README 只保留第一層加 ★ 說明，細節連結到第 3 章。

**整體評語**：README 同時在當專案入口、交接單和流程手冊。建議讓 README 只做穩定的入口；會變動的狀態交給 CHANGELOG 和 HTML 第 12 章。

---

## B. egm-inventive-catalyst 報告

前置檢查（資訊是否足夠）：通過。另外讀了 `start.launch` 第 50–89 行和 `sync_to_robot.sh`。

### C1（Major）第 12–13 行、下一步第 1 點：安全模型被繞過
- `start.launch` 第 62 行寫著「不縮 footprint / inflation：那等於允許真的撞牆」。也就是說，作者為了安全，不肯放寬 DWA 的碰撞模型。
- 但實際做法是改用自己的控制器。它的碰撞檢查只有行進方向 ±20° 雷射小於 0.13 m（`FRONT_STOP`），原地轉向和走 make_plan 折線轉角時，都沒有用車身外形檢查周圍。下一步第 1 點要人在旁邊看「轉角是否擦牆」，說明安全目前靠人眼補。
- `ESCAPE_CLEAR` 降到 0.18，剛好讓上次 0.20 m 的情況過得去。這是處理症狀，不是根因。

**提案**：
- 在 `cmd_vel` 前面加一層共用的安全層。`_follow_line`、`_drive_to`、move_base 送出的速度都先經過它。它用 360° 雷射和車身外接圓檢查，並區分原地轉和前進。burger 外接半徑約 0.105 m，所以離牆 0.20 m 原地轉本來就安全。
- 脫困改成每次往空間最大的方向退，退多遠依當下空間決定，不用固定門檻。

**副作用**：
- 多一個節點會增加延遲。`controller_frequency` 已經降到 5 Hz，所以安全層必須夠輕。
- 安全層會變成單點故障：光達沒資料時要預設停車，這也能順便處理「光達偶發沒資料」。
- 門檻要重新驗證，和 costmap 的判斷不一致時，可能出現新的停在原地不動。
- 動態選脫困方向在邊界情況下比較難預測。

### C2（Major）流程第 4–5 點：參數沒生效卻看起來已同步
CHANGELOG 已記載踩過這個坑：參數伺服器保留舊值，只按「重新建圖」不會生效。這時 `.synced_commit` 已經是新版，實際跑的卻是舊參數，實測結果會對應到錯的版本。
**提案**（只提示，不自動重啟）：
- `sync_to_robot.sh` 比較這次和上一版 `.synced_commit` 之間的 `launch/`、`config/`，有變動就印出「需整套重啟」，或在車上寫一個旗標。
- 另一套更簡單的做法，二選一即可：`launcher.py` 啟動時記下 commit，控制台在「已同步版本 ≠ 執行中版本」時顯示警告，每次覆蓋紀錄也寫入執行中版本。

**副作用**：同步腳本和控制台各多一點維護成本；不建議自動重啟，因為可能打斷正在跑的任務。

### C3（Nit）第 8–13 行：交接資訊手抄三處
和 Z2 是同一件事。補充一點：車上版本改成在需要時去查（ssh 讀檔或在控制台顯示），不要抄進文件。代價是 README 要多點一次才看得到現況。

### C4（Nit）下一步第 2 點：一次只改一個參數上車試
專案已經有假 ROS 模擬（差速模型、3% 輪速誤差）。
**提案**：上車前先在模擬裡跑 `LINE_K_HEAD` × `K_CTE` × `LINE_V` 的組合，只把前一兩組帶上車；也可以選擇讓直線段依側向偏移動態調速。
**副作用**：模擬誤差和實車不同，最後仍要實車確認。

**未列為發現**：用 scp 取回 `data/`、光達偶發沒資料，第 12 章已列入規劃；`sync_to_robot.sh` 第 18 行預設寫死 IP，但可以用 `ROBOT` 環境變數覆寫，可接受。
