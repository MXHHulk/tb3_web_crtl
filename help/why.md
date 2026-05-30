# 為什麼這樣寫？

## 目標

一條指令啟動，讓同網域的任何裝置都能用瀏覽器看到 TB3 的即時地圖。

---

## 整體流程

```
TB3 實體
  └─ SLAM (gmapping) 發布 /map topic
        │
        ▼
  map_server.py  (ROS 節點 + Flask)
    ├─ 訂閱 /map → 轉成 PNG 存在記憶體
    └─ Flask 對外提供 HTTP
          │
          ├─ GET /          → 回傳 index.html（監控頁面）
          └─ GET /map.png   → 回傳最新地圖 PNG
                │
                ▼
  瀏覽器（任何同網域設備）
    └─ 每 2 秒重新請求 /map.png → 顯示最新地圖
```

---

## 為什麼用 Flask？

Flask 是 Python 的輕量 HTTP 框架。  
這個專案的核心邏輯（ROS subscriber + 圖片轉換）已經用 Python 寫了，  
直接在同一個 Python 程式裡加 Flask，就能把地圖「搬」到網路上，  
不需要額外安裝 ROS 的 rosbridge 套件，也不需要 Nginx 這類獨立 Web 伺服器。

---

## 為什麼用輪詢（每 2 秒抓一次）而不用 WebSocket？

輪詢只需要一行 JS：
```javascript
setInterval(() => { img.src = '/map.png?t=' + Date.now(); }, 2000);
```

SLAM 地圖本來就是幾秒更新一次，2 秒抓一次已經夠用。  
WebSocket 或 SSE 需要更多程式碼，在這個用途裡是過度設計。

---

## 為什麼用 `?t=Date.now()` ？

瀏覽器看到同一個 URL 會直接用快取，不重新發請求。  
加上時間戳記讓每次 URL 都不一樣，強迫瀏覽器每次都去伺服器抓新圖。

---

## 為什麼地圖要上下翻轉（`np.flipud`）？

ROS 的地圖座標原點在**左下角**（Y 軸朝上），  
圖片的座標原點在**左上角**（Y 軸朝下）。  
不翻轉的話地圖會上下顛倒。

---

## 為什麼用 `rospkg` 找路徑，不寫死？

```python
PKG = rospkg.RosPack().get_path('turtlebot3_ccpp')
```

catkin 編譯後腳本會被符號連結到 `devel/lib/`，  
用 `__file__` 推算路徑會指到錯誤位置。  
`rospkg` 直接查詢 ROS 套件索引，永遠回傳正確的原始碼路徑。

---

## 為什麼 Flask 要跑在獨立執行緒？

```python
threading.Thread(target=lambda: app.run(...), daemon=True).start()
rospy.spin()  # 主執行緒
```

`rospy.spin()` 需要佔住主執行緒等待 ROS 訊息。  
Flask 的 `app.run()` 也是阻塞式的。  
把 Flask 放到 daemon thread，兩者就能同時跑。  
設 `daemon=True` 代表主程式結束時 Flask 也自動關閉，不會殘留。

---

## 為什麼 launch 用 `<env>` 設定 TURTLEBOT3_MODEL？

```xml
<env name="TURTLEBOT3_MODEL" value="$(arg model)" />
```

`export` 只在當前 shell 有效。  
`<env>` 會在 roslaunch 啟動每個節點之前注入環境變數，  
不需要使用者手動 export，啟動更方便。

---

## 檔案對應

| 檔案 | 職責 |
|------|------|
| `scripts/map_server.py` | ROS 節點：訂閱地圖、轉 PNG、Flask 伺服器 |
| `web/index.html` | 瀏覽器頁面：顯示地圖、每 2 秒刷新 |
| `launch/start.launch` | 一鍵啟動：bringup + SLAM + Flask |
