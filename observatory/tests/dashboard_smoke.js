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
} catch (e) {
  console.error('RUNTIME ERROR:', e.message, '\n', e.stack.split('\n').slice(0,4).join('\n'));
  process.exit(1);
}
