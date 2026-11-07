'use strict';
// node --test tools/   — the wallpaper@1 format check (tools/wallpaper-pack.js, through tools/game-pack.js)
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const GP = require('./game-pack');
const WP = require('./wallpaper-pack');

const ROOT = path.join(__dirname, '..');
const PACK = path.join(ROOT, 'games', 'seaside-terrace', 'pack');

// a small, complete wallpaper (2560×1440), checked with the files and picture sizes it would have on disk
const base = () => ({
  schema: 1, kind: 'wallpaper', engine: 'wallpaper@1', id: 'test-wall', name: '测试壁纸', version: '1.0.0',
  canvas: { width: 2560, height: 1440, background: '#1a2b3c', fit: 'cover', focus: [0.5, 0.6] },
  preview: 'preview.webp',
  layers: [
    { id: 'sky', image: 'sky.webp', z: 0, phases: ['dawn', 'day', 'dusk'] },
    { id: 'night', image: 'night.webp', z: 0, phases: ['night'] },
    { id: 'cloud', image: 'cloud.png', z: 5, drift: [8, 0], loop: true, opacity: 0.9 },
    { id: 'front', image: 'front.png', z: 10 },
  ],
  sky: { phases: true, weather: ['clear', 'cloudy', 'rain'], tint: true },
  fx: { rain: true, fireflies: 6, lights: [{ x: 600, y: 500, r: 90, phases: ['dusk', 'night'] }] },
  pet: {
    height: 200, speed: 70, spawn: [1280, 1200], z: 20,
    area: [[300, 1000], [2300, 1000], [2300, 1400], [300, 1400]],
    blocked: [{ cx: 1800, cy: 1100, rx: 120, ry: 40 }],
    spots: [{ id: 'bench', at: [500, 1050], anim: 'sit', seconds: [20, 60], face: 'right' }],
  },
  power: { fps: 24 },
});
const files = ['manifest.json', 'preview.webp', 'sky.webp', 'night.webp', 'cloud.png', 'front.png'];
const sizes = { 'preview.webp': [1920, 1080], 'sky.webp': [2560, 1440], 'night.webp': [2560, 1440], 'cloud.png': [2560, 1440], 'front.png': [2560, 1440] };
const check = (m, opts = {}) => GP.validateManifest(m, { files, sizes, ...opts });
const fails = (edit, re, opts) => {
  const m = base();
  edit(m);
  const e = check(m, opts);
  assert.ok(e.some((x) => re.test(x)), `expected an error like ${re}, got ${JSON.stringify(e)}`);
};

test('wallpaper@1 is an engine the format knows, and a good wallpaper passes', () => {
  assert.ok(GP.ENGINES.includes('wallpaper@1'));
  assert.deepStrictEqual(check(base()), []);
  assert.deepStrictEqual(GP.packFiles(base()).sort(), ['cloud.png', 'front.png', 'night.webp', 'preview.webp', 'sky.webp']);
  assert.deepStrictEqual(GP.spriteFiles(base()), []);
});

test('kind follows the engine: a wallpaper is not a game, a game is not a wallpaper', () => {
  fails((m) => { m.kind = 'game'; }, /kind must be "wallpaper"/);
  const yard = JSON.parse(fs.readFileSync(path.join(ROOT, 'games', 'pixel-yard', 'pack', 'manifest.json'), 'utf8'));
  yard.kind = 'wallpaper';
  assert.ok(GP.validateManifest(yard).some((x) => /kind must be "game"/.test(x)));
});

