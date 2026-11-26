/* 用 SVG 畫 SCENES 裡的地圖與路徑（世界座標＝公尺，y 往上）。
 * 所有路徑元素都帶 pathLength="1"，engine.js 的 'draw' 才能做描線動畫。 */
window.MapSVG = (function () {
  const f = v => +v.toFixed(3);
  function open(b, pad = 0.15, extra = '') {
    const [x0, y0, x1, y1] = b;
    const vb = [x0 - pad, -(y1 + pad), x1 - x0 + 2 * pad, y1 - y0 + 2 * pad].map(f).join(' ');
    return `<svg viewBox="${vb}" ${extra}><defs>
      <filter id="glow" filterUnits="userSpaceOnUse" x="-50" y="-50" width="100" height="100"><feGaussianBlur stdDeviation="0.014" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs><g transform="scale(1,-1)">`;
  }
  const close = () => '</g></svg>';
  function cells(list, res, cls, inset = 0.006) {
    return list.map(([x, y]) => `<rect class="${cls}" x="${f(x + inset)}" y="${f(y + inset)}" width="${f(res - 2 * inset)}" height="${f(res - 2 * inset)}"/>`).join('');
  }
  function poly(pts, cls, extra = '') {
    if (!pts.length) return '';
    const d = pts.map((p, i) => (i ? 'L' : 'M') + f(p[0]) + ' ' + f(p[1])).join('');
    return `<path class="${cls}" pathLength="1" d="${d}" ${extra}/>`;
  }
  /* 規劃路徑拆三條：掃描與換行（實線，跨區移動處斷開）、跨區移動（虛線）、外圈 */
  function route(plan, prefix = 'rt') {
    const w = plan.waypoints;
    let lastMove = -1;
    if (plan.perimeter.length) for (let i = 0; i < w.length; i++) if (w[i][2] === 'move') lastMove = i;
    const end = lastMove > 0 ? lastMove : w.length;
    let d = '', moves = '';
    for (let i = 0; i < end; i++) {
      const [x, y, k] = w[i];
      if (i === 0 || k === 'move') {
        d += `M${f(x)} ${f(y)}`;
        if (i > 0) moves += `M${f(w[i - 1][0])} ${f(w[i - 1][1])}L${f(x)} ${f(y)}`;
      } else d += `L${f(x)} ${f(y)}`;
    }
    const ring = plan.perimeter.length ? plan.perimeter.concat([plan.perimeter[0]]) : [];
    return `<path class="${prefix}-sweep" pathLength="1" d="${d}"/>` +
      (moves ? `<path class="${prefix}-move" d="${moves}"/>` : '') +
      poly(ring, prefix + '-ring');
  }
  return { open, close, cells, poly, route };
})();
