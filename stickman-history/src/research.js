#!/usr/bin/env node
'use strict';
// Free topic and title research with Agent-Reach (https://github.com/Panniantong/Agent-Reach, MIT, no API key for YouTube search).
//   node src/research.js "mona lisa"              search YouTube, list the titles that exist for that topic
//   node src/research.js --channels               show what Agent-Reach can do on this PC (its own list of commands)
//   node src/research.js "mona lisa" --channel youtube --action search     (these two are the defaults)
// Results are saved in library/research/<topic>.json. Nothing is added to the topic library automatically:
// read the list, then add the topics you like to library/topics.json (or use menu option 1 with --topic "...").
// Agent-Reach is optional. Without it this tool only prints how to install it (free). Read-only: it never posts anything.

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { spawnSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'library', 'research');
const slugify = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50) || 'search';

function parse(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--channels' || argv[i] === '--help' || argv[i] === '--raw') o[argv[i].slice(2)] = true;
    else if (argv[i].startsWith('--')) o[argv[i].slice(2)] = argv[++i];
    else o._.push(argv[i]);
  }
  return o;
}

function reach(args) {
  // no shell: the topic text is passed as one safe argument (also avoids Node's DEP0190 warning on Windows)
  let r = spawnSync('agent-reach', args, { encoding: 'utf8', timeout: 120000 });
  if (r.error && r.error.code === 'ENOENT' && process.platform === 'win32') { // .cmd / .bat launchers need cmd.exe
    r = spawnSync('cmd', ['/d', '/s', '/c', 'agent-reach', ...args], { encoding: 'utf8', timeout: 120000 });
    if (r.status === 1 && /not recognized/i.test(r.stderr || '')) r = { error: { code: 'ENOENT' } };
  }
  return { missing: !!(r.error && r.error.code === 'ENOENT'), status: r.status, out: (r.stdout || '').trim(), err: (r.stderr || '').trim(), error: r.error };
}

const INSTALL = `Agent-Reach is not installed on this PC (it is free, MIT licence, no key needed for YouTube search).
Install it once, in PowerShell:
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  uv tool install https://github.com/Panniantong/Agent-Reach/releases/latest/download/agent-reach.zip
  agent-reach setup
(Do NOT install "agent-reach" from PyPI: that is a different project. If the command is not found afterwards, run "uv tool update-shell" and open a new window.)
Then run this tool again.`;

// Agent-Reach prints JSON ({ok, result, error}); this walks any shape and collects things that look like videos or pages.
function collect(node, acc = []) {
  if (Array.isArray(node)) node.forEach((n) => collect(n, acc));
  else if (node && typeof node === 'object') {
    if (typeof node.title === 'string' && node.title.trim()) {
      acc.push({
        title: node.title.trim(),
        channel: node.channel || node.uploader || node.author || node.owner || '',
        views: Number(node.view_count ?? node.views ?? node.viewCount ?? 0) || 0,
        url: node.url || node.link || node.webpage_url || (node.id ? `https://www.youtube.com/watch?v=${node.id}` : ''),
      });
    }
    Object.values(node).forEach((v) => { if (v && typeof v === 'object') collect(v, acc); });
  }
  return acc;
}

async function main() {
  const o = parse(process.argv.slice(2));
  if (o.help) {
    return console.log('Usage: node src/research.js "topic" [--channel youtube] [--action search] [--raw]\n       node src/research.js --channels');
  }
  const probe = reach(['channels']);
  if (probe.missing) return console.log('\n' + INSTALL);
  if (o.channels) return console.log(probe.out || probe.err || '(no output from agent-reach channels)');

  let q = o._.join(' ').trim();
  if (!q) {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    q = await new Promise((res) => rl.question('Topic or title idea to research on YouTube (Enter = cancel): ', (a) => { rl.close(); res(a.trim()); }));
  }
  if (!q) return console.log('Cancelled.');
  const channel = o.channel || 'youtube', action = o.action || 'search';
  console.log(`\nAsking Agent-Reach: ${channel} ${action} "${q}" ...`);
  const r = reach([channel, action, q]);
  if (r.status !== 0 && !r.out) {
    console.log(`Agent-Reach did not answer: ${r.err || (r.error && r.error.message) || 'unknown error'}`);
    console.log('Run "node src/research.js --channels" to see the exact commands your version supports, then use --channel / --action.');
    return;
  }
  let data;
  try { data = JSON.parse(r.out); } catch (e) { data = null; }
  if (data && data.ok === false) {
    console.log(`Agent-Reach reported a problem: ${JSON.stringify(data.error || data)}`);
    return;
  }
  const seen = new Set();
  const items = data ? collect(data.result !== undefined ? data.result : data).filter((x) => !seen.has(x.title) && seen.add(x.title)) : [];
  items.sort((a, b) => b.views - a.views);
  fs.mkdirSync(OUT, { recursive: true });
  const file = path.join(OUT, `${slugify(q)}.json`);
  fs.writeFileSync(file, JSON.stringify({ query: q, channel, action, date: new Date().toISOString().slice(0, 10), titles: items, raw: data || r.out }, null, 1));
  if (o.raw || !items.length) console.log(r.out.slice(0, 3000));
  if (items.length) {
    console.log(`\n${items.length} titles found (most viewed first):`);
    items.slice(0, 25).forEach((x, i) => console.log(`${String(i + 1).padStart(2)}. ${x.title}${x.views ? `  [${x.views.toLocaleString('en-US')} views]` : ''}${x.channel ? `  - ${x.channel}` : ''}`));
    console.log('\nLook for: a specific person or object doing something odd, a real number, a question. Titles with many views on small channels are the best signs.');
  } else {
    console.log('\nNo titles could be read from the answer (the raw answer is shown above and saved).');
  }
  console.log(`Saved: ${path.relative(ROOT, file)}`);
}

main().catch((e) => { console.error('\nError: ' + e.message); process.exit(1); });
