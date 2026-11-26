# 第 7 階段：批判審查（Critic Review）報告，第 1 輪

- **目標**：`README.md` 第 1–53 行（全檔）
- **審查員**：`egm-design`（完成）、`egm-structural`（完成）、`egm-style`（完成）。三位都有跑完，沒有未執行的。
- **標準**：`feature-spec-standard.md`，用在 design 和 structural 兩位。
- **背景檔案**：`docs/專案架構說明.html`、`docs/05_開發日志/CHANGELOG.md`
- **本輪結果**：🔴 0／🟡 11（合併後 8 項）／🟢 22（合併後 12 項）。這一輪**不算乾淨**，因為還有沒處理的 Major。

## 標準的適用範圍（三位一致）
- **不適用**：Alternatives Rule／Alternatives Considered。設計取捨已經寫在架構說明第 5、8 章，README 有連結過去就夠了。
- **適用或部分適用**：Problem Statement、Goals／Non-Goals、Risks & Limits，以及 Proposed Architecture（可以只放連結）。

## 主持人核對結果
- `sync_to_robot.sh` 第 15 行寫明：「會自動重啟 ccpp-launcher；**不會停掉正在跑的 roslaunch**」。第 14 行寫明：「車上有、但 HEAD 沒有的檔案會被刪除」。所以 **D-1-1 成立**：改了 `map_server.py`／`coverage_planner.py` 同步後，roslaunch 沒重啟，車上跑的仍是舊程式，`.synced_commit` 卻已經寫成新版。這是 README 目前最實際的錯誤，比文件寫法的問題重要。
- `sync_to_robot.sh` 第 6 行有 `ROBOT=` 覆寫 IP 的用法，README 沒提。
- `launcher.py:489` 的 `app.run(host='0.0.0.0', ...)` 屬實，控制台沒有任何驗證。
- 第 10 行「SLAM 參數調整＋去雜點」被列為已實車驗證，但 CHANGELOG 寫「新參數的實際效果還沒在同一場地重跑比較」（S-1-1），兩者矛盾。

---

## 合併後的行動項目

### 🟡 Major

| ID | 行 | 問題 | 建議 | 來源 |
|---|---|---|---|---|
| A1 | 43–49 | 只說改 launch 或參數要重啟，漏了 `scripts/` 底下的節點也要重啟；也沒說同步會刪掉車上舊檔、會重啟控制台 | 第 5 步改成：「改到 start.launch 啟動的節點（`map_server.py`、`coverage_planner.py`）、launch 或參數，都要在『系統』頁停止再啟動」。第 4 步補：「會刪掉車上 HEAD 沒有的檔案、會重啟控制台；任務執行中不要同步」 | D-1-1、S-1-N7 |
| A2 | 1–6 | 沒有專案簡介和範圍，新讀者得先打開 HTML 才知道系統在做什麼 | H1 下補 2–3 行：建圖 → 規劃牛耕路線 → map_server 執行 → 手機操作；寫出前提條件：Burger、Noetic | T-1-1（同 Z1、理解度 #2） |
| A3 | 10–13、20 | 沒有「已知限制」：只能用長方形場地、只在 1.06 × 1.47 m 一個場地驗證過、控制台綁 0.0.0.0 沒有驗證、`ESCAPE_CLEAR` 降低會提高擦牆風險 | 新增短的「已知限制」小節，連到第 12 章；第 12 行補「若擦牆先把 `ESCAPE_CLEAR` 改回 0.25」 | D-1-3、T-1-1 |
| A4 | 51–53 | 「使用」只有一行：沒寫環境需求、開機服務怎麼裝（`install_launcher.sh`）、打開網頁後要按「啟動系統」並等大約 40 秒 | 擴寫成「環境需求 → 首次安裝 → 日常操作」，放在「改程式的流程」之前 | T-1-2、S-1-N8 |
| A5 | 9、46、53 | IP 寫死又寫成佔位符，前後不一致；沒提 `ROBOT=` 覆寫；沒說 IP 變了怎麼查 | 第 46 行補 `ROBOT=ubuntu@<IP> bash ...`；第 53 行說明 IP 的查法；第 9 行標明「當下的值」 | D-1-2、T-1-N11（同 Z4） |
| A6 | 38–49 | 流程比架構說明第 11 章少三步：用 `coverage_bench.py` 離線測、`GIT_CONVENTION.md`、實測後取回 `data/` 補 devlog | 只留一個正本，另一份改成連結；或在 README 補齊這三步 | T-1-3、D-1-N5（同 Z2） |
| A7 | 10–11 | 「已實車驗證」說得太滿：SLAM 去雜點的效果還沒比較；97.7% 沒交代是「實際覆蓋率（軌跡 × 車身寬估算）」、場地、版本 `fb0ef34`、只跑過一次 | 把 SLAM 那項收窄成「參數已生效、效果未比較」；97.7% 補上定義、場地、`fb0ef34`、單次 | S-1-1、S-1-2、D-1-N1 |
| A8 | 12–13、17–18 | 用語太口語、指代不清：「自己開」「借 move_base」「DWA 不肯轉」「這個」；下次測試沒寫場地，也沒有比較基準 | 改用 S-1-3 的寫法；第 1 步寫明場地，並加上「與 97.7%／322 秒／83/83（`fb0ef34`）比較」 | S-1-3、S-1-4（同理解度 #4） |
| A9 | 35 | 沒警告 `01_學習資料` 是 2026-08 的版本、內容已過時；沒連到 `docs/README.md` | 第 35 行或導讀加一句警告，並附連結 | T-1-4、D-1-N4 |

