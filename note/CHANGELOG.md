# 開發日志 CHANGELOG

> 撰寫規範見 [README.md](./README.md)。最新的日志放最上面。

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
