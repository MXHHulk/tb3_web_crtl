// 每鏡輸出成 MP4（1920×1080、30fps、H.264）：逐格 __seek(t) 截圖 → ffmpeg
// 用法：node tools/render.mjs scenes/01-cover.html [scenes/02-….html …]   → video/<scene>.mp4
// 畫面完全由時間軸決定（不是即時錄螢幕），所以不會掉格、每次輸出都一樣。
import { createRequire } from 'module';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';

const require = createRequire(import.meta.url);
const HERE = path.dirname(decodeURIComponent(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, '$1'));
const ROOT = path.resolve(HERE, '..');
const { chromium } = require(path.resolve(ROOT, '../../../.claude/skills/huashu-design/node_modules/playwright'));
const FFMPEG = require(path.join(HERE, 'node_modules/ffmpeg-static'));
const FPS = 30;

fs.mkdirSync(path.join(ROOT, 'video'), { recursive: true });
const browser = await chromium.launch({ channel: 'msedge' });
for (const file of process.argv.slice(2)) {
  const name = path.basename(file, '.html');
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.addInitScript(() => { window.__seekRender = true; });
  await page.goto(pathToFileURL(path.resolve(file)).href);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 20000 });
  await page.waitForTimeout(500);                       // 圖片（建圖快照）載完
  const D = await page.evaluate(() => window.__duration);
  const out = path.join(ROOT, 'video', name + '.mp4');
  const ff = spawn(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const N = Math.round(D * FPS);
  const t0 = Date.now();
  for (let i = 0; i <= N; i++) {
    await page.evaluate(t => window.__seek(t), i / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  console.log(`${name}.mp4  ${D}s  ${N + 1} 格  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  await page.close();
}
await browser.close();
