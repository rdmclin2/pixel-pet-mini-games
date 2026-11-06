#!/usr/bin/env python3
"""手机 / 电脑屏幕上的短视频：用视频模型出 4 段 5 秒竖版短片（raw/clips/<id>.mp4），抽帧拼成图集。
用法：python3 clips.py gen     出片（已有的跳过）
      python3 clips.py atlas   → out/dafeiyu-clips.webp + out/dafeiyu-clips.json（{ "<id>-<nn>": { x, y, w, h } }）
需要已登录的 lh 和 ffmpeg。提示词在 CLIPS 里，都是原创画面，不含文字和商标。
"""
import glob, json, os, re, subprocess, sys, tempfile
from PIL import Image
os.chdir(os.path.dirname(os.path.abspath(__file__)))
MODEL = 'dreamina-seedance-2-0-fast-260128'; PROVIDER = 'lobehub'
FPS = 8; CELL = (180, 320); COLS = 16
STYLE = 'Vertical short video, hand-drawn anime look, slow gentle motion, one continuous shot, no text, no captions, no logo, no people.'
CLIPS = {
  'jellyfish': f'Glowing pink and pale-blue jellyfish drifting and pulsing slowly in a deep blue ocean, light rays from the surface, tiny particles floating. {STYLE}',
  'rain-window': f'A rainy night seen through a window with a warm desk lamp on the sill, raindrops running down the glass, blurred city lights twinkling outside. {STYLE}',
  'city': f'A quiet city street at 2 a.m. in the rain, wet road reflecting neon and shop lights, a few distant cars passing with blurred headlights, slow camera push-in. {STYLE}',
  'cat': f'A sleepy orange kitten on a soft blanket nodding off, eyes slowly closing and opening, warm afternoon light, tail gently moving. {STYLE}',
}
def gen():
    os.makedirs('raw/clips', exist_ok=True)
    for cid, prompt in CLIPS.items():
        out = f'raw/clips/{cid}.mp4'
        if os.path.exists(out): print('skip', cid); continue
        j = subprocess.run(['lh', 'generate', 'video', '-m', MODEL, '-p', PROVIDER, '--aspect-ratio', '9:16', '--duration', '5', '--resolution', '480p', '--json', prompt], capture_output=True, text=True)
        t = j.stdout + j.stderr
        g = re.search(r'"id":\s*"(gen_[^"]+)', t); a = re.search(r'"asyncTaskId":\s*"([^"]+)', t)
        if not g or not a: print('FAIL submit', cid, t[:500], flush=True); continue
        d = subprocess.run(['lh', 'generate', 'download', g.group(1), a.group(1), '-o', out, '--interval', '10', '--timeout', '900'], capture_output=True, text=True)
        print(('ok ' if d.returncode == 0 and os.path.exists(out) else 'FAIL download ' + d.stderr[:300] + ' ') + cid, g.group(1), flush=True)
def atlas():
    frames = []
    for cid in CLIPS:
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'raw/clips/{cid}.mp4', '-vf', f'fps={FPS},scale={CELL[0]}:{CELL[1]}:force_original_aspect_ratio=increase,crop={CELL[0]}:{CELL[1]}', f'{td}/%03d.png'], check=True)
            for i, f in enumerate(sorted(glob.glob(f'{td}/*.png'))): frames.append((f'{cid}-{i:02d}', Image.open(f).convert('RGB').copy()))
    rows = (len(frames) + COLS - 1) // COLS
    sheet = Image.new('RGB', (COLS * CELL[0], rows * CELL[1])); index = {}
    for n, (name, im) in enumerate(frames):
        x, y = (n % COLS) * CELL[0], (n // COLS) * CELL[1]
        sheet.paste(im, (x, y)); index[name] = {'x': x, 'y': y, 'w': CELL[0], 'h': CELL[1]}
    os.makedirs('out', exist_ok=True)
    sheet.save('out/dafeiyu-clips.webp', quality=62, method=6)
    json.dump(index, open('out/dafeiyu-clips.json', 'w'), indent=0)
    print(len(frames), 'frames', sheet.size, os.path.getsize('out/dafeiyu-clips.webp'), 'bytes')
if __name__ == '__main__': {'gen': gen, 'atlas': atlas}[sys.argv[1]]()
