#!/usr/bin/env node
'use strict';
// Publishes a finished Short to YouTube, Facebook (Page reel), Instagram (reel) and TikTok.
// Free: it only uses each platform's official API. Written from the platforms' public documentation, no third-party code.
//
//   node src/publish.js                                  menu: pick a video, pick the platforms
//   node src/publish.js setup                            what is configured, and what is still missing
//   node src/publish.js auth youtube                     sign in to Google once (opens a link)
//   node src/publish.js auth tiktok                      sign in to TikTok once (needs PUBLIC_BASE_URL, see README)
//   node src/publish.js facebook-token <USER_TOKEN>      turn a Facebook user token into a Page token (+ Instagram id)
//   node src/publish.js post <story-id|folder> --to youtube,facebook,instagram,tiktok [--privacy public|unlisted|private]
//                                                        [--public https://xxx.trycloudflare.com] [--dry-run] [--yes] [--again]
//
// Title, description, hashtags and tags come from the info.txt written next to every video.
// Secrets live in .env and publish/tokens.json (both git-ignored). Nothing is ever posted without a confirmation (use --yes to skip it).

const fs = require('fs');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');
const readline = require('readline');
const crypto = require('crypto');
const { loadEnv, probeDuration } = require('./voice');

const ROOT = path.join(__dirname, '..');
const DIR = path.join(ROOT, 'publish');
const TOKENS = path.join(DIR, 'tokens.json');
const LOG = path.join(DIR, 'log.json');
const PORT = Number(process.env.PUBLISH_PORT || 8787);
const PLATFORMS = ['youtube', 'facebook', 'instagram', 'tiktok'];
const ALIAS = { yt: 'youtube', fb: 'facebook', ig: 'instagram', tt: 'tiktok', tiktok: 'tiktok' };

const readJson = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { return d; } };
const saveJson = (f, v) => { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, JSON.stringify(v, null, 2)); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => Math.floor(Date.now() / 1000);

// API hosts. PUBLISH_API_BASE is only used by the offline test (a fake server), never in normal use.
const B = process.env.PUBLISH_API_BASE;
const API = {
  gAuth: 'https://accounts.google.com/o/oauth2/v2/auth',
  gToken: B ? `${B}/google/token` : 'https://oauth2.googleapis.com/token',
  yt: B ? `${B}/yt` : 'https://www.googleapis.com',
  graph: B ? `${B}/graph` : 'https://graph.facebook.com',
  ttAuth: 'https://www.tiktok.com/v2/auth/authorize/',
  tt: B ? `${B}/tiktok/v2` : 'https://open.tiktokapis.com/v2',
};
const GRAPH = () => `${API.graph}/${process.env.META_GRAPH_VERSION || 'v23.0'}`;

function parseArgs(argv) {
  const o = { _: [] };
  const BOOL = new Set(['dry-run', 'yes', 'again', 'help']);
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) { const k = argv[i].slice(2); o[k] = BOOL.has(k) ? true : argv[++i]; } else o._.push(argv[i]);
  }
  return o;
}
const tokens = () => readJson(TOKENS, {});
const saveTokens = (t) => { saveJson(TOKENS, t); try { fs.chmodSync(TOKENS, 0o600); } catch (e) { /* windows */ } };

function ask(q) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((res) => rl.question(q, (a) => { rl.close(); res(a.trim()); }));
}

async function http_(url, opts = {}) {
  const r = await fetch(url, opts);
  const text = await r.text();
  let json = null;
  try { json = JSON.parse(text); } catch (e) { /* not json */ }
  return { ok: r.ok, status: r.status, headers: r.headers, text, json };
}
const fail = (what, r) => new Error(`${what}: ${r.status} ${r.text.slice(0, 400)}`);

// ---------- what to post (read from the video folder) ----------
function sections(text) {
  const out = {};
  let key = null;
  for (const line of text.split(/\r?\n/)) {
    if (/^(TITLE|DESCRIPTION|TAGS|LENGTH NOTE|CHECK THESE FACTS BEFORE PUBLISHING|DRAMATISED.*)$/.test(line)) { key = line.split(' ')[0] === 'DRAMATISED' ? 'DRAMATISED' : line; out[key] = []; } else if (key) out[key].push(line);
  }
  const get = (k) => (out[k] || []).join('\n').trim();
  return { title: get('TITLE'), description: get('DESCRIPTION'), tags: get('TAGS').split(',').map((s) => s.trim()).filter(Boolean), facts: get('CHECK THESE FACTS BEFORE PUBLISHING'), dramatised: get('DRAMATISED') };
}

