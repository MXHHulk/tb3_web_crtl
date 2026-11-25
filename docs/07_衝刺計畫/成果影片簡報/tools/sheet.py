"""把 frames/ 裡每鏡的某一格拼成總覽：python tools/sheet.py [end|mid] → frames/_overview_<which>.png"""
import glob, os, sys
from PIL import Image
which = sys.argv[1] if len(sys.argv) > 1 else 'end'
by = {}
for f in glob.glob('frames/*@*.png'):
    n, t = os.path.basename(f)[:-4].split('@'); by.setdefault(n, []).append((float(t), f))
items = [sorted(v)[-1 if which == 'end' else 0][1] for k, v in sorted(by.items())]
W, H, g, cols = 640, 360, 10, 3
rows = (len(items) + cols - 1) // cols
s = Image.new('RGB', (cols * W + (cols + 1) * g, rows * H + (rows + 1) * g), (40, 40, 40))
for i, f in enumerate(items):
    r, c = divmod(i, cols); s.paste(Image.open(f).convert('RGB').resize((W, H)), (g + c * (W + g), g + r * (H + g)))
s.save(f'frames/_overview_{which}.png'); print(len(items))
