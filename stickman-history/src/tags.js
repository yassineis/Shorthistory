'use strict';
// Tags and hashtags for the upload, chosen from vidIQ keyword research (2026-11-25).
// Story-specific tags (people, places, objects) written by the story writer come first, then these proven search phrases.
// Search volume (vidIQ monthly estimate) is in the comments; all have moderate competition (49-58 out of 100).

const BASE = [
  'animated history',    // ~1.56M searches
  'history explained',  // ~782K
  'weird history',      // ~474K
  'history facts',      // ~337K
  'world history',      // ~376K
  'history shorts',     // ~384K, demand +67%
];
const ANCIENT = ['ancient history', 'roman empire'];       // ~1.04M / ~325K, added only for ancient and Roman stories
const WAR = ['military history'];                           // ~246K
const WORDS_ANCIENT = /\b(ancient|egypt|pyramid|roman|rome|greek|greece|babylon|pharaoh|sphinx|alexandria|pompeii|mesopotamia|olmec|mitanni)/i;
const WORDS_WAR = /\b(war|battle|army|soldier|siege|invasion|napoleon|hannibal|thermopylae|pearl harbor|nuremberg)/i;

function finalTags(story, maxChars = 450) { // YouTube allows 500 characters in total
  const text = `${story.title || ''} ${story.description || ''}`;
  const extra = [...BASE];
  if (WORDS_ANCIENT.test(text)) extra.unshift(...ANCIENT);
  if (WORDS_WAR.test(text)) extra.push(...WAR);
  const seen = new Set();
  const out = [];
  let len = 0;
  for (const raw of [...(story.tags || []), ...extra]) {
    const t = String(raw).replace(/^#/, '').trim();
    const k = t.toLowerCase();
    if (!t || seen.has(k)) continue;
    if (len + t.length + 2 > maxChars) break;
    seen.add(k); out.push(t); len += t.length + 2;
  }
  return out;
}

// Hashtags for the end of the description. #Shorts helps YouTube treat it as a Short; the first three show above the title.
function hashtags(story) {
  const text = `${story.title || ''} ${story.description || ''}`;
  return ['#Shorts', '#History', WORDS_ANCIENT.test(text) ? '#AncientHistory' : '#HistoryFacts', '#AnimatedHistory'].join(' ');
}

module.exports = { finalTags, hashtags, BASE };
