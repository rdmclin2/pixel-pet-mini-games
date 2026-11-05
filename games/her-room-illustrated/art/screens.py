#!/usr/bin/env python3
"""屏幕区域四角（人工标注，1920×1080 世界坐标，顺序 左上、右上、右下、左下 = 屏幕内容的 左上/右上/右下/左下）。
写出 screens.json，并在 preview/screens-<state>-<off|lit>.jpg 画出四边形和坐标（放大裁图），用来人工核对四角是否贴住屏幕玻璃。
自动检测（高亮连通块）只框到屏幕里最亮的文档页 / 被手指挡住，所以改为人工标注 + 叠框核对。"""
import json, os
import numpy as np, cv2
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SCREENS = {
    'phone': [{'id': 'phone', 'content': 'clips', 'corners': [[514, 762], [560, 766], [537, 814], [480, 805]],
               'occluder': '左上角被她的右手食指挡住约 10×12 px（运行时用前景贴片盖回）'}],
    'work': [{'id': 'laptop', 'content': 'page', 'corners': [[1635, 298], [1792, 367], [1753, 473], [1597, 405]],
              'occluder': '左下角被她的头饰和鲸鳍耳挡住（左下角点按两条边延长线外推）'}],
    'sleep': [{'id': 'phone', 'content': 'lock', 'corners': [[330, 766], [361, 752], [414, 800], [382, 816]],
               'occluder': None}],
}
os.makedirs('preview', exist_ok=True)
for st, scr in SCREENS.items():
    for k in ('off', 'lit'):
        src = cv2.imread(f'out/dafeiyu-{st}-{k}.webp')
        pts = np.array([p for s in scr for p in s['corners']])
        pad = 70; x0, y0 = max(0, pts[:, 0].min() - pad), max(0, pts[:, 1].min() - pad)
        x1, y1 = min(1920, pts[:, 0].max() + pad), min(1080, pts[:, 1].max() + pad)
        sc = 900 // max(x1 - x0, y1 - y0) or 1
        c = cv2.resize(src[y0:y1, x0:x1], None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        for s in scr:
            q = np.array([[(x - x0) * sc, (y - y0) * sc] for x, y in s['corners']], np.int32)
            cv2.polylines(c, [q], True, (0, 255, 255), 2, cv2.LINE_AA)
            for i, ((x, y), (px, py)) in enumerate(zip(s['corners'], q)):
                cv2.circle(c, (int(px), int(py)), 6, (0, 0, 255), -1)
                cv2.putText(c, f'{"TL TR BR BL".split()[i]} ({x},{y})', (int(px) + 8, int(py) + (-10 if i < 2 else 24)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(c, f'{st}-{k} : {", ".join(s["id"] for s in scr)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(f'preview/screens-{st}-{k}.jpg', c, [cv2.IMWRITE_JPEG_QUALITY, 92])
json.dump({'world': [1920, 1080], 'order': ['TL', 'TR', 'BR', 'BL'], 'states': SCREENS,
           'closedLaptop': 'phone / sleep 状态里笔记本合着（无屏幕可贴），只有手机屏幕'}, open('screens.json', 'w'), indent=1, ensure_ascii=False)
print(open('screens.json').read())
