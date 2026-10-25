# Design system

Everything with a surface in this project — the landing page, the hosted demo,
the dashboard you render on your own machine — is built from one set of tokens.
This document is the *why*; [`observatory/assets/tokens.css`](../../observatory/assets/tokens.css)
is the *what*, and it is the only file allowed to contain a literal colour.

> **The rule that keeps it true:** every surface inlines `tokens.css` first,
> then its own layout stylesheet. A page that defines its own palette has
> already left the system.

---

## 1. The idea

> **A quiet instrument that is fun to pick up.**

Two things are in tension and both have to survive:

| | |
|---|---|
| **Instrument** | The product's only asset is credibility. Numbers must look like numbers. Nothing decorative may sit near a figure the reader is asked to act on. |
| **Fun to pick up** | Nobody adopts a cost tool out of duty. The first screen has to feel like an experiment worth opening — generous space, real motion, one confident colour. |

The resolution is **spatial**: expression lives in the chrome and the entry
points; restraint lives wherever data is. The hero may drift and glow. A KPI
tile may not.

Three things you can always check a new screen against:

1. **Would a number on this screen be believed?** If the surface behind it is
   doing something, the answer is no.
2. **Can it be read in one breath?** If a sentence needs a second pass, cut it.
3. **Does it work with the lights off?** Both themes, always, from day one.

---

## 2. Colour

One protagonist. Everything else is neutral.

### Roles, not names

| Token | Role |
|---|---|
| `--bg` / `--bg-deep` | Page, and recessed bands within it |
| `--panel` | Any opaque content surface |
| `--ink` / `--muted` / `--faint` | Primary text / secondary / tertiary |
| `--line` / `--line-strong` | Hairlines; the strong variant only on hover |
| `--accent` | The single thing a screen is about |
| `--high` `--med` `--low` `--info` `--ok` | Severity and status — never decoration |

Indigo is the protagonist rather than the usual developer-tool green: green
already means *passing* in every terminal, and this product's job is to be
read, not scanned for pass/fail.

