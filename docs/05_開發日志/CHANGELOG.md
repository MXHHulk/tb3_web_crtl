# 開發日志 CHANGELOG

> 撰寫規範見 [README.md](./README.md)。最新的日志放最上面。

---

## 2026-11-27　docs(slides)：新增簡報逐字稿

- **類型**：docs
- **做了什麼**：新增 `docs/07_衝刺計畫/成果影片簡報/逐字稿.md`，對應目前 8 頁、逐段標出【按一下】的位置，附數字出處與可能被問的問題。
  問題三的 0.69 m² 註明是用同一張實車地圖不過濾雜點「事後重算」的值，且是 6 次中雜點最多的一次（其他 5 次差 0～1%）。

---

## 2026-11-27　fix(slides)：問題三的解法與結果播不出來；刪除結論頁（8 頁）

- **類型**：fix＋docs
- **問題**：問題三頁 steps 為 [2.4, 6.0]，但「解法」「結果」在 6.2 s 之後才出現；引擎在最後一個停點按 → 會直接換下一頁，
  所以實際播放時只看得到問題、看不到解法與結果（frames.mjs 用 __seek 跳到結尾截圖，沒抓到這個錯）。
- **做了什麼**：問題三改為 steps [2.4, 6.0, 9.2]、duration 9.2；逐頁檢查其他頁最後停點之後沒有動畫。
  依使用者決定刪除「結論與未來規劃」頁，實機展示改為 08。
- **驗證**：playwright 開 index.html 實際按 →：06 頁依序停在 2.4、6.0、9.2，第三段顯示解法與 0.69→0.82 m²，再按才換到 07。

---

## 2026-11-27　docs(slides)：簡報精簡為 9 頁，操作流程後直接接問題

- **類型**：docs
- **做了什麼**：依使用者決定刪除第四次修改加入的 04～09 介紹頁（自動建圖、覆蓋規劃五步驟、PCA 與切帶、cell、安全邊距、循跡執行），
  03 操作流程後直接接問題一～四、結論與未來規劃、實機展示；檔名與頁碼重新編號（04-p1-pca … 09-demo）。刪掉的頁可從 776f65f 找回。
- **驗證**：frames.mjs 九頁全部截圖正常。

---

## 2026-11-27　docs：對照組名稱更正為「move_base」，不再寫「A* vs DWA」

- **類型**：docs
- **原因**：A* 是規劃層（算路線），DWA 是 move_base 裡的控制層（開車），兩者不同層；實驗是把兩層一起換掉
  （navfn＋DWA → 自寫 A*＋直線循跡），所以對照名稱應為「自寫 A*＋直線循跡 vs move_base」。數據不變。
- **做了什麼**：簡報 13 頁標題、問題／解法文字、長條圖標籤與圖例、註記；14 頁結論；
  `docs/03_海報/gen_result_table.py` 標題改「自寫導航與 move_base 實測對照」、標籤改「A*＋循跡／move_base」並重產 `result_table.png`；
  Canva 海報換上新圖、結論第 3 點改「取代 move_base」（已存檔）。
- **限制**：兩層未拆開測，無法單獨歸功 A* 或循跡。

---

## 2026-11-27　docs(slides)：成果動畫簡報第四次修改（15 頁，重排敘事順序）

- **類型**：docs
- **做了什麼**：依使用者意見改成「自動建圖 → 覆蓋規劃（海報研究方法五步驟）→ 循跡執行 → 遇到的問題 → 結論與未來」。
  04 補自動建圖怎麼做到（gmapping／explore_lite／move_base）；新增 05 五步驟總覽、09 循跡執行（A* 銜接路線由 `astar.py` 實際算出）；
  原 05「地圖是斜的」併入問題一「為什麼用 PCA、不沿地圖座標軸」；四個問題頁一律「問題 → 解法 → 結果」；限制頁改為「結論與未來規劃」，內容與海報一致。
- **更正**：問題二舊版穿過障礙的掃描線是 2 條不是 3 條（原本用「障礙＋邊距」的高度判斷，現改用障礙物本身）；
  cell 色塊原本畫成左右切，與實際路徑不符，改為依 `bandCuts` 上下切（cell 1 下方整寬、cell 3 上方整寬、cell 2／4 左右兩側）。
  `gen_data.py` 的障礙區改用 `apply_safety_margin`（與規劃程式相同的 3 格正方形膨脹）。
- **驗證**：frames.mjs 逐頁截圖 04～14，確認 11 頁穿過 2 條、cell 範圍與路徑一致，修正 07 標籤與切線重疊。

---

## 2026-11-27　fix(slides)：簡報打開全黑——記住的頁碼超出範圍

- **類型**：fix
- **問題**：`index.html` 用 localStorage 記住上次看到第幾頁；頁數從 14 改為 13 後，停在舊第 14 頁的瀏覽器讀到頁碼 13，
  `go()` 判斷超出範圍直接 return，iframe 沒載入任何頁 → 整個畫面全黑。
- **做了什麼**：`build_scenes.py` 產生的 index.html 讀頁碼時檢查範圍，超出就從第 1 頁開始；localStorage 讀寫包 try/catch。
- **驗證**：Edge（playwright）先寫入舊頁碼 13 再重新整理，載入 01-cover、畫面正常。

---

## 2026-11-27　docs(planner)：MARGIN 註解補上實際膨脹距離

- **類型**：docs（只改註解，程式行為不變）
- **做了什麼**：`coverage_planner.py` 的 MARGIN 註解補充：`apply_safety_margin` 換格數時四捨五入（0.13/0.05→3 格）且為正方形膨脹，
  實際往四周擴 0.15 m，單格雜點變 35 cm 見方；END_TRIM 註解的端點離障礙距離改為約 0.24 m；`apply_safety_margin` docstring 註明取整規則。
- **驗證**：語法檢查通過；使用者決定只改註解、不改 MARGIN 數值。

---

## 2026-11-27　docs(slides)：成果動畫簡報第三次修改（13 頁，依使用者八點意見）

- **類型**：docs
- **做了什麼**：02 三層分隔線上移、內容置於每層中間；04 右側文字垂直置中並修換行；
  07／09 示意場地改 2.0×1.2 m（2.0×1.0 在實際邊距下只剩 3 個 cell），恢復 4 個 cell；
  08 安全邊距改為格子畫法（與地圖頁一致），文字更正為「需要 13 cm，取 3 格＝15 cm」；
  09 恢復上一版畫面並加切點白虛線、4 個 cell 色塊、障礙＋邊距區，數據改為示意圖本身的「5 條中 3 條穿過 → 0 條」（`gen_data.py` 輸出 `cuts`、`oldStats`）；
  10 改為格子畫法並更正為 5＋15＋15＝35 cm 見方；11 問題三改成三張長條圖（受困、覆蓋時間、覆蓋率），併入原 12 數據總表並刪除該頁，
  限制與實機展示改為 12、13 頁。
- **發現**：`apply_safety_margin` 以 `round(MARGIN/解析度)` 格正方形膨脹，MARGIN 0.13 實際擴 3 格＝15 cm（非 13 cm），
  `coverage_planner.py` 中 MARGIN 的註解與實際效果不一致；程式未改，待與使用者討論。
- **驗證**：frames.mjs 逐頁截圖檢查 02、04、07～11，修正 08 文字斷行、09 大字換行與孤字。

---

## 2026-11-27　docs(slides)：成果動畫簡報第二次修改（14 頁，依使用者九點意見）

- **類型**：docs
- **做了什麼**：拿掉 02 行數與全部出處；03 流程每按一下走一格；04 改為「6/6 次自己建出完整地圖」（不放耗時、面積、回起點）；
  06 PCA 長短軸改畫到可走格在軸上的投影範圍（原本固定畫 ±1.7／±0.9 m，長軸穿出牆外；`gen_data.py` 輸出 `axes.ext`），並說明青色外圈；
  新增 08「安全邊距」圖解（13 cm＝半寬 10.5＋半格 2.5）；問題二加 5＋13＋13＝31 cm 圖解，數據改用正式實驗實車地圖
  （雜點最多一次 0.69→0.82 m²，+18%；原 1.08→1.16 為 11/11 離線比較、舊邊距 0.10）；問題一的「穿牆 0 次」改用 6 次實測規劃 331 段；
  問題三主軸改為受困與覆蓋時間、覆蓋率列為附帶；新增 13「限制與未來規劃」（A* 牆邊轉向仍擦撞等）。
  `gen_data.py` 建圖快照來源改為 `experiments/robot/maps/`（原 `turtlebot3_ccpp/maps/` 已於 11-26 整理時刪除）。
- **驗證**：frames.mjs 逐頁截圖，修正 04 換行、08 數字斷行、09 小標重疊。

---

## 2026-11-27　docs(slides)：成果動畫簡報更新為最新成果（12 頁，實機展示移到最後）

- **類型**：docs（`docs/07_衝刺計畫/成果影片簡報/tools/build_scenes.py` 重新產生）
- **做了什麼**
  - 02 系統三層：行數更新（coverage_planner 505、map_server 2290、launcher 493、web/index.html 715），新增 astar.py 151；
    move_base 改標「建圖時導航・對照組 DWA」。03：循跡執行改為「自寫 A*＋直線循跡」。
  - 04 自動建圖：改用正式實驗 6 次（中位 80 s、範圍 49～108 s、面積 1.90～1.95 m²、回起點 4/6，誤差 4～8 cm）。
  - 05：拿掉「轉彎變多」（實測地圖轉彎數 PCA／軸向 2 勝 2 負，不支持此說法）。
  - 10 問題三：改為 A* vs DWA 正式實驗各 3 次（覆蓋 82.7%→90.9%、受困 2→0、全部跑完 1→3、覆蓋時間 10.1→3.2 分）。
  - 11 數據總表：A* vs DWA（含碰牆推估 3 vs 2 並註明推估）。12 實機展示：最後一頁、併入團隊名單，之後接實機影片；
    移除舊「0° vs 30°」與「結尾」頁（使用者決定）。
  - `簡報進度.md`、`簡報生成.md` 同步。
- **驗證**：`frames.mjs` 逐段截圖檢查 02、04、05、10、11、12，修正 04 說明重疊、11 時間欄換行、12 標題被線切過。

---

## 2026-11-27　docs(海報)：海報內容對齊專案現況、成果展示換新截圖與 A* vs DWA 對照圖

- **類型**：docs（Canva 正式海報 DAHWAcA9RhE，使用者確認預覽後儲存）
- **文字修正**（逐句對照程式與日志，5 處與現況不符）：摘要、結論的「ROS 導航模組執行」→「自寫 A* 規劃與直線循跡」；
  限制與未來工作刪去已完成的「結合 frontier 自主探索」「改用 A* 接駁」；系統架構「導航與避障」加「（建圖時）」、
  「任務執行器」加「（A*＋循跡）」（兩框字級 22 以放進原框）。
- **成果展示**：實驗條件改為「開機後自動建圖…」（原場地尺寸 1.35×1.2 m 為 9 月場地，新截圖場地無實測尺寸，暫不寫）；
  4 張 9 月截圖換成使用者提供的 2 張（覆蓋路徑規劃 cell A～F、安全邊距，原檔備份在 media/poster/，不進版控）；
  新增 A* vs DWA 對照圖 `docs/03_海報/result_table.png`（`gen_result_table.py` 由 trials.csv 產生：三個並排小圖——受困點陣、
  平均覆蓋率、覆蓋時間平均＋範圍；強調藍 #2A6FB0 經 dataviz 驗證、DWA 灰並直接標值）。
  以圖片放入的原因：Canva 編輯回應超過 100k 字元截斷，拿不到新增文字元素 ID。
- **更正**：DWA 平均覆蓋率為 82.7%（先前誤寫 82.8%）。

---

## 2026-11-26　data(exp)：正式實驗 A* vs DWA（實驗 20261126-1345，v1.2.0）；PCA 對照實驗取消

- **類型**：data
- **決定**：使用者決定只做 A* vs DWA（各 3 次即可），PCA vs 沿地圖軸實驗取消（快速驗證中同一實測地圖轉彎數 2 勝 2 負，證據不足）。
  原排程第 7～12 輪未執行。
- **有效數據**（`experiments/robot/data/experiments/20261126-1345/trials.csv`，版本皆 ec074f0＝v1.2.0，同一場地，每輪重建地圖）

| 輪 | 條件 | 結果 | 受困 | 碰牆（推估） | 實際覆蓋 | 覆蓋執行秒數 | 覆蓋任務 |
|---|---|---|---|---|---|---|---|
| 1 | A* | 56/56 | 0 | 1 | 89.3% | 210 | 20261126-134730 |
| 4 | A* | 68/68 | 0 | 0 | 97.8% | 188 | 20261126-141521 |
| 5 | A* | 52/52 | 0 | 2 | 85.7% | 186 | 20261126-142054 |
| 2 | DWA | 51/51 | 0 | 0 | 83.6% | 668 | 20261126-135253 |
| 3 | DWA | 40/63（受困停止） | 1 | 1 | 75.7% | 482 | 20261126-140539 |
| 6 | DWA | 50/68（受困停止） | 1 | 1 | 89.0% | 662 | 20261126-144647 |

  - 彙總：受困 A* 0/3、DWA 2/3；平均實際覆蓋 A* 90.9%、DWA 82.7%（三輪 83.57、75.70、88.96 之平均 82.74）；覆蓋執行時間 A* 186～210 s、DWA 482～668 s（約 3 倍，且 DWA 兩輪是受困提早結束）。
    碰牆推估 A* 3、DWA 2（以規劃當下地圖＋官方車身矩形估計，地圖有數公分誤差，不作為主要結論）。
  - **作廢**：trials.csv 中另兩筆第 6 輪（stopped 2/66：暫停程式停錯行程誤中斷；stopped 0/331：接續時系統未重啟、建圖 7.8 m² 異常後手機手動停止），
    原始紀錄保留，原因記在 log.txt。
  - 實際斜角：第 1 輪 −25.9°（快速驗證後車頭未對齊）、第 6 輪 −82.7°（λ 比 3.45，PCA 方向明確；重新放車時車頭約對著短邊）；
    兩種模式都用 PCA，不影響 A* vs DWA 比較。
  - 限制：每組 3 次、各輪地圖不同；結論寫「此次實驗觀察到」，不宣稱統計顯著。
- **過程中的問題**：電量不足（10.99 V 時重啟後光達無資料，與 11:21 的同一症狀，未確定與電壓有關）；
  控制台以指令文字比對停止行程，ssh 指令含相同文字會被一起停掉；以 pgrep 抓實驗腳本 PID 會先抓到外層 bash。
  實驗結束後待改：腳本加「本輪結束後暫停」、開始前檢查光達。

---

## 2026-11-26　fix(coverage,nav,tools)：依官方車身尺寸防撞、碰牆指標；快速驗證（4 輪）結果

- **類型**：fix / feat（分支 `feature/auto-experiment`）
- **快速驗證**（實驗 20261126-1318，版本 095a1f3，`experiments_smoke.json`，全程無人操作）

| 輪 | 條件 | 實際斜角 | 結果 | 受困 | 轉彎 | 覆蓋 | 秒 |
|---|---|---|---|---|---|---|---|
| 1 | A*、PCA、0° | 4.9° | 73/73 | 0 | 37 | 95.9% | 220 |
| 2 | DWA、PCA、0° | −6.9° | 53/71（受困停止） | 1 | 36 | 88.8% | 402 |
| 3 | A*、PCA、目標 30° | 14.6° | 79/79 | 0 | 61 | 93.9% | 218 |
| 4 | A*、沿地圖軸、目標 30° | 27.6° | 91/91 | 0 | 49 | 98.8% | 264 |

  - 流程：回起點、轉向、重設里程計、重建地圖、建圖、覆蓋、受困後回起點繼續，全部自動完成；電壓 11.85 → 11.49 V。
  - **第 1 輪使用者目視撞牆**：131912 的 101.5 s 在路點 32（離障礙格 0.15 m）原地轉 140°，耗時 4.9 s 且位置被擠向牆 4.8 cm。
    Burger 官方 footprint（`costmap_common_params_burger.yaml`）以輪軸為原點往後 0.105、往前 0.041、左右 0.105 m，
    原地轉向車尾角落掃過半徑 0.148 m；程式原以半寬 0.089／半徑 0.11 m 計。DWA（move_base 用官方 footprint）看起來安全。
  - DWA 每點耗時：掃描線端點中位 10.2 s（停下轉正），中途點 1.6 s；路點 54～56 連續停滯→脫困→跳過→受困停止。
  - 斜角控制：目標 30° 兩次實際 14.6°／27.6°，原因未確定（1 次樣本）；腳本以 PCA 實測值記錄。
  - **同一張實測地圖只換掃描方向**（用各輪 grid.npz 重算，現行參數）：轉彎 PCA／軸向 29／27、29／30、38／40、28／24（2 勝 2 負），
    與合成場地（7 勝 3 平 0 負）不同；覆蓋率在斜角約 5° 的兩張 PCA 97.7%／98.0% vs 軸向 86.7%／88.4%。主要指標待與使用者確認。
- **做了什麼**
  - `coverage_planner.py`：`MARGIN` 0.10 → **0.13**（官方半寬 0.105＋半格 0.025）。
  - `map_server.py`
    - 官方車身常數 `FP_REAR/FP_FRONT/FP_HALF_W`、`ROT_SWEEP`（0.148）、`ROT_CLEAR`（0.168）。
    - 規劃後 `_nudge_turns()`：轉彎路點（夾角 ≥ 20°，或與 A* 段相鄰）離障礙格 < 0.168 m 時，每步 1 cm、每步重找最近障礙往外推，最多 6 cm，
      推完前後兩段仍須在可走區內。牆在車子側面時，轉向前沿車頭方向移開幫不上忙，只能在規劃時避開。
    - 原地轉向前 `_make_room_to_turn()`：掃過範圍內有障礙就沿車頭方向往遠離障礙的一側移開（最多 12 cm），`_follow_line`、`/nav/goto` 都會用。
    - 位姿紀錄 `<task>_pose.csv`（含朝向；移動 2 cm 或轉 5° 記一點，原地轉向也有）。
    - 碰牆指標 `_contact_metrics()`：官方車身矩形逐點對規劃當下地圖的障礙格，`n_contact`（次數）、`contact_s`、`min_clear_cm`，寫入紀錄與 CSV。
  - `run_experiments.py`：trials.csv 加 `n_contact`、`contact_s`、`min_clear_cm`；結束時回起點並轉回對齊房間長邊（下次不必人工擺正）。
  - `sim_coverage.py`：`--no-turn-guard`、`--margin` 對照；10 Hz 位置追蹤；起點改在離障礙最遠處。
- **結果 / 驗證**（模擬，兩張今天的實測地圖 × 3 種子，SLAM 誤差 σ 2 cm＋5 cm 跳動＋延遲 0.1 s）

| 地圖 | 舊（邊距 0.10、無防護）碰牆次數 | 新 | 到達 |
|---|---|---|---|
| explore_20261126_131845 | 2、1、4 | **1、0、0** | 皆 100% |
| explore_20261126_132401 | 1、2、2 | **0、0、0** | 皆 100% |

  邊距加大後可走區變小（覆蓋率分母不同，新舊百分比不可直接比），牆邊由外圈補。**尚未實車。**

---

## 2026-11-26　feat(tools,coverage,nav)：自動實驗腳本、scan_axis 對照組、修 cell 碎裂、/nav/goto

- **類型**：feat / fix（分支 `feature/auto-experiment`）
- **背景**：使用者要「把車丟在場地裡，自己重新建圖、重新跑，完成整個實驗流程」，涵蓋 PCA vs 沿地圖軸、A* vs DWA 兩組證明。
  - 查證地圖方向從哪來：同場地三次覆蓋主軸 0.2°／27.3°／−85.6°；11:24 建圖起點朝向 133°。實測系統剛啟動時 /odom＝(0, 0, 5.6°)，
    `rostopic pub /reset` 後朝向 2.7°；`/reset` 的訂閱者是 turtlebot3_core。→ gmapping 地圖方向＝里程計原點方向，
    里程計只在系統啟動（或 /reset）時歸零，同一次開機內重啟 SLAM 不會改變地圖方向。
