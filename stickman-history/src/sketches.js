#!/usr/bin/env node
'use strict';
// Makes the 5 storybook prototype sketches (free: drawn by code, music made by code, Kokoro narrator).
//   node src/sketches.js [--only N] [--fast] [--no-voice] [--out out/sketches]
// Result: out/sketches/sketchN_final.mp4 (picture + music + narration), or sketchN_music.mp4 with --no-voice.
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { loadEnv, runFFmpeg } = require('./voice');

const ROOT = path.join(__dirname, '..');
const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const flag = (k) => process.argv.includes(`--${k}`);

function findPython() {
  for (const c of [process.env.PYTHON, 'python3', 'python', 'py'].filter(Boolean)) {
    if (spawnSync(c, ['-c', 'import PIL, numpy'], { stdio: 'ignore' }).status === 0) return c;
  }
  throw new Error('Python with Pillow and numpy not found. Install Python 3, then run: pip install pillow numpy');
}

async function main() {
  loadEnv(path.join(ROOT, '.env'));
  const out = path.resolve(arg('out', path.join(ROOT, 'out', 'sketches')));
  fs.mkdirSync(out, { recursive: true });
  const only = arg('only') ? Number(arg('only')) : null;
  const python = findPython();
  const ids = [1, 2, 3, 4, 5].filter((n) => !only || n === only);

  for (const n of ids) {
    console.log(`\n=== Sketch ${n} of 5 ===`);
    let r = spawnSync(python, [path.join(ROOT, 'render', 'sb_music.py'), String(n), path.join(out, `music${n}.wav`)], { stdio: 'inherit' });
    if (r.status !== 0) throw new Error('music failed');
    const a = [path.join(ROOT, 'render', 'sb_sketch.py'), 'sketch', String(n), out];
    if (flag('fast')) a.push('--fast');
    r = spawnSync(python, a, { stdio: 'inherit' });
    if (r.status !== 0) throw new Error('drawing the sketch failed (see above)');
  }

  if (flag('no-voice')) {
    for (const n of ids) {
      await runFFmpeg(['-y', '-i', path.join(out, `sketch${n}_silent.mp4`), '-i', path.join(out, `music${n}.wav`), '-map', '0:v', '-map', '1:a',
        '-c:v', 'copy', '-c:a', 'aac', '-shortest', path.join(out, `sketch${n}_music.mp4`)]);
    }
    console.log(`\nDone. Videos with music are in ${out}`);
    return;
  }
  const v = [path.join(__dirname, 'sketch-voice.js'), '--dir', out];
  if (only) v.push('--only', String(only));
  const r = spawnSync(process.execPath, v, { stdio: 'inherit' });
  if (r.status !== 0) throw new Error('adding the voice failed (see above)');
  console.log(`\nDone. Finished sketches are in ${out}`);
}
main().catch((e) => { console.error('\nError: ' + e.message); process.exit(1); });
