#!/usr/bin/env python3
"""后处理：raw/*.png|webp → out/*.webp（1920×1080），并输出数值报告 out/post-report.json。
用法：python3 post.py   （需要 pillow numpy opencv-python-headless）

每张状态图和同一盏灯的底版（base-off / base-lit）合成：差异大的区域（她、被她动过的物件）留状态图，其余逐像素取底版，
窗户多边形内永远取底版。这样所有状态的静止部分逐像素相同，切状态时只有她在变（探针 README 给任务 D 的处理）。
报告：合成前后静止区域差异、她的遮罩范围（bbox，用来核对她在不在预期位置）、开灯前后的亮度和暖色。
"""
import json, os
import numpy as np, cv2
from warm import warm
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
W, H = 1920, 1080
STATES = ['idle', 'idle-lazy', 'phone', 'music', 'sleep', 'work', 'game', 'stand']
PANES = [[[262, 0], [712, 0], [712, 252], [322, 312]], [[742, 0], [1064, 0], [1062, 192], [742, 242]]]
# 判断「静止」的三块（她的任何姿势都不会到这里）；窗户另算
STATIC = {'window': (300, 0, 1060, 300), 'left-wall': (0, 0, 280, 420), 'shelf-wall': (1700, 0, 1920, 320)}
LAMP = (1300, 0, 1920, 700); FAR = (150, 380, 1250, 1080)
# 每个状态允许变化的范围：床上的状态只改床和她，书桌的状态只改书桌、椅子和她；范围外逐像素取底版
BED = (60, 230, 1400, 1080); DESK = (1130, 200, 1920, 1080)
ROI = {'idle': BED, 'idle-lazy': BED, 'phone': BED, 'music': BED, 'sleep': BED, 'work': DESK, 'game': DESK, 'stand': DESK}
# 暖光时要保护蓝色的范围。床上的状态她躺在蓝床单上，变化遮罩会把床单也算进去（留下蓝色色块），所以用人工标注的椭圆只框头发和身体
# [(cx, cy, rx, ry)…]，世界坐标；书桌的状态背景不是蓝的，直接用变化遮罩
HAIR = {'idle': [(800, 630, 200, 330)], 'idle-lazy': [(800, 640, 200, 330)], 'phone': [(470, 650, 170, 130), (720, 720, 230, 110)], 'music': [(560, 500, 210, 220)], 'sleep': [(530, 590, 230, 130)]}
THRESH = 20; MIN_AREA = 700; GROW = 19; FEATHER = 13
def raw(n): return f'raw/{n}.png' if os.path.exists(f'raw/{n}.png') else f'raw/{n}.webp'
def load(n): return cv2.resize(cv2.imread(raw(n), cv2.IMREAD_COLOR), (W, H), interpolation=cv2.INTER_AREA)
def crop(im, b): x0, y0, x1, y1 = b; return im[y0:y1, x0:x1].astype(np.float32)
def mad(a, b, box): return round(float(np.abs(crop(a, box) - crop(b, box)).mean()), 2)
def stats(im, box): c = crop(im, box); return {'luma': round(float(c.mean()), 1), 'warm(R-B)': round(float((c[..., 2] - c[..., 0]).mean()), 1)}
def window_mask():
    m = np.zeros((H, W), np.uint8)
    for p in PANES: cv2.fillPoly(m, [np.array(p, np.int32)], 255)
    return cv2.dilate(m, np.ones((15, 15), np.uint8))
WIN = window_mask()
def change_mask(im, base, roi):
    d = np.abs(cv2.GaussianBlur(im, (0, 0), 3).astype(np.float32) - cv2.GaussianBlur(base, (0, 0), 3).astype(np.float32)).max(axis=2)
    m = (d > THRESH).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= MIN_AREA: keep[lab == i] = 255
    keep[WIN > 0] = 0
    x0, y0, x1, y1 = roi; box = np.zeros_like(keep); box[y0:y1, x0:x1] = 255; keep = cv2.bitwise_and(keep, box)
    return cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (GROW, GROW)))
def subject_mask(state, hard):
    if state not in HAIR: return cv2.GaussianBlur(hard, (0, 0), FEATHER).astype(np.float32) / 255
    m = np.zeros((H, W), np.uint8)
    for cx, cy, rx, ry in HAIR[state]: cv2.ellipse(m, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)
    # 和变化遮罩取交集：头顶旁边的蓝墙没被她动过，不算她
    return cv2.GaussianBlur(cv2.bitwise_and(m, cv2.erode(hard, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (27, 27)))), (0, 0), 7).astype(np.float32) / 255
def composite(im, base, roi):
    hard = change_mask(im, base, roi)
    a = cv2.GaussianBlur(hard, (0, 0), FEATHER).astype(np.float32)[..., None] / 255
    a[WIN > 0] = 0
    return (im * a + base * (1 - a)).round().astype(np.uint8), hard
if __name__ == '__main__':
    os.makedirs('out', exist_ok=True)
    base = {k: load(f'dafeiyu-base-{k}') for k in ('off', 'lit')}
    warmed_base = warm(base['lit'])  # 整屋变暖（warm.py）：lit 图合成后统一烘焙，静止部分仍和底版逐像素相同
    cv2.imwrite('out/dafeiyu-base-off.webp', base['off'], [cv2.IMWRITE_WEBP_QUALITY, 88]); cv2.imwrite('out/dafeiyu-base-lit.webp', warmed_base, [cv2.IMWRITE_WEBP_QUALITY, 88])
    report = {'thresholds': {'diff': THRESH, 'minArea': MIN_AREA, 'grow': GROW, 'feather': FEATHER}, 'static_diff(0-255)': {}, 'mask': {}, 'lighting': {'base': {'lamp-area off': stats(base['off'], LAMP), 'lamp-area lit': stats(warmed_base, LAMP), 'bed-area off': stats(base['off'], FAR), 'bed-area lit': stats(warmed_base, FAR)}}}
    for s in STATES:
        for k in ('off', 'lit'):
            n = f'dafeiyu-{s}-{k}'
            if not os.path.exists(raw(n)): print('missing', n); continue
            im = load(n); out, hard = composite(im, base[k], ROI[s]); ref = base[k]
            if k == 'lit':
                sub = subject_mask(s, hard)
                out = warm(out, subject=sub); ref = warmed_base
            cv2.imwrite(f'out/{n}.webp', out, [cv2.IMWRITE_WEBP_QUALITY, 88])
            ys, xs = np.where(hard > 0)
            report['mask'][n] = {'percent': round(float((hard > 0).mean() * 100), 1), 'bbox': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None}
            report['static_diff(0-255)'][n] = {'vs': f'base-{k}', 'before': {r: mad(im, base[k], b) for r, b in STATIC.items()}, 'after': {r: mad(out, ref, b) for r, b in STATIC.items()}}
        if os.path.exists(f'out/dafeiyu-{s}-lit.webp') and os.path.exists(f'out/dafeiyu-{s}-off.webp'):
            off = cv2.imread(f'out/dafeiyu-{s}-off.webp'); lit = cv2.imread(f'out/dafeiyu-{s}-lit.webp')
            report['lighting'][s] = {'lamp-area off': stats(off, LAMP), 'lamp-area lit': stats(lit, LAMP), 'bed-area off': stats(off, FAR), 'bed-area lit': stats(lit, FAR)}
    json.dump(report, open('out/post-report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in report.items() if k != 'lighting'}, ensure_ascii=False)[:3000])
