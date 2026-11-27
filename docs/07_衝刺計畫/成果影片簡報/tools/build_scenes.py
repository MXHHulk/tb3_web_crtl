#!/usr/bin/env python3
"""
產生 scenes/NN-*.html（15 鏡）與 index.html。每鏡的版面、文字、時間軸都在這支檔案裡，改這裡再重跑。
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
<p class="abs mute" id="legend" style="left:96px; top:978px; font-size:22px;"><span class="acid">黃 來回掃描</span>・<span class="cyan">青 最後沿牆補走一圈</span>・<span class="pink">粉 障礙物</span></p>
''', '''
const d = SCENES.cover, M = MapSVG;
document.getElementById('map').outerHTML = M.open(d.bounds, 0.1, 'id="map" class="abs" style="left:700px; top:-250px; width:1560px; height:1560px;"')
  + M.cells(d.wall, d.res, 'wall') + `<g class="obsg">${M.cells(d.obs, d.res, 'obs')}</g>` + M.route(d.plan) + M.close();
Scene({ duration: 10, steps: [10], tracks: [
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
    (340, '我們寫的', 'acid', [('覆蓋規劃', 'PCA＋cell 分解', None), ('A* 導航', '繞障路線', None),
                             ('執行與循跡', '直線循跡・脫困・紀錄', None), ('手機控制台', '一鍵開始', None),
                             ('網頁監控', '即時地圖與進度', None)], '#F2F7F5'),
    (590, 'ROS 現成套件', 'mute', [('gmapping', '建圖（SLAM）', None), ('explore_lite', '找還沒看過的邊界', None),
                                  ('move_base', '建圖時導航・對照組 DWA', None)], '#8FB3B8'),
    (840, '硬體', 'mute', [('TurtleBot3', 'Burger 差速輪式機器人', None), ('LDS 光達', '360° 雷射測距', None)], '#8FB3B8'),
]
body = '''<p class="abs kicker" id="kick" style="left:96px; top:64px;">系統架構</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">系統分三層，最上層是我們自己寫的</h1>
'''
for li, (y, lab, cls, items, col) in enumerate(layers):
    body += f'<div class="abs rule L{li}" style="left:0; top:{y - 80}px; width:1920px; height:2px; background:{"#DAFF3C" if li == 0 else "#2a4a50"};"></div>\n'
    body += f'<p class="abs lab L{li}t {cls}" style="left:96px; top:{y}px; font-size:34px; font-weight:700;">{lab}</p>\n'
    step = 300 if len(items) > 4 else 380
    for k, (main, sub, n) in enumerate(items):
        x = 400 + k * step
        body += f'<div class="abs it L{li}i" style="left:{x}px; top:{y - 8}px; width:{step - 30}px;">'
        body += f'<p style="font-size:{46 if li == 0 else 44}px; font-weight:{900 if li == 0 else 700}; color:{col}; line-height:1.15;">{main}</p>'
        body += f'<p class="mute" style="font-size:26px; margin-top:6px;">{sub}</p>'
        if n:
            body += f'<p class="num acid" style="font-size:64px; line-height:1.1; margin-top:8px;"><span class="cnt" data-n="{n}">{n}</span> <span style="font-size:28px;">行</span></p>'
        body += '</div>\n'
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
];
Scene({ duration: 14, steps: [2.9, 4.9, 9.0], tracks: tr });
''')

# ═══ 03 一鍵流程 ═══════════════════════════════════════
nodes = [('手機一鍵開始', '手機網頁控制台'), ('自動建圖', 'gmapping＋explore_lite'), ('覆蓋規劃', 'PCA＋cell 分解'),
         ('循跡執行', '自寫 A*＋直線循跡'), ('留下紀錄', '覆蓋率・軌跡・時間')]
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
const X0 = 260, X1 = 1660, P = [2.0, 4.0, 6.0, 8.0, 10.0], MV = 1.4;   // 每段停在 P[k]：第 k 個步驟亮起
Scene({ duration: 10.4, steps: P, tracks: [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#track', at: 0.8, dur: 0.6, fx: 'grow' },
  { sel: '.ns', at: 0.8, dur: 0.4, fx: 'fade', stagger: 0.1 },
], onTime: (t, u) => {
  // 第 k 段（k ≥ 1）：P[k] − MV 到 P[k] 之間，光點從第 k−1 個步驟移到第 k 個
  let q = 0;
  for (let k = 1; k < 5; k++) {
    if (t >= P[k]) q = k / 4;
    else { if (t > P[k] - MV) q = (k - 1) / 4 + u.E.inout((t - (P[k] - MV)) / MV) / 4; break; }
  }
  document.getElementById('lit').style.transform = `scaleX(${q})`;
  const sp = document.getElementById('spark');
  sp.style.left = (X0 + (X1 - X0) * q) + 'px';
  sp.style.opacity = t < P[0] - 0.5 ? 0 : u.clamp((t - (P[0] - 0.5)) / 0.5);
  for (let k = 0; k < 5; k++) {
    const on = t >= P[k] - 0.05;
    document.getElementById('n' + k).style.color = on ? (k === 0 || k === 4 ? '#F2F7F5' : '#DAFF3C') : '#4d6f75';
    document.getElementById('d' + k).style.background = on ? '#DAFF3C' : '#2a4a50';
  }
}});
''')

# ═══ 04 自動建圖 ═══════════════════════════════════════
msteps = [('① gmapping', '用光達一邊走、一邊畫地圖'),
          ('② explore_lite', '找出「已知空地」和「未知區域」的交界'),
          ('③ move_base', '開到交界去看更多；找不到交界就停下、存圖')]
body = '''<img id="flip" class="abs" src="../assets/mapflip/00.png" style="left:60px; top:110px; width:960px; height:909px; image-rendering:pixelated;">
<p class="abs kicker" id="kick" style="left:1120px; top:110px;">自動建圖</p>
<h1 class="abs k" id="t" style="left:1120px; top:156px; font-size:64px; line-height:1.25; width:760px;">自己找路，<br>建完整張地圖</h1>
'''
for k, (a, b) in enumerate(msteps):
    body += (f'<div class="abs ms" style="left:1120px; top:{380 + k * 115}px; width:760px;">'
             f'<p class="num acid" style="font-size:32px;">{a}</p><p style="font-size:28px; line-height:1.4;">{b}</p></div>\n')
body += '''<div class="abs st" style="left:1120px; top:760px;"><p class="num acid" style="font-size:120px; line-height:1;"><span id="s1">6</span><span style="font-size:48px;"> / 6 次</span></p><p style="font-size:28px; font-weight:700;">實測都自己建出完整地圖</p></div>
'''
scene('04-mapping', '04 自動建圖', body, '''
const N = 47, imgs = [];
for (let i = 0; i < N; i++) { const im = new Image(); im.src = `../assets/mapflip/${String(i).padStart(2, '0')}.png`; imgs.push(im); }
Scene({ duration: 10, steps: [6.2], tracks: [
  { sel: '#flip', at: 0.0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.3, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.5, dur: 0.6, fx: 'up' },
  { sel: '.ms', at: 1.4, dur: 0.5, fx: 'up', stagger: 1.4 },
  { sel: '.st', at: 6.4, dur: 0.5, fx: 'up' },
  { sel: '#s1', at: 6.6, dur: 1.0, fx: 'count', from: 0, to: 6 },
], onTime: (t, u) => {
  const i = Math.round(u.clamp((t - 0.6) / 5.4) * (N - 1));
  const el = document.getElementById('flip');
  const src = imgs[i].src;
  if (el.src !== src) el.src = src;
}});
''')

# ═══ 05 覆蓋規劃五步驟（同海報研究方法）═══════════════════
msteps = [('①', 'PCA 主軸對齊', '找散布最廣的方向當長軸，與它垂直的短軸當換行方向'),
          ('②', '切帶', '沿短軸切成等寬的帶，每帶一條掃描線'),
          ('③', 'cell 分解', '把空間分成數個內部沒有障礙的 cell'),
          ('④', 'cell 內牛耕', '每個 cell 內來回掃描，只在換行處轉彎'),
          ('⑤', 'cell 間銜接', '由近到遠，最近的 cell 先做')]
body = '''<p class="abs kicker" id="kick" style="left:96px; top:64px;">覆蓋規劃</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">地圖進去，路線出來：五個步驟</h1>
<p class="abs lede" id="l1" style="left:96px; top:240px; width:1700px; font-size:34px;">建好的地圖先扣掉障礙物周圍的安全邊距，再依序經過五個步驟，變成一串給車子走的路點。</p>
'''
for k, (n, a, b) in enumerate(msteps):
    x = 96 + k * 360
    body += (f'<div class="abs c c{k}" style="left:{x}px; top:400px; width:310px;">'
             f'<p class="num acid" style="font-size:110px; line-height:1;">{n}</p>'
             f'<p style="font-size:40px; font-weight:900; margin-top:24px;">{a}</p>'
             f'<p class="mute" style="font-size:28px; line-height:1.5; margin-top:14px;">{b}</p></div>\n')
    if k < 4:
        body += f'<p class="abs num ar ar{k}" style="left:{x + 300}px; top:420px; font-size:60px; color:#2a4a50;">›</p>\n'
body += '<div class="abs" id="ln" style="left:96px; top:800px; width:1728px; height:2px; background:#2a4a50;"></div>\n'
body += '<p class="abs mute" id="nt" style="left:96px; top:830px; font-size:28px;">①② 決定掃描方向與每條掃描線；③④⑤ 處理障礙物與走的順序</p>\n'
scene('05-method', '05 覆蓋規劃五步驟', body, '''
const tr = [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#l1', at: 0.8, dur: 0.5, fx: 'up' },
];
for (let k = 0; k < 5; k++) {
  tr.push({ sel: '.c' + k, at: 1.6 + 1.2 * k, dur: 0.45, fx: 'up' });
  if (k > 0) tr.push({ sel: '.ar' + (k - 1), at: 1.5 + 1.2 * k, dur: 0.3, fx: 'fade' });
}
tr.push({ sel: '#ln', at: 7.6, dur: 0.6, fx: 'grow' }, { sel: '#nt', at: 7.8, dur: 0.5, fx: 'fade' });
Scene({ duration: 8.6, steps: [1.2, 2.2, 3.4, 4.6, 5.8, 7.0], tracks: tr });
''')

# ═══ 06 PCA ═══════════════════════════════════════════
scene('06-pca', '06 ① PCA ② 切帶', '''
<div id="mapbox" class="abs" style="left:840px; top:40px; width:1040px; height:1000px;"></div>
<p class="abs kicker" id="kick" style="left:96px; top:200px;">覆蓋規劃 ① ②</p>
<h1 class="abs k" id="t" style="left:96px; top:250px; font-size:76px; line-height:1.25; width:720px;">找出房間長邊，<br>沿短軸切帶</h1>
<p class="abs lede" id="l1" style="left:96px; top:500px; width:700px;"><span class="acid">① PCA</span>：把可走的格子當成一團點，散布最廣的方向當長軸，垂直的當短軸。</p>
<p class="abs lede" id="l2" style="left:96px; top:690px; width:700px;"><span class="acid">② 切帶</span>：沿短軸切成等寬的帶，每帶一條掃描線，沿長軸來回掃。</p>
<p class="abs mute" id="lg" style="left:96px; top:900px; width:720px; font-size:28px; line-height:1.6;"><span class="acid">黃</span>：沿長邊來回掃<br><span class="cyan">青</span>：最後沿牆補走一圈，補掃描線頭尾照不到的牆邊</p>
''', '''
const d = SCENES.tilt, M = MapSVG, ax = d.plan.axes, E = ax.ext;   // E＝可走格在長軸、短軸上的投影範圍
const c = ax.c, a = ax.a, b = ax.b;
const seg = (v, lo, hi, cls) => M.poly([[c[0] + v[0] * lo, c[1] + v[1] * lo], [c[0] + v[0] * hi, c[1] + v[1] * hi]], cls);
document.getElementById('mapbox').innerHTML = M.open(d.bounds, 0.1, 'style="left:0; top:0; width:100%; height:100%;"')
  + M.cells(d.wall, d.res, 'wall')
  + `<g id="pts">${d.points.map(p => `<circle cx="${p[0]}" cy="${p[1]}" r="0.011" class="pt"/>`).join('')}</g>`
  + seg(a, E[0], E[1], 'axA') + seg(b, E[2], E[3], 'axB') + M.route(d.plan) + M.close();
Scene({ duration: 12, steps: [2.1, 4.2, 10.2], tracks: [
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
  { sel: '#lg', at: 9.2, dur: 0.6, fx: 'fade' },
]});
''', css='''.pt { fill:#39E6FF; opacity:.75; }
.axA { fill:none; stroke:#F2F7F5; stroke-width:.03; stroke-dasharray:.08 .05; }
.axB { fill:none; stroke:#39E6FF; stroke-width:.022; }''')

# ═══ 07 cell 分解 ═══════════════════════════════════════
scene('07-cells', '07 ③ cell 分解 ④ 牛耕 ⑤ 銜接', '''
<p class="abs kicker" id="kick" style="left:96px; top:64px;">覆蓋規劃 ③ ④ ⑤</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">有障礙物，就切成幾個 cell 各自掃</h1>
<p class="abs lede" id="l1" style="left:96px; top:230px; width:1700px; font-size:34px;"><span class="acid">③</span> 掃描線碰到障礙物會從一段變成兩段，就在那裡（白虛線）切開；<span class="acid">④</span> 每個 cell 內來回掃；<span class="acid">⑤</span> 再由近到遠串起來。</p>
<div id="mapbox" class="abs" style="left:160px; top:340px; width:1600px; height:700px;"></div>
''', '''
const d = SCENES.field, M = MapSVG, cols = ['#DAFF3C', '#39E6FF', '#C9B6FF', '#F2F7F5'];
let g = M.open(d.bounds, 0.08, 'style="left:0; top:0; width:100%; height:100%;"') + M.cells(d.wall, d.res, 'wall')
  + `<g class="obsg">${M.cells(d.obs, d.res, 'obs')}</g>`
  + d.bandCuts.map(y => M.poly([[d.cuts[4], y], [d.cuts[5], y]], 'cutl')).join('');
const cells = d.plan.cells;
cells.forEach((cl, i) => {
  g += M.poly(cl, `cp cp${i}`, `style="stroke:${cols[i % 4]}"`);
  if (i > 0) { const p = cells[i - 1][cells[i - 1].length - 1], q = cl[0]; g += `<path class="mv mv${i}" d="M${p[0]} ${p[1]}L${q[0]} ${q[1]}"/>`; }
  const s = cl[0], up = s[1] + 0.05, near = d.bandCuts.some(y => Math.abs(y - up) < 0.07);
  g += `<g transform="translate(${s[0]} ${near ? s[1] - 0.09 : up}) scale(1,-1)"><text class="cl cl${i}" x="0" y="0" style="fill:${cols[i % 4]}">cell ${i + 1}</text></g>`;
});
document.getElementById('mapbox').innerHTML = g + M.close();
const tr = [
  { sel: '.wall', at: 0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.obsg', at: 1.2, dur: 0.4, fx: 'pop' },
  { sel: '#l1', at: 1.6, dur: 0.5, fx: 'up' },
  { sel: '.cutl', at: 2.0, dur: 0.6, fx: 'draw', stagger: 0.3 },
];
const per = 7.5 / cells.length;
cells.forEach((cl, i) => {
  const at = 3.0 + i * per;
  tr.push({ sel: '.cl' + i, at, dur: 0.3, fx: 'up', dy: 10 });
  tr.push({ sel: '.cp' + i, at: at + 0.2, dur: per - 0.4, fx: 'draw', ease: 'lin' });
  if (i > 0) tr.push({ sel: '.mv' + i, at: at - 0.1, dur: 0.3, fx: 'fade' });
});
Scene({ duration: 14, steps: [2.6, 11.0], tracks: tr });
''', css='''.cp { fill:none; stroke-width:.026; stroke-linejoin:round; stroke-linecap:round; filter:url(#glow); }
.cutl { fill:none; stroke:#F2F7F5; stroke-width:.014; stroke-dasharray:.07 .05; opacity:.85; }
.mv { fill:none; stroke:#F2F7F5; stroke-width:.012; stroke-dasharray:.03 .03; opacity:.8; }
.cl { font-family:Bahnschrift, sans-serif; font-weight:700; font-size:.075px; }''')

# ═══ 08 安全邊距 ═════════════════════════════════════════
# 圖解（格子畫法同地圖頁）：程式把每個障礙格往四周各擴 round(13 cm ÷ 5 cm) = 3 格（正方形），車子中心只走剩下的空地
scene('08-margin', '08 安全邊距', '''
<svg id="dia" class="abs" style="left:60px; top:140px; width:900px; height:840px;" viewBox="0 0 90 84"></svg>
<p class="abs kicker" id="kick" style="left:1040px; top:150px;">安全邊距</p>
<h1 class="abs k" id="t" style="left:1040px; top:196px; font-size:68px; line-height:1.25; width:820px;">障礙物往外擴 3 格，<br>車子就撞不到</h1>
<p class="abs lede" id="l1" style="left:1040px; top:440px; width:840px;">車身半寬 <span class="num">10.5 cm</span>，加上格子誤差 <span class="num">2.5 cm</span>，<br>需要 13 cm；一格 5 cm，取 <span class="num acid" style="white-space:nowrap;">3 格＝15 cm</span>。</p>
<p class="abs lede" id="l2" style="left:1040px; top:640px; width:840px;">路徑只規劃在擴完之後剩下的空地上，<br>車子中心走在上面，車身碰不到障礙物。</p>
<div class="abs" id="d1" style="left:1040px; top:850px;"><p class="num acid" style="font-size:90px; line-height:1;">約 4 成</p><p class="mute" style="font-size:28px;">實測地圖的空地，扣掉安全邊距後車子中心能走的比例</p></div>
''', '''
// 單位：公分，一格 5 cm。障礙物 6×4 格；禁區＝每格往四周各擴 3 格（正方形，與程式 apply_safety_margin 相同）
const C = 5, I = 0.6, ob = [3, 6, 6, 4], R = 3;                  // 障礙物：左下格 (3,6)，寬 6 格、高 4 格
const cell = (gx, gy, cls) => `<rect class="${cls}" x="${gx * C + I}" y="${gy * C + I}" width="${C - 2 * I}" height="${C - 2 * I}"/>`;
const g = [];
for (let gx = 0; gx < 18; gx++) for (let gy = 0; gy < 16; gy++) {
  const inObs = gx >= ob[0] && gx < ob[0] + ob[2] && gy >= ob[1] && gy < ob[1] + ob[3];
  const inZone = gx >= ob[0] - R && gx < ob[0] + ob[2] + R && gy >= ob[1] - R && gy < ob[1] + ob[3] + R;
  g.push(cell(gx, gy, inObs ? 'obsc' : inZone ? 'zonec' : 'freec'));
}
const zx = (ob[0] + ob[2] + R) * C, ox1 = (ob[0] + ob[2]) * C;  // 禁區右緣、障礙物右緣
const cx = zx + C / 2, cy = (ob[1] + ob[3] / 2) * C;              // 車子中心：禁區外第一格的中心
document.getElementById('dia').innerHTML = g.join('')
  + `<g class="dim"><line x1="${ox1}" y1="${ob[1] * C - R * C - 4}" x2="${zx}" y2="${ob[1] * C - R * C - 4}" class="dl"/>`
  + `<line x1="${ox1}" y1="${ob[1] * C - R * C - 6}" x2="${ox1}" y2="${ob[1] * C - R * C - 2}" class="dl"/><line x1="${zx}" y1="${ob[1] * C - R * C - 6}" x2="${zx}" y2="${ob[1] * C - R * C - 2}" class="dl"/>`
  + `<text x="${(ox1 + zx) / 2}" y="${ob[1] * C - R * C - 6.5}" class="dt">3 格＝15 cm</text></g>`
  + `<g class="car"><rect x="${cx - 10.5}" y="${cy - 4.1}" width="21" height="14.6" class="body"/>`
  + `<circle cx="${cx}" cy="${cy}" r="1.3" class="ctr"/><line x1="${cx}" y1="${cy}" x2="${cx}" y2="${cy - 8}" class="hd"/></g>`
  + `<text x="${(ob[0] + ob[2] / 2) * C}" y="${cy + 1.4}" class="bt">障礙物</text>`
  + `<text x="${cx + 12}" y="${cy + 1.4}" class="ct">車子中心</text>`;
Scene({ duration: 10, steps: [2.4, 5.6], tracks: [
  { sel: '.freec', at: 0, dur: 0.6, fx: 'fade', max: 1 },
  { sel: '.obsc', at: 0.4, dur: 0.4, fx: 'pop' }, { sel: '.bt', at: 0.6, dur: 0.4, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.zonec', at: 2.6, dur: 0.8, fx: 'pop' }, { sel: '.dim', at: 3.4, dur: 0.5, fx: 'fade' },
  { sel: '#l1', at: 3.0, dur: 0.5, fx: 'up' },
  { sel: '.car', at: 5.8, dur: 0.6, fx: 'up', dy: 20 }, { sel: '.ct', at: 6.2, dur: 0.4, fx: 'fade' },
  { sel: '#l2', at: 6.2, dur: 0.5, fx: 'up' }, { sel: '#d1', at: 7.2, dur: 0.5, fx: 'up' },
]});
''', css='''.freec { fill:rgba(120,170,178,.10); }
.obsc { fill:#FF4FD8; }
.zonec { fill:rgba(255,79,216,.30); }
.body { fill:rgba(57,230,255,.18); stroke:#39E6FF; stroke-width:.45; }
.ctr { fill:#DAFF3C; } .hd { stroke:#DAFF3C; stroke-width:.5; }
.dl { stroke:#DAFF3C; stroke-width:.35; } .dt { fill:#DAFF3C; font-size:3.2px; font-weight:700; text-anchor:middle; }
.bt { fill:#08161b; font-size:3.6px; font-weight:900; text-anchor:middle; stroke:#FF4FD8; stroke-width:1.4; paint-order:stroke; }
.ct { fill:#DAFF3C; font-size:3px; font-weight:700; }''')

# ═══ 09 循跡執行 ═══════════════════════════════════════
# 開場同一張地圖：掃描線（黃）直線循跡；cell 之間的白線是專案 astar.py 實際算出的 A* 路線
scene('09-execute', '09 循跡執行', '''
<div id="mapbox" class="abs" style="left:20px; top:40px; width:1140px; height:1000px;"></div>
<p class="abs kicker" id="kick" style="left:1220px; top:110px;">循跡執行</p>
<h1 class="abs k" id="t" style="left:1220px; top:156px; font-size:60px; line-height:1.25; width:640px;">掃描線直線循跡，<br>cell 之間走 A*</h1>
<div class="abs" id="r1" style="left:1220px; top:390px; width:640px;">
  <p class="acid" style="font-size:34px; font-weight:900;">直線循跡</p>
  <p style="font-size:30px; line-height:1.5; margin-top:6px;">沿著每條掃描線開直線；偏離了，就依偏離的距離把方向修回來。</p>
</div>
<div class="abs" id="r2" style="left:1220px; top:610px; width:640px;">
  <p style="font-size:34px; font-weight:900;">A* 銜接</p>
  <p style="font-size:30px; line-height:1.5; margin-top:6px;">從一個 cell 到下一個，A* 在地圖格子上找一條繞開障礙、和牆保持距離的路線。</p>
</div>
<p class="abs mute" id="r3" style="left:1220px; top:870px; width:640px; font-size:26px; line-height:1.5;">這兩段原本交給 ROS 的 move_base（DWA），在牆邊容易卡住，所以改成自己寫（問題四）。</p>
''', '''
const d = SCENES.cover, M = MapSVG;
document.getElementById('mapbox').innerHTML = M.open(d.bounds, 0.1, 'style="left:0; top:0; width:100%; height:100%;"')
  + M.cells(d.wall, d.res, 'wall') + `<g class="obsg">${M.cells(d.obs, d.res, 'obs')}</g>` + M.route(d.plan)
  + d.links.map(l => M.poly(l, 'lk')).join('') + M.close();
Scene({ duration: 9.6, steps: [5.4, 8.6], tracks: [
  { sel: '.wall', at: 0, dur: 0.6, fx: 'fade' }, { sel: '.obsg', at: 0.3, dur: 0.4, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.rt-sweep', at: 0.9, dur: 4.2, fx: 'draw', ease: 'lin' },
  { sel: '#r1', at: 1.4, dur: 0.5, fx: 'up' },
  { sel: '.lk', at: 5.8, dur: 1.2, fx: 'draw', stagger: 0.3 },
  { sel: '#r2', at: 5.8, dur: 0.5, fx: 'up' },
  { sel: '.rt-ring', at: 7.0, dur: 1.0, fx: 'draw' },
  { sel: '#r3', at: 7.6, dur: 0.5, fx: 'fade' },
]});
''', css='''.rt-move { display:none; }
.lk { fill:none; stroke:#F2F7F5; stroke-width:.035; stroke-linecap:round; stroke-linejoin:round; filter:url(#glow); }''')

# ═══ 10 問題一：為什麼要 PCA ═══════════════════════════
scene('10-p1-pca', '10 問題一：為什麼要 PCA', '''
<div id="mapbox" class="abs" style="left:840px; top:40px; width:1040px; height:1000px;"></div>
<p class="abs kicker" id="kick" style="left:96px; top:100px;">問題一</p>
<h1 class="abs k" id="t" style="left:96px; top:146px; font-size:64px; line-height:1.25; width:740px;">為什麼用 PCA，<br>不沿地圖座標軸？</h1>
<p class="abs" id="pp" style="left:96px; top:380px; width:700px; font-size:32px; line-height:1.55;"><span class="pill p">問題</span>車子開機時沒擺正，SLAM 地圖就是斜的；沿地圖座標軸掃，掃描線被斜牆切得<span class="pink">又短又碎</span>。</p>
<p class="abs" id="ps" style="left:96px; top:560px; width:700px; font-size:32px; line-height:1.55;"><span class="pill s">解法</span>用 PCA 找出房間的長邊，當作掃描方向。</p>
<p class="abs" id="pr" style="left:96px; top:680px; width:700px; font-size:32px; line-height:1.55;"><span class="pill r">結果</span>掃描線和牆平行，<span class="acid">不管車子開機時朝哪個方向</span>。</p>
''', '''
const d = SCENES.tilt, M = MapSVG;
document.getElementById('mapbox').innerHTML = M.open(d.bounds, 0.1, 'id="map" style="left:0; top:0; width:100%; height:100%;"')
  + M.cells(d.wall, d.res, 'wall') + `<g id="axg">${d.axisLines.map(l => M.poly(l, 'axl')).join('')}</g>` + M.route(d.plan) + M.close();
Scene({ duration: 11, steps: [5.2, 10.4], tracks: [
  { sel: '.wall', at: 0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.axl', at: 3.2, dur: 0.5, fx: 'draw', stagger: 0.06 },
  { sel: '#pp', at: 3.4, dur: 0.5, fx: 'up' },
  { sel: '#axg', at: 5.6, dur: 0.6, fx: 'out' },
  { sel: '#ps', at: 5.8, dur: 0.5, fx: 'up' },
  { sel: '.rt-sweep', at: 6.0, dur: 3.4, fx: 'draw', ease: 'lin' },
  { sel: '.rt-ring', at: 9.2, dur: 0.8, fx: 'draw' },
  { sel: '#pr', at: 9.4, dur: 0.5, fx: 'up' },
], onTime: (t, u) => {
  // 房間先是正的，再轉成斜 30°（模擬車子沒擺正）
  const p = u.E.inout(u.clamp((t - 1.0) / 1.8));
  document.getElementById('map').style.transform = `rotate(${30 * (1 - p)}deg)`;
}});
''', css='.axl { fill:none; stroke:#FF4FD8; stroke-width:.026; stroke-linecap:round; filter:url(#glow); }')

# ═══ 11 問題二：掃描線穿過障礙 ═══════════════════════════
scene('11-p2-cross', '11 問題二：穿過障礙', '''
<p class="abs kicker" id="kick" style="left:96px; top:64px;">問題二</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">掃描線直接穿過障礙物</h1>
<div id="mapbox" class="abs" style="left:40px; top:250px; width:1220px; height:740px;"></div>
<p class="abs mute" id="cap" style="left:96px; top:1000px; font-size:24px;"><span class="pink">粉：舊版的掃描線</span>　<span style="color:#F2F7F5;">白虛線：切開的地方</span>　<span class="acid">黃：cell 分解後的路徑</span></p>
<div class="abs" id="pp" style="left:1320px; top:270px; width:560px;">
  <p style="font-size:30px; line-height:1.5;"><span class="pill p">問題</span>舊版整個房間一起掃</p>
  <p class="num pink" style="font-size:110px; line-height:1.1; margin-top:6px;"><span id="oc"></span> 條</p>
  <p style="font-size:28px;">掃描線直接穿過障礙物（共 <span id="on"></span> 條）</p>
</div>
<p class="abs" id="ps" style="left:1320px; top:560px; width:560px; font-size:30px; line-height:1.5;"><span class="pill s">解法</span>在掃描線從一段變成兩段的地方（白虛線）切開，分成 <span class="num acid">4</span> 個沒有障礙的 cell，各自來回掃。</p>
<div class="abs" id="pr" style="left:1320px; top:790px; width:560px;">
  <p style="font-size:30px;"><span class="pill r">結果</span></p>
  <p class="num acid" style="font-size:68px; line-height:1.1; margin-top:8px; white-space:nowrap;">穿過障礙 0 條</p>
  <p class="mute" style="font-size:24px; margin-top:8px;">實測 6 次規劃，331 段掃描線也全部在可走區內</p>
</div>
''', '''
const d = SCENES.field, M = MapSVG;
document.getElementById('oc').textContent = d.oldStats[1];
document.getElementById('on').textContent = d.oldStats[0];
// cuts：障礙＋邊距 x0,x1,y0,y1；可走區 x0,x1,y0,y1。bandCuts：cell 之間的水平分界
const [zx0, zx1, zy0, zy1, fx0, fx1, fy0, fy1] = d.cuts, [c0, c1] = d.bandCuts;
const cols = ['#DAFF3C', '#39E6FF', '#C9B6FF', '#F2F7F5'];   // 與 07 頁相同（依規劃順序）
const regs = [[fx0, fy0, fx1, c0], [fx0, c1, fx1, fy1], [fx0, c0, zx0, c1], [zx1, c0, fx1, c1]];
const ctr = cl => cl.reduce((a, p) => [a[0] + p[0] / cl.length, a[1] + p[1] / cl.length], [0, 0]);
const inR = (c, r) => c[0] >= r[0] - 1e-3 && c[0] <= r[2] + 1e-3 && c[1] >= r[1] - 1e-3 && c[1] <= r[3] + 1e-3;
const rect = (r, st) => `<rect class="reg" x="${r[0]}" y="${r[1]}" width="${r[2] - r[0]}" height="${r[3] - r[1]}" style="${st}"/>`;
let reg = '';
d.plan.cells.forEach((cl, i) => {
  const r = regs.find(r => inR(ctr(cl), r)); if (!r) return;
  reg += rect(r, `fill:${cols[i % 4]}`);
  const lx = (r[0] + r[2]) / 2, ly = (r[1] + r[3]) / 2;
  reg += `<g transform="translate(${lx} ${ly}) scale(1,-1)"><text class="rl" x="0" y="0.025" style="fill:${cols[i % 4]}">cell ${i + 1}</text></g>`;
});
const cut = y => M.poly([[fx0, y], [fx1, y]], 'cutl');
document.getElementById('mapbox').innerHTML = M.open(d.bounds, 0.08, 'style="left:0; top:0; width:100%; height:100%;"')
  + M.cells(d.wall, d.res, 'wall') + `<g class="regs">${reg}</g>` + `<g class="obsg">${M.cells(d.obs, d.res, 'obs')}</g>`
  + `<g id="oldg">${d.oldLines.map(l => M.poly(l, 'old')).join('')}</g>` + cut(c0) + cut(c1) + M.route(d.plan) + M.close();
Scene({ duration: 14, steps: [3.8, 7.0, 12.6], tracks: [
  { sel: '.wall', at: 0, dur: 0.5, fx: 'fade' }, { sel: '.obsg', at: 0.3, dur: 0.4, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.old', at: 1.0, dur: 0.8, fx: 'draw', stagger: 0.2 },
  { sel: '#pp', at: 2.6, dur: 0.5, fx: 'up' },
  { sel: '.cutl', at: 4.2, dur: 0.8, fx: 'draw', stagger: 0.3 },
  { sel: '#ps', at: 4.6, dur: 0.5, fx: 'up' },
  { sel: '.regs', at: 5.2, dur: 0.8, fx: 'fade' },
  { sel: '.rt-sweep', at: 7.4, dur: 3.6, fx: 'draw', ease: 'lin' },
  { sel: '.rt-move', at: 10.8, dur: 0.4, fx: 'fade' },
  { sel: '.rt-ring', at: 11.0, dur: 0.9, fx: 'draw' },
  { sel: '#pr', at: 8.6, dur: 0.5, fx: 'up' },
  { sel: '#cap', at: 1.6, dur: 0.6, fx: 'fade' },
], onTime: (t) => {
  // 舊線先完整亮著，切開時退成暗影
  document.getElementById('oldg').style.opacity = t < 4.2 ? 1 : Math.max(0.15, 1 - (t - 4.2) / 0.6 * 0.85);
  // cell 標籤在路徑畫出來之後退淡，避免蓋住路徑
  document.querySelectorAll('.rl').forEach(e => e.style.opacity = t < 7.4 ? 1 : Math.max(0.35, 1 - (t - 7.4) / 0.6));
}});
''', css='''.old { fill:none; stroke:#FF4FD8; stroke-width:.03; stroke-linecap:round; filter:url(#glow); }
.cutl { fill:none; stroke:#F2F7F5; stroke-width:.014; stroke-dasharray:.07 .05; opacity:.85; }
.reg { opacity:.13; }
.rl { font-family:Bahnschrift, sans-serif; font-weight:700; font-size:.07px; text-anchor:middle; }''')

# ═══ 12 問題三：光達雜點 ═══════════════════════════════════
scene('12-p3-noise', '12 問題三：假障礙', '''
<svg id="dia" class="abs" style="left:100px; top:150px; width:760px; height:760px;" viewBox="0 0 60 60"></svg>
<p class="abs kicker" id="kick" style="left:960px; top:110px;">問題三</p>
<h1 class="abs k" id="t" style="left:960px; top:156px; font-size:64px; line-height:1.25; width:900px;">光達雜點，被當成障礙物</h1>
<p class="abs" id="pp" style="left:960px; top:300px; width:900px; font-size:32px; line-height:1.55;"><span class="pill p">問題</span>一顆 <span class="num">5 cm</span> 的雜點，四周各擴 <span class="num">3 格（15 cm）</span>，<br>就變成 <span class="num pink">35 cm</span> 見方的禁區，路線被迫繞開。</p>
<p class="abs" id="ps" style="left:960px; top:480px; width:900px; font-size:32px; line-height:1.55;"><span class="pill s">解法</span>規劃前，把 3 格以下的小團塊當成雜點過濾掉。</p>
<div class="abs" id="pr" style="left:960px; top:600px; width:900px;">
  <p style="font-size:32px; line-height:1.55;"><span class="pill r">結果</span>可規劃面積 <span class="acid">+18%</span><span class="mute" style="font-size:26px;">（實測 6 次中雜點最多的一次）</span></p>
  <p class="num" style="font-size:130px; line-height:1; margin-top:20px;"><span class="mute" style="font-size:70px;">0.69 → </span><span id="a2" class="acid">0.82</span><span style="font-size:52px;"> m²</span></p>
</div>
''', '''
// 單位：公分，一格 5 cm（格子畫法同地圖頁）。雜點 1 格在 (5,5)，禁區往四周各擴 3 格 → 7×7 格＝35 cm
const C = 5, I = 0.6, n = 5, R = 3;
const cell = (gx, gy, cls) => `<rect class="${cls}" x="${gx * C + I}" y="${gy * C + I}" width="${C - 2 * I}" height="${C - 2 * I}"/>`;
const g = [];
for (let gx = 0; gx < 12; gx++) for (let gy = 0; gy < 11; gy++) {
  const isN = gx === n && gy === n, inZ = Math.abs(gx - n) <= R && Math.abs(gy - n) <= R;
  g.push(cell(gx, gy, isN ? 'dotn' : inZ ? 'zonec' : 'freec'));
}
const z0 = (n - R) * C, z1 = (n + R + 1) * C, a = n * C, yd = z1 + 4;
const tick = x => `<line x1="${x}" y1="${yd - 1.5}" x2="${x}" y2="${yd + 1.5}" class="dl"/>`;
document.getElementById('dia').innerHTML = g.join('')
  + `<g class="dim"><line x1="${z0}" y1="${yd}" x2="${z1}" y2="${yd}" class="dl"/>${tick(z0)}${tick(a)}${tick(a + C)}${tick(z1)}`
  + `<text x="${(z0 + a) / 2}" y="${yd - 2.2}" class="dt">15</text><text x="${a + C / 2}" y="${yd - 2.2}" class="dt w">5</text>`
  + `<text x="${(a + C + z1) / 2}" y="${yd - 2.2}" class="dt">15</text>`
  + `<text x="${(z0 + z1) / 2}" y="${yd + 6}" class="dt big">= 35 cm</text></g>`
  + `<text x="${a + C / 2}" y="${a + C / 2 + 1.5}" class="ok">過濾後，這裡都能走</text>`;
Scene({ duration: 11, steps: [2.4, 6.0], tracks: [
  { sel: '.freec', at: 0, dur: 0.6, fx: 'fade', max: 1 },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.dotn', at: 1.2, dur: 0.4, fx: 'pop' },
  { sel: '.zonec', at: 2.6, dur: 0.8, fx: 'pop' }, { sel: '.dim', at: 3.4, dur: 0.6, fx: 'fade' },
  { sel: '#pp', at: 3.0, dur: 0.5, fx: 'up' },
  { sel: '#ps', at: 6.2, dur: 0.5, fx: 'up' },
  { sel: '#pr', at: 7.0, dur: 0.5, fx: 'up' },
  { sel: '.ok', at: 7.0, dur: 0.5, fx: 'fade' },
  { sel: '#a2', at: 7.2, dur: 1.4, fx: 'count', from: 0.69, to: 0.82, dec: 2 },
], onTime: (t, u) => {
  // 過濾：6.2 s 起禁區與雜點一起淡掉
  const gone = u.clamp((t - 6.2) / 0.8);
  if (t > 6.2) document.querySelectorAll('.zonec, .dotn, .dim').forEach(e => e.style.opacity = 1 - gone * 0.85);
}});
''', css='''.freec { fill:rgba(120,170,178,.10); }
.zonec { fill:rgba(255,79,216,.30); }
.dotn { fill:#DAFF3C; }
.dl { stroke:#F2F7F5; stroke-width:.3; }
.dt { fill:#FF4FD8; font-size:2.8px; font-weight:700; text-anchor:middle; }
.dt.w { fill:#DAFF3C; } .dt.big { fill:#F2F7F5; font-size:3.6px; }
.ok { fill:#DAFF3C; font-size:3.6px; font-weight:900; text-anchor:middle; }''')

# ═══ 13 問題四：move_base → 自寫 A*＋直線循跡（含數據總表）═══════════════════════
# 三張長條圖：受困次數、覆蓋時間、覆蓋率；自寫 A*＋循跡（本專題）黃綠、move_base（navfn＋DWA）灰。每按一下出一張
# 兩層（算路線、開車）一起換掉，所以比較對象是兩套完整導航，不寫成「A* vs DWA」
A_, M_ = 'A*＋循跡', 'move_base'
charts = [('受困次數', '3 次實驗中', [(A_, 0, '0 次'), (M_, 2, '2 次')], 3),
          ('覆蓋時間', '平均（分鐘）', [(A_, 3.24, '3.2 分'), (M_, 10.07, '10.1 分')], 12),
          ('覆蓋率', '平均', [(A_, 90.9, '90.9%'), (M_, 82.7, '82.7%')], 100)]
body = '''<svg id="corner" class="abs"></svg>
<p class="abs kicker" id="kick" style="left:96px; top:64px;">問題四</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">move_base 在牆邊卡住</h1>
<p class="abs" id="pp" style="left:96px; top:228px; font-size:32px;"><span class="pill p">問題</span>移動交給 ROS 的 move_base，它負責開車的 DWA 在牆邊找不到路就卡住，覆蓋拖很久甚至停擺。</p>
<p class="abs" id="ps" style="left:96px; top:290px; font-size:32px;"><span class="pill s">解法</span>算路線、開車兩層一起換掉：自寫 <span class="acid">A* 規劃路線＋直線循跡開車</span>。</p>
<p class="abs" id="pr" style="left:96px; top:352px; font-size:32px;"><span class="pill r">結果</span>同一場地各跑 3 次：</p>
<p class="abs" id="lg" style="left:960px; top:362px; font-size:26px;"><span class="sw" style="background:#DAFF3C;"></span>自寫 A*＋直線循跡（本專題）　<span class="sw" style="background:#5f8288;"></span><span class="mute">move_base（navfn＋DWA）</span></p>
'''
for c, (name, sub, bars, vmax) in enumerate(charts):
    x0 = 150 + c * 570
    body += f'<div class="abs ch C{c}" style="left:{x0}px; top:430px; width:480px; height:560px;">'
    body += f'<p style="font-size:36px; font-weight:900;">{name}</p><p class="mute" style="font-size:22px;">{sub}</p>'
    body += '<div class="base"></div>'
    for b, (lab, v, txt) in enumerate(bars):
        h = 320 * v / vmax
        col = '#DAFF3C' if b == 0 else '#5f8288'
        body += (f'<div class="bar B{c}" style="left:{60 + b * 200}px; height:{max(h, 4):.0f}px; background:{col};"></div>'
                 f'<p class="val num B{c}v" style="left:{20 + b * 200}px; bottom:{max(h, 4) + 72:.0f}px; color:{"#DAFF3C" if b == 0 else "#8FB3B8"};">{txt}</p>'
                 f'<p class="lab" style="left:{20 + b * 200}px;">{lab}</p>')
    body += '</div>\n'
body += '<p class="abs mute" id="note" style="left:150px; top:1004px; font-size:24px;">A*＋循跡 3 次全部跑完；move_base 只跑完 1 次，另 2 次受困提早結束，實際所需時間更長</p>\n'
scene('13-p4-dwa', '13 問題四：move_base → 自寫 A*＋循跡', body, '''
const d = SCENES.cover, M = MapSVG;
document.getElementById('corner').outerHTML = M.open(d.bounds, 0.1, 'id="corner" class="abs" style="left:1500px; top:-1180px; width:1560px; height:1560px; opacity:.35;"')
  + M.cells(d.wall, d.res, 'wall') + M.route(d.plan) + M.close();
Scene({ duration: 10.4, steps: [1.4, 2.2, 3.0, 5.0, 7.2, 9.4], tracks: [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#pp', at: 0.8, dur: 0.5, fx: 'up' },
  { sel: '#ps', at: 1.6, dur: 0.5, fx: 'up' },
  { sel: '#pr', at: 2.4, dur: 0.5, fx: 'up' }, { sel: '#lg', at: 2.5, dur: 0.5, fx: 'fade' },
  { sel: '.C0', at: 3.2, dur: 0.4, fx: 'fade' }, { sel: '.B0', at: 3.5, dur: 0.9, fx: 'grow', origin: 'center bottom', stagger: 0.25 },
  { sel: '.B0v', at: 4.4, dur: 0.4, fx: 'up', stagger: 0.25 },
  { sel: '.C1', at: 5.2, dur: 0.4, fx: 'fade' }, { sel: '.B1', at: 5.5, dur: 0.9, fx: 'grow', origin: 'center bottom', stagger: 0.25 },
  { sel: '.B1v', at: 6.4, dur: 0.4, fx: 'up', stagger: 0.25 },
  { sel: '.C2', at: 7.4, dur: 0.4, fx: 'fade' }, { sel: '.B2', at: 7.7, dur: 0.9, fx: 'grow', origin: 'center bottom', stagger: 0.25 },
  { sel: '.B2v', at: 8.6, dur: 0.4, fx: 'up', stagger: 0.25 },
  { sel: '#note', at: 9.0, dur: 0.5, fx: 'fade' },
  { sel: '.rt-sweep', at: 0, dur: 3.0, fx: 'draw', ease: 'lin' }, { sel: '.rt-ring', at: 2.6, dur: 0.6, fx: 'draw' },
]});
''', css='''.ch .base { position:absolute; left:20px; right:20px; bottom:70px; height:2px; background:#2a4a50; }
.ch .bar { position:absolute; bottom:72px; width:120px; border-radius:6px 6px 0 0; }
.ch .val { position:absolute; width:200px; text-align:center; font-size:44px; }
.ch .lab { position:absolute; bottom:18px; width:200px; text-align:center; font-size:26px; font-weight:700; white-space:nowrap; }
.sw { display:inline-block; width:22px; height:22px; border-radius:4px; vertical-align:-3px; margin-right:10px; }''')

# ═══ 14 結論與未來規劃（與海報「五、結果與討論」一致）═══════
concl = [('自動建圖', '開機後自主探索建圖，實測 <span class="num acid">6 / 6</span> 次建出完整地圖'),
         ('覆蓋規劃', 'PCA 主軸對齊＋cell 分解；6 次實測規劃，<span class="num acid">331</span> 段掃描線全在可走區內'),
         ('循跡執行', '自寫 A*＋直線循跡取代 move_base：受困 <span class="num acid">2 → 0</span> 次、覆蓋時間 <span class="num acid">10.1 → 3.2</span> 分、覆蓋率 <span class="num acid">82.7 → 90.9%</span>')]
future = [('A* 牆邊原地轉向仍偶有擦撞', '3 次實驗推估 3 次', '改善定位、加強轉向前的空間檢查'),
          ('只驗證單一長方形空間', 'L 形、多房間時 PCA 只給一個方向', '先分區，再各自規劃'),
          ('要先建完圖才能規劃', '大空間要等整張地圖建好', '邊建圖邊覆蓋')]
body = '''<p class="abs kicker" id="kick" style="left:96px; top:64px;">結論與未來規劃</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">完成了什麼，還差什麼</h1>
<p class="abs h1" style="left:96px; top:250px; font-size:36px; font-weight:900;">結論</p>
<div class="abs h1" style="left:96px; top:306px; width:820px; height:2px; background:#DAFF3C;"></div>
<p class="abs h2" style="left:1010px; top:250px; font-size:36px; font-weight:900;">限制與未來規劃</p>
<div class="abs h2" style="left:1010px; top:306px; width:820px; height:2px; background:#39E6FF;"></div>
'''
for k, (a, b) in enumerate(concl):
    y = 340 + k * 220
    body += (f'<div class="abs cc{k}" style="left:96px; top:{y}px; width:820px;"><p style="font-size:34px; font-weight:900;">{a}</p>'
             f'<p style="font-size:28px; line-height:1.5; margin-top:8px;">{b}</p></div>\n')
for k, (a, b, c) in enumerate(future):
    y = 340 + k * 220
    body += (f'<div class="abs ff{k}" style="left:1010px; top:{y}px; width:820px;"><p style="font-size:34px; font-weight:900;">{a}</p>'
             f'<p class="mute" style="font-size:26px; margin-top:6px;">{b}</p>'
             f'<p style="font-size:28px; margin-top:8px;"><span class="cyan">未來</span>　{c}</p></div>\n')
scene('14-conclusion', '14 結論與未來規劃', body, '''
Scene({ duration: 8, steps: [3.6, 6.8], tracks: [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.h1', at: 0.9, dur: 0.5, fx: 'fade' },
  { sel: '.cc0', at: 1.2, dur: 0.45, fx: 'up' }, { sel: '.cc1', at: 1.9, dur: 0.45, fx: 'up' }, { sel: '.cc2', at: 2.6, dur: 0.45, fx: 'up' },
  { sel: '.h2', at: 4.0, dur: 0.5, fx: 'fade' },
  { sel: '.ff0', at: 4.4, dur: 0.45, fx: 'up' }, { sel: '.ff1', at: 5.1, dur: 0.45, fx: 'up' }, { sel: '.ff2', at: 5.8, dur: 0.45, fx: 'up' },
]});
''')

# ═══ 15 實機展示（最後一頁；之後接實機影片）═══════════════
scene('15-demo', '15 實機展示', """
<div class="abs" id="line" style="left:0; top:538px; width:1920px; height:4px; background:#DAFF3C; box-shadow:0 0 22px #DAFF3C;"></div>
<p class="abs kicker" id="kick" style="left:0; top:250px; width:1920px; text-align:center;">接下來播放實車錄影</p>
<h1 class="abs k" id="t" style="left:0; top:300px; width:1920px; text-align:center; font-size:150px;">實機展示</h1>
<p class="abs lede" id="l1" style="left:0; top:580px; width:1920px; text-align:center;">開機 → 自動建圖 → 規劃 → <span class="acid">A* 覆蓋</span></p>
<p class="abs" id="n1" style="left:0; top:700px; width:1920px; text-align:center; font-size:40px; font-weight:700;">陳紹桓　陳柏屹</p>
<p class="abs mute" id="n2" style="left:0; top:770px; width:1920px; text-align:center; font-size:30px;">指導老師　卓世明</p>
<p class="abs mute" id="n3" style="left:0; top:860px; width:1920px; text-align:center; font-size:26px;">牛耕式演算法——以 TurtleBot3 實作</p>
""", """
Scene({ duration: 8, steps: [3.6], tracks: [
  { sel: '#line', at: 0, dur: 1.2, fx: 'grow', origin: 'center center' },
  { sel: '#kick', at: 0.6, dur: 0.5, fx: 'fade' },
  { sel: '#t', at: 1.0, dur: 0.7, fx: 'up', dy: 40 },
  { sel: '#l1', at: 1.7, dur: 0.5, fx: 'up' },
  { sel: '#n1', at: 2.2, dur: 0.5, fx: 'up' }, { sel: '#n2', at: 2.5, dur: 0.5, fx: 'up' },
  { sel: '#n3', at: 2.9, dur: 0.6, fx: 'fade' },
]});
""")


# ═══ index.html：全部場景依序播放 ═════════════════════════
idx = '''<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="UTF-8"><title>牛耕式演算法｜成果簡報</title>
<style>
  html,body{margin:0;height:100%;background:#050d10;color:#8FB3B8;font-family:"Noto Sans TC",sans-serif;overflow:hidden}
  iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
  #hud{position:absolute;right:16px;bottom:10px;margin:0;font-size:13px;opacity:.55;transition:opacity .4s}
  #hud.hide{opacity:0}
</style></head><body>
<iframe id="f" allow="fullscreen"></iframe>
<p id="hud"></p>
<script>
const S = __S__;
let i = 0, hideT = null;
// 記住上次看到第幾頁；頁數變少時（例如 14→13 頁）舊頁碼會超出範圍、畫面全黑，所以超出就從第 1 頁開始
try { const k = parseInt(localStorage.getItem('ccpp-scene'), 10); if (k >= 0 && k < S.length) i = k; } catch (e) {}
const f = document.getElementById('f'), hud = document.getElementById('hud');
function go(k, atEnd) {
  if (k < 0 || k >= S.length) return;
  i = k; try { localStorage.setItem('ccpp-scene', i); } catch (e) {}
  f.src = 'scenes/' + S[i][0] + '.html' + (atEnd ? '#end' : '');
  hud.textContent = (i + 1) + ' / ' + S.length + '　' + S[i][1] + '　｜ → 或點一下：下一段　← ：上一段　R：重播　F：全螢幕';
  hud.classList.remove('hide'); clearTimeout(hideT); hideT = setTimeout(() => hud.classList.add('hide'), 2500);
}
f.onload = () => f.contentWindow.focus();
addEventListener('message', e => {
  const c = e.data && e.data.cmd;
  if (c === 'next') go(i + 1);
  if (c === 'prev') go(i - 1, true);
  if (c === 'fs') { if (!document.fullscreenElement) document.documentElement.requestFullscreen(); else document.exitFullscreen(); }
});
// 焦點在外層時（例如剛切全螢幕），把按鍵轉給場景
addEventListener('keydown', e => { f.contentWindow.postMessage({ key: e.key }, '*'); e.preventDefault(); });
go(i);
</script></body></html>
'''.replace('__S__', json.dumps([[n, t] for n, t in SCENES], ensure_ascii=False))
with open(os.path.join(HERE, '..', 'index.html'), 'w', encoding='utf-8') as f:
    f.write(idx)
print(len(SCENES), 'scenes')
