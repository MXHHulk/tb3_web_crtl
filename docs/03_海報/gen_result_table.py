#!/usr/bin/env python3
"""
產生海報「四、成果展示」的 A* vs DWA 對照圖（640×340 海報 px）（三個並排小圖：受困、平均覆蓋率、覆蓋時間）。
Canva 回傳超過 100k 字元會截斷、拿不到新文字元素 ID，故以圖片放入。

形式：emphasis（本專題 A* 用強調藍、對照組 DWA 用灰），三個量級不同的指標各自一張小圖、各自從 0 起算（不共用軸）。
配色：強調藍 #2A6FB0（海報深藍同色系；dataviz validate_palette：亮度帶、彩度、對白底 ≥ 3:1 皆 PASS）；
      DWA 灰對比不足 3:1 → 每個數值直接標字（relief rule）。
數據來源：experiments/robot/data/experiments/20261126-1345/trials.csv（v1.2.0，第 1～6 輪 done／error 列；作廢列見該實驗 log.txt）
用法：python docs/03_海報/gen_result_table.py      → 輸出 docs/03_海報/result_table.png
"""
import csv
import os
import statistics as st

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TRIALS = os.path.join(REPO, 'experiments', 'robot', 'data', 'experiments', '20261126-1345', 'trials.csv')
OUT = os.path.join(HERE, 'result_table.png')

rows = [r for r in csv.DictReader(open(TRIALS, encoding='utf-8-sig'))
        if int(r['trial']) <= 6 and r['coverage_state'] in ('done', 'error')]
A = sorted([r for r in rows if r['nav_mode'] == 'astar'], key=lambda r: int(r['trial']))
D = sorted([r for r in rows if r['nav_mode'] == 'movebase'], key=lambda r: int(r['trial']))
assert len(A) == 3 and len(D) == 3

stuck = {'A': [int(r['n_stuck']) > 0 for r in A], 'D': [int(r['n_stuck']) > 0 for r in D]}
cov = {'A': st.mean(float(r['actual_cov']) for r in A) * 100, 'D': st.mean(float(r['actual_cov']) for r in D) * 100}
tmin = {k: [float(r['exec_s']) / 60 for r in g] for k, g in (('A', A), ('D', D))}
print('受困', stuck, '覆蓋', cov, '時間', tmin)

S = 3                                   # 海報上 640×340 px → 圖 1920×1020
W, H = 640 * S, 340 * S
ACC, GRAY = (42, 111, 176), (166, 166, 160)            # #2A6FB0、淡化灰
NAVY, INK, MUTED, RULE = (31, 78, 121), (31, 41, 51), (107, 114, 128), (214, 220, 228)
FB, FR = 'C:/Windows/Fonts/msjhbd.ttc', 'C:/Windows/Fonts/msjh.ttc'
F = lambda f, px: ImageFont.truetype(f, int(px * S))
f_title, f_panel, f_val, f_lab, f_note = F(FB, 28), F(FB, 21), F(FB, 22), F(FR, 18), F(FR, 15)

img = Image.new('RGB', (W, H), 'white')
d = ImageDraw.Draw(img)
p = lambda v: int(v * S)


def cross(cx, cy, q, w=3):
    d.line([cx - q, cy - q, cx + q, cy + q], fill=INK, width=p(w))
    d.line([cx - q, cy + q, cx + q, cy - q], fill=INK, width=p(w))


# 第一行：標題＋說明；第二行：圖例（≥ 2 個系列一定有圖例）
d.text((p(0), p(0)), 'A* 與 DWA 實測對照', font=f_title, fill=NAVY)
d.text((p(300), p(14)), '同一場地、同一版本，各 3 次', font=f_note, fill=MUTED, anchor='lm')
lx = p(0)
for col, name in ((ACC, 'A*＋直線循跡（本專題）'), (GRAY, 'DWA（ROS move_base）')):
    d.rounded_rectangle([lx, p(48), lx + p(15), p(63)], radius=p(3), fill=col)
    d.text((lx + p(21), p(56)), name, font=f_lab, fill=INK, anchor='lm')
    lx += p(21) + d.textlength(name, font=f_lab) + p(24)