- **做了什麼**
  - `coverage_planner.py`
    - **修 cell 碎裂**：新增 `MIN_RUN = 0.20 m`（原本 1 格 5 cm）。房間斜放時最外一條掃描帶沿牆在格子上的鋸齒邊緣走，被切成 5～12 cm 碎片，
      每片一個 cell，而且只發生在掃描線與牆平行時（＝PCA），對 PCA 不公平。
    - `plan(scan_axis='pca'|'map_x', min_run=None)`：`map_x`＝固定沿地圖 x 軸（傳統牛耕，對照組）；回傳多 `pca_axis`（房間在地圖上的方向）。
  - `map_server.py`
    - `/coverage/start` 收 `scan_axis`；紀錄與 CSV 多 `scan_axis`、`pca_axis_deg`、`n_turns`（方向變化 > 30° 的次數）；plan.json 參數多 `min_run`。
    - `/slam/restart` 收 `reset_odom`：停 SLAM → 發 `/reset` 重設里程計 → 重啟 SLAM，新地圖 x 軸＝車子當下朝向。
    - 新增 `/nav/goto`（JSON x、y、yaw_deg）與 `/nav/stop`：在目前地圖上用自寫 A*＋循跡開到指定位置、原地轉到指定朝向，失敗時脫困重試 2 次；
      與覆蓋、建圖、手動遙控互斥。`_follow_line` 新增 `alive` 參數。
    - `/coverage/status` 多 `battery_v`、`nav`、`pose`；建圖狀態多 `task`、`home_result`。
  - 新增 `tools/run_experiments.py`（車上執行、只用標準函式庫）＋ `tools/experiments.json`（正式：2 組 × 2 條件 × 3 次 = 12 輪）、
    `tools/experiments_smoke.json`（每組 1 次 = 4 輪）。每輪：/nav/goto 回起點並轉到「房間方向＋斜角」→ /slam/restart（reset_odom），
    20 秒內地圖沒長出來就重啟（最多 3 次）→ 自動建圖 → 覆蓋 → 寫一列 `data/experiments/<編號>/trials.csv`
    （條件、目標與實際斜角、建圖／覆蓋任務編號、結果、轉彎數、電壓、版本）。下一輪的房間方向用本輪 PCA 實測值。
    組內 ABBA 交替；受困記為該輪結果後繼續；回不去起點、光達異常就停止並保存進度；電壓 < 11.0 V 停止；`--resume` 以當下位姿為新起點接著跑。
  - 新增 `test/pca_vs_axis.py`（PCA vs 沿地圖軸離線比較，含 `--sweep-min-run`）；`test/sim_coverage.py` 加 `--scan-axis`、`--goto-home`。
  - `package.xml` 補 `std_msgs` 相依。
- **影響檔案**：`turtlebot3_ccpp/scripts/coverage_planner.py`、`scripts/map_server.py`、`tools/run_experiments.py`（新）、
  `tools/experiments.json`（新）、`tools/experiments_smoke.json`（新）、`test/pca_vs_axis.py`（新）、`test/sim_coverage.py`、`package.xml`
- **結果 / 驗證**
  - `pca_vs_axis.py --sweep-min-run`（合成 3 種房間 × 斜 0/15/30/45° ＋ 實測 grid 1 張）：

| min_run | 斜置／實測 10 張：PCA 轉彎較少／相同／較多 | 平均覆蓋 PCA／軸向 | PCA 最多 cell |
|---|---|---|---|
| 0.05（原本） | 7／2／1 | 99.1%／98.7% | 12 |
| 0.10 | 8／1／1 | 99.1%／98.7% | 7 |
| 0.15 | 8／1／1 | 99.1%／98.7% | 6 |
| **0.20（採用）** | **7／3／0** | 99.1%／98.7% | **4** |
| 0.25 | 7／3／0 | 99.0%／98.6% | 5 |

    `coverage_bench.py`：斜置 15° 由 21 cell、19 段轉場穿牆 → 1 cell、0 段；其他場地覆蓋率不變。
  - `sim_coverage.py`（實測地圖 113453）：pca／map_x／movebase 三種都跑完；`--goto-home` 回起點並轉到 30°：位置誤差 2.8～2.9 cm、朝向 2.4～2.5°。
  - `run_experiments.py` 以假 map_server 測試：12 輪排程（ABBA）、受困記錄後繼續、第 8 次導航故意失敗 → 停止保存 → `--resume` 從第 8 輪接到完成，
    斜角 30° 時實際斜角量得 30.0°。
  - **尚未實車**：`/reset` 是否讓旋轉後的朝向歸零（實測只在靜止時看過 5.6° → 2.7°）、/nav/goto 實車精度、整套無人值守流程。
    腳本用 PCA 量實際斜角，就算重設不準，數據仍以實測值為準。

---

## 2026-11-26　fix(coverage,tools)：紀錄版本改為「程式啟動時」；分析工具改進；ebbc12f 實測分析

- **類型**：fix
- **實測**（場地同上，兩次皆 astar）：
  - 20261126-115816：81/81、零受困、實際覆蓋 98.8%、224 s、主軸 27.3°。**實際執行的是 dd7af0d（舊循跡參數）**：
    11:27 系統啟動 → 11:52 同步 ebbc12f 但沒重啟 → 11:58 跑任務；沒有 plan/track 檔，`coverage_runs.csv` 卻記成 ebbc12f（原始檔不改，以此為準更正）。
  - 20261126-121423（12:09 重啟後，ebbc12f）：73/73、零受困、實際覆蓋 94.5%、220 s、主軸 −85.6°。
  - 蛇行（timeline 每秒一筆，直行時車頭與主軸夾角 90%）：舊參數 23.6°（113553）／21.8°（115816）→ 新參數 **16.5°**（121423）。
    有改善，但不如模擬預測的約 8°；各只有 1 次。
  - **SLAM 位置跳動比模擬假設頻繁**：121423 的 20 Hz 紀錄中單一週期位移 > 3 cm 有 24 次（中位 4.4 cm、最大 18.9 cm），
    模擬只假設 2 次 7 cm。側偏 95%（排除每段起頭 0.15 m）5.7 cm，大於模擬的約 4 cm，主因應是定位跳動。
  - 離障礙 < 0.114 m 共 4 次，其中 3 次前後 1 秒內有位置跳動（可能是定位誤差）；(−1.73, +0.43) 142～145 s 那次沒有。
- **做了什麼**
  - `map_server.py`：紀錄的 `synced` 改為**本程式啟動時**讀到的 `.synced_commit`（`RUN_VERSION`）；
    任務開始時若檔案版本已不同（同步後沒重啟），記一筆 ⚠ 事件。
  - `sync_to_robot.sh`：同步時偵測到 roslaunch 正在執行，提醒「要在手機停止再啟動新版才會生效」。
  - `test/analyze_run.py`：位置跳動改用「單一控制週期位移 > 3 cm」判定（原本用速度，t_s 只到 0.01 s 會誤判出 378 次）；
    近障礙點依位置與時間合併成「次」，並標出前後 1 秒內是否有位置跳動。
- **影響檔案**：`turtlebot3_ccpp/scripts/map_server.py`、`tools/sync_to_robot.sh`、`test/analyze_run.py`
- **結果 / 驗證**：`py_compile` 通過；`analyze_run.py 20261126-121423` 輸出如上。版本記錄的修正要下一次「同步後未重啟」才會看到警告事件。

---

## 2026-11-26　feat(coverage,nav)：規劃與循跡紀錄、降低循跡修正力道（減少蛇行）

- **類型**：feat / tune（分支 `feature/astar-nav`）
- **背景**：A* 第一次實車（任務 20261126-113553，dd7af0d）70/70 到達、零受困、實際覆蓋 95.5%，但使用者看到車子走直線歪歪的、撞到障礙一兩次。分析紀錄：
  - 水平直行每趟 y 擺幅中位 4 cm；直行時車頭與掃描線夾角中位 5.1°、**90% 達 23.5°**（蛇行）。
  - 軌跡中 2 次 6～8 cm 的位置跳動（換算 0.6～0.8 m/s，車子最快 0.12 m/s → SLAM 修正造成）。
  - 兩處車中心離障礙格中心 0.10～0.11 m（< 車身半寬 0.089＋半格 0.025），可能就是擦撞點：113553 的 26.8 s（直線循跡、車頭偏 5～14°）、113336 的 13.0 s（A*）。
  - **規劃路線沒有存檔**：用任務前 1 分鐘存的地圖重算得到 72 路點／5 cell，實際是 70／4（SLAM 地圖一直在變），無法重建。
- **做了什麼**
  - 任務開始時存 `data/coverage/<task>_plan.json`（路點、line/move、中途點、外圈、cell、主軸、循跡參數、版本）與
    `<task>_grid.npz`（規劃當下的原始地圖、去雜點地圖、可走區、解析度與原點）。
  - 直線循跡每個控制週期（20 Hz）記一列到 `<task>_track.csv`：位置、朝向、側偏、方向誤差、修正角、速度指令、所屬段（原地轉正也記）。
  - 循跡：`LINE_K_CTE` 2.5 → 1.0，新增修正角上限 `LINE_CORR_MAX` = 10°（原本無上限；偏 2 cm 就要轉 16°、7 cm 跳動會要轉 39°）。
  - `test/sim_coverage.py`：新增 SLAM 位置誤差模型（每走 0.3 m 修正一次 N(0, σ)、每約 6 m 一次大跳動）、指令延遲、可覆寫循跡參數，
    輸出「車子以為的側偏」與「真實側偏」。新增 `test/analyze_run.py`：讀實車紀錄算循跡品質、位置跳動、擦撞風險（規劃當下地圖）。
- **影響檔案**：`turtlebot3_ccpp/scripts/map_server.py`、`test/sim_coverage.py`、`test/analyze_run.py`（新）
- **結果 / 驗證**（模擬，假設值：σ 2 cm、7 cm 跳動、指令延遲 0.1／0.2 s；5 組參數 × 2 延遲 × 3 種子 = 30 次，取中位數）

| 參數（K_CTE／上限） | 方向誤差 90% | 真實側偏 95% | 覆蓋 | 到達 |
|---|---|---|---|---|
| 2.5／無（舊） | 16.6～16.9° | 4.2～4.4 cm | 94.6～96.3% | 100% |
| 2.5／10° | 10.0～10.5° | 3.8～3.9 cm | 95.0～95.9% | 100% |
| 1.5／15° | 10.7～12.1° | 3.7～4.0 cm | 94.2～96.1% | 100% |
| **1.0／10°（採用）** | **8.1～8.4°** | 3.7～4.0 cm | 95.5～95.9% | 100% |
| 1.0／無 | 8.5～9.0° | 3.8～4.0 cm | 95.0～96.1% | 100% |

  - 結論：新參數讓車頭擺動約減半；**真實側偏幾乎不變**，因為車子只能照「它以為的位置」走，側偏主要受 SLAM 定位誤差限制。
    模擬的 σ 是以「舊參數下方向誤差中位約 5°」對齊實車選的，誤差模型與延遲都是假設，**要用下一次實車的 track.csv 驗證**。
  - `analyze_run.py` 在模擬紀錄上可正常輸出三項分析；舊紀錄（無 plan/track）會提示缺檔。track.csv 約 1.8 KB/秒。
  - **尚未實車。**
- **未處理（已和使用者討論，排在之後）**：防撞缺口——規劃後地圖凍結、安全邊距 0.10 m 小於外接圓 0.11～0.15 m、原地轉身與側後方沒有光達檢查、光達 0.12 m 盲區。

---

## 2026-11-26　chore(vcs)：基準 tag 改名 v1.0-baseline → v1.0.0

- **類型**：chore
- **做了什麼**：依版控規範的 `vX.Y.Z` 格式，在同一個 commit（fcf4941）建立附註 tag `v1.0.0` 並推上 GitHub，確認遠端已有之後才刪除本地與遠端的 `v1.0-baseline`。
  README、GIT_CONVENTION（目前的 tag 表）、衝刺計畫的提及一併更新；本日志較早的條目保留原名，不改歷史。
- **結果 / 驗證**：`git ls-remote --tags origin` 只剩 `v1.0.0`（→ fcf4941）。另有一個更早的 `v0.1.0` 只存在本地，未動。

---

## 2026-11-26　feat(nav)：自寫 A* 跨區導航＋nav_mode 切換（A* vs move_base 對照實驗用）

- **類型**：feat（分支 `feature/astar-nav`）
- **背景**：專題目標 (3)「證明 DWA 不好、改用 A* 更穩」。11/11 實測唯一一次受困：交給 move_base 的跨區段，車子離牆 0.20 m，
  DWA 回報 `Rotation cmd in collision` 83 次＝判定原地轉會撞而不動。之前的 own_nav 仍借 move_base 的 `make_plan`（navfn）算路線，
  且失敗後退回 move_base，無法乾淨比較。和使用者確認的定義（Q3–Q7）：
  - 比較的是兩套導航：**astar**＝自寫 A* 算路線＋自寫循跡開車，完全不讓 move_base 開車、失敗不退回；
    **movebase**（對照組，B1）＝所有路點都交 move_base（navfn＋DWA）。
  - A* 只用在覆蓋的跨區移動；自動建圖仍用 explore_lite＋move_base（目標 (1) 只要求可展示）。
  - 場地內無動態障礙物；主要指標：受困次數、實際覆蓋率。
- **做了什麼**
  - 新增 `scripts/astar.py`（零 ROS 依賴）：在覆蓋規劃同一張可走區（去雜點＋安全邊距）上做 8 鄰格 A*（octile 啟發、不切牆角）；
    每格乘「離牆懲罰」1 + 3 ×（0.15 − 離牆距離）/ 0.15，讓路線走通道中間；起終點不在可走區時吸附到 0.30 m 內最近可走格；
    RDP（0.04 m）簡化，簡化段若切出可走區就換回原始格點。
  - `map_server.py`
    - `_drive_to()`：直線可走就直走，否則改用自寫 A*（移除 `_nav_plan`／`/move_base/make_plan`）；每次規劃記事件（段數、長度、毫秒）。
    - `_run_coverage()`：依 `cov_info['nav_mode']` 選方法鏈，兩種模式重試次數相同（1 + RETRY_MAX），同一方法第二次起先脫困：
      astar＝`line → astar ×3`；movebase＝`move_base ×3`。astar 模式不需要 move_base action server。
    - `/coverage/start` 收 JSON `nav_mode`（預設 astar）；整個任務固定，「從中斷處繼續」沿用。
    - 指標與 `coverage_runs.csv` 新增 `nav_mode`、`n_stuck`（受困停止次數）、`n_escape`（脫困次數）、`synced`（車上 `.synced_commit`，供追溯）。
      CSV 欄位改變，舊檔會自動改名 `coverage_runs_old_<時間>.csv` 保留。
  - 網頁（手機 `launcher.html`、電腦 `index.html`）：開始覆蓋旁加「導航方式」下拉選單；任務指標多「導航方式」「受困次數」。
  - 新增 `test/astar_bench.py`（A* 離線驗證）、`test/sim_coverage.py`（假 ROS 模擬整個覆蓋任務）；CMakeLists 安裝 `astar.py`。
- **影響檔案**：`turtlebot3_ccpp/scripts/astar.py`（新）、`scripts/map_server.py`、`web/launcher.html`、`web/index.html`、
  `test/astar_bench.py`（新）、`test/sim_coverage.py`（新）、`CMakeLists.txt`
- **結果 / 驗證**
  - `astar_bench.py`（合成 2 張＋11/11 實測地圖 3 張，各 100 組隨機起終點）：同連通區找到率 100%、穿牆段 0；
    路線中段離障礙中位數 0.20–0.25 m、最小 0.10–0.20 m。
    規劃時間：先裁切到可走區外框再算（實測地圖 384×384 格、可走區只占中間一小塊）；樹莓派實測地圖中位 200 → 21 ms（最大 257 → 41 ms），PC 7 → 0.6 ms，路線結果完全相同。
    同測試把離牆懲罰關掉（W_CLEAR=0）：中位數 0.16–0.21 m、最小降到 0.05 m → 懲罰項確實讓路線離牆更遠。
  - `sim_coverage.py`（差速車模型、3% 輪速誤差，/scan 無障礙）：
    astar 在三張實測地圖 82/82、73/73、71/71 路點全到，零脫困零受困，實際覆蓋 96.3%／95.7%／98.0%，move_base 開車 0 次；
    movebase 在假 move_base 不僵住時 82/82；設定每個目標 30%／60% 機率僵住時，分別脫困 20／74 次、跳過 1／15 點、受困 0／1 次，
    驗證失敗→脫困→重試→跳過→受困停止的流程與計數正確。**僵住機率是人為設定，不是 DWA 的證據。**
  - JS 語法以 `node --check` 通過；`py_compile` 通過；車上 scipy 1.10.1 有 `distance_transform_edt`。
  - **尚未實車跑。**
- **待辦**：實車驗證 astar 模式（轉角、吸附段）；依實驗規則打 tag 後兩種模式各跑 ≥3 次。

---

## 2026-11-26　chore(vcs)：版本統一、車上資料備份、資料夾整理

- **類型**：chore / feat(tools)
- **背景**：程式同時存在電腦、車上、GitHub；GitHub `main` 停在 PR #2、落後 `rebuild`；車上實驗紀錄（`data/`、`maps/`）只存在車上、沒有任何備份。
- **做了什麼**
  - 確認車上一致：車上 `.synced_commit`＝26f1a1f，19 個程式檔 sha1 與 HEAD 逐檔相同（之後的 commit 都只改文件）。
  - `tools/sync_to_robot.sh` 新增 `--check`：以 `git archive` 打包 HEAD（與實際同步內容相同，含 LF 轉換）後逐檔比 sha1，列出車上「多出／缺少／內容不同」，不改車上。
  - 新增 `tools/pull_from_robot.sh`：車上 `data/`、`maps/` → `experiments/robot/`，只增不刪，每次在 `pull_log.txt` 記時間與車上版本。
    首次備份 676 KB（coverage 1 次、explore 3 次紀錄，6 月與 11/11 地圖）；`coverage_runs.csv` 末列 97.73%／13.65 m／16.79 m 與 11/11 日志一致。
  - 資料夾整理：根目錄三份 README 審查報告 → `docs/05_開發日志/審查/`；系展申請單 → `docs/08_系展/`；
    刪除本地 `turtlebot3_ccpp/maps/`（6 月舊地圖，逐檔確認已包含在車上備份內）；新增 `media/`（影片素材，不進版控）。
  - `.gitignore`：`maps/` 改為只忽略 `turtlebot3_ccpp/maps/`、`turtlebot3_ccpp/data/`（否則 experiments 內的 maps 也被忽略）；新增 `*.bag`、`media/`、`.claude/`（含 94 MB 技能包與本機設定）。
  - README 新增「版本與資料放在哪裡」與更新後的改程式流程；`docs/README.md` 補 07、08。
- **影響檔案**：`turtlebot3_ccpp/tools/sync_to_robot.sh`、`turtlebot3_ccpp/tools/pull_from_robot.sh`（新）、`.gitignore`、`README.md`、`docs/README.md`、`experiments/`（新）
- **結果 / 驗證**：`sync_to_robot.sh --check` 回報「✓ 車上 19 個程式檔與 HEAD 完全一致」；備份檔數與車上 `find data maps -type f` 相同。
- **待辦**：`rebuild` 合回 `main` 並打 `v1.0-baseline`；車上 SD 卡已用 88%（15 GB 剩 1.7 GB），錄 rosbag 前要注意。

---

## 2026-11-25　docs(slides)：成果動畫簡報（13 頁網頁簡報，按一下播一段）

