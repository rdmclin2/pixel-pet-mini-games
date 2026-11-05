'use strict';
// node --test tools/   — the format check (tools/game-pack.js) on the real packs and on broken copies of 她的房间
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const GP = require('./game-pack');

const ROOT = path.join(__dirname, '..');
const HER = path.join(ROOT, 'games', 'her-room', 'pack');
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

test('both packs in the repository pass', () => {
  for (const id of ['pixel-yard', 'her-room']) assert.deepStrictEqual(GP.checkFolder(path.join(ROOT, 'games', id, 'pack')).errors, []);
});

test('her-room: one open theme (dafeiyu) and four coming soon', () => {
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
