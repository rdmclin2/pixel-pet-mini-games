#!/usr/bin/env python3
"""开灯的光照（对照参考录屏的开灯帧）：床、被子和左半屋还是饱和的深蓝月光，暖黄光从台灯向外渐隐，铺在桌面、桌边墙面和地板上，落到床沿和她朝向台灯的一侧。
不是给整张图上色（那样蓝色会被洗成灰紫），而是在 off 图上「多点一盏灯」：
  - 床这边用物理打光：线性空间里 反射率 ≈ off / 月光颜色，再加上 反射率 × 灯色 × 受光量。蓝床单、蓝头发的反射率是蓝的，受暖光也还是蓝的、只是更亮；白围裙和皮肤才变暖。
  - 灯边（书桌、墙、地板）的颜色在 off 图里已经被月光吃掉了，用模型画的 lit 图，按受光量和 off 图渐变过渡；off / lit 原图逐像素对齐（平移 < 0.3 px），过渡处没有重影。
所有状态用同一张受光图、同一个公式，床和背景不按她抠遮罩，也就不会有抠图光晕；她的轮廓（post.py 用 GrabCut 求）只用来给她加迎光一侧的光，书桌状态下让她整个人用 lit 图保住蓝发和衣服的颜色。post.py 处理状态图，blink.py 处理贴片（relight 只用 off 那边）。参数都在这里。
"""
import numpy as np, cv2
W, H = 1920, 1080
LAMP = (1566, 170)                   # 台灯灯泡（世界坐标）
REACH = 610.0                        # 暖光的半径（受光量降到 1/e 的距离）
DOWN = 1.30                          # 灯光往下走得更远：纵向距离除以它（桌面和地板比墙受光多）
LAMP_RGB = np.array((1.0, 0.66, 0.30), np.float32)  # 灯色（线性）
MOON_RGB = np.array((0.26, 0.42, 1.0), np.float32)  # 月光颜色（线性）：off 图 ÷ 它 ≈ 反射率
GAIN = 2.3                           # 灯的亮度（物理打光这边）
TAIL = 0.13                          # 漫反射的尾巴：离灯很远的地方也受一点，整屋的光照跟着变；蓝色物体受了仍是蓝的
TAIL_REACH = 780.0
SHEEN = 0.80                         # 高光里反射率向明度靠多少（见 physical）
SHEEN_FROM, SHEEN_TO = 0.30, 0.60
MOON_CUT = 0.88                      # 灯光占主导时月光的蓝退多少
SIDE = 0.85                          # 她迎光那半边的侧光强度
RIM = 0.32                           # 她迎光一侧勾边光的强度
RIM_W = 9.0                         # 勾边光的宽度（px）
RIM_DIR = (1.0, -0.55)               # 床到台灯的大致方向（归一化前）
FLOOR = 1.1                          # lit 图的地板：模型只把灯下画亮了，往下按受光量提亮，暖光铺到椅子和床边的地板
LIT_FROM, LIT_TO = 0.05, 0.42        # 受光量在这段之间，从物理打光渐变到模型画的 lit 图
# 床和被子的范围（世界坐标，人工标注，羽化后用）：lit 图把这里画灰了，床上一律用物理打光；床沿仍然受暖光
# 桌边墙（1.0.2）：参考开灯帧里台灯把整面墙照成一大片桃色暖光，一直到窗帘边。范围是人工标注的墙面（从窗帘右边、床后、书桌后沿围起来），书桌、窗帘和床都不在里面，所以边界就是物体本来的轮廓，不会有光晕
WALL = np.array([[1262, 0], [1920, 0], [1920, 345], [1750, 240], [1640, 165], [1325, 250], [1252, 285], [1250, 420], [1172, 450], [1040, 352], [900, 372], [900, 300], [1060, 258], [1150, 246], [1208, 228], [1244, 214], [1252, 110]], np.int32)
WALL_RGB = np.array((1.0, 0.55, 0.23), np.float32)  # 墙上暖光（线性）
WALL_REACH = 600.0                   # 墙上暖光的半径（比桌面 REACH 宽：墙离灯近，又是浅色）
WALL_ADD, WALL_GAIN = 0.34, 0.12     # 叠加的暖光 / 原有明暗的提亮
WALL_FROM, WALL_TO = 880, 1190       # 从窗帘下方往床那边渐隐到 0，床头和左半屋不受影响
BED = np.array([[0, 470], [640, 245], [1110, 330], [1345, 560], [1350, 780], [760, 1080], [0, 1080]], np.int32)
PANES = [[[262, 0], [712, 0], [712, 252], [322, 312]], [[742, 0], [1064, 0], [1062, 192], [742, 242]]]
def _smooth(x, a, b): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def _maps():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot(x - LAMP[0], (y - LAMP[1]) / DOWN)
    k = np.exp(-(d / REACH) ** 2)
    glass = np.zeros((H, W), np.uint8)
    for p in PANES: cv2.fillPoly(glass, [np.array(p, np.int32)], 255)
    k = k * (1 - cv2.GaussianBlur(glass, (0, 0), 4).astype(np.float32) / 255)  # 窗玻璃外的雨夜不受灯影响
    bed = np.zeros((H, W), np.uint8); cv2.fillPoly(bed, [BED], 255)
    bed = cv2.GaussianBlur(bed, (0, 0), 22).astype(np.float32) / 255
    tail = TAIL * np.exp(-d / TAIL_REACH) * (1 - cv2.GaussianBlur(glass, (0, 0), 4).astype(np.float32) / 255)
    boost = 1 + FLOOR * _smooth(y, 520, 760) * _smooth(k, 0.03, 0.4)
    return k, tail, boost, _smooth(k, LIT_FROM, LIT_TO) * (1 - bed), x, y, d
