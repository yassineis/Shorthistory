'use strict';
// Topic -> full script (scenes with narration, setting, actors, props) written by Gemini's free text API.
// mockStory() builds a placeholder script with no network, for testing the pipeline.

const { loadEnv } = require('./voice');

const SETTINGS = ['edo_street', 'egypt_temple', 'roman_forum', 'medieval_town', 'viking_coast', 'greek_agora', 'china_palace',
  'desert', 'ship_sea', 'old_west', 'london', 'cave', 'steppe', 'jungle_temple', 'battlefield', 'harbor', 'moon', 'snow'];
const POSES = ['stand', 'walk', 'wave', 'point', 'cheer', 'think', 'hold', 'slump', 'write'];
const HATS = ['crown', 'helmet', 'cap', 'kasa', 'nemes', 'laurel', 'viking', 'tophat', 'hood', 'tricorn', 'turban', 'kabuto', 'cowboy'];
const OUTFITS = ['red', 'blue', 'green', 'yellow', 'purple', 'brown', 'white', 'black', 'orange', 'pink', 'teal', 'gray'];
const HOLDS = ['book', 'scroll', 'flag', 'coins', 'bulb', 'quill'];
const PROPS = ['sun', 'cloud', 'tree', 'house', 'town', 'castle', 'ship', 'flag', 'crown', 'scroll', 'book', 'stack', 'press',
  'coins', 'mountain', 'map', 'bulb', 'clock', 'gear', 'arrow', 'pages', 'crowd', 'quill'];
const EMOTES = ['!', '?', '!?', '...', ':('];
const WPS = 2.5; // spoken words per second, used only for the pre-check; the real length is measured after the voice is made

const words = (s) => String(s).replace(/\[\[|\]\]/g, '').split(/\s+/).filter(Boolean).length;
const pick = (v, list, d) => (list.includes(v) ? v : d);

function estimate(story) {
  return story.scenes.reduce((a, s) => a + words(s.narration) / WPS + 1.0, 0);
}

function buildPrompt(topic, avoid, o) {
  return `You write scripts for short animated history videos in a funny, friendly cartoon style (stick figures with white round heads, colourful period settings). The voice is a warm narrator speaking English.

TOPIC: ${topic.title}
ANGLE: ${topic.angle || ''}

RULES
- Tell ONE complete story with a hook in the first sentence, a clear middle, and a satisfying last line.
- Only use facts that are well documented. Do not invent dates, numbers, names or quotes. If something is disputed, say "according to" or "historians think". If unsure, leave it out.
- Light humour is welcome (funny reactions, understatement), never at the expense of real victims.
- ${o.minScenes} to ${o.maxScenes} scenes. Each narration is 18 to 26 words. Total ${o.minWords} to ${o.maxWords} words.
- Narration is plain spoken English: no emojis, no stage directions, no hashtags. Wrap 1 to 3 key words per scene in [[double brackets]] so they show in red in the captions.
- Years and big numbers are written so they are easy to speak.
${avoid.length ? `- Do NOT repeat these already-made stories: ${avoid.slice(0, 40).join('; ')}.\n` : ''}${o.fix ? `- FIX FROM LAST TRY: ${o.fix}\n` : ''}
Return ONLY JSON with this shape:
{
 "title": "catchy YouTube title under 70 characters",
 "description": "2 sentence YouTube description",
 "tags": ["8 to 12 tags"],
 "facts_to_check": ["every date, number and claim a human should verify"],
 "scenes": [
  {
   "kicker": "2-4 word on-screen title",
   "stamp": "optional short red stamp such as a year, else empty string",
   "narration": "spoken text",
   "setting": one of ${JSON.stringify(SETTINGS)},
   "actors": [ {"x": 0.2-0.8, "pose": one of ${JSON.stringify(POSES)}, "outfit": one of ${JSON.stringify(OUTFITS)}, "outfit_kind": "tunic" or "robe", "hat": optional one of ${JSON.stringify(HATS)}, "holds": optional one of ${JSON.stringify(HOLDS)}, "face": "left" or "right", "talk": true for the speaking character, "emote": optional one of ${JSON.stringify(EMOTES)} for a funny reaction, "to": optional x to walk to } ],
   "props": [ {"type": one of ${JSON.stringify(PROPS)}, "x": 0.1-0.9, "size": 0.6-1.4} ]
  }
 ]
}
Use 1 to 3 actors per scene, with costumes that fit the era and place. Keep the same setting for neighbouring scenes unless the story moves. Use 0 to 2 props per scene.`;
}

async function geminiText(prompt) {
  const key = ['GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_KEY'].map((n) => process.env[n]).find(Boolean);
  if (!key) throw new Error('No Gemini key found. Put GEMINI_API_KEY=... in .env, or use --mock-story to test without one.');
  const models = [process.env.GEMINI_TEXT_MODEL, 'gemini-3.8-flash', 'gemini-2.5-flash', 'gemini-2.0-flash'].filter(Boolean);
  let lastErr;
  for (const model of models) {
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': key },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { responseMimeType: 'application/json', temperature: 0.8 } }),
      });
      if (res.status === 404) { lastErr = new Error(`Model ${model} not found`); break; } // try the next model name
      if (res.status === 429 || res.status >= 500) {
        lastErr = new Error(`Gemini ${res.status}`);
        await new Promise((r) => setTimeout(r, 5000 * attempt));
        continue;
      }
      if (!res.ok) throw new Error(`Gemini text error ${res.status}: ${(await res.text()).slice(0, 300)}`);
      const j = await res.json();
      const text = j.candidates && j.candidates[0] && j.candidates[0].content.parts.map((p) => p.text || '').join('');
      if (!text) { lastErr = new Error('Gemini returned no text'); continue; }
      return text;
    }
  }
  throw lastErr || new Error('Gemini text request failed');
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
      setting, stage: { props, actors },
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
  if (opts.mock) return normalize(mockStory(topic), topic);
  const o = { minWords: 300, maxWords: 400, minScenes: 14, maxScenes: 17, ...opts };
  let fix = opts.fix || '';
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const story = normalize(parseJson(await geminiText(buildPrompt(topic, opts.avoid || [], { ...o, fix }))), topic);
    const est = estimate(story);
    if (est >= 100 && est <= 165) return story;
    fix = `The last version would run about ${Math.round(est)} seconds. It must be between 115 and 150 seconds: ${est < 100 ? 'add scenes or lengthen narration' : 'cut scenes or shorten narration'}.`;
    if (attempt === 3) return story; // make.js measures the real length and the caller decides
  }
}

module.exports = { writeStory, estimate, normalize, mockStory, SETTINGS };