async function loadVideo(ref) {
  let dir = ref;
  if (!fs.existsSync(path.join(dir, 'final.mp4'))) dir = path.join(ROOT, 'out', 'shorts', ref);
  const file = path.join(dir, 'final.mp4');
  if (!fs.existsSync(file)) throw new Error(`No final.mp4 found for "${ref}" (looked in ${dir}).`);
  const infoFile = path.join(dir, 'info.txt');
  if (!fs.existsSync(infoFile)) throw new Error(`No info.txt next to the video (${infoFile}).`);
  const info = sections(fs.readFileSync(infoFile, 'utf8'));
  const seconds = await probeDuration(file);
  const hashtags = (info.description.match(/#[\p{L}\p{N}_]+/gu) || []);
  return { id: path.basename(dir), dir, file, size: fs.statSync(file).size, seconds, ...info, hashtags };
}

// ---------- tiny local web server: sign-in callbacks, and the video link for Instagram ----------
function startServer({ videoFile, onCode }) {
  const srv = http.createServer((req, res) => {
    const u = new URL(req.url, `http://127.0.0.1:${PORT}`);
    if (u.pathname.startsWith('/callback/')) {
      const err = u.searchParams.get('error');
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(err ? `<h2>Sign-in failed: ${err}</h2>` : '<h2>Signed in. You can close this tab and go back to the terminal.</h2>');
      if (onCode) onCode(u.pathname.split('/')[2], u.searchParams.get('code'), err, u.searchParams.get('state'));
      return;
    }
    if (videoFile && u.pathname === '/video.mp4') {
      const size = fs.statSync(videoFile).size;
      const range = /bytes=(\d*)-(\d*)/.exec(req.headers.range || '');
      if (range) {
        const start = range[1] ? Number(range[1]) : 0;
        const end = range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
        res.writeHead(206, { 'Content-Type': 'video/mp4', 'Accept-Ranges': 'bytes', 'Content-Range': `bytes ${start}-${end}/${size}`, 'Content-Length': end - start + 1 });
        return fs.createReadStream(videoFile, { start, end }).pipe(res);
      }
      res.writeHead(200, { 'Content-Type': 'video/mp4', 'Accept-Ranges': 'bytes', 'Content-Length': size });
      return fs.createReadStream(videoFile).pipe(res);
    }
    res.writeHead(404); res.end('not found');
  });
  return new Promise((resolve, reject) => { srv.on('error', reject); srv.listen(PORT, '127.0.0.1', () => resolve(srv)); });
}

// A free Cloudflare "quick tunnel" gives the local video server a public https address, which Instagram needs to download the video.
// Started and stopped automatically, so nothing has to be copied by hand. Needs cloudflared (winget install Cloudflare.cloudflared).
function startTunnel() {
  const candidates = [process.env.CLOUDFLARED_BIN, 'cloudflared', 'C:\\Program Files (x86)\\cloudflared\\cloudflared.exe', 'C:\\Program Files\\cloudflared\\cloudflared.exe'].filter(Boolean);
  return new Promise((resolve, reject) => {
    const tryNext = (i) => {
      if (i >= candidates.length) return reject(new Error('cloudflared is not installed. Install it once (free): winget install Cloudflare.cloudflared, then open a new window. Or pass --public https://... yourself.'));
      let child;
      try { child = spawn(candidates[i], ['tunnel', '--no-autoupdate', '--url', `http://127.0.0.1:${PORT}`], { windowsHide: true }); } catch (e) { return tryNext(i + 1); }
      let done = false, log = '';
      const stop = () => { try { child.kill(); } catch (e) { /* already gone */ } };
      const timer = setTimeout(() => { if (!done) { done = true; stop(); reject(new Error(`cloudflared gave no address after 40 seconds.\n${log.slice(-400)}`)); } }, 40000);
      child.on('error', (e) => { if (done) return; done = true; clearTimeout(timer); if (e.code === 'ENOENT') tryNext(i + 1); else reject(e); });
      const onData = (d) => {
        log += d.toString();
        const m = /https:\/\/[a-z0-9-]+\.trycloudflare\.com|http:\/\/127\.0\.0\.1:\d+/.exec(log);
        if (m && !done) { done = true; clearTimeout(timer); resolve({ url: m[0], stop }); }
      };
      child.stdout.on('data', onData); child.stderr.on('data', onData);
      child.on('exit', () => { if (!done) { done = true; clearTimeout(timer); reject(new Error(`cloudflared stopped: ${log.slice(-400)}`)); } });
    };
    tryNext(0);
  });
}

// quick tunnels can take a few seconds before the new address answers
async function waitReachable(base, tries = 20) {
  for (let i = 0; i < tries; i += 1) {
    try { const r = await fetch(`${base}/video.mp4`, { headers: { Range: 'bytes=0-0' } }); if (r.ok) return true; } catch (e) { /* not yet */ }
    await sleep(Number(process.env.PUBLISH_POLL_MS || 2000));
  }
  return false;
}

async function waitForCode(provider, state, timeoutMs = 300000) {
  let timer, srv;
  const got = new Promise((resolve, reject) => {
    startServer({ onCode: (p, code, err, st) => {
      if (p !== provider) return;
      if (err || !code) reject(new Error(`Sign-in failed: ${err || 'no code'}`));
      else if (st !== state) reject(new Error('Sign-in answer did not match (state). Try again.'));
      else resolve(code);
    } }).then((s2) => { srv = s2; }, reject);
    timer = setTimeout(() => reject(new Error('Timed out waiting for sign-in (5 minutes).')), timeoutMs);
  });
  try { return await got; } finally { clearTimeout(timer); if (srv) srv.close(); }
}

// ---------- sign-in ----------
async function authYoutube() {
  const id = process.env.GOOGLE_CLIENT_ID, secret = process.env.GOOGLE_CLIENT_SECRET;
  if (!id || !secret) throw new Error('Put GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env first (see README, "Publishing").');
  const redirect = `http://127.0.0.1:${PORT}/callback/youtube`;
  const state = crypto.randomBytes(12).toString('hex');
  const url = `${API.gAuth}?${new URLSearchParams({ client_id: id, redirect_uri: redirect, response_type: 'code', scope: 'https://www.googleapis.com/auth/youtube.upload', access_type: 'offline', prompt: 'consent', state })}`;
  console.log(`\nOpen this link in your browser and allow the app:\n\n${url}\n`);
  const code = await waitForCode('youtube', state);
  const r = await http_(API.gToken, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ client_id: id, client_secret: secret, code, grant_type: 'authorization_code', redirect_uri: redirect }) });
  if (!r.ok || !r.json.refresh_token) throw fail('Google did not give a refresh token', r);
  const t = tokens();
  t.youtube = { access_token: r.json.access_token, expires_at: now() + r.json.expires_in, refresh_token: r.json.refresh_token };
  saveTokens(t);
  console.log('YouTube is connected.');
  console.log('Note: while the Google app is in "Testing", Google expires the sign-in after 7 days. Set the app to "In production" (Google Auth Platform > Audience) to keep it.');
}