LIGHT, TAIL_MAP, FLOOR_BOOST, FROM_LIT, X, Y, DIST = _maps()
def _wall():
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [WALL], 255)
    m = cv2.GaussianBlur(m, (0, 0), 1.5).astype(np.float32) / 255
    return m * np.exp(-(DIST / WALL_REACH) ** 2) * _smooth(X, WALL_FROM, WALL_TO)
WALL_MAP = _wall()
def lin(a): return np.power(a.astype(np.float32) / 255, 2.2)
def srgb(a): return np.clip(np.power(np.clip(a, 0, 1), 1 / 2.2) * 255, 0, 255).round().astype(np.uint8)
def physical(off, subject=None):
    """off（BGR uint8）→ 物理打光（线性 RGB float）。subject: 她的轮廓（HxW 0–1），只用来加她朝向台灯那一侧的光"""
    l = lin(off)[..., ::-1]
    albedo = np.clip(l / MOON_RGB, 0, 1)
    neutral = albedo.max(axis=2, keepdims=True)
    # 布料受强光时有漫射高光，不全是固有色：受光越多，反射率越接近它的明度，床沿和被子才读得出暖色（只算固有色，蓝床单只会变青）
    t = _smooth(LIGHT, SHEEN_FROM, SHEEN_TO)
    a = albedo + (neutral - albedo) * (SHEEN * t)[..., None]
    # 灯光占主导的地方，眼睛按灯光定白平衡，月光的蓝退下去（否则蓝 + 橙 = 灰）
    l = l * (1 - (MOON_CUT * t)[..., None] * np.array((0.0, 0.25, 1.0), np.float32))
    out = l + a * LAMP_RGB * ((LIGHT + TAIL_MAP) * GAIN)[..., None]
    if subject is not None:
        # 她朝向台灯的一侧：沿灯的方向，从身体中线到迎光边渐强（侧光），最边上再多一条勾边光。都在她的轮廓里面，不外溢
        n = np.hypot(*RIM_DIR); ux, uy = RIM_DIR[0] / n, RIM_DIR[1] / n
        along = X * ux + Y * uy
        ys, xs = np.where(subject > 0.5)
        lo, hi = np.percentile(along[ys, xs], (45, 99.5)) if len(xs) else (0, 1)
        side = _smooth(along, lo, hi) * subject
        M = np.float32([[1, 0, -ux * RIM_W], [0, 1, -uy * RIM_W]])
        rim = cv2.GaussianBlur(np.clip(subject - cv2.warpAffine(subject, M, (W, H)), 0, 1), (0, 0), 3) * subject
        # 侧光按固有色反射（蓝发只是更亮，皮肤和围裙才变暖），只有最边上那条勾边光读得出暖色
        out = out + (albedo * side[..., None] * SIDE + neutral * rim[..., None] * RIM) * LAMP_RGB
    return out
def wall_light(l, subject=None):
    """线性 RGB → 桌边墙加一层暖光。深色的东西（书架、书脊、线条）按明暗少加一点，所以细节还在；她挡在墙前面的地方不加"""
    w = WALL_MAP if subject is None else WALL_MAP * (1 - subject)
    keep = _smooth(l.max(axis=2), 0.015, 0.12)
    return l * (1 + (WALL_GAIN * w)[..., None]) + WALL_RGB * (WALL_ADD * w * keep)[..., None]
def relight(off, lit=None, subject=None, subject_lit=False):
    """off: 台灯关的图；lit: 同一构图模型画的开灯图（只在灯边用，贴片传 None）；subject: 她的轮廓；subject_lit: 她站在灯边（书桌的状态），她整个人都用 lit 图，蓝发和衣服保持原色。BGR uint8 → BGR uint8"""
    p = physical(off, None if subject_lit else subject)
    if lit is None: return srgb(p)[..., ::-1]
    # 模型的 lit 图只在灯边用，按受光量和物理打光过渡，所以暖光是从灯往外渐隐的
    a = np.maximum(FROM_LIT, subject) if subject_lit and subject is not None else FROM_LIT
    return srgb(wall_light(p * (1 - a[..., None]) + lin(lit)[..., ::-1] * FLOOR_BOOST[..., None] * a[..., None], subject))[..., ::-1]
