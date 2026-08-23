// Headless check for the findings carousel on the landing page.
//
//   node site/tools/carousel_check.js
//
// Two things have gone wrong here before and neither is visible in a build:
//
//   1. The advance interval drifted long enough that a reader who stopped on
//      the section never saw a second card and assumed three was all there is.
//   2. The pause-on-hover zone was bound to the whole #finding band — a
//      full-width section holding the eyebrow, the heading and the note. At
//      that size, *reading* the section meant hovering it, so the deck stopped
//      on arrival and never restarted. It looked broken rather than paused.
//
// Both are timing and event-wiring bugs that a screenshot cannot catch and a
// browser cannot be trusted to measure in a background tab, where timers are
// throttled. So the DOM is stubbed and the clock is fake: deterministic, no
// dependencies, runs in milliseconds.
'use strict';
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'app.js');
const failures = [];
const ok = (cond, msg) => { console.log(`  ${cond ? 'ok  ' : 'FAIL'}  ${msg}`); if (!cond) failures.push(msg); };

// ---- the smallest DOM these four features touch ---------------------------
let intervals = [];          // every setInterval(fn, ms) the script registers
let cleared = 0;

function El(id, cls) {
  const el = {
    id, className: cls || '', tagName: 'DIV', type: '', href: '',
    textContent: '', innerHTML: '', hidden: false, style: {},
    children: [], parentNode: null, _on: {},
    classList: {
      _s: new Set((cls || '').split(' ').filter(Boolean)),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, f) { f ? this._s.add(c) : this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    },
    setAttribute(k, v) { el[k] = v; }, getAttribute(k) { return el[k] ?? null; },
    removeAttribute(k) { delete el[k]; },
    addEventListener(t, fn) { (el._on[t] = el._on[t] || []).push(fn); },
    appendChild(c) { el.children.push(c); c.parentNode = el; return c; },
    querySelectorAll() { return []; }, querySelector() { return null; },
    closest() { return null; },
    // Containment is what the pause zone is decided by, so it has to be real.
    contains(node) {
      if (!node) return false;
      for (let p = node; p; p = p.parentNode) if (p === el) return true;
      return false;
    },
    fire(type, ev) { (el._on[type] || []).forEach((fn) => fn(ev || {})); },
  };
  return el;
}

const deck = El('deck', 'deck');
const deckbar = El('deckbar', 'deckbar');
const finding = El('finding', 'band');          // the whole section
finding.appendChild(deck);
finding.appendChild(deckbar);

const cards = [El(null, 'find'), El(null, 'find'), El(null, 'find')];
cards.forEach((c) => deck.appendChild(c));
deck.querySelectorAll = (sel) => (sel === '.find' ? cards : []);

const dots = El('dots');
const els = { deck, deckbar, finding, dots, prev: El('prev'), next: El('next') };

global.document = {
  getElementById: (id) => els[id] || (els[id] = El(id)),
  createElement: (t) => El(null, ''),
  addEventListener() {}, querySelectorAll: () => [], querySelector: () => null,
  documentElement: El('html'), body: El('body'), readyState: 'complete',
  execCommand() { return true; },
};
global.window = {
  addEventListener() {},
  matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
  localStorage: { getItem: () => null, setItem() {} },
  setInterval: (fn, ms) => { intervals.push({ fn, ms }); return intervals.length; },
  clearInterval: () => { cleared++; intervals = []; },
};
global.localStorage = window.localStorage;
global.matchMedia = window.matchMedia;
// Node 21+ defines navigator as a getter-only global, so it is redefined
// rather than assigned.
Object.defineProperty(global, 'navigator', {
  value: { language: 'en', clipboard: null }, configurable: true, writable: true,
});
global.setInterval = window.setInterval;
global.clearInterval = window.clearInterval;
global.setTimeout = () => 0;
global.IntersectionObserver = function () {
  return { observe() {}, unobserve() {}, disconnect() {} };
};

console.log('carousel:');
new Function(fs.readFileSync(APP, 'utf8'))();

// ---- 1. it advances, and fast enough to be noticed ------------------------
ok(intervals.length === 1, `exactly one timer registered (got ${intervals.length})`);
const ms = intervals.length ? intervals[0].ms : null;
ok(ms !== null && ms <= 3000,
   `advance interval is ${ms}ms — must be <=3000ms to read as motion`);

// ---- 2. hovering the section must NOT stop it -----------------------------
// This is the regression. `finding` is the band around the deck; a pointer
// resting anywhere in it while reading must leave the timer alone.
finding.fire('mouseenter', {});
ok(intervals.length === 1 && cleared === 0,
   'hovering the #finding band does not stop the carousel');

// ---- 3. hovering the deck or its controls DOES stop it --------------------
deck.fire('mouseenter', {});
ok(intervals.length === 0, 'hovering the deck pauses it');

deck.fire('mouseleave', { relatedTarget: null });
ok(intervals.length === 1, 'leaving the deck resumes it');

deckbar.fire('mouseenter', {});
ok(intervals.length === 0, 'hovering the arrows and dots pauses it too');

// Moving deck -> deckbar fires leave-then-enter. Resuming on that would
// restart the clock mid-gesture, changing the card as the pointer travels
// toward the "next" arrow.
deckbar.fire('mouseleave', { relatedTarget: deck });
ok(intervals.length === 0, 'moving between the deck and its controls stays paused');

deckbar.fire('mouseleave', { relatedTarget: finding });
ok(intervals.length === 1, 'leaving the zone entirely resumes it');

console.log(failures.length
  ? `\ncarousel: ${failures.length} failure(s)`
  : '\ncarousel: all checks passed');
process.exit(failures.length ? 1 : 0);
