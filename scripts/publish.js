#!/usr/bin/env node
'use strict';
// 发布：把 out/ 里打好的包传到 LobeHub 的 CDN（Develop Center `dc ops-assets upload`，
// dc/ops-assets/archives/pixel-pet/<release>/），再从应用下载用的地址下载回来比对大小和 sha256，
// 都对上了才在 catalog.json 里把这一版标成 published。之后提交并推送 catalog.json：
// 应用读的是 main 分支上的这份文件（raw.githubusercontent.com），推上去就算上架 / 升级。
//   node scripts/build.js && node scripts/publish.js [id …] [--dry-run]
// 需要 dc（或 DC_CLI=/path/to/dc/dist/index.js）已登录：dc auth login --token <DC_CLI_TOKEN> --base-url <DC 地址>。
// 同名文件已在 CDN 上且大小相同会跳过（--skip-existing）；大小不同会报错——已发布的包不会被悄悄替换。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');

const ROOT = path.join(__dirname, '..');
const CATALOG = path.join(ROOT, 'catalog.json');
const CDN = 'https://chat-cloud.lobeobjects.space';
const PREFIX_ROOT = 'dc/ops-assets/archives/pixel-pet';
const DRY = process.argv.includes('--dry-run');
const only = process.argv.slice(2).filter((a) => !a.startsWith('--'));

function dc(args) {
  const cli = process.env.DC_CLI;
  const [cmd, pre] = cli ? [process.execPath, [cli]] : ['dc', []];
  return execFileSync(cmd, [...pre, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'], maxBuffer: 64 * 1024 * 1024 });
}

async function main() {
  const catalog = JSON.parse(fs.readFileSync(CATALOG, 'utf8'));
  const prefix = `${PREFIX_ROOT}/${catalog.release}`;
  const todo = catalog.games.filter((g) => !only.length || only.includes(g.id));
  const files = todo.map((g) => path.join(ROOT, 'out', g.file));
  const missing = files.filter((f) => !fs.existsSync(f));
  if (missing.length) throw new Error(`not built: ${missing.map((f) => path.basename(f)).join(', ')} (node scripts/build.js)`);
  console.log(`${files.length} archive(s) → ${prefix}/`);
  if (DRY) { for (const g of todo) console.log(`  ${g.file}  ${g.bytes}  ${CDN}/${prefix}/${g.file}`); return; }
  const results = JSON.parse(dc(['ops-assets', 'upload', ...files, '--prefix', prefix, '--skip-existing']));
  const problems = [];
  for (const g of todo) {
    const url = `${CDN}/${prefix}/${g.file}`;
    const r = results.find((x) => path.basename(x.file) === g.file);
    if (!r) { problems.push(`${g.file}: not uploaded`); continue; }
    if (r.publicUrl !== url) problems.push(`${g.file}: the CDN address is ${r.publicUrl}, the app downloads ${url}`);
    const res = await fetch(url);
    const buf = res.ok ? Buffer.from(await res.arrayBuffer()) : null;
    const sha = buf && crypto.createHash('sha256').update(buf).digest('hex');
    const ok = buf && buf.length === g.bytes && sha === g.sha256;
    if (!ok) problems.push(`${g.file}: ${res.ok ? `downloaded ${buf.length} bytes, sha256 ${sha.slice(0, 12)}` : `HTTP ${res.status}`} (catalog: ${g.bytes}, ${g.sha256.slice(0, 12)})`);
    else g.published = new Date().toISOString().slice(0, 10);
    console.log(`  ${ok ? '✓' : '✗'} ${g.file}  ${r.skipped ? 'already there' : 'uploaded'}  ${url}`);
  }
  fs.writeFileSync(CATALOG, `${JSON.stringify(catalog, null, 2)}\n`);
  if (problems.length) { console.error(`\n${problems.length} problem(s):\n  ${problems.join('\n  ')}`); process.exit(1); }
  console.log('\nAll on the CDN and matching catalog.json. Commit and push catalog.json to put them in the store.');
}

main().catch((e) => { console.error(e.message || e); process.exit(1); });
