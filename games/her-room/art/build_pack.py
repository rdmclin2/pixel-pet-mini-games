#!/usr/bin/env python3
"""manifest.src.json + out/ → ../pack/：把屏幕四角（screens.json）、眨眼贴片（out/blink.json）、光斑位置（out/bokeh-spots.json）填进 manifest，
贴片拼成 dafeiyu-parts.webp + dafeiyu-parts.json，再复制状态图。pack/ 里只有 manifest 列出的文件。
用法：python3 post.py && python3 bokeh.py && python3 blink.py && python3 build_pack.py && node ../../../tools/game-pack.js ../pack
"""
import json, os, shutil
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
m = json.load(open('manifest.src.json'))
room = m['rooms'][0]; rid = room['id']
scr = json.load(open('screens.json'))['states']
blink = json.load(open('out/blink.json'))
PACK = '../pack'
shutil.rmtree(PACK, ignore_errors=True); os.makedirs(PACK)
# 屏幕四角
for key, st in room['states'].items():
    for sid, sc in (st.get('screens') or {}).items():
        sc['corners'] = scr[key][sid]['corners']
# 光斑位置
room['window']['bokeh']['spots'] = json.load(open('out/bokeh-spots.json'))
# 贴片图集
cells = []
for key, b in blink.items():
    for k in ('off', 'lit'): cells.append((b[k], Image.open(f'out/blink/{key}-{k}.png')))
atlas_w = sum(c[1].width + 2 for c in cells); atlas_h = max(c[1].height for c in cells)
atlas = Image.new('RGBA', (atlas_w, atlas_h), (0, 0, 0, 0)); index = {}; x = 0
for name, im in cells:
    atlas.paste(im, (x, 0)); index[name] = {'x': x, 'y': 0, 'w': im.width, 'h': im.height}; x += im.width + 2
atlas.save(f'{PACK}/{rid}-parts.webp', lossless=True, exact=True)
json.dump(index, open(f'{PACK}/{rid}-parts.json', 'w'), indent=1)
room['images'] = {'parts': f'{rid}-parts.webp'}; room['sprites'] = f'{rid}-parts.json'
# 屏幕的真实内容（clips.py、web_pages.py 的产物）：视频帧图集、封面、网页长图
room['images'].update({'clips': f'{rid}-clips.webp', 'cover-rain-whale': f'{rid}-cover-rain-whale.webp', 'cover-moonlight': f'{rid}-cover-moonlight.webp', 'page-rain-notes': f'{rid}-page-rain-notes.webp'})
room['frames'] = {'clips': f'{rid}-clips.json'}
for f in [*list(room['images'].values())[1:], room['frames']['clips']]: shutil.copy(f'out/{f}', f'{PACK}/{f}')
for key, b in blink.items():
    st = room['states'][key]
    st['blink'] = {'sprite': {'off': b['off'], 'lit': b['lit']}, 'at': b['at'], 'every': (st.get('blink') or {}).get('every', [3, 6])}
# 状态图
for st in room['states'].values():
    for f in st['images'].values(): shutil.copy(f'out/{f}', f'{PACK}/{f}')
json.dump(m, open(f'{PACK}/manifest.json', 'w'), ensure_ascii=False, indent=2)
print('pack:', len(os.listdir(PACK)), 'files,', sum(os.path.getsize(f'{PACK}/{f}') for f in os.listdir(PACK)), 'bytes')
