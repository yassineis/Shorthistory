'use strict';
// Topic -> full script (scenes with narration, setting, actors, props) written by Gemini's free text API.
// mockStory() builds a placeholder script with no network, for testing the pipeline.

const { loadEnv } = require('./voice');

const SETTINGS = ['edo_street', 'egypt_temple', 'roman_forum', 'medieval_town', 'viking_coast', 'greek_agora', 'china_palace',
  'desert', 'ship_sea', 'old_west', 'london', 'cave', 'steppe', 'jungle_temple', 'battlefield', 'harbor', 'moon', 'snow', 'museum', 'interior', 'stairwell'];
const POSES = ['stand', 'walk', 'wave', 'point', 'cheer', 'think', 'hold', 'slump', 'write'];
const HATS = ['crown', 'helmet', 'cap', 'kasa', 'nemes', 'laurel', 'viking', 'tophat', 'hood', 'tricorn', 'turban', 'kabuto', 'cowboy'];
const OUTFITS = ['red', 'blue', 'green', 'yellow', 'purple', 'brown', 'white', 'black', 'orange', 'pink', 'teal', 'gray'];
const HOLDS = ['book', 'scroll', 'flag', 'coins', 'bulb', 'quill'];
const PROPS = ['sun', 'cloud', 'tree', 'house', 'town', 'castle', 'ship', 'flag', 'crown', 'scroll', 'book', 'stack', 'press',
  'coins', 'mountain', 'map', 'bulb', 'clock', 'gear', 'arrow', 'pages', 'crowd', 'quill'];
const EMOTES = ['!', '?', '!?', '...', ':('];
const SFX = ['door', 'steps', 'ding', 'coins', 'drum', 'bell', 'crowd', 'thud']; // small sound effects made by the code
const SFX_ENH = [...SFX, 'glass', 'splash', 'crash', 'laugh', 'gasp', 'boing', 'thunder', 'applause', 'creak', 'zap']; // enhanced mode (option A)
const ACTIONS = ['throw', 'swing', 'fall', 'impact', 'door', 'sail', 'glide', 'train']; // prop actions drawn by render/sb_actions.py
const MOODS = ['shock', 'angry', 'smug', 'excited', 'scared', 'sad', 'joy', 'curious', 'worry'];
// Spoken words per second at the narrator's speed (about 3.5 at speed 1.21, measured from real runs). Used for the length pre-check.
const wps = () => 2.9 * (parseFloat(process.env.KOKORO_SPEED) || 1.21);

const words = (s) => String(s).replace(/\[\[|\]\]/g, '').split(/\s+/).filter(Boolean).length;
const pick = (v, list, d) => (list.includes(v) ? v : d);

function estimate(story) {
  const pad = story.mode === 'true' || story.enhanced ? 0.4 : 1.0; // true-story mode cuts tighter between shots
  return story.scenes.reduce((a, s) => a + words(s.narration) / wps() + pad, 0) + 3.3; // + the subscribe line at the end
}

// Story shapes that suit short narrated cartoons: always one main character and a TRUE ending that pays off the hook.
const SHAPES = {
  underdog: 'STORY SHAPE (mocked underdog): one main character does something that looks foolish, people laugh or refuse to listen, and a real physical or scientific principle proves them right in the end. Show the mockery clearly in the middle, then the payoff.',
  experiment: 'STORY SHAPE (weird real experiment or institution): one main character (or the odd person who runs it) does something that sounds absurd; explain the real reason it exists and what it proved or protects. The twist is why it makes sense.',
  scheme: 'STORY SHAPE (clever scheme or loophole): one main character plans something sneaky or clever; show the plan step by step, then a twist that reveals how it really worked.',
};
const shapeFor = (topic) => (SHAPES[topic.type] ? `${SHAPES[topic.type]}${topic.character ? ` MAIN CHARACTER: ${topic.character}.` : ''}\n` : '');

