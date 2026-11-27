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
const BOOL = new Set(['sample', 'dry-voice', 'no-music', 'no-presenter', 'no-sfx', 'force', 'help']);

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
  --voice kokoro|gemini  kokoro (default) = free offline voice, no key, no limits; gemini = Gemini TTS (needs key)
  --dry-voice        use a placeholder tone instead of a real voice (fastest test)
  --aspect 16:9|9:16 default 16:9 (9:16 for Shorts / Reels)
  --height 720       frame height in pixels (default 720)
  --fps 24           frames per second
  --pause 4000       pause in ms between Gemini voice requests (only with --voice gemini)
  --no-music         skip the background music
  --no-sfx           skip the sound effects (storybook style)
  --no-presenter     hide the corner presenter
  --font <file.ttf>  caption font (default: a bold system font)
  --style sb|a5|b5   sb = storybook cartoon, vertical 9:16 (default for shorts), a5 = old colourful stick figures, b5 = paper stickman explainer
  --next "Title"     (not used any more: the storybook ending is now a looping subscribe overlay on the last scene)
  --min 70 --max 90 refuse the video if narration + padding (+ the subscribe line) falls outside these seconds (exit code 3)
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

  const style = args.style || script.style || 'b5';
  const sb = style === 'sb';
  if (sb && args.aspect && args.aspect !== '9:16') console.log('  (the storybook style is vertical, so 9:16 is used)');
  const aspect = sb ? '9:16' : (args.aspect || script.aspect || '16:9');
  const height = parseInt(args.height || script.height || (sb ? '1280' : '720'), 10);
  const [aw, ah] = aspect.split(':').map(Number);
  const width = Math.round((height * aw) / ah / 2) * 2;
  const fps = parseInt(args.fps || '24', 10);
  const pause = parseInt(args.pause || '4000', 10);
  const python = findPython();
  const voice = script.voice || {};
  const scenes = args.sample ? script.scenes.slice(0, 1) : script.scenes;

  console.log(`"${script.title || name}": ${scenes.length} scene(s), ${width}x${height} @ ${fps}fps${args['dry-voice'] ? ' [dry voice]' : ''}`);
  const enhanced = script.enhanced === true; // option A: option 9 plus prop actions, faces on key words, mastered audio
  const trueMode = script.mode === 'true' || enhanced; // option 9: short one-sentence shots, tighter cuts
  const lead = trueMode ? 0.15 : 0.45, tail = trueMode ? 0.25 : 0.55;
  const clips = [];
  let total = 0;

  // pass 1: voice for every scene (cached), so the length can be checked before the slow rendering
  const items = [];
  for (let i = 0; i < scenes.length; i += 1) {
    const sc = scenes[i];
    const num = String(i + 1).padStart(2, '0');
    if (!sc.narration) throw new Error(`Scene ${i + 1} has no "narration".`);
    const provider = args.voice || process.env.VOICE_PROVIDER || 'kokoro';
    // enhanced: the hook is a touch slower and the last line slower still (it lands better); normal modes keep one speed
    const baseSpeed = Number(process.env.KOKORO_SPEED || 1.21);
    const sMul = enhanced ? (i === scenes.length - 1 ? 0.92 : i === 0 ? 0.97 : 1) : 1;
    const audioKey = hash(JSON.stringify([sc.narration, voice, provider, !!args['dry-voice'], process.env.KOKORO_VOICE || '', process.env.KOKORO_SPEED || '', ...(enhanced ? [sMul] : [])]));
    const audio = path.join(out, 'audio', `scene_${num}_${audioKey}.mp3`);
    if (!fs.existsSync(audio) || args.force) {
      process.stdout.write(`  scene ${num}: voice... `);
      await generateVoice(sc.narration, audio, { dry: !!args['dry-voice'], provider, ...voice, ...(enhanced && sMul !== 1 ? { kokoroSpeed: baseSpeed * sMul } : {}) });
      console.log('ok');
      if (!args['dry-voice'] && provider === 'gemini' && i < scenes.length - 1) await sleep(pause);
    }
    items.push({ sc, num, audio, adur: await probeDuration(audio), narr: sc.narration });
  }

  // Looping ending (storybook style): no separate end card. The narrator's last story line flows straight into a short
  // "Subscribe, and ring the bell..." line, and the Subscribe button pops up over the SAME final scene, so viewers do not
  // swipe away at a card and the video can loop back into its hook.
  if (sb && !args.sample) {
    const line = 'Subscribe, and ring the bell, to see our next episode.';
    const provider = args.voice || process.env.VOICE_PROVIDER || 'kokoro';
    const vkey = hash(JSON.stringify([line, voice, provider, !!args['dry-voice'], process.env.KOKORO_VOICE || '', process.env.KOKORO_SPEED || '']));
    const ctaVoice = path.join(out, 'audio', `cta_${vkey}.mp3`);
    if (!fs.existsSync(ctaVoice) || args.force) await generateVoice(line, ctaVoice, { dry: !!args['dry-voice'], provider, ...voice });
    const last = items[items.length - 1];
    const gap = 0.3;
    const joinedAudio = path.join(out, 'audio', `scene_${last.num}_cta_${hash(last.audio + vkey)}.mp3`);
    if (!fs.existsSync(joinedAudio) || args.force) {
      await runFFmpeg(['-y', '-i', last.audio, '-i', ctaVoice, '-filter_complex',
        `[0:a]aformat=sample_rates=24000:channel_layouts=mono,apad=pad_dur=${gap}[a];[1:a]aformat=sample_rates=24000:channel_layouts=mono[b];[a][b]concat=n=2:v=0:a=1[o]`,
        '-map', '[o]', '-c:a', 'libmp3lame', '-b:a', '128k', joinedAudio]);
    }
    last.cta_start = lead + last.adur + gap; // seconds into the final scene clip where the subscribe line begins
    last.audio = joinedAudio;
    last.adur = await probeDuration(joinedAudio);
    last.narr = `${last.narr} ${line}`;
  }
  const estimate = items.reduce((a, it) => a + it.adur + lead + tail, 0);
  if (!args.sample && (args.min || args.max)) {
    const lo = parseFloat(args.min || '0'), hi = parseFloat(args.max || '1e9');
    if (estimate < lo || estimate > hi) {
      console.error(`DURATION ${estimate.toFixed(1)} (allowed ${lo}-${hi})`);
      process.exit(3);
    }
  }

  // enhanced: when (seconds into the clip) the key word of the sentence is spoken; faces change and props act from there
  const keyAt = (sc, adur) => {
    const words = sc.narration.trim().split(/\s+/);
    let idx = Math.floor(words.length * 0.55);
    if (sc.key) {
      const k = String(sc.key).toLowerCase().replace(/[^a-z0-9]/g, '');
      const f = words.findIndex((w) => w.toLowerCase().replace(/[^a-z0-9]/g, '') === k);
      if (f >= 0) idx = f;
    }
    const chars = words.slice(0, idx).join(' ').length / Math.max(1, sc.narration.trim().length);
    return Math.round((lead + Math.max(0, adur * chars - 0.05)) * 100) / 100;
  };

  // pass 2: render each scene (cached by spec hash)
  for (let i = 0; i < items.length; i += 1) {
    const { sc, num, audio, adur, narr, cta_start } = items[i];
    const spec = {
      index: i, narration: narr, cta_start, kicker: sc.kicker || '', stamp: sc.stamp || '', stamp_at: sc.stamp_at,
      stage: sc.stage || {}, style, setting: sc.setting || script.setting,
      presenter: !args['no-presenter'] && (style === 'a5' ? script.presenter === true : script.presenter !== false),
      presenter_pose: sc.presenter_pose, audio, audio_duration: adur,
      width, height, fps, font: args.font || script.font || undefined,
      ...(trueMode ? { lead, tail, enter: i === 0 || (scenes[i - 1].setting || script.setting) !== (sc.setting || script.setting) } : {}),
      ...(enhanced ? { enhanced: true, action: sc.action, key_at: keyAt(sc, adur) } : {}),
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

  // Sound effects: a soft whoosh at every scene change, plus the effect the story asks for in a scene ("sfx": door, steps...).
  let sfxWav = null;
  if (sb && !args['no-sfx']) {
    const events = [];
    let at = 0;
    for (let i = 0; i < clips.length; i += 1) {
      const newPlace = !trueMode || i === 0 || (items[i] && items[i - 1] && items[i].sc.setting !== items[i - 1].sc.setting);
      if (i > 0 && newPlace) events.push({ t: at - 0.05, name: 'whoosh', gain: 0.55 }); // true-story mode: only when the place changes
      const tag = items[i] && items[i].sc.sfx;
      if (tag) events.push({ t: at + 0.5, name: tag, gain: 1.0 });
      if (enhanced && items[i]) {
        const sc = items[i].sc, ka = keyAt(sc, items[i].adur);
        const enters = i === 0 || (items[i - 1].sc.setting || script.setting) !== (sc.setting || script.setting);
        if (enters) { events.push({ t: at + 0.05, name: 'step2', gain: 0.5 }); events.push({ t: at + 0.4, name: 'step2', gain: 0.5 }); } // footsteps while they walk in
        const AX = { throw: [['thud', 1.25]], swing: [['thud', 0.42], ['crash', 1.32]], fall: [['crash', 0.75]], impact: [['crash', 0]], door: [['door', 0]], sail: [['splash', 0.3]], glide: [['whoosh', 0]], train: [['whoosh', 0.2], ['bell', 0]] };
        for (const [nm, off] of AX[sc.action] || []) events.push({ t: at + ka + off, name: nm, gain: 0.9 });
        const acts = sc.stage && sc.stage.actors ? sc.stage.actors : [];
        if (!tag && !sc.action && acts.some((a) => a.mood === 'shock' || a.mood === 'scared')) events.push({ t: at + ka, name: 'gasp', gain: 0.7 });
      }
      at += await probeDuration(clips[i]);
    }
    const ev = path.join(out, 'sfx.json');
    sfxWav = path.join(out, 'sfx.wav');
    fs.writeFileSync(ev, JSON.stringify({ total: at, events }));
    const r0 = spawnSync(python, [path.join(ROOT, 'render', 'sb_sfx.py'), ev, sfxWav], { stdio: 'inherit' });
    if (r0.status !== 0) { console.log('  (sound effects skipped)'); sfxWav = null; }
  }
  const final = path.join(out, args.sample ? 'sample.mp4' : 'final.mp4');
  if (args['no-music']) {
    await runFFmpeg(['-y', '-i', joined, '-i', narration, '-map', '0:v', '-map', '1:a',
      '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', final]);
  } else {
    const music = path.join(out, 'music.wav');
    const mstyle = (parseInt(hash(script.title || name), 16) % 5) + 1; // one of 5 code-made music styles, chosen per story
    const ctaAt = items[items.length - 1].cta_start;
    const hush = enhanced && ctaAt ? ['--hush', String((total - items[items.length - 1].adur - lead - tail + ctaAt).toFixed(2))] : [];
    const r = sb
      ? spawnSync(python, [path.join(ROOT, 'render', 'sb_music.py'), String(mstyle), music, String(total + 1), '--bg', ...hush], { stdio: 'inherit' })
      : spawnSync(python, [path.join(ROOT, 'render', 'music.py'), String(total + 1), music], { stdio: 'inherit' });
    if (r.status !== 0) throw new Error('Music generation failed.');
    const ins = ['-i', joined, '-i', narration, '-i', music];
    let fc = '[1:a]volume=1.0[n];[2:a]volume=0.14[m];';
    if (enhanced && sfxWav) {
      // mastered: clean and compress the voice, duck the music under it, level to -14 LUFS (YouTube's loudness)
      fc = '[1:a]highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=80:makeup=4,equalizer=f=3000:t=q:w=1:g=2,asplit=2[n][nk];'
        + '[2:a]volume=0.22[m0];[m0][nk]sidechaincompress=threshold=0.02:ratio=9:attack=15:release=350[m];'
        + '[3:a]volume=0.35[x];[n][m][x]amix=inputs=3:duration=first:dropout_transition=0:normalize=0[mix];'
        + '[mix]loudnorm=I=-14:TP=-1.5:LRA=11[a]';
      ins.push('-i', sfxWav);
    } else if (sfxWav) {
      ins.push('-i', sfxWav);
      fc += '[3:a]volume=0.35[x];[n][m][x]amix=inputs=3:duration=first:dropout_transition=0:normalize=0[mix];[mix]volume=1.1[a]';
    } else {
      fc += '[n][m]amix=inputs=2:duration=first:dropout_transition=0[mix];[mix]volume=2[a]';
    }
    await runFFmpeg(['-y', ...ins, '-filter_complex', fc,
      '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', final]);
  }

  console.log(`\nDone: ${final}  (${total.toFixed(1)}s)`);
  if (!args.sample && !args.max && total > 120) console.log('Note: longer than 2 minutes. Shorten the narration or drop a scene.');
  if (!args.sample && aspect === '9:16' && total > 180) console.log('Note: YouTube Shorts may be capped by YouTube (check current limit); this one is longer.');
}

main().catch((e) => { console.error('\nError: ' + e.message); process.exit(1); });
