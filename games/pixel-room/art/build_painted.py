#!/usr/bin/env python3
"""像素房间：大肥鱼房间的手绘底图（art/raw/dafeiyu-room-painted.webp，2048×1152）→ pack/。

  python3 games/pixel-room/art/build_painted.py   (needs Pillow)

家具都画在底图里，所以图集里的家具精灵是透明的占位（定点击框、标签和层次）。睡觉时盖住她的被子和床柱
从底图原样切出来，她就真的躺在画里的床上；小道具（手机、Z、音符……）沿用现有图集。
"""
import json, os
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); PACK = os.path.join(HERE, '..', 'pack')
WORLD = (1024, 576)
room = Image.open(os.path.join(HERE, 'raw', 'dafeiyu-room-painted.webp')).convert('RGB')
world = room.resize(WORLD, Image.LANCZOS).convert('RGBA')
old_idx = json.load(open(os.path.join(HERE, 'dafeiyu-pixel-props.json')))
old = Image.open(os.path.join(HERE, 'raw', 'dafeiyu-pixel-props.webp')).convert('RGBA')
def old_sprite(n, k=1.0):
    b = old_idx[n]; s = old.crop((b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
    return s if k == 1 else s.resize((max(1, round(s.width * k)), max(1, round(s.height * k))), Image.LANCZOS)
def cut(box, polys, feather=0):  # the painting's pixels inside polys (world coordinates), transparent elsewhere, cropped to box
    m = Image.new('L', (WORLD[0] * 2, WORLD[1] * 2), 0); d = ImageDraw.Draw(m)
    for p in polys: d.polygon([(x * 2, y * 2) for x, y in p], fill=255)
    m = m.resize(WORLD, Image.LANCZOS)
    if feather: m = m.filter(ImageFilter.GaussianBlur(feather))
    out = world.copy(); out.putalpha(m); return out.crop(box)
BED = (0, 60, 250, 460)
s = {}
for n, w, h in [('bed', 250, 400), ('nightstand', 64, 80), ('desk', 190, 163), ('record-cabinet', 147, 151), ('tv-cabinet', 180, 230), ('whale-beanbag', 180, 126)]:
    s[n] = Image.new('RGBA', (w, h), (0, 0, 0, 0))
# in front of her in bed: the near post and its bow
s['bed-front'] = cut(BED, [[(170, 60), (192, 60), (192, 462), (170, 462)], [(148, 372), (190, 372), (190, 416), (148, 416)]])
# over her: the painted pillows and cover, down to the foot of the bed
# (from the shoulder on: her head stays on the pillow, the pillows and cover hide the rest of her)
s['quilt'] = cut((10, 262, 250, 400), [[(150, 264), (247, 264), (248, 372), (215, 398), (12, 398), (12, 362), (112, 356), (136, 330)]], feather=2.5)
for n in ['z1', 'z2', 'note1', 'note2', 'note3', 'heart', 'star', 'sparkle', 'tv-1', 'tv-2', 'tv-3', 'tv-4', 'record-disc', 'monitor-bg', 'controller', 'phone-lit']:
    s[n] = old_sprite(n)
s['phone-on-table'] = old_sprite('phone-on-table', 0.6)
W = 1024; x = y = row = 2; idx = {}; atlas = Image.new('RGBA', (W, 1024), (0, 0, 0, 0))
for n in sorted(s, key=lambda k: -s[k].height):
    im = s[n]
    if x + im.width + 2 > W: x = 2; y += row + 2; row = 0
    atlas.paste(im, (x, y)); idx[n] = {'x': x, 'y': y, 'w': im.width, 'h': im.height}; x += im.width + 2; row = max(row, im.height)
atlas = atlas.crop((0, 0, W, y + row + 2))
room.save(os.path.join(PACK, 'dafeiyu-room.webp'), quality=88, method=6)
atlas.save(os.path.join(PACK, 'dafeiyu-atlas.webp'), lossless=True, method=6)
json.dump(idx, open(os.path.join(PACK, 'dafeiyu-sprites.json'), 'w'), indent=1, sort_keys=True)
print(atlas.size, len(idx))
