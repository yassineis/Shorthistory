'use strict';
// Voice generation. Default engine: Kokoro (kokoro-js, free, offline, runs on the CPU, no API key, no limits),
// ported from YOUTUBE-AGENT (kids-channel/animation/lib/voices.js). Optional engine: Gemini TTS
// (--voice gemini), ported from YOUTUBE-AGENT (utils/ai-video-generator.js -> generateGeminiTTS).
// Same request shape and the same PCM -> FFmpeg step. The only change: it calls the Gemini REST
// endpoint with fetch (Node 18+) so this project needs no npm packages.
//
// Gemini returns raw PCM (24 kHz, mono, 16-bit); FFmpeg encodes it to the requested container.

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const FFMPEG = process.env.FFMPEG_PATH || 'ffmpeg';
const FFPROBE = process.env.FFPROBE_PATH || 'ffprobe';

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '', err = '';
    p.stdout.on('data', (d) => (out += d));
    p.stderr.on('data', (d) => (err += d));
    p.on('error', (e) => reject(new Error(
      e.code === 'ENOENT' ? `${cmd} not found. Install FFmpeg (https://ffmpeg.org) and make sure it is on your PATH.` : e.message)));
    p.on('close', (code) => (code === 0 ? resolve(out) : reject(new Error(`${cmd} failed (${code}): ${err.slice(-400)}`))));
  });
}

const runFFmpeg = (args) => run(FFMPEG, ['-hide_banner', '-loglevel', 'error', ...args]);

async function probeDuration(file) {
  const out = await run(FFPROBE, ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file]);
  const d = parseFloat(out.trim());
  if (!Number.isFinite(d)) throw new Error(`Could not read the duration of ${file}`);
  return d;
}

// Minimal .env reader so nothing needs installing. Existing environment variables win.
function loadEnv(file) {
  if (!file || !fs.existsSync(file)) return false;
  for (const raw of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = raw.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/);
    if (!m || raw.trim().startsWith('#')) continue;
    const v = m[2].trim().replace(/^["']|["']$/g, '').trim();
    if (v && process.env[m[1]] === undefined) process.env[m[1]] = v;
  }
  return true;
}

function geminiKey() {
  for (const n of ['GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_KEY']) {
    const v = (process.env[n] || '').trim().replace(/^[=\s]+/, '').replace(/^["']|["']$/g, '').trim();
    if (v) return v;
  }
  return '';
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function geminiTTS(text, outputPath, { apiKey, model, voice, style }) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;
  const spoken = style ? `${style} ${text}` : text;
  const body = JSON.stringify({
    contents: [{ parts: [{ text: spoken }] }],
    generationConfig: {
      responseModalities: ['AUDIO'],
      speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voice } } },
    },
  });

  let lastError;
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
        body,
      });
      if (res.status === 429 || res.status >= 500) {
        lastError = new Error(`Gemini TTS busy (HTTP ${res.status})`);
        await sleep(5000 * 2 ** attempt); // free tier is rate limited: back off and retry
        continue;
      }
      if (!res.ok) {
        const msg = (await res.text()).replace(apiKey, '***').slice(0, 300);
        throw new Error(`Gemini TTS failed (HTTP ${res.status}): ${msg}`);
      }
      const json = await res.json();
      const audioData = json.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
      if (!audioData) throw new Error('Gemini TTS returned no audio data');

      const pcmPath = outputPath + '.pcm';
      fs.writeFileSync(pcmPath, Buffer.from(audioData, 'base64'));
      await runFFmpeg(['-y', '-f', 's16le', '-ar', '24000', '-ac', '1', '-i', pcmPath, outputPath]);
      fs.unlinkSync(pcmPath);
      return outputPath;
    } catch (e) {
      if (/Gemini TTS (failed|returned)/.test(e.message)) throw e;
      lastError = e;
      await sleep(3000 * (attempt + 1));
    }
  }
  throw lastError || new Error('Gemini TTS failed');
}

// Placeholder "speech" (a wobbling tone) so the whole pipeline can be tested with no key and no internet.
async function dryVoice(text, outputPath) {
  const words = text.split(/\s+/).filter(Boolean).length;
  const dur = Math.max(1.5, words / 2.6).toFixed(2);
  const expr = '0.09*sin(2*PI*170*t)*(0.55+0.45*sin(2*PI*3.3*t))*(0.5+0.5*sin(2*PI*0.7*t))';
  await runFFmpeg(['-y', '-f', 'lavfi', '-i', `aevalsrc=${expr}:s=24000:d=${dur}`, '-ac', '1', outputPath]);
  return outputPath;
}

// ---------------------------------------------------------------- Kokoro (free, offline)
// Same clean-up chain as YOUTUBE-AGENT: remove rumble, add clarity, even loudness.
const POLISH = 'highpass=f=75,equalizer=f=200:t=q:w=1.2:g=-1.5,equalizer=f=3200:t=q:w=1.1:g=2.5,equalizer=f=7500:t=q:w=1.5:g=1.5,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000';
const kokoroCache = {};

