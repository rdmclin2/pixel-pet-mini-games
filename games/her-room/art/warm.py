#!/usr/bin/env python3
"""开灯后整屋变暖：模型只把台灯附近画暖了，床一侧还是蓝月光。这里按到台灯的距离叠一层暖光（所有 lit 图用同一张光照图，所以状态之间一致）。
是「加光」不是「换色」：蓝通道压一点、红绿按画面明度加上去，蓝头发、蓝床单仍然是蓝的，只是被暖光照着；窗玻璃留冷色，窗外的雨和光斑不受影响。
post.py 对 lit 状态图、blink.py 对 lit 贴片调用 warm()（她的软遮罩 / 1.0）。参数改这里。
"""
import numpy as np, cv2
W, H = 1920, 1080
LAMP = (1566, 170)     # 台灯灯泡（世界坐标）
REACH = 1000.0          # 距离衰减的半径，越大暖光走得越远
FAR = 0.40             # 房间最远处的受光量（漫反射，不是 0：整屋都变）
NEAR = 1.0             # 灯边的受光量
GLASS = 0.04           # 窗玻璃的受光量
PANES = [[[262, 0], [712, 0], [712, 252], [322, 312]], [[742, 0], [1064, 0], [1062, 192], [742, 242]]]
def light_map():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot(x - LAMP[0], (y - LAMP[1]) * 1.1)
    k = FAR + (NEAR - FAR) / (1 + (d / REACH) ** 2 * 1.6)
    g = np.zeros((H, W), np.uint8)
    for p in PANES: cv2.fillPoly(g, [np.array(p, np.int32)], 255)
    g = cv2.GaussianBlur(g, (0, 0), 4).astype(np.float32) / 255
    return k * (1 - g) + GLASS * g
LIGHT = light_map()
SUBJECT = 0.88         # 她身上蓝色的部分（头发、裙子、尾巴）受光量打折，蓝发不被洗成灰紫；皮肤、围裙、遮罩里的桌面不是蓝的，照常受光，不留光环
def warm(im, subject=None):
    """im: BGR uint8，世界坐标 1920×1080 → 同尺寸 uint8。subject: 她的软遮罩（0–1，HxW）或一个常数（只处理她身上的贴片时用 1）"""
    a = im.astype(np.float32); b, g, r = a[..., 0], a[..., 1], a[..., 2]
    blue = np.clip((b - np.maximum(g, r)) / np.maximum(b, 1) * 2.0, 0, 1)
    k = LIGHT if subject is None else LIGHT * (1 - SUBJECT * subject * blue)
    v = 0.6 * a.max(axis=2) + 0.4 * (0.0722 * b + 0.7152 * g + 0.2126 * r)  # 这一点的明度
    out = np.dstack([b * (1 - 0.30 * k), g + v * 0.06 * k + 2 * k, r + v * 0.66 * k + 12 * k])
    return np.clip(out, 0, 255).round().astype(np.uint8)
