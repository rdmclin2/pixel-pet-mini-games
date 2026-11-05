#!/usr/bin/env node
'use strict';
// 打包：games/<id>/pack → out/<id>-<version>.zip，并把大小、sha256、更新说明写进 catalog.json（商店目录）。
//   node scripts/build.js [id …]        不写 id 就打包全部
//   node scripts/build.js --check       重新打包，和 catalog.json 逐字节比对（不改文件）
// 打出来的 zip 可复现（排序、固定时间戳）。已经发布的版本内容变了会报错：改了内容就要升版本号
// （pack/manifest.json 的 version，并在 CHANGELOG.md 顶部写这一版的说明）。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const GP = require('../tools/game-pack');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'out');
const CATALOG = path.join(ROOT, 'catalog.json');
const REPO = 'https://github.com/rdmclin2/pixel-pet-mini-games';
const RAW = 'https://raw.githubusercontent.com/rdmclin2/pixel-pet-mini-games/main';
const RELEASE = 'games-v1';
const CHECK = process.argv.includes('--check');
const only = process.argv.slice(2).filter((a) => !a.startsWith('--'));

const ZIP_PY = `
import os, sys, zipfile
src, dest = sys.argv[1], sys.argv[2]
files = sorted(n for n in os.listdir(src) if os.path.isfile(os.path.join(src, n)))
with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in files:
        info = zipfile.ZipInfo(f, date_time=(1980, 1, 1, 0, 0, 0))
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        with open(os.path.join(src, f), 'rb') as fh:
            z.writestr(info, fh.read())
`;
const sha256 = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const readJson = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));

// the folder must be exactly what the app accepts: a manifest that validates, and only the files it names
function checkPack(dir, id) {
  const { manifest: m, errors } = GP.checkFolder(dir);
  if (m && m.id !== id) throw new Error(`${id}: manifest id is "${m.id}"`);
  if (errors.length) throw new Error(`${id}: ${errors.join('; ')}`);
  return m;
}

// the newest CHANGELOG.md section: "## 1.0.0 · 2026-11-05" then its lines
function notes(game, version) {
  const f = path.join(ROOT, 'games', game, 'CHANGELOG.md');
  if (!fs.existsSync(f)) return '';
  const text = fs.readFileSync(f, 'utf8');
  const m = text.match(new RegExp(`^## ${version.replace(/\./g, '\\.')}\\b[^\\n]*\\n([\\s\\S]*?)(?=^## |$(?![\\s\\S]))`, 'm'));
  if (!m) throw new Error(`${game}: CHANGELOG.md has no "## ${version}" section`);
  return m[1].trim();
}

function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const catalog = fs.existsSync(CATALOG) ? readJson(CATALOG) : { schema: 1, release: RELEASE, games: [] };
  const ids = fs.readdirSync(path.join(ROOT, 'games')).filter((d) => fs.existsSync(path.join(ROOT, 'games', d, 'pack', 'manifest.json'))).sort();
  for (const id of ids) {
    if (only.length && !only.includes(id)) continue;
    const dir = path.join(ROOT, 'games', id, 'pack');
    const m = checkPack(dir, id);
    const meta = fs.existsSync(path.join(ROOT, 'games', id, 'store.json')) ? readJson(path.join(ROOT, 'games', id, 'store.json')) : {};
    const file = `${id}-${m.version}.zip`;
    const zip = path.join(OUT, file);
    fs.rmSync(zip, { force: true });
    execFileSync('python3', ['-I', '-c', ZIP_PY, dir, zip]);
    const entry = {
      id, type: 'game', name: m.name, version: m.version, engine: m.engine,
      ...(meta.minAppVersion ? { minAppVersion: meta.minAppVersion } : {}),
      description: m.description || '', credit: m.credit || '', features: meta.features || [],
      repo: `${REPO}/tree/main/games/${id}`,
      picture: fs.existsSync(path.join(ROOT, 'games', id, 'cover.webp')) ? `${RAW}/games/${id}/cover.webp` : null,
      // 商店详情页的预览截图（App Store 式横向一排）：games/<id>/screenshots/ 里 store.json 列出的那些
      screenshots: (meta.screenshots || []).map((x) => {
        if (!/^[a-z0-9][a-z0-9._-]*\.(webp|png)$/.test(String(x.file)) || !fs.existsSync(path.join(ROOT, 'games', id, 'screenshots', x.file))) throw new Error(`${id}: screenshots/${x.file} is missing`);
        return { url: `${RAW}/games/${id}/screenshots/${x.file}`, caption: String(x.caption || '') };
      }),
      changelog: notes(id, m.version),
      file, bytes: fs.statSync(zip).size, sha256: sha256(zip),
    };
    const was = catalog.games.find((g) => g.id === id);
    if (was && was.version === entry.version && was.sha256 !== entry.sha256) {
      if (CHECK) throw new Error(`${id} ${entry.version}: the archive differs from catalog.json (run node scripts/build.js)`);
      if (was.published) throw new Error(`${id} ${entry.version} is published already and its contents changed: raise the version in pack/manifest.json and add a CHANGELOG.md section`);
    }
    if (CHECK && (!was || was.version !== entry.version)) throw new Error(`${id}: catalog.json lists ${was ? was.version : 'nothing'}, the pack is ${entry.version}`);
    if (was && was.version === entry.version && was.published) entry.published = was.published;
    catalog.games = [...catalog.games.filter((g) => g.id !== id), entry].sort((a, b) => a.id.localeCompare(b.id));
    console.log(`  ${id} ${entry.version}  ${file}  ${entry.bytes} bytes  ${entry.sha256.slice(0, 12)}${entry.published ? '  (published)' : ''}`);
  }
  if (CHECK) { console.log('catalog.json matches the packs'); return; }
  catalog.schema = 1;
  catalog.release = RELEASE;
  fs.writeFileSync(CATALOG, `${JSON.stringify(catalog, null, 2)}\n`);
  console.log(`catalog.json written; archives in ${path.relative(ROOT, OUT)}/`);
}

main();