- **類型**：docs
- **背景**：展示要交 3 分鐘成果影片；逐頁規格與旁白已寫在 `docs/07_衝刺計畫/簡報生成.md`，需要能直接剪輯的動畫畫面。
- **做了什麼**
  - 用 huashu-design skill（裝在 `.claude/skills/`，未進版控）走設計流程：三方向初稿 → 使用者指定普普漫畫風 → 霓虹夜景風 →
    「太 AI、太多幾何框」→ 定稿為深青綠底、無框、真實路徑當光帶、字級對比。每次調整的原話記在 `direction-approved.md`。
  - `docs/07_衝刺計畫/成果影片簡報/`：13 鏡 HTML 動畫（自寫時間軸引擎，畫面完全由 t 決定）＋ `index.html` 連播
    ＋ `tools/render.mjs` 逐格截圖經 ffmpeg 輸出 1080p30 MP4。
  - 路徑、PCA 主軸、cell 分解直接取自 `coverage_planner.plan()`（`tools/gen_data.py` 匯出 JSON，SVG 描線）；
    04 鏡用 2026-06-27 實測 gmapping 快照 47 張逐格播放。對照用的舊版做法一律標「示意」。
  - 未拍的實機畫面留「REC 待拍」區；數據總表的【待填】未填任何假設值。
  - `tools/gen_figs.py` 的 `room_map()` 加參數（可不含障礙、自訂場地與障礙尺寸），不影響既有呼叫。
- **影響檔案**：`docs/07_衝刺計畫/成果影片簡報/`（新）、本日志
- **結果 / 驗證**：13 鏡每鏡截中段與最後一格檢查（修掉：水平線因濾鏡區域為 0 而消失、節點字被切、cell 標籤翻轉、外圈提早出現等）；
  MP4 由 ffmpeg 讀回確認 1920×1080、30 fps。
- **追加（同日）**：使用者說明要的是「簡報動畫」不是 .mp4 → 引擎改成分段播放：每頁 `steps` 停頓點，→／空白／點擊播下一段、←回上一段，
  最後一段再按換頁、第一段按上一段回上一頁（顯示播完狀態）；`index.html` 改成配合分段的播放器（F 全螢幕）。
  `tools/test_play.mjs` 模擬按鍵驗證分段、跳段、上一段、跨頁；`frames.mjs … steps` 截每段停格逐一檢查。
- **待辦 / 已知問題**：實機畫面（S1–S3）待拍後放進 11 頁；P9 數據總表待重複實驗後填；沒有做可編輯 PPTX（動畫版不適用）。

---

## 2026-11-11　feat(coverage)：跨區移動改由自己開；實測分析；專案架構說明與收工交接

- **類型**：feat / docs
- **實測分析**（任務 20261111-112057，車上版本 fb0ef34，紀錄在 `data/coverage/20261111-112057_*`）
  - 實際覆蓋率 **97.7%**（規劃 99.4%）、83/83 路點、零跳過、執行 322 秒、規劃 13.65 m／實走 16.79 m。
    上一版同場地：71%、436 秒。DWA 失敗 1127 → 209 次（都發生在交給 move_base 的段落）。
  - 75 段直線循跡只有 1 段（路點 70）停滯改交 move_base，16 秒後到達。
  - **唯一一次受困**：路點 14～16（kind＝move，交給 move_base）。車子停在離最近障礙 0.20 m 處 30 秒幾乎沒動，
    日誌 `Rotation cmd in collision`／`Invalid Trajectory` 各 83 次＝DWA 判定原地轉會撞；
    `_escape()` 要求行進方向 ≥ 0.25 m 空間才動，也不動 → 連續 3 點失敗判定受困。使用者按繼續後順利跑完。
- **做了什麼**
  - `map_server._drive_to()`：從目前位置到目標的直線整段在規劃用可走區內 → 直接直線循跡；否則呼叫 `/move_base/make_plan`
    （只借全域規劃器算繞障路線，不讓 move_base 開車），RDP（0.04 m）簡化後逐段直線循跡。
  - 每個路點依序嘗試 `line → own_nav → move_base → (脫困) move_base`，事件記錄每次改用下一種的原因。
  - `ESCAPE_CLEAR` 0.25 → 0.18。
  - 新增 `docs/專案架構說明.html`（白話全貌＋未來規劃），根目錄 `README.md` 加「目前狀態／下次從這裡開始」，`docs/README.md` 連結。
- **影響檔案**：`turtlebot3_ccpp/scripts/map_server.py`、`docs/專案架構說明.html`（新）、`README.md`、`docs/README.md`
- **結果 / 驗證**
  - 假 ROS 模擬（第三次實測地圖、3% 輪速誤差，**move_base 開車設成永遠停滯**、`make_plan` 回傳 L 形折線、強迫 > 0.5 m 的跨區走 make_plan）：
    82/82 路點全到（line 72、own_nav 10，其中 3 次用 make_plan），move_base 開車 0 次，實際覆蓋率 96.95%。
  - 車上（26f1a1f）啟動系統後實際呼叫 `/move_base/make_plan` 成功（回傳 9 點）、`/scan` 5 Hz；測完已停止系統。
  - **尚未實車跑覆蓋。**
- **待辦 / 已知問題**：見根目錄 README「下次從這裡開始」與架構說明第 12 章。

---

## 2026-11-11　feat(coverage)：覆蓋執行改善——直線循跡（A）、導航調校（B）、線距重疊＋外圈（C）、真實掃過範圍與紀錄（D）

- **類型**：feat / tune
- **背景**（任務 20261111-104832 的日誌與 CSV）：規劃 7.4 m 實走 10.2 m（多 38%）、436 秒（每路點 12 秒）、3 次受困；
  `DWA planner failed to produce path` 出現 1127 次、控制迴圈 27 次趕不上 10 Hz。
  規劃覆蓋率 76%、實際 71%，而且覆蓋半徑用 0.10 m（比車身寬 0.178 m 還寬）算，數字偏樂觀。
  線距 0.18 m 與車身同寬，走歪就留縫；牆邊一圈（安全邊距＋線尾內縮）完全沒規劃。
- **做了什麼**
  - A：`map_server._follow_line()`：路點 kind 為 `line` 且車子就在上一個路點附近時，由自己控制直行——
    方向誤差 > 14° 先原地轉正（到 3° 內），再以 `角速度 = 2.0 ×（方向誤差 − atan(2.5 × 側向偏移 / 速度)）` 修正前進，
    線尾減速（下一段方向差 < 15° 則不減速直接接續）；前方 ±20° 雷射 < 0.13 m 或停滯 3 秒 → 改交 move_base（不算失敗），
    其後沿用原本的脫困重試、跳過、受困停止流程。kind 為 `move`（進入新 cell、開到外圈起點）才用 move_base。
    停止或結束時一律送零速度。
  - B：`start.launch`：`local_costmap/inflation_radius` 1.0 → 0.25（與全域一致）、`controller_frequency` 10 → 5；
    gmapping `linearUpdate` 0.2 → 0.3、`angularUpdate` 0.1 → 0.15（減輕樹莓派負擔）。
  - C：`coverage_planner`：`SPACING` 0.18 → 0.14（重疊約 20%）、`COVER_R` 0.10 → 0.089（車身半寬）；
    `plan()` 新增 `kind`（line/move，換行段確認整段可走才算 line）與 `perimeter`：最大可走區往內 1 格（中心離牆約 0.15 m）
    填洞後以 Moore 鄰域追蹤外緣、RDP 簡化成直線段，從最近的頂點起繞一圈。`coverage_bench.py` 改傳 `perimeter=False`。
  - D：網頁（手機＋電腦版）新增「實際掃過範圍」圖層：沿軌跡畫車身寬的半透明綠帶；覆蓋軌跡改每 5 cm 記一點；
    `/coverage/status` 多回傳 `cover_r`。每次覆蓋結束寫 `data/coverage/<task>_{path.csv,timeline.csv,events.txt,map.png}`
    （停止後繼續會累積同一任務；事件含每個路點用 line 或 move_base 到達、花幾秒、改用 move_base 的原因、跳過、受困）。
- **影響檔案**：`turtlebot3_ccpp/scripts/map_server.py`、`scripts/coverage_planner.py`、`launch/start.launch`、
  `config/gmapping_params.yaml`、`web/launcher.html`、`web/index.html`、`test/coverage_bench.py`
- **結果 / 驗證**
  - 用第二次實測地圖（explore_20261111_104808）離線比較，以真實車寬 0.089 m 計算規劃覆蓋率：
    舊設定 69.7%（與實測 71% 吻合）→ 新設定無外圈 92.8% → 新設定＋外圈 100%；路點 32 → 71、路徑 6.1 → 14.7 m。
  - 假 ROS 模擬（差速車模型，加 3% 輪速誤差與雜訊，move_base 以直線內插代替）：71 個路點全到（line 66、move_base 5），
    軌跡離規劃路線平均 0.4 cm、95% 1.9 cm、最大 3.1 cm；以車身寬計實際覆蓋率 96.6%；紀錄檔四個都正確產生。
  - 車上整套重啟後確認：`local_costmap` 的 `inflation_layer/inflation_radius=0.25`、`controller_frequency=5.0`、
    gmapping 0.3／0.15、`cover_r=0.089`。**尚未實車跑覆蓋。**
  - 驗證時遇到一次光達驅動啟動後沒有資料（`/scan` 無輸出、move_base 一直等 map 座標）；直接對 `/dev/ttyUSB0` 下啟動指令有正常資料，
    整套再重啟一次就恢復。原因未明，先記錄。
- **待辦 / 已知問題**
  - 實車確認直線循跡參數（速度 0.12 m/s、增益）與外圈離牆距離是否合適；外圈轉角處車子離兩面牆約 0.15 m，第一次請在旁邊看。
  - 控制台可考慮偵測「系統啟動後 /scan 沒資料」並在網頁提示。

---

## 2026-11-11　feat(slam,coverage)：減少地圖假障礙——調 gmapping 參數（A）＋規劃前去雜點（B）

- **類型**：feat / fix
- **背景**：第一次在 1.06 × 1.47 m 場地自動建圖（任務 20261111-102235）：55 秒、走 4.1 m、回起點誤差 3 cm，
  scan matching 分數穩定（163 次僅 1 次失敗），定位正常；但地圖空地裡有零星假障礙、右牆被畫成 2～3 格厚。
  覆蓋規劃直接用這張圖，規劃前又把障礙膨脹 10 cm，一顆 5 cm 雜點就變成約 25 cm 的禁區。
- **做了什麼**
  - A：新增 `config/gmapping_params.yaml` 與 `launch/slam_gmapping.launch`（含 turtlebot3_remote，等同官方 slam launch），
    `map_server.slam_launch()` 在 gmapping 時改用本套件版本。改動：`occ_thresh` 0.25→0.5、`linearUpdate` 1.0→0.2、
    `angularUpdate` 0.2→0.1、`maxUrange` 3.0→2.0。
  - B：`coverage_planner.remove_noise()`：8 鄰接相連、不超過 3 格的障礙團塊視為雜點，改成空地（只作用在規劃用的地圖）。
    `coverage_start()` 與「安全邊距」圖層都改用去雜點後的地圖；新增 `/map_noise.png`，手機與電腦版網頁多一個黃色「雜點（規劃忽略）」圖層；
    `cov_info`／覆蓋 CSV 多 `n_noise`。`_log_run()` 發現 CSV 欄位不同時，舊檔改名為 `coverage_runs_old_<時間>.csv` 保留。
  - `sync_to_robot.sh` 同步範圍加 `config/`；CMakeLists 安裝 `config/`。
- **踩到的坑（已修）**：一開始在參數檔加了 `maxRange: 3.5`，結果地圖憑空多出半徑 2 m 的一整圈空地。
  原因：LDS-01 收不到反射時回報 0，slam_gmapping 把它換成 range_max（3.5）；預設 maxRange＝3.49 會忽略這種讀值，
  設成 3.5 反而被當成「此方向 maxUrange 內都是空地」。當時一圈 360 筆有 153 筆是 0。已拿掉 `maxRange`（commit 4d434a9）。
  另外 ROS 參數伺服器會保留舊參數，改參數檔後要**整套系統重啟**，只按「重新建圖」不會生效。
- **影響檔案**：`turtlebot3_ccpp/config/gmapping_params.yaml`（新）、`launch/slam_gmapping.launch`（新）、
  `scripts/coverage_planner.py`、`scripts/map_server.py`、`scripts/launcher.py`、`web/launcher.html`、`web/index.html`、
  `tools/sync_to_robot.sh`、`CMakeLists.txt`
- **結果 / 驗證**
  - 用第一次實測存下的地圖離線比較：去雜點移除 4 格（空地中 2 顆假障礙＋牆外 2 顆），中間方框與四面牆保留；
    可規劃面積 1.08 → 1.16 m²（+7%），cell 3 → 4、路點 31 → 32。
  - 車上整套重啟後確認 gmapping 參數生效（`occ_thresh=0.5` 等、`maxRange` 未設），`/map_noise.png` 正常。
  - 驗證當下車子周圍的地圖有多條光束穿出場地外，光達在部分方向看得很遠，和第一次實測的封閉場地不同，可能是車子或圍牆位置變了。
    **新參數的實際效果還沒在同一場地重跑比較。**
- **待辦 / 已知問題**：請在封閉場地內按「清空地圖、重新建圖」後再跑一次「自動建圖 → 自動覆蓋」，比較兩次的雜點數、牆厚與規劃覆蓋率。

---

## 2026-11-11　feat(explore)：自動建圖紀錄（摘要、每秒過程、軌跡、事件、軌跡疊圖）

- **類型**：feat
- **做了什麼**：`map_server.py` 每輪自動建圖結束（完成、停止、錯誤皆然）寫出：
  - `data/explore_runs.csv`：每輪一列摘要——結果、結束原因、總時間／探索時間、起訖已知面積、剩餘邊界、
    行走距離、回起點結果與誤差、起訖電壓、地圖檔名、當次參數。
  - `data/explore/<task>_timeline.csv`：每秒一列（狀態、已知面積、邊界數、x/y/朝向、累計距離、電壓），探索與回起點階段都記。
  - `data/explore/<task>_path.csv`：行走軌跡，每 5 cm 一點（只在探索與回起點時記，不影響覆蓋軌跡 `robot_path`）。
  - `data/explore/<task>_events.txt`：摘要＋事件時間線，含 explore_lite 自己在 `/rosout` 印的 INFO 以上訊息、使用者按停止。
  - `data/explore/<task>_map.png`：最後的地圖放大 4 倍，疊上紅色軌跡（綠圈起點、藍圈終點）。
  - `_go_home()` 改為回傳 reached／failed／timeout／stopped。
- **為什麼**：使用者要在 1.06 × 1.47 m 的簡易場地實測，事後讓 Claude 讀紀錄評估實際成效；原本只有文字日誌和最終地圖，看不出過程與路線。
- **影響檔案**：`turtlebot3_ccpp/scripts/map_server.py`
- **結果 / 驗證**：本地以假 ROS 模組載入 map_server，用合成地圖模擬一輪（走一圈、回起點），
  五個檔案皆正確產生，CSV 欄位與疊圖正確。尚未在車上實跑。
- **待辦 / 已知問題**：`data/` 不在同步範圍，要用 scp 取回分析。

---

## 2026-11-11　feat(explore)：自動建圖（frontier 探索）與開機自動啟動

- **類型**：feat
- **做了什麼**（設計見 `docs/01_學習資料/開機自動建圖說明.html`）
  - `map_server.py`
    - 以子行程管理 `explore_lite`（`rosrun explore_lite explore`，參數在 `EXPLORE_PARAMS`），寫法同 SLAM 管理。
    - 新增探索狀態 `exp_status`：idle → countdown → exploring → saving → returning → done（或 stopped／error）。
      `manual_allowed()` 改為「覆蓋執行中或建圖中都不能遙控」；建圖中不能開始／繼續覆蓋，覆蓋中不能開始建圖。
    - 完成條件（任一）：explore_lite 在 `/rosout_agg` 印出 "Exploration stopped"、已知面積 90 秒沒變大、超過 10 分鐘、`/battery_state` < 10.8 V。
      收尾：收掉 explore_lite → 取消 move_base 目標 → `map_saver` 存到 `maps/explore_<時間>.pgm/.yaml` → 開回起點（90 秒逾時）。
    - `map_callback()` 多算已知空地面積與邊界段數（空地且碰到未知、長度 ≥ 0.3 m 的相連段），給網頁顯示。
    - 新路由 `/explore/start`、`/explore/stop`；`/coverage/status` 多回傳 `explore`，`manual` 改用 `manual_allowed()`。
    - 參數 `~auto_explore`：true 時等地圖、車子位置、move_base 都就緒後倒數 10 秒自動開始。
    - 共用一個 move_base action client，按停止時能立刻取消目標；每輪探索有編號，停止後馬上再開始不會讓舊執行緒復活。
    - 重啟 SLAM 前會先停止自動建圖。
  - `start.launch`：新增 `auto_explore` 參數（預設 false），傳給 map_server。
  - `launcher.py`
    - 設定檔 `~/.ros/ccpp_launcher/config.json`（`autostart`、`auto_explore`、`model`），`/api/config` 讀寫；放在家目錄，同步程式不會蓋掉。
    - 開機自動啟動：**只在系統開機 5 分鐘內**控制台啟動時才做（同步程式造成的重啟不會自動開系統）；
      先等 `/dev/ttyACM0`（OpenCR）、`/dev/ttyUSB0`（光達）、網路 IP，最多 3 分鐘，都到齊再等 5 秒才啟動。
    - `start()` 可帶 `auto_explore`；轉接白名單加 `explore/start|stop`；`/api/status` 多回傳 `boot`、`config`。
  - `launcher.html`：「操作」頁加「自動建圖」卡片（開始／停止、已知面積、剩餘邊界、時間），建圖中鎖搖桿與覆蓋；
    頂端步驟改「② 建圖」並依建圖狀態提示；「系統」頁加「開機自動啟動系統」「啟動後自動建圖」開關（開啟自動建圖需再確認）。
- **為什麼**：使用者要車子開機後自己把地圖建好，不用遙控繞場地。
- **影響檔案**：`turtlebot3_ccpp/scripts/map_server.py`、`launcher.py`、`launch/start.launch`、`web/launcher.html`
- **結果 / 驗證**（車上 172.20.10.5）
  - 車上 `explore_lite` 2.1.4、`map_server` 已安裝。
  - 設定開關可存檔；控制台因同步而重啟時正確顯示「不是在開機時啟動，不自動啟動」。
  - 啟動系統後 `/coverage/status` 的 `explore` 正確（已知 5.73 m²、10 段邊界），`/explore/stop`、遙控零速度正常；
    map_server 有訂閱 `/rosout_agg`、`/battery_state`；`map_saver` 指令實測可存出 .pgm/.yaml。測完已停止系統。
  - **未實測**（車子會自己移動，需要有人在旁）：實際跑完一次自動建圖、完成判定、回起點；真正重開機的開機自動啟動。
- **待辦 / 已知問題**
  - 實測後可能要調 `min_frontier_size`、`EXPLORE_IDLE_S`、`EXPLORE_MAX_S`。
  - 建圖時速度沿用 DWA 官方上限，若太快可降 `max_vel_x`。

---

## 2026-11-11　refactor：車上程式集中到 `turtlebot3_ccpp/`

- **類型**：refactor
- **做了什麼**：`scripts/ launch/ web/ test/ tools/ CMakeLists.txt package.xml` 移入 `turtlebot3_ccpp/`（本機 `maps/` 一併移入，不進版控），
  與車上 `~/catkin_ws/src/turtlebot3_ccpp` 一對一；`sync_to_robot.sh` 改打包 `HEAD:turtlebot3_ccpp`；新增根目錄 `README.md` 說明結構與改程式流程；
  `docs/README.md` 的 `coverage_bench` 指令改新路徑。
- **為什麼**：使用者要所有上車的程式集中在一個資料夾，和文件分開。
- **結果 / 驗證**：同步 f4aa390 到車上，沒有任何檔案被刪除或變動（內容與先前相同）。
- **待辦 / 已知問題**：`docs/01_學習資料` 各章內文的 `scripts/...` 路徑是相對於套件資料夾來寫的，未逐一改寫。

---

## 2026-11-10　feat(launcher)：車上常駐控制台（手機開熱點即可啟動／觀察專案）＋同步腳本

