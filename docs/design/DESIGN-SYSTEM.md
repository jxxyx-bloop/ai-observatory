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

Display sizes are fluid; **body text is not**. A paragraph that resizes with
the viewport is harder to read, not easier. Line length is capped at
`--measure` (64ch). Numerals in any table, KPI, or chart label use
`font-variant-numeric: tabular-nums`, so columns of figures align.

Weights: 400 body, 500–600 UI, 650–700 display. Nothing heavier — the stack has
no reliable 800.

---

## 4. Space, shape, elevation

**Space** is a 4px scale (`--s1` … `--s10`). Layout uses the scale; raw pixel
values are a bug.

**Radius** carries meaning:

| | |
|---|---|
| `--r` (6px) | Dense data — table cells, dashboard panels. Data reads wrong when rounded. |
| `--r-sm` / `--r-md` | Cards, inputs, code blocks |
| `--r-lg` / `--r-xl` | Hero surfaces and full-bleed bands |
| `--r-pill` | Anything with an icon in it |

**Elevation** is three shadows, and depth is only ever expressed as *one* of
shadow, border, or fill — never two at once.

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

Every icon is **inline SVG** on a 24px grid, 1.6px stroke, `currentColor`, round
caps and joins. No icon font, no sprite sheet, no package.

That is not a preference, it is the product's promise made structural. The
dashboard claims zero external requests; a landing page advertising that claim
while pulling a webfont would be the loudest possible contradiction. So:

- system font stacks only,
- inline SVG only,
- no CDN, no tracking pixel, nothing fetched to draw the page,
- enforced by the CSP in `site/build.py` (`default-src 'none'`) **and** by a CI
  step that fails the build on any remote `src`/`href`.

The CSP is what makes the promise checkable by a browser instead of a sentence
in a README.

**The one boundary, drawn explicitly.** A deployment may count visits to its
*marketing* pages — the landing page and `/setup/` — by setting `ANALYTICS_ID`;
see [ANALYTICS.md](../setup/ANALYTICS.md). It may not reach `/demo/`, and it may
not reach the dashboard `render.py` writes onto a laptop. Those two carry the
promise, so the boundary is structural rather than remembered: the demo is
rendered by the engine's own renderer, `check_no_remote.py` refuses to exempt
anything under `demo/`, and `check_headers.py` fails a policy that would let a
remote host reach it. The privacy copy is switched by the same variable as the
tag, in all thirteen locales, so a page cannot advertise a promise it is not
keeping.

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
generated rather than designed. `title` in both i18n tables is "Your AI
coding, measured" — not "…measured." A stop *inside* a heading for rhythm is
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
