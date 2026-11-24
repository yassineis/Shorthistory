#!/usr/bin/env node
'use strict';
// Adds the free Kokoro narrator (am_fenrir 0.88, the Oli voice from YOUTUBE-AGENT) to the 5 prototype sketches.
//   node src/sketch-voice.js --dir out/sketches [--only 3]
// Needs in --dir:  sketchN_silent.mp4 and musicN.wav  (made by render/sb_sketch.py and render/sb_music.py)
// Writes:          sketchN_final.mp4  (picture + music + narration)
const fs = require('fs');
const path = require('path');
const { generateVoice, probeDuration, runFFmpeg } = require('./voice');

const ROOT = path.join(__dirname, '..');
const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };

async function main() {
  const dir = path.resolve(arg('dir', path.join(ROOT, 'out', 'sketches')));
  const only = arg('only') ? Number(arg('only')) : null;
  const lines = JSON.parse(fs.readFileSync(path.join(ROOT, 'sketches', 'lines.json'), 'utf8'));
  for (const sk of lines.sketches) {
    if (only && sk.id !== only) continue;
    const video = path.join(dir, `sketch${sk.id}_silent.mp4`);
    const music = path.join(dir, `music${sk.id}.wav`);
    if (!fs.existsSync(video) || !fs.existsSync(music)) { console.log(`sketch ${sk.id}: files missing in ${dir}, skipped`); continue; }
    console.log(`sketch ${sk.id}: voicing ${sk.lines.length} lines (${sk.music})`);
    const vdir = path.join(dir, `voice${sk.id}`);
    const inputs = ['-i', video, '-i', music];
    const filters = [];
    const labels = [];
    for (let i = 0; i < sk.lines.length; i += 1) {
      const wav = path.join(vdir, `line${i + 1}.wav`);
      await generateVoice(sk.lines[i].text, wav, { provider: 'kokoro' });
      const dur = await probeDuration(wav);
      const next = sk.lines[i + 1] ? sk.lines[i + 1].start : 20;
      if (sk.lines[i].start + dur > next) console.log(`  note: line ${i + 1} runs ${dur.toFixed(1)}s, longer than its slot`);
      inputs.push('-i', wav);
      const ms = Math.round(sk.lines[i].start * 1000);
      filters.push(`[${i + 2}:a]adelay=${ms}|${ms},volume=1.6[v${i}]`);
      labels.push(`[v${i}]`);
    }
    filters.push(`[1:a]volume=0.8[m]`);
    filters.push(`[m]${labels.join('')}amix=inputs=${labels.length + 1}:duration=first:normalize=0,alimiter=limit=0.95[a]`);
    const out = path.join(dir, `sketch${sk.id}_final.mp4`);
    await runFFmpeg(['-y', ...inputs, '-filter_complex', filters.join(';'), '-map', '0:v', '-map', '[a]',
      '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', out]);
    console.log(`  wrote ${out}`);
  }
}
main().catch((e) => { console.error('Error: ' + e.message); process.exit(1); });