async function authTiktok(args) {
  const key = process.env.TIKTOK_CLIENT_KEY, secret = process.env.TIKTOK_CLIENT_SECRET;
  const base = (args.public || process.env.PUBLIC_BASE_URL || '').replace(/\/$/, '');
  if (!key || !secret) throw new Error('Put TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in .env first (see README, "Publishing").');
  if (!base.startsWith('https://')) throw new Error(`TikTok only accepts an https redirect. Start a free tunnel (cloudflared tunnel --url http://localhost:${PORT}) and run again with --public https://<your-tunnel>.trycloudflare.com`);
  const redirect = `${base}/callback/tiktok`;
  const state = crypto.randomBytes(12).toString('hex');
  const url = `${API.ttAuth}?${new URLSearchParams({ client_key: key, scope: 'user.info.basic,video.publish', response_type: 'code', redirect_uri: redirect, state })}`;
  console.log(`\nThe redirect address ${redirect} must be listed in your TikTok app (Login Kit > Redirect URI).\nOpen this link in your browser and allow the app:\n\n${url}\n`);
  const code = await waitForCode('tiktok', state);
  const r = await http_(`${API.tt}/oauth/token/`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ client_key: key, client_secret: secret, code, grant_type: 'authorization_code', redirect_uri: redirect }) });
  if (!r.ok || !r.json || !r.json.access_token) throw fail('TikTok did not give a token', r);
  const t = tokens();
  t.tiktok = { access_token: r.json.access_token, expires_at: now() + r.json.expires_in, refresh_token: r.json.refresh_token, refresh_expires_at: now() + (r.json.refresh_expires_in || 31536000), open_id: r.json.open_id };
  saveTokens(t);
  console.log('TikTok is connected.');
}

