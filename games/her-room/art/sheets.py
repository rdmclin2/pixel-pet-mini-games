#!/usr/bin/env python3
"""验收对照图和一致性数值：preview/states.jpg（每个状态台灯关 / 开）、character.jpg（设定图 vs 每个状态里的她）、layout.jpg（同一组参考线）、
compare.jpg（参考录屏 vs 成品）、out/consistency.json（发色色相、静止区域差异）。"""
import colorsys, glob, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
os.chdir(os.path.dirname(os.path.abspath(__file__)))
FONT = next(iter(glob.glob('/usr/share/fonts/**/NotoSansCJK*-Regular.tt*', recursive=True) + glob.glob('/usr/share/fonts/**/*wqy*.tt*', recursive=True) + glob.glob('/usr/share/fonts/**/*CJK*.tt*', recursive=True)), None)
def font(s): return ImageFont.truetype(FONT, s) if FONT else ImageFont.load_default()
O = lambda n: Image.open(f'out/{n}.webp').convert('RGB')
NAMES = {'idle': '发呆（坐在床边）', 'idle-lazy': '犯懒（坐在床边）', 'phone': '看手机（趴在床上）', 'music': '听音乐（靠在床头）', 'sleep': '睡觉（盖着被子）', 'work': '工作（背对镜头用电脑）', 'game': '打游戏（侧身握手柄）', 'stand': '起身（床和书桌之间的过渡）'}
# 她在每个状态里的范围（世界坐标，人工框）
CH = {'idle': (560, 340, 1000, 1030), 'idle-lazy': (560, 340, 1000, 1030), 'phone': (250, 300, 1000, 830), 'music': (250, 240, 940, 960), 'sleep': (250, 410, 1210, 830), 'work': (1330, 250, 1810, 890), 'game': (1270, 250, 1790, 890), 'stand': (1180, 480, 1680, 1060)}
def label(im, text, size=30):
    d = ImageDraw.Draw(im); f = font(size); b = d.textbbox((0, 0), text, font=f)
    d.rectangle((0, 0, b[2] + 24, b[3] + 16), fill=(0, 0, 0)); d.text((12, 6), text, font=f, fill=(255, 255, 255)); return im
