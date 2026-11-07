'use strict';
// The wallpaper@1 format check, written from the app's design (rdmclin2/lobehub-pixel-pet-affection
// docs/wallpaper-mode.md §3) before the app's engine existed. The app now has its own src/core/wallpaper-pack.js
// (stricter: canvas / z / speed ranges, forbidden fields such as entry / html / script / url, picture sizes read from
// the file headers); this copy is NOT byte-identical to it. `node scripts/build.js` uses this copy as a first gate;
// the authoritative check is the app's: run, from the app checkout,
//   node scripts/check-store-contract.js <this repository> --cdn
// which validates every pack with the app's own install check (game-store.js checkFolder) and every catalog entry with
// its store index (game-index.js), and compares the archives on the CDN (docs/wallpaper-mode.md §9.2).
//
// 壁纸包 (wallpaper@1): a live desktop wallpaper she lives in. Data only, like a game pack: one manifest.json plus
// the layer pictures (.webp / .png) it names — no entry, script, HTML, shader or URL. The engine built into the app
// (src/renderer/wallpaper/) draws the layers back to front by z, puts her in at pet.z, walks her inside pet.area and
// sends her to pet.spots.
//
//   { schema: 1, kind: 'wallpaper', engine: 'wallpaper@1', id, name, version, description?, credit?,
//     canvas: { width, height, background?, fit?, focus? },  preview: <file>,
//     layers: [{ id, image, z, drift?, loop?, opacity?, blend?, phases? }],
//     sky?: { phases?, weather?, tint? },  fx?: { rain?, snow?, fireflies?, lights? },
//     pet: { height, speed?, spawn, z?, area, blocked?, spots? },  power?: { fps } }
//
// validateWallpaper(m, { files, sizes, fileRe }) checks everything past the common fields (game-pack.js
// validateManifest checks schema / engine / id / name / version and that kind is "wallpaper"). `files`: the names in
// the folder. `sizes`: { <file>: [width, height] } read from the file headers (imageSize()), to hold the pixel budget.
// namedFiles(m) lists every file the manifest names (preview + every layer image); the store refuses any other file.
//
// Electron-free and DOM-free.

const PHASES = ['dawn', 'day', 'dusk', 'night'];
const WEATHER = ['clear', 'cloudy', 'rain', 'storm', 'snow', 'fog'];
const BLENDS = ['normal', 'add', 'screen', 'multiply'];
const FITS = ['cover', 'contain'];
// the same as game-pack.js USE_ANIMS (kept here so this file needs nothing else)
const USE_ANIMS = ['idle', 'sit', 'play', 'pat', 'look', 'happy', 'eat', 'sleep', 'think', 'lookAround'];
const IMAGE_RE = /^[a-z0-9][a-z0-9._-]{0,63}\.(webp|png)$/;
const LIMITS = {
  layers: 16, spots: 16, lights: 32, fireflies: 40, fps: 30, drift: 200,
  imageW: 7680, imageH: 4320, previewW: 1920, previewH: 1080, totalPixels: 64 * 1000 * 1000,
  description: 400, credit: 200, name: 40,
};

const num = (v) => typeof v === 'number' && Number.isFinite(v);
const int = (v) => Number.isInteger(v);
const between = (v, lo, hi) => num(v) && v >= lo && v <= hi;
const pt = (p) => Array.isArray(p) && p.length === 2 && num(p[0]) && num(p[1]);
const poly = (p) => Array.isArray(p) && p.length >= 3 && p.every(pt);
const ellipse = (s) => s && !Array.isArray(s) && num(s.cx) && num(s.cy) && num(s.rx) && num(s.ry) && s.rx > 0 && s.ry > 0;
const shape = (s) => poly(s) || ellipse(s);
const subset = (v, of) => Array.isArray(v) && v.every((x) => of.includes(x));
const COLOR_RE = /^#[0-9A-Fa-f]{6}$/;

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
const walkable = (q, pet) => inPoly(q, pet.area) && !(pet.blocked || []).some((s) => inShape(q, s));