async function facebookToken(args) {
  let user = args._[1];
  if (!user) throw new Error('Usage: node src/publish.js facebook-token <USER_ACCESS_TOKEN>   (get one in the Graph API Explorer, see README)');
  if (process.env.META_APP_ID && process.env.META_APP_SECRET) { // short-lived -> long-lived, so the Page token never expires
    const x = await http_(`${GRAPH()}/oauth/access_token?${new URLSearchParams({ grant_type: 'fb_exchange_token', client_id: process.env.META_APP_ID, client_secret: process.env.META_APP_SECRET, fb_exchange_token: user })}`);
    if (x.ok && x.json.access_token) user = x.json.access_token; else console.log('(could not make a long-lived token, using the one you gave)');
  }
  const r = await http_(`${GRAPH()}/me/accounts?${new URLSearchParams({ fields: 'id,name,access_token,instagram_business_account{id,username}', limit: '100', access_token: user })}`);
  if (!r.ok) throw fail('Facebook refused the token', r);
  const pages = r.json.data || [];
  if (!pages.length) throw new Error('This token manages no Facebook Pages (it needs pages_show_list and pages_manage_posts).');
  let page = pages[0];
  if (pages.length > 1) {
    pages.forEach((p, i) => console.log(`  ${i + 1}. ${p.name}${p.instagram_business_account ? `  (Instagram @${p.instagram_business_account.username})` : ''}`));
    const n = Number(args.page || await ask('Which Page? number: '));
    page = pages[n - 1];
    if (!page) throw new Error('Cancelled.');
  }
  const t = tokens();
  t.facebook = { page_id: page.id, page_name: page.name, page_token: page.access_token };
  if (page.instagram_business_account) t.instagram = { ig_user_id: page.instagram_business_account.id, username: page.instagram_business_account.username, token: page.access_token };
  saveTokens(t);
  console.log(`Saved Page "${page.name}"${page.instagram_business_account ? ` and Instagram @${page.instagram_business_account.username}` : ' (no Instagram account is linked to this Page, so Instagram stays off)'}.`);
}

// ---------- posting ----------
async function youtubeAccess() {
  const t = tokens();
  if (!t.youtube) throw new Error('YouTube is not connected. Run: node src/publish.js auth youtube');
  if (t.youtube.expires_at > now() + 60) return t.youtube.access_token;
  const r = await http_(API.gToken, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ client_id: process.env.GOOGLE_CLIENT_ID, client_secret: process.env.GOOGLE_CLIENT_SECRET, refresh_token: t.youtube.refresh_token, grant_type: 'refresh_token' }) });
  if (!r.ok) throw fail('Google sign-in expired, run "auth youtube" again', r);
  t.youtube.access_token = r.json.access_token; t.youtube.expires_at = now() + r.json.expires_in;
  saveTokens(t);
  return t.youtube.access_token;
}

