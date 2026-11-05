#!/usr/bin/env python3
"""光斑位置：在底版窗户里找画好的灯（亮的连通块），输出 out/bokeh-spots.json [[x, y, r, warm]…]，引擎让它们在原位闪烁。"""
import json, os
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
from post import PANES, W, H
im = cv2.imread('out/dafeiyu-base-off.webp')
g = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (0, 0), 2)
m = np.zeros((H, W), np.uint8)
for p in PANES: cv2.fillPoly(m, [np.array(p, np.int32)], 255)
m = cv2.erode(m, np.ones((9, 9), np.uint8))
n, lab, st, c = cv2.connectedComponentsWithStats(((g > 165) & (m > 0)).astype(np.uint8))
spots = []
for i in range(1, n):
    a = st[i, cv2.CC_STAT_AREA]
    if a < 14: continue
    x, y = c[i]; b, gg, r = im[lab == i].mean(axis=0)
    spots.append([int(round(x)), int(round(y)), int(round(min(46, max(8, (a / 3.14) ** 0.5 * 2.6)))), 1 if r > b * 0.88 else 0])
spots = sorted(spots, key=lambda s: -s[2])[:60]
json.dump(spots, open('out/bokeh-spots.json', 'w'))
print(len(spots), spots[:12])
