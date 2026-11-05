# Notices

The code in this repository and the game art listed below as original are MIT (see [LICENSE](LICENSE)). Some pictures show characters from [Pixel Pet Affection](https://github.com/rdmclin2/lobehub-pixel-pet-affection) and keep those characters' terms.

## 像素小院 (`games/pixel-yard/`)

All art was generated with OpenAI `gpt-image-2.5-sunburst` through LobeHub (`lh generate image`) from the prompts in `games/pixel-yard/art/prompts.json` and pixelated by `scripts/game_sprites.py`. It shows no existing character and comes from no existing game: MIT.

## 她的房间 (`games/her-room/`)

- **Room art** — `art/raw/dafeiyu-room`, `dafeiyu-furniture`, `dafeiyu-props`, `dafeiyu-screens` were generated on 2026-11-05 with OpenAI `gpt-image-2.5-sunburst` through LobeHub (`scripts/generate.sh games/her-room`, prompts in `art/prompts.json`) and cut, keyed and pixelated into `pack/dafeiyu-room.webp`, `pack/dafeiyu-atlas.webp` and `pack/dafeiyu-sprites.json` by `scripts/game_sprites.py` (`art/layout.json`). The prompts ask for no people and no characters; the room, its furniture and its whale motifs are original: MIT.
- **大肥鱼 (Dafeiyu)** — the game pack contains no picture of her. In the room the app draws her from her own look, the `daily` outfit (her signature maid dress, `sheets/daily.webp`) of the `dafeiyu-pixel` pack built into the app (`src/renderer/packs/dafeiyu-pixel/`), with its existing actions (`sleep`, `think`, `look`, `happy`, `play`, `idle`, `walk`). No new pose of her was generated for this game.
- **Pictures that show her** — `cover.webp` and the store screenshots of this game contain frames of the `dafeiyu-pixel` `daily` sheet. That pack depicts a community character (the DeepSeek whale-girl maid; original design ZipZipPipe, character sheet lmy414 / ai-chan-sheets, pixel art rdmclin2 generated with `gpt-image-2.5`), so these pictures are **CC BY-NC-SA 4.0, non-commercial only**, like the pack — see the app's [NOTICE.md](https://github.com/rdmclin2/lobehub-pixel-pet-affection/blob/canary/NOTICE.md).
