/* Capture the live site into docs/assets/, so the README's visuals are the
 * product rather than a drawing of it.
 *
 *   python3 site/build.py && node site/tools/shots.js
 *
 * Every image the README shows is produced here from `site/dist/`, in both
 * themes, at fixed viewports. That is the whole point: a README screenshot
 * pasted in by hand rots the moment the design changes, and nothing fails when
 * it does. This runs in CI on every push that touches the site, commits what
 * changed, and so the README can only ever show the current design.
 *
 * Playwright is a dev-time tool, invoked with npx. It is deliberately not a
 * dependency of the engine, which stays stdlib-only Python.
 */
const {chromium} = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const DIST = path.join(ROOT, 'site', 'dist');
const OUT = path.join(ROOT, 'docs', 'assets');

// name, page, theme, viewport. Every image here is referenced by the README —
// an unreferenced screenshot is just a large file nobody checks.
const SHOTS = [
  ['landing-light',        'index.html',      'light', [1280, 860]],
  ['landing-dark',         'index.html',      'dark',  [1280, 860]],
  ['landing-mobile-light', 'index.html',      'light', [414, 900]],
  ['landing-mobile-dark',  'index.html',      'dark',  [414, 900]],
  ['demo-light',           'demo/index.html', 'light', [1280, 900]],
  ['demo-dark',            'demo/index.html', 'dark',  [1280, 900]],
];

(async () => {
  if (!fs.existsSync(path.join(DIST, 'index.html'))) {
    console.error('shots: run `python3 site/build.py` first — site/dist is empty');
    process.exit(1);
  }
  fs.mkdirSync(OUT, {recursive: true});

  const browser = await chromium.launch();
  for (const [name, page, theme, [w, h]] of SHOTS) {
    const ctx = await browser.newContext({
      viewport: {width: w, height: h},
      deviceScaleFactor: 2,             // legible when GitHub scales it down
      colorScheme: theme,
      reducedMotion: 'reduce',          // no half-finished drift in a still
    });
    const p = await ctx.newPage();
    // The stored theme wins over colorScheme, so set it before the page loads.
    await p.addInitScript(t => {
      try { localStorage.setItem('observatory-theme', t); } catch (e) {}
    }, theme);
    await p.goto('file://' + path.join(DIST, page), {waitUntil: 'load'});
    await p.waitForTimeout(700);        // charts render, reveal settles

    const file = path.join(OUT, name + '.png');
    await p.screenshot({path: file});

    console.log('  ' + path.relative(ROOT, file) +
                '  ' + (fs.statSync(file).size / 1024).toFixed(0) + ' KB');
    await ctx.close();
  }
  await browser.close();
  console.log(`shots: ${SHOTS.length} images into docs/assets/`);
})().catch(e => { console.error(e); process.exit(1); });
