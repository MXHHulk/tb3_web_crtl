#!/usr/bin/env python3
"""
霓虹夜景風背景圖（2026-11-25 第二次調整）：深色安靜底，霓虹細線／斜切標籤／警示斜線只放邊角，
發光只給內容本身（規劃路徑、關鍵數字的框）。普普漫畫風的網點只留一小塊點綴。
文字不畫進圖裡，HTML 疊在上層，匯出 PPTX 後可編輯。

用法：python tools/gen_neon.py   → ../assets/neon_*.png（1920×1080）
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'assets')
W, H = 1920, 1080

BG0, BG1 = (8, 22, 27), (14, 44, 50)          # 深青綠底（邊緣→中心）
ACID = (218, 255, 60)                           # 霓虹黃綠：只給主角
CYAN = (57, 230, 255)
PINK = (255, 79, 216)
DIM = (58, 96, 104)                             # 次要框線
INK = (8, 14, 16)


def rgba(c, a=255):
    return (*c, a)


# ── 底 ──────────────────────────────────────────────
def base(cx=0.62, cy=0.5):
    """徑向暗角＋5 cm 佔據格網（呼應 SLAM 地圖），都壓得很淡。"""
    y, x = np.mgrid[0:H, 0:W]
    d = np.hypot((x - cx * W) / W, (y - cy * H) / H) / 0.75
    t = np.clip(d, 0, 1)[..., None]
    img = (np.array(BG1) * (1 - t) + np.array(BG0) * t).astype(np.uint8)
    im = Image.fromarray(img, 'RGB').convert('RGBA')
    grid = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    for gx in range(0, W, 48):
        g.line([(gx, 0), (gx, H)], fill=rgba(CYAN, 10), width=1)
    for gy in range(0, H, 48):
        g.line([(0, gy), (W, gy)], fill=rgba(CYAN, 10), width=1)
    im.alpha_composite(grid)
    return im


def glow(im, layer, radius=10, strength=2):
    """把 layer 模糊後疊兩次當光暈，再疊上清楚的本體。"""
    halo = layer.filter(ImageFilter.GaussianBlur(radius))
    for _ in range(strength):
        im.alpha_composite(halo)
    im.alpha_composite(layer)


def arc(layer, box, start, end, color, width=3):
    ImageDraw.Draw(layer).arc(box, start, end, fill=rgba(color, 230), width=width)


def chamfer(x0, y0, x1, y1, c=34):
    """左上、右下切角的面板（賽博介面常見的不對稱切角）。"""
    return [(x0 + c, y0), (x1, y0), (x1, y1 - c), (x1 - c, y1), (x0, y1), (x0, y0 + c)]


def panel(im, box, edge, edge_w=3, fill=(10, 30, 35, 215), glow_edge=False, c=34):
    pts = chamfer(*box, c=c)
    body = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(body).polygon(pts, fill=fill)
    im.alpha_composite(body)
    line = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(line).line(pts + [pts[0]], fill=rgba(edge), width=edge_w, joint='curve')
    if glow_edge:
        glow(im, line, radius=8, strength=1)
    else:
        im.alpha_composite(line)


def tag(im, x, y, w, h, color=ACID):
    """斜切標籤底（平行四邊形），文字由 HTML 疊上。"""
    s = h * 0.38
    ImageDraw.Draw(im).polygon([(x + s, y), (x + w + s, y), (x + w, y + h), (x, y + h)], fill=rgba(color))


def hatch(im, x, y, n=7, h=22, step=13, color=ACID, alpha=255):
    """警示斜線條 //////"""
    d = ImageDraw.Draw(im)
    for k in range(n):
        x0 = x + k * step
        d.polygon([(x0 + 8, y), (x0 + 14, y), (x0 + 6, y + h), (x0, y + h)], fill=rgba(color, alpha))


def halftone_corner(im, x0, y0, x1, y1, color=CYAN, step=16, rmax=3.2, toward=None):
    """普普風網點，只留一角點綴：越往 toward 那個角點越大（預設右下角）。"""
    d = ImageDraw.Draw(im)
    cx, cy = toward or (x1, y1)
    for yy in range(y0, y1, step):
        for xx in range(x0, x1, step):
            t = 1 - math.hypot((xx - cx) / (x1 - x0), (yy - cy) / (y1 - y0)) / 1.2
            r = rmax * max(0.0, t)
            if r > 0.6:
                d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=rgba(color, 70))


