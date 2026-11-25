// 用本機 Edge 把每頁 HTML 截成 1920×1080 PNG（借 huashu-design skill 裝好的 playwright，不另外下載瀏覽器）
// 用法：node tools/shot.mjs <html…>   → 同名 .png 放在 HTML 旁
import { createRequire } from 'module';
import path from 'path';
import { pathToFileURL } from 'url';

const require = createRequire(import.meta.url);
const SKILL = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')),
  '../../../../.claude/skills/huashu-design/node_modules/playwright');
const { chromium } = require(SKILL);

const browser = await chromium.launch({ channel: 'msedge' });
// 960pt = 1280 CSS px；deviceScaleFactor 1.5 → 1920×1080
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 });
for (const f of process.argv.slice(2)) {
  await page.goto(pathToFileURL(path.resolve(f)).href);
  await page.evaluate(() => document.fonts.ready);
  const out = f.replace(/\.html$/, '.png');
  await page.screenshot({ path: out });
  console.log('shot', out);
}
await browser.close();
