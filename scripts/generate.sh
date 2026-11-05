#!/bin/bash
# GPT Image 原图：按 games/<id>/art/prompts.json 一张张生成（一次一张、间隔 20 秒，不并行），已有的跳过。
#   scripts/generate.sh games/pixel-yard [name ...]      → games/pixel-yard/art/raw/<name>.png
# 需要已登录的 lh（LobeHub CLI）。生成后可以转成无损 WebP 再提交（python3 -c 'from PIL import Image; …'）。
set -u
GAME="${1:?game dir, e.g. games/pixel-yard}"; shift
P="$GAME/art/prompts.json"; OUT="$GAME/art/raw"
mkdir -p "$OUT"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); [print(j["name"]+"\t"+j["size"]+"\t"+j["prompt"]+" "+d["style"]) for j in d["jobs"]]' "$P" | while IFS=$'\t' read -r name size prompt; do
  if [ $# -gt 0 ] && [[ ! " $* " =~ " $name " ]]; then continue; fi
  { [ -s "$OUT/$name.png" ] || [ -s "$OUT/$name.webp" ]; } && { echo "skip $name"; continue; }
  j=$(lh generate image -m gpt-image-2.5-sunburst -p lobehub --param size=$size --param quality=high --json "$prompt" 2>&1)
  g=$(printf '%s' "$j" | grep -o '"id": *"gen_[^"]*' | head -1 | sed 's/.*"gen_/gen_/')
  a=$(printf '%s' "$j" | grep -o '"asyncTaskId": *"[^"]*' | head -1 | sed 's/.*: *"//')
  if [ -z "$g" ]; then echo "FAIL submit $name: $j" | head -c 600; echo; continue; fi
  lh generate download "$g" "$a" -o "$OUT/$name.png" --interval 5 --timeout 900 >/dev/null 2>&1 && echo "ok $name" || echo "FAIL download $name $g $a"
  sleep 20
done
