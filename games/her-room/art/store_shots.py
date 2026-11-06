#!/usr/bin/env python3
"""商店截图（screenshots/*.webp，960×600）：从应用 e2e 的真实截图生成，store.json 的顺序。
先在应用仓库跑 PIXELPET_ROOM_PACK=<这里的 pack> xvfb-run -a -s "-screen 0 1280x800x24" node e2e/run.js illustrated，
用法：python3 store_shots.py <应用仓库>/out/e2e/illustrated-room
"""
import os, sys
from PIL import Image
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SHOTS = {'01-idle': 'idle-off', '02-lamp': 'idle-lit', '03-lazy': 'idle-lazy-off', '04-phone': 'phone-off', '05-music': 'music-off', '06-sleep': 'sleep-off', '07-work': 'work-lit', '08-game': 'game-lit'}
for out, src in SHOTS.items():
    Image.open(os.path.join(sys.argv[1], f'i4b-{src}.png')).convert('RGB').resize((960, 600), Image.LANCZOS).save(f'../screenshots/{out}.webp', quality=82, method=6)
    print(out, os.path.getsize(f'../screenshots/{out}.webp'))
