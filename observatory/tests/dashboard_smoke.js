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
    addEventListener(type, fn) { (this._h = this._h || {})[type] = fn; }, appendChild(){}, querySelectorAll(){ return []; },
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
global.window = { addEventListener(){}, matchMedia: () => ({matches:false, addEventListener(){}, addListener(){}}), localStorage: {getItem:(k)=>k==='obs.px'?(process.env.OBS_PX||null):null,setItem(){}}, location:{hash: process.env.OBS_HASH||''} };
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

  // The version strip. Same element as freshness, so the assertion is the same
  // shape: a build told an update is waiting must say so, and the class has to
  // change with it — the border colour is the only thing separating "your
  // numbers are old" from "your copy of the tool is old".
  if (want === 'update') {
    const cls = (els['fresh'] || {}).className || '';
    if (!head) { console.error('a waiting update was not announced'); process.exit(1); }
    if (!/\bupdate|updated\b/.test(cls)) {
      console.error('update strip did not take its own class, got: ' + cls);
      process.exit(1);
    }
    console.log('UPDATE STRIP: head="' + head + '" class="' + cls + '"');
  }

  // The Prices page. trends.py computes the numbers and app.js only draws them,
  // so what is asserted here is that it draws *something true*: every part
  // filled, nothing NaN, and the three headline counts, the bars and the focus
  // card agreeing with a second, independent reading of the same change points.
  const px = JSON.parse(digest).price_trends;
  if (px) {
    const pv = els['pricesView'] || {};
    if (process.env.OBS_HASH !== '#prices') {
      if (pv.hidden !== true) { console.error('the Prices page must stay hidden until asked for'); process.exit(1); }
    } else {
      if (pv.hidden !== false) { console.error('#prices did not show the Prices page'); process.exit(1); }
      const text = (id) => (els[id] || {}).textContent || '';
      const markup = (id) => (els[id] || {})._html || '';
      const saved = JSON.parse(process.env.OBS_PX || '{}');
      const zoom = saved.zoom || 'lines', basis = saved.basis || 'ref', comp = saved.comp || 'input', range = saved.range || '90';
      const key = basis === 'list' ? comp : (basis === 'you' && px.mixes.yours ? 'eff_you' : 'eff_ref');
      const day = (d) => Date.parse(d + 'T00:00:00Z');
      const first = px.lines.map((l) => l.points[0].date).sort()[0];
      const from = range === 'all' ? first : new Date(day(px.as_of) - parseInt(range, 10) * 864e5).toISOString().slice(0, 10);
      const at = (l, d) => { let v = null; for (const p of l.points) if (p.date <= d) v = p[key]; return v; };
      const pct = (l) => {
        const base = at(l, from) != null ? at(l, from) : (l.points[0].date <= px.as_of ? l.points[0][key] : null);
        const cur = at(l, px.as_of);
        return base == null || cur == null ? null : (cur / base - 1) * 100;
      };

      const everything = ['pxStamp', 'pxBasisNote'].map(text)
        .concat(['pxKpis', 'pxList', 'pxFocus', 'pxChart', 'pxLegend', 'pxModels', 'pxEvents', 'pxNotes', 'pxWatch'].map(markup)).join('\n');
      if (/NaN|undefined|Infinity|\[object/.test(everything)) {
        console.error('the Prices page drew a bad value:\n' + everything.match(/.{0,60}(NaN|undefined|Infinity|\[object).{0,40}/)[0]);
        process.exit(1);
      }
      if (!text('pxStamp')) { console.error('Prices page: the stamp is empty'); process.exit(1); }

      // 1. at a glance: the three counts, against an independent reading
      let down = 0, up = 0, flat = 0, n = 0;
      for (const l of px.lines) {
        const c = pct(l);
        if (c == null) continue;
        n++; if (c < -1) down++; else if (c > 1) up++; else flat++;
      }
      const tiles = [...markup('pxKpis').matchAll(/<div class="pxkpi (down|up|flat)"><b>(\d+)<\/b>/g)].map((m) => [m[1], +m[2]]);
      const want = [['down', down], ['up', up], ['flat', flat]];
      if (JSON.stringify(tiles) !== JSON.stringify(want)) {
        console.error('the three counts disagree with the points: got ' + JSON.stringify(tiles) + ', want ' + JSON.stringify(want));
        process.exit(1);
      }
      if (!new RegExp('\\b' + n + '\\b').test(markup('pxKpis').match(/<p class="pxkof">.*?<\/p>/)[0])) {
        console.error('the "of N model lines" sentence does not name ' + n); process.exit(1);
      }

      // ...and the bar list: a row per line (per lab at the Labs level), each bar on the right side of zero
      const rows = (markup('pxList').match(/<button type="button" class="pxrow/g) || []).length;
      const wantRows = zoom === 'labs' ? px.lines.filter((l) => l.headline).length : px.lines.length;
      if (rows !== wantRows) { console.error('bar list has ' + rows + ' rows, wanted ' + wantRows + ' for zoom=' + zoom); process.exit(1); }
      const bars = (cls) => (markup('pxList').match(new RegExp('class="pxfill ' + cls + '"', 'g')) || []).length;
      const shown = (zoom === 'labs' ? px.lines.filter((l) => l.headline) : px.lines).map(pct).filter((c) => c != null);
      const wantBars = { down: shown.filter((c) => c < -1).length, up: shown.filter((c) => c > 1).length };
      if (bars('down') !== wantBars.down || bars('up') !== wantBars.up) {
        console.error('cheaper/dearer bars disagree with the points: ' + bars('down') + '/' + bars('up') + ' vs ' + JSON.stringify(wantBars));
        process.exit(1);
      }
      if ((markup('pxList').match(/<svg class="pxsp"/g) || []).length !== rows) { console.error('a row has no sparkline'); process.exit(1); }
      if (px.watch.length && !(els['pxWatch'] && els['pxWatch']._html)) { console.error('a rate under review was not surfaced'); process.exit(1); }

      // 2. one line in focus: it names a line, draws it, and says why
      const focusName = (markup('pxFocus').match(/<h2>.*?<\/h2>/) || [''])[0].replace(/<[^>]+>/g, '').trim();
      const heads = px.lines.filter((l) => focusName.indexOf(l.label) >= 0);
      if (!heads.length) { console.error('the focus card names no line: "' + focusName + '"'); process.exit(1); }
      if (!/<path class="pxmain"/.test(markup('pxFocus'))) { console.error('the focus chart drew no line'); process.exit(1); }
      if (!/class="pxwhy"/.test(markup('pxFocus'))) { console.error('the focus card has no "why" panel'); process.exit(1); }

      // Press every row, as a click would: each must bring its own line into focus.
      const press = els['pxList']._h && els['pxList']._h.click;
      if (!press) { console.error('the bar list has no click handler'); process.exit(1); }
      for (const l of px.lines) {
        if (zoom === 'labs' && !l.headline) continue;
        press({ target: { matches: () => true, getAttribute: (k) => (k === 'data-line' ? l.id : null), parentNode: null } });
        const name = (markup('pxFocus').match(/<h2>.*?<\/h2>/) || [''])[0].replace(/<[^>]+>/g, '');
        if (name.indexOf(l.label) < 0) { console.error('pressing ' + l.id + ' focused "' + name.trim() + '"'); process.exit(1); }
        if (/NaN|undefined|Infinity|\[object/.test(markup('pxFocus'))) { console.error('the focus card for ' + l.id + ' drew a bad value'); process.exit(1); }
        if (!/<path class="pxmain"/.test(markup('pxFocus'))) { console.error('no focus chart for ' + l.id); process.exit(1); }
      }

      // 3. the rest
      const drawn = (markup('pxChart').match(/<path class="pxl /g) || []).length;
      if (!drawn) { console.error('the all-lines chart drew no lines'); process.exit(1); }
      if (!/<li/.test(markup('pxEvents')) || !/<li/.test(markup('pxNotes'))) { console.error('events or notes are empty'); process.exit(1); }
      if (px.events.length > 8 && (markup('pxEvents').match(/<li/g) || []).length !== 8) { console.error('the change log is not limited to 8'); process.exit(1); }
      if (zoom === 'models' && !/<tr>/.test(markup('pxModels'))) { console.error('the Models level drew no table'); process.exit(1); }
      if (zoom !== 'models' && (els['pxModelsCard'] || {}).hidden !== true) { console.error('the Models table must stay hidden at this level'); process.exit(1); }
      if (basis !== 'list' && (els['pxComp'] || {}).hidden !== true) { console.error('the four price chips must appear only on the list-price basis'); process.exit(1); }
      console.log('PRICES PAGE: zoom=' + zoom + ' basis=' + basis + ' rows=' + rows + ' counts=' + down + '/' + up + '/' + flat + ' focus="' + focusName + '"');
    }
  }
} catch (e) {
  console.error('RUNTIME ERROR:', e.message, '\n', e.stack.split('\n').slice(0,4).join('\n'));
  process.exit(1);
}
