'use strict';
// Voice generation, ported from YOUTUBE-AGENT (utils/ai-video-generator.js -> generateGeminiTTS).
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

// Strip the [[red word]] caption markup before the text is spoken.
const speakable = (t) => t.replace(/\[\[(.+?)\]\]/g, '$1').replace(/\s+/g, ' ').trim();

async function generateVoice(text, outputPath, opts = {}) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  const clean = speakable(text);
  if (opts.dry) return dryVoice(clean, outputPath);
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

module.exports = { generateVoice, probeDuration, runFFmpeg, loadEnv, speakable };

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
