# 成果動畫簡報

網頁動畫簡報，13 頁、一頁一件事，**按一下播一段**。內容、旁白、數據出處以 `../簡報生成.md` 為準；分鏡見 `導演稿.md`。

## 怎麼播

雙擊開 `index.html`（Edge／Chrome），按 F 全螢幕。

| 操作 | 按鍵 |
|---|---|
| 下一段（最後一段再按＝下一頁） | → 、空白、Enter、PageDown、滑鼠左鍵（簡報筆的「下一頁」也可以） |
| 上一段（第一段再按＝回上一頁，顯示播完的樣子） | ← 、PageUp、Backspace、滑鼠右鍵 |
| 播放中想直接看完這段 | 再按一次下一段 |
| 重播本頁／全螢幕 | R／F |

- 進頁會自動播第一段；每頁分幾段寫在 `tools/build_scenes.py` 每個 `Scene({ steps: [...] })`。
- 關掉再開會停在上次那一頁。

## 改內容之後重新產生

```bash
python tools/gen_data.py        # 規劃路徑、示意線、建圖快照 → assets/scenes.js、assets/mapflip/
python tools/build_scenes.py    # 13 鏡的版面、文字、時間軸都在這支 → scenes/*.html、index.html
node tools/frames.mjs scenes/05-tilted.html steps  # 截每一段停住的畫面檢查 → frames/
node tools/test_play.mjs                           # 模擬按鍵測播放流程
```

- 截圖與測試借用 `.claude/skills/huashu-design` 已安裝的 playwright，瀏覽器用本機 Edge。
- 需要單頁影片檔時：在 `tools/` 跑一次 `npm install`（裝 `ffmpeg-static`），再 `node tools/render.mjs scenes/NN-*.html` → `video/`（整頁動畫一次播完）。

## 素材是真是假

- 所有黃色掃描路徑、PCA 主軸、cell 分解都是 `turtlebot3_ccpp/scripts/coverage_planner.plan()` 的真實輸出（離線、合成場地）。
- 標「示意」的是對照用：沿地圖座標軸的掃描線（05）、舊版穿過障礙的掃描線（08）、雜點膨脹（09）。
- 04 的地圖是 2026-06-27 實測 gmapping 快照；右側數字是 2026-11-11 實測，畫面上已分別註明。
- 實機畫面（11 擺正／斜放）是「REC 待拍」區；拍完可把影片放進 `assets/` 後在 `build_scenes.py` 的 11 頁換成 `<video>`。
- 12 的【待填】是實驗做完才填的格子，不放假設值；數字確定後改 `tools/build_scenes.py` 的 `data` 再重跑。

## 檔案

| 路徑 | 內容 |
|---|---|
| `scenes/engine.js` | 時間軸引擎＋分段播放（`Scene({duration, steps, tracks, onTime})`、`__seek(t)`） |
| `scenes/map.js`、`map.css` | 把規劃資料畫成 SVG（可描線） |
| `tools/gen_neon2.py` | 顆粒背景 `assets/neo3_grain.png` |
| `spec.md`、`directions.md`、`direction-approved.md`、`polish-log.md` | 設計過程：spec、三個初稿方向、使用者每次調整的原話、每輪修圖 |
| `design-demos/` | 歷次版本（三方向初稿、普普風 v1、霓虹 v2） |
| `slides/` | 定稿前的兩頁靜態 showcase（P1、P7） |
