'use strict';
// A copy of the app's src/core/game-pack.js (rdmclin2/lobehub-pixel-pet-affection): the format the app checks every
// downloaded game against. Keep it in step with the app — `node scripts/build.js` uses it so a pack that would be
// refused by the app never gets built.
// 小游戏包 (docs/mini-games.md §3): what a downloadable game is on disk. A game pack is data only — pictures and
// one manifest.json — played by the engine built into the app (src/renderer/game/), so nothing downloaded is
// ever run as code. validateManifest() is the one check for every pack, whether it comes from the store, from
// catalog/games/ in a checkout or from a test.
//
// validateManifest() checks the fields every pack has (schema, kind, engine, id, name, version) and then hands the
// rest to the engine's own check:
//
//   yard@1 (像素小院)  { world: { width, height, background }, images: { <key>: <file> }, sprites: <file>,
//                     camera: { zoom, min, max, start: [x, y] }, petHeight, petSpeed, spawn: [x, y],
//                     walk: { cell, area: [[x, y]…], blocked: [shape…] },
//                     objects: [{ id, sprite, x, y, … }], fx: { waterfall, water, fireflies }, quests: [ … ],
//                     lines: { <event>: [text…] } }
//   room@1 (像素房间)  { defaultTheme, activities: { <kind>: { label, verb, anim, seconds, deltas, needs? } },
//                     themes: [{ id, character, status: 'open' | 'soon', name, blurb, motifs, palette, …open fields }],
//                     items, quests, lines }  — docs/her-room-design.md §1 in the app repository
//   <files>         the pictures (.webp / .png) and the sprites indexes (.json) named there; nothing else
//
// packFiles(m) lists every file a manifest names (the store refuses any other file in the folder) and
// spriteFiles(m) the sprites indexes among them; pass those indexes back as `sprites` (yard: the one index;
// room: { <file>: index }).
//
// Electron-free and DOM-free (main, the build script and the tests require() it).
const ENGINES = ['yard@1', 'room@1'];
const ID_RE = /^[a-z0-9][a-z0-9-]{2,63}$/;
const FILE_RE = /^[a-z0-9][a-z0-9._-]{0,63}\.(webp|png|json)$/;
const USE_ANIMS = ['idle', 'sit', 'play', 'pat', 'look', 'happy', 'eat', 'sleep', 'think', 'lookAround'];
const EFFECTS = ['lamp', 'water', 'ripple', 'harvest', 'rest', 'none'];

// room@1
const KINDS = ['sleep', 'work', 'phone', 'music', 'game'];
const STATS = ['energy', 'mood', 'focus', 'fullness'];
const PALETTE_KEYS = ['primary', 'accent', 'base', 'trim'];
const STATUSES = ['open', 'soon'];
const FX = ['dim', 'layer', 'swap', 'hide', 'hold', 'spin', 'frames', 'screen-type', 'emit', 'bob', 'glow'];
const CHARACTERS = ['claude', 'dafeiyu', 'gemini', 'gpt', 'grok']; // the default five (src/characters/<id>.json)
const MAX_THEMES = 12;
const MAX_THEME_FILES = 4;
const MAX_MANIFEST_BYTES = 256 * 1024;
const MAX_DELTA = 40;

const num = (v) => typeof v === 'number' && Number.isFinite(v);
const pt = (p) => Array.isArray(p) && p.length === 2 && num(p[0]) && num(p[1]);
const poly = (p) => Array.isArray(p) && p.length >= 3 && p.every(pt);
const shape = (s) => poly(s) || (s && num(s.cx) && num(s.cy) && num(s.rx) && num(s.ry) && s.rx > 0 && s.ry > 0);
const between = (v, lo, hi) => num(v) && v >= lo && v <= hi;
const str = (v) => typeof v === 'string' && v.trim().length > 0;
const strs = (v) => Array.isArray(v) && v.length > 0 && v.every(str);
const COLOR_RE = /^#[0-9A-Fa-f]{6}$/;

