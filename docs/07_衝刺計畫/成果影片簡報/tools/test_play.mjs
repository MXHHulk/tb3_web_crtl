// 測試簡報播放：開 index.html，模擬按鍵，記錄每次按完在哪一鏡、第幾段，必要時截圖。
// node tools/test_play.mjs
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path'; import { pathToFileURL } from 'url';
const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(decodeURIComponent(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, '$1')), '..');
const { chromium } = require(path.join(ROOT, '../../../.claude/skills/huashu-design/node_modules/playwright'));

const b = await chromium.launch({ channel: 'msedge' });
const p = await b.newPage({ viewport: { width: 1600, height: 900 } });
const errs = []; p.on('pageerror', e => errs.push(e.message));
await p.goto(pathToFileURL(path.join(ROOT, 'index.html')).href);
await p.evaluate(() => localStorage.setItem('ccpp-scene', '0'));
await p.reload();
await p.waitForTimeout(1500);
fs.mkdirSync(path.join(ROOT, 'frames/play'), { recursive: true });
const where = async () => {
  const fr = p.frames().find(f => f.url().includes('/scenes/'));
  const name = fr.url().split('/').pop();
  const st = await fr.evaluate(() => JSON.stringify(window.__state()));
  return name + ' ' + st;
};
const log = [];
// 第 1 鏡等它播完，再一路按 → 走到第 3 鏡
await p.waitForTimeout(10500); log.push('start: ' + await where());
const press = async (k, wait, shot) => {
  await p.keyboard.press(k); await p.waitForTimeout(wait);
  const w = await where(); log.push(`${k} → ${w}`);
  if (shot) await p.screenshot({ path: path.join(ROOT, 'frames/play', shot + '.png') });
};
await press('ArrowRight', 1600, 'a-02-step1');     // 換到 02，自動播第一段（標題）
await press('ArrowRight', 2200, 'b-02-step2');     // 硬體層
await press('ArrowRight', 300);                    // 播放中再按：直接跳到段尾
await press('ArrowRight', 5000, 'c-02-step4');     // 自寫層（最後一段）
await press('ArrowRight', 2000, 'd-03-step1');     // 換到 03
await press('ArrowLeft', 1500, 'e-back-02-end');   // 回 02：應顯示播完的樣子
await p.mouse.click(800, 450); await p.waitForTimeout(2000); log.push('click → ' + await where());
console.log(log.join('\n')); console.log('errors:', errs);
await b.close();