// Option 9 'true story' mode: mocked-underdog style with short one-sentence shots (inspired by a viral stickman Shorts tutorial).
function buildTruePrompt(topic, avoid, o) {
  const shape = SHAPES[topic.type] || SHAPES.underdog;
  return `You write scripts for short narrated cartoon videos that tell ONE TRUE story about a real person, in a funny, friendly cartoon style (round white heads, colourful settings). The voice is a fast, warm narrator speaking English.

TOPIC: ${topic.title}
ANGLE: ${topic.angle || ''}
${shape}${topic.character ? ` MAIN CHARACTER: ${topic.character}.` : ''}

RULES
- The story is TRUE. Real people, real events, real outcome. The only things you may dramatise are small things around the edges: a doubter's short jokes, a rival, a trophy, a reaction. List every dramatised detail in "invented_details" so the human can see what is real and what is invented. Never invent the main facts, dates, outcome or science.
- HOOK (first sentence): a person doing something that looks strange, with one specific number that is part of the real story (a count, a year, an age, a distance), for example "A golfer hammers 327 dents into his new ball before the village tournament." Name the main subject within the first 8 words. Never start with a date alone, "Today we...", or "Have you ever wondered".
- SHOTS: ${o.minScenes} to ${o.maxScenes} scenes. Each scene is ONE sentence of 12 to 17 words: one place, one clear action, one new fact or beat. Stay in the same setting for consecutive scenes unless the location really changes. Total ${o.minWords} to ${o.maxWords} words. The finished video must not be longer than 1 minute 30 seconds.
- THE DOUBTERS: show the mockery in the middle. Give the doubters 1 or 2 very short funny lines (3 to 6 words) in quotes, such as "Nice potato!" and "Pothole alert!". Light teasing only, never about real victims.
- PAYOFF: in the last third, a side-by-side result: first what the doubter's way did, then what the underdog's way did ("First..., then..."). Then one short last line that repeats a key word or image from the first sentence. No goodbye, no call to subscribe, no summary: the video adds its own short subscribe line.
- MAIN CHARACTER LOOK: the main character is always the FIRST actor of every scene, with the identical outfit, hat and beard in all scenes. Describe that look once in "character". Other people have other outfits.
- FIRST SCENE MATCHES THE HOOK: its setting, props and pose show exactly what the first sentence says (indoors use "museum", "interior" or "stairwell"). Give it an active pose and an emote.
- Narration is plain spoken English: no emojis, no stage directions, no hashtags. Wrap 1 to 3 key words per scene in [[double brackets]] so they show in red. Write numbers so they are easy to speak.
${avoid.length ? `- Do NOT repeat these already-made stories: ${avoid.slice(0, 40).join('; ')}.\n` : ''}${o.fix ? `- FIX FROM LAST TRY: ${o.fix}\n` : ''}
Return ONLY JSON with this shape:
{
 "title": "title under 60 characters, in one of these patterns: \"They laughed at [odd idea]\", \"Why [normal thing] is secretly weird\", \"The [person] who [odd action]\", or a question; never a lie",
 "description": "2 sentence YouTube description; the first sentence repeats the odd detail from the title",
 "tags": ["6 to 10 tags: specific ones first (person, place, object, science idea), then 2 broad ones"],
 "facts_to_check": ["every date, number and claim a human should verify"],
 "invented_details": ["each small thing you dramatised, such as the rival, the trophy, a joke"],
 "character": {"name": "main character", "outfit": one of ${JSON.stringify(OUTFITS)}, "outfit_kind": "tunic" or "robe", "hat": optional one of ${JSON.stringify(HATS)}},
 "scenes": [
  {
   "kicker": "2-4 word on-screen title",
   "stamp": "optional short red stamp such as a year, else empty string",
   "narration": "ONE spoken sentence",
   "sfx": optional, one of ${JSON.stringify(SFX)}, only when something in the scene really makes that sound,
   "setting": one of ${JSON.stringify(SETTINGS)},
   "actors": [ {"x": 0.2-0.8, "pose": one of ${JSON.stringify(POSES)}, "outfit": one of ${JSON.stringify(OUTFITS)}, "outfit_kind": "tunic" or "robe", "hat": optional one of ${JSON.stringify(HATS)}, "holds": optional one of ${JSON.stringify(HOLDS)}, "face": "left" or "right", "talk": true for the speaking character, "emote": optional one of ${JSON.stringify(EMOTES)}, "to": optional x to walk to } ],
   "props": [ {"type": one of ${JSON.stringify(PROPS)}, "x": 0.1-0.9, "size": 0.6-1.4} ]
  }
 ]
}`;
}

