# 她的房间 · 状态清单（T-11697）

世界坐标 1920×1080。每个状态一张专门画的完整构图，台灯关 / 开各一张（`pack/dafeiyu-<id>-off.webp`、`-lit.webp`）。动效由 `illustrated-room@1` 引擎按 manifest 字段做。

| id | 名称（活动） | 姿势 | 构图 | 屏幕（内容） | 眨眼 | 呼吸区域 / 其它动效 |
| --- | --- | --- | --- | --- | --- | --- |
| `idle` | 发呆（idle，默认状态） | 坐在床边，面朝镜头抬头，双手撑床，双脚悬空 | 人在床中段前沿，手机放在身边 | 手机（锁屏） | 差分贴片 | `[690,590,220,150]`，周期 4.4 秒 |
| `idle-lazy` | 犯懒（idle） | 同一位置，半闭眼、头歪、肩膀垂下、手收在腿上 | 同上，上半身塌下来 | 手机（锁屏） | 差分贴片（更勤） | `[690,590,220,150]`，周期 5.2 秒 |
| `phone` | 看手机（phone） | 趴在床头一侧，手指点屏幕，脚和尾巴翘起 | 人横在床上半部，手机平放胸前 | 手机（真实短视频帧） | 差分贴片 | `[610,540,300,150]`，周期 3.6 秒 |
| `music` | 听音乐（music） | 靠在床头枕头上，戴白色大耳机，闭眼微笑，腿伸直 | 人在床头，手机放在腿上 | 手机（播放器：封面、歌名、歌词） | 闭着眼，不眨 | `[470,480,200,130]`，轻晃 84 BPM，音符飘起 |
| `sleep` | 睡觉（sleep） | 侧躺，闭眼，被子盖到肩，尾巴露出 | 被子从床尾拉上来铺满床，手机在枕边 | 手机（锁屏） | 闭着眼，不眨 | `[560,560,440,170]`，周期 5.2 秒，Z 飘起 |
| `work` | 工作（work） | 背对镜头坐转椅，双手打字 | 人在右下书桌前，床空着，外套换到椅背 | 笔记本（文档和真实网页轮流） | 背对，不眨 | `[1420,430,250,250]`，进入时自动开灯 |
| `game` | 打游戏（game） | 侧身前倾，双手握白手柄，尾巴翘起 | 同一张书桌，露出半边脸和手柄 | 笔记本（小游戏） | 看不到正脸，不眨 | `[1360,430,240,230]`，周期 3.2 秒 |
| `stand` | 起身（过渡，不能直接选） | 背对镜头站在床尾和书桌之间，手扶椅背 | 人站在地板上，全身可见 | 无 | 无 | 床 ↔ 书桌切换时停 0.6 秒 |

`idle-lazy` 有三个入口：状态栏「发呆」旁边的「犯懒」按钮（来自 manifest 的 `idle.variants`）、聊天（「好懒啊」「犯懒吧」「躺平吧」）、键盘 7。

## 屏幕四角（左上、右上、右下、左下）

见 `screens.json`，核对图 `preview/screens.jpg`（每个带屏幕的状态 off / lit 各一格，红框是标注）。

## 动效素材

| 素材 | 文件 | manifest 字段 |
| --- | --- | --- |
| 眨眼差分（idle、idle-lazy、phone × off / lit，共 6 块） | `pack/dafeiyu-parts.webp` + `dafeiyu-parts.json` | `states.<id>.blink { sprite: { off, lit }, at, every }` |
| 呼吸形变区域 | 无单独素材，切状态图的矩形 | `states.<id>.breath { rect, amp, period }` |
| 光斑位置（在底版窗户里找到的 28 盏灯） | 无单独素材，引擎画径向渐变 | `window.bokeh.spots [[x, y, r, warm]…]` |
| 雨丝、水珠 | 引擎画 | `window.rain` |
| 台灯光晕 | 引擎画 | `lighting.lamp.glow` |
| 开灯的光照 | 烘焙进所有 lit 图（`warm.py`：床保持蓝色，暖光从灯向外渐隐） | `states.<id>.images.lit` |

## 屏幕内容

| 内容 | 素材 | manifest 字段 |
| --- | --- | --- |
| 短视频 | 4 段视频模型出的 5 秒短片（水母、雨夜窗边、凌晨街道、犯困小猫），抽帧成图集 `dafeiyu-clips.webp` + `dafeiyu-clips.json` | `frames.clips`、`images.clips`、`content.clips.list[]`（`frames`、`pingpong`、`caption`） |
| 网页 | `web/rain-notes.html` 用真实 Chromium 渲染的长图 `dafeiyu-page-rain-notes.webp`，引擎慢慢往下滚，和逐字打字的周报轮流 | `images.page-rain-notes`、`content.page { seconds, templates[] }` |
| 正在播放 | 封面 `dafeiyu-cover-*.webp`，歌名、歌手、时长、进度、带时间的歌词（原创歌词，没有音频） | `images.cover-*`、`content.player.tracks[]`（`cover`、`lyrics`） |
| 小游戏 | 引擎画的「鲸鱼跳跳」，自己玩，得分走动 | `content.game` |