async function postYoutube(v, o) {
  const access = await youtubeAccess();
  const tags = []; let len = 0;
  for (const tag of v.tags) { if (len + tag.length + 1 > 450) break; tags.push(tag); len += tag.length + 1; }
  let description = v.description;
  if (!/#shorts/i.test(description)) description += '\n\n#Shorts';
  const body = { snippet: { title: v.title.slice(0, 100), description: description.slice(0, 4900), tags, categoryId: '27' }, status: { privacyStatus: o.privacy, selfDeclaredMadeForKids: false } };
  const init = await http_(`${API.yt}/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${access}`, 'Content-Type': 'application/json; charset=UTF-8', 'X-Upload-Content-Length': String(v.size), 'X-Upload-Content-Type': 'video/mp4' },
    body: JSON.stringify(body),
  });
  if (!init.ok) throw fail('YouTube refused the upload request', init);
  const loc = init.headers.get('location');
  if (!loc) throw new Error('YouTube gave no upload address.');
  const up = await http_(loc, { method: 'PUT', headers: { 'Content-Type': 'video/mp4', 'Content-Length': String(v.size) }, body: fs.readFileSync(v.file) });
  if (!up.ok || !up.json || !up.json.id) throw fail('YouTube upload failed', up);
  const got = up.json.status && up.json.status.privacyStatus;
  const locked = got && got !== o.privacy ? ` (YouTube made it ${got}: until Google audits your API project, uploads are locked private. See README)` : '';
  return { url: `https://www.youtube.com/shorts/${up.json.id}`, note: locked };
}

async function postFacebook(v, o) {
  const f = tokens().facebook;
  if (!f) throw new Error('Facebook is not connected. Run: node src/publish.js facebook-token <USER_TOKEN>');
  const caption = v.description.slice(0, 2000);
  const form = (p) => ({ method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ access_token: f.page_token, ...p }) });
  if (v.seconds > 90) { // reels are limited to 90 seconds on Pages: longer videos go up as a normal Page video
    const fd = new FormData();
    fd.append('access_token', f.page_token); fd.append('description', caption); fd.append('title', v.title.slice(0, 100));
    fd.append('source', new Blob([fs.readFileSync(v.file)], { type: 'video/mp4' }), 'video.mp4');
    const r2 = await http_(`${GRAPH()}/${f.page_id}/videos`, { method: 'POST', body: fd });
    if (!r2.ok || !r2.json || !r2.json.id) throw fail('Facebook video upload failed', r2);
    return { url: `https://www.facebook.com/${f.page_id}/videos/${r2.json.id}`, note: ' (posted as a normal Page video: over 90 s is too long for a reel)' };
  }
  const start = await http_(`${GRAPH()}/${f.page_id}/video_reels`, form({ upload_phase: 'start' }));
  if (!start.ok || !start.json || !start.json.video_id) throw fail('Facebook reel start failed', start);
  const up = await http_(start.json.upload_url, { method: 'POST', headers: { Authorization: `OAuth ${f.page_token}`, offset: '0', file_size: String(v.size) }, body: fs.readFileSync(v.file) });
  if (!up.ok) throw fail('Facebook reel upload failed', up);
  const fin = await http_(`${GRAPH()}/${f.page_id}/video_reels`, form({ upload_phase: 'finish', video_id: start.json.video_id, video_state: o.privacy === 'public' ? 'PUBLISHED' : 'DRAFT', description: caption, title: v.title.slice(0, 100) }));
  if (!fin.ok) throw fail('Facebook reel publish failed', fin);
  return { url: `https://www.facebook.com/reel/${start.json.video_id}`, note: o.privacy === 'public' ? '' : ' (saved as a draft on the Page)' };
}

async function postInstagram(v, o, publicBase) {
  const ig = tokens().instagram;
  if (!ig) throw new Error('Instagram is not connected (it needs a Business/Creator account linked to your Facebook Page). Run: node src/publish.js facebook-token <USER_TOKEN>');
  if (!publicBase) throw new Error('Instagram downloads the video from a public https link, and no tunnel address is available (install cloudflared, or pass --public https://...).');
  const caption = v.description.slice(0, 2200);
  const post = (p, params) => http_(`${GRAPH()}/${p}`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ access_token: ig.token, ...params }) });
  const c = await post(`${ig.ig_user_id}/media`, { media_type: 'REELS', video_url: `${publicBase}/video.mp4`, caption, share_to_feed: 'true' });
  if (!c.ok || !c.json || !c.json.id) throw fail('Instagram refused the video', c);
  let status = '';
  for (let i = 0; i < 60; i += 1) {
    const s = await http_(`${GRAPH()}/${c.json.id}?${new URLSearchParams({ fields: 'status_code,status', access_token: ig.token })}`);
    status = s.json && s.json.status_code;
    if (status === 'FINISHED') break;
    if (status === 'ERROR' || status === 'EXPIRED') throw new Error(`Instagram could not process the video: ${s.json.status || status}`);
    await sleep(Number(process.env.PUBLISH_POLL_MS || 5000));
  }
  if (status !== 'FINISHED') throw new Error('Instagram is still processing after 5 minutes. Check the account before posting again.');
  const p = await post(`${ig.ig_user_id}/media_publish`, { creation_id: c.json.id });
  if (!p.ok || !p.json || !p.json.id) throw fail('Instagram publish failed', p);
  const link = await http_(`${GRAPH()}/${p.json.id}?${new URLSearchParams({ fields: 'permalink', access_token: ig.token })}`);
  return { url: (link.json && link.json.permalink) || `https://www.instagram.com/${ig.username}/`, note: '' };
}