// True-story mode: the main character (first actor) looks the same in every scene, and the invented bits are listed.
// Enhanced look and sound (option A, and the default for options 1 and 2): the normal prompt plus prop actions,
// face moods on a key word, and more sound effects. Applied on top of whichever base prompt is used.
function enhancePrompt(p) {
  p = p.replace(`"sfx": optional, one of ${JSON.stringify(SFX)}`, `"sfx": optional, one of ${JSON.stringify(SFX_ENH)}`);
  p = p.replace('The finished video must not be longer than 1 minute 30 seconds.', 'The finished video must be between 1 minute and 1 minute 30 seconds, never longer.');
  p = p.replace(/\n ?Return ONLY JSON/, `
- ACTIONS: in about one scene out of three, give an "action" that animates something with the main character: ${ACTIONS.join(', ')}. throw = the main character throws the held prop, swing = swings it, fall = the prop falls and crashes, impact = a hit with a screen shake, door = a door opens behind, sail = a boat sails past, glide = a plane glides past, train = a train rushes past. Use an action only when it matches what the sentence says. Skip it in other scenes.
- REACTIONS: for each actor you may set "mood" (${MOODS.join(', ')}) which the face switches to on the scene's key word. Use it on onlookers and doubters (smug, angry, shock) and on the main character at the payoff (joy, excited). Add "key": the one word of the narration (no punctuation) where the reaction or action lands.
- SOUND: add "sfx" in about half the scenes (glass for something breaking, splash for water, crash for a big hit, laugh when people laugh, gasp for shock, boing for something bouncy, thunder, applause at the payoff, creak for an old door, zap for science).

Return ONLY JSON`);
  p = p.replace(/"narration": "[^"]*",/, (m) => m + ' "key": "one word of the narration", "action": optional, one of ' + JSON.stringify(ACTIONS) + ',');
  p = p.replace('"talk": true for the speaking character,', '"talk": true for the speaking character, "mood": optional, one of ' + JSON.stringify(MOODS) + ',');
  return p;
}
const buildEnhancedPrompt = (topic, avoid, o) => enhancePrompt(buildTruePrompt(topic, avoid, o)); // option A: true stories
const buildEnhancedHistoryPrompt = (topic, avoid, o) => enhancePrompt(buildPrompt(topic, avoid, o)); // options 1 and 2

function finishTrue(raw, story) {
  const c = raw && raw.character ? raw.character : {};
  const first = story.scenes[0].stage.actors[0];
  const look = {
    outfit: pick(c.outfit, OUTFITS, first.outfit),
    outfit_kind: c.outfit_kind === 'robe' ? 'robe' : (c.outfit_kind === 'tunic' ? 'tunic' : first.outfit_kind),
    hat: HATS.includes(c.hat) ? c.hat : first.hat,
  };
  for (const s of story.scenes) {
    const a = s.stage.actors[0];
    a.outfit = look.outfit; a.outfit_kind = look.outfit_kind;
    if (look.hat) a.hat = look.hat; else delete a.hat;
  }
  story.mode = 'true';
  story.invented_details = (Array.isArray(raw.invented_details) ? raw.invented_details : []).map(String);
  return story;
}