test('wallpaper@1 refuses broken packs', () => {
  fails((m) => { m.canvas.width = 100; }, /canvas\.width \/ height/);
  fails((m) => { m.canvas.fit = 'stretch'; }, /canvas\.fit must be/);
  fails((m) => { m.canvas.focus = [0.5, 2]; }, /canvas\.focus/);
  fails((m) => { m.canvas.background = 'blue'; }, /canvas\.background/);
  fails((m) => { delete m.preview; }, /preview is missing/);
  fails((m) => { m.layers = []; }, /layers must be a list of 1–16/);
  fails((m) => { m.layers = Array.from({ length: 17 }, (_, i) => ({ id: `l${i}`, image: 'sky.webp', z: 0 })); }, /layers must be a list of 1–16/);
  fails((m) => { m.layers[1].id = 'sky'; }, /id "sky" twice/);
  fails((m) => { m.layers[0].image = 'sky.mp4'; }, /file name "sky\.mp4" is not allowed/); // no video in v1
  fails((m) => { m.layers[0].image = 'other.webp'; }, /other\.webp is missing/);
  fails((m) => { m.layers[0].image = 'sprites.json'; }, /not allowed \(\.webp \/ \.png\)/);
  fails((m) => { m.layers[0].z = 1.5; }, /z must be a whole number/);
  fails((m) => { m.layers[2].drift = [500, 0]; }, /drift must be/);
  fails((m) => { delete m.layers[2].drift; }, /loop needs a drift/);
  fails((m) => { m.layers[2].opacity = 2; }, /opacity must be 0–1/);
  fails((m) => { m.layers[3].blend = 'overlay'; }, /blend must be one of/);
  fails((m) => { m.layers[0].phases = ['noon']; }, /phases must be a list of/);
  fails((m) => { m.sky.weather = ['hail']; }, /sky\.weather/);
  fails((m) => { m.fx.fireflies = 99; }, /fx\.fireflies must be 0–40/);
  fails((m) => { m.fx.lights[0].x = 9999; }, /fx\.lights\[0\]/);
  fails((m) => { m.pet.height = 2; }, /pet\.height must be 16–800/);
  fails((m) => { m.pet.spawn = [10, 10]; }, /pet\.spawn .* not inside pet\.area/);
  fails((m) => { m.pet.spawn = [1800, 1100]; }, /pet\.spawn .* not inside pet\.area \(or is blocked\)/);
  fails((m) => { m.pet.area = [[0, 0], [9000, 0], [0, 100]]; }, /pet\.area must be a polygon .* inside the canvas/);
  fails((m) => { m.pet.spots[0].anim = 'fly'; }, /anim "fly" is not one of/);
  fails((m) => { m.pet.spots[0].seconds = [30, 900]; }, /seconds must be \[min, max\]/);
  fails((m) => { m.pet.spots[0].at = [100, 100]; }, /bench\)\.at .* not inside pet\.area/);
  fails((m) => { m.power.fps = 60; }, /power\.fps must be 1–30/);
  // data only
  fails((m) => { m.html = 'index.html'; }, /html: a wallpaper is pictures and numbers only/);
  fails((m) => { m.url = 'https://example.com'; }, /url: a wallpaper is pictures and numbers only/);
  fails((m) => { m.script = 'x.js'; }, /script: a wallpaper is pictures and numbers only/);
});

test('wallpaper@1 holds the picture budget', () => {
  fails(() => {}, /preview\.webp is 2560×1440 \(at most 1920×1080\)/, { sizes: { ...sizes, 'preview.webp': [2560, 1440] } });
  fails(() => {}, /sky\.webp is 8000×4500/, { sizes: { ...sizes, 'sky.webp': [8000, 4500] } });
  const big = { ...sizes, 'sky.webp': [7680, 4320], 'night.webp': [7680, 4320] }; // 66.4 MP with the rest
  fails(() => {}, /the layers add up to .* MP \(at most 64 MP\)/, { sizes: big });
  fails(() => {}, /front\.png is not a PNG or WebP picture/, { sizes: { ...sizes, 'front.png': undefined } });
});

test('imageSize reads PNG and WebP (VP8X / VP8L / VP8) headers without decoding', () => {
  const png = Buffer.alloc(33);
  png.writeUInt32BE(0x89504e47, 0); png.writeUInt32BE(0x0d0a1a0a, 4); png.writeUInt32BE(13, 8); png.write('IHDR', 12, 'ascii');
  png.writeUInt32BE(2560, 16); png.writeUInt32BE(1440, 20);
  assert.deepStrictEqual(WP.imageSize(png), [2560, 1440]);
  const riff = (chunk) => { const b = Buffer.alloc(40); b.write('RIFF', 0, 'ascii'); b.write('WEBP', 8, 'ascii'); b.write(chunk, 12, 'ascii'); return b; };
  const x = riff('VP8X'); x.writeUIntLE(3839, 24, 3); x.writeUIntLE(2159, 27, 3);
  assert.deepStrictEqual(WP.imageSize(x), [3840, 2160]);
  const l = riff('VP8L'); l[20] = 0x2f; l.writeUInt32LE((1919) | (1079 << 14), 21);
  assert.deepStrictEqual(WP.imageSize(l), [1920, 1080]);
  const v = riff('VP8 '); v[23] = 0x9d; v[24] = 0x01; v[25] = 0x2a; v.writeUInt16LE(960, 26); v.writeUInt16LE(600, 28);
  assert.deepStrictEqual(WP.imageSize(v), [960, 600]);
  assert.strictEqual(WP.imageSize(Buffer.from('not a picture, not a picture, not')), null);
});

test('seaside-terrace: the real pack on disk passes, and checkFolder refuses a stray file', () => {
  const { manifest: m, errors } = GP.checkFolder(PACK);
  assert.deepStrictEqual(errors, []);
  assert.strictEqual(m.engine, 'wallpaper@1');
  assert.strictEqual(m.kind, 'wallpaper');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'wall-'));
  try {
    for (const f of fs.readdirSync(PACK)) fs.copyFileSync(path.join(PACK, f), path.join(tmp, f));
    fs.writeFileSync(path.join(tmp, 'run.png'), 'x');
    assert.ok(GP.checkFolder(tmp).errors.some((x) => /run\.png is not named by the manifest/.test(x)));
    fs.rmSync(path.join(tmp, 'run.png'));
    fs.copyFileSync(path.join(PACK, 'manifest.json'), path.join(tmp, 'manifest.json'));
    fs.writeFileSync(path.join(tmp, m.layers[0].image), 'not a picture');
    assert.ok(GP.checkFolder(tmp).errors.some((x) => /is not a PNG or WebP picture/.test(x)));
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
});