def grid(cells, cols, w, h, title, pad=12):
    rows = (len(cells) + cols - 1) // cols; top = 70
    out = Image.new('RGB', (cols * w + (cols + 1) * pad, rows * h + (rows + 1) * pad + top), (24, 26, 34))
    ImageDraw.Draw(out).text((pad + 4, 14), title, font=font(38), fill=(255, 255, 255))
    for i, (im, t) in enumerate(cells):
        c = im.copy(); c.thumbnail((w, h), Image.LANCZOS); bg = Image.new('RGB', (w, h), (12, 14, 20)); bg.paste(c, ((w - c.width) // 2, (h - c.height) // 2))
        out.paste(label(bg, t), (pad + (i % cols) * (w + pad), top + pad + (i // cols) * (h + pad)))
    return out
os.makedirs('preview', exist_ok=True)
for f in ('lighting.jpg',):
    if os.path.exists(f'preview/{f}'): os.remove(f'preview/{f}')
# 每个状态 台灯关 / 开
cells = []
for s, n in NAMES.items(): cells += [(O(f'dafeiyu-{s}-off'), f'{n} · 台灯关'), (O(f'dafeiyu-{s}-lit'), f'{n} · 台灯开')]
grid(cells, 2, 960, 540, '每个状态 台灯关 / 开：姿势和构图专门画，房间不变').save('preview/states.jpg', quality=88)
# 角色
sh = Image.open('raw/dafeiyu-sheet.webp').convert('RGB')
cells = [(sh.crop((0, 0, 2048, 1330)), '设定图：正 / 侧 / 背'), (sh.crop((0, 1330, 2048, 2048)), '设定图：睁眼 / 闭眼 / 犯懒 / 笑')]
for s, n in NAMES.items():
    for k in ('off', 'lit'): cells.append((O(f'dafeiyu-{s}-{k}').crop(CH[s]), f'{n.split("（")[0]} · {"关" if k == "off" else "开"}'))
grid(cells, 4, 520, 480, '角色一致性：设定图 vs 每个状态里的大肥鱼').save('preview/character.jpg', quality=88)
# 布局
LINES = [((340, 0), (340, 1080)), ((1070, 0), (1070, 1080)), ((0, 380), (1920, 380)), ((1325, 0), (1325, 1080)), ((0, 245), (1920, 245)), ((0, 655), (1920, 655)), ((1480, 0), (1480, 1080))]
cells = []
for n, t in [('dafeiyu-base-off', '空房间底版')] + [(f'dafeiyu-{s}-off', v) for s, v in NAMES.items()]:
    im = O(n); d = ImageDraw.Draw(im)
    for a, b in LINES: d.line([a, b], fill=(255, 60, 60), width=3)
    cells.append((im, t))
grid(cells, 3, 640, 360, '房间布局一致性：九张图叠同一组红色参考线').save('preview/layout.jpg', quality=88)
# 参考录屏 vs 成品
sheet16 = Image.open('ref/ref-sheet16.webp').convert('RGB'); tile = lambda r, c: sheet16.crop((c * 640, r * 360, c * 640 + 640, r * 360 + 360))
pairs = [(Image.open('ref/ref-8.webp').convert('RGB'), '参考 ref-8', 'phone', 'off'), (tile(1, 1), '参考：坐在床上发呆', 'idle', 'off'), (tile(1, 2), '参考：开灯、犯懒', 'idle-lazy', 'lit'), (tile(0, 3), '参考：闭眼犯困', 'sleep', 'off'), (tile(3, 1), '参考：背对镜头用电脑', 'work', 'lit')]
cells = []
for r, t, s, k in pairs: cells += [(r, t), (O(f'dafeiyu-{s}-{k}'), f'成品 {NAMES[s]} · {"台灯开" if k == "lit" else "台灯关"}')]
grid(cells, 2, 800, 450, '参考录屏（左） vs 成品（右）').save('preview/compare.jpg', quality=88)
# 数值：她的发色（蓝色且够饱和的像素的色相中位数），和设定图比
def hue(im):
    a = np.asarray(im.convert('HSV')).reshape(-1, 3).astype(np.float32); h = a[:, 0] * 360 / 255; m = (a[:, 1] > 110) & (a[:, 2] > 50) & (h > 190) & (h < 270)
    return round(float(np.median(h[m])), 1), int(m.sum())
ref, _ = hue(sh.crop((0, 0, 2048, 1330)))
rep = json.load(open('out/post-report.json'))
res = {'sheetHue': ref, 'hairHue': {}, 'staticDiffAfter': {k: v['after'] for k, v in rep['static_diff(0-255)'].items()}}
for s in NAMES:
    for k in ('off', 'lit'):
        h, n = hue(O(f'dafeiyu-{s}-{k}').crop(CH[s])); res['hairHue'][f'{s}-{k}'] = {'hue': h, 'deltaFromSheet': round(h - ref, 1), 'pixels': n}
json.dump(res, open('out/consistency.json', 'w'), indent=1, ensure_ascii=False); print(json.dumps(res['hairHue'], ensure_ascii=False)[:1500]); print('sheet', ref, 'maxStatic', max(max(v.values()) for v in res['staticDiffAfter'].values()))

over = {k: v['deltaFromSheet'] for k, v in res['hairHue'].items() if abs(v['deltaFromSheet']) > 12}
print('hue over 12°:', over or 'none')

# 开灯帧和参考录屏的开灯帧并排（床上的状态对参考第 2 行第 3 张，书桌的状态对第 4 行第 2 张）
REF_BED, REF_DESK = tile(1, 2), tile(3, 1)
cells = []
for s, n in NAMES.items():
    desk = s in ('work', 'game', 'stand')
    cells += [(REF_DESK if desk else REF_BED, f'参考开灯帧（{"书桌" if desk else "床上"}）'), (O(f'dafeiyu-{s}-lit'), f'1.0.2 {n} · 台灯开')]
grid(cells, 4, 640, 360, '开灯帧 vs 参考录屏的开灯帧').save('preview/lit-vs-ref.jpg', quality=88)
# 逐状态的光照数值：床左半是否还是饱和的蓝、暖光是否从灯往外渐隐、她身边有没有光晕
BOX = {'bed-left': (120, 620, 520, 1000), 'bed-edge': (1200, 560, 1330, 720), 'desk': (1400, 230, 1800, 480), 'desk-wall': (1250, 60, 1450, 200), 'floor': (1400, 850, 1560, 1000), 'left-wall': (20, 120, 240, 400)}
def box_stats(im, b):
    c = np.asarray(im.crop(b)).astype(np.float32); r, g, bl = c[..., 0], c[..., 1], c[..., 2]
    mx, mn = c.max(axis=2), c.min(axis=2)
    return {'sat': round(float(((mx - mn) / np.maximum(mx, 1)).mean()), 2), 'R-B': round(float((r - bl).mean()), 1), 'luma': round(float(c.mean()), 1)}
import cv2
bo, bl = np.asarray(O('dafeiyu-base-off')).astype(np.float32), np.asarray(O('dafeiyu-base-lit')).astype(np.float32)
check = {}
for s, n in NAMES.items():
    off, lit = O(f'dafeiyu-{s}-off'), O(f'dafeiyu-{s}-lit')
    sub = (cv2.imread(f'out/subject-{s}.png', cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8)
    # 轮廓外 8–48 px 这一圈：开灯带来的变化和空房间的差多少。贴着她多出来的光晕或色块会让这个数变大
    ring = (cv2.dilate(sub, np.ones((97, 97), np.uint8)) > 0) & (cv2.dilate(sub, np.ones((17, 17), np.uint8)) == 0)
    halo = np.abs((np.asarray(lit).astype(np.float32) - np.asarray(off).astype(np.float32)) - (bl - bo)).max(axis=2)[ring]
    check[s] = {'lit': {k: box_stats(lit, b) for k, b in BOX.items()}, 'off-bed-left': box_stats(off, BOX['bed-left']), 'halo-ring-mean(0-255)': round(float(halo.mean()), 2), 'halo-ring-p99': round(float(np.percentile(halo, 99)), 1), 'hairHue-lit': res['hairHue'][f'{s}-lit']['hue'], 'hairHue-off': res['hairHue'][f'{s}-off']['hue']}
json.dump(check, open('preview/lighting-check.json', 'w'), indent=1, ensure_ascii=False)
for s, v in check.items(): print(s, 'bed-left sat', v['lit']['bed-left']['sat'], 'R-B', v['lit']['bed-left']['R-B'], '| bed-edge R-B', v['lit']['bed-edge']['R-B'], '| desk R-B', v['lit']['desk']['R-B'], 'wall', v['lit']['desk-wall']['R-B'], 'floor', v['lit']['floor']['R-B'], '| halo', v['halo-ring-mean(0-255)'], 'p99', v['halo-ring-p99'], '| hair', v['hairHue-off'], '→', v['hairHue-lit'])
# 商店封面：看手机 · 开灯的画面，裁成 16:10
c = O('dafeiyu-phone-lit'); h = 400; w = round(c.width * h / c.height); c = c.resize((w, h), Image.LANCZOS); x = (w - 640) // 2
c.crop((x, 0, x + 640, h)).save('../cover.webp', quality=86, method=6)