function namedFiles(m) {
  if (!m || typeof m !== 'object') return [];
  const out = [m.preview, ...(Array.isArray(m.layers) ? m.layers : []).map((l) => l && l.image)];
  return [...new Set(out.filter((f) => typeof f === 'string'))];
}
const spriteFiles = () => []; // a wallpaper has no sprites index

// [width, height] of a PNG or WebP from its header, without decoding it; null when it is neither
function imageSize(buf) {
  if (!Buffer.isBuffer(buf) || buf.length < 30) return null;
  if (buf.readUInt32BE(0) === 0x89504e47 && buf.toString('ascii', 12, 16) === 'IHDR') return [buf.readUInt32BE(16), buf.readUInt32BE(20)];
  if (buf.toString('ascii', 0, 4) !== 'RIFF' || buf.toString('ascii', 8, 12) !== 'WEBP') return null;
  const chunk = buf.toString('ascii', 12, 16);
  if (chunk === 'VP8X') return [1 + buf.readUIntLE(24, 3), 1 + buf.readUIntLE(27, 3)];
  if (chunk === 'VP8L' && buf[20] === 0x2f) {
    const b = buf.readUInt32LE(21);
    return [1 + (b & 0x3fff), 1 + ((b >>> 14) & 0x3fff)];
  }
  if (chunk === 'VP8 ' && buf[23] === 0x9d && buf[24] === 0x01 && buf[25] === 0x2a) return [buf.readUInt16LE(26) & 0x3fff, buf.readUInt16LE(28) & 0x3fff];
  return null;
}

function checkPhases(v, at) {
  if (v === undefined) return [];
  return Array.isArray(v) && v.length && subset(v, PHASES) && new Set(v).size === v.length ? [] : [`${at} must be a list of ${PHASES.join(' / ')}`];
}