### 🟢 Nit

| ID | 行 | 內容 | 來源 |
|---|---|---|---|
| B1 | 4、35、41 | 「日志」和「日誌」混用，統一成「日志」 | S-N6、T-N8、D-N3 |
| B2 | 8 | `.synced_commit` 要寫車上的完整路徑；「與本地 HEAD 一致」改成「與 `26f1a1f` 一致」 | S-N1、T-N10、D-N6 |
| B3 | 3、17、20 | 「第 9 章」「第 12 章」改成連結 `#s9`、`#s12`；.html 要註明下載後用瀏覽器開 | T-N9、D-N2 |
| B4 | 6–20 | 目前狀態是有日期的快照，和 CHANGELOG 重複；附上核對方法或改成連結 | T-N12、D-N6 |
| B5 | 20 | 括號裡的清單和第 12 章對不上 | S-N4 |
| B6 | 43–49 | 程式碼區塊打斷編號清單（要縮排 3 格）；`--build` 沒有範例；第 5 步其實是條件提醒 | T-N5、S-N7 |
| B7 | 24 | 程式碼區塊加上 `text` 語言標記 | T-N6 |
| B8 | 26–35 | 目錄樹把兩個項目擠在同一行；`★` 是裝飾符號；「＝」和「一對一」說的是同一件事 | T-N7、S-N5 |
| B9 | 11、13 | 「最後一次」和「上一次」指同一次實測，統一用語 | S-N2 |
| B10 | 19 | 「若仍左右擺動」的「仍」前面沒交代；`data/coverage/...` 是車上路徑，取回後本機路徑會不同 | S-N3、D-N6 |
| B11 | 46 | Windows 要用 Git Bash 執行；沒說 `rebuild` 和 `main` 是什麼關係 | D-N5 |
| B12 | 53 | 「手機連上熱點」和「手機熱點」說法衝突 | S-N8 |

---

## 追溯表（原始發現 → 合併項目）

| 原始 ID | 審查員 | 嚴重度 | → |
|---|---|---|---|
| design-1-1 | design | Major | A1 |
| design-1-2 | design | Major | A5 |
| design-1-3 | design | Major | A3 |
| design-1-N1 | design | Nit | A7 |
| design-1-N2 | design | Nit | B3 |
| design-1-N3 | design | Nit | B1 |
| design-1-N4 | design | Nit | A9 |
| design-1-N5 | design | Nit | A6、B11 |
| design-1-N6 | design | Nit | B2、B4、B10 |
| structural-1-1 (F1) | structural | Major | A2、A3 |
| structural-1-2 (F2) | structural | Major | A4 |
| structural-1-3 (F3) | structural | Major | A6 |
| structural-1-4 (F4) | structural | Major | A9 |
| structural-1-N (F5) | structural | Nit | B6 |
| structural-1-N (F6) | structural | Nit | B7 |
| structural-1-N (F7) | structural | Nit | B8 |
| structural-1-N (F8) | structural | Nit | B1 |
| structural-1-N (F9) | structural | Nit | B3 |
| structural-1-N (F10) | structural | Nit | B2 |
| structural-1-N (F11) | structural | Nit | A5 |
| structural-1-N (F12) | structural | Nit | B4 |
| style-1-1 (M1) | style | Major | A7 |
| style-1-2 (M2) | style | Major | A7 |
| style-1-3 (M3) | style | Major | A8 |
| style-1-4 (M4) | style | Major | A8 |
| style-1-N1 | style | Nit | B2 |
| style-1-N2 | style | Nit | B9 |
| style-1-N3 | style | Nit | B10 |
| style-1-N4 | style | Nit | B5 |
| style-1-N5 | style | Nit | B8 |
| style-1-N6 | style | Nit | B1 |
| style-1-N7 | style | Nit | A1、B6 |
| style-1-N8 | style | Nit | A4、B12 |

## 審查員確認正確的內容（不用改）
- 檔案樹列出的檔案都存在；`--build` 的用法和腳本一致。
- 架構說明第 9、12 章的章號和內容對得上。
- `own_nav`、「改用 move_base」、「受困」這些事件字串確實由 `map_server.py` 寫出。
- `LINE_K_HEAD` 2.0、`LINE_V` 0.12、`ESCAPE_CLEAR` 0.18 和程式碼一致；97.7%、83/83、322 秒、路點 14～16 和 CHANGELOG 一致。
- 「已上車、還沒實車跑」和 CHANGELOG 一致。全文沒有誇大或行銷用語。

## 與前幾個階段的關係
- A2、A4、A6、B4 和第 5 階段的 Z1、Z2 是同一個根本問題：README 同時在當入口、交接單和流程手冊。
- 第 6 階段要求在 README 裡定義參數，第 5 階段的 Z3 要求把參數移出 README，兩者衝突。處理方式見 `comprehension_report.md` 的主持人註記：README 寫目的，細節用連結。A8 的改寫應該照這個原則。