- **類型**：feat / chore
- **做了什麼**
  - 新增 `scripts/launcher.py`：不依賴 ROS master 的常駐 Flask 服務，port 8000。
    - `/api/start`（可選 burger/waffle/waffle_pi）以獨立行程群組 `roslaunch turtlebot3_ccpp start.launch`；
      每次啟動依車子**當下 IP** 設定 `ROS_MASTER_URI`／`ROS_HOSTNAME`，換熱點 IP 變了也不用改 `.bashrc`。
    - `/api/stop`：SIGINT（同 Ctrl+C，讓 map_server 停車、收 SLAM）→ 20 秒逾時 SIGTERM → SIGKILL，最後清殘留 `turtlebot3_slam.launch`。
    - 能偵測從終端機手動開的 start.launch（顯示「執行中（終端機開的）」，也能停）。
    - `/api/status`：行程狀態、地圖頁（8080）是否就緒、`rosnode list`、`/battery_state` 電壓、
      覆蓋任務摘要（轉讀 map_server `/coverage/status`，只留進度與指標）、CPU 溫度／負載／記憶體／硬碟。慢的查詢都在背景執行緒每 2 秒輪詢，API 只讀快取。
    - `/api/log`：roslaunch 輸出日誌（存在 `~/.ros/ccpp_launcher/`，保留最近 20 份）。
    - `/api/power`：先停專案再 `sudo -n systemctl poweroff/reboot`，拔電前安全關機。
  - 新增 `web/launcher.html`：手機優先的單頁控制台，無外部資源（熱點沒網路也能開）。
  - 新增 `tools/ccpp-launcher.service`、`tools/install_launcher.sh`：開機自動啟動控制台；
    `KillMode=process`，重啟控制台不會殺掉正在跑的 roslaunch。
  - 新增 `tools/sync_to_robot.sh`：以 `git archive HEAD` 把已 commit 的實作程式推上車（LF 換行），
    有未 commit 的程式變更就拒絕；刪除車上 HEAD 已不存在的檔案；寫 `.synced_commit`；`--build` 會 catkin_make；控制台在跑就自動重啟。
- **為什麼**：使用者要求車子自己架網頁，讓連同一熱點的手機也能用瀏覽器啟動、觀察專案；
  並且從此每次改程式都要版控、本地與車上同步。
- **影響檔案**：`scripts/launcher.py`、`web/launcher.html`、`tools/*`
- **結果 / 驗證**：`py_compile`、`bash -n`、頁面 JS 語法檢查通過；以模擬 API 在 375 px 手機寬度預覽版面正常。
  撰寫期間車子（172.20.10.5）SSH 逾時離線，**尚未部署與實車驗證**。
- **待辦 / 已知問題**
  - 電池電壓讀 `/battery_state`，門檻以 Burger 3S 鋰電池設定（<11.0 V 紅、<11.5 V 黃）。

---

## 2026-11-10　feat(launcher)：8000 整合 8080，手機一個網址操作全部功能

- **類型**：feat
- **做了什麼**
  - `launcher.py`：新增 `proxy()`，把 map_server（8080）的 `map*.png`、`robot_state`、`scan`、
    `coverage/status|runs.csv`（GET）與 `coverage/start|stop|resume`、`teleop`、`slam/restart`（POST）
    轉接到 8000，同源呼叫；白名單以外一律 404，map_server 沒起來回 502「系統未啟動」。
    開始覆蓋、重啟 SLAM 逾時 40 秒，其餘 5 秒。
  - `launcher.html` 全面改版成手機分頁式介面：
    - 頂端：系統狀態、三步驟（① 啟動系統 → ② 遙控建圖 → ③ 自動覆蓋）與「下一步」提示，依狀態自動切換。
    - 「操作」：系統未啟動時只顯示一顆「啟動系統」大按鈕；就緒後是地圖（畫法與 8080 相同）、
      開始／繼續／結束、按住式 3×3 搖桿（放開、手指滑出、切到背景都會停車）、直立速度滑桿、可收合的圖層與圖例（記住選擇）。
    - 「數據」：本次任務 12 項指標、CSV 下載（尚無紀錄時跳提示，不再跳到錯誤頁）、車況。
    - 「系統」：啟動／停止、車型、重新建圖、ROS 節點、系統日誌、關機／重開、電腦版 8080 連結。
  - 8080 電腦版頁面不變。
- **為什麼**：使用者要 8000 與 8080 整合，讓手機操作更方便易懂。原本 8080 是寬螢幕側欄版面，手機上很擠，且要記兩個網址。
- **影響檔案**：`scripts/launcher.py`、`web/launcher.html`
- **結果 / 驗證**（車上 172.20.10.5，手機尺寸 375×812）
  - 按「啟動系統」約 40 秒後地圖出現，步驟自動跳到「② 遙控建圖」；數據、系統分頁顯示正常（電池 12.46 V）。
  - 轉接：`/map.png` 200（約 0.12 s）、`/coverage/status` 200、`/teleop` 送零速度回 `ok`、白名單外路徑 404、系統未啟動時 502。
  - CSV 尚無紀錄時跳出提示。測完已從 API 停止系統，無殘留行程。
  - **未實測**：實際按住搖桿讓車子移動、自動覆蓋全程（需有人在車旁）。
- **備註**：測試期間硬碟剩餘從 4.0 GB 降到 3.1 GB，原因是 VS Code 遠端連線重新安裝了 `~/.vscode-server`（658 MB），不是程式寫檔。

---

## 2026-11-10　部署車上控制台並實測；fix(launcher)：電池電壓讀不到

- **類型**：fix / chore
- **做了什麼**
  - `sync_to_robot.sh` 同步到車上，`install_launcher.sh` 安裝 `ccpp-launcher.service`（已 enable，開機自啟）。
  - 實測發現 `rostopic echo -n 1 /battery_state/voltage` 在樹莓派上要約 6.5 秒，超過原本 6 秒逾時，電壓一直是空的。
    改成獨立的 `_battery_poller` 執行緒、逾時 20 秒、每 20 秒讀一次，不再卡住主輪詢；`rosnode list` 逾時 5 → 8 秒。
- **影響檔案**：`scripts/launcher.py`
- **結果 / 驗證**（從同熱點的筆電呼叫 `http://172.20.10.5:8000`）
  - 啟動：約 38 秒地圖頁（8080）就緒，8 個節點（map_server、move_base、turtlebot3_core／lds／diagnostics、gmapping…）。
  - 同步新版時控制台自動重啟，正在跑的 roslaunch 沒被中斷，狀態顯示「執行中（終端機開的）」，電壓讀到 12.48 V。
  - 停止：約 12 秒回到「未啟動」，`pgrep` 確認 roslaunch／rosmaster／gmapping／move_base／map_server 無殘留。
  - 手機寬度實頁畫面正常。尚未按「關機／重新開機」實測（會真的關掉車子）。

---

## 2026-11-10　chore：車上程式與本地同步、整理本地與車上資料夾

- **類型**：chore
- **做了什麼**
  - 比對車上 `~/catkin_ws/src/turtlebot3_ccpp`（172.20.10.5）與本地：車上停在 2026-09-24 版
    （有線尾內縮、脫困／受困處理，但沒有「掃描線中途點」與「任務指標／CSV」），沒有本地缺少的修改。
  - 先把車上整包備份到 `~/backup/turtlebot3_ccpp_20261110_101919`，再把本地的
    `scripts/`、`launch/`、`web/`、`test/*.py`、`CMakeLists.txt`、`package.xml` 推上車（轉成 LF 換行），
    md5 與本地一致，`py_compile` 通過。
  - 車上：刪掉從 Windows 帶上去的 `__pycache__`（cpython-313）；
    `devel/lib/turtlebot3_ccpp/` 刪除舊架構留下的 7 個失效 relay（ccpp_manager.py 等），重跑 `catkin_make`。
  - 本地：刪 `scripts/`、`test/` 的 `__pycache__`；`docs/README.md` 的 03_海報 段落改成只剩 `專題海報.pdf`。
- **為什麼**：專案擱置一段時間，車上與本地版本不一致，下次實車測試前要先對齊。
- **影響檔案**：`docs/README.md`、本檔；車上套件目錄
- **結果 / 驗證**：車上檔案 md5 與本地相同、可編譯；尚未在車上 `roslaunch` 實跑。
- **車上清理（使用者確認後執行）**：刪除與專案無關的資料，硬碟 90% → 73%（剩 3.8 GB）。
  - 舊專案 `tb3_web_crtl`、`my_tb3_driver` 先打包到 `~/backup/old_packages_tb3_web_crtl_my_tb3_driver_20261110.tar.gz`
    （`tb3_web_crtl` 有 10 個未推送 commit；打包前已移除遠端網址內嵌的 GitHub 權杖）後刪除；`rosboard` 一併刪除。
  - 刪除 `~/opencv`、`~/opencv_contrib`（OpenCV 4.5.0 已裝在 `/usr/local`，`cv2` 仍可用）、
    `~/.vscode-server` 等 VS Code／AI 工具資料夾、`~/.cache`、重複的 `catkin_ws/opencr_update`，`rosclean purge` 清掉 ROS 日誌。
  - `build/`、`devel/` 清掉重新 `catkin_make`，`rospack find turtlebot3_ccpp` 正常。
- **待辦 / 已知問題**
  - 中途點與任務指標兩個功能仍未實車驗證。
  - 舊權杖需到 GitHub 撤銷；`/etc/systemd/system/tb3_web.service`（已停用、指向已刪的腳本）留給使用者自行移除。

---

## 2026-10-04　feat(web)：「規劃資訊」改為任務指標面板，並記錄每次執行數據

- **類型**：feat
- **做了什麼**
  - `coverage_planner.py`：新增 `COVER_R = 0.10`、`coverage_mask()`／`coverage_ratio()`
    （線段取樣標格後一次距離轉換）；`plan()` 多回傳 `sweeps`（依走訪順序的掃描線，不含換行銜接）。
  - `map_server.py`
    - 規劃時記錄規劃時間（含安全邊距膨脹）、規劃覆蓋率、規劃路徑長、可達面積，並保存規劃當下的可走格 `cov_grid`。
    - 新增 `cov_metrics()`：實際覆蓋率（行走軌跡在 `cov_grid` 上掃過的比例，軌跡沒變就用快取）、
      任務完成率（到達路點 / 總路點）、跳過數、累計執行時間（停止後繼續會接著算）、實際行走長。
    - `run_coverage()` 改成計時外殼，原本主體改名 `_run_coverage()`；每次結束（完成、停止、錯誤）
      把指標追加到 `data/coverage_runs.csv`（utf-8-sig）。新增 `/coverage/runs.csv` 下載。
    - `/coverage/status` 多回傳 `metrics`。
  - `web/index.html`：「規劃資訊」改為「任務指標」，分規劃／執行兩組；加 CSV 下載連結。
    原本的連通區間、臨界點、cell、主軸、λ 比從面板移除，但仍寫在 CSV 裡。
- **為什麼**：使用者要能產出實質數據（覆蓋率、規劃時間、任務完成率）做實驗比較。
  實際覆蓋率沿用規劃當下的地圖算，分母才和規劃覆蓋率一致（SLAM 執行中地圖會變大、原點會移）。
- **影響檔案**：`scripts/coverage_planner.py`、`scripts/map_server.py`、`web/index.html`
- **結果 / 驗證**：以假 ROS 模組載入 `map_server`，用合成地圖跑 `/coverage/start`、模擬行走與結束，
  指標、CSV 內容與下載路由皆正確；補點與不補點的 `sweeps` 算出相同規劃覆蓋率；網頁 JS 以 `node --check` 通過。尚未實車驗證。
- **待辦 / 已知問題**
  - 軌跡每 0.1 m 才記一點，實際覆蓋率對最後一小段略為低估。
  - 停止後再繼續，CSV 會多一列（同一個 task 編號），分析時取每個 task 的最後一列。

---

## 2026-10-04　feat(coverage)：掃描線補中途點，讓實車照直線走

- **類型**：feat
- **做了什麼**
  - `coverage_planner.py`：新增 `VIA_STEP = 0.25` 與 `_densify()`，每條掃描線依此間距補上中途點；
    `plan()` 多回傳 `via`（與 `waypoints` 等長的旗標，True = 中途點），並新增 `via_step` 參數（`inf` = 只給頭尾，同舊行為）。
  - `map_server.py`：新增 `VIA_NEAR = 0.12` 與 `cov_via`；`_go_to()` 新增 `near` 參數，
    中途點只要車子進入半徑就直接送下一點（不取消目標，move_base 會無縫接手），不等 move_base 判定到達；
    輪詢間隔 0.5 → 0.2 秒，避免高速通過中途點時才發現。線頭、線尾仍照舊等到達並對準方向。
  - `test/coverage_bench.py`：改呼叫 `plan(..., via_step=math.inf)`，因為統計假設路點是「掃描線、銜接線」兩兩交替。
- **為什麼**：實車測試發現每條來回線只送頭尾兩點，navfn 依 costmap 成本自己找路，
  長線常被拉彎、沒照直線走，覆蓋會漏。補點把路線釘在掃描線上；
  中途點若也等 move_base 判定到達，DWA 每點都會減速停車再轉向，所以改成「靠近就換點」。
- **影響檔案**：`scripts/coverage_planner.py`、`scripts/map_server.py`、`test/coverage_bench.py`
- **結果 / 驗證**：合成地圖確認中途點間距 ≤ 0.25 m、`via` 旗標線頭線尾為 False；
  `coverage_bench.py` 14 個場地數值與補點前一致（覆蓋率 94.9%～99.1%）。尚未上實車驗證。
- **待辦 / 已知問題**
  - 需實車確認：中途點是否仍有頓挫、`VIA_STEP`／`VIA_NEAR` 是否要調。
  - 路點總數變多，網頁進度「done / total」的分母會跟著變大。

---

## 2026-09-29　docs(簡報)：DAHV_tdfklM 精簡為「圖為主、字為輔」並補上 22 頁講稿

- **類型**：docs
- **做了什麼**
  - 依使用者要求「整理核心重點、盡量用圖搭配少量文字、附上講稿」，整份簡報改寫。
  - 六步驟頁（p11～16）：「怎麼做」長段落改成 3 條短句，「產生的結果」縮成一句；
    右側實機截圖由 700 寬放大到 860 寬（p11 兩張放大到 650 寬）。
  - p3 摘要：276 px 長段落改成「問題／做法／成果」三行，右側新增覆蓋路徑成果圖（MAHVpmX51Tg）。
  - p4：刪掉背景兩張無關的房間照與底部冗長句子；「沒擺正／有擺正」示意圖左右對調，
    使其對應上方的「①地圖的方向是歪的／PCA 主軸對齊」。
  - p5：左右原本是同一張房間照，改成原始地圖（MAHVvasuUYU）對膨脹後（MAHVpnzrTkw）；
    兩個圖框原帶 -90° 旋轉，先轉正再重新定位。
  - p10、p13、p17、p19 文字精簡；p13 刪掉與「產生的結果」重複的圖說。
  - 22 頁全部寫入演講者備忘稿（講稿），含備問頁提示與常見提問清單。
- **為什麼**：原本多頁是整段文字，不適合上台講；使用者要求把要講的內容移到講稿、版面留給圖。
- **影響檔案**：無（只動 Canva 設計 DAHV_tdfklM，不含專案程式）。
- **結果 / 驗證**：已 commit 至 Canva；每頁以回傳縮圖逐頁確認版面無破圖、無文字溢出。
- **待辦 / 已知問題**
  - Canva MCP 無法改字級：`format_text` 的 `fontSize` 送出後不生效，`add_text` 新增的文字固定 16 px。
    因此「四張圖看完整流程」的 2×2 回顧頁沒有做（標題與圖說無法排到合適字級），需要的話得手動加。
  - p6 與 p7 都是系統架構，正式報告建議只留一頁。
  - 成果展示頁的影片框仍是空的。

---

## 2026-09-23　docs(簡報)：新版專題簡報 DAHV_tdfklM 從 12 頁骨架補成 19 頁完稿

- **類型**：docs
- **做了什麼**
  - 使用者新開一份骨架簡報（Canva `DAHV_tdfklM`，原 12 頁多為佔位文字），
    依其指示套用舊簡報 `DAHVDXdRNpE` 的「A232 直角藍」樣式並補完內容，現為 19 頁。
  - 新增 7 頁：研究方法六步驟各一頁（①地圖前處理 ②PCA ③切帶 ④cell 分解
    ⑤cell 內牛耕 ⑥cell 間銜接）＋「實驗設定與場地」。
  - 內容來源：`docs/03_海報/答辯資料/`（硬體規格、套件清單、已知限制）與
    `docs/01_學習資料/20_驗證與實驗方法.md`（光達實測 4.99 Hz、最遠有效 3.02 m）。
  - 圖片沿用該簡報第 18 頁「可用圖片」的既有素材（Canva mediaId），未上傳新檔。
  - 修正骨架上第 3、4 頁標題與內容對調的問題（第 3 頁內容是研究動機，標題卻寫背景與系統摘要）。
- **為什麼**：原骨架只有佔位文字，且使用者要求 20 分鐘的簡報份量、方法章節以圖片為主視覺。
- **影響檔案**：無（只動 Canva 設計，不含專案程式）。
- **結果 / 驗證**：已 commit 至 Canva；頁序經 page_metadata 確認為
  封面 / 目錄 / 動機摘要 / 系統架構 / 現成套件(備問) / 硬體規格 / 研究方法總覽 /
  ①～⑥ / 實驗設定 / 成果展示 / 結論 / 結尾 / 可用圖片 ×2。
- **待辦 / 已知問題**
  - 成果展示頁的影片框仍是空的，待使用者放入實機影片。
  - ⑥ cell 間銜接沿用 ④ 的 A～D 圖，若有「走訪順序」專屬截圖可換掉。
  - 字型為 Canva 預設，MCP 無法改字型；若要與舊簡報一致需手動調整。

---

## 2026-09-13　fix(coverage,launch,web)：車子卡死不再原地跳光路點 — 線尾內縮、脫困重試、受困停止可接續；軌跡改用地圖座標

- **類型**：fix
- **症狀（使用者實機回報）**
  1. 行走軌跡與「覆蓋路徑」圖層對不上。
  2. 車子停滯後無法自救，停在原地一直跳過路點（同日稍早「停滯 3 秒就跳下一點」的方案不合用）。
- **根因**
  - **卡死**：掃描線端點落在可走區邊界，離牆只有 0.10~0.125 m；Burger 外接圓半徑 0.11~0.15 m，
    在線尾要轉向下一條線時車尾會掃到牆 → DWA 找不到可行軌跡。move_base 內建自救（清 costmap、
    原地旋轉）同樣轉不了身；而舊方案取消後直接送下一點，車還在原位，於是每一點都一樣失敗。
  - **軌跡對不上**（兩個原因）：
    ① 軌跡取自 `/odom`，odom 座標會累積漂移，卻被當成地圖座標畫（答辯資料已知限制第 11 項）；
       規劃起點 `robot_pos` 也是 odom 座標。
    ② 官方全域 costmap 膨脹 1.0 m，小場地幾乎整片都有成本，navfn 為了避開高成本把貼牆的掃描線
       繞到場地中間走（每條線只有兩個端點路點，中間怎麼走由 navfn 決定）。
