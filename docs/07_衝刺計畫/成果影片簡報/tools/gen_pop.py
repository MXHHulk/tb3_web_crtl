#!/usr/bin/env python3
"""
普普漫畫風背景圖（2026-11-25 使用者指定風格）：放射尖角碎片、粗黑描邊、網點、RGB 錯位故障。
文字不畫在圖裡——HTML 疊在上層，匯出 PPTX 後仍可編輯。

用法：python tools/gen_pop.py   → ../assets/pop_*.png（1920×1080）
"""
import math
import os
import random

from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'assets')
W, H = 1920, 1080

MAG, YEL, CYA, VIO, RED = '#FF1F8E', '#FFE500', '#00C2FF', '#7A2BFF', '#FF4B1F'
LIME, BLK, WHT, PINK = '#C8F000', '#111111', '#FFFFFF', '#FF8AC8'


# ── 基本筆刷 ─────────────────────────────────────────
def shard(im, pts, fill, edge=10, inner=0, halftone=None):
    """多邊形碎片：填色＋（可選）網點＋粗黑描邊＋（可選）白色內描邊。"""
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=fill)
    if halftone:
        dot(im, pts, *halftone)
    if inner:
        d.line(pts + [pts[0]], fill=WHT, width=edge + inner * 2, joint='curve')
    d.line(pts + [pts[0]], fill=BLK, width=edge, joint='curve')