PW, GAP = 196, 26                       # 每格寬、間距（海報 px）
PT, TOPB, BOT = 88, 150, 288            # 小圖標題 y、長條可達最高 y、基線 y
for k, t in enumerate(('受困次數', '平均覆蓋率', '覆蓋時間（分）')):
    x0 = k * (PW + GAP)
    d.text((p(x0), p(PT)), t, font=f_panel, fill=NAVY)
    d.line([p(x0), p(PT + 32), p(x0 + PW - 10), p(PT + 32)], fill=RULE, width=p(1.5))

# ── ① 受困：每次實驗一個點（實心＝跑完、空心＋✕＝受困停止） ──
for j, (key, col, name) in enumerate((('A', ACC, 'A*'), ('D', GRAY, 'DWA'))):
    cy = p(160 + j * 64)
    d.text((p(0), cy), name, font=f_val, fill=INK, anchor='lm')
    for i, s_ in enumerate(stuck[key]):
        cx, r = p(74 + i * 27), p(10)
        if s_:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=p(3), fill='white')
            cross(cx, cy, p(5))
        else:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    d.text((p(194), cy), f"{sum(stuck[key])} 次", font=f_val, fill=INK, anchor="rm")
ly = p(BOT + 18)
d.ellipse([p(0), ly - p(6), p(12), ly + p(6)], fill=MUTED)
d.text((p(17), ly), '跑完', font=f_note, fill=MUTED, anchor='lm')
d.ellipse([p(62), ly - p(6), p(74), ly + p(6)], outline=MUTED, width=p(2))
cross(p(68), ly, p(3), 2)
d.text((p(79), ly), '受困停止', font=f_note, fill=MUTED, anchor='lm')


def bars(x0, vals, vmax, fmt, ranges=None):
    """單軸長條：0 起算、上端 4 px 圓角，兩條之間留白；數值直接標在長條（或範圍線）上方。"""
    base, top = p(BOT), p(TOPB)
    bw, gap = 54, 22
    d.line([p(x0), base, p(x0 + PW - 10), base], fill=RULE, width=p(1.5))
    for i, (key, col) in enumerate((('A', ACC), ('D', GRAY))):
        bx = x0 + 24 + i * (bw + gap)
        h = (base - top) * vals[key] / vmax
        d.rounded_rectangle([p(bx), base - h, p(bx + bw), base], radius=p(4), fill=col,
                            corners=(True, True, False, False))
        ytxt = base - h
        if ranges:
            lo, hi = min(ranges[key]), max(ranges[key])
            ylo, yhi = base - (base - top) * lo / vmax, base - (base - top) * hi / vmax
            cx = p(bx + bw / 2)
            for yy in (ylo, yhi):
                d.line([cx - p(7), yy, cx + p(7), yy], fill=INK, width=p(2))
            d.line([cx, ylo, cx, yhi], fill=INK, width=p(2))
            ytxt = min(ytxt, yhi)
        d.text((p(bx + bw / 2), ytxt - p(5)), fmt(vals[key]), font=f_val, fill=INK, anchor='md')
        d.text((p(bx + bw / 2), base + p(4)), 'A*' if key == 'A' else 'DWA', font=f_lab, fill=INK, anchor='mt')


bars(PW + GAP, cov, 100, lambda v: f'{v:.1f}%')
mean_t = {k: st.mean(v) for k, v in tmin.items()}
bars(2 * (PW + GAP), mean_t, 12, lambda v: f'{v:.1f}', ranges=tmin)
d.text((p(0), p(BOT + 42)), '長條＝平均，細線＝最短～最長；DWA 有 2 次受困提早結束，實際所需時間更長',
       font=f_note, fill=MUTED, anchor='lm')

img.save(OUT)
print('→', OUT, img.size)
