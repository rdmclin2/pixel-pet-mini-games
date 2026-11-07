#!/usr/bin/env python3
"""原图 → 壁纸包。raw/*.png（GPT Image 原图，2048×1152）→ pack/ 的图层、预览，以及商店的 cover.webp、screenshots/。
用法（在仓库根目录）：uv run --with pillow --with numpy python3 games/seaside-terrace/art/post.py
- 天空（sky-day / sky-night）：整张不透明，缩放到画布 2560×1440。
- 露台（terrace-day / terrace-night）、云（clouds）：原图里天空是纯品红 #FF00FF，抠成透明，边缘去品红溢色。
- 云：抠出来的云带放到画布上方（天空那一段），按整朵云等间距重排、左右两边自然透明，两份并排横向循环时没有接缝（1.0.0 在 x=160 / 2400 硬切了两朵云，见 CHANGELOG 1.0.1）。
- 商店图：按 manifest 的图层顺序合成；黄昏图套一层暖色（应用里 sky.tint 做的事），雨图加几道雨丝。
画面里没有她：她由应用的 wallpaper@1 引擎用角色包的动作画在露台上（pet.area）。
"""
import json, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
RAW, PACK, SHOTS = os.path.join(HERE, 'raw'), os.path.join(GAME, 'pack'), os.path.join(GAME, 'screenshots')
W, H = 2560, 1440
os.makedirs(SHOTS, exist_ok=True)


def raw(name):
    for ext in ('.png', '.webp'):
        p = os.path.join(RAW, name + ext)
        if os.path.exists(p):
            return Image.open(p).convert('RGB')
    raise SystemExit(f'missing raw/{name}.png (python3 art/generate.py {name})')