**The dashboard resolves the same names to different values.** The dashboard
page carries `body.dash`, which re-points `--bg`, `--panel`, `--ink`, `--muted`,
`--faint`, `--line`, `--track` and `--bar` at the Wingman Hangar port's palette
(page `#f2f3f5`, card `#fff`, hairline `#e6e6e9`, and a warm `#151513` /
`#1d1d1a` dark rather than the landing page's blue-black), points `--accent` at
the Shopee orange `--accent-data`, and defines `--sev-*` for the left edge of a
finding card. `app.css` keeps reading the shared names, so no rule in it knows
which palette it is drawing in; the landing page has no `.dash` and is
untouched. Hangar has no tertiary ink — every secondary line is one muted grey —
so `--faint` collapses onto `--muted` there, which is also why the dashboard's
small text passes contrast where the landing page's `#8b8b99` does not.

### The gradient

`--grad` runs cool→warm across blue, violet, magenta, amber. It is the one
expressive element in the system and it is rationed to **three** uses:

1. the accent word in a display headline,
2. the primary call to action,
3. the ambient field behind the hero.

A fourth use makes it wallpaper, and wallpaper means nothing.

### Contrast

`--ink` on `--bg` clears 4.5:1 in both themes; `--muted` clears 4.5:1 at body
size; `--faint` is for 12px+ non-essential text only and is never the sole
carrier of meaning. Dark is a designed theme, not an inversion — the accent is
*lifted* (`#4f46e5` → `#9b93ff`) so it holds the same perceived weight against
a dark ground.

---

## 3. Type

One system sans, one system mono. **No webfont** — see §7.

| Token | Use | Tracking |
|---|---|---|
| `--t-display` | Hero headline only, one per page | `--tr-display` (−.035em) |
| `--t-h1` / `--t-h2` / `--t-h3` | Section heads | `--tr-head` (−.02em) |
| `--t-lede` | The one paragraph under a headline | normal |
| `--t-body` / `--t-sm` / `--t-xs` | Prose / UI / dense UI | normal |
| `--t-micro` | Eyebrows and badges, uppercase | `--tr-eyebrow` (+.14em) |
| `--t-cap` / `--t-cap-lg` | Rail tiles, KPI keys, panel heads, table headers | `--cap-track` / `--cap-track-lg` |

### The caption scale is per-script

`--t-cap` and its siblings (`--cap-track`, `--cap-case`, `--cap-weight`,
`--cap-lh`) are **redefined by the document's language**, and a caption must
read them rather than hard-code a size.

A 9.5px uppercase caption is a Latin device. It works because capitals are
simple, open shapes the eye completes from very little ink, and because
tracking them apart is what makes a run of capitals legible at all. None of
that transfers: `text-transform:uppercase` is a no-op on CJK and Devanagari,
so those scripts render their full stroke count at a size chosen for shapes
that had been simplified, and fill in to a grey smudge. Thai keeps Latin-ish
widths but hangs marks outside a 1.15 line-height.

| Script | `--t-cap` | Case | Tracking |
|---|---|---|---|
| Latin (default) | 9.5px | uppercase | +.05em |
| Latin, long section words (id, ms, fil, pt-BR, es, vi) | 9.5px | none | +.01em |
| Thai, Devanagari | 10.5px | none | +.01em, `--cap-lh` 1.5 |
| CJK (zh-Hans, zh-Hant, ja, ko) | 12px | none | 0, `--cap-lh` 1.35 |

The rule matches on both `[lang]` and `[data-lang]`: the landing page ships one
static page per language and sets `lang` at build time, while the dashboard is
a single page that sets both at runtime when the reader switches.

Display sizes are fluid; **body text is not**. A paragraph that resizes with
the viewport is harder to read, not easier. Line length is capped at
`--measure` (64ch). Numerals in any table, KPI, or chart label use
`font-variant-numeric: tabular-nums`, so columns of figures align.

Weights: 400 body, 500–600 UI, 650–700 display. The dashboard's title and its
scoreboard numbers are 800, as on the Hangar port — the one place a heavier
weight earns its keep, because those are the figures a reader came for.

---

## 4. Space, shape, elevation

**Space** is a 4px scale (`--s1` … `--s10`). Layout uses the scale; raw pixel
values are a bug.

**Radius** carries meaning:

| | |
|---|---|
| `--r-data` (3px) / `--r-data-sm` (2px) / `--r-data-bar` (1px) | **The dashboard**, Hangar's own corners. Cards, the KPI strip and chips / tags and inline code / bar tracks and heatmap cells — a flat edge to measure against. |
| `--r` (6px) | Dense data — table cells. Data reads wrong when rounded. |
| `--r-sm` / `--r-md` | **Landing page** cards, inputs, code blocks |
| `--r-lg` / `--r-xl` | Hero surfaces and full-bleed bands |
| `--r-pill` | Anything with an icon in it |

The two surfaces share a palette, a type stack and a spacing base, but **not a
corner**. The landing page is a brochure and rounds generously; the dashboard
is an instrument, and at instrument density a 12px corner eats the top-left
cell of every table and leaves a visible crescent of page between panels meant
to read as one field. `--r-data` is a separate token rather than an override
of the scale so that restyling one surface cannot silently restyle the other.

**Width.** The landing page caps content at `--page` (1120px) to protect the
measure of its prose. The dashboard caps at **1560px**, because it has no
measure to protect — the Hangar port does not cap at all, and this keeps that
behaviour everywhere a laptop or desktop monitor is likely to be, stopping only
where a chart stretched across an ultrawide becomes its own problem.

**Seams, not moats.** Cells that share a scale and are meant to be read across
(the KPI strip) get one border and 1px seams, not one rounded box each with a
gap between them. Each tile draws its own top and left hairline and a `-1px`
margin on those two sides lets it cover its neighbour's last pixel; the first
row's and column's land under the container's `overflow:hidden`, so the outer
edge is the container's single border. (Hangar paints the seams with `gap:1px`
over a `--line` background, which is the same picture at five across — but with
five tiles in two or three columns, the unfilled cell shows up as a grey block.)
The column count steps 5 → 3 → 2 on the section's own width and the last tile
takes whatever is left of its row, because five never divides evenly and an
orphan beside empty cells reads as a missing number.

