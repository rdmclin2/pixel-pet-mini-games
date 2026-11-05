'use strict';
// node --test tools/   — the format check (tools/game-pack.js) on the real packs and on broken copies of 像素房间
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const GP = require('./game-pack');

const ROOT = path.join(__dirname, '..');
const HER = path.join(ROOT, 'games', 'pixel-room', 'pack');
const read = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));
const base = () => read(path.join(HER, 'manifest.json'));
const files = fs.readdirSync(HER);
const sprites = { 'dafeiyu-sprites.json': read(path.join(HER, 'dafeiyu-sprites.json')) };
const check = (m) => GP.validateManifest(m, { files, sprites });
const fails = (edit, re) => {
  const m = base();
  edit(m);
  const e = check(m);
  assert.ok(e.some((x) => re.test(x)), `expected an error like ${re}, got ${JSON.stringify(e)}`);
};
const room = (m) => m.themes.find((t) => t.id === 'dafeiyu');

test('every pack in the repository passes', () => {
  for (const id of ['pixel-yard', 'pixel-room', 'her-room']) assert.deepStrictEqual(GP.checkFolder(path.join(ROOT, 'games', id, 'pack')).errors, []);
});

test('pixel-room: one open theme (dafeiyu) and four coming soon', () => {
  const m = base();
  assert.strictEqual(m.engine, 'room@1');
  assert.deepStrictEqual(m.themes.map((t) => [t.id, t.status]), [['dafeiyu', 'open'], ['claude', 'soon'], ['grok', 'soon'], ['gemini', 'soon'], ['gpt', 'soon']]);
  assert.strictEqual(room(m).outfit, 'daily');
});

test('room@1 refuses broken packs', () => {
  fails((m) => { delete room(m).activities.game; }, /activities\.game is missing/);
  fails((m) => { room(m).activities.work.at = 'sofa'; }, /work\.at "sofa" is not a piece of furniture/);
  fails((m) => { room(m).activities.phone.spot = [500, 100]; }, /phone\.spot .* not on the walkable floor/);
  fails((m) => { room(m).activities.music.props.push({ fx: 'explode' }); }, /fx "explode" is not one of/);
  fails((m) => { room(m).activities.sleep.props[0].to = 0.1; }, /dim\): to must be 0\.3–1/);
  fails((m) => { room(m).activities.phone.props[1].hand = [1.5, 0.5]; }, /hand must be \[u, v\] in 0–1/);
  fails((m) => { room(m).activities.game.props[0].rect = [1000, 300, 83, 57]; }, /rect must be .* inside the world/);
  fails((m) => { room(m).activities.music.props[0].sprite = 'nope'; }, /no sprite "nope"/);
  fails((m) => { m.activities.sleep.deltas.energy = 80; }, /deltas\.energy must be/);
  fails((m) => { m.activities.sleep.deltas.affection = 5; }, /deltas\.affection: only/);
  fails((m) => { m.activities.work.seconds = 2; }, /seconds must be 5–600/);
  fails((m) => { delete room(m).activities.sleep.lie; }, /pose "tucked" needs lie/); // she would lie on the floor beside the bed
  fails((m) => { room(m).activities.sleep.deltas = { energy: 40 }; }, /a theme cannot change the numbers/);
  fails((m) => { room(m).images.room = 'claude-room.webp'; }, /must start with "dafeiyu-"/);
  fails((m) => { room(m).images.room = 'dafeiyu-other.webp'; }, /dafeiyu-other\.webp is missing/);
  fails((m) => { m.themes[1].character = 'nobody'; }, /character "nobody" is not one of/);
  fails((m) => { m.themes[2].palette.base = 'red'; }, /palette\.base must be #RRGGBB/);
  fails((m) => { m.themes[3].status = 'later'; }, /status must be open or soon/);
  fails((m) => { m.defaultTheme = 'claude'; }, /defaultTheme "claude" is not an open theme/);
  fails((m) => { room(m).status = 'soon'; }, /at least one theme must be open/);
  fails((m) => { m.quests[0].on.kind = 'swim'; }, /on\.kind must be one of/);
  fails((m) => { m.quests[0].on.theme = 'castle'; }, /on\.theme is not a theme here/);
  fails((m) => { m.lines.big = ['x'.repeat(300 * 1024)]; }, /manifest\.json is \d+ bytes/);
});

test('a soon theme needs only the basic fields', () => {
  const m = base();
  assert.deepStrictEqual(Object.keys(m.themes[1]).sort(), ['blurb', 'character', 'id', 'motifs', 'name', 'palette', 'status']);
  assert.deepStrictEqual(check(m), []);
});

test('packFiles lists every file the store may keep; anything else is refused', () => {
  assert.deepStrictEqual(GP.packFiles(base()).sort(), ['dafeiyu-atlas.webp', 'dafeiyu-room.webp', 'dafeiyu-sprites.json']);
  const yard = read(path.join(ROOT, 'games', 'pixel-yard', 'pack', 'manifest.json'));
  assert.deepStrictEqual(GP.packFiles(yard).sort(), ['atlas.webp', 'sprites.json', 'terrain.webp']);
});

// ---- 她的房间 (illustrated-room@1): the real pack, broken copies of it and the room format's room to grow ---------
const ROOM = path.join(ROOT, 'games', 'her-room', 'pack');
const her = () => read(path.join(ROOM, 'manifest.json'));
const herFiles = fs.readdirSync(ROOM);
const herSprites = { 'dafeiyu-parts.json': read(path.join(ROOM, 'dafeiyu-parts.json')) };
const herCheck = (m, files = herFiles) => GP.validateManifest(m, { files, sprites: herSprites });
const herFails = (edit, re) => {
  const m = her();
  edit(m.rooms[0], m);
  const e = herCheck(m);
  assert.ok(e.some((x) => re.test(x)), `expected an error like ${re}, got ${JSON.stringify(e)}`);
};