- **動了什麼**
  - **`scripts/coverage_planner.py`**：新增 `END_TRIM = 0.09`，`_slice_runs` 把每條掃描線兩端各內縮
    0.09 m（區間太短縮成中點），端點離障礙 ≈ 0.19 m，與側向（第一條線離邊界 `SPACING/2`）一致。
    `a0/a1` 維持真實範圍供 `_link_runs` 判斷連通，**cell 分解結果不變**。`plan()` 新增 `end_trim` 參數。
  - **`scripts/map_server.py`**
    - 位置與軌跡改由 `pose_tick`（10 Hz）用 TF 查 `map → base_footprint`，移除 `/odom` 訂閱。
    - 執行邏輯拆成 `_go_to`（送單一目標＋停滯偵測）與 `run_coverage(start_idx)`：
      失敗（停滯或 move_base 放棄）→ 已在路點 0.15 m 內就算到；否則 `_escape` 脫困後**重送同一點**，
      `RETRY_MAX = 2` 次仍失敗才跳過。
    - `_escape`：直接發 `/cmd_vel` 以 0.05 m/s 直線退開 0.12 m（先試後退、再試前進），
      該方向要同時通過 **SLAM 地圖**（車身掃過的長條區全為自由格，補雷射 0.12 m 內量不到的盲區）
      與 **雷射**（±35° 扇形最近障礙 > 0.25 m）檢查才動；行進中有東西靠近就停；最後呼叫
      `/move_base/clear_costmaps`。
    - **受困停止**：連續 `STUCK_MAX = 3` 個路點失敗且車子移動 < 0.30 m → 狀態改 `error`、
      進度退回第一個失敗的路點、撤掉這串跳過紀錄，提示使用者手動移車。車子若有在移動
      （只是那幾點真的到不了）則照常跳過繼續。
    - 新增 `POST /coverage/resume`：沿用同一條路徑從 `done` 接著走、不重新規劃；
      僅 `stopped`／`error` 且尚有未走路點時接受。重啟 SLAM 時一併清空 `cov_skips`。
  - **`launch/start.launch`**：`global_costmap/inflation_radius = 0.25`（寫在舊參數位置，
    costmap 以 pre-Hydro 方式載入時會搬進 `inflation_layer`）。局部 costmap 維持官方值。
  - **`web/index.html`**：新增「⏵ 從中斷處繼續」按鈕（`stopped`／`error` 且有未走路點時可按）。
- **關鍵決策**
  - **內縮線尾，不加大 `MARGIN`**：側向只需車身半寬，只有要轉身的線尾需要外接圓的空間；
    加大 `MARGIN` 會連窄通道一起封掉。
  - **脫困走直線、不原地轉**：卡死的原因正是轉不了身；差速車只能沿車頭方向進退。
  - **受困就停，不跳光**：跳過只對「點到不了但車能動」有意義；以「連續失敗＋幾乎沒移動」區分兩者。
- **結果 / 驗證**
  - `py_compile`、`node --check`、launch XML 解析皆通過。
  - `test/coverage_bench.py` 前後對照（覆蓋率｜轉場穿牆）：

    | 場地 | 覆蓋率 前 → 後 | 轉場穿牆 前 → 後 |
    |---|---|---|
    | 長方形4x2 | 100.0 → 98.7% | 0 → 0 |
    | 含柱4x2 | 100.0 → 98.4% | 0 → 0 |
    | 雙柱4x2 | 98.4 → 95.7% | 2 → 2 |
    | L形4x4 | 100.0 → 97.7% | 1 → 1 |
    | 斜置15度 | 100.0 → 99.1% | 8 → 0 |
    | 斜置30度 | 100.0 → 95.6% | 30 → 19 |
    | 斜置45度 | 95.9 → 94.9% | 3 → 0 |

    14 個場地覆蓋率平均降約 1.9 個百分點（線尾各少掃約 9 cm）；掃描線穿牆全為 0；
    端點離牆較遠，斜置場地的直線轉場穿牆明顯減少。
  - 以假 ROS（假車依 `/cmd_vel` 積分、假 move_base 依劇本回應、假地圖與假雷射）跑 10 個情境全數通過：
    正常走完；停滯一次→後退 0.12 m→重試成功不跳過；單點到不了→脫困 2 次後跳過並繼續；
    四周貼滿障礙→不移動、連續 3 點失敗後停止並退回路點 3；按繼續從路點 3 走完；
    無未走路點時拒絕繼續；連續 4 點到不了但車有移動→照常跳過不誤判受困；
    路點旁 8 cm 停滯→視同到達；後方地圖是牆→改為前進脫困。
  - **尚未上實機**。
- **已知待辦 / 風險**
  - 脫困會繞過 costmap 直接驅動馬達（0.05 m/s、最多 0.12 m），安全靠地圖＋雷射雙重檢查；
    假設 `base_scan` 與車身同向（TB3 URDF 如此）。
  - 請在機器人上確認 `rosparam get /move_base/global_costmap/inflation_layer/inflation_radius`
    為 0.25；若官方參數檔有 `plugins` 設定，要改寫在 `inflation_layer` 底下才會生效。
  - 請確認 footprint：`rosparam get /move_base/local_costmap/footprint`（官方 burger 可能是
    後方較長的矩形，外接圓約 0.15 m；若實機仍在線尾卡住，把 `END_TRIM` 加到 0.12）。
  - `docs/01_學習資料` 第 13、15 章與答辯資料的「已知限制 11（odom 漂移）」描述已過時，尚未更新。

---

## 2026-09-13　feat(web)：新增「規劃路點」圖層與跳過標記；地圖 canvas 改為顯示解析度繪製

- **類型**：feat
- **動機**：實機上車子會自己開進動不了的地方，接著連續跳過一串路點，但網頁只顯示
  「路點 i/n 跳過」最後一筆文字，看不出是哪些路點、在地圖的哪裡、為什麼被跳過。
- **動了什麼**
  - **後端 `scripts/map_server.py`**：新增共享狀態 `cov_skips = [[路點序號, 原因], ...]`；
    `run_coverage` 跳過時記一筆（原因＝「停滯」或「無法到達」），`coverage_start` 清空，
    `/coverage/status` 多回傳 `skipped` 欄位（序號對應 `path_px` 的索引）。
  - **前端 `web/index.html`**：
    - 新圖層「規劃路點」：○ 待走、● 已到達、✕ 跳過（紅＝無法到達、橘＝停滯）、
      ◎ 目前目標；跳過與目前目標旁標路點序號（從 1 起算，與「路點 i/n 跳過」訊息一致）。
      疊在行走軌跡之上，✕ 先描深色底，壓在紅色安全邊距上也看得清楚。
    - 圖層區下方加圖例；「規劃資訊」表新增「跳過路點 k / n」。
    - **canvas 改以實際顯示解析度繪製**（見踩到的坑）。
- **踩到的坑：疊加圖層全部是馬賽克**
  - 原本 canvas 的像素尺寸＝地圖格數（例如 78 × 54），再用 CSS 放大十幾倍，
    所以線條、圓點、文字都跟著地圖格子一起被放大成方塊；新圖層的序號完全讀不出來。
    這個問題既有圖層（cell 標籤、覆蓋路徑）本來就有，只是之前沒有需要細看的東西。
  - 修法：`fitCanvas` 把 canvas 的像素尺寸設成 CSS 尺寸 × `devicePixelRatio`，
    `draw` 每次 `setTransform(zoom)`，**所有繪圖座標仍是地圖像素，既有繪圖程式碼不用改**；
    `imageSmoothingEnabled = false` 讓地圖格子維持銳利方塊，外觀與原本相同。
  - `shadowBlur` 不吃 transform，機器人光暈改乘上 `zoom` 以維持原本大小。
  - 新圖層的字級與線寬用螢幕像素（`cssPx()`）指定，任何縮放下都一樣粗細；
    圓點半徑上限 1.5 格（7.5 cm），不會和相鄰掃描線（3.6 格）的點黏在一起。
- **影響檔案**：`scripts/map_server.py`、`web/index.html`。
- **結果 / 驗證**
  - `py_compile` 通過；抽出頁面 script 以 `node --check` 通過。
  - 以假 ROS 模組跑 `map_server` 真正的 Flask 路由（合成 3.0 × 1.8 m 房間＋中央障礙、
    真實 `plan()` 輸出、手動塞入 5 筆跳過），Chrome 實際開啟：主控台無錯誤；
    跳過 ✕ 與序號、目前目標 ◎、已到達／待走圓點皆清晰可辨；
    「跳過路點」顯示 `5 / 24`；canvas 為 1761 × 1220（CSS 1174 × 813 × dpr 1.5）。
  - 尚未在實機地圖上看過。

---

## 2026-09-13　fix(coverage,launch)：貼牆路點不再一碰就卡住 — 停滯偵測＋move_base 容錯覆寫

- **類型**：fix
- **症狀**：覆蓋執行時，機器人走到貼近安全邊距的路點（多半是掃描線兩端）就停住，
  等幾十秒才跳下一點。
- **為什麼會停**：網頁上的紅色「安全邊距」圖層只決定路點放哪裡，執行期間沒有人檢查它；
  真正讓車停的是 move_base。`MARGIN = 0.10 m` ≈ Burger 半寬 0.105 m，再加上 SLAM 定位
  幾公分的誤差，車身一靠近路點就壓到 costmap 障礙區 → DWA 找不到可行軌跡而送出速度 0 →
  move_base 乾等 `controller_patience`（官方約 15 s）→ 清 costmap、原地旋轉 → `ABORTED` →
  `run_coverage` 才跳過。
- **動了什麼**
  - **A. `launch/start.launch`**：在官方 yaml 載入之後覆寫四個 move_base 參數：
    `NavfnROS/default_tolerance = 0.1`（路點落在障礙區時改規劃到附近可達點）、
    `DWAPlannerROS/xy_goal_tolerance = 0.10`（官方 0.05）、
    `controller_patience = 5.0`、`planner_patience = 2.0`（早點放棄）。
  - **B. `scripts/map_server.py` 的 `run_coverage`**：
    - 新增 `_robot_pose(frame)`，用 TF 查 `base_footprint` 在地圖座標的 (x, y, yaw)。
    - **停滯偵測**：等待迴圈每 0.5 s 查一次位姿，位移沒超過 `STALL_DIST = 0.03 m`、
      轉角也沒超過 `STALL_YAW = 0.20 rad`，連續 `STALL_SEC = 3.0 s` 就自行取消目標，
      不等 move_base 的 patience 和自救動作。
    - **貼在旁邊就算到**：沒拿到 `SUCCEEDED` 但離路點 < `GOAL_NEAR = 0.15 m` 時，
      視同到達、不記跳過；否則照舊跳過，訊息區分「停滯」與「無法到達」。
- **關鍵決策**
  - **不縮 `footprint` / `robot_radius`、不調 `inflation_radius`**：前者等於允許真的撞牆，
    後者只影響「偏好離牆多遠」，不會移動「壓到就停」的那條界線。
  - 停滯判定把**原地旋轉也算作進展**，否則 DWA 對準方向的原地轉身會被誤判為卡住。
  - TF 查不到時完全不做停滯判定，行為退回改版前（等 move_base 回報）。
  - `GOAL_NEAR` 取 0.15 m 而非更大：掃描線端點提早收尾會少掃靠牆那一段，
    0.15 m 小於覆蓋寬度 0.20 m。
- **影響檔案**：`launch/start.launch`、`scripts/map_server.py`。
- **結果 / 驗證**
  - `py_compile` 通過；launch XML 解析通過，四個覆寫參數都在。
  - 以假 ROS 模組（rospy／actionlib／tf2 全換成替身、模擬時鐘）跑 `run_coverage` 五種情境，
    全數符合預期：正常到達 6.0 s 不誤判；遠處卡住 4.0 s 跳過並標「停滯」；
    路點旁 8 cm 卡住 4.0 s 視同到達；原地慢轉 5 s 後到達不誤判；TF 不可用時行為同改版前。
  - **尚未上實機驗證**；參數官方值是憑印象，請在機器人上用
    `rosparam get /move_base/controller_patience` 等確認，並確認
    `/move_base/base_global_planner` 是 navfn（否則 `NavfnROS/default_tolerance` 無效）。
- **已知待辦 / 風險**
  - 停滯 3 s 就取消，比 `controller_patience` 早，所以 **move_base 的自救動作不會再被觸發**。
    若 local costmap 殘留假障礙把車困住，後續幾個路點可能被連續快速跳過；
    實機若遇到，可在停滯時先呼叫 `/move_base/clear_costmaps` 再決定是否跳過。
  - 根本解仍是讓路點離牆有餘裕（`MARGIN` 0.15），代價是靠牆覆蓋率與窄通道。

---

## 2026-09-11　docs(海報)：v5 版面重排 — 摘要＋五步圖解研究方法，新增示意圖產生器

- **類型**：docs
- **動了什麼**：新增 `docs/03_海報/gen_poster_v5.py`（產出 `改_v5.docx`）與
  `gen_method_figs.py`（產出 `fig/method_1~5_*.png`）。
  - **版面**：標題 → 左欄「一、摘要／二、系統架構（沿用架構圖＋橫式照片預留框）」、
    右欄「三、研究方法」五步（① PCA 主軸對齊 → ② 切帶 → ③ cell 分解 → ④ cell 內牛耕 →
    ⑤ cell 間銜接，每步左圖右文、步驟間向下箭頭）→ 通欄「四、成果展示」（實驗條件註記＋
    預留框）→「五、結果討論」（結論｜限制與未來工作）。
  - **字數**：內文（不含標題）從 v4 的 1,989 字降到 756 字；摘要 144 字（上限 150）。
  - **標題**改為「TurtleBot3 牛耕式路徑規劃系統」，副標沿用。
  - 架構圖縮 0.794 放進左欄（字 7.5 pt），單行標籤依字數自動加寬，修掉 v4 被截斷的
    「目前狀態」「網頁架設」等；錯字「機器人的位子」→「位置」。
- **為什麼**：使用者回饋 v4「字太多、缺有效圖片」，並親自定下六區塊版面與五步流程；
  實機照片由使用者自行拍攝後放入預留框。
- **關鍵決策**
  - **示意圖由規劃器實際算出**，不是手繪：合成地圖餵給 `coverage_planner` 的
    `principal_axes`／`_slice_runs`／`_link_runs`／`_build_cells`／`plan`，
    並 assert 中間結果與 `plan()` 的 cell 數一致。
  - **合成場地選 2.4 × 1.5 m、斜 25°、含一個 0.45 m 障礙物**：掃過 3 種尺寸 × 4 種角度，
    3.0 × 1.8 m 與 2.7 × 1.6 m 會觸發「最外側掃描帶沿鋸齒邊界碎裂」切出 6～23 個 cell，
    2.4 × 1.5 m 在 15°～30° 都穩定切出 4 個（覆蓋率 99.2%～99.7%、掃描線穿牆 0）。
  - 成果展示的前提寫「長方形（長寬比 ≥ 1.5）」而非「四邊形」：正方形會讓 PCA 退化。
- **踩到的坑**
  - v4 的圖形分屬兩個錨定段落（原點差 1.34 cm）。v5 把所有圖形集中到同一段，
    輸出檔只剩一個座標系，之後不必再換算。
  - scratchpad 裡取名 `inspect.py` 的腳本會遮蔽標準庫，讓 numpy import 失敗。
- **影響檔案**：`docs/03_海報/gen_poster_v5.py`、`gen_method_figs.py`（新增）、
  `改_v5.docx`、`fig/*.png`（產物）。`改_v4.docx` 未修改。
- **結果 / 驗證**：Word 開啟並轉 PDF 無修復提示、單頁；逐區塊目視確認無溢框、無重疊。
- **已知待辦**：架構圖 7.5 pt 偏小（版面之後再談）；鋸齒邊界碎裂缺陷仍未修，
  實機斜置場地若切出大量碎 cell，成果圖會受影響。

---

## 2026-09-09　docs(學習資料)：`index.html` 改版 — 六步流程主視覺、程式碼摺疊、取消章號

- **類型**：docs
- **動了什麼**：把前一版「六部章節式」的 `index.html` 重構成**以演算法流程為主軸**的互動頁面。
  - **首屏主視覺**：`① 地圖前處理 → ② PCA 主軸對齊 → ③ 切帶與中心線取樣 →
    ④ cell 分解 → ⑤ cell 內路徑規劃 → ⑥ cell 間銜接規劃` 六個節點，
    點任一節點展開該步的**輸入 / 方法 / 輸出 / 為何這樣做**卡片，並可跳到完整說明。
  - **章節拆進階段**：不再以「章」為單位。例如階段 ① = 第 07 章全章 + 8.1 形態學膨脹，
    階段 ② = 8.2~8.5，階段 ⑤ = 12.1~12.3，階段 ⑥ = 12.4~12.9。
    每個階段標題下標示「內容來源：第 NN 章 …」保留回溯性。
  - **取消章號**：主線只用階段編號 ①~⑥，附錄 16 章只有標題不編號
    （原本 09→10→11→12→08→07→02 的跳號很難讀）。小節編號（7.1、8.1）保留，
    因為內文有大量「第 03 章 3.5」這種交叉引用。
  - **程式碼全部摺疊**：331 個程式碼區塊改成預設收合的 `<details>`，
    摘要行直接用區塊第一行的來源註解（例如 `scripts/coverage_planner.py:222-224`），
    不用點開就知道那段在哪。196 個 ASCII 示意圖維持直接顯示（那是講解主力，不是程式碼）。
  - 第 09 章獨立成「演算法演進史」，第 22、23 章合成「實測與能力邊界」，兩者仍屬主線。
- **為什麼**：使用者回饋——版面與開頭數字要重整、程式碼不要、
  而且希望「一進來就看懂牛耕演算法的流程」，再點擊逐步深入。
- **關鍵決策：六步而不是五步**
  - 使用者原本列的是 `PCA → 切帶取樣 → cell 分解 → cell 內 → cell 間` 五步。
  - 但 `apply_safety_margin()`（`binary_dilation` 膨脹）是在 `map_server.py` 裡
    **`plan()` 之外、之前**被呼叫的（`map_server.py:163`、`468`），
    而 `plan()` 的第一件事就是拿 `free` 去做 PCA。
  - 少了這一步，「PCA 吃的點集哪裡來」會斷掉，所以補上 ① 地圖前處理。
- **踩到的坑：章節重組讓內文的交叉引用全部指向不存在的錨點**
  - 內文有大量「第 10 章」「第 22 章」字樣，前一版都轉成 `#ch10` 這種錨點。
    章節被拆進階段之後，`#ch10` 不再存在。
  - 修法是加一張 `chapter_anchors()` 對照表（10→`#s3`、09→`#hist`、22/23→`#limits`…），
    讓 `mdblocks` 轉連結時查表。第 08 章橫跨 ①②，指向 ②（PCA 是它的主體）。
  - 另外每段內容改成用**自己的章號**產生錨點，避免不同章的同名 h3 在同一階段裡碰撞。
- **影響檔案**：
  - `docs/01_學習資料/index.html` — 重寫（1,013 KB）
  - 24 個 `.md` 原始檔 — **未修改**
- **結果 / 驗證**：
  - **切片完整性**：逐章掃出所有 h2 小節，確認每一節都出現在產物裡；
    24 章共 200+ 個小節只有 1 個不在——第 23 章的「全書章節索引」，
    因為它索引的是原始九部編排，重排後已失效，**刻意移除**。
  - **結構**：標籤配對平衡；頁內錨點 100% 可解析（含全部改寫過的交叉引用）；
    外部資源 0 個（維持完全離線）。
  - **實機**：瀏覽器實測六節點點擊展開／互斥收合、深淺色、側欄搜尋與捲動追蹤、
    程式碼摺疊標籤、ASCII 圖對齊，皆正常。
  - ⚠ 修掉一個渲染缺陷：`第 ① 步` 的圈號在等寬字型堆疊裡沒有字形，
    會顯示成方框；改用無襯線字型。程式碼摺疊圖示同理改成純 ASCII 的 `</>`。
- **已知待辦**：產生這份 HTML 的三支腳本（`mdconv.py` 語法高亮、`mdblocks.py` Markdown
  轉換、`build.py` + `structure.py` 組版與結構定義）仍不在版控裡，`.md` 更新後無法重新產生。

---

## 2026-09-09　docs(學習資料)：24 章講義合併為單檔離線 `index.html`，改以牛耕為主線重排

