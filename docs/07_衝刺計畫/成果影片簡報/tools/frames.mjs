// 截關鍵格檢查：node tools/frames.mjs <scene.html> [t1 t2 …]   （預設截 40% 與最後一格）
// 第二個參數給 steps＝截每一段停住的畫面。輸出 frames/<scene>@<t>.png；用時間軸 __seek，畫面完全由 t 決定
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(decodeURIComponent(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, '$1')), '..');
const { chromium } = require(path.join(ROOT, '../../../.claude/skills/huashu-design/node_modules/playwright'));

const [file, ...ts] = process.argv.slice(2);
const browser = await chromium.launch({ channel: 'msedge' });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.addInitScript(() => { window.__seekRender = true; });
await page.goto(pathToFileURL(path.resolve(file)).href);
await page.waitForFunction(() => window.__ready === true, null, { timeout: 15000 });
const D = await page.evaluate(() => window.__duration);
const steps = await page.evaluate(() => window.__steps);
const times = ts[0] === 'steps' ? steps : ts.length ? ts.map(Number) : [+(D * 0.4).toFixed(2), D];
fs.mkdirSync(path.join(ROOT, 'frames'), { recursive: true });
const name = path.basename(file, '.html');
for (const t of times) {
  await page.evaluate(t => window.__seek(t), t);
  await page.waitForTimeout(120);
  const out = path.join(ROOT, 'frames', `${name}@${t}.png`);
  await page.screenshot({ path: out });
  console.log(out);
}
await browser.close();
