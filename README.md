# TurtleBot3 CCPP — 牛耕式完全覆蓋路徑規劃

```
turtlebot3_ccpp_local/
├── turtlebot3_ccpp/   ★ 車上跑的全部程式（= 車上 ~/catkin_ws/src/turtlebot3_ccpp，一對一）
│   ├── scripts/       ROS 節點與控制台：map_server.py、coverage_planner.py、launcher.py
│   ├── launch/        start.launch
│   ├── web/           網頁：launcher.html（手機版，port 8000）、index.html（電腦版，port 8080）
│   ├── test/          量測與離線評估工具（不在正式啟動流程）
│   ├── tools/         同步腳本、開機服務
│   ├── CMakeLists.txt / package.xml
│   └── maps/          地圖錄製輸出（不進版控、不同步）
└── docs/              文件（學習資料、論文、海報、簡報、開發日誌、規範），不上車
```

## 改程式的流程

1. 改 `turtlebot3_ccpp/` 底下的程式
2. 在 `docs/05_開發日志/CHANGELOG.md` 補一筆
3. `git commit`、`git push origin rebuild`
4. 同步到車上（只送已 commit 的內容）：

```bash
bash turtlebot3_ccpp/tools/sync_to_robot.sh
```

## 使用

手機連上和車子同一個熱點，瀏覽器開 `http://<車子 IP>:8000`。