- **類型**：docs
- **動了什麼**：新增 `docs/01_學習資料/index.html`（979 KB，單一檔案、零外部依賴），
  把該目錄下 24 章 Markdown（582 KB、約 14,200 行）合併成一份可離線閱讀的講義。
  - **章節重排成六部**：原始 Markdown 是九部編排，本頁改以**牛耕演算法為主線**——
    第一部（09→10→11→12）講演算法本身，第五部（18、20~23、19）講驗證、調校與能力邊界；
    其餘章節依「牛耕會用到什麼」歸成三個支線部（數學與地圖資料／ROS 與導航／系統與網頁工程）。
  - **內容一字未刪**。第 08 章兩段純數學術語的旁支（譜定理、`eigh` 與 `eig` 的差別）
    改成預設收合的 `<details>`，讓主線動線乾淨，點開仍可閱讀。
  - **頁面功能**：側欄兩層目錄（章 + 節）、章節搜尋（`/` 聚焦）、捲動位置追蹤、
    深／淺色切換（記在 `localStorage`）、閱讀進度條、列印時自動展開所有摺疊區塊。
  - 章末的「上一章／下一章」與內文所有「第 NN 章」字樣都自動轉成頁內錨點連結。
- **為什麼**：24 個 `.md` 分散，交叉參照要一直開檔案；要一份能直接雙擊閱讀、
  也能離線帶著看的整合版本。
- **關鍵決策：不套 CDN，自己寫 Markdown 轉換器與語法高亮**
  - 機器人端可能沒有網路，載不到 CDN 就整份掛掉（同第 15 章前端「零外部依賴」的理由）。
  - 更關鍵的是**無語言標記的 code fence 有 723 個，絕大多數是 ASCII 示意圖不是程式碼**。
    通用高亮器會把 `████`、`●───→` 這些字元亂上色。改成只有標了語言的 331 個區塊才高亮，
    197 個示意圖以等寬虛線框原樣保留。
- **踩到的三個坑**
  - **`fold_sections` 把程式碼註解當成標題**：掃描「下一個同級標題」時，
    fence 內的 Python 註解 `# scripts/coverage_planner.py:38-40` 被 `^#{1,6}\s` 匹配成 h1，
    導致 `</details>` 被插進程式碼區塊中間。修法是掃描時追蹤 fence 開合狀態。
  - **表格裡的 `<br>` 被跳脫成字面文字**：`inline()` 會整段 `html.escape`，
    `<br>` 變成畫面上看得到的 `&lt;br&gt;`。修法是跳脫後把 `&lt;br&gt;` 還原成真正的換行。
  - ⚠ **忘了宣告 `<meta charset="utf-8">`**：這不是 Artifact 而是獨立檔案，
    外層 `<!doctype>`／`<head>` 要自己寫。少了 charset 整頁中文變亂碼——
    這個缺陷靜態檢查完全看不出來，是實際開瀏覽器才發現的。
- **影響檔案**：
  - `docs/01_學習資料/index.html` — 新增（產物）
  - 24 個 `.md` 原始檔 — **未修改**
- **結果 / 驗證**：
  - **內容完整性**：逐章比對「實質字元數」（只取中日文與英數），24 章總計
    源碼 179,593 字元 vs 產物 179,250，差 −0.19%；再做逐行比對，
    全書只有 13 行未命中，全部確認為比對方式的假影（摺疊標題被摘要取代、
    有序清單編號由 CSS 產生、表格 `<br>`），**沒有內容遺失**。
  - **結構**：所有標籤配對平衡；頁內錨點 100% 可解析（0 個死連結）；
    殘留的 `.md` 連結 0 個；外部 `http(s)` 資源 0 個（確認完全離線）。
  - **實機**：以 `python -m http.server` 開瀏覽器實測深／淺色、側欄搜尋與捲動追蹤、
    表格換行、ASCII 示意圖對齊、摺疊區塊，皆正常。
- **已知待辦**：產生這份 HTML 的腳本（Markdown 轉換器 + 語法高亮 + 組版）目前不在版控裡，
  `.md` 更新後無法重新產生。若要維護這份講義，需要把腳本一併收進專案。

---

## 2026-09-09　docs(海報)：`改_v4.docx` — 字級統一、架構圖縮 4/5 置中、版面改用絕對座標重排

- **類型**：docs
- **動了什麼**：新增 `docs/03_海報/gen_poster_v4.py`，同樣以 `改_v2.docx` 為底本產出
  `改_v4.docx`（v2、v3 的腳本與檔案都保留）。內容承接 v3 的四步鏈，這次處理的是版面：
  - **字級統一**：全篇內文一律 11 pt（v3 的「一、」還是 12 pt）；架構圖內原本混了
    寫死的 10 pt 與吃 Normal 樣式的 10.5 pt，一併統一。
  - **系統架構圖縮 4/5 並水平置中**：41 個圖形整組等比縮放，框、字級、內距同步縮
    （字級 → 8.5 pt）。原圖靠左（x 0.00～20.68），縮完置中為 x 5.31～21.85。
  - **騰出的空間給三～六**：四格內文統一 10.10 cm 高、上下兩排等高，三、四由 v3 的
    8.60 cm 再加高。內文補回 v3 為了塞版面砍掉的細節（costmap 分工、連通判準只做
    區間比較、未知格不進規劃等）。
  - **減少框內留白**：文字方塊內距由 7.2／3.6 pt 縮到 2.83／1.42 pt（VML 那份也補上
    `inset`）。
  - **標題與內文之間的空隙**壓到 0.05～0.15 cm（原本 0.48 cm）。
- **關鍵發現：檔案裡有兩個錨定段落，座標系差 1.34 cm**
  - 浮動圖形的 `wp:positionV relativeFrom="paragraph"` 是相對各自錨定段落算的。
    本檔頂層有兩個 `w:p`：段 0 有 61 個圖形（標題列、各節標題、架構圖、三～六內文），
    段 1 只有 2 個（「一、」的內文方塊，和架構圖裡的一條接點）。
  - 兩者原點差 1.34 cm。反推證據：v2 中「一」內文在段 1 的 y=4.16、高 4.62，
    加 1.34 後底部正好 10.12 ＝ 段 0 中「二、系統架構」標題的位置；段 1 那條接點
    y=12.35 加 1.34 後落在架構圖中段，與相鄰方塊對得上。
  - v3 只做等量平移，平移量與原點無關，所以沒出錯；v4 要做絕對定位與縮放，
    就必須先換算到同一個座標系，否則「一」的內文會壓到「二」的標題上。
- **為什麼**：v3 給使用者看過後的回饋——字級不一致、架構圖偏左、框內留白太多、
  標題與內文之間有空隙、三～六的篇幅不夠。
- **影響檔案**：
  - `docs/03_海報/gen_poster_v4.py` — 新增
  - `docs/03_海報/改_v4.docx` — 新增（`.gitignore` 忽略 `docs/**/*.docx`，不進版控）
  - v2、v3 的腳本與檔案皆未修改
- **結果 / 驗證**：
  - 所有 `.xml` / `.rels` 皆可被 `ElementTree` 解析。
  - 63 個圖形逐一核對 DrawingML 與 VML 兩份座標是否同步；除了頁首背景圖與幾個原本就
    用 `wp:align` 對齊、VML `margin-left` 本來就對不上的圖形（v2 即如此）之外全部一致。
  - 版面座標核對：一 內文 5.15→7.50、二 標題 7.85→8.86、架構圖 9.16→17.25、
    三四 標題 17.70、內文 18.79→28.89、五六 標題 29.34、內文 30.56→40.66；
    最低點 40.66 cm 未超出下邊界 40.73 cm，最右點 27.16 cm 未超出文字寬。
  - 架構圖置中檢查：左右邊距皆為 5.31 cm。
  - 內文高度粗估：一 1.79/2.35、三四五 各 9.52/10.10，皆有餘裕。
- **待辦 / 已知問題**：
  - 架構圖字級縮到 8.5 pt（4/5 × 10.5 pt），A3 尺寸下偏小，需目視確認可讀性。
  - 內文高度仍是粗估（把西文詞當可自由斷行），需在 Word 裡確認未爆框。
    本機沒有 LibreOffice，無法自動算圖驗證。
  - 第六節內容仍待討論；`test/coverage_bench.py` 的 `--baseline` 參數尚未補。

---

## 2026-09-09　docs(海報)：`改_v3.docx` — 內容重心移到牛耕演算法，並補上版面重排

- **類型**：docs
- **動了什麼**：新增 `docs/03_海報/gen_poster_v3.py`，以 `改_v2.docx` 為底本產出
  `改_v3.docx`（v2 的腳本與檔案都保留不動，可對照）。
  - **三～五重寫成一條四步鏈**：PCA 主軸對齊 → 取得長軸／短軸 → 沿短軸切帶取樣切
    cell → 每個 cell 各自蛇行。小節標題同步改為
    「三、核心方法 : 可走區與主軸對齊」「四、核心方法 : 切帶與 cell 分解」
    「五、核心方法 : 牛耕與 cell 排序」。
  - **敘述改白話**：拿掉「實對稱半正定」「譜定理」「特徵值為非負實數」等術語，
    改用「點散得最開／最窄的方向」「兩者一定互相垂直」描述長短軸的來源。
  - **一、研究動機與目的**縮短約三成（框高 4.62 → 3.10 cm），把版面讓給演算法。
  - **版面重排**：「二、系統架構」整組 49 個圖形（含標題、方塊與連接線）與三、四
    兩格整體上移 1.50 cm，三、四框高 7.10／7.31 → 8.60 cm，四格大小拉齊。
  - **六、驗證結果與討論**內文暫清成一行佔位字，驗證項目待討論後再補。
  - 順手清掉「五、」標題框裡殘留的更早版本文字（`ROS基本概念`、
    `核心方法(2)  安全邊距膨脹`）—— 標題框只有 0.92 cm 高，這些字會溢出到框外。
- **為什麼**：v2 的內容已經追不上程式。v2 第五節寫「掃描帶只取投影極值、等於假設該帶
  連通」，第六節把「做真正的牛耕式區域分解」列為未來工作；但 `35d16ea` 之後
  `scripts/coverage_planner.py` 早已實作完 `_slice_runs`（中心線取樣切 run）、
  `_link_runs`（投影範圍重疊判連通）、`_build_cells`（一對一才延伸，分裂／合併即臨界點）
  與貪婪最近鄰的 cell 排序。海報再照 v2 講會與程式和口試說詞對不上。
- **影響檔案**：
  - `docs/03_海報/gen_poster_v3.py` — 新增（產檔腳本）
  - `docs/03_海報/改_v3.docx` — 新增（產出）
  - `docs/03_海報/gen_poster_v2.py`、`改_v2.docx` — 未修改
- **結果 / 驗證**：
  - 產檔後所有 `.xml` / `.rels` 皆可被 `ElementTree` 解析。
  - 63 個圖形的 DrawingML（`wp:positionV` / `wp:extent`）與 VML
    （`margin-top` / `height`）兩份座標一致（唯一不同步者是頁首背景圖，v2 即如此）。
  - 版面最低點 40.65 cm，未超出下邊界 40.73 cm（頁高 42 cm）。
  - 內文高度粗估：一 3.07/3.10、三 8.40/8.60、四 8.40/8.60、五 7.55/8.50，皆未爆框。
- **待辦 / 已知問題**：
  - **粗估不等於實際**：估算把西文詞當可自由斷行處理，但 Word 不會把 `run`、`cell`、
    `costmap`、`move_base` 斷在詞中間，實際高度可能略高於估算；三、四只剩 0.20 cm
    餘裕，需在 Word 裡目視確認有無爆框。本機沒有 LibreOffice，無法自動算圖驗證。
  - 第六節內容待討論：要驗證哪些項目、放不放 PCA 與地圖軸對齊的量化對照。
  - `test/coverage_bench.py` 目前沒有 baseline 模式（把主軸換成地圖座標軸），
    第六節若要做對照表需要先補一個 `--baseline` 參數。

---

## 2026-09-06　fix：`scripts/map_server.py` 補上執行權限（8080 連不上 + move_base 等不到 TF 的共同根因）

- **類型**：fix
- **動了什麼**：`git update-index --chmod=+x scripts/map_server.py`，
  索引模式由 `100644` 改為 `100755`。無程式碼變更。
- **症狀**：機器人端 `roslaunch turtlebot3_ccpp start.launch` 出現
  `[WARN] Timed out waiting for transform from base_footprint to map ...`
  `canTransform: target_frame map does not exist. canTransform: source_frame base_footprint does not exist.`
  且網頁 `172.20.10.5:8080` 無法連線。
- **為什麼**：開發機是 Windows、`core.filemode=false`，本地檔案模式不會被 git 追蹤，
  所以 `map_server.py` 是以 `100644` 進索引的（對照組：`test/map_server_raw.py` 是在
  Linux 上 add 的，索引裡是 `100755`）。機器人端 clone 出來就沒有 `+x`，
  roslaunch 的節點解析（`roslib.packages.find_node` 會以 `os.access(path, os.X_OK)` 過濾）
  找不到它，印出
  `ERROR: cannot launch node of type [turtlebot3_ccpp/map_server.py] ... permission is set to executable (chmod +x)`
  後**繼續啟動其他節點**，所以整包看起來有在跑。
- **一個原因、兩個症狀**：
  1. `map_server` 沒起來 → Flask 沒跑 → 8080 連線被拒。
  2. `map_server` 沒起來 → `map_server.py:614` 的 `slam_launch()` 沒執行 →
     gmapping 與 `turtlebot3_remote.launch`（robot_state_publisher）都沒上線 →
     `map` 與 `base_footprint` 兩個 frame 皆不存在 → move_base 的 `Costmap2DROS`
     建構子卡在等待迴圈，每 5 秒印一次那個 WARN，**永遠不會恢復**。
     （這個 WARN 本身是可自癒的：SLAM 一上線就會過。但這次 SLAM 根本不會上線。）
- **注意這是 SLAM 搬出 launch 後才浮現的耦合**：`35d16ea` 把 SLAM 生命週期交給
  `map_server.py` 管理之後，`map_server` 就成了 SLAM 的唯一啟動者 ——
  它掛掉不再只是「網頁沒了」，而是連導航定位一起沒了。
- **怎麼驗的**：`git ls-files -s scripts/` 確認模式已變 `100755`。
  機器人端 `chmod +x` 後重跑可立即驗證（不必等本次 commit）。
- **沒有動的**：`scripts/coverage_planner.py` 維持 `100644` —— 它是被
  `map_server.py` 以 `sys.path.insert` + `import` 載入的模組，不是 roslaunch 節點，
  不需要執行權限。

---

## 2026-08-30　docs：`01_學習資料/` 全部重寫為九部 24 章講義；新增 `test/coverage_bench.py`

- **類型**：docs / test
- **動了什麼**：
  - 刪除 `docs/01_學習資料/` 原有的 8 個 .md（`coverage_algorithm.md`、`ros_topics_nodes.md`、
    `web_architecture.md`、`專案設計架構.md`、`教學報告.md`、`演算法原理.md`、
    `覆蓋規劃程式碼說明.md`、`路徑規劃架構與假完成診斷.md`）。
  - 新增 **24 章、14,232 行**的完整講義（九部）：背景知識 3 章、設計歷程 2 章、
    骨架 2 章、演算法核心 5 章、執行層 1 章、網頁 3 章、系統議題 2 章、
    收尾 2 章、實測 3 章 + 導讀 1 章。
  - 新增 `test/coverage_bench.py`：離線覆蓋效果評估工具（零 ROS 依賴，14 種合成場地）。
  - 改寫 `docs/README.md` 的 01_學習資料 索引段（原本指向已刪除的檔案）。
- **為什麼**：舊的 8 份內容互相重疊且已過時 —— `演算法原理.md` 與
  `路徑規劃架構與假完成診斷.md` 講的還是舊版單一全域 PCA 直線掃描，沒有 cell 分解；
  `專案設計架構.md` 還把 `boustrophedon.py` 當成主要規劃節點，但它早已移到 `test/`。
- **新架構**：每章七段式編排（問題 → 直覺做法 → 撞牆 → 現在做法 → 被否決的方案 →
  重點回顧 → 自我檢核題），全書 100+ 道附答案的檢核題、201 處程式碼行號對照、
  大量 ASCII 圖解。相對舊版新增兩條主線：
  - **設計歷程**（第 04、05、09 章）：從一句話需求推導模組切分；
    覆蓋演算法 **v0→v1→v2→v3** 四個版本的演進（內容取自 git 歷史
    `daf9225` / `21a2184` / `2356673` / `d454f7b` 與 2026-08-16 的開發日志），
    含四個被否決的修法（`scipy.ndimage.label` 連通標記、`res/2` 步長、
    「四鄰格全可走」、各 cell 各自求 PCA）。
  - **實作效果與能力邊界**（第 21~23 章）：14 種合成場地的實測。
- **`test/coverage_bench.py`**：用 `(X,Y)→bool` 判定函式合成地圖，
  前處理與 `map_server.py:468-469` 逐字相同，直接呼叫 `plan()`。
  六個指標：cell/run/臨界數、主軸與 λ₁/λ₂、覆蓋率（點到**線段**距離 ≤ 0.10 m）、
  掃描長/轉場長/轉場佔比、穿牆段數（掃描/轉場分開計）、可走面積。
  `--detail <場地>` 可印逐掃描帶診斷。
- **量到的結果**（14 種場地，`SPACING=0.18`、`MARGIN=0.10`）：
  - ★ **234 條掃描線，穿牆 0 條**（中心線取樣的構造性保證）
  - **L 形 4×4 可以跑**：覆蓋率 100.0%、3 個 cell、掃描線 0 穿牆；
    ⚠ 但主軸是 **−45°**（對稱 L 形的對角線），總長 67.9 m，比同面積長方形多約 23%，
    且角落出現 0.24 m 的極短掃描線。不對稱的 L 形（5×3）主軸 −20.1°、λ 比 4.60，明顯較好。
  - **正方形 3×3 的 λ₁/λ₂ = 1.00**（PCA 完全退化），覆蓋率仍有 98.2%
  - **未探索場地**：右側 29% 設為 `-1`，系統回報覆蓋率 **100.0%**、cell 1、穿牆 0
    —— **所有指標都是滿分**，但對真實空間的覆蓋率只有 **71%**
- **⚠ 新發現的缺陷（尚未修）**：
  1. **最外側掃描帶的落點是「刀鋒條件」**。`b_centers` 的最後一項可能超出 `b_max`：
     - 落在區外 → 那一整條沒掃（細長 6×1.5 → 96.3%；斜置 45° → 95.9%）
     - **正好貼在光柵化的鋸齒邊界上 → 碎裂**（斜置 30°：前 9 帶各 1 條 run，
       第 10 帶碎成 **22 條**長度 7~28 cm 的 run，`min_len=res`（5 cm）擋不住
       → **23 個 cell、30 段轉場穿牆**）。15° 與 45° 沒事純屬幾何巧合，任何角度都可能觸發。
  2. **無連通性檢查**：`MARGIN` 把通道封死時，`plan()` 仍會規劃跨區路徑，
     `move_base` 每個路點都失敗，被「跳過繼續」吞掉，最後仍顯示「完成」。
  3. 轉場直線接駁（既有缺陷）在斜置場地是常態：斜置 15° 已有 8 段穿牆。
- **建議的修法**（第 23 章，合計 < 20 行）：
  ① `scipy.ndimage.label` 只保留起點所在的連通元件；
  ② `b_centers` 改用 `np.linspace(b_min+spacing/2, b_max-spacing/2, round(...))`；
  ③ `run_coverage` 加 `skipped` 計數並回報。
- **怎麼驗的**：
  - 24 個檔案的 `<details>` 標籤配對、24 個內部章節連結全部通過程式檢查
  - **201 處程式碼行號**全部以程式驗證在檔案行數範圍內，另抽 19 處比對實際內容（19/19 通過）
  - `docs/README.md` 的 26 個連結全部通過存在性檢查
- **影響檔案**：`docs/01_學習資料/`（−8 +24）、`docs/README.md`、`test/coverage_bench.py`（新增）

---

## 2026-08-17　網頁調整：移除雷射/侵蝕圖層，行走軌跡改為只在執行中記錄

- **類型**：fix
- **動了什麼**：
  - `web/index.html`：`LAYERS` 從 8 層減為 6 層，移除「雷射掃描」與「侵蝕層」，
    並清掉隨之無用的 `scanPts`、`drawScan()` 與 200 ms 的 `/scan` 輪詢。
  - `scripts/map_server.py`：`odom_callback()` 只在 `cov_status['state'] == 'running'`
    時累積 `robot_path`；手動移動不留痕。`robot_pos`（機器人圖示與規劃起點用）
    仍然一律更新。
  - `/coverage/start` 裡把 `robot_path.clear()` 移到切換成 `running` **之前**，
    確保軌跡是從按下開始執行的那一刻起算，中間不會夾到殘留點。
