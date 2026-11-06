#!/usr/bin/env python3
"""屏幕上的真实内容素材：封面（raw/cover-*）→ out/dafeiyu-cover-*.webp；真网页 web/rain-notes.html 用真实 Chromium 渲染成长图 out/dafeiyu-page-rain-notes.webp。
用法：python3 web_pages.py <chromium 路径>"""
import os, shutil, subprocess, sys, tempfile
from PIL import Image
os.chdir(os.path.dirname(os.path.abspath(__file__)))
def raw(n): return f'raw/{n}.png' if os.path.exists(f'raw/{n}.png') else f'raw/{n}.webp'
os.makedirs('out', exist_ok=True)
for n in ('cover-rain-whale', 'cover-moonlight'):
    Image.open(raw(n)).convert('RGB').resize((360, 360), Image.LANCZOS).save(f'out/dafeiyu-{n}.webp', quality=80, method=6)
with tempfile.TemporaryDirectory() as td:
    shutil.copy('web/rain-notes.html', td)
    for n in ('cover-rain-whale', 'cover-moonlight'): shutil.copy(f'out/dafeiyu-{n}.webp', f'{td}/{n}.webp')
    Image.open(raw('dafeiyu-base-off')).convert('RGB').crop((262, 0, 1064, 310)).resize((640, 247), Image.LANCZOS).save(f'{td}/hero.webp', quality=82)
    subprocess.run([sys.argv[1], '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--window-size=640,1500', '--force-device-scale-factor=1', f'--screenshot={td}/page.png', f'file://{td}/rain-notes.html'], check=True, capture_output=True)
    im = Image.open(f'{td}/page.png').convert('RGB')
    # 裁掉页面到底后的空白
    px = im.load(); h = im.height
    while h > 400 and all(px[x, h - 1] == px[0, h - 1] for x in range(0, 640, 16)): h -= 1
    im.crop((0, 0, 640, h)).save('out/dafeiyu-page-rain-notes.webp', quality=78, method=6)
    print('page', im.size, '→', h)
