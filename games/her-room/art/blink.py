#!/usr/bin/env python3
"""眨眼差分：raw/<状态>-blink-{off,lit} 是「只把眼睛改成闭眼」的编辑图，这里只裁她眼睛那一小块，贴回 out/ 的状态图时不会有接缝。
用法：python3 blink.py → out/blink/*.png（带 alpha）、out/blink.json { <状态>: { off, lit, at: [x, y], size: [w, h] } }
EYES 是每个状态两只眼睛的外接框（人工标注，世界坐标），off / lit 共用同一块，所以开灯时两块贴片的位置不变。
"""
import json, os
import numpy as np, cv2
from warm import warm
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
W, H = 1920, 1080
EYES = json.load(open('blink-eyes.json'))
def raw(n): return f'raw/{n}.png' if os.path.exists(f'raw/{n}.png') else f'raw/{n}.webp'
def load(n): return cv2.resize(cv2.imread(raw(n), cv2.IMREAD_COLOR), (W, H), interpolation=cv2.INTER_AREA)
def shift_to(src, ref, box):
    """把编辑图平移对齐到状态图（只看脸这一块，模型重画时可能挪 1–3 px）"""
    x0, y0, x1, y1 = box; pad = 60
    b = (max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad))
    a = cv2.cvtColor(ref[b[1]:b[3], b[0]:b[2]], cv2.COLOR_BGR2GRAY).astype(np.float32)
    c = cv2.cvtColor(src[b[1]:b[3], b[0]:b[2]], cv2.COLOR_BGR2GRAY).astype(np.float32)
    M = np.eye(2, 3, dtype=np.float32)
    try: _, M = cv2.findTransformECC(a, c, M, cv2.MOTION_TRANSLATION, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5), None, 5)
    except cv2.error: pass
    return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
def main():
    os.makedirs('out/blink', exist_ok=True); index = {}
    for s, box in EYES.items():
        x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
        # alpha：框内是 1，四周 6 px 羽化到 0
        a = np.zeros((h, w), np.float32); a[6:h - 6, 6:w - 6] = 1; a = cv2.GaussianBlur(a, (0, 0), 3); a = np.clip(a * 1.0, 0, 1)
        e = {'at': [x0, y0], 'size': [w, h]}
        for k in ('off', 'lit'):
            ref = cv2.imread(f'out/dafeiyu-{s}-{k}.webp'); b = load(f'dafeiyu-{s}-blink-{k}')
            if k == 'lit': b = warm(b, subject=1.0)  # 和 post.py 烘焙进 lit 状态图的是同一层暖光
            b = shift_to(b, ref, box)
            cut = b[y0:y1, x0:x1].astype(np.float32)
            # 贴片的整体明暗对齐状态图（编辑时整张图可能轻微变色），只保留眼睛的改动
            rc = ref[y0:y1, x0:x1].astype(np.float32)
            ring = a < 0.5
            if ring.any(): cut = np.clip(cut + (rc[ring].mean(axis=0) - cut[ring].mean(axis=0)), 0, 255)
            rgba = np.dstack([cut, (a * 255)]).round().astype(np.uint8)
            cv2.imwrite(f'out/blink/{s}-{k}.png', rgba); e[k] = f'{s}-blink-{k}'
        index[s] = e
    json.dump(index, open('out/blink.json', 'w'), indent=1)
    print(json.dumps(index))
if __name__ == '__main__': main()
