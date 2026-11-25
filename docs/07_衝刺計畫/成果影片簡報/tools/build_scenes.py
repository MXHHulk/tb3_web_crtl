#!/usr/bin/env python3
"""
產生 scenes/NN-*.html（13 鏡）與 index.html。每鏡的版面、文字、時間軸都在這支檔案裡，改這裡再重跑。
數據與出處以 ../簡報生成.md 為準；【待填】不得填假設值。

用法：python tools/build_scenes.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(HERE, '..', 'scenes')

HEAD = '''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<link rel="stylesheet" href="base.css">
<link rel="stylesheet" href="map.css">
<style>{css}</style>
<script src="../assets/scenes.js"></script>
<script src="map.js"></script>
<script src="engine.js"></script>
</head>
<body>
<div class="stage">
{body}
</div>
<script>
{js}
</script>
</body>
</html>
'''

SCENES = []


def scene(name, title, body, js, css=''):
    SCENES.append((name, title))
    with open(os.path.join(SC, name + '.html'), 'w', encoding='utf-8') as f:
        f.write(HEAD.format(title=title, body=body.strip('\n'), js=js.strip('\n'), css=css))


# ═══ 01 開場 ═══════════════════════════════════════════
scene('01-cover', '01 開場', '''
<svg id="map" class="abs" style="left:700px; top:-250px; width:1560px; height:1560px;"></svg>
<div class="abs" style="left:0; top:0; width:1200px; height:1080px; background:linear-gradient(90deg, rgba(8,22,27,.94) 45%, rgba(8,22,27,0));"></div>
<p class="vtext" style="top:300px;">BOUSTROPHEDON COVERAGE / TURTLEBOT3</p>
<h1 class="abs k" id="t" style="left:92px; top:268px; font-size:160px; line-height:1.15;">牛耕式演算法</h1>
<div class="tag" id="tag" style="left:92px; top:556px;"><p>以 TurtleBot3 實作</p></div>
<div class="abs" style="left:96px; top:686px;">
  <p class="lede l">車子不必擺正。</p>
  <p class="lede l">自動建圖之後，走遍每一寸地面。</p>
</div>
<p class="abs mute" id="names" style="left:96px; top:930px; font-size:26px;">指導老師 卓世明　｜　陳紹桓、陳柏屹</p>
<p class="abs mute" id="legend" style="left:96px; top:978px; font-size:22px;">背景路徑為規劃程式真實輸出（3.0×2.6 m 合成場地斜放 30°）：<span class="acid">黃 掃描</span>・<span class="cyan">青 外圈</span>・<span class="pink">粉 障礙物</span></p>
''', '''
const d = SCENES.cover, M = MapSVG;
document.getElementById('map').outerHTML = M.open(d.bounds, 0.1, 'id="map" class="abs" style="left:700px; top:-250px; width:1560px; height:1560px;"')
  + M.cells(d.wall, d.res, 'wall') + `<g class="obsg">${M.cells(d.obs, d.res, 'obs')}</g>` + M.route(d.plan) + M.close();
Scene({ duration: 10, tracks: [
  { sel: '.wall', at: 0, dur: 1.0, fx: 'fade', max: 1 },
  { sel: '.obsg', at: 0.6, dur: 0.4, fx: 'fade' },
  { sel: '.rt-sweep', at: 0.8, dur: 5.4, fx: 'draw', ease: 'lin' },
  { sel: '.rt-move', at: 5.6, dur: 0.6, fx: 'fade' },
  { sel: '.rt-ring', at: 6.0, dur: 1.4, fx: 'draw' },
  { sel: '#t', at: 1.0, dur: 0.6, fx: 'up', dy: 40 },
  { sel: '#tag', at: 1.7, dur: 0.45, fx: 'grow' },
  { sel: '.l', at: 2.3, dur: 0.5, fx: 'up', stagger: 0.35 },
  { sel: '#names', at: 3.2, dur: 0.6, fx: 'fade' },
  { sel: '#legend', at: 6.6, dur: 0.6, fx: 'fade' },
]});
''')

# ═══ 02 系統三層 ═══════════════════════════════════════
layers = [
    # (y, 標籤, 標籤 class, [(主字, 小字, 行數 or None)], 字色)
    (280, '我們寫的', 'acid', [('覆蓋規劃', 'coverage_planner.py', 488), ('執行與循跡', 'map_server.py', 1783),
                             ('手機控制台', 'launcher.py', 493), ('網頁監控', 'web/index.html', 704)], '#F2F7F5'),
    (600, 'ROS 現成套件', 'mute', [('gmapping', '建圖（SLAM）', None), ('explore_lite', '找還沒看過的邊界', None),
                                  ('move_base', '全域路徑（備援）', None)], '#8FB3B8'),
    (830, '硬體', 'mute', [('TurtleBot3', 'Burger 差速輪式機器人', None), ('LDS 光達', '360° 雷射測距', None)], '#8FB3B8'),
]
body = '''<p class="abs kicker" id="kick" style="left:96px; top:64px;">系統架構</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">系統分三層，最上層是我們自己寫的</h1>
'''
for li, (y, lab, cls, items, col) in enumerate(layers):
    body += f'<div class="abs rule L{li}" style="left:0; top:{y - 26}px; width:1920px; height:2px; background:{"#DAFF3C" if li == 0 else "#2a4a50"};"></div>\n'
    body += f'<p class="abs lab L{li}t {cls}" style="left:96px; top:{y}px; font-size:34px; font-weight:700;">{lab}</p>\n'
    for k, (main, sub, n) in enumerate(items):
        x = 400 + k * 380
        body += f'<div class="abs it L{li}i" style="left:{x}px; top:{y - 8}px; width:350px;">'
        body += f'<p style="font-size:{52 if li == 0 else 44}px; font-weight:{900 if li == 0 else 700}; color:{col}; line-height:1.15;">{main}</p>'
        body += f'<p class="mute" style="font-size:26px; margin-top:6px;">{sub}</p>'
        if n:
            body += f'<p class="num acid" style="font-size:64px; line-height:1.1; margin-top:8px;"><span class="cnt" data-n="{n}">{n}</span> <span style="font-size:28px;">行</span></p>'
        body += '</div>\n'
body += '<p class="abs src" id="src" style="left:96px; top:1000px;">行數：wc -l，2026-11-25</p>\n'
scene('02-layers', '02 系統三層', body, '''
const tr = [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' },
  { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  // 由下往上堆：硬體 → 現成 → 自寫
  { sel: '.L2', at: 1.4, dur: 0.6, fx: 'grow' }, { sel: '.L2t', at: 1.6, dur: 0.4, fx: 'up' },
  { sel: '.L2i', at: 1.8, dur: 0.45, fx: 'up', stagger: 0.18 },
  { sel: '.L1', at: 3.2, dur: 0.6, fx: 'grow' }, { sel: '.L1t', at: 3.4, dur: 0.4, fx: 'up' },
  { sel: '.L1i', at: 3.6, dur: 0.45, fx: 'up', stagger: 0.18 },
  { sel: '.L0', at: 5.4, dur: 0.7, fx: 'grow' }, { sel: '.L0t', at: 5.6, dur: 0.4, fx: 'up' },
  { sel: '.L0i', at: 5.8, dur: 0.5, fx: 'up', stagger: 0.25 },
  { sel: '#src', at: 8.0, dur: 0.6, fx: 'fade' },
];
document.querySelectorAll('.cnt').forEach((el, k) => {
  el.id = 'c' + k; tr.push({ sel: '#c' + k, at: 6.0 + k * 0.25, dur: 1.4, fx: 'count', from: 0, to: +el.dataset.n });
});
Scene({ duration: 14, tracks: tr });
''')

# ═══ 03 一鍵流程 ═══════════════════════════════════════
nodes = [('手機一鍵開始', '手機網頁控制台'), ('自動建圖', 'gmapping＋explore_lite'), ('覆蓋規劃', 'PCA＋cell 分解'),
         ('循跡執行', '自寫直線循跡'), ('留下紀錄', '覆蓋率・軌跡・時間')]
body = '''<p class="abs kicker" id="kick" style="left:96px; top:64px;">操作流程</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">按一個鍵，車子自己跑完全程</h1>
<div class="abs" id="track" style="left:260px; top:600px; width:1400px; height:3px; background:#2a4a50;"></div>
<div class="abs" id="lit" style="left:260px; top:599px; width:1400px; height:5px; background:#DAFF3C; box-shadow:0 0 18px #DAFF3C; transform-origin:left center; transform:scaleX(0);"></div>
<div class="abs" id="spark" style="left:150px; top:588px; width:28px; height:28px; margin-left:-14px; border-radius:50%; background:#F2F7F5; box-shadow:0 0 30px 10px #DAFF3C;"></div>
'''
for k, (a, b) in enumerate(nodes):
    x = 260 + k * 350
    body += f'<div class="abs dot" id="d{k}" style="left:{x - 9}px; top:592px; width:18px; height:18px; border-radius:50%; background:#2a4a50;"></div>\n'
    body += f'<p class="abs nd" id="n{k}" style="left:{x - 200}px; top:476px; width:400px; text-align:center; font-size:48px; font-weight:900; font-style:italic; color:#4d6f75;">{a}</p>\n'
    body += f'<p class="abs mute ns" style="left:{x - 200}px; top:650px; width:400px; text-align:center; font-size:26px;">{b}</p>\n'
scene('03-flow', '03 一鍵流程', body, '''
const X0 = 260, X1 = 1660, A = 1.4, B = 7.4;
Scene({ duration: 10, tracks: [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#track', at: 0.8, dur: 0.6, fx: 'grow' },
  { sel: '.ns', at: 1.0, dur: 0.4, fx: 'fade', stagger: 0.1 },
], onTime: (t, u) => {
  const p = u.clamp((t - A) / (B - A));
  const q = u.E.inout(p);
  document.getElementById('lit').style.transform = `scaleX(${q})`;
  const sp = document.getElementById('spark');
  sp.style.left = (X0 + (X1 - X0) * q) + 'px';
  sp.style.opacity = t < A ? 0 : (p >= 1 ? 0.6 : 1);
  for (let k = 0; k < 5; k++) {
    const on = q >= k / 4 - 0.001 && t >= A;
    document.getElementById('n' + k).style.color = on ? (k === 0 || k === 4 ? '#F2F7F5' : '#DAFF3C') : '#4d6f75';
    document.getElementById('d' + k).style.background = on ? '#DAFF3C' : '#2a4a50';
  }
}});
''')

# ═══ 04 自動建圖 ═══════════════════════════════════════
scene('04-mapping', '04 自動建圖', '''
<img id="flip" class="abs" src="../assets/mapflip/00.png" style="left:60px; top:110px; width:960px; height:909px; image-rendering:pixelated;">
<p class="abs src" id="cap" style="left:96px; top:1010px;">畫面：2026-06-27 實測 gmapping 建圖快照 47 張（每格 5 cm）；實機快轉待拍，剪輯時疊於此</p>
<p class="abs kicker" id="kick" style="left:1120px; top:120px;">自動建圖</p>
<h1 class="abs k" id="t" style="left:1120px; top:166px; font-size:68px; line-height:1.25; width:760px;">自己找路建完地圖，<br>再開回起點</h1>
<div class="abs st" style="left:1120px; top:440px;"><p class="num" style="font-size:110px; line-height:1;"><span id="s1">55</span><span style="font-size:44px;"> 秒</span></p><p class="mute" style="font-size:26px;">建完整張地圖</p></div>
<div class="abs st" style="left:1520px; top:440px;"><p class="num" style="font-size:110px; line-height:1;"><span id="s2">4.1</span><span style="font-size:44px;"> m</span></p><p class="mute" style="font-size:26px;">行走距離</p></div>
<div class="abs st" style="left:1120px; top:680px;"><p class="num acid" style="font-size:150px; line-height:1;"><span id="s3">3</span><span style="font-size:56px;"> cm</span></p><p style="font-size:30px; font-weight:700;">回到起點的誤差</p></div>
<p class="abs src st" style="left:1120px; top:920px; width:740px;">scan matching 163 次僅 1 次失敗｜實車 1 次（開發日誌 2026-11-11）</p>
''', '''
const N = 47, imgs = [];
for (let i = 0; i < N; i++) { const im = new Image(); im.src = `../assets/mapflip/${String(i).padStart(2, '0')}.png`; imgs.push(im); }
Scene({ duration: 14, tracks: [
  { sel: '#flip', at: 0.0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.3, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.5, dur: 0.6, fx: 'up' },
  { sel: '.st', at: 3.0, dur: 0.5, fx: 'up', stagger: 1.1 },
  { sel: '#s1', at: 3.0, dur: 1.2, fx: 'count', from: 0, to: 55 },
  { sel: '#s2', at: 4.1, dur: 1.2, fx: 'count', from: 0, to: 4.1, dec: 1 },
  { sel: '#s3', at: 5.2, dur: 1.0, fx: 'count', from: 40, to: 3 },
  { sel: '#cap', at: 1.0, dur: 0.6, fx: 'fade' },
], onTime: (t, u) => {
  const i = Math.round(u.clamp((t - 0.6) / 8.5) * (N - 1));
  const el = document.getElementById('flip');
  const src = imgs[i].src;
  if (el.src !== src) el.src = src;
}});
''')

# ═══ 05 地圖是斜的 ═══════════════════════════════════════
scene('05-tilted', '05 地圖是斜的', '''
<div id="mapbox" class="abs" style="left:840px; top:40px; width:1040px; height:1000px;"></div>
<p class="abs kicker" id="kick" style="left:96px; top:200px;">為什麼要 PCA</p>
<h1 class="abs k" id="t" style="left:96px; top:250px; font-size:76px; line-height:1.25; width:720px;">車子沒擺正，<br>地圖就是斜的</h1>
<p class="abs lede" id="l1" style="left:96px; top:520px; width:700px;">SLAM 地圖的方向，<br>跟著車子開機時的朝向。</p>
<p class="abs lede" id="l2" style="left:96px; top:660px; width:700px;">沿地圖座標軸掃，掃描線會被斜牆切得<span class="pink">又短又碎</span>，轉彎變多。</p>
<p class="abs src" id="cap" style="left:96px; top:960px;">示意：同一張可走格地圖、沿地圖 x 軸切線（未用 PCA）</p>
''', '''
const d = SCENES.tilt, M = MapSVG;
document.getElementById('mapbox').innerHTML = M.open(d.bounds, 0.1, 'id="map" style="left:0; top:0; width:100%; height:100%;"')
  + M.cells(d.wall, d.res, 'wall') + d.axisLines.map(l => M.poly(l, 'axl')).join('') + M.close();
Scene({ duration: 10, tracks: [
  { sel: '.wall', at: 0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#l1', at: 1.3, dur: 0.5, fx: 'up' },
  { sel: '.axl', at: 4.0, dur: 0.5, fx: 'draw', stagger: 0.08 },
  { sel: '#l2', at: 4.6, dur: 0.5, fx: 'up' },
  { sel: '#cap', at: 5.0, dur: 0.6, fx: 'fade' },
], onTime: (t, u) => {
  // 房間先是正的，再轉成斜 30°（模擬車子沒擺正）
  const p = u.E.inout(u.clamp((t - 1.2) / 1.8));
  document.getElementById('map').style.transform = `rotate(${30 * (1 - p)}deg)`;
}});
''', css='.axl { fill:none; stroke:#FF4FD8; stroke-width:.026; stroke-linecap:round; filter:url(#glow); }')

# ═══ 06 PCA ═══════════════════════════════════════════
scene('06-pca', '06 PCA 找主軸', '''
<div id="mapbox" class="abs" style="left:840px; top:40px; width:1040px; height:1000px;"></div>
<p class="abs kicker" id="kick" style="left:96px; top:200px;">PCA 主軸</p>
<h1 class="abs k" id="t" style="left:96px; top:250px; font-size:76px; line-height:1.25; width:720px;">用 PCA 找出<br>房間的長邊</h1>
<p class="abs lede" id="l1" style="left:96px; top:520px; width:700px;">把可走的格子當成一團點，變化最大的方向就是房間長邊。</p>
<p class="abs lede" id="l2" style="left:96px; top:700px; width:700px;">掃描線沿著它走，<span class="acid">永遠平行牆面</span>。</p>
<p class="abs src" id="cap" style="left:96px; top:960px;">規劃程式真實輸出（coverage_planner.plan()）</p>
''', '''
const d = SCENES.tilt, M = MapSVG, ax = d.plan.axes, L = 1.7, Lb = 0.9;
const c = ax.c, a = ax.a, b = ax.b;
const arrow = (v, len, cls) => M.poly([[c[0] - v[0] * len, c[1] - v[1] * len], [c[0] + v[0] * len, c[1] + v[1] * len]], cls);
document.getElementById('mapbox').innerHTML = M.open(d.bounds, 0.1, 'style="left:0; top:0; width:100%; height:100%;"')
  + M.cells(d.wall, d.res, 'wall')
  + `<g id="pts">${d.points.map(p => `<circle cx="${p[0]}" cy="${p[1]}" r="0.011" class="pt"/>`).join('')}</g>`
  + arrow(a, L, 'axA') + arrow(b, Lb, 'axB') + M.route(d.plan) + M.close();
Scene({ duration: 12, tracks: [
  { sel: '.wall', at: 0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#pts', at: 1.0, dur: 1.0, fx: 'fade' },
  { sel: '#l1', at: 1.4, dur: 0.5, fx: 'up' },
  { sel: '.axA', at: 2.6, dur: 1.0, fx: 'draw' },
  { sel: '.axB', at: 3.2, dur: 0.8, fx: 'draw' },
  { sel: '#pts', at: 4.6, dur: 0.8, fx: 'out' },
  { sel: '.rt-sweep', at: 4.8, dur: 4.2, fx: 'draw', ease: 'lin' },
  { sel: '.rt-ring', at: 9.0, dur: 0.9, fx: 'draw' },
  { sel: '#l2', at: 5.4, dur: 0.5, fx: 'up' },
  { sel: '#cap', at: 5.8, dur: 0.6, fx: 'fade' },
]});
''', css='''.pt { fill:#39E6FF; opacity:.75; }
.axA { fill:none; stroke:#F2F7F5; stroke-width:.03; stroke-dasharray:.08 .05; }
.axB { fill:none; stroke:#39E6FF; stroke-width:.022; }''')

# ═══ 07 cell 分解 ═══════════════════════════════════════
scene('07-cells', '07 cell 分解', '''
<p class="abs kicker" id="kick" style="left:96px; top:64px;">cell 分解</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">有障礙物，就把空間切成幾塊各自掃</h1>
<p class="abs lede" id="l1" style="left:96px; top:230px; width:1700px; font-size:34px;">障礙物前後，同一條掃描線會從一段變成兩段，那裡就是切點。每個 cell 內部來回掃，再由近到遠串起來。</p>
<div id="mapbox" class="abs" style="left:160px; top:340px; width:1600px; height:700px;"></div>
<p class="abs src" id="cap" style="left:96px; top:1010px;">規劃程式真實輸出・2.0 × 1.0 m 場地＋中央障礙（離線）</p>
''', '''
const d = SCENES.field, M = MapSVG, cols = ['#DAFF3C', '#39E6FF', '#C9B6FF', '#F2F7F5'];
let g = M.open(d.bounds, 0.08, 'style="left:0; top:0; width:100%; height:100%;"') + M.cells(d.wall, d.res, 'wall')
  + `<g class="obsg">${M.cells(d.obs, d.res, 'obs')}</g>`;
const cells = d.plan.cells;
cells.forEach((cl, i) => {
  g += M.poly(cl, `cp cp${i}`, `style="stroke:${cols[i % 4]}"`);
  if (i > 0) { const p = cells[i - 1][cells[i - 1].length - 1], q = cl[0]; g += `<path class="mv mv${i}" d="M${p[0]} ${p[1]}L${q[0]} ${q[1]}"/>`; }
  const s = cl[0];
  g += `<g transform="translate(${s[0]} ${s[1] + 0.05}) scale(1,-1)"><text class="cl cl${i}" x="0" y="0" style="fill:${cols[i % 4]}">cell ${i + 1}</text></g>`;
});
document.getElementById('mapbox').innerHTML = g + M.close();
const tr = [
  { sel: '.wall', at: 0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.obsg', at: 1.2, dur: 0.4, fx: 'pop' },
  { sel: '#l1', at: 1.6, dur: 0.5, fx: 'up' },
  { sel: '#cap', at: 2.0, dur: 0.6, fx: 'fade' },
];
const per = 7.5 / cells.length;
cells.forEach((cl, i) => {
  const at = 3.0 + i * per;
  tr.push({ sel: '.cl' + i, at, dur: 0.3, fx: 'up', dy: 10 });
  tr.push({ sel: '.cp' + i, at: at + 0.2, dur: per - 0.4, fx: 'draw', ease: 'lin' });
  if (i > 0) tr.push({ sel: '.mv' + i, at: at - 0.1, dur: 0.3, fx: 'fade' });
});
Scene({ duration: 14, tracks: tr });
''', css='''.cp { fill:none; stroke-width:.026; stroke-linejoin:round; stroke-linecap:round; filter:url(#glow); }
.mv { fill:none; stroke:#F2F7F5; stroke-width:.012; stroke-dasharray:.03 .03; opacity:.8; }
.cl { font-family:Bahnschrift, sans-serif; font-weight:700; font-size:.075px; }''')

# ═══ 08 問題一 ═══════════════════════════════════════════
scene('08-problem1', '08 問題一：穿過障礙', '''
<p class="abs kicker" id="kick" style="left:96px; top:64px;">問題一</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">掃描線直接穿過障礙物</h1>
<div id="mapbox" class="abs" style="left:40px; top:300px; width:1220px; height:640px;"></div>
<p class="abs src" id="cap" style="left:96px; top:1000px;"><span class="pink">粉：舊版做法示意</span>　<span class="acid">黃：cell 分解後的真實規劃輸出</span>（2.0 × 1.0 m 場地，離線）</p>
<div class="abs" id="old" style="left:1340px; top:330px; width:520px;">
  <p class="mute" style="font-size:28px; font-weight:700;">舊版</p>
  <p class="num pink" style="font-size:150px; line-height:1;">0%</p>
  <p style="font-size:28px; line-height:1.5;">有效覆蓋：5 條掃描線全部橫跨障礙，最嚴重一條 75% 落在障礙內</p>
</div>
<div class="abs" id="new" style="left:1340px; top:700px; width:520px;">
  <p class="mute" style="font-size:28px; font-weight:700;">cell 分解後</p>
  <p class="num acid" style="font-size:110px; line-height:1;">穿牆 0 次</p>
  <p class="mute" style="font-size:24px;">離線評估 14 種場地</p>
</div>
<p class="abs src" id="src" style="left:1340px; top:960px; width:540px;">開發日誌 2026-08-16（200 × 100 cm 含障礙場地，實機觀察）</p>
''', '''
const d = SCENES.field, M = MapSVG;
document.getElementById('mapbox').innerHTML = M.open(d.bounds, 0.08, 'style="left:0; top:0; width:100%; height:100%;"')
  + M.cells(d.wall, d.res, 'wall') + `<g class="obsg">${M.cells(d.obs, d.res, 'obs')}</g>`
  + `<g id="oldg">${d.oldLines.map(l => M.poly(l, 'old')).join('')}</g>` + M.route(d.plan) + M.close();
Scene({ duration: 12, tracks: [
  { sel: '.wall', at: 0, dur: 0.5, fx: 'fade' }, { sel: '.obsg', at: 0.3, dur: 0.4, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.old', at: 1.2, dur: 0.9, fx: 'draw', stagger: 0.25 },
  { sel: '#old', at: 2.6, dur: 0.5, fx: 'up' },
  { sel: '#oldg', at: 5.6, dur: 0.6, fx: 'fade', max: 0.25, ease: 'lin' },
  { sel: '.rt-sweep', at: 5.8, dur: 3.6, fx: 'draw', ease: 'lin' },
  { sel: '.rt-move', at: 9.2, dur: 0.4, fx: 'fade' },
  { sel: '.rt-ring', at: 9.4, dur: 0.9, fx: 'draw' },
  { sel: '#new', at: 7.0, dur: 0.5, fx: 'up' },
  { sel: '#cap', at: 1.6, dur: 0.6, fx: 'fade' }, { sel: '#src', at: 3.4, dur: 0.6, fx: 'fade' },
], onTime: (t) => {
  // 舊線先完整亮著，5.6 s 後退成暗影
  const g = document.getElementById('oldg');
  if (t < 5.6) g.style.opacity = 1; else g.style.opacity = Math.max(0.25, 1 - (t - 5.6) / 0.6 * 0.75);
}});
''', css='.old { fill:none; stroke:#FF4FD8; stroke-width:.03; stroke-linecap:round; filter:url(#glow); }')

# ═══ 09 問題二 ═══════════════════════════════════════════
scene('09-problem2', '09 問題二：假障礙', '''
<div id="mapbox" class="abs" style="left:120px; top:80px; width:700px; height:920px;"></div>
<p class="abs src" id="cap" style="left:120px; top:1010px;">示意：1.06 × 1.47 m 房間、5 cm 格</p>
<p class="abs kicker" id="kick" style="left:960px; top:120px;">問題二</p>
<h1 class="abs k" id="t" style="left:960px; top:166px; font-size:72px; line-height:1.25; width:880px;">光達雜點，被當成障礙物</h1>
<p class="abs lede" id="l1" style="left:960px; top:380px; width:880px;">一顆 <span class="num">5 cm</span> 的雜點，加上安全距離，會變成 <span class="num pink">25 cm</span> 的禁區。</p>
<p class="abs lede" id="l2" style="left:960px; top:540px; width:880px;">把 3 格以下的小團塊過濾掉：</p>
<div class="abs" id="area" style="left:960px; top:640px;">
  <p class="num" style="font-size:130px; line-height:1;"><span class="mute" style="font-size:70px;">1.08 → </span><span id="a2" class="acid">1.16</span><span style="font-size:52px;"> m²</span></p>
  <p style="font-size:32px; font-weight:700; margin-top:8px;">可規劃面積 <span class="acid">+7%</span></p>
</div>
<p class="abs src" id="src" style="left:960px; top:960px;">離線比較：11/11 第一次實測地圖（開發日誌 2026-11-11）</p>
''', '''
// 示意房間：1.06 × 1.47 m，散落 4 顆雜點；禁區＝雜點外擴 10 cm（方形膨脹）
const W = 1.06, H = 1.47, R = 0.05, noise = [[0.30, 0.42], [0.72, 0.95], [0.55, 0.22], [0.25, 1.12]];
let g = MapSVG.open([0, 0, W, H], 0.06, 'style="left:0; top:0; width:100%; height:100%;"');
g += `<rect x="0" y="0" width="${W}" height="${H}" class="room"/>`;
noise.forEach(([x, y], i) => {
  g += `<rect class="zone z${i}" x="${x - 0.1}" y="${y - 0.1}" width="${0.25}" height="${0.25}"/>`;
  g += `<rect class="dotn n${i}" x="${x}" y="${y}" width="${R}" height="${R}"/>`;
});
document.getElementById('mapbox').innerHTML = g + MapSVG.close();
Scene({ duration: 12, tracks: [
  { sel: '.room', at: 0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.dotn', at: 1.2, dur: 0.3, fx: 'pop', stagger: 0.15 },
  { sel: '#l1', at: 2.0, dur: 0.5, fx: 'up' },
  { sel: '#l2', at: 5.6, dur: 0.5, fx: 'up' },
  { sel: '#area', at: 6.4, dur: 0.5, fx: 'up' },
  { sel: '#a2', at: 6.6, dur: 1.4, fx: 'count', from: 1.08, to: 1.16, dec: 2 },
  { sel: '#cap', at: 1.0, dur: 0.6, fx: 'fade' }, { sel: '#src', at: 7.4, dur: 0.6, fx: 'fade' },
], onTime: (t, u) => {
  // 2.6–4.2 s 禁區由雜點長大到 25 cm；5.8–6.8 s 過濾掉（禁區與雜點一起消失）
  const grow = u.E.out3(u.clamp((t - 2.6) / 1.6)), gone = u.clamp((t - 5.8) / 1.0);
  document.querySelectorAll('.zone').forEach((z, i) => {
    const [x, y] = noise[i], s = 0.05 + 0.2 * grow, c = 0.025;
    z.setAttribute('x', x + c - s / 2); z.setAttribute('y', y + c - s / 2);
    z.setAttribute('width', s); z.setAttribute('height', s);
    z.style.opacity = t < 2.6 ? 0 : 1 - gone;
  });
  if (t > 5.8) document.querySelectorAll('.dotn').forEach(n => n.style.opacity = 1 - gone);
}});
''', css='''.room { fill:#12333a; stroke:rgba(120,170,178,.8); stroke-width:.02; }
.zone { fill:rgba(255,79,216,.28); stroke:#FF4FD8; stroke-width:.006; }
.dotn { fill:#DAFF3C; }''')

# ═══ 10 問題三 ═══════════════════════════════════════════
rows = [('執行時間', '436 → 322 s'), ('受困次數', '3 → 1'), ('DWA 規劃失敗', '1127 → 209'), ('實走／規劃距離', '1.38 → 1.23')]
body = '''<svg id="corner" class="abs"></svg>
<p class="vtext" style="top:760px;">BEFORE / AFTER</p>
<p class="abs kicker" id="kick" style="left:96px; top:76px;">問題三</p>
<h1 class="abs k" id="t" style="left:96px; top:120px; font-size:68px;">導航套件卡在牆邊，我們改成自己開</h1>
<p class="abs src" id="src" style="left:96px; top:228px;">實車・同一場地 1.06 × 1.47 m・兩種方式各 1 次（開發日誌 2026-11-11）；重複 3 次的平均待補</p>
<p class="abs num" id="ghost" style="left:76px; top:250px; font-size:420px; line-height:1.15; color:transparent; -webkit-text-stroke:3px rgba(143,179,184,.5); font-stretch:condensed;">71%</p>
<p class="abs mute" id="bl" style="left:104px; top:630px; font-size:32px;">改善前　ROS 內建 DWA</p>
<div class="abs" id="after" style="left:760px; top:332px; width:1100px; text-align:right;">
  <p style="font-size:36px; font-weight:700;">改善後　自寫直線循跡</p>
  <p class="num acid" style="font-size:372px; line-height:1; letter-spacing:-6px;"><span id="big">97.7</span>%</p>
  <p class="mute" style="font-size:30px; margin-top:12px;">同一場地的實際覆蓋率（改善前 71%）</p>
</div>
'''
for k, (a, b) in enumerate(rows):
    y = 720 + k * 68
    body += f'<div class="abs row" style="left:104px; top:{y}px; width:620px;"><p class="mute" style="position:absolute; top:10px; font-size:28px;">{a}</p><p class="num" style="position:absolute; left:256px; font-size:44px;">{b}</p></div>\n'
scene('10-problem3', '10 問題三：DWA → 自寫循跡', body, '''
const d = SCENES.cover, M = MapSVG;
document.getElementById('corner').outerHTML = M.open(d.bounds, 0.1, 'id="corner" class="abs" style="left:1300px; top:-1120px; width:1560px; height:1560px; opacity:.55;"')
  + M.cells(d.wall, d.res, 'wall') + M.route(d.plan) + M.close();
Scene({ duration: 14, tracks: [
  { sel: '.rt-sweep', at: 0, dur: 3.0, fx: 'draw', ease: 'lin' }, { sel: '.rt-ring', at: 2.6, dur: 0.6, fx: 'draw' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#src', at: 1.0, dur: 0.6, fx: 'fade' },
  { sel: '#ghost', at: 1.6, dur: 0.8, fx: 'fade' }, { sel: '#bl', at: 1.9, dur: 0.5, fx: 'up' },
  { sel: '#after', at: 3.4, dur: 0.5, fx: 'up' },
  { sel: '#big', at: 3.5, dur: 1.8, fx: 'count', from: 71, to: 97.7, dec: 1 },
  { sel: '.row', at: 6.0, dur: 0.45, fx: 'up', stagger: 0.3 },
]});
''')

# ═══ 11 實機展示 ═══════════════════════════════════════
scene('11-demo', '11 實機展示：擺正 vs 斜放', '''
<div class="ph" id="p0" style="left:0; top:0; width:952px; height:1080px;"><div class="scan" id="s0"></div>
  <p class="rec"><b>REC</b>待拍 S2：車子擺正，完整覆蓋（俯拍＋手機畫面，8 倍快轉）</p></div>
<div class="ph" id="p1" style="left:968px; top:0; width:952px; height:1080px;"><div class="scan" id="s1"></div>
  <p class="rec"><b>REC</b>待拍 S3：車子斜放約 30°，完整覆蓋</p></div>
<p class="abs num" id="a0" style="left:56px; top:150px; font-size:240px; line-height:1; color:rgba(242,247,245,.9);">0°</p>
<p class="abs num acid" id="a1" style="left:1024px; top:150px; font-size:240px; line-height:1;">30°</p>
<div class="abs" id="tbar" style="left:0; top:0; width:1920px; height:130px; background:linear-gradient(180deg, rgba(8,22,27,.95), rgba(8,22,27,0));"></div>
<h1 class="abs k" id="t" style="left:56px; top:36px; font-size:60px;">同一個房間，擺法不同，路徑一樣貼著牆平行掃</h1>
''', '''
Scene({ duration: 22, tracks: [
  { sel: '.ph', at: 0, dur: 0.6, fx: 'fade', stagger: 0.2 },
  { sel: '#t', at: 0.5, dur: 0.6, fx: 'up' },
  { sel: '#a0', at: 1.2, dur: 0.5, fx: 'up' }, { sel: '#a1', at: 1.6, dur: 0.5, fx: 'up' },
  { sel: '.rec', at: 2.2, dur: 0.6, fx: 'fade', stagger: 0.2 },
], onTime: (t) => {
  for (let k = 0; k < 2; k++) document.getElementById('s' + k).style.top = (((t * 140) + k * 400) % 1080) + 'px';
}});
''')

# ═══ 12 數據總表 ═══════════════════════════════════════
cols = [('實驗', 250), ('條件', 470), ('覆蓋率', 190), ('時間', 170), ('受困', 150), ('轉彎數', 170), ('類型', 330)]
data = [('執行方式', 'DWA vs 自寫循跡', '【待填】', '【待填】', '【待填】', '—', '實車，各 ≥3 次平均'),
        ('掃描方向', 'PCA vs 沿地圖軸（斜放 0/15/30/45°）', '—', '—', '—', '【待填】', '離線，修 cell 碎裂後重跑'),
        ('擺放角度', '0° vs 30°', '【待填】', '【待填】', '【待填】', '【待填】', '實車')]
body = '''<p class="abs kicker" id="kick" style="left:96px; top:64px;">數據總表</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">每組實驗重複三次以上</h1>
<div class="abs rule" id="r0" style="left:96px; top:330px; width:1730px; height:3px; background:#DAFF3C;"></div>
'''
x = 96
for name, w in cols:
    body += f'<p class="abs mute th" style="left:{x}px; top:280px; width:{w}px; font-size:26px;">{name}</p>\n'
    x += w
for r, row in enumerate(data):
    y = 370 + r * 150
    x = 96
    for c, ((name, w), val) in enumerate(zip(cols, row)):
        cls = 'pend' if val == '【待填】' else ''
        size = 34 if c < 2 else 32
        weight = 900 if c == 0 else 500
        color = '#8FB3B8' if c == 6 else '#F2F7F5'
        body += f'<p class="abs cell R{r} {cls}" style="left:{x}px; top:{y}px; width:{w - 20}px; font-size:{size if c != 6 else 24}px; font-weight:{weight}; color:{color}; line-height:1.35;">{val}</p>\n'
        x += w
    body += f'<div class="abs rule R{r}r" style="left:96px; top:{y + 118}px; width:1730px; height:1px; background:#2a4a50;"></div>\n'
body += '<p class="abs lede" id="sum" style="left:96px; top:850px; width:1700px; font-size:36px;">自寫循跡讓覆蓋率穩定在 <span class="acid">【待填】</span> 以上，車子斜放時轉彎數也比沿地圖座標軸少 <span class="acid">【待填】</span>。</p>\n'
body += '<p class="abs src" id="src" style="left:96px; top:990px;">【待填】＝實驗完成後才填，不放假設值</p>\n'
scene('12-table', '12 數據總表', body, '''
Scene({ duration: 14, tracks: [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#r0', at: 1.0, dur: 0.6, fx: 'grow' }, { sel: '.th', at: 1.2, dur: 0.4, fx: 'fade', stagger: 0.06 },
  { sel: '.R0', at: 2.0, dur: 0.4, fx: 'up', stagger: 0.07 }, { sel: '.R0r', at: 2.3, dur: 0.5, fx: 'grow' },
  { sel: '.R1', at: 3.2, dur: 0.4, fx: 'up', stagger: 0.07 }, { sel: '.R1r', at: 3.5, dur: 0.5, fx: 'grow' },
  { sel: '.R2', at: 4.4, dur: 0.4, fx: 'up', stagger: 0.07 }, { sel: '.R2r', at: 4.7, dur: 0.5, fx: 'grow' },
  { sel: '#sum', at: 6.0, dur: 0.5, fx: 'up' }, { sel: '#src', at: 6.6, dur: 0.6, fx: 'fade' },
  { sel: '.pend', at: 7.4, dur: 0.3, fx: 'pulse' },
]});
''', css='.pend { color:#DAFF3C !important; }')

# ═══ 13 結尾 ═══════════════════════════════════════════
scene('13-end', '13 結尾', '''
<div class="abs" id="line" style="left:0; top:538px; width:1920px; height:4px; background:#DAFF3C; box-shadow:0 0 22px #DAFF3C;"></div>
<h1 class="abs k" id="t" style="left:0; top:330px; width:1920px; text-align:center; font-size:150px;">謝謝觀看</h1>
<p class="abs" id="n1" style="left:0; top:600px; width:1920px; text-align:center; font-size:40px; font-weight:700;">陳紹桓　陳柏屹</p>
<p class="abs mute" id="n2" style="left:0; top:670px; width:1920px; text-align:center; font-size:30px;">指導老師　卓世明</p>
<p class="abs mute" id="n3" style="left:0; top:760px; width:1920px; text-align:center; font-size:26px;">牛耕式演算法——以 TurtleBot3 實作</p>
''', '''
Scene({ duration: 8, tracks: [
  { sel: '#line', at: 0, dur: 1.2, fx: 'grow', origin: 'center center' },
  { sel: '#t', at: 1.0, dur: 0.7, fx: 'up', dy: 40 },
  { sel: '#n1', at: 1.8, dur: 0.5, fx: 'up' }, { sel: '#n2', at: 2.1, dur: 0.5, fx: 'up' },
  { sel: '#n3', at: 2.6, dur: 0.6, fx: 'fade' },
]});
''')


# ═══ index.html：全部場景依序播放 ═════════════════════════
idx = '''<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="UTF-8"><title>牛耕式演算法｜成果影片動畫簡報</title>
<style>
  html,body{margin:0;height:100%;background:#050d10;color:#8FB3B8;font-family:"Noto Sans TC",sans-serif;overflow:hidden}
  iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
  #hud{position:absolute;right:16px;bottom:12px;font-size:13px;opacity:.6}
</style></head><body>
<iframe id="f"></iframe>
<p id="hud"></p>
<script>
const S = __S__;
let i = +(localStorage.getItem('ccpp-scene') || 0), auto = false, timer = null;
const f = document.getElementById('f'), hud = document.getElementById('hud');
function go(k) {
  i = Math.max(0, Math.min(S.length - 1, k)); localStorage.setItem('ccpp-scene', i);
  f.src = 'scenes/' + S[i][0] + '.html';
  hud.textContent = (i + 1) + ' / ' + S.length + '　' + S[i][1] + '　（← → 換鏡、空白鍵重播、A 自動連播）';
  clearTimeout(timer);
  f.onload = () => { f.contentWindow.focus(); if (auto) timer = setTimeout(() => go(i + 1), (f.contentWindow.__duration || 10) * 1000); };
}
function key(k) {
  if (k === 'ArrowRight') go(i + 1);
  if (k === 'ArrowLeft') go(i - 1);
  if (k === 'a' || k === 'A') { auto = !auto; go(i); }
}
addEventListener('message', e => e.data && e.data.key && key(e.data.key));
addEventListener('keydown', e => {
  if (e.key === 'ArrowRight') go(i + 1);
  if (e.key === 'ArrowLeft') go(i - 1);
  if (e.key === 'a' || e.key === 'A') { auto = !auto; go(i); }
});
go(i);
</script></body></html>
'''.replace('__S__', json.dumps([[n, t] for n, t in SCENES], ensure_ascii=False))
with open(os.path.join(HERE, '..', 'index.html'), 'w', encoding='utf-8') as f:
    f.write(idx)
print(len(SCENES), 'scenes')