def key_magenta(img, glow=None):
    """纯品红 → 透明。品红度 m = min(R, B) − G − |R − B| / 2：高于 150 全透明，低于 50 不动，中间渐变（灯泡的光晕混着品红，
    整圈抠掉，夜里的光由引擎的 fx.lights 画）。半透明处先按「前景 × α + 品红 × (1 − α)」把品红减掉；剩下还偏品红的像素
    （透明玻璃灯泡透出来的底色）把 R、B 压到 G + 8，变回白 / 灰。"""
    a = np.asarray(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = np.minimum(r, b) - g - np.abs(r - b) * 0.5
    alpha = 1.0 - np.clip((m - 50.0) / 100.0, 0.0, 1.0)
    k = np.maximum(alpha, 0.05)
    for c, bg in ((0, 255.0), (1, 0.0), (2, 255.0)):
        a[..., c] = np.where(alpha < 1, (a[..., c] - (1 - alpha) * bg) / k, a[..., c])
    a = a.clip(0, 255)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    spill = (np.minimum(r, b) - g - np.abs(r - b) * 0.5) > 15
    pinkish = (np.minimum(r, b) - g) > 20  # 先记下（压色之后就看不出来了）
    cap = g + 8
    a[..., 0] = np.where(spill, np.minimum(r, cap), r)
    a[..., 2] = np.where(spill, np.minimum(b, cap), b)
    if glow is not None:  # 夜景：半透明的那圈是灯泡光晕，染成暖光、再淡一点，不留灰圈
        above = (np.arange(a.shape[0]) < int(a.shape[0] * 0.39))[:, None]  # 只在矮墙以上（灯串那一段）
        soft = ((alpha < 0.97) | pinkish) & above  # 光晕：半透明的，和原本偏品红、被压成灰的玻璃
        a[..., :3] = np.where(soft[..., None], np.array(glow, np.float32), a[..., :3])
        alpha = np.where(soft, alpha * 0.7, alpha)
    out = np.dstack([a, alpha * 255.0]).clip(0, 255).astype(np.uint8)
    rgba = Image.fromarray(out, 'RGBA')
    # 收一圈边：抗锯齿留下的一像素品红边
    al = rgba.getchannel('A').filter(ImageFilter.MinFilter(3))
    rgba.putalpha(al)
    return rgba


def tile_clouds(band):
    """云带 → 横向可平铺：按「这一列有没有云」切出一朵朵整云（间隙 ≥ 8px 才算两朵，云里的小碎块跟着它那朵），
    等间距排开，首尾各留半个间距。返回同宽的云带，左右两列全透明。"""
    a = np.asarray(band)
    on = a[..., 3].max(axis=0) > 4
    runs, x = [], 0
    while x < len(on):
        if on[x]:
            x0 = x
            while x < len(on) and on[x:x + 8].any():
                x += 1
            runs.append((x0, x))
        x += 1
    total = sum(x1 - x0 for x0, x1 in runs)
    gap = (band.size[0] - total) / len(runs)
    if gap < 24:
        raise SystemExit(f'clouds too wide to tile: {total}px of clouds in {band.size[0]}px')
    out = np.zeros_like(a)
    cx = gap / 2
    for x0, x1 in runs:
        at = int(round(cx))
        out[:, at:at + x1 - x0] = a[:, x0:x1]
        cx += x1 - x0 + gap
    return Image.fromarray(out, 'RGBA')


def save(img, name, lossless=False):
    p = os.path.join(PACK, name)
    img.save(p, 'WEBP', quality=90, alpha_quality=100, method=6, lossless=lossless, exact=lossless)
    print(f'  pack/{name:22} {img.size[0]}×{img.size[1]}  {os.path.getsize(p)} bytes')


def main():
    up = lambda im: im.resize((W, H), Image.LANCZOS)
    # 天空原图的海平线在 42% 高度，露台矮墙顶在 40%：取原图右下 84% 放大，海平线移到约 31%，墙上方露出一段海和灯塔岛
    def sky(im):
        w, h = im.size
        y0, x0 = int(h * 0.16), int(w * 0.12)
        return up(im.crop((x0, y0, x0 + int((h - y0) * 16 / 9), h)))
    sky_day, sky_night = sky(raw('sky-day')), sky(raw('sky-night'))
    terr_day, terr_night = key_magenta(up(raw('terrace-day'))), key_magenta(up(raw('terrace-night')), glow=(255, 206, 128))

    # 云：抠图后取有云的那几行，放到画布 y≈90 处。原图里五朵云左右互不重叠：按列切成整朵（不切进云里），
    # 再等间距重新排开，最左、最右各留半个间距的透明——两份并排循环时，接缝处的间距和云之间的一样，看不出接缝
    cl = key_magenta(up(raw('clouds')))
    rows = np.where(np.asarray(cl.getchannel('A')).max(axis=1) > 8)[0]
    band = cl.crop((0, max(0, rows.min() - 8), W, min(H, rows.max() + 8)))
    band = band.resize((W, int(band.size[1] * 0.75)), Image.LANCZOS)
    clouds = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    clouds.alpha_composite(tile_clouds(band), (0, 90))
    al = np.asarray(clouds.getchannel('A'))
    assert al[:, 0].max() == 0 and al[:, -1].max() == 0, 'clouds must be transparent at the left / right edge'

    save(sky_day, 'sky-day.webp')
    save(sky_night, 'sky-night.webp')
    save(clouds, 'clouds.webp')
    save(terr_day, 'terrace-day.webp')
    save(terr_night, 'terrace-night.webp')

    day = sky_day.convert('RGBA')
    day.alpha_composite(Image.blend(Image.new('RGBA', (W, H), (0, 0, 0, 0)), clouds, 0.85))
    day.alpha_composite(terr_day)
    night = sky_night.convert('RGBA')
    night.alpha_composite(terr_night)
    preview = day.convert('RGB').resize((1920, 1080), Image.LANCZOS)
    save(preview, 'preview.webp')

    # 黄昏：暖色乘一层（应用里 sky.tint 做的是同一件事）
    dusk =Image.fromarray((np.asarray(day.convert('RGB')).astype(np.float32) * (np.array([1.0, 0.80, 0.66]))).clip(0, 255).astype(np.uint8))
    # 雨夜：夜景压暗一点，加斜雨丝
    rain = Image.fromarray((np.asarray(night.convert('RGB')).astype(np.float32) * 0.82).astype(np.uint8)).convert('RGBA')
    streaks = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(streaks)
    rnd = random.Random(7)
    for _ in range(900):
        x, y, n = rnd.uniform(-200, W), rnd.uniform(-100, H), rnd.uniform(40, 110)
        d.line((x, y, x + n * 0.22, y + n), fill=(200, 215, 240, rnd.randint(50, 110)), width=2)
    rain.alpha_composite(streaks)

    def shot(img, name, size=(960, 600)):
        img = img.convert('RGB')
        cw = int(H * size[0] / size[1])  # 16:10 取中间
        x0 = (W - cw) // 2
        img.crop((x0, 0, x0 + cw, H)).resize(size, Image.LANCZOS).save(os.path.join(SHOTS if name != 'cover.webp' else GAME, name), 'WEBP', quality=86, method=6)
        print(f'  {"" if name == "cover.webp" else "screenshots/"}{name}  {size[0]}×{size[1]}')

    shot(day, 'cover.webp', (640, 400))
    shot(day, '01-day.webp')
    shot(dusk, '02-dusk.webp')
    shot(night, '03-night.webp')
    shot(rain, '04-rain.webp')


if __name__ == '__main__':
    main()
