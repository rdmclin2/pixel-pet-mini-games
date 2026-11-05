#!/usr/bin/env python3
"""她的房间 (room@1) art preview: stills of an open theme, to check the art and the coordinates in the manifest.

  python3 scripts/room_preview.py games/her-room/pack <pet sheet.webp> <pet pack.json> <out-dir> [theme]

Composes the room (background, flat and sorted furniture, the activity's props) with the room owner drawn from
her pixel pack (for 大肥鱼: the app's src/renderer/packs/dafeiyu-pixel, sheets/daily.webp = her maid dress), once
idle and once per activity → room-idle.png, act-<kind>.png. It is not the engine (the app's engines/room.js draws
the game): props are shown at one moment (a few particles, the record turned a little, 2 of 5 lines typed, tucked
in = only her head above the quilt), to see that everything is where the manifest says.
Needs Pillow.
"""
import json, sys, os, math
from PIL import Image, ImageDraw, ImageEnhance
pack, sheet_path, packjson, outdir = sys.argv[1:5]
m = json.load(open(os.path.join(pack, 'manifest.json')))
want = sys.argv[5] if len(sys.argv) > 5 else None
t = next(x for x in m['themes'] if x['status'] == 'open' and (want is None or x['id'] == want))
idx = json.load(open(os.path.join(pack, t['sprites'])))
atlas = Image.open(os.path.join(pack, t['images']['atlas'])).convert('RGBA')
room = Image.open(os.path.join(pack, t['images']['room'])).convert('RGBA')
pj = json.load(open(packjson)); FW, FH = pj['frame']['width'], pj['frame']['height']
sheet = Image.open(sheet_path).convert('RGBA')
os.makedirs(outdir, exist_ok=True)
def spr(n):
    b = idx[n]; return atlas.crop((b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
def frame(anim, k=0):
    a = pj['actions'][anim]; r, c = a['row'], a['col'] + k
    return sheet.crop((c * FW, r * FH, (c + 1) * FW, (r + 1) * FH))
def pet_img(anim, face, h):
    f = frame(anim); bb = f.getbbox(); f = f.crop(bb)
    s = h / FH; f = f.resize((max(1, round(f.width * s)), max(1, round(f.height * s))), Image.NEAREST)
    if face == 'left': f = f.transpose(Image.FLIP_LEFT_RIGHT)
    return f
def put_feet(dst, im, x, y):  # x, y = bottom centre
    dst.alpha_composite(im, (round(x - im.width / 2), round(y - im.height)))
def scale(im, k):
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.NEAREST)
def render(kind=None, frame_i=0):
    W, H = t['world']['width'], t['world']['height']
    img = room.copy()
    a = t['activities'].get(kind) if kind else None
    props = a['props'] if a else []
    hidden = {p['sprite'] for p in props if p['fx'] == 'hide'}
    flat = [f for f in t['furniture'] if f.get('flat')]
    for f in sorted(flat, key=lambda f: f['y']):
        if f['sprite'] not in hidden: put_feet(img, spr(f['sprite']), f['x'], f['y'])
    anim = (a.get('anim') if a else None) or (m['activities'][kind]['anim'] if kind else 'idle')
    spot = a['spot'] if a else t['spawn']; face = a.get('face', 'right') if a else 'right'
    ph = t['petHeight']; pet = pet_img(anim, face, ph)
    tucked = a and a.get('pose') == 'tucked'
    bob = 0
    items = [(f['y'], 'f', f) for f in t['furniture'] if not f.get('flat')]
    if not tucked: items.append((spot[1], 'p', None))
    for y, k, f in sorted(items, key=lambda i: i[0]):
        if k == 'f': put_feet(img, spr(f['sprite']), f['x'], f['y'])
        else: put_feet(img, pet, spot[0], spot[1] - bob)
    pet_box = None if tucked else (spot[0] - pet.width / 2, spot[1] - pet.height, pet.width, pet.height)
    if tucked:
        layer = next(p for p in props if p['fx'] == 'layer')
        q = spr(layer['sprite']); qtop = layer['y'] - q.height
        bed = next(f for f in t['furniture'] if f['id'] == a['at'])
        # she is tucked in: only her head (with the fin ears and the headdress) shows above the quilt's lace edge,
        # on the pillow end of the bed
        f = frame('sleep'); f = f.crop(f.getbbox()); k = ph / FH
        f = f.resize((round(f.width * k), round(f.height * k)), Image.NEAREST)
        head = f.crop((0, 0, f.width, round(f.height * 0.34)))
        put_feet(img, head, layer['x'] - q.width / 2 + 34, qtop + 12)
        put_feet(img, q, layer['x'], layer['y'])
        if bed.get('front'):
            put_feet(img, spr(bed['front']), bed['x'], bed['y'])
    for p in props:
        fx = p['fx']
        if fx == 'layer' and not tucked: put_feet(img, spr(p['sprite']), p['x'], p['y'])
        elif fx == 'spin':
            d = spr(p['sprite']).rotate(frame_i * 30)
            d = d.resize((d.width, max(1, round(d.height * p['squash']))), Image.NEAREST)
            img.alpha_composite(d, (round(p['x'] - d.width / 2), round(p['y'] - d.height / 2)))
        elif fx == 'frames':
            x, y, w, h = p['rect']; fr = spr(p['sprites'][frame_i % len(p['sprites'])]).resize((w, h), Image.NEAREST)
            img.alpha_composite(fr, (x, y))
        elif fx == 'screen-type':
            x, y, w, h = p['rect']
            if p.get('sprite'): img.alpha_composite(spr(p['sprite']).resize((w, h), Image.NEAREST), (x, y))
            d = ImageDraw.Draw(img); col = t['palette'].get(p['color'], p['color'])
            rows = p['rows']; lh = (h - 8) / rows; done = 2
            for r in range(done + 1):
                ww = (w - 18) * (1 if r < done else 0.55) * (0.7 + 0.3 * ((r * 7) % 3) / 2)
                yy = y + 4 + r * lh + lh * 0.25
                d.rectangle([x + 14, yy, x + 14 + ww, yy + max(2, lh * 0.45)], fill=col)
            d.rectangle([x + 14 + (w - 18) * 0.55 + 2, y + 4 + done * lh + 1, x + 14 + (w - 18) * 0.55 + 4, y + 4 + done * lh + lh - 1], fill=col)
        elif fx == 'hold' and pet_box:
            s = spr(p['sprite']); u, v = p['hand']
            if face == 'left': u = 1 - u
            img.alpha_composite(s, (round(pet_box[0] + u * pet_box[2] - s.width / 2), round(pet_box[1] + v * pet_box[3] - s.height / 2)))
        elif fx == 'glow':
            g = Image.new('RGBA', img.size); gd = ImageDraw.Draw(g)
            for r in range(p['r'], 0, -4): gd.ellipse([p['x'] - r, p['y'] - r, p['x'] + r, p['y'] + r], fill=(255, 240, 180, int(40 * (1 - r / p['r']))))
            img.alpha_composite(g)
    if any(p['fx'] == 'dim' for p in props):
        to = next(p['to'] for p in props if p['fx'] == 'dim')
        rgb = ImageEnhance.Brightness(img.convert('RGB')).enhance(to)
        rgb = Image.blend(rgb, Image.new('RGB', img.size, (20, 30, 80)), 0.18)
        img = rgb.convert('RGBA')
    for p in props:
        if p['fx'] == 'emit':
            fr = p['from'] if p['from'] != 'head' else [spot[0], spot[1] - (pet.height if pet_box else 40) - 6]
            for i, n in enumerate(p['sprites'] * 2):
                k = (i + 1) / (len(p['sprites']) * 2 + 1)
                s = scale(spr(n), 1.5)
                img.alpha_composite(s, (round(fr[0] + 14 * math.sin(i * 2.1) - s.width / 2 + i * 6), round(fr[1] - k * p.get('rise', 40) - s.height)))
    return img
render().save(os.path.join(outdir, 'room-idle.png'))
for k in ['sleep', 'work', 'phone', 'music', 'game']:
    render(k, 1).save(os.path.join(outdir, f'act-{k}.png'))
print('ok', outdir)
