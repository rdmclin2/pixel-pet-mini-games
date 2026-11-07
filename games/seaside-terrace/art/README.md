# 海边露台 · 美术源

商店里的第一张壁纸（引擎 `wallpaper@1`，格式见应用仓库 `docs/wallpaper-mode.md` §3）。全部美术由 GPT Image（`gpt-image-2.5`）按下面的提示词生成，是原创画面：没有用到 Wallpaper Engine 或任何现有作品的素材、构图或角色。画面里没有她，她由应用用角色包的动作画在露台上。

## 文件

| 文件 | 作用 |
| --- | --- |
| `prompts.json` | 提示词（下面原文列出），`style` 和 `terrace` 会拼进每条 |
| `generate.py` | 逐张出图（一次一张、间隔 20 秒）；带 `refs` 的那条先上传参考图，再用编辑模式重画（夜景沿用白天的构图） |
| `post.py` | 原图 → `pack/` 的图层与预览、`cover.webp`、`screenshots/`：品红抠透明、天空裁到海平线在 31%、云带放到上方并左右留透明（横向循环无缝）、夜里灯泡光晕染成暖光 |
| `raw/*.webp` | 原图（无损 WebP，2048×1152） |

## 重新生成

```bash
python3 games/seaside-terrace/art/generate.py [name …]                         # 需要已登录的 lh；已有的跳过
uv run --with pillow --with numpy python3 games/seaside-terrace/art/post.py  # 写 pack/、cover.webp、screenshots/
node tools/game-pack.js games/seaside-terrace
```

## 坐标（画布 2560×1440）

- 露台矮墙顶在 y≈576，墙根 y≈930；`pet.area` 是墙根往下的地砖，左上角让开薰衣草花盆，右边 `blocked` 让开圆桌和两把椅子。
- `fx.lights` 是灯串上 10 个灯泡的位置（黄昏和夜里亮）。

## 提示词（原文）

**style**（每条都带）：Soft painterly hand-drawn anime background art for a cozy desktop wallpaper, clean shapes, gentle gradients, warm Mediterranean seaside light, wide 16:9 composition. Original scene. No text, no letters, no watermark, no logo, no UI, no people, no characters, no animals.

**terrace**（露台两张共用）：a small whitewashed rooftop terrace by the sea, seen straight from the front at a slightly raised eye level: the terracotta tile floor fills the bottom 40% of the frame and is mostly open and empty in the middle so someone can walk across it; its back edge is a low white rounded parapet wall running straight across the whole width at about 58% of the frame height; on the left a long wooden bench with pale blue cushions stands against the parapet; on the right a small round blue-and-white mosaic table with two wooden folding chairs; big terracotta pots with a small lemon tree at the far right and lavender and herbs at the far left; a thin wooden post at each side edge carries a string of round light bulbs that sags in a gentle curve across the upper part of the frame

### sky-day（2048x1152）

A wide calm seascape seen from a rooftop: clear soft blue morning-to-noon sky with only a couple of faint thin clouds near the horizon, the sea horizon runs straight across at about 50% of the frame height, the calm sea below with gentle sparkles of sunlight, a small distant green island with a tiny white lighthouse on the right side of the horizon, a few far white sailboats. No buildings in the foreground, no terrace, no railing, nothing in front of the sea: the lower half is only open sea down to the bottom edge. {style}

### sky-night（2048x1152，参考 raw/sky-day.png）

Repaint this exact seascape at night with the same composition: the horizon, the island and the lighthouse stay in exactly the same place. Deep navy starry sky with many small stars and a faint milky band, a crescent moon high on the upper left, a long silver moonlight reflection on the dark calm sea, the lighthouse lamp on the island glowing warm yellow with a soft beam, sailboats gone. Nothing in front of the sea. {style}

### terrace-day（2048x1152）

Only the foreground of a scene: {terrace}. Bright daytime sunlight from the upper left with soft shadows on the tiles. Everything above and behind the parapet wall (where the sky and the sea would be) is one perfectly flat solid pure magenta color #FF00FF with no gradient, no texture, no shadow, no glow; the magenta also shows between the light bulbs and through the gaps of the plants above the wall. The light bulbs are unlit. {style}

### terrace-night（2048x1152，参考 raw/terrace-day.png）

Repaint this exact image at night with exactly the same layout, objects and outlines: cool blue moonlight ambient on the white walls and the tiles, every round bulb of the string lights glowing warm yellow with small warm pools of light below them, a small glowing glass lantern on the mosaic table, warm light on the bench cushions. Keep every area that is pure magenta #FF00FF exactly the same flat solid magenta, with no glow, no darkening and no stars on it. {style}

### clouds（2048x1152）

Five separate soft fluffy white-and-cream cumulus clouds of different sizes floating in a loose horizontal row through the middle of the frame, painted with soft lavender shadow undersides, on a perfectly flat solid pure magenta #FF00FF background with no gradient. No cloud touches the left, right, top or bottom edge of the image: leave a wide empty magenta margin all around. Nothing else in the image. {style}
