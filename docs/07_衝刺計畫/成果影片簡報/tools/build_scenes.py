#!/usr/bin/env python3
"""
產生 scenes/NN-*.html（14 鏡）與 index.html。每鏡的版面、文字、時間軸都在這支檔案裡，改這裡再重跑。
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
    (280, '我們寫的', 'acid', [('覆蓋規劃', 'PCA＋cell 分解', None), ('A* 導航', '繞障路線', None),
                             ('執行與循跡', '直線循跡・脫困・紀錄', None), ('手機控制台', '一鍵開始', None),
                             ('網頁監控', '即時地圖與進度', None)], '#F2F7F5'),
    (600, 'ROS 現成套件', 'mute', [('gmapping', '建圖（SLAM）', None), ('explore_lite', '找還沒看過的邊界', None),
                                  ('move_base', '建圖時導航・對照組 DWA', None)], '#8FB3B8'),
    (830, '硬體', 'mute', [('TurtleBot3', 'Burger 差速輪式機器人', None), ('LDS 光達', '360° 雷射測距', None)], '#8FB3B8'),
]
body = '''<p class="abs kicker" id="kick" style="left:96px; top:64px;">系統架構</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">系統分三層，最上層是我們自己寫的</h1>
'''
for li, (y, lab, cls, items, col) in enumerate(layers):
    body += f'<div class="abs rule L{li}" style="left:0; top:{y - 26}px; width:1920px; height:2px; background:{"#DAFF3C" if li == 0 else "#2a4a50"};"></div>\n'
    body += f'<p class="abs lab L{li}t {cls}" style="left:96px; top:{y}px; font-size:34px; font-weight:700;">{lab}</p>\n'
    step = 300 if len(items) > 4 else 380
    for k, (main, sub, n) in enumerate(items):
        x = 400 + k * step
        body += f'<div class="abs it L{li}i" style="left:{x}px; top:{y - 8}px; width:{step - 30}px;">'
        body += f'<p style="font-size:{52 if li == 0 else 44}px; font-weight:{900 if li == 0 else 700}; color:{col}; line-height:1.15;">{main}</p>'
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
scene('04-mapping', '04 自動建圖', '''
<img id="flip" class="abs" src="../assets/mapflip/00.png" style="left:60px; top:110px; width:960px; height:909px; image-rendering:pixelated;">
<p class="abs kicker" id="kick" style="left:1120px; top:120px;">自動建圖</p>
<h1 class="abs k" id="t" style="left:1120px; top:166px; font-size:68px; line-height:1.25; width:760px;">自己找路，<br>建完整張地圖</h1>
<p class="abs lede st" style="left:1120px; top:420px; width:740px;">按一下開始，車子自己去還沒看過的地方，<br>看完就停下、存好地圖。</p>
<div class="abs st" style="left:1120px; top:640px;"><p class="num acid" style="font-size:150px; line-height:1;"><span id="s1">6</span><span style="font-size:56px;"> / 6 次</span></p><p style="font-size:30px; font-weight:700;">實測都自己建出完整地圖</p></div>
''', '''
const N = 47, imgs = [];
for (let i = 0; i < N; i++) { const im = new Image(); im.src = `../assets/mapflip/${String(i).padStart(2, '0')}.png`; imgs.push(im); }
Scene({ duration: 10, steps: [6.2], tracks: [
  { sel: '#flip', at: 0.0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.3, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.5, dur: 0.6, fx: 'up' },
  { sel: '.st', at: 6.4, dur: 0.5, fx: 'up', stagger: 0.9 },
  { sel: '#s1', at: 7.3, dur: 1.0, fx: 'count', from: 0, to: 6 },
], onTime: (t, u) => {
  const i = Math.round(u.clamp((t - 0.6) / 5.4) * (N - 1));
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
<p class="abs lede" id="l2" style="left:96px; top:660px; width:700px;">沿地圖座標軸掃，掃描線會被斜牆切得<span class="pink">又短又碎</span>。</p>
''', '''
const d = SCENES.tilt, M = MapSVG;
document.getElementById('mapbox').innerHTML = M.open(d.bounds, 0.1, 'id="map" style="left:0; top:0; width:100%; height:100%;"')
  + M.cells(d.wall, d.res, 'wall') + d.axisLines.map(l => M.poly(l, 'axl')).join('') + M.close();
Scene({ duration: 10, steps: [3.2, 7.0], tracks: [
  { sel: '.wall', at: 0, dur: 0.6, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#l1', at: 1.3, dur: 0.5, fx: 'up' },
  { sel: '.axl', at: 4.0, dur: 0.5, fx: 'draw', stagger: 0.08 },
  { sel: '#l2', at: 4.6, dur: 0.5, fx: 'up' },
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
scene('07-cells', '07 cell 分解', '''
<p class="abs kicker" id="kick" style="left:96px; top:64px;">cell 分解</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">有障礙物，就把空間切成幾塊各自掃</h1>
<p class="abs lede" id="l1" style="left:96px; top:230px; width:1700px; font-size:34px;">障礙物前後，同一條掃描線會從一段變成兩段，那裡就是切點。每個 cell 內部來回掃，再由近到遠串起來。</p>
<div id="mapbox" class="abs" style="left:160px; top:340px; width:1600px; height:700px;"></div>
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
.mv { fill:none; stroke:#F2F7F5; stroke-width:.012; stroke-dasharray:.03 .03; opacity:.8; }
.cl { font-family:Bahnschrift, sans-serif; font-weight:700; font-size:.075px; }''')

# ═══ 08 安全邊距 ═════════════════════════════════════════
# 圖解：障礙物往外擴 13 cm（車身半寬 10.5＋半格 2.5）；車子中心只走擴完剩下的空地，車身就碰不到
scene('08-margin', '08 安全邊距', '''
<svg id="dia" class="abs" style="left:60px; top:150px; width:900px; height:840px;" viewBox="0 0 90 84"></svg>
<p class="abs kicker" id="kick" style="left:1040px; top:150px;">安全邊距</p>
<h1 class="abs k" id="t" style="left:1040px; top:196px; font-size:68px; line-height:1.25; width:820px;">障礙物往外擴 13 cm，<br>車子就撞不到</h1>
<p class="abs lede" id="l1" style="left:1040px; top:440px; width:820px;">車身半寬 <span class="num">10.5 cm</span>，<br>加上地圖格子邊緣的誤差 <span class="num">2.5 cm</span>，<br>合計 <span class="num acid">13 cm</span>。</p>
<p class="abs lede" id="l2" style="left:1040px; top:650px; width:820px;">路徑只規劃在擴完之後剩下的空地上：<br>車子中心走在線上，車身剛好碰不到。</p>
<div class="abs" id="d1" style="left:1040px; top:860px;"><p class="num acid" style="font-size:90px; line-height:1;">約 4 成</p><p class="mute" style="font-size:28px;">實測地圖的空地，扣掉安全邊距後車子中心能走的比例</p></div>
''', '''
// 單位：公分。障礙物 30×20 cm（粉），外擴 13 cm 的禁區（圓角＝往四周等距外擴），右側放一台車（官方車身：輪軸往後 10.5、往前 4.1、左右 10.5）
const g = [];
for (let x = 0; x <= 90; x += 5) g.push(`<line x1="${x}" y1="0" x2="${x}" y2="84" class="gd"/>`);
for (let y = 0; y <= 84; y += 5) g.push(`<line x1="0" y1="${y}" x2="90" y2="${y}" class="gd"/>`);
const bx = 15, by = 32, bw = 30, bh = 20, M = 13, cx = bx + bw + M, cy = 42;
document.getElementById('dia').innerHTML = g.join('')
  + `<rect class="zone" x="${bx - M}" y="${by - M}" width="${bw + 2 * M}" height="${bh + 2 * M}" rx="${M}"/>`
  + `<rect class="box" x="${bx}" y="${by}" width="${bw}" height="${bh}"/>`
  + `<g class="dim"><line x1="${bx + bw}" y1="${by - M - 5}" x2="${cx}" y2="${by - M - 5}" class="dl"/>`
  + `<line x1="${bx + bw}" y1="${by - M - 7}" x2="${bx + bw}" y2="${by - M - 3}" class="dl"/><line x1="${cx}" y1="${by - M - 7}" x2="${cx}" y2="${by - M - 3}" class="dl"/>`
  + `<text x="${bx + bw + M / 2}" y="${by - M - 7}" class="dt">13 cm</text></g>`
  + `<g class="car"><rect x="${cx - 10.5}" y="${cy - 4.1}" width="21" height="14.6" class="body"/>`
  + `<circle cx="${cx}" cy="${cy}" r="1.3" class="ctr"/><line x1="${cx}" y1="${cy}" x2="${cx}" y2="${cy - 8}" class="hd"/></g>`
  + `<text x="${bx + bw / 2}" y="${by + bh / 2 + 1.6}" class="bt">障礙物</text>`
  + `<text x="${cx + 13}" y="${cy + 1.5}" class="ct">車子中心</text>`;
Scene({ duration: 10, steps: [2.4, 5.6], tracks: [
  { sel: '.gd', at: 0, dur: 0.6, fx: 'fade', max: 1 },
  { sel: '.box', at: 0.4, dur: 0.4, fx: 'pop' }, { sel: '.bt', at: 0.6, dur: 0.4, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.zone', at: 2.6, dur: 1.0, fx: 'pop' }, { sel: '.dim', at: 3.4, dur: 0.5, fx: 'fade' },
  { sel: '#l1', at: 3.0, dur: 0.5, fx: 'up' },
  { sel: '.car', at: 5.8, dur: 0.6, fx: 'up', dy: 20 }, { sel: '.ct', at: 6.2, dur: 0.4, fx: 'fade' },
  { sel: '#l2', at: 6.2, dur: 0.5, fx: 'up' }, { sel: '#d1', at: 7.2, dur: 0.5, fx: 'up' },
]});
''', css='''.gd { stroke:rgba(120,170,178,.18); stroke-width:.15; }
.box { fill:#FF4FD8; }
.zone { fill:rgba(255,79,216,.22); stroke:#FF4FD8; stroke-width:.3; stroke-dasharray:1 .8; }
.body { fill:rgba(57,230,255,.18); stroke:#39E6FF; stroke-width:.45; }
.ctr { fill:#DAFF3C; } .hd { stroke:#DAFF3C; stroke-width:.5; }
.dl { stroke:#DAFF3C; stroke-width:.35; } .dt { fill:#DAFF3C; font-size:3.2px; font-weight:700; text-anchor:middle; font-family:Bahnschrift, sans-serif; }
.bt { fill:#08161b; font-size:3.4px; font-weight:900; text-anchor:middle; }
.ct { fill:#DAFF3C; font-size:3px; font-weight:700; }''')

# ═══ 09 問題一 ═══════════════════════════════════════════
scene('09-problem1', '09 問題一：穿過障礙', '''
<p class="abs kicker" id="kick" style="left:96px; top:64px;">問題一</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">掃描線直接穿過障礙物</h1>
<div id="mapbox" class="abs" style="left:40px; top:300px; width:1220px; height:640px;"></div>
<p class="abs mute" id="cap" style="left:96px; top:1000px; font-size:24px;"><span class="pink">粉：舊版的掃描線</span>　<span class="acid">黃：cell 分解後的路徑</span></p>
<div class="abs" id="old" style="left:1340px; top:330px; width:520px;">
  <p class="mute" style="font-size:28px; font-weight:700;">舊版</p>
  <p class="num pink" style="font-size:150px; line-height:1;">0%</p>
  <p style="font-size:28px; line-height:1.5;">有效覆蓋：5 條掃描線全部橫跨障礙，最嚴重一條 75% 落在障礙內</p>
</div>
<div class="abs" id="new" style="left:1340px; top:700px; width:520px;">
  <p class="mute" style="font-size:28px; font-weight:700;">cell 分解後</p>
  <p class="num acid" style="font-size:110px; line-height:1; margin-top:14px;">穿牆 0 次</p>
  <p class="mute" style="font-size:26px;">6 次實測規劃，331 段掃描線全部在可走區內</p>
</div>
''', '''
const d = SCENES.field, M = MapSVG;
document.getElementById('mapbox').innerHTML = M.open(d.bounds, 0.08, 'style="left:0; top:0; width:100%; height:100%;"')
  + M.cells(d.wall, d.res, 'wall') + `<g class="obsg">${M.cells(d.obs, d.res, 'obs')}</g>`
  + `<g id="oldg">${d.oldLines.map(l => M.poly(l, 'old')).join('')}</g>` + M.route(d.plan) + M.close();
Scene({ duration: 12, steps: [4.2, 10.6], tracks: [
  { sel: '.wall', at: 0, dur: 0.5, fx: 'fade' }, { sel: '.obsg', at: 0.3, dur: 0.4, fx: 'fade' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.old', at: 1.2, dur: 0.9, fx: 'draw', stagger: 0.25 },
  { sel: '#old', at: 2.6, dur: 0.5, fx: 'up' },
  { sel: '#oldg', at: 5.6, dur: 0.6, fx: 'fade', max: 0.25, ease: 'lin' },
  { sel: '.rt-sweep', at: 5.8, dur: 3.6, fx: 'draw', ease: 'lin' },
  { sel: '.rt-move', at: 9.2, dur: 0.4, fx: 'fade' },
  { sel: '.rt-ring', at: 9.4, dur: 0.9, fx: 'draw' },
  { sel: '#new', at: 7.0, dur: 0.5, fx: 'up' },
  { sel: '#cap', at: 1.6, dur: 0.6, fx: 'fade' },
], onTime: (t) => {
  // 舊線先完整亮著，5.6 s 後退成暗影
  const g = document.getElementById('oldg');
  if (t < 5.6) g.style.opacity = 1; else g.style.opacity = Math.max(0.25, 1 - (t - 5.6) / 0.6 * 0.75);
}});
''', css='.old { fill:none; stroke:#FF4FD8; stroke-width:.03; stroke-linecap:round; filter:url(#glow); }')

# ═══ 10 問題二 ═══════════════════════════════════════════
scene('10-problem2', '10 問題二：假障礙', '''
<svg id="dia" class="abs" style="left:100px; top:150px; width:760px; height:760px;" viewBox="0 0 60 60"></svg>
<p class="abs kicker" id="kick" style="left:960px; top:120px;">問題二</p>
<h1 class="abs k" id="t" style="left:960px; top:166px; font-size:72px; line-height:1.25; width:880px;">光達雜點，被當成障礙物</h1>
<p class="abs lede" id="l1" style="left:960px; top:380px; width:880px;">一顆 <span class="num">5 cm</span> 的雜點，四周各擴 <span class="num">13 cm</span>，<br>就變成 <span class="num pink">31 cm</span> 寬的禁區。</p>
<p class="abs lede" id="l2" style="left:960px; top:560px; width:880px;">把 3 格以下的小團塊過濾掉：</p>
<div class="abs" id="area" style="left:960px; top:650px;">
  <p class="num" style="font-size:130px; line-height:1;"><span class="mute" style="font-size:70px;">0.69 → </span><span id="a2" class="acid">0.82</span><span style="font-size:52px;"> m²</span></p>
  <p style="font-size:32px; font-weight:700; margin-top:8px;">可規劃面積 <span class="acid">+18%</span><span class="mute" style="font-size:26px; font-weight:500;">（實測 6 次中雜點最多的一次）</span></p>
</div>
''', '''
// 單位：公分。5 cm 雜點在正中央，往四周各擴 13 cm → 5 + 13 + 13 = 31 cm
const g = [];
for (let x = 0; x <= 60; x += 5) g.push(`<line x1="${x}" y1="0" x2="${x}" y2="60" class="gd"/>`);
for (let y = 0; y <= 60; y += 5) g.push(`<line x1="0" y1="${y}" x2="60" y2="${y}" class="gd"/>`);
const a = 27.5, M = 13, z0 = a - M, z1 = a + 5 + M, yd = z1 + 5;
const tick = x => `<line x1="${x}" y1="${yd - 1.5}" x2="${x}" y2="${yd + 1.5}" class="dl"/>`;
document.getElementById('dia').innerHTML = g.join('')
  + `<rect class="zone" x="${z0}" y="${z0}" width="${z1 - z0}" height="${z1 - z0}" rx="${M}"/>`
  + `<rect class="dotn" x="${a}" y="${a}" width="5" height="5"/>`
  + `<g class="dim"><line x1="${z0}" y1="${yd}" x2="${z1}" y2="${yd}" class="dl"/>${tick(z0)}${tick(a)}${tick(a + 5)}${tick(z1)}`
  + `<text x="${z0 + M / 2}" y="${yd - 2.2}" class="dt">13</text><text x="${a + 2.5}" y="${yd - 2.2}" class="dt w">5</text>`
  + `<text x="${a + 5 + M / 2}" y="${yd - 2.2}" class="dt">13</text>`
  + `<text x="${(z0 + z1) / 2}" y="${yd + 6}" class="dt big">= 31 cm</text></g>`;
Scene({ duration: 11, steps: [2.4, 6.0], tracks: [
  { sel: '.gd', at: 0, dur: 0.6, fx: 'fade', max: 1 },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.dotn', at: 1.2, dur: 0.4, fx: 'pop' },
  { sel: '.zone', at: 2.6, dur: 1.2, fx: 'pop' }, { sel: '.dim', at: 3.6, dur: 0.6, fx: 'fade' },
  { sel: '#l1', at: 3.0, dur: 0.5, fx: 'up' },
  { sel: '#l2', at: 6.2, dur: 0.5, fx: 'up' },
  { sel: '#area', at: 7.0, dur: 0.5, fx: 'up' },
  { sel: '#a2', at: 7.2, dur: 1.4, fx: 'count', from: 0.69, to: 0.82, dec: 2 },
], onTime: (t, u) => {
  // 過濾：6.2 s 起禁區與雜點一起淡掉
  const gone = u.clamp((t - 6.2) / 0.8);
  if (t > 6.2) ['.zone', '.dotn', '.dim'].forEach(q => document.querySelector(q).style.opacity = 1 - gone * 0.85);
}});
''', css='''.gd { stroke:rgba(120,170,178,.2); stroke-width:.12; }
.zone { fill:rgba(255,79,216,.25); stroke:#FF4FD8; stroke-width:.25; stroke-dasharray:.9 .7; }
.dotn { fill:#DAFF3C; }
.dl { stroke:#F2F7F5; stroke-width:.3; }
.dt { fill:#FF4FD8; font-size:2.8px; font-weight:700; text-anchor:middle; font-family:Bahnschrift, sans-serif; }
.dt.w { fill:#DAFF3C; } .dt.big { fill:#F2F7F5; font-size:3.6px; }''')

# ═══ 11 問題三 ═══════════════════════════════════════════
rows = [('覆蓋時間', '10.1 → 3.2 分'), ('全部跑完', '1 → 3 次'), ('覆蓋率（附帶）', '82.7 → 90.9%')]
body = '''<svg id="corner" class="abs"></svg>
<p class="vtext" style="top:760px;">DWA / A*</p>
<p class="abs kicker" id="kick" style="left:96px; top:76px;">問題三</p>
<h1 class="abs k" id="t" style="left:96px; top:120px; font-size:64px;">DWA 在牆邊卡住，覆蓋拖很久甚至停擺</h1>
<p class="abs lede" id="sub" style="left:96px; top:220px; font-size:34px;">改用自寫 <span class="acid">A* 規劃路線＋直線循跡</span>，同一場地各跑 3 次：</p>
<p class="abs num" id="ghost" style="left:76px; top:270px; font-size:420px; line-height:1.15; color:transparent; -webkit-text-stroke:3px rgba(143,179,184,.5); font-stretch:condensed;">2</p>
<p class="abs mute" id="bl" style="left:104px; top:650px; font-size:32px;">DWA 受困次數</p>
<div class="abs" id="after" style="left:760px; top:300px; width:1100px; text-align:right;">
  <p style="font-size:36px; font-weight:700;">A* 受困次數</p>
  <p class="num acid" style="font-size:372px; line-height:1; letter-spacing:-6px;"><span id="big">0</span></p>
  <p class="mute" style="font-size:30px; margin-top:12px;">3 次全部跑完，沒有一次卡住</p>
</div>
'''
for k, (a, b) in enumerate(rows):
    y = 730 + k * 68
    body += f'<div class="abs row" style="left:104px; top:{y}px; width:720px;"><p class="mute" style="position:absolute; top:10px; font-size:28px;">{a}</p><p class="num" style="position:absolute; left:256px; font-size:44px;">{b}</p></div>\n'
scene('11-problem3', '11 問題三：DWA → A*', body, '''
const d = SCENES.cover, M = MapSVG;
document.getElementById('corner').outerHTML = M.open(d.bounds, 0.1, 'id="corner" class="abs" style="left:1300px; top:-1120px; width:1560px; height:1560px; opacity:.55;"')
  + M.cells(d.wall, d.res, 'wall') + M.route(d.plan) + M.close();
Scene({ duration: 14, steps: [2.6, 5.5, 7.8], tracks: [
  { sel: '.rt-sweep', at: 0, dur: 3.0, fx: 'draw', ease: 'lin' }, { sel: '.rt-ring', at: 2.6, dur: 0.6, fx: 'draw' },
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#sub', at: 1.0, dur: 0.5, fx: 'up' },
  { sel: '#ghost', at: 1.6, dur: 0.8, fx: 'fade' }, { sel: '#bl', at: 1.9, dur: 0.5, fx: 'up' },
  { sel: '#after', at: 3.4, dur: 0.5, fx: 'up' },
  { sel: '#big', at: 3.5, dur: 1.2, fx: 'count', from: 2, to: 0 },
  { sel: '.row', at: 6.0, dur: 0.45, fx: 'up', stagger: 0.4 },
]});
''')

# ═══ 12 數據總表（A* vs DWA，正式實驗）═══════════════════
cols = [('方式', 400), ('全部跑完', 200), ('受困', 150), ('平均覆蓋率', 240), ('覆蓋時間', 360), ('碰牆（推估）', 230)]
data = [('自寫 A*＋直線循跡', '3 / 3', '0 次', '90.9%', '3.1～3.5 分', '3 次'),
        ('ROS 內建 DWA', '1 / 3', '2 次', '82.7%', '8.0～11.1 分', '2 次')]
body = """<p class="abs kicker" id="kick" style="left:96px; top:64px;">數據總表</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">同一場地、同一版本，各跑三次</h1>
<div class="abs rule" id="r0" style="left:96px; top:330px; width:1730px; height:3px; background:#DAFF3C;"></div>
"""
x = 96
for name, w in cols:
    body += f'<p class="abs mute th" style="left:{x}px; top:280px; width:{w}px; font-size:26px;">{name}</p>\n'
    x += w
for r, row in enumerate(data):
    y = 380 + r * 170
    x = 96
    for c, ((name, w), val) in enumerate(zip(cols, row)):
        hl = ' acid' if r == 0 and c > 0 else ''
        size = 40 if c == 0 else 52
        weight = 900 if c == 0 else 700
        color = '#F2F7F5' if r == 0 else '#8FB3B8'
        body += f'<p class="abs cell R{r}{hl}" style="left:{x}px; top:{y + (8 if c == 0 else 0)}px; width:{w - 20}px; font-size:{size}px; font-weight:{weight}; color:{color}; line-height:1.2;">{val}</p>\n'
        x += w
    body += f'<div class="abs rule R{r}r" style="left:96px; top:{y + 120}px; width:1730px; height:1px; background:#2a4a50;"></div>\n'
body += '<p class="abs lede" id="sum" style="left:96px; top:760px; width:1730px; font-size:38px;">A* 三次全部跑完、<span class="acid">零受困</span>，時間約 DWA 的<span class="acid">三分之一</span>；覆蓋率也高約 8 個百分點。</p>\n'
body += '<p class="abs src" id="src" style="left:96px; top:940px; width:1730px;">DWA 有 2 次受困提早結束，實際所需時間更長；碰牆為推估值</p>\n'
scene('12-table', '12 數據總表', body, """
Scene({ duration: 12, steps: [4.2, 6.6], tracks: [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '#r0', at: 1.0, dur: 0.6, fx: 'grow' }, { sel: '.th', at: 1.2, dur: 0.4, fx: 'fade', stagger: 0.06 },
  { sel: '.R1', at: 2.0, dur: 0.4, fx: 'up', stagger: 0.07 }, { sel: '.R1r', at: 2.3, dur: 0.5, fx: 'grow' },
  { sel: '.R0', at: 3.0, dur: 0.4, fx: 'up', stagger: 0.07 }, { sel: '.R0r', at: 3.3, dur: 0.5, fx: 'grow' },
  { sel: '#sum', at: 4.6, dur: 0.5, fx: 'up' }, { sel: '#src', at: 5.4, dur: 0.6, fx: 'fade' },
]});
""", css='.cell.acid { color:#DAFF3C !important; }')

# ═══ 13 限制與未來規劃 ═════════════════════════════════════
items = [('A* 在牆邊轉向，仍偶爾擦撞', '3 次實驗推估共碰觸 3 次；主因是定位跳動與轉向空間不足',
          '更準的定位（固定地圖＋AMCL）、轉向前的空間檢查再加強'),
         ('只驗證單一長方形空間、方形障礙物', '斜牆、L 形、多房間時 PCA 只能給一個方向',
          '先把空間分區，再各自規劃'),
         ('建完圖才規劃路徑', '大空間要等整張地圖建好才開始掃',
          '邊建圖邊覆蓋')]
body = '''<p class="abs kicker" id="kick" style="left:96px; top:64px;">限制與未來規劃</p>
<h1 class="abs k title" id="t" style="left:96px; top:108px;">還沒做好的地方</h1>
'''
for k, (a, b, c) in enumerate(items):
    y = 290 + k * 240
    body += f'<p class="abs num acid it{k}" style="left:96px; top:{y - 6}px; font-size:72px; line-height:1;">0{k + 1}</p>\n'
    body += f'<p class="abs it{k}" style="left:240px; top:{y}px; width:1600px; font-size:44px; font-weight:900;">{a}</p>\n'
    body += f'<p class="abs mute it{k}" style="left:240px; top:{y + 70}px; width:1600px; font-size:28px;">{b}</p>\n'
    body += f'<p class="abs it{k}" style="left:240px; top:{y + 118}px; width:1600px; font-size:30px;"><span class="cyan">未來</span>　{c}</p>\n'
scene('13-limits', '13 限制與未來規劃', body, '''
Scene({ duration: 8, steps: [2.0, 4.0, 6.0], tracks: [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.it0', at: 1.2, dur: 0.45, fx: 'up', stagger: 0.12 },
  { sel: '.it1', at: 3.2, dur: 0.45, fx: 'up', stagger: 0.12 },
  { sel: '.it2', at: 5.2, dur: 0.45, fx: 'up', stagger: 0.12 },
]});
''')

# ═══ 14 實機展示（最後一頁；之後接實機影片）═══════════════
scene('14-demo', '14 實機展示', """
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
let i = +(localStorage.getItem('ccpp-scene') || 0), hideT = null;
const f = document.getElementById('f'), hud = document.getElementById('hud');
function go(k, atEnd) {
  if (k < 0 || k >= S.length) return;
  i = k; localStorage.setItem('ccpp-scene', i);
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