// point in polygon (even–odd) and in a shape (polygon or ellipse)
function inPoly([x, y], p) {
  let inside = false;
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    const [xi, yi] = p[i];
    const [xj, yj] = p[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
const inShape = (q, s) => (Array.isArray(s) ? inPoly(q, s) : ((q[0] - s.cx) / s.rx) ** 2 + ((q[1] - s.cy) / s.ry) ** 2 <= 1);
const walkable = (q, walk) => inPoly(q, walk.area) && !(walk.blocked || []).some((s) => inShape(q, s));

function spriteFiles(m) {
  if (!m || typeof m !== 'object') return [];
  if (m.engine === 'room@1') return (Array.isArray(m.themes) ? m.themes : []).map((t) => t && t.sprites).filter((f) => typeof f === 'string');
  return typeof m.sprites === 'string' ? [m.sprites] : [];
}

function packFiles(m) {
  if (!m || typeof m !== 'object') return [];
  if (m.engine === 'room@1') {
    const out = [];
    for (const t of Array.isArray(m.themes) ? m.themes : []) {
      if (!t || typeof t !== 'object') continue;
      out.push(...Object.values(t.images && typeof t.images === 'object' ? t.images : {}), t.sprites, t.preview);
    }
    return out.filter((f) => typeof f === 'string');
  }
  return [...Object.values(m.images && typeof m.images === 'object' ? m.images : {}), m.sprites].filter(Boolean);
}

// → [error…] (empty = good). `files`: the names in the folder (when checking one on disk), to see every file the
// manifest names is there. `sprites`: the sprites index (yard) or { <file>: index } (room). `characters`: the
// character ids a room theme may belong to. `bytes`: the size of manifest.json on disk.
function validateManifest(m, opts = {}) {
  const e = [];
  if (!m || typeof m !== 'object') return ['manifest is not an object'];
  if (m.schema !== 1) e.push('schema must be 1');
  if (m.kind !== 'game') e.push('kind must be "game"');
  if (!ENGINES.includes(m.engine)) e.push(`engine "${m.engine}" is not one this app plays (${ENGINES.join(', ')})`);
  if (!ID_RE.test(String(m.id || ''))) e.push('id must be 3–64 of a-z 0-9 -');
  if (typeof m.name !== 'string' || !m.name.trim()) e.push('name is missing');
  if (typeof m.version !== 'string' || !/^\d+\.\d+\.\d+$/.test(m.version)) e.push('version must be x.y.z');
  if (m.engine === 'room@1') return e.concat(validateRoom(m, opts));
  return e.concat(validateYard(m, opts));
}

function validateYard(m, { files = null, sprites = null } = {}) {
  const e = [];
  const w = m.world || {};
  if (!(num(w.width) && num(w.height) && w.width > 0 && w.height > 0 && w.width <= 8192 && w.height <= 8192)) e.push('world.width / height must be 1–8192');
  const images = m.images && typeof m.images === 'object' ? m.images : {};
  if (!images.terrain) e.push('images.terrain is missing');
  const named = [...Object.values(images), m.sprites].filter(Boolean);
  for (const f of named) {
    if (!FILE_RE.test(String(f))) e.push(`file name "${f}" is not allowed`);
    else if (files && !files.includes(f)) e.push(`${f} is missing`);
  }
  if (!m.walk || !poly(m.walk.area)) e.push('walk.area must be a polygon');
  else if (m.walk.blocked && !(Array.isArray(m.walk.blocked) && m.walk.blocked.every(shape))) e.push('walk.blocked must be polygons / ellipses');
  if (!pt(m.spawn)) e.push('spawn must be [x, y]');
  if (m.petHeight !== undefined && !(num(m.petHeight) && m.petHeight >= 8 && m.petHeight <= 400)) e.push('petHeight must be 8–400');
  if (m.petSpeed !== undefined && !(num(m.petSpeed) && m.petSpeed > 0 && m.petSpeed <= 400)) e.push('petSpeed must be 1–400');
  if (!Array.isArray(m.objects)) e.push('objects must be a list');
  const ids = new Set();
  for (const [i, o] of (m.objects || []).entries()) {
    const at = `objects[${i}]`;
    if (!o || typeof o.id !== 'string' || !o.id) { e.push(`${at}.id is missing`); continue; }
    if (ids.has(o.id)) e.push(`${at}: id "${o.id}" twice`);
    ids.add(o.id);
    if (!(num(o.x) && num(o.y)) && !poly(o.hit)) e.push(`${at} (${o.id}): x / y`);
    if (typeof o.sprite !== 'string' && !poly(o.hit)) e.push(`${at} (${o.id}): needs a sprite or a hit polygon`);
    if (sprites) for (const s of [].concat(o.sprite || [], (o.stages || []).filter(Boolean))) if (!sprites[s]) e.push(`${at} (${o.id}): no sprite "${s}"`);
    if (o.block && !shape(o.block)) e.push(`${at} (${o.id}): block`);
    e.push(...checkUse(o.use, `${at} (${o.id})`));
    if (o.lights && !(Array.isArray(o.lights) && o.lights.every((l) => l && num(l.x) && num(l.y) && num(l.r)))) e.push(`${at} (${o.id}): lights`);
  }
  for (const [i, q] of (m.quests || []).entries()) {
    if (!q || typeof q.id !== 'string' || typeof q.title !== 'string' || !q.on || typeof q.on.type !== 'string') e.push(`quests[${i}]: id / title / on.type`);
    else if (q.on.obj && ![].concat(q.on.obj).every((id) => ids.has(id))) e.push(`quests[${i}] (${q.id}): on.obj is not an object here`);
  }
  return e;
}

function checkUse(use, at) {
  const e = [];
  if (!use) return e;
  if (!pt(use.at)) e.push(`${at}: use.at`);
  if (use.anim && !USE_ANIMS.includes(use.anim)) e.push(`${at}: use.anim "${use.anim}"`);
  if (use.effect && !EFFECTS.includes(use.effect)) e.push(`${at}: use.effect "${use.effect}"`);
  if (use.seconds && !(Array.isArray(use.seconds) && use.seconds.length === 2 && use.seconds.every(num))) e.push(`${at}: use.seconds`);
  return e;
}

// ---------------------------------------------------------------------------------------------------------------
// room@1 (像素房间): docs/her-room-design.md §1.4

function checkLines(lines, at) {
  if (lines === undefined) return [];
  if (!lines || typeof lines !== 'object' || Array.isArray(lines)) return [`${at} must be { <event>: [text…] }`];
  const e = [];
  for (const [k, v] of Object.entries(lines)) {
    if (k === 'sky' && v && typeof v === 'object' && !Array.isArray(v)) {
      for (const [s, t] of Object.entries(v)) if (!str(t) && !strs(t)) e.push(`${at}.sky.${s} must be text`);
    } else if (!strs(v)) e.push(`${at}.${k} must be a list of text`);
  }
  return e;
}

function checkActivityDefs(acts) {
  const e = [];
  if (!acts || typeof acts !== 'object' || Array.isArray(acts)) return ['activities must be { <kind>: … }'];
  for (const k of Object.keys(acts)) if (!KINDS.includes(k)) e.push(`activities.${k}: kind must be one of ${KINDS.join(', ')}`);
  for (const k of KINDS) {
    const a = acts[k];
    const at = `activities.${k}`;
    if (!a || typeof a !== 'object') { e.push(`${at} is missing`); continue; }
    if (!str(a.label)) e.push(`${at}.label is missing`);
    if (a.verb !== undefined && !str(a.verb)) e.push(`${at}.verb must be text`);
    if (!USE_ANIMS.includes(a.anim)) e.push(`${at}.anim "${a.anim}" is not one of ${USE_ANIMS.join(', ')}`);
    if (!between(a.seconds, 5, 600)) e.push(`${at}.seconds must be 5–600`);
    if (!a.deltas || typeof a.deltas !== 'object' || Array.isArray(a.deltas)) e.push(`${at}.deltas must be { energy, mood, focus, fullness }`);
    else for (const [s, v] of Object.entries(a.deltas)) {
      if (!STATS.includes(s)) e.push(`${at}.deltas.${s}: only ${STATS.join(' / ')}`);
      else if (!between(v, -MAX_DELTA, MAX_DELTA)) e.push(`${at}.deltas.${s} must be −${MAX_DELTA}…${MAX_DELTA}`);
    }
    if (a.needs !== undefined) {
      if (!a.needs || typeof a.needs !== 'object' || Object.keys(a.needs).some((s) => s !== 'energy')) e.push(`${at}.needs: only energy`);
      else if (!between(a.needs.energy, 0, 100)) e.push(`${at}.needs.energy must be 0–100`);
    }
    e.push(...checkLines(a.lines, `${at}.lines`));
  }
  return e;
}

const inWorld = (r, w) => Array.isArray(r) && r.length === 4 && r.every(num) && r[2] > 0 && r[3] > 0 && r[0] >= 0 && r[1] >= 0 && r[0] + r[2] <= w.width && r[1] + r[3] <= w.height;
const ptIn = (p, w) => pt(p) && p[0] >= 0 && p[1] >= 0 && p[0] <= w.width && p[1] <= w.height;

// one prop of an activity: its fx is in the vocabulary (§1.3) and every parameter is in range
function checkProp(p, at, { has, world }) {
  const e = [];
  if (!p || typeof p !== 'object') return [`${at} must be an object`];
  if (!FX.includes(p.fx)) return [`${at}: fx "${p.fx}" is not one of ${FX.join(', ')}`];
  const sprite = (k) => {
    if (typeof p[k] !== 'string') e.push(`${at} (${p.fx}): ${k} is missing`);
    else if (!has(p[k])) e.push(`${at} (${p.fx}): no sprite "${p[k]}"`);
  };
  const sprites = () => {
    if (!Array.isArray(p.sprites) || !p.sprites.length) e.push(`${at} (${p.fx}): sprites must be a list`);
    else for (const s of p.sprites) if (typeof s !== 'string' || !has(s)) e.push(`${at} (${p.fx}): no sprite "${s}"`);
  };
  const xy = () => { if (!ptIn([p.x, p.y], world)) e.push(`${at} (${p.fx}): x / y must be inside the world`); };
  const rect = () => { if (!inWorld(p.rect, world)) e.push(`${at} (${p.fx}): rect must be [x, y, w, h] inside the world`); };
  const range = (k, lo, hi, optional = false) => {
    if (optional && p[k] === undefined) return;
    if (!between(p[k], lo, hi)) e.push(`${at} (${p.fx}): ${k} must be ${lo}–${hi}`);
  };
  switch (p.fx) {
    case 'dim': range('to', 0.3, 1); break;
    case 'layer': sprite('sprite'); xy(); if (p.under !== undefined && p.under !== 'front') e.push(`${at} (layer): under must be "front"`); break;
    case 'swap': sprite('sprite'); sprite('to'); break;
    case 'hide': sprite('sprite'); break;
    case 'hold':
      sprite('sprite');
      if (!(Array.isArray(p.hand) && p.hand.length === 2 && p.hand.every((v) => between(v, 0, 1)))) e.push(`${at} (hold): hand must be [u, v] in 0–1`);
      break;
    case 'spin': sprite('sprite'); xy(); range('squash', 0.1, 1); range('rpm', 1, 120); break;
    case 'frames': rect(); sprites(); range('fps', 1, 30); break;
    case 'screen-type':
      rect(); range('rows', 1, 20);
      if (!(PALETTE_KEYS.includes(p.color) || COLOR_RE.test(String(p.color)))) e.push(`${at} (screen-type): color must be a palette key or #RRGGBB`);
      if (p.sprite !== undefined) sprite('sprite');
      break;
    case 'emit':
      sprites();
      if (!(p.from === 'head' || ptIn(p.from, world))) e.push(`${at} (emit): from must be [x, y] inside the world or "head"`);
      range('every', 0.2, 30); range('rise', 0, 400, true);
      break;
    case 'bob': if (p.target !== 'pet') e.push(`${at} (bob): target must be "pet"`); range('period', 0.2, 10); range('amp', 0, 20); break;
    case 'glow': xy(); range('r', 1, 1024); break;
    default: break;
  }
  return e;
}

function checkTheme(t, i, { files, sprites, characters, kinds }) {
  const at = `themes[${i}]`;
  const e = [];
  if (!t || typeof t !== 'object') return [`${at} must be an object`];
  const name = `${at} (${t.id})`;
  if (!ID_RE.test(String(t.id || ''))) e.push(`${at}.id must be 3–64 of a-z 0-9 -`);
  if (!characters.includes(t.character)) e.push(`${name}: character "${t.character}" is not one of ${characters.join(', ')}`);
  if (!STATUSES.includes(t.status)) e.push(`${name}: status must be open or soon`);
  if (!str(t.name)) e.push(`${name}: name is missing`);
  if (!str(t.blurb)) e.push(`${name}: blurb is missing`);
  if (!strs(t.motifs)) e.push(`${name}: motifs must be a list of text`);
  if (!t.palette || typeof t.palette !== 'object') e.push(`${name}: palette is missing`);
  else for (const k of PALETTE_KEYS) if (!COLOR_RE.test(String(t.palette[k]))) e.push(`${name}: palette.${k} must be #RRGGBB`);

  // its files: named with the theme id in front, at most MAX_THEME_FILES, and there
  const own = [...Object.values(t.images && typeof t.images === 'object' ? t.images : {}), t.sprites, t.preview].filter((f) => f !== undefined);
  if (own.length > MAX_THEME_FILES) e.push(`${name}: at most ${MAX_THEME_FILES} files per theme`);
  for (const f of own) {
    if (!FILE_RE.test(String(f))) e.push(`${name}: file name "${f}" is not allowed`);
    else if (!String(f).startsWith(`${t.id}-`)) e.push(`${name}: file "${f}" must start with "${t.id}-"`);
    else if (files && !files.includes(f)) e.push(`${name}: ${f} is missing`);
  }
  if (t.status !== 'open') return e;

  // an open theme is a playable room
  const w = t.world || {};
  const okWorld = between(w.width, 256, 4096) && between(w.height, 256, 4096);
  if (!okWorld) e.push(`${name}: world.width / height must be 256–4096`);
  if (w.background !== undefined && !COLOR_RE.test(String(w.background))) e.push(`${name}: world.background must be #RRGGBB`);
  const world = okWorld ? w : { width: 4096, height: 4096 };
  if (!t.images || typeof t.images.room !== 'string') e.push(`${name}: images.room is missing`);
  if (!t.images || typeof t.images.atlas !== 'string') e.push(`${name}: images.atlas is missing`);
  if (typeof t.sprites !== 'string') e.push(`${name}: sprites is missing`);
  if (!(t.outfit === undefined || str(t.outfit))) e.push(`${name}: outfit must be an outfit id`);
  if (t.smooth !== undefined && typeof t.smooth !== 'boolean') e.push(`${name}: smooth must be true / false`);
  if (t.petHeight !== undefined && !between(t.petHeight, 8, 400)) e.push(`${name}: petHeight must be 8–400`);
  if (t.petSpeed !== undefined && !(num(t.petSpeed) && t.petSpeed > 0 && t.petSpeed <= 400)) e.push(`${name}: petSpeed must be 1–400`);
  const index = sprites && typeof t.sprites === 'string' ? sprites[t.sprites] : null;
  if (sprites && typeof t.sprites === 'string' && !index) e.push(`${name}: ${t.sprites} could not be read`);
  const has = (s) => !index || Boolean(index[s]);

  const walk = t.walk;
  const okWalk = walk && poly(walk.area) && (walk.blocked === undefined || (Array.isArray(walk.blocked) && walk.blocked.every(shape)));
  if (!okWalk) e.push(`${name}: walk.area must be a polygon (walk.blocked polygons / ellipses)`);
  const onFloor = (p, what) => {
    if (!pt(p)) e.push(`${name}: ${what} must be [x, y]`);
    else if (okWalk && !walkable(p, walk)) e.push(`${name}: ${what} [${p}] is not on the walkable floor`);
  };
  onFloor(t.spawn, 'spawn');
  onFloor(t.door, 'door');

  const furn = new Map();
  if (!Array.isArray(t.furniture) || !t.furniture.length) e.push(`${name}: furniture must be a list`);
  for (const [j, f] of (Array.isArray(t.furniture) ? t.furniture : []).entries()) {
    const fat = `${name}.furniture[${j}]`;
    if (!f || typeof f.id !== 'string' || !f.id) { e.push(`${fat}.id is missing`); continue; }
    if (furn.has(f.id)) e.push(`${fat}: id "${f.id}" twice`);
    furn.set(f.id, f);
    if (!ptIn([f.x, f.y], world)) e.push(`${fat} (${f.id}): x / y must be inside the world`);
    if (typeof f.sprite !== 'string') e.push(`${fat} (${f.id}): sprite is missing`);
    else if (!has(f.sprite)) e.push(`${fat} (${f.id}): no sprite "${f.sprite}"`);
    if (f.front !== undefined && (typeof f.front !== 'string' || !has(f.front))) e.push(`${fat} (${f.id}): no front sprite "${f.front}"`);
    if (f.label !== undefined && !str(f.label)) e.push(`${fat} (${f.id}): label must be text`);
    if (f.hit !== undefined && !poly(f.hit)) e.push(`${fat} (${f.id}): hit must be a polygon`);
    if (f.block !== undefined && !shape(f.block)) e.push(`${fat} (${f.id}): block`);
    e.push(...checkUse(f.use, `${fat} (${f.id})`));
    if (f.use && pt(f.use.at) && okWalk && !walkable(f.use.at, walk)) e.push(`${fat} (${f.id}): use.at is not on the walkable floor`);
  }

  const acts = t.activities && typeof t.activities === 'object' && !Array.isArray(t.activities) ? t.activities : null;
  if (!acts) e.push(`${name}: activities must be { <kind>: … }`);
  else {
    for (const k of Object.keys(acts)) if (!KINDS.includes(k)) e.push(`${name}.activities.${k}: kind must be one of ${KINDS.join(', ')}`);
    for (const k of kinds) {
      const a = acts[k];
      const aat = `${name}.activities.${k}`;
      if (!a || typeof a !== 'object') { e.push(`${aat} is missing (an open theme has all five)`); continue; }
      for (const no of ['seconds', 'deltas', 'needs']) if (a[no] !== undefined) e.push(`${aat}.${no}: a theme cannot change the numbers (set them in the top-level activities)`);
      if (!furn.has(a.at)) e.push(`${aat}.at "${a.at}" is not a piece of furniture here`);
      onFloor(a.spot, `activities.${k}.spot`);
      if (a.face !== undefined && !['left', 'right'].includes(a.face)) e.push(`${aat}.face must be left or right`);
      if (a.pose !== undefined && a.pose !== 'tucked') e.push(`${aat}.pose must be "tucked"`);
      // lying down needs the place to lie: without `lie` she would lie where she stands, on the floor beside the bed
      if (a.pose === 'tucked' && a.lie === undefined) e.push(`${aat}: pose "tucked" needs lie [x, y] (where her feet go on the bed)`);
      if (a.anim !== undefined && !USE_ANIMS.includes(a.anim)) e.push(`${aat}.anim "${a.anim}"`);
      if (a.bubble !== undefined && !ptIn(a.bubble, world)) e.push(`${aat}.bubble must be [x, y] inside the world`);
      if (a.lieScale !== undefined && !between(a.lieScale, 0.3, 1)) e.push(`${aat}.lieScale must be 0.3–1`);
      if (a.props !== undefined && !Array.isArray(a.props)) e.push(`${aat}.props must be a list`);
      for (const [n, p] of (Array.isArray(a.props) ? a.props : []).entries()) e.push(...checkProp(p, `${aat}.props[${n}]`, { has, world }));
      if (a.lines !== undefined) {
        if (!a.lines || typeof a.lines !== 'object') e.push(`${aat}.lines must be { doing, done }`);
        else for (const [s, v] of Object.entries(a.lines)) if (!strs(v)) e.push(`${aat}.lines.${s} must be a list of text`);
      }
    }
  }
  if (t.lights !== undefined && !(Array.isArray(t.lights) && t.lights.every((l) => l && ptIn([l.x, l.y], world) && between(l.r, 1, 1024) && (l.on === undefined || KINDS.includes(l.on))))) e.push(`${name}: lights must be [{ x, y, r, on? }] inside the world`);
  if (t.window !== undefined && !(t.window && inWorld(t.window.rect, world) && (t.window.arch === undefined || typeof t.window.arch === 'boolean'))) e.push(`${name}: window.rect must be [x, y, w, h] inside the world`);
  e.push(...checkLines(t.lines, `${name}.lines`));
  return e;
}

function validateRoom(m, { files = null, sprites = null, characters = CHARACTERS, bytes = null } = {}) {
  const e = [];
  const size = num(bytes) ? bytes : Buffer.byteLength(JSON.stringify(m));
  if (size > MAX_MANIFEST_BYTES) e.push(`manifest.json is ${size} bytes (at most ${MAX_MANIFEST_BYTES})`);
  e.push(...checkActivityDefs(m.activities));
  const themes = Array.isArray(m.themes) ? m.themes : null;
  if (!themes || !themes.length) e.push('themes must be a list');
  else if (themes.length > MAX_THEMES) e.push(`at most ${MAX_THEMES} themes`);
  const ids = new Set();
  const open = new Set();
  const furniture = new Set();
  for (const [i, t] of (themes || []).entries()) {
    if (t && typeof t.id === 'string') {
      if (ids.has(t.id)) e.push(`themes[${i}]: id "${t.id}" twice`);
      ids.add(t.id);
      if (t.status === 'open') open.add(t.id);
      for (const f of Array.isArray(t.furniture) ? t.furniture : []) if (f && f.id) furniture.add(f.id);
    }
    e.push(...checkTheme(t, i, { files, sprites, characters, kinds: KINDS }));
  }
  if (themes && !open.size) e.push('at least one theme must be open');
  if (!open.has(m.defaultTheme)) e.push(`defaultTheme "${m.defaultTheme}" is not an open theme`);
  if (m.items !== undefined && !(m.items && typeof m.items === 'object' && !Array.isArray(m.items))) e.push('items must be an object');
  if (m.quests !== undefined && !Array.isArray(m.quests)) e.push('quests must be a list');
  const qids = new Set();
  for (const [i, q] of (Array.isArray(m.quests) ? m.quests : []).entries()) {
    if (!q || typeof q.id !== 'string' || typeof q.title !== 'string' || !q.on || typeof q.on.type !== 'string') { e.push(`quests[${i}]: id / title / on.type`); continue; }
    const at = `quests[${i}] (${q.id})`;
    if (qids.has(q.id)) e.push(`${at}: id twice`);
    qids.add(q.id);
    if (q.on.kind !== undefined && !KINDS.includes(q.on.kind)) e.push(`${at}: on.kind must be one of ${KINDS.join(', ')}`);
    if (q.on.theme !== undefined && !ids.has(q.on.theme)) e.push(`${at}: on.theme is not a theme here`);
    if (q.on.complete !== undefined && typeof q.on.complete !== 'boolean') e.push(`${at}: on.complete must be true / false`);
    if (q.on.obj !== undefined && ![].concat(q.on.obj).every((id) => furniture.has(id))) e.push(`${at}: on.obj is not a piece of furniture here`);
    if (q.count !== undefined && !(Number.isInteger(q.count) && q.count >= 1 && q.count <= 100)) e.push(`${at}: count must be 1–100`);
    if (q.distinct !== undefined && q.distinct !== 'kind') e.push(`${at}: distinct must be "kind"`);
  }
  e.push(...checkLines(m.lines, 'lines'));
  return e;
}

// A folder on disk, the way the app's game-store checkFolder() takes it: a manifest that validates and no file the
// manifest does not name. → { manifest, files, errors }
function checkFolder(dir) {
  const fs = require('node:fs');
  const path = require('node:path');
  const read = (f) => { try { return JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')); } catch { return null; } };
  const m = read('manifest.json');
  if (!m) return { manifest: null, files: [], errors: ['manifest.json is missing or not JSON'] };
  const files = fs.readdirSync(dir);
  const sheets = spriteFiles(m);
  const sprites = m.engine === 'room@1' ? Object.fromEntries(sheets.filter((f) => files.includes(f)).map((f) => [f, read(f)]).filter(([, v]) => v)) : (sheets[0] ? read(sheets[0]) : null);
  const errors = validateManifest(m, { files, sprites, bytes: fs.statSync(path.join(dir, 'manifest.json')).size });
  const named = new Set(['manifest.json', ...packFiles(m)]);
  for (const f of files) {
    if (!fs.lstatSync(path.join(dir, f)).isFile()) errors.push(`${f}: a folder (the app takes flat packs only)`);
    else if (!named.has(f)) errors.push(`${f} is not named by the manifest (the app refuses extra files)`);
  }
  return { manifest: m, files, errors };
}

module.exports = {
  ENGINES, ID_RE, FILE_RE, USE_ANIMS, EFFECTS, KINDS, STATS, FX, CHARACTERS,
  validateManifest, validateYard, validateRoom, packFiles, spriteFiles, walkable, checkFolder,
};

// node tools/game-pack.js <games/<id> | games/<id>/pack> …  → checks each pack folder, exit 1 when one fails
if (require.main === module) {
  const fs = require('node:fs');
  const path = require('node:path');
  const args = process.argv.slice(2);
  if (!args.length) { console.error('usage: node tools/game-pack.js games/<id> [games/<id> …]'); process.exit(2); }
  let bad = 0;
  for (const a of args) {
    const dir = fs.existsSync(path.join(a, 'pack', 'manifest.json')) ? path.join(a, 'pack') : a;
    const { manifest: m, files, errors } = checkFolder(dir);
    if (errors.length) {
      bad++;
      console.log(`FAIL ${dir}: ${errors.length} error(s)`);
      for (const x of errors) console.log(`  - ${x}`);
      continue;
    }
    const bytes = files.reduce((n, f) => n + fs.statSync(path.join(dir, f)).size, 0);
    console.log(`ok   ${dir}: ${m.id} ${m.version} (${m.engine}), ${files.length} files, ${bytes} bytes`);
    if (m.engine === 'room@1') {
      for (const t of m.themes) {
        const extra = t.status === 'open' ? `  furniture ${t.furniture.length}, activities ${Object.keys(t.activities).join('/')}, outfit ${t.outfit || '-'}` : '';
        console.log(`     theme ${t.id.padEnd(8)} ${t.status.padEnd(4)} ${t.character.padEnd(8)} ${t.name}${extra}`);
      }
      console.log(`     quests ${(m.quests || []).length}, default theme ${m.defaultTheme}`);
    }
  }
  process.exit(bad ? 1 : 0);
}
