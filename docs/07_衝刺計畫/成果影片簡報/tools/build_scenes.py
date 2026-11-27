#!/usr/bin/env python3
"""
產生 scenes/NN-*.html（9 鏡）與 index.html。每鏡的版面、文字、時間軸都在這支檔案裡，改這裡再重跑。
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

# ═══ 04 問題一：為什麼要 PCA ═══════════════════════════
scene('04-p1-pca', '04 問題一：為什麼要 PCA', '''
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

# ═══ 05 問題二：掃描線穿過障礙 ═══════════════════════════
scene('05-p2-cross', '05 問題二：穿過障礙', '''
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

# ═══ 06 問題三：光達雜點 ═══════════════════════════════════
scene('06-p3-noise', '06 問題三：假障礙', '''
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

# ═══ 07 問題四：move_base → 自寫 A*＋直線循跡（含數據總表）═══════════════════════
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
scene('07-p4-dwa', '07 問題四：move_base → 自寫 A*＋循跡', body, '''
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

# ═══ 08 結論與未來規劃（與海報「五、結果與討論」一致）═══════
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
scene('08-conclusion', '08 結論與未來規劃', body, '''
Scene({ duration: 8, steps: [3.6, 6.8], tracks: [
  { sel: '#kick', at: 0.2, dur: 0.4, fx: 'up' }, { sel: '#t', at: 0.4, dur: 0.6, fx: 'up' },
  { sel: '.h1', at: 0.9, dur: 0.5, fx: 'fade' },
  { sel: '.cc0', at: 1.2, dur: 0.45, fx: 'up' }, { sel: '.cc1', at: 1.9, dur: 0.45, fx: 'up' }, { sel: '.cc2', at: 2.6, dur: 0.45, fx: 'up' },
  { sel: '.h2', at: 4.0, dur: 0.5, fx: 'fade' },
  { sel: '.ff0', at: 4.4, dur: 0.45, fx: 'up' }, { sel: '.ff1', at: 5.1, dur: 0.45, fx: 'up' }, { sel: '.ff2', at: 5.8, dur: 0.45, fx: 'up' },
]});
''')

# ═══ 09 實機展示（最後一頁；之後接實機影片）═══════════════
scene('09-demo', '09 實機展示', """
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