// → [error…] (empty = good)
function validateWallpaper(m, { files = null, sizes = null, fileRe = IMAGE_RE } = {}) {
  const e = [];
  if (!m || typeof m !== 'object') return ['manifest is not an object'];
  if (m.kind !== 'wallpaper') e.push('kind must be "wallpaper"');
  if (typeof m.name === 'string' && m.name.length > LIMITS.name) e.push(`name must be at most ${LIMITS.name} characters`);
  if (m.description !== undefined && !(typeof m.description === 'string' && m.description.length <= LIMITS.description)) e.push(`description must be text of at most ${LIMITS.description} characters`);
  if (m.credit !== undefined && !(typeof m.credit === 'string' && m.credit.length <= LIMITS.credit)) e.push(`credit must be text of at most ${LIMITS.credit} characters`);
  // data only: nothing that would be loaded or run
  for (const k of ['entry', 'main', 'html', 'script', 'scripts', 'shader', 'url', 'video']) if (m[k] !== undefined) e.push(`${k}: a wallpaper is pictures and numbers only`);

  // canvas: the design space every coordinate is in
  const c = m.canvas && typeof m.canvas === 'object' ? m.canvas : {};
  const okCanvas = int(c.width) && int(c.height) && between(c.width, 640, 7680) && between(c.height, 360, 4320);
  if (!okCanvas) e.push('canvas.width / height must be whole numbers, 640–7680 / 360–4320');
  const W = okCanvas ? c.width : 7680;
  const H = okCanvas ? c.height : 4320;
  if (c.background !== undefined && !COLOR_RE.test(String(c.background))) e.push('canvas.background must be #rrggbb');
  if (c.fit !== undefined && !FITS.includes(c.fit)) e.push(`canvas.fit must be ${FITS.join(' or ')}`);
  if (c.focus !== undefined && !(pt(c.focus) && c.focus.every((v) => between(v, 0, 1)))) e.push('canvas.focus must be [x, y] in 0–1');
  const inCanvas = (p) => pt(p) && p[0] >= 0 && p[1] >= 0 && p[0] <= W && p[1] <= H;

  // files: only pictures, all there; sizes within the budget
  const image = (f, at) => {
    if (!fileRe.test(String(f)) || !IMAGE_RE.test(String(f))) { e.push(`${at}: file name "${f}" is not allowed (.webp / .png)`); return null; }
    if (files && !files.includes(f)) { e.push(`${at}: ${f} is missing`); return null; }
    if (!sizes) return null;
    const s = sizes[f];
    if (!s) { e.push(`${at}: ${f} is not a PNG or WebP picture`); return null; }
    return s;
  };
  if (m.preview === undefined) e.push('preview is missing');
  else {
    const s = image(m.preview, 'preview');
    if (s && (s[0] > LIMITS.previewW || s[1] > LIMITS.previewH)) e.push(`preview: ${m.preview} is ${s[0]}×${s[1]} (at most ${LIMITS.previewW}×${LIMITS.previewH})`);
  }

  const layers = Array.isArray(m.layers) ? m.layers : null;
  if (!layers || !layers.length || layers.length > LIMITS.layers) e.push(`layers must be a list of 1–${LIMITS.layers}`);
  const ids = new Set();
  let pixels = 0;
  for (const [i, l] of (layers || []).entries()) {
    const at = `layers[${i}]`;
    if (!l || typeof l !== 'object') { e.push(`${at} must be an object`); continue; }
    const name = `${at} (${l.id})`;
    if (typeof l.id !== 'string' || !/^[a-z0-9][a-z0-9-]{0,31}$/.test(l.id)) e.push(`${at}.id must be 1–32 of a-z 0-9 -`);
    else if (ids.has(l.id)) e.push(`${at}: id "${l.id}" twice`);
    ids.add(l.id);
    if (typeof l.image !== 'string') e.push(`${name}: image is missing`);
    else {
      const s = image(l.image, name);
      if (s) {
        if (s[0] > LIMITS.imageW || s[1] > LIMITS.imageH) e.push(`${name}: ${l.image} is ${s[0]}×${s[1]} (at most ${LIMITS.imageW}×${LIMITS.imageH})`);
        pixels += s[0] * s[1];
      }
    }
    if (!(int(l.z) && between(l.z, -100, 100))) e.push(`${name}: z must be a whole number −100…100`);
    if (l.drift !== undefined && !(pt(l.drift) && l.drift.every((v) => Math.abs(v) <= LIMITS.drift))) e.push(`${name}: drift must be [x, y] px/s, each at most ${LIMITS.drift}`);
    if (l.loop !== undefined && typeof l.loop !== 'boolean') e.push(`${name}: loop must be true / false`);
    if (l.loop && l.drift === undefined) e.push(`${name}: loop needs a drift`);
    if (l.opacity !== undefined && !between(l.opacity, 0, 1)) e.push(`${name}: opacity must be 0–1`);
    if (l.blend !== undefined && !BLENDS.includes(l.blend)) e.push(`${name}: blend must be one of ${BLENDS.join(', ')}`);
    e.push(...checkPhases(l.phases, `${name}.phases`));
  }
  if (pixels > LIMITS.totalPixels) e.push(`the layers add up to ${(pixels / 1e6).toFixed(1)} MP (at most ${LIMITS.totalPixels / 1e6} MP)`);

  if (m.sky !== undefined) {
    const s = m.sky;
    if (!s || typeof s !== 'object' || Array.isArray(s)) e.push('sky must be an object');
    else {
      if (s.phases !== undefined && typeof s.phases !== 'boolean') e.push('sky.phases must be true / false');
      if (s.tint !== undefined && typeof s.tint !== 'boolean') e.push('sky.tint must be true / false');
      if (s.weather !== undefined && !(Array.isArray(s.weather) && s.weather.length && subset(s.weather, WEATHER))) e.push(`sky.weather must be a list of ${WEATHER.join(' / ')}`);
    }
  }
  if (m.fx !== undefined) {
    const f = m.fx;
    if (!f || typeof f !== 'object' || Array.isArray(f)) e.push('fx must be an object');
    else {
      for (const k of ['rain', 'snow']) if (f[k] !== undefined && typeof f[k] !== 'boolean') e.push(`fx.${k} must be true / false`);
      if (f.fireflies !== undefined && !(int(f.fireflies) && between(f.fireflies, 0, LIMITS.fireflies))) e.push(`fx.fireflies must be 0–${LIMITS.fireflies}`);
      if (f.lights !== undefined) {
        if (!Array.isArray(f.lights) || f.lights.length > LIMITS.lights) e.push(`fx.lights must be a list of at most ${LIMITS.lights}`);
        else for (const [i, l] of f.lights.entries()) {
          if (!(l && inCanvas([l.x, l.y]) && between(l.r, 1, 2000))) e.push(`fx.lights[${i}] must be { x, y, r: 1–2000 } inside the canvas`);
          else e.push(...checkPhases(l.phases, `fx.lights[${i}].phases`));
        }
      }
    }
  }

  // her: where she stands, walks and rests
  const p = m.pet && typeof m.pet === 'object' ? m.pet : null;
  if (!p) e.push('pet is missing');
  else {
    if (!between(p.height, 16, 800)) e.push('pet.height must be 16–800');
    if (p.speed !== undefined && !between(p.speed, 1, 400)) e.push('pet.speed must be 1–400');
    if (p.z !== undefined && !(int(p.z) && between(p.z, -100, 100))) e.push('pet.z must be a whole number −100…100');
    const okArea = poly(p.area) && p.area.every(inCanvas);
    if (!okArea) e.push('pet.area must be a polygon of 3 or more points inside the canvas');
    const okBlocked = p.blocked === undefined || (Array.isArray(p.blocked) && p.blocked.every(shape));
    if (!okBlocked) e.push('pet.blocked must be polygons / ellipses');
    const ok = okArea && okBlocked;
    const onFloor = (q, what) => {
      if (!pt(q)) e.push(`${what} must be [x, y]`);
      else if (ok && !walkable(q, p)) e.push(`${what} [${q}] is not inside pet.area (or is blocked)`);
    };
    onFloor(p.spawn, 'pet.spawn');
    if (p.spots !== undefined) {
      if (!Array.isArray(p.spots) || p.spots.length > LIMITS.spots) e.push(`pet.spots must be a list of at most ${LIMITS.spots}`);
      const sids = new Set();
      for (const [i, s] of (Array.isArray(p.spots) ? p.spots : []).entries()) {
        const at = `pet.spots[${i}]`;
        if (!s || typeof s.id !== 'string' || !/^[a-z0-9][a-z0-9-]{0,31}$/.test(s.id)) { e.push(`${at}.id must be 1–32 of a-z 0-9 -`); continue; }
        const name = `${at} (${s.id})`;
        if (sids.has(s.id)) e.push(`${name}: id twice`);
        sids.add(s.id);
        onFloor(s.at, `${name}.at`);
        if (!USE_ANIMS.includes(s.anim)) e.push(`${name}: anim "${s.anim}" is not one of ${USE_ANIMS.join(', ')}`);
        if (s.seconds !== undefined && !(Array.isArray(s.seconds) && s.seconds.length === 2 && s.seconds.every(num) && s.seconds[0] > 0 && s.seconds[0] <= s.seconds[1] && s.seconds[1] <= 600)) e.push(`${name}: seconds must be [min, max] with 0 < min ≤ max ≤ 600`);
        if (s.face !== undefined && !['left', 'right'].includes(s.face)) e.push(`${name}: face must be left or right`);
        e.push(...checkPhases(s.phases, `${name}.phases`));
      }
    }
  }

  if (m.power !== undefined && !(m.power && typeof m.power === 'object' && (m.power.fps === undefined || (int(m.power.fps) && between(m.power.fps, 1, LIMITS.fps))))) e.push(`power.fps must be 1–${LIMITS.fps}`);
  return e;
}

module.exports = { PHASES, WEATHER, BLENDS, LIMITS, validateWallpaper, namedFiles, spriteFiles, imageSize, walkable };