- **為什麼**：實機看過網頁後，雷射點與侵蝕層在畫面上只是雜訊；
  行走軌跡原本從節點啟動就一直記，手動把機器人推去建圖的路徑也被畫進去，
  分不出哪一段才是演算法跑出來的結果。
- **保留的部分**：後端 `/scan`、`/map_eroded.png`、`/map_dilated.png` 三個端點沒有移除
  （仍是可用功能，`test/` 也可能用到），只是網頁不再顯示。
- **怎麼驗的**：mock 測試從 22 項增加到 28 項，新增 6 項針對軌跡行為：
  手動走 10 步軌跡長度為 0、但 `robot_pos` 有更新、開始執行時軌跡已清空、
  執行中走 10 步軌跡增長到 10 點、`/robot_state` 回傳點數一致、
  結束後軌跡保留且不再增長。前端另做 JS 語法檢查、id 對照、殘留字串掃描。
- **影響檔案**：`web/index.html`、`scripts/map_server.py`

---

## 2026-08-17　網頁：圖層重整、手動遙控（與執行互斥）、cell 視覺化、重啟 SLAM

- **類型**：feat
- **動了什麼**：
  - **`scripts/map_server.py`**
    - 新增 `/map_margin.png`：直接呼叫 `apply_safety_margin()` 產生，
      與規劃用的膨脹**完全一致**（原本的 `/map_dilated.png` 是 `MORPH_ITER` 顯示用，兩者保留）。
    - `/coverage/start` 改呼叫 `coverage_planner.plan()`（原本是 `boustrophedon()`），
      額外回傳 cell 分解結果；並把機器人目前位置當作 `start` 傳進去，
      讓貪婪最近鄰從實際起點開始排序。開始執行時清空行走軌跡。
    - `/coverage/status` 新增 `cells_px`（每個 cell 的路點，像素座標）、
      `info`（連通區間數／臨界點數／cell 數／主軸角度／λ1:λ2）、`manual`、`slam_managed`。
    - **新增 `/teleop`**（POST `{v, w}`，比例值 −1~1）：後端乘上 `V_MAX=0.18 m/s`、
      `W_MAX=1.5 rad/s` 後發布到 `/cmd_vel`。10 Hz 心跳送出，
      指令超過 `TELEOP_TTL=0.6` 秒沒續傳就自動歸零停車。
    - **新增 `/slam/restart`**：停覆蓋 → 停車 → 收掉 SLAM → 清空地圖/軌跡/規劃 → 重新啟動。
    - **模式互斥**：單一真相來源是 `cov_status['state']`，
      `== 'running'` 時 `/teleop` 回 409 且心跳不發布 `/cmd_vel`（控制權完全交給 move_base）；
      按停止、覆蓋完成、或發生錯誤都會離開 running，自動解鎖手動。
    - **SLAM 生命週期改由本節點管理**（`manage_slam` 參數，預設 true），
      以 `subprocess` 開獨立行程群組跑 `turtlebot3_slam.launch`，
      重啟時對整組送 SIGINT（逾時改 SIGKILL）。
  - **`launch/start.launch`**：移除 SLAM 的 `<include>`（改由 map_server 啟動），
    map_server 新增 `manage_slam` / `slam_methods` 兩個參數。原本的 include 保留為註解，
    要改回舊行為只需把 `manage_slam` 設成 false 並取消註解。
  - **`web/index.html`**：改成「地圖 + 右側控制欄」版面。
    - 圖層：原始地圖／安全邊距（膨脹）／侵蝕層／**cell 分解**／覆蓋路徑／行走軌跡／雷射／機器人。
    - cell 分解圖層：每個 cell 一種顏色（8 色輪用），粗實線＝掃描線、細虛線＝cell 內換行、
      字母 A/B/C… 標在重心表示走訪順序。
    - 手動操作：3×3 九宮格搖桿（含斜向）＋ 鍵盤 W/A/S/D、空白鍵停止、速度比例滑桿。
      按住持續送、放開自動停。執行中整組 disabled 並顯示鎖定提示。
    - 執行控制：開始執行／結束、進度條、規劃資訊表。
    - 建圖：重啟 SLAM 按鈕（有二次確認）。
- **為什麼**：原本網頁只能看，不能操作；要先把地圖建好得另外開 teleop 終端機，
  改場地擺設還得整包 roslaunch 重跑。而且 cell 分解做出來了卻看不到，
  沒辦法在展示時說明演算法。
- **怎麼驗的**：本機沒有 ROS，用 mock 把 rospy／tf2_ros／actionlib／move_base_msgs
  全部換掉，以 Flask test client 跑 22 項端點測試全數通過，涵蓋：
  四種圖層 PNG、遙控速度上下限夾制、逾時自動停車、開始執行後 `/teleop` 回 409 且
  心跳不發布、按結束/完成後解鎖、SLAM 重啟清空狀態、未管理 SLAM 時回 400、
  無地圖時開始執行被擋。前端另做 JS 語法檢查與 `getElementById` 對照檢查。
- **踩到的坑**：
  - `updateUI()` 每秒把 `btn-slam.disabled = false`，會蓋掉點擊處理器設的 3 秒冷卻，
    改成該按鈕的 disabled 只由自己的處理器管。
  - `imgCache['orig']` 決定 canvas 尺寸，原本只載入「開啟中」的圖層，
    使用者關掉原始地圖再重啟 SLAM 就會永遠空白。改成 orig 一律載入。
- **影響檔案**：
  - `scripts/map_server.py`、`web/index.html`、`launch/start.launch`
- **待辦／未驗證**：
  - **上述 ROS 相關功能尚未在實體機器上跑過**（本機無 ROS，只驗到 Flask 層）。
    首次上機要確認三件事：`/cmd_vel` 話題名稱是否與 bringup 一致、
    `roslaunch turtlebot3_slam` 子行程能否正常收掉、以及重啟 SLAM 後 move_base
    是否能在 TF 短暫中斷後自行恢復。
  - cell 之間仍是直線接駁交給 move_base，尚未用 A\* 規劃。

---

## 2026-08-16　演算法：補上真正的牛耕式 cell 分解，修掉掃描線穿越障礙

- **類型**：feat
- **動了什麼**：改寫 `scripts/coverage_planner.py`，把「單一全域 PCA + 等間距平行掃描」
  補成真正的 boustrophedon decomposition。新增 4 個內部函式與 1 個對外函式 `plan()`：
  - `principal_axes()`：PCA 抽成獨立函式（原本內嵌在 `boustrophedon()` 裡）。
  - `_slice_runs()`：**核心改動**。原本每條掃描帶只取 `proj_a` 的 min/max 當兩端，
    等於假設帶內永遠連通；改成沿掃描帶的**中心線**以 res/8 為步長取樣，
    只保留落在可走格上的連續區間，端點直接取自取樣點。
  - `_link_runs()`：相鄰兩帶的區間若沿長軸投影範圍重疊則視為相接。
  - `_build_cells()`：只有前後一對一才延伸成同一個 cell；一分為多（split）
    或多合為一（merge）即為**臨界點**，cell 在此切開。
  - `_cell_waypoints()` + `plan()` 裡的貪婪最近鄰：每個 cell 各自蛇行，
    四種進入方式（帶順序正/反 × 起始側左/右）取進入點離目前位置最近者。
  - `boustrophedon()` 簽名不變（`free, res, ox, oy`），兩個呼叫端
    `map_server.py:365`、`test/boustrophedon.py:59` 皆不需修改。
- **為什麼**：舊版有兩個同源的缺陷，實測 200×100 cm 場地（含圓形＋方形障礙）：
  1. 5 條掃描線**全部**橫跨障礙物，最嚴重一條 75% 長度落在障礙內，
     有效覆蓋率 0%（沒有任何一條線是機器人真的走得完的）；
  2. 端點以 `center + a極值·axis_a + b·axis_b` 還原，但 a 的極值與 b 來自不同格，
     垂直方向最多偏 `spacing/2` = 9 cm，傾斜 25° 時 8/10 路點落在膨脹帶內、
     離障礙僅 0.05 m，小於 Burger 外接圓半徑 0.112 m，move_base 會拒絕。
- **結果**（同一組合成地圖，舊版 → 新版）：

  | 場景 | 掃描線 | 穿障線段 | 壞路點 | 有效覆蓋率 | 路徑長 |
  |---|---|---|---|---|---|
  | 200×100 平行 | 5 → 11 | 5 → **0** | 2 → **0** | 0% → **100.0%** | 8.09 → 7.29 m |
  | 200×100 傾斜 25° | 5 → 9 | 5 → **0** | 8 → **0** | 0% → **99.6%** | 7.48 → 4.57 m |
  | 240×120 傾斜 35° | 6 → 11 | 6 → **0** | 6 → **0** | 0% → **99.4%** | 12.82 → 9.58 m |
  | 300×150 傾斜 15° | 8 → 21 | 8 → **0** | 11 → **0** | 0% → **99.7%** | 22.11 → 17.74 m |

  4 種房型 × 9 種傾角共 437 條掃描線的全掃描：撞到真實障礙 **0 條**；
  有 7 條輕微切到安全邊距帶，最深 4.5 mm（邊距本身有 100 mm 餘裕）；
  平均覆蓋率 97.4%、最低 86.0%。規劃耗時 1.3 ms（300×150 場景）。
- **踩到的坑**：
  - 第一版用 `scipy.ndimage.label` 對每條帶做 8-連通標記來切段。段的**端點連直線**
    仍會穿出去，因為連通段在網格上可能是彎的（繞過障礙轉角）。改成對中心線取樣後，
    線段由取樣點本身定義，才從構造上保證不越界。
  - 取樣步長 res/2 時，斜向掃描線仍會從障礙格角落「跨」過去，實測漏掉 11 mm 切角；
    改用 res/8。
  - 試過「取樣點的四個包夾格全可走」的保守判定，切角完全杜絕，但會把只有兩格寬的
    窄通道整條刪掉，平均覆蓋率從 97% 掉到 89%、最低 57%，代價過大，**不採用**。
- **影響檔案**：
  - `scripts/coverage_planner.py` — 大幅改寫（84 → 約 240 行）
  - `docs/01_學習資料/覆蓋規劃程式碼說明.md` — 新增（逐段程式碼講解報告）
- **待辦**：
  - cell 之間的接駁目前仍是直線送給 move_base 自行繞行，尚未用 A\* 規劃接駁路徑。
    這是唯一會影響數據正確性的項目（規劃路徑長 ≠ 實走路徑長）。
  - cell 走訪順序是貪婪最近鄰，未做 2-opt 最佳化。
  - 海報 `改_v2.docx` 第五、六節的敘述需同步更新（原本寫「主要限制」的部分已解決）。
- **更正**：本筆日志原本把「各 cell 各自求 PCA 主軸」列為下一步，經實測後**撤回**。
  逐 cell 重掃只讓掃描線 52 → 49 條（5.8%），但會破壞 cell 的定義性質
  （每條切片單一連通），實測 39 條掃描帶中有 10 條（26%）分裂成多段；
  且 L 型房間實測顯示它救不了全域主軸的偏差（cell 形狀本就由歪掉的全域軸切出，
  自身主軸仍離牆面 11～12°）。正確解法是**先分區、後求軸**，屬於另一個演算法。
  詳見 `docs/01_學習資料/覆蓋規劃程式碼說明.md` 第六節。

---

## 2026-08-16　海報加深：`改.docx` → `改_v2.docx`，補上第六節「驗證結果與討論」

- **類型**：docs
- **動了什麼**：
  - 新增 `docs/03_海報/gen_poster_v2.py`：以 `改.docx` 為底本產生 `改_v2.docx`，
    不動版面骨架（A3 直式、系統架構圖、標題橫幅），只改四格核心方法的內文與框高。
  - 三、安全邊距膨脹：補上 0.10 m 邊距的依據（Burger 底盤直徑 0.20 m 的半徑）、
    5×5 方形結構元素等價於 Chebyshev 距離（對角多留約 41% 餘裕）、
    與 costmap inflation 的分工差異、以及邊距大小的權衡。
  - 四、PCA 主軸對齊：補上共變異數矩陣 `C = (1/N) Σ dᵢdᵢᵀ` 的式子、
    「C 實對稱半正定 ⇒ 譜定理保證兩特徵向量正交」（說明掃描/換行方向為何天生垂直）、
    以及 `coverage_planner.py:56-59` 固定特徵向量正負號的用意（規劃結果可重現）。
  - 五、牛耕式演算法：補上 `SPACING = 0.18` 相對覆蓋寬度 0.20 m 的 10% 重疊依據；
    **刪除原稿「不需要事先做區域分解」這句錯誤敘述**，改為誠實說明
    `a_vals.min()/max()` 等於假設掃描帶連通，在凹形或帶柱子的房間會失效。
  - 六、驗證結果與討論：右下角原本只有空標題「六、」，新增一個內文方塊
    （複製 PCA 方塊的 XML 結構，改 id/z-index/位置/大小），內容為實機驗證流程、
    量化比較表（數字留空待量測）、已知限制、未來工作四段。
  - 內文字級由 12 pt 降為 11 pt、行高 12 pt、段後 5 pt，四格才塞得進既有框位；
    「一、研究動機」維持 12 pt 形成層級差。
- **為什麼**：原稿三格全是「怎麼做」，缺少參數依據、數學性質與結果驗證，深度不足；
  且第五節那句「不需要事先做區域分解」與程式實作不符，海報上寫出來會被問倒。
  第六節補齊「所以有沒有比較好、有沒有真的跑」這兩個評審必問的問題。
- **影響檔案**：
  - `docs/03_海報/gen_poster_v2.py` — 新增
  - `docs/03_海報/改_v2.docx` — 新增（由上述腳本產生，`.gitignore` 已忽略 docx）
- **待辦**：量化比較表的四個數字（掃描線數／路徑長／累積轉彎角／規劃耗時）尚未量測；
  可離線比較「地圖軸對齊 vs PCA 對齊」得出，不需實機統計。

---

## 2026-08-11　文件整併：`help/` + `note/` → `docs/` 六大分類

- **類型**：docs
- **動了什麼**：
  - 把原本 `help/` 與 `note/` 兩個資料夾的所有內容，合併到根目錄的 `docs/`，依用途分成六類：
    `01_學習資料`、`02_論文`、`03_海報`、`04_簡報`、`05_開發日志`、`06_規範`。
  - `gen_*.py` 產生腳本跟它的產出物放在同一層（腳本都用 `HERE = dirname(__file__)`，
    輸出路徑自動跟著搬，程式邏輯零改動，只更新 docstring 內的說明路徑）。
  - 新增 `docs/README.md` 作為總索引，含 01_學習資料的**建議閱讀順序**。
  - 修正搬移後失效的相對連結：
    `演算法原理.md` ↔ `coverage_algorithm.md`（改為同層互連）、
    `答辯資料/README.md` → `../../01_學習資料/*`、
    `05_開發日志/README.md` → `../06_規範/GIT_CONVENTION.md`、
    `教學報告.md` 的專案目錄樹改成新的 `docs/` 結構。
  - 刪除 `help/poster/__pycache__/`。
  - `.gitignore`：移除 `help/` 整包忽略，改為只忽略 `docs/**/*.docx`、`docs/**/*.pptx`
    （由 `gen_*.py` 產生的成品）。
- **為什麼**：文件散在 `help/` 與 `note/` 兩處，且 `help/` 內部把說明文件、論文、海報、簡報
  混在同一層，找東西要憑記憶。分類後有單一入口，也讓「學習用」和「交件用」的東西分開。
- **影響檔案**：
  - `docs/`（新增整棵樹，共 29 個檔案由 `help/`、`note/` 搬入）
  - `docs/README.md` — 新增（總索引）
  - `docs/01_學習資料/演算法原理.md`、`docs/01_學習資料/教學報告.md`、
    `docs/03_海報/答辯資料/README.md`、`docs/05_開發日志/README.md`、
    `docs/06_規範/GIT_CONVENTION.md` — 修正連結／目錄樹
  - `docs/02_論文/gen_paper.py`、`gen_learning.py`、`docs/03_海報/gen_poster.py`、
    `gen_arch.py`、`docs/04_簡報/gen_slides.py` — 只改 docstring 的輸出路徑說明
  - `.gitignore` — 改忽略規則
  - `help/`、`note/` — 移除（已淨空）
- **結果 / 驗證**：`docs/` 下 29 個檔案全部就位，`grep` 確認已無殘留的 `help/`、`note/`
  失效連結（CHANGELOG 舊條目內的歷史路徑刻意保留，那是當時的事實）。未動任何執行期程式碼，
  `scripts/`、`launch/`、`web/` 完全沒碰，不影響機器人執行。
- **待辦 / 已知問題**：
  - `.gitignore` 規則改變後，原本被忽略的 `docs/**/*.md`（學習資料、答辯資料）與 `gen_*.py`
    會開始進版控；若不想追蹤，把 `.gitignore` 改回整包忽略對應資料夾即可。
  - `docs/03_海報/改.docx` 檔名語意不明（手改稿），日後可考慮改成有意義的名稱。

---

## 2026-07-28　新增海報答辯補充資料 `help/poster/答辯資料/`

- **類型**：docs
- **動了什麼**：新增 6 份文件＋索引，專門收「海報上簡略帶過、但被追問時要答得出來」的細節。
  - `README.md`：索引，並回答「這些該不該加進海報」——**建議不要**（海報已滿版 1 頁 A3；
    細節是講出來的不是印上去的），只建議把 ④ 硬體層那行與 ③↔④ 箭頭標籤改精確。
  - `01_現成套件清單.md`：把海報 ③ 層的四個名字展開成實際的 6 個 ROS 套件
    （`turtlebot3_bringup` 底下其實是 `rosserial_python`＋`hls_lfcd_lds_driver`＋
    `robot_state_publisher` 三個節點）＋4 個 Python 函式庫，附現場查證指令。
  - `02_硬體規格與里程來源.md`：LDS-01／XL430／OpenCR 規格，以及「輪子轉幾度、走多遠」
    的完整鏈路與公式（4096 ticks/圈、1 tick ≈ 0.0506 mm、輪子一圈 0.207 m），
    並註明 ROS 端沒有套件在算里程、以及官方韌體的 θ 取自 IMU 這個易被抓的細節。
  - `03_參數速查與選擇理由.md`：自訂參數（0.18／0.10／MORPH_ITER 2／0.1 m 軌跡門檻…）
    與官方預設值分開列，並釐清**系統裡有三個獨立的「膨脹」**（規劃安全邊距／網頁顯示圖層／
    costmap inflation），這題最容易被問倒。
  - `04_演算法數學細節.md`：PCA 從共變異數矩陣到 Rayleigh 商的推導、投影切帶、複雜度分析。
  - `05_預想問答.md`：28 題 Q&A，含「怎麼證明完全覆蓋」「L 形房間怎麼辦」等會被抓的題目。
  - `06_已知限制與未來工作.md`：11 項限制與優先順序排序。
- **為什麼**：使用者要準備口試備詢，海報只能寫結論，需要一個地方放展開的細節。
- **驗證**：所有數字與行號都對照 `scripts/map_server.py`、`scripts/coverage_planner.py`、
  `launch/start.launch`、`web/index.html` 原始碼核對過；外部套件的預設值標注為
  「官方預設，請用 `rosparam get` 確認」，未當成實測值陳述。
- **影響檔案**：`help/poster/答辯資料/`（新增 7 個檔）

---

## 2026-07-28　系統架構圖重畫：色帶改真方塊圖、層序翻轉、箭頭改標實際介面

