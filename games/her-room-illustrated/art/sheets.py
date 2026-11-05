#!/usr/bin/env python3
"""拼验收对照图到 preview/：compare.jpg（参考帧 vs 小样）、character.jpg（角色一致性）、lighting.jpg（台灯关/开）、layout.jpg（房间布局对齐）。"""
import os, glob
from PIL import Image, ImageDraw, ImageFont
os.chdir(os.path.dirname(os.path.abspath(__file__)))
FONT = next(iter(glob.glob('/usr/share/fonts/**/NotoSansCJK*-Regular.tt*', recursive=True) + glob.glob('/usr/share/fonts/**/*wqy*.tt*', recursive=True) + glob.glob('/usr/share/fonts/**/*CJK*.tt*', recursive=True)), None)
def font(s): return ImageFont.truetype(FONT, s) if FONT else ImageFont.load_default()
REF = 'ref/'
O = lambda n: Image.open(f'out/{n}.webp').convert('RGB')
R = lambda n: Image.open(f'raw/{n}.png' if os.path.exists(f'raw/{n}.png') else f'raw/{n}.webp').convert('RGB')
def label(im, text, size=30):
    d = ImageDraw.Draw(im); f = font(size); b = d.textbbox((0, 0), text, font=f)
    d.rectangle((0, 0, b[2] + 24, b[3] + 16), fill=(0, 0, 0)); d.text((12, 6), text, font=f, fill=(255, 255, 255)); return im
def fit(im, w, h): return im.resize((w, h), Image.LANCZOS)
def grid(cells, cols, w, h, title=None, pad=12):
    rows = (len(cells) + cols - 1) // cols; top = 70 if title else 0
    out = Image.new('RGB', (cols * w + (cols + 1) * pad, rows * h + (rows + 1) * pad + top), (24, 26, 34))
    if title: ImageDraw.Draw(out).text((pad + 4, 14), title, font=font(38), fill=(255, 255, 255))
    for i, (im, t) in enumerate(cells):
        if im is None: continue
        c = label(fit(im, w, h), t); out.paste(c, (pad + (i % cols) * (w + pad), top + pad + (i // cols) * (h + pad)))
    return out
os.makedirs('preview', exist_ok=True)
sheet16 = Image.open(REF + 'ref-sheet16.webp').convert('RGB')  # 2560×1440，4×4 帧，每帧 640×360
tile = lambda r, c: sheet16.crop((c * 640, r * 360, c * 640 + 640, r * 360 + 360))
refs = {'phone': (Image.open(REF + 'ref-8.webp').convert('RGB'), '参考 ref-8（床上，手机亮着）'),
        'work': (tile(3, 1), '参考 16 帧总览第 14 帧（背对镜头用电脑，台灯开）'),
        'sleep': (tile(0, 3), '参考 16 帧总览第 4 帧（床上闭眼犯困）')}
names = {'phone': '趴在床上看手机', 'work': '背对镜头坐在桌前用电脑', 'sleep': '睡觉'}
W, H = 800, 450
cells = [(Image.open(REF + 'ref-52.webp').convert('RGB'), '参考 ref-52（房间全景，台灯开）'), (O('dafeiyu-base-off'), '小样 空房间底版 off'), (O('dafeiyu-base-lit'), '小样 空房间底版 lit')]
for st in ('phone', 'work', 'sleep'):
    cells += [refs[st], (O(f'dafeiyu-{st}-off'), f'小样 {names[st]} · 台灯关'), (O(f'dafeiyu-{st}-lit'), f'小样 {names[st]} · 台灯开')]
grid(cells, 3, W, H, '参考帧（左列） vs 大肥鱼插画小样（中：台灯关 / 右：台灯开）').save('preview/compare.jpg', quality=90)
# 角色一致性：设定图 + 各状态角色放大
sh = R('dafeiyu-sheet').convert('RGB')
CH = {'phone': (360, 300, 980, 830), 'work': (1330, 250, 1810, 890), 'sleep': (250, 410, 1210, 830)}
cells = [(sh.crop((0, 0, 2048, 1330)), '设定图：正 / 侧 / 背 三视图'), (sh.crop((0, 1330, 2048, 2048)), '设定图：睁眼 / 闭眼 / 犯懒 / 笑'),
         (Image.open(REF + 'ref8-character-crop.webp').convert('RGB'), '参考录屏里的大肥鱼（ref-8 放大）')]
for st in ('phone', 'work', 'sleep'):
    for k in ('off', 'lit'): cells.append((O(f'dafeiyu-{st}-{k}').crop(CH[st]), f'{names[st]} · {"台灯关" if k == "off" else "台灯开"}'))
cells.append((R('round1/dafeiyu-phone-off').convert('RGB').resize((1920, 1080)).crop(CH['phone']), '第 1 轮 看手机（手机背面朝镜头，已弃用）'))
grid(cells, 3, 720, 560, '角色一致性：设定图 vs 3 个状态里的大肥鱼（局部放大）').save('preview/character.jpg', quality=90)
# 台灯关 / 开
cells = []
for st in ('base', 'phone', 'work', 'sleep'):
    n = '空房间底版' if st == 'base' else names[st]
    cells += [(O(f'dafeiyu-{st}-off'), f'{n} · 台灯关（月光）'), (O(f'dafeiyu-{st}-lit'), f'{n} · 台灯开（暖光）')]
grid(cells, 2, 960, 540, '台灯关 / 开 两版：每个状态同构图，开灯后书桌一侧暖黄光晕，床和窗户保持蓝色月光').save('preview/lighting.jpg', quality=90)
# 房间布局：同一组参考线叠在底版和 3 个状态上
LINES = [((340, 0), (340, 1080)), ((1070, 0), (1070, 1080)), ((0, 380), (1920, 380)), ((1325, 0), (1325, 1080)), ((0, 245), (1920, 245)), ((0, 655), (1920, 655)), ((1480, 0), (1480, 1080))]
cells = []
for n, t in (('dafeiyu-base-off', '空房间底版'), ('dafeiyu-phone-off', names['phone']), ('dafeiyu-work-off', names['work']), ('dafeiyu-sleep-off', names['sleep'])):
    im = O(n); d = ImageDraw.Draw(im)
    for a, b in LINES: d.line([a, b], fill=(255, 60, 60), width=3)
    cells.append((im, f'{t}'))
grid(cells, 2, 960, 540, '房间布局一致性：四张图叠同一组红色参考线（窗框、窗台、床尾、书桌左边、台灯、椅子）').save('preview/layout.jpg', quality=90)
print('ok')
