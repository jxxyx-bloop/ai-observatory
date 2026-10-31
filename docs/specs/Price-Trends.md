# Spec — Price Trends

The **Prices** page (`#prices` in the dashboard) answers one question: *what is going up and what is going down?* It is computed by [`observatory/trends.py`](../../observatory/trends.py) from the dated rate card ([Cost-Estimation § Dated rates](Cost-Estimation.md#dated-rates)) and drawn by `app.js`. The page contains no arithmetic of its own, so the tests assert the numbers once.

## Why one price per model is not enough

A model has four prices — input, output, cache read, cache write — and they move independently. For an agentic coding session the cache read is nearly all of the bill (97% of the tokens on the maintainer's own store), so a cache discount moves the real price far more than a headline change does:

| | Input / output | Cache read | Typical coding session |
|---|---|---|---|
| Opus 5 → Opus 5.5 | $5/$25 → $4/$20 (−20%) | 0.10× → 0.05× | **−46%** |

So every line is also reduced to **one number**: the cost of 1M tokens of a *reference mix* (`reference_mix` in `pricing.json`), or of the reader's own mix, measured from their digest. List price stays one toggle away.

## Lines, not models

A lab's flagship is replaced, not repriced: Opus 4.8 → Opus 5 is a new model at the same price, Opus 5 → 5.5 is a new model at a lower one. A chart of "Opus 5" alone would stop the day it was succeeded. `lines` in `pricing.json` records *which model a lab offered in a tier, and when the next one took over*; a model's own repricing still comes from `history`. A line starts at its first model's `from` — prices before a model existed are never invented.

```json
{"id": "anthropic-premium", "lab": "anthropic", "label": "Opus", "tier": "premium", "headline": true,
 "models": [{"model": "claude-opus-4-5", "from": "2025-11-24T00:00+08:00"}, ..., {"model": "claude-opus-5-5", "from": "2026-09-22T00:00+08:00"}]}
```

`headline: true` marks the one line that stands for its lab at the most zoomed-out level. Anthropic's is Opus (long history, the line most used for coding), not the gated top tier.

## What the page shows

Read top to bottom in the order the questions come: **a glance, then one line in focus, then everything else on demand.**

1. **At a glance.** Three big counts — *N got cheaper · N got dearer · N unchanged* — with the biggest drop and rise (and the model and date behind each) beside them, and a **Watch** strip for any rate the vendor has said will end (`recheck_after`). Then **What changed**: one row per model line, grouped by lab. Each row is a diverging bar with zero in the middle — cheaper grows left and green, dearer grows right and orange, no change is a grey tick that says so — plus the percentage, the price now, and a tiny step line showing *when* it moved. Labs / Lines / Models chips set the level of detail (one headline line per lab, every line, or every line plus the table of every model).
2. **One line in focus.** Click a row — or take the default, the biggest mover among each lab's headline lines — and that one line is drawn properly: its price now, the change over the range, and a single step chart with **every model named where it took over**. Beside it, **what moved**: the four prices (input, output, cache read, cache write) old → new, each with its share of the effect on the displayed number (price change × how many tokens of that kind a session has), and one sentence saying so — *"Cache read accounts for 85% of the change, because most tokens in a session are of that kind."* That sentence is the whole point of using an effective price, stated where the reader is looking.
3. **On demand.** *Compare all lines on one chart* (collapsed; hover a name to isolate its line; lines that end at the same price share one label), the table of every model and the window each price applied for (Models level), the change log (newest 8, *Show all* for the rest), and what the page does not show.

The controls are the ones a reader actually reaches for: the **range** (90 days / 180 days / all) and the **price basis** (typical session / your mix / list price, with the four component chips appearing only on list price). Scale (dollars or index) and change markers belong to the all-lines chart and live inside it.

### Why it is built this way

The first version put all seven lines on one chart with a scoreboard table above it and ten toggles in a row, and it did not survive a reader's first look:

- **Seven lines cannot be labelled without collisions.** Opus and the GPT flagship both sat at $5; Sonnet and GPT-5.6 Terra at $2. Their labels printed on top of each other, and so did the model names written along the lines. Drawing *one* line in focus is the only way to name every model on it; the all-lines chart keeps its end labels (merged where lines coincide) and drops the model names.
- **Ten toggles made people configure the chart before they could read it.** Price basis, the price of, scale and markers were four groups, ten buttons, in one row, all needed before the first number meant anything. The summary is now readable with none of them touched; each control sits next to the thing it changes.
- **A sentence and a table is not a glance.** The counts and the bars answer *what is going up and what is going down?* before any text is read, and direction is carried by position, sign and words as well as colour.

## The payload

`trends.build(pricing, totals, today)` returns plain JSON (about 12 KB): `lines` (each a short list of **change points**, not a daily series — a price is constant until it changes), `events`, `watch`, `untraced`, `labs`, and the `mixes`. Dates are Singapore-time calendar days, the benchmark the rate card is kept in. It is embedded in the digest as `price_trends`; a digest without it (an older file) simply hides the page's rail link.

## Honest limits

- **Only OpenAI and Anthropic are traced** through their price changes (`_verified_by_vendor`). Every other vendor on the card is listed under *Not traced yet* with its current rates and **no trend** — a flat line would read as "never changed", which is a claim, not an absence.
- **List price, not a bill.** A gateway or reseller can bill differently and apply a vendor's change at its own time.
- **Dates are good to about a day.** Vendors publish a date, not an hour; a date-only change is shown from the start of that day in Singapore time.
- **Price per token is not price per task.** Anthropic says Fable 5 and Sonnet 5 turn the same text into about 30% more tokens than earlier models. Not modelled.
- **Not modelled:** long-prompt surcharges and Fast mode; a transcript records neither.
- **GPT-5.4's launch price** is not stated in OpenAI's changelog; the card assumes today's $2.50/$15 because the changelog records no repricing.

## Keeping it current

The page is only as current as `pricing.json`. A change is a PR: move the old rate into `history`, set the new `from`, and — if a new model takes over a tier — append it to that line. `validate_card` rejects a line that names a model not on the card or whose models do not move forward in time, and `doctor` flags a promotional rate that has passed its documented end. Fetching prices at runtime stays rejected ([ADR-012](../adr/ADR-012-Rate-Card-As-Config.md)).

## Tests

`test_engine.py::test_price_trends` checks the numbers against arithmetic done by hand (the Opus figure above, Sonnet 5.5's cache-read cut, Sol's promotion, a rise, a line that has not started yet). `tests/dashboard_smoke.js` renders the page under every level, price basis, scale and range, and checks — against an independent reading of the same change points — the three counts, that the bars sit on the right side of zero, that there is a row and a sparkline per line, and that **pressing every row** brings that line into focus with its own chart and nothing `NaN`. It was checked by breaking the page on purpose (a wrong direction threshold, a wrong row, a `NaN` price) and confirming each is caught.
