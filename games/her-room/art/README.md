# 她的房间 · 美术源（T-11695 探针 → T-11697 整包）

大肥鱼「鲸鱼女仆的雨夜小屋」：设定图 1 张、空房间底版（台灯关 / 开）、8 个状态 × 台灯关 / 开、3 个状态的闭眼差分 × 台灯关 / 开。状态清单见 [STATES.md](STATES.md)，一致性自查表见 [CONSISTENCY.md](CONSISTENCY.md)。

流程按方案 T-11682（应用仓库 `docs/illustrated-room-design.md` §11）：GPT Image 编辑模式，每张状态图都带「空房间底版 + 冻结的设定图」作参考，提示词里逐字复制同一段角色描述。

## 重跑

需要 pillow、numpy、opencv-python-headless 和已登录的 `lh`。

```bash
python3 generate.py [名字…]     # 出图：一次一张，已有的跳过，--force 重出。raw/ 提交前转无损 WebP
python3 post.py                 # raw → out：和底版合成，out/post-report.json
python3 bokeh.py                # out/bokeh-spots.json：窗户里画好的灯位
python3 blink.py                # out/blink/*.png、out/blink.json：只裁眼睛（框在 blink-eyes.json）
python3 screens.py              # preview/screens.jpg：屏幕四角叠框核对（标注在 screens.json）
python3 build_pack.py           # manifest.src.json + out → ../pack
python3 sheets.py               # preview/*.jpg、out/consistency.json
node ../../../tools/game-pack.js ../pack
```

`out/` 不提交，可以从 `raw/` 重新生成。

## 文件

| 路径 | 内容 |
| --- | --- |
| `prompts.json` | 全部提示词：`character`（固定角色描述）、`style`、`room`，每张图的 `prompt` / `refs` / `size`；`round` 是第几轮出的 |
| `raw/` | 模型原图（2048×1152，设定图 2048×2048），无损 WebP。`raw/round1/` 是探针第 1 轮被替换下来的图 |
| `ref/` | 参考：录屏截帧、角色裁图、像素桌宠的大肥鱼 |
| `manifest.src.json` | manifest 手写的部分；屏幕四角、眨眼贴片、光斑位置由 `build_pack.py` 填入 |
| `screens.json`、`blink-eyes.json` | 人工标注：屏幕四角、眼睛范围 |
| `preview/` | 验收对照图：`states.jpg`（台灯关 / 开）、`character.jpg`、`layout.jpg`、`compare.jpg`、`screens.jpg` |

## 出图顺序

1. `dafeiyu-sheet`：三视图 + 4 个表情，**冻结**。
2. `dafeiyu-base-off`：没有人的房间，台灯关。`dafeiyu-base-lit`：编辑 off，只开台灯。
3. `dafeiyu-<状态>-off`：编辑 base-off + 设定图，放进一个姿势。`idle-lazy` 编辑 `idle-off`（同一位置）；`game` 编辑 `work-off`（同一个笔记本）。
4. `dafeiyu-<状态>-lit`：编辑该状态的 off 图 + base-lit，只改光照。
5. `dafeiyu-<状态>-blink-{off,lit}`：编辑状态图，只把眼睛改成闭眼。

需要屏幕的姿势在提示词里写明「屏幕朝上可见」（探针第 1 轮手机背面朝镜头，贴不了内容）。

## 后处理

- 所有状态的静止部分逐像素取底版（`post.py`）：差异大的区域（她、被她动过的东西）留状态图，窗户内和 ROI 外一律取底版，交叉淡化时只有她在变。探针时窗户区差 7.5/255，现在 ≤ 0.42，全部静止区域 ≤ 2.92。
- 眨眼贴片：编辑图平移对齐到状态图，整体明暗对齐，四周羽化 6 px。off / lit 共用一个框，引擎按台灯亮度混合。
- 屏幕四角避开手和头：engine 的屏幕网格盖在插画上，没有前景遮挡层，所以四边形收到不盖住她的位置。