function buildPrompt(topic, avoid, o) {
  return `You write scripts for short animated history videos in a funny, friendly cartoon style (stick figures with white round heads, colourful period settings). The voice is a warm narrator speaking English.

TOPIC: ${topic.title}
ANGLE: ${topic.angle || ''}
${shapeFor(topic)}
RULES
- Tell ONE complete story with a hook in the first sentence, a clear middle, and a satisfying last line.
- HOOK (first scene): the first sentence drops the viewer straight into one specific person, object or odd fact in action, for example "He crawled down the road at midnight, hammering glass marbles into the tarmac." Never start with a date, "In the year...", "Today we..." or "Have you ever wondered". The first sentence must name the main subject people search for (for example the Mona Lisa, the pyramids, Genghis Khan) within its first 8 words. The hook must be true and must be paid off later.
- FIRST SCENE MATCHES THE HOOK: the first scene's setting, props and actors must show exactly what the first sentence says (a "dark stairwell" means setting "stairwell"; a gallery or museum means "museum"; a room, workshop, court or house interior means "interior"). Use the indoor settings for anything that happens indoors. Give the first scene a clear, active pose and an emote ("!" or "?"), never a plain standing pose.
- CURIOSITY TURN (about the middle): one short line that makes the viewer need the answer, such as "But it gets weird." or "But how could that possibly work?" Keep the answer for the last third.
- LAST LINE: a short punchy twist or payoff that repeats a key word or image from the first sentence, so the ending flows straight back into the start when the video loops. Do not write a goodbye, a call to subscribe or a summary: the video adds its own short subscribe line after your last line.
- Keep every scene moving: each scene brings one new fact, image or surprise. No filler, no repeating the topic.
- Only use facts that are well documented. Do not invent dates, numbers, names or quotes. If something is disputed, say "according to" or "historians think". If unsure, leave it out.
- Light humour is welcome (funny reactions, understatement), never at the expense of real victims.
- ${o.minScenes} to ${o.maxScenes} scenes. Each narration is 20 to 26 words. Total ${o.minWords} to ${o.maxWords} words. The finished video must NOT be longer than 1 minute 30 seconds (and not shorter than about 1 minute 10), so be brief: no filler, no second explanation of the same point.
- Narration is plain spoken English: no emojis, no stage directions, no hashtags. Wrap 1 to 3 key words per scene in [[double brackets]] so they show in red in the captions.
- Years and big numbers are written so they are easy to speak.
${avoid.length ? `- Do NOT repeat these already-made stories: ${avoid.slice(0, 40).join('; ')}.\n` : ''}${o.fix ? `- FIX FROM LAST TRY: ${o.fix}\n` : ''}
Return ONLY JSON with this shape:
{
 "title": "curiosity title under 60 characters, written as a question (Why did..., How did..., What did X think of Y?), or as \"Why [normal thing] is secretly weird\", or as \"They laughed at [odd idea]\", or as one odd specific detail; never a lie; the story must answer it",
 "description": "2 sentence YouTube description; the first sentence repeats the question or odd detail from the title",
 "tags": ["6 to 10 tags: first the specific ones (people, place, era, object from this story), then 2 broad ones such as history facts"],
 "facts_to_check": ["every date, number and claim a human should verify"],
 "scenes": [
  {
   "kicker": "2-4 word on-screen title",
   "stamp": "optional short red stamp such as a year, else empty string",
   "narration": "spoken text",
   "sfx": optional, one of ${JSON.stringify(SFX)}, only when something in the scene really makes that sound (a door opens, footsteps, a coin, a drum, a bell, a crowd, a thud),
   "setting": one of ${JSON.stringify(SETTINGS)},
   "actors": [ {"x": 0.2-0.8, "pose": one of ${JSON.stringify(POSES)}, "outfit": one of ${JSON.stringify(OUTFITS)}, "outfit_kind": "tunic" or "robe", "hat": optional one of ${JSON.stringify(HATS)}, "holds": optional one of ${JSON.stringify(HOLDS)}, "face": "left" or "right", "talk": true for the speaking character, "emote": optional one of ${JSON.stringify(EMOTES)} for a funny reaction, "to": optional x to walk to } ],
   "props": [ {"type": one of ${JSON.stringify(PROPS)}, "x": 0.1-0.9, "size": 0.6-1.4} ]
  }
 ]
}
Use 1 to 3 actors per scene, with costumes that fit the era and place. Keep the same setting for neighbouring scenes unless the story moves. Use 0 to 2 props per scene.`;
}

