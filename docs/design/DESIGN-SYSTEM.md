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

Localised copy is translated for **meaning**, not word-for-word, and is allowed
to be shorter than the English. Nothing may be padded to match a layout.

---

## 9. Where this lives

| File | Contains |
|---|---|
| [`observatory/assets/tokens.css`](../../observatory/assets/tokens.css) | Every token. The only file with literal colours. |
| [`observatory/assets/app.css`](../../observatory/assets/app.css) | Dashboard layout and charts |
| [`site/style.css`](../../site/style.css) | Landing page layout |
| [`site/i18n.py`](../../site/i18n.py) | Landing copy, all locales |
| [`observatory/assets/i18n.js`](../../observatory/assets/i18n.js) | Dashboard copy, all locales |

### Adding a surface

1. Inline `tokens.css`, then your layout stylesheet.
2. Reuse `.glass`, `.iconbtn` and the topbar markup — do not re-cut them.
3. Add every string to the locale table; never hard-code English in markup.
4. Both themes and a keyboard pass before it ships.
5. `python3 site/build.py` must stay clean, and the page must load nothing
   remote.

## 10. Checks

Run before any visual change lands:

```bash
python3 site/build.py                                  # every locale builds
observatory/tests/run.sh                               # dashboard still renders
grep -rInE '<(script|link|img)[^>]+(src|href)="https?://' site/dist/  # must be empty
python3 site/shots.py                                  # refresh README visuals
```
