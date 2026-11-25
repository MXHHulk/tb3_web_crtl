# 成果影片動畫簡報

3 分鐘專題成果影片的畫面素材：13 鏡動畫，每鏡一件事，各自輸出成 MP4 給剪輯軟體用（旁白、配樂由剪輯時加）。
內容、旁白、數據出處以 `../簡報生成.md` 為準；分鏡與時長見 `導演稿.md`。

## 怎麼看、怎麼用

| 要做什麼 | 怎麼做 |
|---|---|
| 瀏覽器預覽全部 | 開 `index.html`：← → 換鏡、空白鍵重播、A 自動連播 |
| 單看一鏡 | 開 `scenes/NN-*.html`（自動播一次停在最後一格） |
| 剪輯素材 | `video/NN-*.mp4`（1920×1080、30fps、H.264，每鏡最後約 1.5 秒靜止方便接旁白） |

## 改內容之後重新產生

```bash
python tools/gen_data.py        # 規劃路徑、示意線、建圖快照 → assets/scenes.js、assets/mapflip/
python tools/build_scenes.py    # 13 鏡的版面、文字、時間軸都在這支 → scenes/*.html、index.html
node tools/frames.mjs scenes/05-tilted.html 4 10   # 截關鍵格檢查 → frames/
node tools/render.mjs scenes/05-tilted.html        # 輸出 MP4 → video/
```

- 第一次輸出影片前要在 `tools/` 跑 `npm install`（只裝 `ffmpeg-static`）；截圖與輸出借用 `.claude/skills/huashu-design` 已安裝的 playwright，瀏覽器用本機 Edge。
- 輸出是逐格 seek 截圖（不是即時錄螢幕），不會掉格，每次輸出結果一樣。

## 素材是真是假

- 所有黃色掃描路徑、PCA 主軸、cell 分解都是 `turtlebot3_ccpp/scripts/coverage_planner.plan()` 的真實輸出（離線、合成場地）。
- 標「示意」的是對照用：沿地圖座標軸的掃描線（05）、舊版穿過障礙的掃描線（08）、雜點膨脹（09）。
- 04 的地圖是 2026-06-27 實測 gmapping 快照；右側數字是 2026-11-11 實測，畫面上已分別註明。
- 實機畫面（04 疊加、11 擺正／斜放）是「REC 待拍」區，拍完在剪輯時疊上。
- 12 的【待填】是實驗做完才填的格子，不放假設值；數字確定後改 `tools/build_scenes.py` 的 `data` 再重跑。

## 檔案

| 路徑 | 內容 |
|---|---|
| `scenes/engine.js` | 時間軸引擎（`Scene({duration, tracks, onTime})`、`__seek(t)`） |
| `scenes/map.js`、`map.css` | 把規劃資料畫成 SVG（可描線） |
| `tools/gen_neon2.py` | 顆粒背景 `assets/neo3_grain.png` |
| `spec.md`、`directions.md`、`direction-approved.md`、`polish-log.md` | 設計過程：spec、三個初稿方向、使用者每次調整的原話、每輪修圖 |
| `design-demos/` | 歷次版本（三方向初稿、普普風 v1、霓虹 v2） |
| `slides/` | 定稿前的兩頁靜態 showcase（P1、P7） |