// ---- Gemini text, same approach as YOUTUBE-AGENT (kids-channel/story/gemini-rest.js) ----
// Model names change, so we do not trust a fixed name: ask the API which models this key can use, test them
// together with a tiny question, take the fastest one that answers, and remember it for next time.
const path = require('path');
const fs = require('fs');
const BASE = 'https://generativelanguage.googleapis.com/v1beta';
const MODEL_CACHE = path.join(__dirname, '..', 'out', '.text-model');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

class QuotaError extends Error {}
class TempError extends Error {}   // network trouble, timeout, 5xx: worth trying again
class MissingModel extends Error {} // 404: this model name is not available for this key

function apiKey() {
  const key = ['GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_KEY'].map((n) => process.env[n]).find(Boolean);
  if (!key) throw new Error('No Gemini key found. Put GEMINI_API_KEY=... in the .env file (free key: https://aistudio.google.com/apikey), or use --mock-story to test without one.');
  return key;
}

async function listModels(key) {
  const res = await fetch(`${BASE}/models?pageSize=200`, { headers: { 'x-goog-api-key': key }, signal: AbortSignal.timeout(30000) });
  if (!res.ok) throw new Error(`models list failed (${res.status})`);
  const data = await res.json();
  return (data.models || [])
    .filter((m) => (m.supportedGenerationMethods || []).includes('generateContent'))
    .map((m) => String(m.name).replace(/^models\//, ''))
    .filter((n) => /^gemini/.test(n) && !/image|tts|live|embed|audio|vision|robotics|computer|native|thinking|learnlm|omni|veo|imagen|video|music|lyria|gemma/i.test(n));
}

// Steadiest first: stable "flash", then "flash-lite", then previews, then the rest.
function rankModels(names) {
  const score = (n) => (/preview|exp/i.test(n) ? 10 : 0) + (/flash-lite|lite/i.test(n) ? 3 : /flash/i.test(n) ? 0 : 6);
  return [...new Set(names)].sort((a, b) => score(a) - score(b) || b.localeCompare(a));
}

async function once(key, model, prompt, ms) {
  let res;
  try {
    res = await fetch(`${BASE}/models/${model}:generateContent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-goog-api-key': key },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { responseMimeType: 'application/json', temperature: 0.8, maxOutputTokens: 16384 } }),
      signal: AbortSignal.timeout(ms),
    });
  } catch (e) {
    const timeout = /timeout|abort/i.test(e.message);
    throw new TempError(`Gemini (${model}) ${timeout ? 'did not answer in time' : 'could not be reached'}. Check the internet connection, a VPN or a firewall.`);
  }
  const raw = await res.text();
  if (!res.ok) {
    const msg = raw.replace(key, '[hidden key]').slice(0, 300);
    if (res.status === 429 || /RESOURCE_EXHAUSTED|quota/i.test(msg)) throw new QuotaError(`Gemini limit reached (${res.status}).`);
    if (res.status === 404) throw new MissingModel(`Model ${model} not found`);
    if ([500, 502, 503, 504].includes(res.status)) throw new TempError(`Gemini (${model}) error ${res.status}`);
    throw new Error(`Gemini (${model}) error ${res.status}: ${msg}${res.status === 400 || res.status === 403 ? ' | Check GEMINI_API_KEY in the .env file.' : ''}`);
  }
  let data;
  try { data = JSON.parse(raw); } catch (e) { throw new TempError('Gemini sent an answer that is not JSON'); }
  const text = ((data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts) || []).map((p) => p.text || '').join('');
  if (!text.trim()) throw new TempError('Gemini sent an empty answer');
  return text;
}

let currentModel = null;
const bad = new Map(); // model -> time until which we skip it (Infinity = model does not exist for this key, skipped for the whole run)

const markBad = (name, e) => bad.set(name, e instanceof MissingModel ? Infinity : Date.now() + (e instanceof QuotaError ? 10 * 60000 : 60000));

// Test the models that are not marked bad, five at a time, and take the fastest one that answers.
// If none of a batch answers, go straight on to the next five, so every model the key offers gets a turn.
async function pickModel(key, preferred) {
  console.log('  checking which Gemini model is ready...');
  let names = [preferred];
  try { names.push(...rankModels(await listModels(key))); } catch (e) { /* try the default only */ }
  const usable = [...new Set(names.filter(Boolean))].filter((n) => !(bad.get(n) > Date.now()));
  for (let k = 0; k < usable.length; k += 5) {
    const results = await Promise.all(usable.slice(k, k + 5).map(async (name) => {
      const t0 = Date.now();
      try { await once(key, name, 'Reply with exactly this JSON and nothing else: {"ok": true}', 25000); return { name, ms: Date.now() - t0, ok: true }; } catch (e) {
        markBad(name, e);
        return { name, ok: false, why: e instanceof QuotaError ? 'no free quota' : e instanceof MissingModel ? 'not found' : e.message.slice(0, 60) };
      }
    }));
    results.forEach((r) => console.log(r.ok ? `    ${r.name}: ready (${(r.ms / 1000).toFixed(1)}s)` : `    ${r.name}: not ready (${r.why})`));
    const ready = results.filter((r) => r.ok).sort((a, b) => a.ms - b.ms);
    if (ready.length) {
      try { fs.mkdirSync(path.dirname(MODEL_CACHE), { recursive: true }); fs.writeFileSync(MODEL_CACHE, ready[0].name); } catch (e) { /* not important */ }
      console.log(`    using ${ready[0].name}`);
      return ready[0].name;
    }
    if (k + 5 < usable.length) console.log('    none of these answered, trying the next models...');
  }
  return null;
}

// Keeps going, switching to another model whenever one stops, until the story arrives or 10 minutes pass.
async function geminiText(prompt) {
  const key = apiKey();
  let cached = '';
  try { cached = fs.readFileSync(MODEL_CACHE, 'utf8').trim(); } catch (e) { /* no cache yet */ }
  const preferred = process.env.GEMINI_TEXT_MODEL || cached || 'gemini-3.8-flash';
  const patience = Number(process.env.STORY_PATIENCE_MS) || 10 * 60000;
  const pause = Number(process.env.STORY_WAIT_MS) || 20000;
  const started = Date.now();
  let last;
  for (;;) {
    if (Date.now() - started > patience) break;
    if (!currentModel) {
      currentModel = await pickModel(key, preferred);
      if (!currentModel) {
        bad.forEach((until, n) => { if (until !== Infinity) bad.delete(n); }); // forget short-term failures, retry after a pause
        console.log(`  no model is ready right now. Checking again in ${Math.round(pause / 1000)}s...`);
        await sleep(pause);
        continue;
      }
    }
    try { return await once(key, currentModel, prompt, 120000); } catch (e) {
      last = e;
      if (!(e instanceof QuotaError || e instanceof TempError || e instanceof MissingModel)) throw e;
      markBad(currentModel, e);
      console.log(`  ${currentModel} stopped (${e.message}). Trying another model...`);
      currentModel = null;
    }
  }
  throw new Error(`Gemini did not give a story in ${Math.round(patience / 60000)} minutes${last ? ` (last problem: ${last.message})` : ''}. Check the internet connection, then run again: finished stories are saved.`);
}

function parseJson(text) {
  const t = text.trim().replace(/^```(?:json)?/i, '').replace(/```$/, '').trim();
  try { return JSON.parse(t); } catch (e) {
    const a = t.indexOf('{'), b = t.lastIndexOf('}');
    return JSON.parse(t.slice(a, b + 1));
  }
}

// Make whatever the model returned safe for the renderer: unknown values fall back to defaults.
function normalize(raw, topic) {
  if (!raw || !Array.isArray(raw.scenes) || raw.scenes.length < 3) throw new Error('The story has no usable scenes.');
  let lastSetting = topic.setting || 'medieval_town';
  const scenes = raw.scenes.map((s, i) => {
    const narration = String(s.narration || '').trim();
    if (!narration) throw new Error(`Scene ${i + 1} has no narration.`);
    const setting = pick(s.setting, SETTINGS, lastSetting);
    lastSetting = setting;
    const actors = (Array.isArray(s.actors) ? s.actors : []).slice(0, 3).map((a, k) => {
      const o = {
        x: Math.min(0.85, Math.max(0.12, Number(a.x) || 0.3 + 0.3 * k)),
        pose: pick(a.pose, POSES, 'stand'),
        outfit: pick(a.outfit, OUTFITS, OUTFITS[(i + k) % OUTFITS.length]),
        outfit_kind: a.outfit_kind === 'robe' ? 'robe' : 'tunic',
        face: a.face === 'left' ? 'left' : 'right',
      };
      if (HATS.includes(a.hat)) o.hat = a.hat;
      if (HOLDS.includes(a.holds)) o.holds = a.holds;
      if (a.talk) o.talk = true;
      if (MOODS.includes(a.mood)) o.mood = a.mood;
      if (EMOTES.includes(a.emote)) o.emote = a.emote;
      if (Number.isFinite(Number(a.to)) && a.to !== null && a.to !== '') o.to = Math.min(0.88, Math.max(0.1, Number(a.to)));
      return o;
    });
    if (!actors.length) actors.push({ x: 0.4, pose: 'stand', outfit: 'blue', outfit_kind: 'tunic', face: 'right', talk: true });
    if (!actors.some((a) => a.talk)) actors[0].talk = true;
    const props = (Array.isArray(s.props) ? s.props : []).filter((p) => PROPS.includes(p.type)).slice(0, 2).map((p) => ({
      type: p.type, x: Math.min(0.9, Math.max(0.1, Number(p.x) || 0.7)), size: Math.min(1.5, Math.max(0.5, Number(p.size) || 1)),
    }));
    return {
      kicker: String(s.kicker || '').slice(0, 28), stamp: String(s.stamp || '').slice(0, 14), narration,
      setting, stage: { props, actors }, ...(SFX_ENH.includes(s.sfx) ? { sfx: s.sfx } : {}),
      ...(ACTIONS.includes(s.action) ? { action: s.action } : {}), ...(s.key ? { key: String(s.key).replace(/[^A-Za-z0-9']/g, '') } : {}),
    };
  });
  return {
    title: String(raw.title || topic.title).slice(0, 90),
    description: String(raw.description || ''),
    tags: (Array.isArray(raw.tags) ? raw.tags : []).map(String).slice(0, 15),
    facts_to_check: (Array.isArray(raw.facts_to_check) ? raw.facts_to_check : []).map(String),
    style: 'a5', voice: { name: 'Kore' }, scenes,
  };
}

// Offline placeholder (not real history): lets you test the pipeline without a key or internet.
function mockStory(topic) {
  const beats = [
    'Long ago, a story began that people still talk about today, and it all starts with a very surprising [[question]].',
    'In those days life was hard, news travelled slowly, and almost nobody expected what was about to happen next.',
    'Our hero, who was not famous yet, looked at the problem and decided there had to be a [[better way]].',
    'Friends and neighbours laughed at first, because new ideas always sound a little silly before they work.',
    'But the plan moved forward, one careful step at a time, with plenty of mistakes along the road.',
    'Then came the first big test, and for a moment everyone held their breath and stared at the [[result]].',
    'It did not go perfectly, and a few people said they had told everyone so, loudly and often.',
    'Still, the team learned something important from the failure, and they came back the next morning with a new idea.',
    'Word began to spread across the land, carried by travellers, traders and anyone with a good story to tell.',
    'Soon the whole region was talking about it, and even the doubters came to see it with their own eyes.',
    'The change was not instant, but year after year it made ordinary life a little easier for everybody.',
    'Historians later pointed to this moment as a true [[turning point]], though nobody felt that way at the time.',
    'And the funny part is that the biggest lesson was simple: curiosity, patience and a little courage can change a lot.',
    'So the next time you hear this story, remember the people behind it, who were just trying to solve one problem.',
    'That is how a small moment became a big piece of history, and why we still remember it today.',
  ];
  const settings = [topic.setting || 'medieval_town'];
  const posesA = ['stand', 'point', 'think', 'wave', 'hold', 'cheer', 'slump', 'walk'];
  const emotes = ['', '?', '', '!', '', '!?', '...', ''];
  return {
    title: `${topic.title} (mock)`, description: 'Placeholder script for testing.', tags: ['history', 'mock'], facts_to_check: ['MOCK STORY - not real history'],
    style: 'a5', voice: { name: 'Kore' },
    scenes: beats.map((b, i) => ({
      kicker: i === 0 ? topic.title.slice(0, 26) : `Part ${i + 1}`, stamp: i === 0 ? 'MOCK' : '', narration: b, setting: settings[0],
      stage: {
        props: i % 3 === 0 ? [{ type: ['tree', 'house', 'book', 'map', 'castle'][i % 5], x: 0.75, size: 1 }] : [],
        actors: [
          { x: 0.3, pose: posesA[i % posesA.length], outfit: OUTFITS[i % OUTFITS.length], outfit_kind: i % 2 ? 'robe' : 'tunic', face: 'right', talk: true, hat: HATS[i % HATS.length], emote: emotes[i % emotes.length] },
          { x: 0.6, pose: posesA[(i + 3) % posesA.length], outfit: OUTFITS[(i + 4) % OUTFITS.length], face: 'left' },
        ],
      },
    })),
  };
}

// opts: { mock, avoid: [titles], minWords, maxWords, minScenes, maxScenes, fix }
async function writeStory(topic, opts = {}) {
  loadEnv(opts.envFile);
  const isEnhTrue = opts.mode === 'enhanced';
  const isEnhHist = !opts.mode && opts.enhance === true; // options 1 and 2: library history topics, enhanced look and sound
  const isEnh = isEnhTrue || isEnhHist;
  if (opts.mock) {
    const m = normalize(mockStory(topic), topic);
    if (!isEnh) return opts.mode === 'true' ? finishTrue({}, m) : m;
    const acts = ['throw', 'swing', 'fall', 'impact', 'door', 'sail', 'glide', 'train'], moods = ['shock', 'angry', 'smug', 'excited', 'scared', 'joy', 'curious', 'worry'];
    m.scenes.forEach((s, i) => { if (i % 2 === 1) s.action = acts[(i >> 1) % acts.length]; s.stage.actors[s.stage.actors.length - 1].mood = moods[i % moods.length]; });
    if (isEnhTrue) finishTrue({}, m);
    m.enhanced = true; return m;
  }
  const isTrue = opts.mode === 'true' || isEnhTrue;
  const o = isEnhHist ? { minWords: 205, maxWords: 245, minScenes: 9, maxScenes: 11, ...opts } : isEnh ? { minWords: 200, maxWords: 240, minScenes: 14, maxScenes: 18, ...opts } : isTrue ? { minWords: 215, maxWords: 255, minScenes: 14, maxScenes: 18, ...opts } : { minWords: 215, maxWords: 255, minScenes: 9, maxScenes: 11, ...opts };
  let fix = opts.fix || '';
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const raw = parseJson(await geminiText((isEnhHist ? buildEnhancedHistoryPrompt : isEnhTrue ? buildEnhancedPrompt : isTrue ? buildTruePrompt : buildPrompt)(topic, opts.avoid || [], { ...o, fix })));
    const story = isTrue ? finishTrue(raw, normalize(raw, topic)) : normalize(raw, topic);
    if (isEnh) story.enhanced = true;
    const est = estimate(story);
    const [lo, hi] = isEnh ? [64, 86] : [70, 88];
    if (est >= lo && est <= hi) return story;
    fix = `The last version would run about ${Math.round(est)} seconds. It must be between ${isEnh ? '68 and 82' : '75 and 85'} seconds, so the finished video stays under 1 minute 30: ${est < lo ? 'add scenes or lengthen narration' : 'cut scenes or shorten narration'}.`;
    if (attempt === 3) return story; // make.js measures the real length and the caller decides
  }
}

module.exports = { buildEnhancedPrompt, writeStory, estimate, normalize, mockStory, SETTINGS };
