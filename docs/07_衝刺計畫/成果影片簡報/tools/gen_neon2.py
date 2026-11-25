#!/usr/bin/env python3
"""
霓虹夜景風 v3（2026-11-25 第三次調整：「太 AI、太單板、太多幾何框」）
- 拿掉所有面板框、斜線條、網點、無關弧線
- 封面：真實規劃路徑放大出血，當成穿過畫面的光帶，標題疊在上面
- 數據頁：71% 退成描邊淡影（裝飾，真正的數字在 HTML 可編輯文字裡），一段路徑光帶從右上角切入
- 底加細顆粒，少一點螢幕感
配色沿用 gen_neon.py（已定案）。

用法：python tools/gen_neon2.py   → ../assets/neo3_*.png
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_neon import ACID, BG0, BG1, CYAN, H, OUT, W, glow, path_neon, rgba, tag  # noqa: E402

FONT_NUM = 'C:/Windows/Fonts/bahnschrift.ttf'


def base(cx, cy, seed=0):
    y, x = np.mgrid[0:H, 0:W]
    d = np.hypot((x - cx * W) / W, (y - cy * H) / H) / 0.8
    t = np.clip(d, 0, 1)[..., None]
    img = np.array(BG1) * (1 - t) + np.array(BG0) * t
    img += np.random.default_rng(seed).normal(0, 4.0, img.shape[:2])[..., None]   # 細顆粒
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def shade(im, box, alpha=200, blur=90):
    """在文字區後面墊一塊柔邊暗影，讓疊在光帶上的字讀得清楚。"""
    m = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(m).rectangle(box, fill=(*BG0, alpha))
    im.alpha_composite(m.filter(ImageFilter.GaussianBlur(blur)))


def vtext(im, text, x, y, size=17, color=CYAN, alpha=150, spacing=6):
    """直排小字（裝飾性的英文標記），轉 90° 貼在邊上。"""
    f = ImageFont.truetype(FONT_NUM, size)
    f.set_variation_by_name(b'SemiBold')
    w = int(sum(f.getlength(c) + spacing for c in text)) + 10
    t = Image.new('RGBA', (w, size + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    cx = 0
    for c in text:
        d.text((cx, 0), c, font=f, fill=rgba(color, alpha))
        cx += f.getlength(c) + spacing
    im.alpha_composite(t.rotate(90, expand=True), (x, y))


def trail(im, x0, y0, length, rows, gap, color=ACID, width=6, alpha=255):
    """一段牛耕光帶：rows 條平行線＋U 形轉彎，從 (x0, y0) 往右延伸出畫面。"""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = []
    for k in range(rows):
        y = y0 + k * gap
        a, b = (x0, x0 + length) if k % 2 == 0 else (x0 + length, x0)
        pts += [(a, y), (b, y)]
    d.line(pts, fill=rgba(color, alpha), width=width, joint='curve')
    glow(im, layer, radius=9, strength=1)


def cover():
    im = base(0.75, 0.45, seed=1)
    art, _ = path_neon(1560)
    im.alpha_composite(art, (700, -250))
    shade(im, (0, 150, 900, 1000), alpha=215, blur=110)
    vtext(im, 'BOUSTROPHEDON  COVERAGE  /  TURTLEBOT3', 30, 300)
    tag(im, 92, 556, 470, 64)
    im.convert('RGB').save(os.path.join(OUT, 'neo3_cover.png'))


def data_page():
    im = base(0.7, 0.45, seed=2)
    # 右上角切入封面那張真實路徑的一角（同一套光帶語彙，不是另畫的框）
    art, _ = path_neon(1560)
    faded = art.copy()
    faded.putalpha(faded.getchannel('A').point(lambda v: int(v * 0.55)))
    im.alpha_composite(faded, (1300, -1120))
    # 71% 描邊淡影
    f = ImageFont.truetype(FONT_NUM, 420)
    f.set_variation_by_name(b'Bold Condensed')
    ghost = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ghost).text((70, 250), '71%', font=f, fill=(0, 0, 0, 0),
                               stroke_width=3, stroke_fill=rgba((143, 179, 184), 120))
    im.alpha_composite(ghost)
    vtext(im, 'BEFORE  /  AFTER', 30, 760)
    im.convert('RGB').save(os.path.join(OUT, 'neo3_data.png'))


if __name__ == '__main__':
    cover(); data_page()
    print('ok')