test('her-room: the pack passes as the app takes it (flat, only named files)', () => {
  assert.deepStrictEqual(GP.checkFolder(ROOM).errors, []);
  const m = her();
  assert.strictEqual(m.id, 'her-room');
  assert.strictEqual(m.name, '她的房间');
  assert.strictEqual(m.engine, 'illustrated-room@1');
});

test('her-room: every activity has its own picture, each with the lamp off and on', () => {
  const r = her().rooms[0];
  const shown = Object.entries(r.states).filter(([, s]) => !s.transient);
  for (const kind of ['sleep', 'work', 'phone', 'music', 'game', 'idle']) assert.ok(shown.some(([, s]) => s.activity === kind), kind);
  for (const [k, s] of Object.entries(r.states)) {
    assert.strictEqual(s.images.off, `dafeiyu-${k}-off.webp`);
    assert.strictEqual(s.images.lit, `dafeiyu-${k}-lit.webp`);
  }
  const pictures = Object.values(r.states).flatMap((s) => [s.images.off, s.images.lit]);
  assert.strictEqual(new Set(pictures).size, pictures.length, 'no state borrows another one\'s picture');
  assert.ok(r.states.idle.variants.includes('idle-lazy') && r.states['idle-lazy'].activity === 'idle', '犯懒 is a 发呆');
});

test('her-room: screens are annotated per state, blinks are the atlas\'s patches, bokeh sits on the painted lights', () => {
  const r = her().rooms[0];
  const want = { idle: ['phone', 'lock'], 'idle-lazy': ['phone', 'lock'], phone: ['phone', 'clips'], music: ['phone', 'player'], sleep: ['phone', 'lock'], work: ['laptop', 'page'], game: ['laptop', 'game'] };
  for (const [k, [id, content]] of Object.entries(want)) {
    assert.strictEqual(r.states[k].screens[id].content, content, k);
    assert.ok(r.states[k].screens[id].corners, `${k} has its corners`);
  }
  for (const k of ['idle', 'idle-lazy', 'phone']) {
    const b = r.states[k].blink;
    for (const n of [b.sprite.off, b.sprite.lit]) assert.ok(herSprites['dafeiyu-parts.json'][n], `${k}: ${n}`);
  }
  for (const k of ['music', 'sleep', 'work', 'game']) assert.strictEqual(r.states[k].blink, null, `${k}: eyes closed or back to the camera`);
  for (const [k, s] of Object.entries(r.states)) if (!s.transient) assert.ok(s.breath, `${k} breathes`);
  assert.ok(r.window.bokeh.spots.length >= 12);
});

test('her-room: broken packs are refused', () => {
  herFails((r) => { delete r.states.music; }, /no state for the activity music/);
  herFails((r) => { r.states.idle.images.lit = 'dafeiyu-gone-lit.webp'; }, /dafeiyu-gone-lit\.webp is missing/);
  herFails((r) => { r.states.idle.images.lit = 'other-idle-lit.webp'; }, /must start with "dafeiyu-"/);
  herFails((r) => { r.states.work.screens.laptop.corners = [[0, 0], [10, 10], [0, 10], [10, 0]]; }, /convex quad/);
  herFails((r) => { r.states.idle.blink.sprite.off = 'nope'; }, /no sprite "nope"/);
  herFails((r) => { r.states.work.enterVia = 'phone'; }, /enterVia must be a transient state/);
  herFails((r) => { r.window.bokeh.spots = [[-5, 10, 8]]; }, /bokeh\.spots/);
  herFails((r) => { r.defaultState = 'stand'; }, /defaultState must be a state that is not transient/);
});

test('her-room: the format takes more rooms and more states without touching the app', () => {
  const m = her();
  const room = m.rooms[0];
  // another open room: the same fields under its own id and file prefix
  const other = JSON.parse(JSON.stringify(room).replaceAll('dafeiyu-', 'claude-'));
  other.id = 'claude'; other.character = 'claude'; other.name = '午后的书房';
  m.rooms.push(other);
  const names = JSON.stringify(other).match(/claude-[a-z-]+\.(?:webp|json)/g);
  const sprites = { ...herSprites, 'claude-parts.json': herSprites['dafeiyu-parts.json'] };
  assert.deepStrictEqual(GP.validateManifest(m, { files: [...herFiles, ...names], sprites }), []);
  // one more state of an activity in a room
  const m2 = her();
  m2.rooms[0].states['phone-sofa'] = { ...m2.rooms[0].states.phone };
  assert.deepStrictEqual(herCheck(m2), []);
  // a coming-soon room needs no pictures
  const m3 = her();
  m3.rooms.push({ id: 'claude', character: 'claude', status: 'soon', name: '午后的书房' });
  assert.deepStrictEqual(herCheck(m3), []);
});

test('pixel-room keeps its new display name and leaves 她的房间 to the illustrated game', () => {
  const m = read(path.join(ROOT, 'games', 'pixel-room', 'pack', 'manifest.json'));
  assert.strictEqual(m.id, 'pixel-room');
  assert.strictEqual(m.name, '像素房间');
  assert.strictEqual(m.engine, 'room@1');
  assert.doesNotMatch(fs.readFileSync(path.join(ROOT, 'games', 'pixel-room', 'store.json'), 'utf8'), /她的房间/);
});
