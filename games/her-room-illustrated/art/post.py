#!/usr/bin/env python3
"""小样后处理：raw/*.png|webp → out/*.webp（1920×1080），并输出对齐 / 静止区域差异 / 光照变化 的数值报告。
用法：python3 post.py   （需要 pillow numpy opencv-python-headless）
- 每张状态图用 OpenCV ECC（仿射）对齐到 base-off；对齐前后都报告静止区域（窗户、床头墙、书架墙）平均像素差。
- off vs lit：报告「台灯区」和「床/窗区」的平均亮度与暖色（R-B）变化，证明开灯改变了光照、远处保持月光。
"""
import json, os, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
W, H = 1920, 1080
STATES = ['phone', 'work', 'sleep']
# 1920×1080 世界坐标下的区域
STATIC = {'window': (300, 0, 1060, 300), 'left-wall': (0, 0, 280, 420), 'shelf-wall': (1700, 0, 1920, 320)}
LAMP = (1300, 0, 1920, 700)      # 书桌、台灯、书架
FAR = (150, 380, 1250, 1080)     # 床
def load(n):
    im = cv2.imread(f'raw/{n}.png' if os.path.exists(f'raw/{n}.png') else f'raw/{n}.webp', cv2.IMREAD_COLOR)
    return cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA)
def crop(im, b): x0, y0, x1, y1 = b; return im[y0:y1, x0:x1].astype(np.float32)
def mad(a, b, box): return float(np.abs(crop(a, box) - crop(b, box)).mean())
def align(src, ref):
    g1 = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY).astype(np.float32); g2 = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY).astype(np.float32)
    s = 0.25; a = cv2.resize(g1, None, fx=s, fy=s); b = cv2.resize(g2, None, fx=s, fy=s)
    M = np.eye(2, 3, dtype=np.float32)
    try:
        _, M = cv2.findTransformECC(a, b, M, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    except cv2.error: return src, None
    M[:, 2] /= s
    return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE), M
def stats(im, box):
    c = crop(im, box); return {'luma': round(float(c.mean()), 1), 'warm(R-B)': round(float((c[..., 2] - c[..., 0]).mean()), 1)}
os.makedirs('out', exist_ok=True)
base = {k: load(f'dafeiyu-base-{k}') for k in ('off', 'lit')}
report = {'static_diff_vs_base_off(0-255)': {}, 'lighting': {}}
for k, im in base.items(): cv2.imwrite(f'out/dafeiyu-base-{k}.webp', im, [cv2.IMWRITE_WEBP_QUALITY, 88])
cv2.imwrite('out/dafeiyu-sheet.webp', cv2.imread('raw/dafeiyu-sheet.png' if os.path.exists('raw/dafeiyu-sheet.png') else 'raw/dafeiyu-sheet.webp'), [cv2.IMWRITE_WEBP_QUALITY, 90])
report['lighting']['base'] = {'lamp-area off': stats(base['off'], LAMP), 'lamp-area lit': stats(base['lit'], LAMP), 'bed-area off': stats(base['off'], FAR), 'bed-area lit': stats(base['lit'], FAR)}
for st in STATES:
    for k in ('off', 'lit'):
        n = f'dafeiyu-{st}-{k}'
        if not (os.path.exists(f'raw/{n}.png') or os.path.exists(f'raw/{n}.webp')): continue
        im = load(n); ref = base[k]
        before = {r: round(mad(im, ref, b), 2) for r, b in STATIC.items()}
        al, M = align(im, ref)
        after = {r: round(mad(al, ref, b), 2) for r, b in STATIC.items()}
        use = al if M is not None and np.mean(list(after.values())) <= np.mean(list(before.values())) else im
        cv2.imwrite(f'out/{n}.webp', use, [cv2.IMWRITE_WEBP_QUALITY, 88])
        report['static_diff_vs_base_off(0-255)'][n] = {'vs': f'base-{k}', 'raw': before, 'aligned': after, 'used': 'aligned' if use is al else 'raw'}
    if os.path.exists(f'out/dafeiyu-{st}-lit.webp'):
        off = cv2.imread(f'out/dafeiyu-{st}-off.webp'); lit = cv2.imread(f'out/dafeiyu-{st}-lit.webp')
        report['lighting'][st] = {'lamp-area off': stats(off, LAMP), 'lamp-area lit': stats(lit, LAMP), 'bed-area off': stats(off, FAR), 'bed-area lit': stats(lit, FAR)}
json.dump(report, open('out/post-report.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(report, indent=1, ensure_ascii=False))