# ── 主角：真實規劃路徑（霓虹線稿） ────────────────────
def path_neon(size=820):
    sys.path.insert(0, HERE)
    import gen_figs as gf
    from coverage_planner import MARGIN, apply_safety_margin, plan
    data, ox, oy, _ = gf.room_map(gf.TILT, 2.2)
    free = (data == 0) & ~apply_safety_margin(data, MARGIN, gf.RES)
    r = plan(free, gf.RES, ox, oy)
    n = data.shape[0]
    S = size / (n * gf.RES)
    P = lambda p: ((p[0] - ox) * S, size - (p[1] - oy) * S)

    walls = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    wd = ImageDraw.Draw(walls)
    ys, xs = np.where(data == 100)
    cell = gf.RES * S
    for yy, xx in zip(ys.tolist(), xs.tolist()):
        x, y = xx * cell, size - (yy + 1) * cell
        is_obs = abs(xx - n / 2) < n * 0.25 and abs(yy - n / 2) < n * 0.25
        wd.rectangle([x + 1, y + 1, x + cell - 1, y + cell - 1],
                     fill=rgba(PINK, 255) if is_obs else rgba((120, 170, 178), 200))

    lines = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    wps, kinds = r['waypoints'], r['kind']
    stop = max(i for i, k in enumerate(kinds) if k == 'move') if r['perimeter'] else len(wps)
    for k in range(1, stop):
        if kinds[k] == 'line':
            ld.line([P(wps[k - 1]), P(wps[k])], fill=rgba(ACID), width=6, joint='curve')
    for p, q in r['sweeps']:
        ld.line([P(p), P(q)], fill=rgba(ACID), width=6)
    ring = r['perimeter']
    if ring:
        ld.line([P(p) for p in ring + ring[:1]], fill=rgba(CYAN), width=4, joint='curve')

    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.alpha_composite(walls)
    glow(out, lines, radius=7, strength=1)
    return out, len(r['cells'])


# ── 頁面 ────────────────────────────────────────────
def cover():
    im = base(0.68, 0.5)
    # 邊角霓虹弧線（只在畫面外緣，不穿過文字區）
    deco = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    arc(deco, (-760, 960, 560, 1760), 300, 345, ACID, 3)
    glow(im, deco, radius=9, strength=2)
    # 路徑圖面板
    panel(im, (1010, 110, 1840, 960), DIM, edge_w=2)
    art, _ = path_neon(780)
    im.alpha_composite(art, (1035, 145))
    # 標題下的黃色斜切標籤＋警示線
    tag(im, 92, 556, 470, 64)
    hatch(im, 600, 577, n=8)
    # 左上小標籤（細框）
    ImageDraw.Draw(im).line([(96, 236), (380, 236)], fill=rgba(CYAN, 200), width=2)
    halftone_corner(im, 0, 0, 380, 170, CYAN, toward=(0, 0))
    im.convert('RGB').save(os.path.join(OUT, 'neon_cover.png'))


def data_page():
    im = base(0.6, 0.55)
    deco = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    arc(deco, (1640, -560, 2440, 190), 110, 175, CYAN, 3)
    glow(im, deco, radius=9, strength=2)
    # 標題前的「問題三」斜切標籤
    tag(im, 96, 74, 168, 56)
    hatch(im, 1700, 92, n=8)
    # 改善前（暗框）／改善後（發光框）
    panel(im, (96, 268, 760, 690), DIM, edge_w=2)
    panel(im, (900, 228, 1824, 730), ACID, edge_w=3, glow_edge=True, fill=(12, 36, 38, 230))
    # 中間箭頭：三個 chevron
    d = ImageDraw.Draw(im)
    for k in range(3):
        x = 790 + k * 30
        d.line([(x, 440), (x + 22, 479), (x, 518)], fill=rgba(ACID, 110 + 60 * k), width=6, joint='curve')
    # 底部四格只用一條細頂線
    for k in range(4):
        x = 96 + k * 436
        d.line([(x, 812), (x + 380, 812)], fill=rgba(CYAN, 170), width=2)
    halftone_corner(im, 1560, 900, 1920, 1080, ACID)
    im.convert('RGB').save(os.path.join(OUT, 'neon_data.png'))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    cover(); data_page()
    print('ok')
