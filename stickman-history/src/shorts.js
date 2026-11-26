#!/usr/bin/env node
'use strict';
// Makes finished history Shorts, one after another.
//   1. asks how many videos (1-10)
//   2. picks topics from library/topics.json that are not made yet (top-scored first)
//   3. for each: writes the story with Gemini (saved in library/stories/), voices it, renders it
//   4. records every story in library/index.json so a story is never made twice
// Each video (subscribe line included) should come out around 1:10 to 1:30. The story is sized to that; nothing is refused
// afterwards: if the real voice makes it a bit shorter or longer, the video is kept and a note is added to the summary.

const fs = require('fs');
const path = require('path');
const { finalTags, hashtags } = require('./tags');
const readline = require('readline');
const { spawnSync } = require('child_process');
const { loadEnv } = require('./voice');
const { writeStory, estimate } = require('./story');

const ROOT = path.join(__dirname, '..');
const LIB = path.join(ROOT, 'library');
const NOTE_BELOW = 60, NOTE_ABOVE = 92, MAX_VIDEOS = 10; // seconds: outside this, the summary adds a length note
const BOOL = new Set(['dry-voice', 'mock-story', 'no-music', 'yes', 'random', 'list', 'redo', 'force', 'help']);

function parseArgs(argv) {
  const o = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (!argv[i].startsWith('--')) continue;
    const k = argv[i].slice(2);
    o[k] = BOOL.has(k) ? true : argv[++i];
  }
  return o;
}

const readJson = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { return d; } };
const saveJson = (f, v) => { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, JSON.stringify(v, null, 1)); };
const slugify = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50) || 'story';
const normTitle = (s) => s.toLowerCase().replace(/\(mock\)/g, '').replace(/[^a-z0-9]+/g, ' ').trim();

function help() {
  console.log(`Usage: node src/shorts.js [options]

It asks how many videos to make (1-10), then makes them. Videos are about 1:10 to 1:30 long (subscribe line included).

  --count N        skip the question and make N videos (max ${MAX_VIDEOS})
  --topic "text"   make a video about your own topic (repeatable use: run again for more)
  --random         pick unused library topics at random instead of top score first
  --yes            do not ask for confirmation
  --list           show the library: topics made and topics left
  --redo           show the stories already made and remake the one you pick (same story, new render, no Gemini)
  --mock-story     placeholder story, no Gemini (to test the pipeline)
  --voice kokoro|gemini  default kokoro: free offline voice, no key, no limits
  --dry-voice      placeholder voice (to test the pipeline)
  --style sb|a5     sb = storybook look, vertical 9:16 (default);  a5 = old stick figures, 16:9
  --aspect 16:9|9:16 (a5 only);  --height;  --pause 4000;  --no-music;  --env file`);
}

