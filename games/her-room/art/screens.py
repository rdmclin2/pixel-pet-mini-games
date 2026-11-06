#!/usr/bin/env python3
"""屏幕四角（screens.json，人工标注，世界坐标 1920×1080，顺序 左上、右上、右下、左下）叠框核对图：preview/screens.jpg（每个带屏幕的状态 off / lit 各一格，放大）。"""
import json, os
from PIL import Image, ImageDraw
os.chdir(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open('screens.json'))['states']
cells = []
for key, screens in S.items():
    for sid, sc in screens.items():
        xs = [p[0] for p in sc['corners']]; ys = [p[1] for p in sc['corners']]
        box = (min(xs) - 50, min(ys) - 50, max(xs) + 50, max(ys) + 50)
        for k in ('off', 'lit'):
            c = Image.open(f'out/dafeiyu-{key}-{k}.webp').convert('RGB').crop(box); z = 480 / c.width
            c = c.resize((480, int(c.height * z)), Image.LANCZOS); d = ImageDraw.Draw(c)
            pts = [((x - box[0]) * z, (y - box[1]) * z) for x, y in sc['corners']]
            d.line(pts + pts[:1], fill=(255, 40, 80), width=2); d.text((4, 4), f'{key} {k} {sid}={sc["content"]}', fill=(255, 255, 0))
            cells.append(c)
H = max(c.height for c in cells); cols = 4
out = Image.new('RGB', (cols * 484, ((len(cells) + cols - 1) // cols) * (H + 4)), (20, 20, 28))
for i, c in enumerate(cells): out.paste(c, ((i % cols) * 484, (i // cols) * (H + 4)))
os.makedirs('preview', exist_ok=True); out.save('preview/screens.jpg', quality=88); print(out.size)