async function tiktokAccess() {
  const t = tokens();
  if (!t.tiktok) throw new Error('TikTok is not connected. Run: node src/publish.js auth tiktok');
  if (t.tiktok.expires_at > now() + 60) return t.tiktok.access_token;
  const r = await http_(`${API.tt}/oauth/token/`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ client_key: process.env.TIKTOK_CLIENT_KEY, client_secret: process.env.TIKTOK_CLIENT_SECRET, grant_type: 'refresh_token', refresh_token: t.tiktok.refresh_token }) });
  if (!r.ok || !r.json || !r.json.access_token) throw fail('TikTok sign-in expired, run "auth tiktok" again', r);
  t.tiktok = { ...t.tiktok, access_token: r.json.access_token, expires_at: now() + r.json.expires_in, refresh_token: r.json.refresh_token || t.tiktok.refresh_token };
  saveTokens(t);
  return t.tiktok.access_token;
}

async function postTiktok(v, o) {
  const access = await tiktokAccess();
  const hdr = { Authorization: `Bearer ${access}`, 'Content-Type': 'application/json; charset=UTF-8' };
  // ask TikTok which audiences this account may use; an app TikTok has not audited can only post "Only me"
  const info = await http_(`${API.tt}/post/publish/creator_info/query/`, { method: 'POST', headers: hdr, body: '{}' });
  const options = (info.json && info.json.data && info.json.data.privacy_level_options) || ['SELF_ONLY'];
  const want = { public: 'PUBLIC_TO_EVERYONE', unlisted: 'MUTUAL_FOLLOW_FRIENDS', private: 'SELF_ONLY' }[o.privacy] || 'SELF_ONLY';
  const privacy = options.includes(want) ? want : (options.includes('SELF_ONLY') ? 'SELF_ONLY' : options[0]);
  const bytes = fs.readFileSync(v.file);
  const MB = 1024 * 1024;
  const chunk = v.size <= 64 * MB ? v.size : 32 * MB; // one piece when it fits, else 32 MB pieces (the last one takes the remainder)
  const count = Math.max(1, Math.floor(v.size / chunk));
  const title = [v.title, v.hashtags.join(' ')].filter(Boolean).join(' ').slice(0, 2000);
  const init = await http_(`${API.tt}/post/publish/video/init/`, { method: 'POST', headers: hdr, body: JSON.stringify({
    post_info: { title, privacy_level: privacy, disable_duet: false, disable_comment: false, disable_stitch: false },
    source_info: { source: 'FILE_UPLOAD', video_size: v.size, chunk_size: chunk, total_chunk_count: count },
  }) });
  if (!init.ok || !init.json || !init.json.data || !init.json.data.upload_url) throw fail('TikTok refused the upload request', init);
  for (let i = 0; i < count; i += 1) {
    const s = i * chunk, e = i === count - 1 ? v.size : s + chunk;
    const up = await http_(init.json.data.upload_url, { method: 'PUT', headers: { 'Content-Type': 'video/mp4', 'Content-Length': String(e - s), 'Content-Range': `bytes ${s}-${e - 1}/${v.size}` }, body: bytes.subarray(s, e) });
    if (!up.ok) throw fail('TikTok upload failed', up);
  }
  for (let i = 0; i < 60; i += 1) {
    await sleep(Number(process.env.PUBLISH_POLL_MS || 5000));
    const st = await http_(`${API.tt}/post/publish/status/fetch/`, { method: 'POST', headers: hdr, body: JSON.stringify({ publish_id: init.json.data.publish_id }) });
    const d = st.json && st.json.data;
    if (d && d.status === 'PUBLISH_COMPLETE') {
      const id = d.publicaly_available_post_id && d.publicaly_available_post_id[0];
      return { url: id ? `https://www.tiktok.com/@/video/${id}` : 'https://www.tiktok.com/ (TikTok is still reviewing it, check your profile)', note: privacy === 'SELF_ONLY' ? ' (private: "Only me". TikTok must audit the app before public posts)' : '' };
    }
    if (d && d.status === 'FAILED') throw new Error(`TikTok failed to publish: ${d.fail_reason || 'unknown reason'}`);
  }
  throw new Error('TikTok is still processing after 5 minutes. Check your profile before posting again.');
}

