# TurtleBot3 地圖 Web 伺服器邏輯解析 (`map_server.py`)

本文件詳細說明了如何將 TurtleBot3 的 ROS `/map` 訊息透過 Flask 伺服器發佈到網頁上的實作邏輯。

## 1. 程式進入點：`main()`
程式的執行流程從 `main()` 開始，其核心職責是初始化並協調 ROS 與 Web 伺服器：

- **ROS 節點初始化**：`rospy.init_node('map_server')` 建立名為 `map_server` 的節點。
- **取得參數**：透過 `rospy.get_param` 讀取連接埠，預設為 `8080`。
- **訂閱地圖**：`rospy.Subscriber('/map', OccupancyGrid, map_callback)`。每當地圖有更新時，都會自動觸發 `map_callback` 函數。
- **自動偵測 IP**：透過 `socket` 模組取得當前電腦的內部 IP，方便使用者知道要在瀏覽器輸入哪個網址。
- **啟動 Flask 執行緒**：
  - 由於 Flask 的 `app.run()` 是阻塞式的（會卡住程式），我們使用 `threading.Thread` 將 Web 伺服器放在後台執行。
  - 設定 `daemon=True` 確保當 ROS 節點關閉時，Web 伺服器也會跟著停止。
- **主循環**：執行 `rospy.spin()`，讓主執行緒留在這裡處理 ROS 的回調（Callback）。

## 2. 地圖處理核心：`map_callback(msg)`
這是將 ROS 數據轉化為圖片的關鍵流程：

1. **數據轉換**：ROS 的 `OccupancyGrid` 是一個一維陣列，值為 `-1` (未知)、`0` (空地)、`100` (障礙物)。
   - 使用 `numpy` 將其重新塑形（reshape）成二維矩陣。
2. **灰階映射**：
   - 未知區域 (`-1`) 設為灰色 (128)。
   - 已知區域將 0~100 映射至 255~0（0 為白，100 為黑）。
3. **座標修正**：ROS 的地圖原點在左下角，但電腦圖片的原點在左上角，因此使用 `np.flipud(gray)` 進行上下翻轉。
4. **影像壓縮**：利用 `PIL (Pillow)` 將 numpy 陣列轉換為 PNG 格式。
5. **執行緒安全**：使用 `map_lock` 保護 `map_png` 變數，避免 Flask 讀取時 ROS 同時在寫入導致資料損毀。

## 3. Web 服務介面 (Flask Routes)

- **`/` (首頁)**：
  - 讀取 `web/index.html` 檔案並回傳。這讓同網域的設備可以看到監控介面。
- **`/map.png` (圖片介面)**：
  - 從記憶體中提取最新的 `map_png` 二進位數據。
  - 使用 `send_file` 回傳圖片，並設定標頭 `Cache-Control: no-store`，強制瀏覽器每次都抓取最新圖資，不使用舊快取。

## 4. 呈現方式總結
TurtleBot3 的地圖是透過 **「即時影像串流」** 的概念呈現。前端網頁會不斷（或定期）請求 `/map.png`，後端則負責將 ROS 複雜的佔據網格資料轉換成簡單、輕量的圖片格式，達成跨平台、跨裝置的可視化。
