/* 成果影片動畫簡報：共用時間軸引擎
 *
 * 每鏡一個 HTML，呼叫 Scene({ duration, steps, tracks, onTime })。
 * - 簡報模式（瀏覽器開啟）：按一下播一段，見下方「簡報模式」說明
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
        const clock = window.__seekRender ? t : (window.__wall || 0);
        const w = 0.55 + 0.45 * Math.cos(clock * Math.PI * 1.6);
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
      if (cfg.onTime) cfg.onTime(t, { E, clamp, wall: window.__seekRender ? t : (window.__wall || 0) });
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

    /* ── 簡報模式：按一下播一段 ─────────────────────────────
     * cfg.steps＝每段播完要停的時間點（遞增，最後一個通常是 D）。進頁自動播第一段。
     * 下一段：→ 空白 Enter PageDown 或滑鼠左鍵；播放中再按＝直接跳到這段結尾。
     * 上一段：← PageUp Backspace（直接顯示上一段停住的畫面）；R 重播本鏡；F 全螢幕。
     * 已在最後一段再按下一段＝換下一鏡；在第一段按上一段＝回上一鏡（顯示它播完的樣子）。 */
    const steps = (cfg.steps && cfg.steps.length ? cfg.steps : [D]).map(v => Math.min(v, D));
    window.__steps = steps;
    let t = 0, k = 0, playing = false, last = null;
    const here = location.pathname.split('/').pop().replace('.html', '');
    const embedded = window.top !== window;
    const startAtEnd = location.hash === '#end';

    function frame(now) {
      if (window.__seekRender) return;
      if (playing) {
        if (last != null) t += (now - last) / 1000;
        if (t >= steps[k]) { t = steps[k]; playing = false; }
      }
      last = now;
      window.__wall = now / 1000;          // 給持續性的環境動畫（掃描線、呼吸閃爍）用
      render(t);
      requestAnimationFrame(frame);
    }
    function play(to) { k = to; playing = true; last = null; }
    function goScene(dir) {
      if (embedded) { window.parent.postMessage({ cmd: dir > 0 ? 'next' : 'prev' }, '*'); return; }
      const i = ORDER.indexOf(here), j = i + dir;
      if (j >= 0 && j < ORDER.length) location.href = ORDER[j] + '.html' + (dir < 0 ? '#end' : '');
    }
    function next() {
      if (playing) { t = steps[k]; playing = false; return; }
      if (k < steps.length - 1) play(k + 1); else goScene(1);
    }
    function prev() {
      playing = false;
      if (k > 0) { k -= 1; t = steps[k]; } else goScene(-1);
    }
    function replay() { t = 0; play(0); }
    function act(key) {
      if (['ArrowRight', ' ', 'Enter', 'PageDown', 'ArrowDown'].includes(key)) next();
      else if (['ArrowLeft', 'PageUp', 'Backspace', 'ArrowUp'].includes(key)) prev();
      else if (key === 'r' || key === 'R') replay();
      else if (key === 'f' || key === 'F') {
        if (embedded) window.parent.postMessage({ cmd: 'fs' }, '*');
        else if (!document.fullscreenElement) document.documentElement.requestFullscreen(); else document.exitFullscreen();
      }
    }
    window.__step = act;
    window.__state = () => ({ k, t: +t.toFixed(2), playing });

    render(0);
    document.fonts.ready.then(() => {
      window.__ready = true;
      if (window.__seekRender) return;
      if (startAtEnd) { k = steps.length - 1; t = steps[k]; } else play(0);
      requestAnimationFrame(frame);
    });
    addEventListener('keydown', e => {
      if (e.repeat) return;
      if ([' ', 'PageDown', 'PageUp', 'Backspace', 'ArrowDown', 'ArrowUp'].includes(e.key)) e.preventDefault();
      act(e.key);
    });
    addEventListener('mousedown', e => { if (e.button === 0) next(); });
    addEventListener('contextmenu', e => { e.preventDefault(); prev(); });
    addEventListener('message', e => { if (e.data && e.data.key) act(e.data.key); });
  };
})();
