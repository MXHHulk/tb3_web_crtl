# 開發日志 CHANGELOG

> 撰寫規範見 [README.md](./README.md)。最新的日志放最上面。

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
