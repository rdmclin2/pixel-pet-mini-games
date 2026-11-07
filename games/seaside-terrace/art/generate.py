#!/usr/bin/env python3
"""按 prompts.json 逐张出图（一次一张、间隔 20 秒）。refs 里的本地图先 lh file upload 拿到 URL，再作为 imageUrls 传给 gpt-image（编辑 / 参考模式）。
用法：python3 generate.py [--force] [name ...]   → raw/<name>.png；已有的（png 或提交用的无损 webp）跳过。
提交前转无损 WebP：python3 -c 'from PIL import Image;…' （见 README.md）。
"""
import json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
args = sys.argv[1:]
force = '--force' in args
names = [a for a in args if not a.startswith('--')]
cfg = json.load(open('prompts.json'))
cache_p = 'raw/.upload-cache.json'
cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
def url_of(path):
    if not os.path.exists(path) and os.path.exists(path[:-4] + '.webp'): path = path[:-4] + '.webp'
    key = f"{path}:{os.path.getmtime(path)}"
    if key not in cache:
        out = subprocess.run(['lh', 'file', 'upload', '-f', path, '--json'], capture_output=True, text=True).stdout
        cache[key] = json.loads(out[out.index('{'):])['url']
        json.dump(cache, open(cache_p, 'w'), indent=1)
    return cache[key]
def fill(s):
    return s.replace('{style}', cfg['style']).replace('{terrace}', cfg.get('terrace', ''))
os.makedirs('raw', exist_ok=True)
first = True
for job in cfg['jobs']:
    n = job['name']
    if names and n not in names: continue
    out = f'raw/{n}.png'
    if (os.path.exists(out) or os.path.exists(out[:-4] + '.webp')) and not force: print('skip', n); continue
    if not first: time.sleep(20)
    first = False
    urls = [url_of(r) for r in job.get('refs', [])]
    cmd = ['lh', 'generate', 'image', '-m', 'gpt-image-2.5-sunburst', '-p', 'lobehub',
           '--param', f"size={job['size']}", '--param', f"quality={cfg['quality']}", '--json']
    if urls: cmd += ['--param', 'imageUrls=' + json.dumps(urls)]
    cmd.append(fill(job['prompt']))
    j = subprocess.run(cmd, capture_output=True, text=True)
    txt = j.stdout + j.stderr
    g = re.search(r'"id":\s*"(gen_[^"]+)', txt); a = re.search(r'"asyncTaskId":\s*"([^"]+)', txt)
    if not g or not a: print('FAIL submit', n, txt[:600]); continue
    d = subprocess.run(['lh', 'generate', 'download', g.group(1), a.group(1), '-o', out, '--interval', '5', '--timeout', '900'], capture_output=True, text=True)
    print(('ok ' if d.returncode == 0 and os.path.exists(out) else 'FAIL download ') + n, g.group(1), flush=True)
