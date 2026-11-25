/* 成果影片動畫簡報：共用時間軸引擎
 *
 * 每鏡一個 HTML，呼叫 Scene({ duration, tracks, onTime })。
 * - 瀏覽器開啟：自動播放一次，停在最後一格；空白鍵重播，← → 換鏡（照 index.html 的順序）
 * - 匯出影片：tools/render.mjs 會設 window.__seekRender = true，再逐格呼叫 window.__seek(t) 截圖，
 *   所以畫面完全由 t 決定（不靠 CSS animation），同一個 t 永遠是同一張畫面。
 *
 * tracks 每筆：{ sel, at, dur, fx, ...參數 }
 *   fx: 'up'    由下往上推進＋淡入（dy 預設 24px）
 *       'fade'  淡入
 *       'out'   淡出
 *       'draw'  SVG 描線（元素要有 pathLength="1"）；可給 from/to 只畫一段
 *       'count' 數字計數：from, to, dec（小數位）, pre, suf
 *       'grow'  由左長出（scaleX）
 *       'pop'   放大彈入
 *       'pulse' 從 at 起持續呼吸閃爍
 *   stagger: sel 對到多個元素時，每個延後幾秒
 */
(function () {
  const ORDER = ['01-cover', '02-layers', '03-flow', '04-mapping', '05-tilted', '06-pca', '07-cells',
    '08-problem1', '09-problem2', '10-problem3', '11-demo', '12-table', '13-end'];

  const E = {
    out3: p => 1 - Math.pow(1 - p, 3),
    inout: p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    back: p => { const c = 1.70158, c3 = c + 1; return 1 + c3 * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); },
    lin: p => p,
  };
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));

  function apply(el, tr, t, k) {
    const at = tr.at + (tr.stagger || 0) * k;
    const raw = clamp((t - at) / (tr.dur || 0.4));
    const p = (E[tr.ease] || (tr.fx === 'draw' ? E.inout : E.out3))(raw);
    switch (tr.fx) {
      case 'up': {
        const dy = tr.dy == null ? 24 : tr.dy;
        el.style.opacity = p; el.style.transform = `translateY(${(1 - p) * dy}px)`; break;
      }
      case 'fade': el.style.opacity = p * (tr.max == null ? 1 : tr.max); break;
      case 'out': el.style.opacity = 1 - p; break;
      case 'draw': {
        const a = tr.from || 0, b = tr.to == null ? 1 : tr.to;
        const len = a + (b - a) * p;
        el.style.strokeDasharray = '1 1';
        el.style.strokeDashoffset = 1 - len;
        el.style.opacity = t < at ? 0 : 1;
        break;
      }
      case 'count': {
        const v = tr.from + (tr.to - tr.from) * p;
        el.textContent = (tr.pre || '') + v.toFixed(tr.dec || 0) + (tr.suf || '');
        el.style.opacity = t < at ? 0 : 1;
        break;
      }
      case 'grow':
        el.style.transformOrigin = tr.origin || 'left center';
        el.style.transform = `scaleX(${p})`; el.style.opacity = p > 0 ? 1 : 0; break;
      case 'pop': {
        const q = E.back(raw);
        el.style.opacity = clamp(raw * 3); el.style.transform = `scale(${0.6 + 0.4 * q})`; break;
      }
      case 'pulse': {
        if (t < at) { el.style.opacity = 0; break; }
        const w = 0.55 + 0.45 * Math.cos((t - at) * Math.PI * 1.6);
        el.style.opacity = clamp((t - at) / 0.3) * w; break;
      }
    }
  }

  window.Scene = function (cfg) {
    const D = cfg.duration;
    const tracks = cfg.tracks.map(tr => ({ ...tr, els: [...document.querySelectorAll(tr.sel)] }));
    // 起始狀態：所有有動畫的元素先藏起來（避免第一格閃現）
    // 同一元素有多段動畫時：還沒開始的後段不覆蓋已生效的前段（第一段負責初始狀態）
    function render(t) {
      const touched = new Set();
      for (const tr of tracks) tr.els.forEach((el, k) => {
        const at = tr.at + (tr.stagger || 0) * k;
        if (t < at && touched.has(el)) return;
        apply(el, tr, t, k); touched.add(el);
      });
      if (cfg.onTime) cfg.onTime(t, { E, clamp });
    }
    window.__duration = D;
    window.__seek = t => render(clamp(t, 0, D));

    // 舞台等比縮放填滿視窗（匯出時視窗就是 1920×1080，比例 1）
    const stage = document.querySelector('.stage');
    const fit = () => {
      const s = Math.min(innerWidth / 1920, innerHeight / 1080);
      stage.style.transform = `translate(${(innerWidth - 1920 * s) / 2}px, ${(innerHeight - 1080 * s) / 2}px) scale(${s})`;
    };
    addEventListener('resize', fit); fit();

    let t0 = null;
    function loop(now) {
      if (window.__seekRender) return;
      if (t0 == null) t0 = now;
      const t = (now - t0) / 1000;
      render(t);
      if (t < D) requestAnimationFrame(loop);
    }
    render(0);
    document.fonts.ready.then(() => {
      window.__ready = true;
      if (!window.__seekRender) requestAnimationFrame(loop);
    });

    addEventListener('keydown', e => {
      if (window.top !== window) {            // 在 index.html 裡：換鏡交給外層播放器
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {
          window.parent.postMessage({ key: e.key }, '*'); return;
        }
      }
      const here = location.pathname.split('/').pop().replace('.html', '');
      const i = ORDER.indexOf(here);
      if (e.key === ' ') { t0 = null; requestAnimationFrame(loop); e.preventDefault(); }
      if (e.key === 'ArrowRight' && i < ORDER.length - 1) location.href = ORDER[i + 1] + '.html';
      if (e.key === 'ArrowLeft' && i > 0) location.href = ORDER[i - 1] + '.html';
    });
  };
})();
