#!/usr/bin/env python3
"""后处理：raw/*.png|webp → out/*.webp（1920×1080），并输出数值报告 out/post-report.json。
用法：python3 post.py   （需要 pillow numpy opencv-python-headless）

每张状态图和同一盏灯的底版（base-off / base-lit）合成：差异大的区域（她、被她动过的物件）留状态图，其余逐像素取底版，
窗户多边形内永远取底版。这样所有状态的静止部分逐像素相同，切状态时只有她在变（探针 README 给任务 D 的处理）。
报告：合成前后静止区域差异、她的遮罩范围（bbox，用来核对她在不在预期位置）、开灯前后的亮度和暖色。
"""
import json, os
import numpy as np, cv2
from warm import relight
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
# 她的范围（世界坐标，人工标注）：和「跟空房间的差异」取交集后用 GrabCut 收紧成她的轮廓（warm.py 用来加她迎光一侧的光）。床上的状态她躺在床单上，被她压皱、盖上的被子也有差异，所以用椭圆框住人；书桌的状态用矩形
BODY = {'idle': [(780, 660, 230, 370)], 'idle-lazy': [(780, 660, 230, 370)], 'phone': [(470, 650, 190, 150), (720, 720, 260, 130)], 'music': [(570, 580, 310, 360)], 'sleep': [(480, 590, 240, 130)]}
BODY_BOX = {'work': (1330, 250, 1810, 890), 'game': (1270, 250, 1790, 890), 'stand': (1180, 480, 1680, 1060)}
SUBJECT_DIFF = 14
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
def subject_mask(state, off, base_off):
    m = np.zeros((H, W), np.uint8)
    for cx, cy, rx, ry in BODY.get(state, []): cv2.ellipse(m, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)
    if state in BODY_BOX: x0, y0, x1, y1 = BODY_BOX[state]; m[y0:y1, x0:x1] = 255
    d = np.abs(cv2.GaussianBlur(off, (0, 0), 1.5).astype(np.float32) - cv2.GaussianBlur(base_off, (0, 0), 1.5).astype(np.float32)).max(axis=2)
    t = (d > SUBJECT_DIFF).astype(np.uint8) * 255
    t = cv2.morphologyEx(t, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    t = cv2.bitwise_and(t, m)
    # 床单上压出来的褶皱是细长的差异：开运算去掉，只留最大的一块（大致是她），再用 GrabCut 在这块附近收紧到真正的轮廓
    t = cv2.morphologyEx(t, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(t); keep = np.zeros_like(t)
    if n > 1: keep[lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))] = 255
    cnt, _ = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(keep, cnt, -1, 255, -1)
    k = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r))
    gc = np.full((H, W), cv2.GC_BGD, np.uint8)
    gc[cv2.dilate(keep, k(45)) > 0] = cv2.GC_PR_BGD; gc[keep > 0] = cv2.GC_PR_FGD; gc[cv2.erode(keep, k(55)) > 0] = cv2.GC_FGD
    cv2.setRNGSeed(1)
    cv2.grabCut(off, gc, None, np.zeros((1, 65)), np.zeros((1, 65)), 5, cv2.GC_INIT_WITH_MASK)
    fg = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)).astype(np.uint8) * 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, k(5))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg); keep = np.zeros_like(fg)
    if n > 1: keep[lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))] = 255
    return cv2.GaussianBlur(keep, (0, 0), 1.2).astype(np.float32) / 255
def composite(im, base, roi):
    hard = change_mask(im, base, roi)
    a = cv2.GaussianBlur(hard, (0, 0), FEATHER).astype(np.float32)[..., None] / 255
    a[WIN > 0] = 0
    return (im * a + base * (1 - a)).round().astype(np.uint8), hard
if __name__ == '__main__':
    os.makedirs('out', exist_ok=True)
    base = {k: load(f'dafeiyu-base-{k}') for k in ('off', 'lit')}
    lit_base = relight(base['off'], base['lit'])  # 开灯（warm.py）：所有 lit 图同一张受光图，静止部分仍和底版逐像素相同
    cv2.imwrite('out/dafeiyu-base-off.webp', base['off'], [cv2.IMWRITE_WEBP_QUALITY, 88]); cv2.imwrite('out/dafeiyu-base-lit.webp', lit_base, [cv2.IMWRITE_WEBP_QUALITY, 88])
    report = {'thresholds': {'diff': THRESH, 'minArea': MIN_AREA, 'grow': GROW, 'feather': FEATHER}, 'static_diff(0-255)': {}, 'mask': {}, 'lighting': {'base': {'lamp-area off': stats(base['off'], LAMP), 'lamp-area lit': stats(lit_base, LAMP), 'bed-area off': stats(base['off'], FAR), 'bed-area lit': stats(lit_base, FAR)}}}
    for s in STATES:
        n = f'dafeiyu-{s}-off'
        if not (os.path.exists(raw(n)) and os.path.exists(raw(f'dafeiyu-{s}-lit'))): print('missing', s); continue
        im = load(n); off, hard = composite(im, base['off'], ROI[s])
        lit_src, hard_lit = composite(load(f'dafeiyu-{s}-lit'), base['lit'], ROI[s])
        sub = subject_mask(s, off, base['off'])
        lit = relight(off, lit_src, sub, subject_lit=s in BODY_BOX)
        cv2.imwrite(f'out/{n}.webp', off, [cv2.IMWRITE_WEBP_QUALITY, 88])
        cv2.imwrite(f'out/dafeiyu-{s}-lit.webp', lit, [cv2.IMWRITE_WEBP_QUALITY, 88])
        cv2.imwrite(f'out/subject-{s}.png', (sub * 255).astype(np.uint8))
        for k, h, source, result, ref, b0 in (('off', hard, im, off, base['off'], base['off']), ('lit', hard_lit, load(f'dafeiyu-{s}-lit'), lit, lit_base, base['lit'])):
            ys, xs = np.where(h > 0); nm = f'dafeiyu-{s}-{k}'
            report['mask'][nm] = {'percent': round(float((h > 0).mean() * 100), 1), 'bbox': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None}
            report['static_diff(0-255)'][nm] = {'vs': f'base-{k}', 'before': {r: mad(source, b0, b) for r, b in STATIC.items()}, 'after': {r: mad(result, ref, b) for r, b in STATIC.items()}}
        report['lighting'][s] = {'lamp-area off': stats(off, LAMP), 'lamp-area lit': stats(lit, LAMP), 'bed-area off': stats(off, FAR), 'bed-area lit': stats(lit, FAR)}
    json.dump(report, open('out/post-report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in report.items() if k != 'lighting'}, ensure_ascii=False)[:3000])