// Reuse a model already downloaded by another project (e.g. YOUTUBE-AGENT) so it is not downloaded twice.
// Set KOKORO_CACHE to a cache folder, or leave it empty and the usual Desktop folders are searched.
async function useExistingCache() {
  const os = require('os');
  const sub = path.join('node_modules', '@huggingface', 'transformers', '.cache');
  const home = os.homedir();
  const names = ['YOUTUBE-AGENT-backup', 'YOUTUBE-AGENT', 'youtube-agent'];
  const cands = [process.env.KOKORO_CACHE, process.env.YOUTUBE_AGENT_DIR && path.join(process.env.YOUTUBE_AGENT_DIR, sub)]
    .concat(names.flatMap((n) => [path.join(home, 'Desktop', n, sub), path.join(home, 'OneDrive', 'Desktop', n, sub), path.join(home, n, sub)]))
    .filter(Boolean);
  const found = cands.find((c) => fs.existsSync(path.join(c, 'onnx-community')));
  if (!found) return;
  try {
    const { env } = await import('@huggingface/transformers');
    env.cacheDir = found;
    console.log(`  (using the voice model already downloaded in ${found})`);
  } catch (e) { /* package layout differs: fall back to a normal download */ }
}

async function loadKokoro(dtype) {
  if (!kokoroCache[dtype]) {
    kokoroCache[dtype] = (async () => {
      let mod;
      try { mod = await import('kokoro-js'); } catch (e) {
        throw new Error('The free voice engine is not installed. Run "npm install" in this folder (run.bat does it for you), or use --voice gemini / --dry-voice.');
      }
      await useExistingCache();
      console.log(`  (loading the Kokoro voice model, ${dtype}; the first time it downloads about ${dtype === 'q8' ? '90' : '330'} MB)`);
      return mod.KokoroTTS.from_pretrained('onnx-community/Kokoro-82M-v1.0-ONNX', { dtype, device: 'cpu' });
    })();
  }
  return kokoroCache[dtype];
}

function writeWavFile(file, samples, rate) {
  const buf = Buffer.alloc(44 + samples.length * 2);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + samples.length * 2, 4); buf.write('WAVEfmt ', 8);
  buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22); buf.writeUInt32LE(rate, 24);
  buf.writeUInt32LE(rate * 2, 28); buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34); buf.write('data', 36);
  buf.writeUInt32LE(samples.length * 2, 40);
  for (let i = 0; i < samples.length; i += 1) buf.writeInt16LE(Math.round(Math.max(-1, Math.min(1, samples[i])) * 32767), 44 + i * 2);
  fs.writeFileSync(file, buf);
}

// One sentence at a time sounds better than a long block; join with a short natural pause.
async function kokoroVoice(text, outputPath, { voice, speed, dtype }) {
  const tts = await loadKokoro(dtype);
  const parts = (text.match(/[^.!?]+[.!?]+["')\]]*|[^.!?]+$/g) || [text]).map((x) => x.trim()).filter(Boolean);
  const chunks = [];
  let rate = 24000;
  for (const sentence of parts) {
    const a = await tts.generate(sentence, { voice, speed });
    rate = a.sampling_rate || rate;
    chunks.push(Float32Array.from(a.audio));
    chunks.push(new Float32Array(Math.round(rate * 0.22)));
  }
  chunks.pop();
  const all = new Float32Array(chunks.reduce((n, c) => n + c.length, 0));
  let at = 0;
  for (const c of chunks) { all.set(c, at); at += c.length; }
  const wav = outputPath.replace(/\.[^.]+$/, '') + '.raw.wav';
  writeWavFile(wav, all, rate);
  await runFFmpeg(['-y', '-i', wav, '-af', POLISH, '-ac', '1', outputPath]);
  fs.unlinkSync(wav);
  return outputPath;
}

// Strip the [[red word]] caption markup before the text is spoken.
const speakable = (t) => t.replace(/\[\[(.+?)\]\]/g, '$1').replace(/\s+/g, ' ').trim();

async function generateVoice(text, outputPath, opts = {}) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  const clean = speakable(text);
  if (opts.dry) return dryVoice(clean, outputPath);
  const provider = opts.provider || process.env.VOICE_PROVIDER || 'kokoro';
  if (provider === 'kokoro') {
    return kokoroVoice(clean, outputPath, {
      voice: opts.kokoroVoice || process.env.KOKORO_VOICE || 'bf_emma',
      speed: Number(opts.kokoroSpeed || process.env.KOKORO_SPEED || 0.95),
      dtype: opts.kokoroDtype || process.env.KOKORO_DTYPE || 'fp32',
    });
  }
  const apiKey = geminiKey();
  if (!apiKey) {
    throw new Error('No Gemini key found. Put GEMINI_API_KEY=... in stickman-history/.env (free key: https://aistudio.google.com/apikey), or run with --dry-voice to test without one.');
  }
  return geminiTTS(clean, outputPath, {
    apiKey,
    model: opts.model || process.env.GEMINI_TTS_MODEL || 'gemini-3.8-flash-tts',
    voice: opts.voice || process.env.GEMINI_TTS_VOICE || 'Kore',
    style: opts.style || '',
  });
}

module.exports = { generateVoice, kokoroVoice, probeDuration, runFFmpeg, loadEnv, speakable };

// Quick voice test:  node src/voice.js "Hello from history" out/test.mp3 [--dry]
if (require.main === module) {
  (async () => {
    loadEnv(path.join(__dirname, '..', '.env'));
    const args = process.argv.slice(2).filter((a) => a !== '--dry');
    const dry = process.argv.includes('--dry');
    const text = args[0] || 'In the fourteen forties, a goldsmith named Johannes Gutenberg had an idea.';
    const out = args[1] || path.join('out', 'voice-test.mp3');
    await generateVoice(text, out, { dry });
    console.log(`Wrote ${out} (${(await probeDuration(out)).toFixed(1)}s)`);
  })().catch((e) => { console.error(e.message); process.exit(1); });
}
