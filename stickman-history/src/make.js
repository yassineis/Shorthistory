#!/usr/bin/env node
'use strict';
// Script -> voice per scene -> render per scene -> join -> music -> final.mp4
// Every scene is its own short clip (usually 8-15 s) and clips are cached, so a re-run only redoes
// what changed. Nothing is uploaded or published; the result is a local mp4.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');
const { generateVoice, probeDuration, runFFmpeg, loadEnv } = require('./voice');

const ROOT = path.join(__dirname, '..');
const BOOL = new Set(['sample', 'dry-voice', 'no-music', 'no-presenter', 'force', 'help']);

function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (!a.startsWith('--')) { o._.push(a); continue; }
    const k = a.slice(2);
    o[k] = BOOL.has(k) ? true : argv[++i];
  }
  return o;
}

const hash = (s) => crypto.createHash('sha1').update(s).digest('hex').slice(0, 8);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function findPython() {
  for (const c of [process.env.PYTHON, 'python3', 'python', 'py'].filter(Boolean)) {
    const r = spawnSync(c, ['-c', 'import PIL, numpy'], { stdio: 'ignore' });
    if (r.status === 0) return c;
  }
  throw new Error('Python with Pillow and numpy not found. Install Python 3, then run: pip install pillow numpy');
}

function help() {
  console.log(`Usage: node src/make.js <script.json> [options]

  --out <dir>        output folder (default: out/<script name>)
  --sample           make only the first scene -> sample.mp4 (check style and voice first)
  --dry-voice        use a placeholder tone instead of Gemini (no key, no internet)
  --aspect 16:9|9:16 default 16:9 (9:16 for Shorts / Reels)
  --height 720       frame height in pixels (default 720)
  --fps 24           frames per second
  --pause 4000       pause in ms between voice requests (raise it if you hit free-tier limits)
  --no-music         skip the background music
  --no-presenter     hide the corner presenter
  --font <file.ttf>  caption font (default: a bold system font)
  --force            ignore cached voice and clips
  --env <file>       file with GEMINI_API_KEY (default: .env)`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args._[0]) return help();
  loadEnv(args.env || path.join(ROOT, '.env'));

  const scriptPath = path.resolve(args._[0]);
  const script = JSON.parse(fs.readFileSync(scriptPath, 'utf8'));
  if (!Array.isArray(script.scenes) || !script.scenes.length) throw new Error('The script needs a "scenes" array.');
  const name = path.basename(scriptPath).replace(/\.json$/i, '');
  const out = path.resolve(args.out || path.join('out', name));
  for (const d of ['audio', 'scenes', 'clips']) fs.mkdirSync(path.join(out, d), { recursive: true });

  const aspect = args.aspect || script.aspect || '16:9';
  const height = parseInt(args.height || script.height || '720', 10);
  const [aw, ah] = aspect.split(':').map(Number);
  const width = Math.round((height * aw) / ah / 2) * 2;
  const fps = parseInt(args.fps || '24', 10);
  const pause = parseInt(args.pause || '4000', 10);
  const python = findPython();
  const voice = script.voice || {};
  const scenes = args.sample ? script.scenes.slice(0, 1) : script.scenes;

  console.log(`"${script.title || name}": ${scenes.length} scene(s), ${width}x${height} @ ${fps}fps${args['dry-voice'] ? ' [dry voice]' : ''}`);
  const clips = [];
  let total = 0;

  for (let i = 0; i < scenes.length; i += 1) {
    const sc = scenes[i];
    const num = String(i + 1).padStart(2, '0');
    if (!sc.narration) throw new Error(`Scene ${i + 1} has no "narration".`);

    const audioKey = hash(JSON.stringify([sc.narration, voice, !!args['dry-voice']]));
    const audio = path.join(out, 'audio', `scene_${num}_${audioKey}.mp3`);
    if (!fs.existsSync(audio) || args.force) {
      process.stdout.write(`  scene ${num}: voice... `);
      await generateVoice(sc.narration, audio, { dry: !!args['dry-voice'], ...voice });
      console.log('ok');
      if (!args['dry-voice'] && i < scenes.length - 1) await sleep(pause);
    }
    const adur = await probeDuration(audio);

    const spec = {
      index: i, narration: sc.narration, kicker: sc.kicker || '', stamp: sc.stamp || '', stamp_at: sc.stamp_at,
      stage: sc.stage || {}, presenter: !args['no-presenter'] && script.presenter !== false,
      presenter_pose: sc.presenter_pose, audio, audio_duration: adur,
      width, height, fps, font: args.font || script.font || undefined,
    };
    Object.keys(spec).forEach((k) => spec[k] === undefined && delete spec[k]);
    const clip = path.join(out, 'clips', `scene_${num}_${hash(JSON.stringify(spec))}.mp4`);
    spec.out = clip;
    const specPath = path.join(out, 'scenes', `scene_${num}.json`);
    fs.writeFileSync(specPath, JSON.stringify(spec, null, 2));

    if (!fs.existsSync(clip) || !fs.existsSync(clip.replace(/\.mp4$/, '.wav')) || args.force) {
      process.stdout.write(`  scene ${num}: rendering (${adur.toFixed(1)}s of speech)... `);
      const t0 = Date.now();
      const r = spawnSync(python, [path.join(ROOT, 'render', 'render_scene.py'), specPath], { stdio: 'inherit' });
      if (r.status !== 0) throw new Error(`Rendering scene ${num} failed.`);
      console.log(`done in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    clips.push(clip);
    total += await probeDuration(clip);
  }

  const wavs = clips.map((c) => c.replace(/\.mp4$/, '.wav'));
  if (!args.sample) { // drop clips from older versions of the script so the folder does not fill up
    const keep = new Set([...clips, ...wavs]);
    for (const f of fs.readdirSync(path.join(out, 'clips'))) {
      const full = path.join(out, 'clips', f);
      if (!keep.has(full)) fs.unlinkSync(full);
    }
  }

  // Video clips are joined without audio; narration is joined as lossless WAV and encoded once at the end.
  const concat = async (files, dest) => {
    if (files.length === 1) return fs.copyFileSync(files[0], dest);
    const list = dest + '.txt';
    fs.writeFileSync(list, files.map((c) => `file '${c.replace(/\\/g, '/').replace(/'/g, "'\\''")}'`).join('\n'));
    return runFFmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', dest]);
  };
  const joined = path.join(out, args.sample ? 'sample_video.mp4' : 'joined_video.mp4');
  const narration = path.join(out, 'narration.wav');
  await concat(clips, joined);
  await concat(wavs, narration);

  const final = path.join(out, args.sample ? 'sample.mp4' : 'final.mp4');
  if (args['no-music']) {
    await runFFmpeg(['-y', '-i', joined, '-i', narration, '-map', '0:v', '-map', '1:a',
      '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', final]);
  } else {
    const music = path.join(out, 'music.wav');
    const r = spawnSync(python, [path.join(ROOT, 'render', 'music.py'), String(total + 1), music], { stdio: 'inherit' });
    if (r.status !== 0) throw new Error('Music generation failed.');
    await runFFmpeg(['-y', '-i', joined, '-i', narration, '-i', music, '-filter_complex',
      '[1:a]volume=1.0[n];[2:a]volume=0.14[m];[n][m]amix=inputs=2:duration=first:dropout_transition=0[mix];[mix]volume=2[a]',
      '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', final]);
  }

  console.log(`\nDone: ${final}  (${total.toFixed(1)}s)`);
  if (!args.sample && total > 120) console.log('Note: longer than 2 minutes. Shorten the narration or drop a scene.');
  if (!args.sample && aspect === '9:16' && total > 60) console.log('Note: YouTube Shorts are 60 s or less; this one is longer.');
}

main().catch((e) => { console.error('\nError: ' + e.message); process.exit(1); });