const POSTERS = { youtube: postYoutube, facebook: postFacebook, tiktok: postTiktok };

function configured() {
  const t = tokens(), e = process.env;
  return {
    youtube: !!t.youtube, facebook: !!t.facebook, instagram: !!t.instagram, tiktok: !!t.tiktok,
    keys: { google: !!(e.GOOGLE_CLIENT_ID && e.GOOGLE_CLIENT_SECRET), tiktok: !!(e.TIKTOK_CLIENT_KEY && e.TIKTOK_CLIENT_SECRET) },
  };
}

async function setup() {
  const c = configured();
  const tick = (b) => (b ? 'connected' : 'NOT connected');
  console.log(`\nPublishing status:\n  YouTube    ${tick(c.youtube)}${c.keys.google ? '' : '   (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET missing in .env)'}\n  Facebook   ${tick(c.facebook)}\n  Instagram  ${tick(c.instagram)}   (comes with the Facebook Page token when the Page has a linked Business/Creator account)\n  TikTok     ${tick(c.tiktok)}${c.keys.tiktok ? '' : '   (TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET missing in .env)'}\n`);
  console.log('Step by step guide: README.md, section "Publishing".');
}

async function post(args) {
  const ref = args._[1];
  if (!ref) throw new Error('Usage: node src/publish.js post <story-id|folder> --to youtube,facebook,instagram,tiktok');
  const v = await loadVideo(ref);
  if (/\(mock\)/i.test(v.title)) throw new Error('This is a test video made with the placeholder story (mock). It will not be posted.');
  const to = (args.to || 'youtube').split(',').map((s) => ALIAS[s.trim().toLowerCase()] || s.trim().toLowerCase()).filter(Boolean);
  for (const p of to) if (!PLATFORMS.includes(p)) throw new Error(`Unknown platform "${p}". Use: ${PLATFORMS.join(', ')}`);
  const privacy = args.privacy || 'public';
  if (!['public', 'unlisted', 'private'].includes(privacy)) throw new Error('--privacy must be public, unlisted or private');
  const publicBase = (args.public || process.env.PUBLIC_BASE_URL || '').replace(/\/$/, '');

  console.log(`\nVideo:     ${v.title}  (${Math.round(v.seconds)} s, ${(v.size / 1048576).toFixed(1)} MB)\nTo:        ${to.join(', ')}   [${privacy}]\nCaption:\n${v.description.split('\n').map((l) => `  ${l}`).join('\n')}`);
  if (v.facts) console.log(`\nCheck these facts first:\n${v.facts.split('\n').map((l) => `  ${l}`).join('\n')}`);
  if (v.dramatised) console.log(`\nInvented for the story (not fact):\n${v.dramatised.split('\n').map((l) => `  ${l}`).join('\n')}`);
  if (args['dry-run']) return console.log('\nDry run: nothing was posted.');
  if (!args.yes) {
    const a = (await ask('\nPost it now? (y/n): ')).toLowerCase();
    if (a !== 'y' && a !== 'yes') return console.log('Cancelled. Nothing was posted.');
  }

  const log = readJson(LOG, []);
  let srv = null, tunnel = null, base = (args.public || '').replace(/\/$/, ''); // Instagram: only an address typed with --public is used as is; otherwise a fresh tunnel is opened
  const results = [];
  try {
    if (to.includes('instagram')) {
      srv = await startServer({ videoFile: v.file });
      if (!base) { // no address given: open a free tunnel just for this post
        process.stdout.write('  opening a free tunnel for Instagram... ');
        try {
          tunnel = await startTunnel();
          base = tunnel.url;
          console.log(await waitReachable(base) ? 'ready' : 'opened (not confirmed reachable yet, trying anyway)');
        } catch (e) { console.log('failed'); results.push(`FAIL instagram: ${e.message}`); to.splice(to.indexOf('instagram'), 1); }
      }
    }
    for (const p of to) {
      if (!args.again && log.some((l) => l.id === v.id && l.platform === p)) { results.push(`SKIP ${p}: already posted (use --again to post a second time)`); continue; }
      process.stdout.write(`  ${p}... `);
      try {
        const r = p === 'instagram' ? await postInstagram(v, { privacy }, base) : await POSTERS[p](v, { privacy });
        console.log('done');
        log.push({ id: v.id, platform: p, url: r.url, date: new Date().toISOString() });
        saveJson(LOG, log);
        results.push(`OK   ${p}: ${r.url}${r.note || ''}`);
      } catch (e) {
        console.log('failed');
        results.push(`FAIL ${p}: ${e.message}`);
      }
    }
  } finally { if (tunnel) tunnel.stop(); if (srv) srv.close(); }
  console.log('\n===== Published =====');
  results.forEach((r) => console.log(r));
  if (results.some((r) => r.startsWith('FAIL'))) process.exitCode = 1;
}