- **類型**：docs
- **動了什麼**：重寫 `help/poster/gen_poster.py` 的系統架構圖，並新增 `help/poster/gen_arch.py`。
  - **色帶 → 真方塊圖**：舊版 `arch_band()`／`arch_conn()`（段落底色＋粗左框線假裝色條、
    箭頭是打字的 ▼▲）整組移除，改用巢狀表格畫出有彩色外框的方塊：新增
    `tbl_borders()`、`cell_borders()`、`fix_width()`、`_fig_table()` 與
    `arch_box()`／`arch_sub()`／`arch_core()`／`arch_flow()`／`arch_caption()`／
    `build_arch_figure()`。
  - **層序翻轉**：改為由上而下「① 使用者端 → ② 本專題自行開發 → ③ ROS 現成套件 →
    ④ 機器人硬體」。舊版把硬體放最上面，卻在內文寫「由下而上感知、由上而下下令」，
    圖與文互相矛盾。
  - **② 層拆成兩個子方塊**：`coverage_planner.py`（純演算法、不依賴 ROS）→ 路點串列 →
    `map_server.py`（ROS 節點），把「演算法與 ROS 解耦」這個賣點畫出來；紫色外框加粗
    2.25 pt，是全圖唯一亮色。
  - **箭頭標籤改標實際介面**：`/coverage/start`、`move_base action goal`、
    `/map`·`/tf`·`/scan`·`/odom`、`/cmd_vel`，取代舊版「感知：四周距離」這類形容詞；
    左紅為指令下行、右灰為感測與狀態上行。並補上 `map_server` 其實直接訂閱
    `/scan`、`/odom`（舊圖只畫硬體→套件，漏掉這條）。
  - **新增 `gen_arch.py`**：只輸出 `系統架構圖.docx`（與海報同寬 A3），可直接複製貼進
    手改中的 `改.docx`。
  - 為了讓變高的架構圖仍塞得下 A3 單頁，全域字級／行距同步收緊：`body`／`bullet`
    10.5→10 pt、行距 1.15→1.06、`mono_box` 8.5→7.5 pt、`section` 段前 7→3 pt、
    橫幅上下內距 150→110 dxa。
- **為什麼**：使用者指出程式生成的架構圖仍不完善——它其實不是方塊圖，看不出誰接誰，
  箭頭標的不是介面名稱，且圖的上下順序與內文敘述相反。
- **驗證**：Word COM 轉 PDF＋PyMuPDF 算圖檢視，`專題海報.docx` 為 **1 頁 A3**
  （內容底緣 40.63 cm，邊界 40.9 cm 內）；`系統架構圖.docx` 為 1 頁，四層方塊、
  框線、箭頭標籤與圖例皆正確呈現、無跨頁截斷。
- **影響檔案**：`help/poster/gen_poster.py`、`help/poster/gen_arch.py`（新增）
- **注意**：重新產生前需先關閉 Word 中已開啟的 `專題海報.docx`／`系統架構圖.docx`，
  否則存檔會 PermissionError；已開著的話請關掉重開才會看到新版。

---

## 2026-07-27　海報改版：系統架構改「分層方塊圖為主」、核心方法拆三節、移除系統實作

- **類型**：docs
- **動了什麼**：續前一版再調整 `help/poster/gen_poster.py`。
  - 「二、系統架構」由條列文字改為**四層分層方塊圖為主、文字為輔**：硬體→現成套件→我寫的
    程式→使用者端，每層一條粗左彩條色帶，層間以置中箭頭列標注傳遞的資料（▼感知／▲下令）。
    新增 `arch_band()`、`arch_conn()` 兩個元件與使用者端綠色 US_C/US_BG。
  - **核心方法拆成三個獨立節**：三 PCA 主軸對齊、四 安全邊距膨脹、五 牛耕路點生成，
    各自附示意圖／程式碼框；牛耕路點新增蛇行示意 ASCII 圖。
  - **移除「系統實作（三執行緒解耦）」**整節。
  - 版面重構為：全寬動機 → 全寬架構圖 → 雙欄（左：PCA＋膨脹；右：牛耕＋ROS概念）→
    全寬結果結論 → 參考文獻，讓內容由上到下填滿、結論置底不留大片空白。
  - 新增 `full_cell()`（全寬單格）、`mono_box` 加細框、`OUT_NAME` 支援環境變數改輸出檔名
    （方便產生預覽檔）。
- **為什麼**：使用者要求系統架構以圖為主、文字為輔；核心方法分別拆開說明；系統實作不需要；
  並把底部空白透過排版填滿。
- **驗證**：以 Word COM 將 `_preview.docx` 轉 PDF、PyMuPDF 算圖檢視，確認為 **1 頁 A3**、
  四層架構圖清楚、結論與參考文獻落在底部邊界內、無大片空白。
- **影響檔案**：`help/poster/gen_poster.py`

---

## 2026-07-27　海報系統架構改寫：三層角色 + 白話運作 + ROS 概念

- **類型**：docs
- **動了什麼**：改寫 `help/poster/gen_poster.py` 的內容區塊，讓未深入了解專題的讀者也能讀懂。
  - 新增「二、系統怎麼運作（白話總覽）」整段口語敘述整條資料流。
  - 「三、系統三大角色與互動」用色塊標頭把**硬體 / 現成套件 / 我寫的程式**分成三層，
    各附一句到三句簡介；現成套件依需求獨立成一區塊，逐一介紹 turtlebot3_bringup、
    gmapping、move_base+DWA。新增資料流迴圈示意圖與「互動關鍵」說明。
  - 新增「四、支撐本專題的 ROS 概念」：Node／Topic／Action／TF／launch，各自扣回專題用途。
  - 新增樣式工具 `left_bar()`（段落左彩條）、`role_head()`（角色標頭），
    `bullet()` 加 `lead_color` 參數；新增三層角色配色 HW/RD/MY。
  - 原核心方法②③（安全膨脹、牛耕路點）合併為一節，結果與結論精簡，讓版面塞滿 A3。
- **為什麼**：使用者要求海報要能面向非專題背景的評審——用文字描述整體運作、明確標示硬體／
  現成套件／自寫程式三者互動，並補 ROS 背景，且排版要佔滿 A3 不留過多空白。
- **影響檔案**：`help/poster/gen_poster.py`
- **注意**：重新產生前需先關閉 Word 中已開啟的 `專題海報.docx`，否則存檔會 PermissionError。

---

## 2026-07-24　整理專案結構：scripts/ 只留執行路徑，測試工具集中 test/

- **類型**：chore
- **動了什麼**：
  - `scripts/boustrophedon.py` → `test/boustrophedon.py`（`git mv`）。它在 launch 內被註解掉，
    不是啟動後的執行路徑；正式覆蓋路徑由 `map_server.py` 自行計算並顯示於網頁。
  - 修正搬移後的 import：原本 `sys.path.insert(0, 自身目錄)` 才找得到 `coverage_planner`，
    改成指向 `../scripts`，否則在 `test/` 下會 ImportError。
  - `CMakeLists.txt` 移除 `scripts/boustrophedon.py` 的 `catkin_install_python`。
  - `launch/start.launch` 刪掉那段註解掉的 `<node>`（`pkg`/`type` 已不再指得到），
    改在檔尾統一列出 `test/` 五支工具的單獨執行指令；後續節次編號 5 → 4。
  - `.gitignore` 移除 `test/`，把 `map_recorder.py`、`test_lidar_freq.py`、
    `test_lidar_range.py` 一併納入版控。
  - 同步更新 `help/ros_topics_nodes.md`、`help/coverage_algorithm.md`、
    `help/教學報告.md`（目錄樹）、`help/路徑規劃架構與假完成診斷.md` 的路徑與行號。
- **為什麼**：使用者要求「啟動後會用到的程式放 scripts/ 與 web/，沒用到的測試程式歸 test/」，
  讓資料夾本身就能表達「哪些是執行路徑」。test/ 解除忽略是使用者選的——那幾支量測工具
  （光達有效距離、/map 頻率）是有價值的實驗程式，值得留在 repo 而非只存在本機。
- **影響檔案**：
  - `scripts/boustrophedon.py` → `test/boustrophedon.py`（移動 + 改 import/docstring）
  - `CMakeLists.txt`、`launch/start.launch`、`.gitignore`
  - `test/map_recorder.py`、`test/test_lidar_freq.py`、`test/test_lidar_range.py`（新納入版控）
  - `help/ros_topics_nodes.md`、`help/coverage_algorithm.md`、`help/教學報告.md`、
    `help/路徑規劃架構與假完成診斷.md`
- **結果 / 驗證**：三支主程式 `ast.parse` 語法檢查通過；`grep` 確認全專案已無殘留的
  `scripts/boustrophedon.py` 路徑引用。**未在實機 roslaunch 驗證**——啟動路徑本身沒被更動
  （`map_server.py`、`coverage_planner.py`、`web/index.html` 皆原封不動），但 catkin 重新
  `catkin_make` 後才會反映 CMakeLists 的異動。
- **待辦 / 已知問題**：
  - `help/` 仍在 `.gitignore` 內，故上述文件更新不會進版控。
  - `help/教學報告.md` 內多處 `boustrophedon.py:NN` 行號引用在本次搬移前就已與程式碼不符
    （部分實際指向 `coverage_planner.py`），本次未逐一修正。

## 2026-07-23　新增演算法原理技術文件

- **類型**：docs
- **動了什麼**：
  - 新增 `note/演算法原理.md`，聚焦三大核心演算法的**數學原理與逐行程式對照**：
    安全邊距膨脹（形態學 dilation 定義、一維/二維直覺、規劃用 vs 顯示用差異）、
    PCA 主軸對齊（去中心化→協方差→特徵分解→挑軸的四步，及 `np.cov`/`eigh` 逐行）、
    牛耕式覆蓋（投影分帶、蛇行交替、10% 重疊、全向量化）。
  - 附「函式庫 vs 我們」的分工表，釐清哪些是 SciPy/NumPy 做、哪些是本專案邏輯。
- **為什麼**：使用者要一份偏原理層面的技術文件，供報告/口試用；既有
  `help/coverage_algorithm.md` 偏流程串接，兩者互補，文首互相交叉連結。
- **影響檔案**：
  - `note/演算法原理.md`（新增）
- **結果 / 驗證**：依 `coverage_planner.py`、`map_server.py` 原始碼統整，未動任何程式邏輯。
- **待辦 / 已知問題**：無。

## 2026-07-21　新增專題海報（Word）生成器

- **類型**：docs
- **動了什麼**：
  - 新增 `help/poster/gen_poster.py`，以 python-docx 生成 A3 直式專題海報 `help/poster/專題海報.docx`。
  - 版面：頂部深藍標題橫幅 + 作者列，下方雙欄（無框線表格）分七區：研究動機與目的、
    系統架構、PCA 主軸對齊、安全邊距膨脹、牛耕路點生成、三執行緒解耦、結果與結論，
    底部附參考文獻列；含資料流／PCA 對齊／安全邊距程式碼等等寬字示意方塊。
- **為什麼**：使用者要一份可列印的專題海報，格式用 Word。
- **影響檔案**：
  - `help/poster/gen_poster.py`（新增）
  - `help/poster/專題海報.docx`（新增，生成產物）
- **結果 / 驗證**：執行 `python gen_poster.py` 成功產出 A3（29.7×42 cm）docx，
  內容依 `專案設計架構.md`、`coverage_algorithm.md`、`ros_topics_nodes.md` 統整，未動程式邏輯。

---

## 2026-07-10　新增覆蓋演算法說明文件

- **類型**：docs
- **動了什麼**：
  - 新增 `help/coverage_algorithm.md`，說明牛耕式覆蓋演算法（`coverage_planner.py`）：
    PCA 主軸對齊、安全邊距膨脹、投影分帶、來回掃描與 10% 重疊；以及 `run_coverage()`
    送 move_base 的執行策略、三執行緒解耦如何達成「即時呈現在網頁」。
- **為什麼**：使用者想了解演算法怎麼實作、又怎麼流暢地邊走邊即時呈現。
- **影響檔案**：
  - `help/coverage_algorithm.md`（新增）
- **結果 / 驗證**：依 `coverage_planner.py`、`map_server.py`、`boustrophedon.py` 原始碼描述，未動程式邏輯。

---

## 2026-07-10　新增 /web 網頁架構說明文件

- **類型**：docs
- **動了什麼**：
  - 新增 `help/web_architecture.md`，說明 `map_server.py`（Flask 後端）＋ `web/index.html`
    （前端）如何把 ROS 節點資料呈現在網頁：一節點雙角色、ROS 回呼存記憶體、Flask 路由
    轉 PNG/JSON、前端 1s＋200ms 雙輪詢畫 Canvas、覆蓋按鈕反向控制 move_base。
- **為什麼**：使用者想了解網頁端的資料呈現原理。
- **影響檔案**：
  - `help/web_architecture.md`（新增）
- **結果 / 驗證**：依 `map_server.py` Flask 路由與 `index.html` 前端程式描述，未動程式邏輯。

---

## 2026-07-10　ROS 統整文件補充各 Subscriber topic 用途

- **類型**：docs
- **動了什麼**：
  - `help/ros_topics_nodes.md` 新增「四之一、各 Subscriber 訂閱的 Topic 是用來做什麼」段落，
    逐一說明 `/map`、`/odom`、`/scan`、`/tf`(+`/tf_static`) 各 callback 的實際用途與處理流程。
- **為什麼**：使用者想知道每個訂閱的 topic 分別拿來做什麼事。
- **影響檔案**：
  - `help/ros_topics_nodes.md`（新增段落）
- **結果 / 驗證**：依 `map_callback`、`odom_callback`、`scan_callback` 原始碼描述，未動程式邏輯。

---

## 2026-07-10　新增 ROS 節點/Topic 統整文件

- **類型**：docs
- **動了什麼**：
  - 新增 `help/ros_topics_nodes.md`，統整本專案所有 Node、Publisher、Subscriber、Topic，
    並標註各項出自哪一隻程式（含原始碼行號）。
- **為什麼**：使用者需要一份清楚列表，快速掌握專案的 ROS 收發結構。
- **影響檔案**：
  - `help/ros_topics_nodes.md`（新增）
- **結果 / 驗證**：依 `scripts/map_server.py`、`scripts/boustrophedon.py`、`launch/start.launch` 原始碼整理，未動到程式邏輯。

---

## 2026-06-27　網頁新增 /scan 即時雷射圖層

- **類型**：feat
- **動了什麼**：
  - **後端 `map_server.py`**：
    - 新增訂閱 `/scan`（`LaserScan`），用 `tf2_ros` 查詢 `map ← 雷射座標` 轉換，
      把雷射點轉到地圖世界座標、再用既有 `world_to_px` 換成裁切後圖片像素。
    - 新增 `/scan` 路由，回傳 `{'points': [[px,py],...]}`。
    - `main()` 建立 tf2 Buffer/Listener 並訂閱 `/scan`。
  - **前端 `web/index.html`**：
    - 新增「雷射掃描」圖層（紅點，可開關）。
    - 新增 `drawScan()` 把雷射點畫成小方點。
    - 新增 **5 Hz 獨立輪詢** `refreshScan()`：地圖維持 1 Hz、雷射用 200ms 輪詢，
      這樣地圖慢慢長、雷射點即時跳動，能直觀看到「掃描→建圖」過程。
- **為什麼**：使用者想在網頁直觀看到 `/scan` 不斷更新產生地圖的過程。
  原本前端只有 1 Hz 輪詢、地圖又只有 ~0.33 Hz，看起來「沒在動」。
  釐清觀念：`/map` ~0.33 Hz 是 gmapping 出圖節奏，`/scan` 才是 ~5 Hz 的雷達即時資料。
- **影響檔案**：
  - `scripts/map_server.py` — 新增 LaserScan/tf2 import、scan 狀態、`scan_callback`、`/scan` 路由、main 訂閱
  - `web/index.html` — 新增 scan 圖層、`drawScan()`、5 Hz `refreshScan()`
- **結果 / 驗證**：`python -c ast.parse` 語法檢查通過；尚未在實機/模擬器跑過 ROS 端驗證。
- **待辦 / 已知問題**：
  - 需在實機或 Gazebo 確認 `map → base_scan` 的 TF 鏈存在、雷射點與地圖對齊。
  - 若 TF 查不到（例如尚未收到 map→odom）會回空陣列，前端不畫點，屬正常退場。
  - 雷射座標 frame 預設取 `msg.header.frame_id`，TB3 通常為 `base_scan`。

---

## 2026-06-27　start.launch 移除 map_recorder（改回測試工具定位）

- **類型**：refactor
- **動了什麼**：
  - 從 `start.launch` 移除 `map_recorder` 節點，以及 `record` / `record_period` 兩個 launch 參數。
  - 在 launch 內留下註解，說明 `test/map_recorder.py` 為測量用途、需要時單獨執行的方式。
- **為什麼**：`map_recorder.py` 是用來**測量雷達原始地圖每秒接收幾張、觀察每張地圖變化**的測試工具，
  並非專案功能，不該掛進正式啟動流程。它本身就設計成獨立節點（啟動自建時間戳資料夾、可單獨跑）。
- **影響檔案**：
  - `launch/start.launch` — 移除 `record`/`record_period` 參數與 `map_recorder` 節點，改放使用說明註解
- **結果 / 驗證**：未實機驗證；單獨測量時執行 `python3 test/map_recorder.py`
  （或加 `_min_period:=1.0` 節流），存圖到 `maps/<時間戳>/`。
- **待辦 / 已知問題**：無（先前 2026-06-23 那筆的 catkin 路徑待辦已不適用——不再由 launch 啟動）。

---

## 2026-06-27　新增 note/ 開發日志資料夾

- **類型**：docs
- **動了什麼**：
  - 新增 `note/` 資料夾，建立開發日志制度。
  - `note/README.md`：日志撰寫規範與模板。
  - `note/CHANGELOG.md`：開發日志主檔（本檔），時間倒序記錄每次程式修改。
- **為什麼**：commit message 只能寫一句話摘要，無法記錄改動的動機、做法與踩到的坑。
  需要一份更詳細、給未來自己看的開發紀錄。
- **影響檔案**：
  - `note/README.md` — 新增
  - `note/CHANGELOG.md` — 新增
- **結果 / 驗證**：純文件，無需執行驗證。
- **待辦 / 已知問題**：往後每次改程式都要回來補一筆。

---

## 2026-06-23　地圖錄製功能 + 地圖顯示形態學還原（未提交）

- **類型**：feat / refactor
- **動了什麼**：
  - **地圖錄製**：在 `start.launch` 新增 `map_recorder` 節點，
    每次收到 `/map` callback 就把當下地圖存成一張 PNG 到 `maps/<時間戳>/`。
    新增兩個 launch 參數：
    - `record`（預設 `true`）：是否啟用錄製。
    - `record_period`（預設 `0.0`）：兩次存圖最小間隔秒數，`0` = 每次都存。
    對應執行檔為 `test/map_recorder.py`。
  - **地圖顯示形態學還原**：`map_server.py` 的侵蝕／膨脹圖層，
    從「動態套用 `apply_safety_margin`（與路徑規劃同步）」改回
    「固定 3×3 核、`MORPH_ITER = 3` 次的純視覺化處理」。
    補回 `from scipy.ndimage import binary_dilation`。
  - **註解精簡**：移除 `map_server.py` 多數函式的 docstring。
  - **`.gitignore`**：新增忽略 `maps/`（錄製輸出）與 `help/`。
- **為什麼**：
  - 要把每次建圖過程的原始地圖留存下來，方便事後分析 / 做資料集。
  - 顯示用的侵蝕／膨脹層改回固定核，與路徑規劃的安全邊距解耦（純視覺參考）。
- **影響檔案**：
  - `launch/start.launch` — 新增 `record` / `record_period` 參數與 `map_recorder` 節點
  - `scripts/map_server.py` — 形態學圖層改回固定核、補 import、精簡 docstring
  - `.gitignore` — 忽略 `maps/`、`help/`
  - `test/map_recorder.py` — 錄製節點（既有檔案）
- **結果 / 驗證**：尚未驗證（工作目錄中尚未 commit）。
- **待辦 / 已知問題**：
  - launch 中 `type="map_recorder.py"` 對應的執行檔目前在 `test/`，
    需確認 catkin 能在套件路徑找到（或移到 `scripts/`）。
  - 確認錄製頻率與磁碟用量是否需要節流。
