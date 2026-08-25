# ADR-016 — One token file for every surface; static pages per locale, generated docs

**Status:** accepted · **Date:** 2026-08-19

## Context

Three things had drifted or were missing:

1. **Two stylesheets, two palettes.** `site/style.css` and
   `observatory/assets/app.css` each declared their own `:root` block with the
   same hex values copied by hand. They already disagreed on radius, and would
   have disagreed on colour the first time either was touched.
2. **Language as a card.** The Chinese documentation was a card in the middle of
   the landing page — the one place a reader looking to change language does not
   look. Nothing else was translated at all, in a product whose entire
   positioning is Southeast Asia and China.
3. **A README nobody could keep true.** Prose describing a dashboard, next to no
   picture of it, with counts ("fifteen detectors", "thirteen currencies")
   restated by hand in four places.

The product's wedge is the region. Shipping it in English only was the largest
gap between the strategy documents and the artefact.

## Decision

**One design system, thirteen languages, and every derived document generated.**

### 1. `observatory/assets/tokens.css` is the only file with a literal colour

Every surface inlines it, then its own layout sheet. The landing page, the
hosted demo and a dashboard rendered on someone's laptop are the same design
system rather than three that resemble each other. The rationale — colour roles,
the type scale, where glass is and is not allowed, the zero-network rule — is
`docs/design/DESIGN-SYSTEM.md`.

### 2. Thirteen locales: every distinct SEA language, plus the largest AI markets

`en · zh-Hans · zh-Hant · ja · ko · hi · id · vi · th · ms · fil · pt-BR · es`

### 3. The landing page is static per locale; the dashboard switches in the browser

Deliberately different, for a reason that is structural rather than stylistic:

| | Landing page | Dashboard |
|---|---|---|
| Shape | one static page per locale | one page, all locales inlined |
| Why | crawlable URLs, `hreflang`, works with scripting off | also opened from `file://`, where no sibling URLs exist to link to |
| Cost | 13 × ~45 KB | ~20 KB of strings inside one page |

Both read the same `observatory-lang` and `observatory-theme` keys, so a choice
made on either carries to the other.

### 4. Interface strings are translated; so, since 2026-08-25, are findings

*(Originally: "generated findings are not." Reversed — see below.)*

The dashboard's chrome, filters, panel titles and captions are localised. So
are the footer's method notes, which are fixed editorial copy. Findings sit in
between: `insights.py` still composes them once, in English, with live numbers
threaded through sentences it builds itself — but every detector now also
returns `i18n_params`, the same locals under stable names, and
`assets/i18n.js` carries an `f_<id>_title` / `f_<id>_body` / `f_<id>_action`
template per detector per locale. `translateFindings()` in `assets/app.js`
substitutes on every language switch; English is not exempt, so a round-trip
through another locale and back is proven to return the same text rather than
assumed to. `test_findings_i18n_coverage` in `tests/test_engine.py` fails the
suite if a detector is missing its template in any of the thirteen locales.

The reversal is why the original limitation was accepted in the first place,
addressed rather than argued around: translating a template with numbers
already in it is a different job from translating a fixed label — the risk was
never the mechanism, it was a template rendering wrong and nobody noticing.
That is what the coverage test exists to catch, and what a native reviewer of
each locale should still spot-check before trusting it in production.

### 5. Every figure in the README is generated

| Generated | By | From |
|---|---|---|
| `docs/assets/*.svg` | `site/tools/diagrams.py` | `pricing.json`, `plans.json`, `insights.py`, `collectors/` |
| `docs/assets/*.png` | `site/tools/shots.js` | headless Chromium against the built site |
| `docs/readme/*.md` | `site/tools/readmes.py` | `site/i18n.py` |

`visuals.yml` refreshes and commits them on push; `site.yml` fails a PR whose
generated files no longer match their sources.

## Consequences

**Good.** A colour change lands in one file and reaches every surface. A reader
in Jakarta, Hanoi or Bangkok gets the pitch in their own language, from a URL
Google can index. A redesign updates its own documentation, so the README cannot
show last quarter's product. Correcting a rate in `pricing.json` redraws the
peak-window figure that argues for the product.

**Costs.** Thirteen locales are thirteen things to keep current — mitigated by
English fallback per key, so a partial translation degrades to English rather
than to a blank, and by `build.py` printing every key still falling back.
Screenshot generation needs Playwright, which is a dev-time and CI dependency;
the engine stays stdlib-only Python, and nothing in the shipped product depends
on it.

**Former accepted limitation, now closed.** Generated findings stayed English
from 2026-08-19 to 2026-08-25. §4 above has the current mechanism and why
translating a template with numbers already in it turned out to be tractable
where translating a runtime-composed sentence is not: the numbers are named
and passed as data, so no translator ever touches a number, only the sentence
around it.

## Alternatives considered

**A CSS framework.** Would have brought the first dependency into a repo whose
whole claim is that it has none, for a page that is six sections long.

**Client-side switching on the landing page too.** One URL, no `hreflang`, no
indexed page in any language but English — for a product whose growth argument
is regional search. Rejected.

**Machine-translating the findings at render time.** Requires a network call
from a page that promises it makes none. Rejected outright — this is also why
§4's mechanism is a fixed template per detector rather than a general-purpose
translator: the set of sentences a detector can produce is closed and known at
build time, so it can be hand-translated once rather than translated live.

**Hand-written translated READMEs.** Twelve documents that go stale the first
time the English changes, which is the failure mode this ADR exists to remove.

## Revisit when

- A locale's fallback list stops shrinking — it has an owner or it should be
  dropped, rather than sitting half-English indefinitely.
- Findings become templated enough that translating them is a data change rather
  than a prose change.
- A fourth surface appears (a native shell, an embeddable widget) and the
  `home`/breadcrumb argument in `render.py` needs generalising.