def dot(im, pts, color, step=14, r=4.2, angle=45):
    """在多邊形內鋪 45° 網點。"""
    mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    a = math.radians(angle)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = int(max(max(xs) - min(xs), max(ys) - min(ys)))
    for i in range(-span // step - 2, span // step + 2):
        for j in range(-span // step - 2, span // step + 2):
            u, v = i * step, j * step
            x = cx + u * math.cos(a) - v * math.sin(a)
            y = cy + u * math.sin(a) + v * math.cos(a)
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    im.paste(layer, (0, 0), ImageChops.multiply(layer.split()[3], mask))


def burst(cx, cy, r_out, r_in, n, rot=0, jitter=0.0, seed=0):
    """尖角爆炸星。"""
    rnd = random.Random(seed)
    pts = []
    for k in range(2 * n):
        r = r_out if k % 2 == 0 else r_in
        r *= 1 + rnd.uniform(-jitter, jitter)
        t = math.radians(rot) + k * math.pi / n
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def rays(im, cx, cy, colors, n=18, seed=1, edge=8):
    """從某點往畫面外放射的三角碎片，鋪滿底。"""
    rnd = random.Random(seed)
    R = 2600
    angles = sorted(rnd.uniform(0, 2 * math.pi) for _ in range(n))
    for k, a0 in enumerate(angles):
        a1 = angles[(k + 1) % n] + (2 * math.pi if k == n - 1 else 0)
        p0 = (cx + rnd.uniform(-40, 40), cy + rnd.uniform(-40, 40))
        pts = [p0, (cx + R * math.cos(a0), cy + R * math.sin(a0)),
               (cx + R * math.cos(a1), cy + R * math.sin(a1))]
        ht = (LIME, 16, 4.5) if colors[k % len(colors)] == YEL and k % 3 == 0 else None
        shard(im, pts, colors[k % len(colors)], edge=edge, halftone=ht)


def glitch(im, box, n=7, seed=3, max_shift=60):
    """在 box 範圍內做水平切片位移＋RGB 錯位。"""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        h = rnd.randint(6, 26)
        y = rnd.randint(y0, y1 - h)
        dx = rnd.randint(-max_shift, max_shift)
        strip = im.crop((x0, y, x1, y + h))
        r, g, b, *a = strip.split()
        r = ImageChops.offset(r, 10, 0); b = ImageChops.offset(b, -10, 0)
        strip = Image.merge(strip.mode, (r, g, b, *a))
        im.paste(strip, (x0 + dx, y))


def path_art(color=BLK, obstacle=MAG):
    """把 gen_figs 的真實規劃結果重新上色成漫畫線稿（粗黑線、洋紅障礙）。"""
    import numpy as np, sys
    sys.path.insert(0, HERE)
    import gen_figs as gf
    from coverage_planner import MARGIN, apply_safety_margin, plan
    data, ox, oy, _ = gf.room_map(gf.TILT, 2.2)
    free = (data == 0) & ~apply_safety_margin(data, MARGIN, gf.RES)
    r = plan(free, gf.RES, ox, oy)
    n = data.shape[0]; S = 1000 / (n * gf.RES)
    img = Image.new('RGBA', (1000, 1000), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    P = lambda p: ((p[0] - ox) * S, 1000 - (p[1] - oy) * S)
    # 房間外框（障礙格也一起畫）
    ys, xs = np.where(data == 100)
    room_cells = set(zip(ys.tolist(), xs.tolist()))
    for (yy, xx) in room_cells:
        x, y = xx * gf.RES * S, 1000 - (yy + 1) * gf.RES * S
        inside_obs = abs(xx - n / 2) < n * 0.25 and abs(yy - n / 2) < n * 0.25
        d.rectangle([x, y, x + gf.RES * S, y + gf.RES * S], fill=obstacle if inside_obs else color)
    wps, kinds = r['waypoints'], r['kind']
    stop = max(i for i, k in enumerate(kinds) if k == 'move') if r['perimeter'] else len(wps)
    for k in range(1, stop):
        p, q = P(wps[k - 1]), P(wps[k])
        if kinds[k] == 'line':
            d.line([p, q], fill=color, width=9, joint='curve')
    for (p, q) in r['sweeps']:
        d.line([P(p), P(q)], fill=color, width=9)
    ring = r['perimeter']
    if ring:
        d.line([P(p) for p in ring + ring[:1]], fill=CYA, width=6, joint='curve')
    return img


def cover():
    im = Image.new('RGBA', (W, H), WHT)
    rays(im, 1250, 470, [MAG, YEL, VIO, CYA, YEL, RED, MAG, WHT, YEL], n=19, seed=7)
    # 中央白色爆炸框（路徑圖舞台）
    shard(im, burst(1270, 520, 560, 410, 9, rot=-8, jitter=0.12, seed=2), WHT, edge=14, inner=0)
    art = path_art().resize((900, 900))
    im.paste(art, (820, 70), art)
    glitch(im, (900, 360, 1640, 700), n=3, seed=11, max_shift=28)
    # 左側黃色標題斜板＋黑色副標條
    shard(im, [(40, 250), (980, 200), (930, 560), (70, 600)], YEL, edge=14, inner=7,
          halftone=(LIME, 18, 5.5))
    shard(im, [(70, 610), (820, 585), (800, 700), (60, 720)], BLK, edge=10)
    shard(im, [(40, 830), (820, 808), (808, 1010), (50, 1030)], WHT, edge=10)
    # 角落裝飾：小爆星
    shard(im, burst(150, 120, 110, 50, 7, rot=10, seed=5), CYA, edge=10)
    im.convert('RGB').save(os.path.join(OUT, 'pop_cover.png'))


def data_page():
    im = Image.new('RGBA', (W, H), WHT)
    rays(im, 1500, 560, [VIO, MAG, CYA, VIO, YEL, MAG, VIO, CYA], n=17, seed=21)
    # 改善前：青色小碎片框
    shard(im, [(70, 290), (760, 250), (730, 640), (100, 600)], CYA, edge=12, inner=6,
          halftone=('#7FE3FF', 15, 4))
    # 改善後：黃色大爆炸星
    shard(im, burst(1340, 470, 430, 290, 11, rot=4, jitter=0.1, seed=9), YEL, edge=16, inner=8,
          halftone=(LIME, 18, 5.5))
    # 箭頭（洋紅粗箭）
    shard(im, [(720, 430), (850, 400), (845, 350), (960, 440), (860, 540), (858, 488), (730, 505)],
          MAG, edge=10)
    # 底部四格白色對話框
    for k in range(4):
        x = 60 + k * 455
        shard(im, [(x, 820), (x + 420, 808), (x + 410, 968), (x + 8, 978)], WHT, edge=9)
    # 標題黑條（最後畫，壓在爆炸星上面）
    shard(im, [(30, 40), (1560, 20), (1540, 170), (50, 190)], BLK, edge=10)
    glitch(im, (0, 700, 900, 780), n=2, seed=5, max_shift=60)
    im.convert('RGB').save(os.path.join(OUT, 'pop_data.png'))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    cover(); data_page()
    print('ok')