**One protagonist per chart.** Supporting marks take `--bar`; the single mark
that answers the panel's question takes `--accent`. Colouring every bar in the
accent spends it on the sorting rather than on the finding.

**Charts are measured, never scaled.** An SVG scales its type and its
hairlines along with its geometry, so a 720-wide viewBox stretched to fill a
1175px panel renders 11px axis labels at 18px. Chart code reads its
container's width and emits a viewBox that matches it 1:1, with a floor below
which the panel scrolls horizontally instead. This is a width rule, not a
height one — see the next paragraph for why the two are decided separately.

**A grid's row height is a design decision, not a side effect of its width.**
The weekday×hour heatmap (`meter()`) inherited the same fixed-viewBox bug as
the daily chart, with a worse result: because a 2D grid's height is *derived*
from its width through the aspect ratio a fixed viewBox bakes in, widening the
page to close the whitespace gap (see the width-cap change above) widened this
chart too, which *proportionally grew its height with it* — 20px cells
rendering at ~30px, on a chart with no text of its own to make the distortion
obvious the way axis labels did on the daily chart. The fix is the same
measure-the-container rule, but the height in the viewBox this chart computes
stays a **fixed pixel value** (16px cell, 2px gap) regardless of what the
measured width comes out to — width and height are independent numbers here,
not two sides of one ratio.

16/2 is deliberate, not incidental: it is the exact density of the Wingman
Hangar port's `HeatmapStrip.svelte`, adopted because a 7×24 grid is a texture
read at a glance, not 168 things read one at a time, and a texture can afford
to be small. Precedent for this already existed in-repo before either chart
was fixed — the "long view" GitHub-style calendar (`calendar()`) uses a fixed
cell (16px at an 18px pitch, so its seven rows line up with the grid beside it)
and was never stretched, because it renders at its own intrinsic size
(`#calendar svg{width:auto}`) rather than filling its container. `meter()` and
`daily()` chose the opposite shape — filling the container is what makes the
KPI-strip-style page rhythm work at the width this redesign settled on — so
they need the measurement discipline the calendar gets for free.

**A shape may stretch; a plot may not.** The third variant of the same bug:
a sparkline's viewBox is 220×46, and `svg{height:auto}` rendered it at ~71px
inside a ~340px card. Unlike the two charts above, the fix is not to measure —
nothing is read off a sparkline's x-axis, so it is *free* to stretch
horizontally. What it may not do is derive its height from that stretch. So
sparklines pin `height` in CSS and keep the viewBox's own aspect — the 220px
line sits centred in a wider card, exactly as it does on the Hangar port — grid
charts measure width and pin height in the viewBox, and full plots measure both.
Three different answers, one question to ask first: **is this value read off
an axis, or is it a shape?**

**One card per question, sub-headed rather than split.** The three behavioral
sparklines and the weekday×hour grid answer one question — how am I working,
and is it changing — so they live in one panel under one section heading,
with the grid introduced by an `<h3>` inside the card. They had been two
sections with two rail stops, which made a reader treat them as unrelated and
left the grid alone in a card tall enough to fill a screen. Splitting a
question across two nav stops costs more than the scroll it saves. This is
also the Hangar port's arrangement, and the reason its `#trends` card carries
an `<h3>` in the middle of it.

**Elevation** is three shadows, and depth is only ever expressed as *one* of
shadow, border, or fill — never two at once.

### The dashboard is the Wingman Hangar port's design

The company-wide Observatory on Hangar is the reference for how the dashboard
looks, and the geometry in `app.css` is copied from that port's Svelte
components on purpose — a 92px rail, 18px between cards, a 36px/800 scoreboard,
15px/700 card titles, 9px bar tracks, chips instead of a joined control — so the
two can be put side by side and differ only in what the data says. Its source
is mirrored in the shopee-os repository under
`projects/active/ai-observatory/hangar/frontend/src`; when the port changes,
that is where to look.

It is a port of the *look*, not of the stack: Hangar needs Svelte and a backend,
and this project's pitch is that it needs neither. So where Hangar has a
feature this tool does not have a source for (company comparison, app health,
setup tour), nothing is faked. And where this tool has something Hangar does
not, it is kept and drawn in Hangar's own vocabulary rather than a second one:

| This page has | Hangar has | How it is reconciled |
|---|---|---|
| Provider / lane / repository filters, From–To dates | none | A **Filters** chip in the range row, same style; it lights an orange dot while anything narrows the page |
| A metric switch on the daily chart, click-a-day drill-down | spend only | Chips in the card header; bars stay neutral until hovered |
| "Inside <repo>" and "Named subagents" cards, the long-view calendar | none | Same card, same bar list; the calendar sits beside the heatmap |
| Repository attribution ("Where the effort went") | workspace folder names | Same card and note; the data underneath is richer |
| Heatmap peak-window rings for time-priced vendors | none | Drawn only when a time-priced vendor is in range |
| A "This month" preset | 7 / 30 / 90 / All | Dropped from the row; the From–To dates take any range |

Two things in the port are deliberately **not** copied. Its model-switch callout
is a flex row, which collapses the spaces around the bold number ("in**18**% of
sessions"); here it is a block, so the sentence keeps its spaces. And its KPI
seams are painted with `gap:1px` over a `--line` background, which leaves a grey
cell on a phone — see *Seams, not moats*.

---

## 5. Glass

`.glass` is a translucent, blurred, saturated surface with a hairline. It is
for **floating chrome only**: the top bar, popovers, the hero card.

Content panels stay opaque. Text over a live blur is where "liquid glass" turns
into unreadable, and every number in this product is text.

The recipe exists once, in `tokens.css`, wrapped in `@supports`. A browser
without `backdrop-filter` gets `--glass-flat` — opaque, still correct, no
per-component fallback to forget.

---

## 6. Motion

One curve (`--ease`), three durations (`--d-fast` 120ms, `--d-mid` 220ms,
`--d-slow` 420ms). Motion earns its place by explaining a state change:
entering, filtering, expanding. Nothing loops in the reader's field of view
except the hero's ambient gradient, which is slow enough to be felt rather than
watched.

`prefers-reduced-motion` is handled globally in `tokens.css`. Because every
animation goes through those tokens, one media query stills the entire system —
there is no per-component opt-in to forget.

---

## 7. Iconography and the zero-network rule

**Icons before words.** Theme, language, external links and navigation are all
glyphs with an `aria-label` and a `title`; a text label appears only where the
glyph would be ambiguous.

Every icon is **inline SVG** on a 24px grid (the dashboard rail uses the Hangar
port's 20px set), 1.6px stroke, `currentColor`, round caps and joins. No icon font, no sprite sheet, no package.

That is not a preference, it is the product's promise made structural. The
dashboard claims zero external requests; a landing page advertising that claim
while pulling a webfont would be the loudest possible contradiction. So:

- system font stacks only,
- inline SVG only,
- no CDN, no analytics, no tracking pixel,
- enforced by the CSP in `site/build.py` (`default-src 'none'`) **and** by a CI
  step that fails the build on any remote `src`/`href`.

The CSP is what makes the promise checkable by a browser instead of a sentence
in a README.

---

## 8. Voice

The copy is part of the system.

| Do | Don't |
|---|---|
| "Know what to change." | "Actionable intelligence for AI spend optimisation" |
| "Nothing leaves your laptop." | "Privacy-first architecture" |
| A number with a unit | A number with an adjective |
| Say what it *doesn't* do | Imply it does everything |

Rules: one idea per sentence; a claim gets a figure or gets cut; no
capitalised Product Nouns; no exclamation marks; no "simply", "just",
"seamless", "powerful", "revolutionary", "leverage", "unlock".

**No terminal punctuation on a heading or sub-heading** — `<h1>`, `<h2>`,
`<h3>`, a KPI label, a panel title, a nav tile. A full stop at the end of a
line that is already set off by size and whitespace reads as a sentence
someone forgot to stop typing, which is the fastest tell that copy was
generated rather than designed. The dashboard's `title` key is "Where your AI
effort went" — not "…went." A stop *inside* a heading for rhythm is
fine and stays (`find_h2`: "Not a number. A next move") — it is only the
trailing one that goes, because the layout already marks the boundary.
Sentences of body copy under a heading keep normal punctuation; this rule is
for the heading itself, in every locale.

Localised copy is translated for **meaning**, not word-for-word, and is allowed
to be shorter than the English. Nothing may be padded to match a layout.

---

## 9. Drawing an SVG figure

Figures are generated by [`site/tools/diagrams.py`](../../site/tools/diagrams.py),
never drawn by hand. The spacing constants at the top of that file are the
executable half of this section; change them there, not in a call site.

### Rhythm — the rule that caught us

**Rows of the same kind share one pitch.**

The first peak-pricing chart stacked its two working-hour rows at a 42px pitch
and its vendor rows at 74px. Every number in it was right and it still read as
broken. Uneven spacing is not neutral: the eye takes it as a *claim* — *these
two belong together, those don't* — and there was no such claim being made. The
reader spends attention resolving a grouping that means nothing, and concludes
something is wrong without being able to say what.

| Token | Value | Rule |
|---|---|---|
| `ROW_PITCH` | 56px | Baseline-to-baseline for every row of the same kind. Never varied within a group. |
| `ROW_H` | 30px | The drawn height of one row |
| `GROUP_GAP` | 28px | Extra space **only** where the kind of row genuinely changes — and it must be obvious to the reader why |
| `GUTTER` | 40px | Figure edge → content. Titles and captions align here, like any other left margin. |
| `PAD` | 18px | Card edge → the text inside it |

A second gap size means a second kind of boundary. If you cannot name what
changed, use `ROW_PITCH`.

### Height follows the copy

Never hard-code a card height. Wrap every label first, take the longest, and
derive the height from it:

```python
notes = [wrap(n, box_w - 2 * PAD, 12) for n in all_notes]
bh = 104 + (max(len(n) for n in notes) - 1) * 15 + 20   # 20px under the last baseline
```

A fixed height is how the third line of a box ends up sitting on its own bottom
stroke — which happened here, in this repo, and is caught by the audit below.
The box exists to hold the text; the text does not exist to fit the box.

### Before committing a figure

1. **Last-line gap ≥ 20px.** Audit *every* card in *every* figure in the diff,
   not only the ones you edited — a copy change three cards away moves text you
   were not looking at.
2. **One pitch per group.** Measure two adjacent rows of the same kind; the
   difference must be zero.
3. **No collisions.** Render at 100% and read every label. Legends and captions
   get their own line rather than competing for one.
4. **Recompute the viewBox.** Anything past it is silently clipped.
5. **Both themes.** Every figure ships `-light` and `-dark`.

### Say what you checked, and only that

A figure that shows five vendors while its subtitle says thirteen is not a
rounding error, it is a false claim. Where the data covers part of a field,
draw the remainder explicitly as *unchecked* — a dashed, empty row — and let
the counts come from the data rather than from a sentence someone has to
remember to update. "We looked and there is nothing there" and "nobody has
looked" are different findings, and the reader cannot tell them apart unless
the figure does it for them.

## 10. Where this lives

| File | Contains |
|---|---|
| [`observatory/assets/tokens.css`](../../observatory/assets/tokens.css) | Every token. The only file with literal colours. |
| [`observatory/assets/app.css`](../../observatory/assets/app.css) | Dashboard layout and charts |
| [`site/style.css`](../../site/style.css) | Landing page layout |
| [`site/i18n.py`](../../site/i18n.py) | Landing copy, all locales |
| [`site/tools/diagrams.py`](../../site/tools/diagrams.py) | Every generated figure, and the spacing constants in §9 |
| [`observatory/assets/i18n.js`](../../observatory/assets/i18n.js) | Dashboard copy, all locales |

### Adding a surface

1. Inline `tokens.css`, then your layout stylesheet.
2. Reuse `.glass`, `.iconbtn` and the topbar markup — do not re-cut them.
3. Add every string to the locale table; never hard-code English in markup.
4. Both themes and a keyboard pass before it ships.
5. `python3 site/build.py` must stay clean, and the page must load nothing
   remote.

## 11. Checks

Run before any visual change lands:

```bash
python3 site/build.py                                  # every locale builds
observatory/tests/run.sh                               # dashboard still renders
grep -rInE '<(script|link|img)[^>]+(src|href)="https?://' site/dist/  # must be empty
python3 site/shots.py                                  # refresh README visuals
```
