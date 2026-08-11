# 開發日志 CHANGELOG

> 撰寫規範見 [README.md](./README.md)。最新的日志放最上面。

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