async function menu() {
  const index = readJson(path.join(ROOT, 'library', 'index.json'), { stories: [] });
  const made = index.stories.filter((s) => s.status === 'rendered' && s.video && fs.existsSync(path.join(ROOT, s.video)));
  if (!made.length) return console.log('No rendered video found in out/shorts yet. Make one first (options 1-9, A or W).');
  const log = readJson(LOG, []);
  console.log('\nRendered videos:');
  made.forEach((s, i) => console.log(`  ${i + 1}. ${s.title}  [${s.duration || '?'}s]${log.filter((l) => l.id === s.id).length ? `  (posted to ${log.filter((l) => l.id === s.id).map((l) => l.platform).join(', ')})` : ''}`));
  const n = Number(await ask('\nWhich video? number (Enter = cancel): '));
  if (!(n >= 1 && n <= made.length)) return console.log('Cancelled.');
  const c = configured();
  console.log('\nPlatforms: Y = YouTube, F = Facebook, I = Instagram, T = TikTok  (connected: ' + PLATFORMS.filter((p) => c[p]).join(', ') + ')');
  const pick = (await ask('Letters to post to, for example YF, or ALL: ')).toUpperCase();
  const map = { Y: 'youtube', F: 'facebook', I: 'instagram', T: 'tiktok' };
  const to = pick === 'ALL' ? PLATFORMS.filter((p) => c[p]) : [...pick].map((x) => map[x]).filter(Boolean);
  if (!to.length) return console.log('Cancelled.');
  const priv = (await ask('Visibility: public / unlisted / private (Enter = public): ')).toLowerCase() || 'public';
  await post({ _: ['post', made[n - 1].id], to: to.join(','), privacy: priv });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  loadEnv(path.join(ROOT, '.env'));
  const cmd = args._[0];
  if (args.help || cmd === 'help') return console.log(fs.readFileSync(__filename, 'utf8').split('\n').slice(2, 15).map((l) => l.replace(/^\/\/ ?/, '')).join('\n'));
  if (!cmd) return menu();
  if (cmd === 'setup') return setup();
  if (cmd === 'auth') {
    if (args._[1] === 'youtube') return authYoutube();
    if (args._[1] === 'tiktok') return authTiktok(args);
    throw new Error('Usage: node src/publish.js auth youtube|tiktok   (Facebook and Instagram use: facebook-token <USER_TOKEN>)');
  }
  if (cmd === 'facebook-token') return facebookToken(args);
  if (cmd === 'post') return post(args);
  throw new Error(`Unknown command "${cmd}". Try: node src/publish.js --help`);
}

if (require.main === module) main().catch((e) => { console.error('\nError: ' + e.message); process.exit(1); });
module.exports = { sections, loadVideo, postYoutube, postFacebook, postInstagram, postTiktok };
