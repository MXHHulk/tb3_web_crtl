# TurtleBot3 CCPP — 牛耕式完全覆蓋路徑規劃

> **第一次看／隔一陣子回來**：先讀 [docs/專案架構說明.html](docs/專案架構說明.html)（白話版全貌），
> 再看下面「目前狀態」和 [開發日志](docs/05_開發日志/CHANGELOG.md) 最上面幾筆。

## 目前狀態（2026-11-11 收工時）

- 分支 `rebuild`，已推上 origin；車上版本 `26f1a1f`（`turtlebot3_ccpp/.synced_commit`），與本地 HEAD 的程式一致。
- 車子：`ubuntu@172.20.10.5`（手機熱點），控制台 `http://172.20.10.5:8000` 開機自動執行；收工時系統為停止狀態。
- 已完成並實車驗證：手機控制台、自動建圖（explore_lite）、SLAM 參數調整＋去雜點、直線循跡＋外圈
  （最後一次實測覆蓋率 97.7%、83/83 路點、322 秒）。
- **已上車、還沒實車跑**：跨區移動改由自己開（`_drive_to`：直線或借 move_base 算路線），DWA 退為備援；`ESCAPE_CLEAR` 0.25 → 0.18。
  上一次實測唯一一次受困（路點 14～16，離牆 0.20 m 時 DWA 不肯轉）就是為了這個。

### 下次從這裡開始

1. 在同一個場地跑「清空地圖 → 自動建圖 → 自動覆蓋」，取回紀錄（指令見架構說明第 9 章），確認：
   `events.txt` 裡 `own_nav` 是否都成功、還有沒有 `改用 move_base`／受困；轉角是否擦牆。
2. 看 `data/coverage/<任務>_map.png`，掃描線若仍左右擺動，試 `LINE_K_HEAD` 2.0 → 1.5 或 `LINE_V` 0.12 → 0.10。
3. 未來規劃清單見架構說明第 12 章（外圈先走可選、AMCL 鎖地圖、手動修圖、網頁看歷次紀錄、障礙物周圍補一圈、光達無資料偵測）。

## 資料夾

```
turtlebot3_ccpp_local/
├── turtlebot3_ccpp/   ★ 車上跑的全部程式（= 車上 ~/catkin_ws/src/turtlebot3_ccpp，一對一）
│   ├── scripts/       launcher.py（控制台 :8000）、map_server.py（主節點 :8080）、coverage_planner.py（演算法）
│   ├── launch/        start.launch、slam_gmapping.launch
│   ├── config/        gmapping_params.yaml
│   ├── web/           launcher.html（手機版）、index.html（電腦版）
│   ├── test/          量測與離線評估工具（不在正式啟動流程）
│   ├── tools/         同步腳本、開機服務
│   ├── CMakeLists.txt / package.xml
│   └── maps/、data/   地圖與執行紀錄（車上產生，不進版控、不同步）
└── docs/              文件（架構說明、學習資料、論文、海報、簡報、開發日誌、規範），不上車
```

## 改程式的流程

1. 改 `turtlebot3_ccpp/` 底下的程式
2. 在 `docs/05_開發日志/CHANGELOG.md` 最上面補一筆
3. `git commit`、`git push origin rebuild`
4. 同步到車上（只送已 commit 的內容；改了 CMakeLists 加 `--build`）：

```bash
bash turtlebot3_ccpp/tools/sync_to_robot.sh
```

5. 改到 launch 或 SLAM／move_base 參數時，要在手機「系統」頁停止再啟動才會生效。

## 使用

手機連上和車子同一個熱點，瀏覽器開 `http://<車子 IP>:8000`。