function ask(rl, q) { return new Promise((res) => rl.question(q, (a) => res(a.trim()))); }

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) return help();
  loadEnv(args.env || path.join(ROOT, '.env'));

  const topicsFile = path.join(LIB, 'topics.json');
  const indexFile = path.join(LIB, 'index.json');
  const lib = readJson(topicsFile, { topics: [] });
  const index = readJson(indexFile, { version: 1, stories: [] });
  const done = new Set(index.stories.filter((s) => s.status !== 'failed' && s.status !== 'scripted').map((s) => s.topic_id));
  const unfinished = index.stories.filter((s) => s.status === 'scripted' || s.status === 'failed');
  const left = lib.topics.filter((t) => !done.has(t.id) && !unfinished.some((u) => u.topic_id === t.id));

  if (args.list) {
    console.log(`Library: ${lib.topics.length} topics, ${index.stories.length} stories recorded, ${left.length} topics left.`);
    for (const s of index.stories) console.log(`  [${s.status}] ${s.title}${s.duration ? ` (${s.duration}s)` : ''}`);
    return;
  }

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  let queue = [];
  if (args.redo) {
    const made = index.stories.filter((s) => s.status !== 'sample' && fs.existsSync(path.join(LIB, 'stories', `${s.id}.json`)));
    if (!made.length) { rl.close(); return console.log('No story has been made yet. Use option 1 first.'); }
    console.log('\nStories already made:');
    made.forEach((s, i) => console.log(`  ${i + 1}. ${s.title}  [${s.status}${s.duration ? `, ${s.duration}s` : ''}]${s.video ? `  ${s.video}` : ''}`));
    const a = (await ask(rl, '\nWhich one do you want to remake? Type a number, or "all" (just Enter = cancel): ')).toLowerCase();
    let picks = [];
    if (a === 'all') picks = made;
    else if (/^\d+$/.test(a) && +a >= 1 && +a <= made.length) picks = [made[+a - 1]];
    if (!picks.length) { rl.close(); return console.log('Cancelled. Nothing was changed.'); }
    queue = picks.map((u) => ({ resume: u, redo: true }));
    args.yes = true;
  } else {
    let n = parseInt(args.count, 10);
    while (!(n >= 1 && n <= MAX_VIDEOS)) {
      n = parseInt(await ask(rl, `How many videos do you want to make? (1-${MAX_VIDEOS}): `), 10);
      if (!(n >= 1 && n <= MAX_VIDEOS)) console.log(`Please type a number from 1 to ${MAX_VIDEOS}.`);
    }
    // queue: unfinished stories first, then a custom topic, then library topics
    queue = unfinished.slice(0, n).map((u) => ({ resume: u }));
    if (args.topic && queue.length < n) queue.push({ topic: { id: slugify(args.topic), title: args.topic, angle: '', setting: 'medieval_town', source: 'custom' } });
    const pool = args.random ? [...left].sort(() => Math.random() - 0.5) : [...left].sort((a, b) => b.score - a.score);
    while (queue.length < n && pool.length) queue.push({ topic: pool.shift() });
    if (queue.length < n) console.log(`Only ${queue.length} topics are left in the library. Add more with vidIQ later, or use --topic.`);
  }
  if (!queue.length) { rl.close(); return console.log('Nothing to make.'); }

  console.log('\nWill make:');
  queue.forEach((q, i) => console.log(`  ${i + 1}. ${q.resume ? `${q.resume.title} (continue)` : q.topic.title}`));
  if (!args.yes) {
    const a = (await ask(rl, '\nStart? (y/n): ')).toLowerCase();
    if (a !== 'y' && a !== 'yes') { rl.close(); return console.log('Cancelled. Nothing was made.'); }
  }
  rl.close();

  // title for the "Up next" end card: the next video in this run, otherwise the best library topic not made yet
  const nextTitle = (i) => {
    const q = queue[i + 1];
    if (q) return q.resume ? q.resume.title : q.topic.title;
    const taken = new Set(queue.map((x) => (x.resume ? x.resume.topic_id : x.topic.id)));
    const t = [...left].filter((x) => !taken.has(x.id)).sort((a, b) => b.score - a.score)[0];
    return t ? t.title : '';
  };

  const results = [];
  for (let i = 0; i < queue.length; i += 1) {
    const q = queue[i];
    const label = q.resume ? q.resume.title : q.topic.title;
    console.log(`\n=== Video ${i + 1} of ${queue.length}: ${label} ===`);
    let entry = q.resume;
    try {
      if (!entry) {
        const avoid = index.stories.map((s) => s.title);
        console.log('  writing the story...');
        const story = await writeStory(q.topic, { mock: args['mock-story'], avoid, envFile: args.env || path.join(ROOT, '.env') });
        if (index.stories.some((s) => normTitle(s.title) === normTitle(story.title))) throw new Error(`A story titled "${story.title}" already exists in the library.`);
        let slug = slugify(q.topic.id), k = 2;
        while (index.stories.some((s) => s.id === slug)) slug = `${slugify(q.topic.id)}-${k++}`;
        story.topic_id = q.topic.id; story.library_id = slug; story.created = new Date().toISOString().slice(0, 10);
        saveJson(path.join(LIB, 'stories', `${slug}.json`), story);
        entry = { id: slug, topic_id: q.topic.id, title: story.title, status: 'scripted', created: story.created, est_seconds: Math.round(estimate(story)) };
        index.stories.push(entry);
        saveJson(indexFile, index);
        console.log(`  saved: library/stories/${slug}.json  (${story.scenes.length} scenes, about ${entry.est_seconds}s)`);
      }

      const scriptPath = path.join(LIB, 'stories', `${entry.id}.json`);
      const outDir = path.join('out', 'shorts', entry.id);
      let ok = false;
      for (let attempt = 1; attempt <= 3 && !ok; attempt += 1) {
        const margs = [path.join(__dirname, 'make.js'), scriptPath, '--out', outDir, '--style', args.style || 'sb'];
        for (const k of ['aspect', 'height', 'pause', 'env', 'voice']) if (args[k]) margs.push(`--${k}`, args[k]);
        const nextT = nextTitle(i);
        if (nextT) margs.push('--next', nextT);
        for (const k of ['dry-voice', 'no-music']) if (args[k]) margs.push(`--${k}`);
        if (q.redo || args.force) margs.push('--force');
        const r = spawnSync(process.execPath, margs, { stdio: ['inherit', 'inherit', 'pipe'], encoding: 'utf8' });
        if (r.stderr) process.stderr.write(r.stderr);
        if (r.status === 0) { ok = true; break; }
        throw new Error('make.js failed (see above).');
      }
      const final = path.join(outDir, 'final.mp4');
      const { probeDuration } = require('./voice');
      entry.duration = Math.round(await probeDuration(final));
      entry.status = 'rendered';
      entry.video = final.replace(/\\/g, '/');
      saveJson(indexFile, index);
      const story = readJson(scriptPath);
      fs.writeFileSync(path.join(outDir, 'info.txt'),
        `TITLE\n${story.title}\n\nDESCRIPTION\n${story.description}\n\n${hashtags(story)}\n\nTAGS\n${finalTags(story).join(', ')}\n\nCHECK THESE FACTS BEFORE PUBLISHING\n${(story.facts_to_check || []).map((f) => `- ${f}`).join('\n')}\n`);
      const lenNote = entry.duration > NOTE_ABOVE ? '  (note: longer than 1:30)' : entry.duration < NOTE_BELOW ? '  (note: shorter than 1:00)' : '';
      results.push(`OK   ${entry.title} - ${entry.duration}s - ${final}${lenNote}`);
    } catch (e) {
      console.error(`  failed: ${e.message}`);
      if (entry) { entry.status = 'failed'; saveJson(indexFile, index); }
      results.push(`FAIL ${label}: ${e.message}`);
    }
  }
  console.log('\n===== Summary =====');
  results.forEach((r) => console.log(r));
  if (!results.some((r) => r.startsWith('OK'))) process.exitCode = 1;
  console.log('\nFailed or unfinished stories are kept in the library and are finished first next time you run this.');
}

main().catch((e) => { console.error('\nError: ' + e.message); process.exit(1); });
