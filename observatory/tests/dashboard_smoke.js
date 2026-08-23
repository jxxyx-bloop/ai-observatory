// Headless smoke test for the rendered dashboard.
//
//   node tests/dashboard_smoke.js ../dist/observatory.html assets/app.js
//
// The dashboard is one self-contained HTML file with no build step and no test
// framework — exactly the kind of thing that breaks silently. This stands up
// just enough of a DOM for app.js to execute against a real digest, so a typo
// in a chart function fails here rather than in someone's browser.
//
// The stubs are deliberately dumb. Selects default to "All" because that is
// what the real page sets them to on init; getting that wrong once made every
// panel silently filter to nothing, which is the failure this file exists to
// catch.
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const digest = html.match(/<script id="digest"[^>]*>([\s\S]*?)<\/script>/)[1];
// The freshness strip reads a second payload. OBS_META lets a caller override
// `generated_at` so the aged and stale branches can be exercised without
// waiting a week for the clock to catch up.
const metaRaw = (html.match(/<script id="meta"[^>]*>([\s\S]*?)<\/script>/) || [, '{}'])[1];
const meta = Object.assign(JSON.parse(metaRaw), JSON.parse(process.env.OBS_META || '{}'));

function El(id) {
  return {
    id, textContent: '', _html: '', value: 'All', hidden: false, dataset: {},
    style: {}, checked: false,
    set innerHTML(v) { this._html = String(v); }, get innerHTML() { return this._html; },
    classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
    setAttribute(){}, removeAttribute(){}, getAttribute(){ return null; },
    addEventListener(){}, appendChild(){}, querySelectorAll(){ return []; },
    querySelector(){ return null; }, closest(){ return null; },
    getBoundingClientRect(){ return {top:0,left:0,width:100,height:20}; },
  };
}
const els = {};
global.document = {
  getElementById(id) {
    if (id === 'digest') return { textContent: digest };
    if (id === 'meta') return { textContent: JSON.stringify(meta) };
    return (els[id] = els[id] || El(id));
  },
  createElement: (t) => El(t),
  addEventListener(){}, querySelectorAll(){ return []; }, querySelector(){ return null; },
  body: El('body'), documentElement: El('html'),
  readyState: 'complete',
};
global.window = { addEventListener(){}, matchMedia: () => ({matches:false, addEventListener(){}, addListener(){}}), localStorage: {getItem:()=>null,setItem(){}}, location:{hash:''} };
global.localStorage = global.window.localStorage;
global.matchMedia = global.window.matchMedia;
global.navigator = { language: 'en-SG' };

const app = fs.readFileSync(process.argv[3], 'utf8');
try {
  new Function(app)();
  const ids = Object.keys(els).filter(k => els[k]._html);
  console.log('app.js executed cleanly. Panels rendered:', ids.length);
  console.log('rendered ids:', ids.join(', '));
  const phase = els['phaseNote'];
  if (phase && phase._html) console.log('\nPHASE PANEL:\n  ' + phase._html.replace(/<[^>]+>/g,''));
  const kpi = els['kpis'];
  if (kpi) console.log('\nKPI markup bytes:', kpi._html.length);

  // Freshness: a report rendered minutes ago must stay silent, and an aged or
  // sample-data one must not. Both directions matter — a strip that never
  // appears is as broken as one that never goes away.
  // Detected from the heading rather than `.hidden`, because the stub element
  // starts visible while the real one carries the `hidden` attribute — reading
  // the flag would report "shown" for a page that never ran the branch.
  const head = (els['freshHead'] || {}).textContent || '';
  const shown = head !== '';
  const want = process.env.OBS_EXPECT;
  console.log('\nFRESHNESS: shown=' + !!shown + (head ? ' head="' + head + '"' : ''));
  if (want === 'shown' && !shown) { console.error('expected the freshness strip'); process.exit(1); }
  if (want === 'hidden' && shown) { console.error('freshness strip should be silent'); process.exit(1); }
  if (shown && !(els['freshCmd'] || {}).textContent) {
    console.error('freshness strip shown without a refresh command'); process.exit(1);
  }

  // Sample data discloses itself on the title line instead of in the strip —
  // and the disclosure is the one thing on this page that must never be
  // possible to lose, so it is asserted rather than assumed. A demo build that
  // silently stops saying it is a demo is the worst bug this page could ship.
  const chip = (els['demoChip'] || {}).textContent || '';
  console.log('DEMO FLAG: chip="' + chip + '" link="'
    + ((els['demoTry'] || {}).textContent || '') + '"');
  if (want === 'demo') {
    if (!chip) { console.error('sample data did not disclose itself'); process.exit(1); }
    if (shown) { console.error('sample data should use the title flag, not the strip'); process.exit(1); }
  }
  if (want === 'hidden' && chip) {
    console.error('real data must not be flagged as a sample'); process.exit(1);
  }
} catch (e) {
  console.error('RUNTIME ERROR:', e.message, '\n', e.stack.split('\n').slice(0,4).join('\n'));
  process.exit(1);
}
