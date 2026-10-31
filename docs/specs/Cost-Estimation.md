# Spec — Cost Estimation

## What is exact and what is not

**Exact:** every token count. They come from the `usage` object the API returned and are not recomputed or approximated.

**Estimated:** every dollar figure. It applies a local price list to those exact counts. Treat spend as a **relative** measure of where effort goes, not as a bill.

Three reasons the number is not a bill:
1. On a seat or enterprise plan, per-token rates are notional — nobody invoices these tokens individually.
2. The price list is a local snapshot (`pricing.json._verified_on`) and drifts as pricing changes.
3. Unknown models fall back to Opus-tier rates, flagged `confidence: low`.

This is why the dashboard leads with **cache efficiency and behavioural ratios**, not spend. Those are exact and are the levers the owner actually controls.

## The formula

Per turn, in `analyze.py::cost_of`:

```
cost = input        × rate_in
     + output       × rate_out
     + cache_read   × rate_in × 0.1
     + cache_5m     × rate_in × 1.25
     + cache_1h     × rate_in × 2.0
```

Rates come from `pricing.json`, keyed by canonical model alias, with a `speed_overrides` entry for fast mode.

## The multipliers, and why they matter more than the rates

| Operation | Multiplier on input rate |
|---|---|
| Cache read | **0.1×** (default — see override below) |
| Cache write, 5m TTL | 1.25× |
| Cache write, 1h TTL | 2.0× |

The spread between reading (0.1×) and rebuilding (1.25×) is **12.5×**. That single ratio is why "keep the session alive" is the highest-leverage habit available, and why `cache-cold` is a high-severity detector.

**Per-model override.** The 0.1× cache-read discount is Anthropic's own price list, not a law of nature — Moonshot's Kimi models price a cache hit at ~0.17–0.2× their miss rate instead. A model entry in `pricing.json` may set its own `cache_read_mult` (see `kimi-k2.7-code`); `cost_of` prefers it over the global default when present.

Break-even on the 1h TTL is roughly three reads per written token (2.0 + 0.2×n versus 1.25 + 0.1×n against paying full rate each time). Below that, the long TTL is paid for and unused — detector `cache-1h-underused`.

## The unsplit-write guard

When a provider reports `cache_create` but not the TTL split, the whole write is priced at the cheaper **5m** rate. Overstating cost would make every finding look more valuable than it is, so the guard deliberately errs low.

## Dated rates

A price is only right for a moment in time. A flat card makes every month before a price cut look as cheap as the month after it, and every month before a rise look dearer. So `cost_of` prices each turn at the rate in force **at that turn's own timestamp**.

`pricing.json` keeps the current rate in `models` and the superseded ones in `history`:

```json
"models":  { "gpt-5.6-terra": { "input": 2.0, "output": 12.0, "from": "2026-07-30T00:00+08:00", ... } },
"history": { "gpt-5.6-terra": [ { "from": "2026-07-09T00:00+08:00",
                                  "until": "2026-07-30T00:00+08:00",
                                  "input": 2.5, "output": 15.0 } ] }
```

- **One benchmark: Singapore time.** Every boundary is an ISO instant ending `+08:00`. `validate_card` rejects anything else, and `instant()` refuses a time with no offset, so a boundary can never be read as UTC by accident. Event timestamps are UTC; the comparison is between instants, so no one has to convert.
- `from` is inclusive, `until` exclusive, and a version's `until` is the next version's `from`. No gaps, no overlaps — `validate_card` checks it.
- Each history entry overrides only the fields it lists (`input`, `output`, `cache_read_mult`, ...); tier, vendor and window carry over.
- **Vendors publish dates, not hours.** A date-only source is recorded as 00:00 SGT on that date with `"precision": "date"`. That is good to about a day, which is below what a dollar estimate resolves anyway. Write the real instant, and drop `precision`, when a source gives one.
- **An introductory or promotional rate with no published successor** gets `recheck_after` (the earliest it might end). It keeps pricing — there is nothing better to use, and inventing the successor would be worse — and `review_due` reports it once the date passes. `doctor` shows it as a failed check, so it is seen. Example: `gpt-5.6-sol`'s $4/$20 is "available at least through November 21, 2026".
- The first history entry's `from` is the model's launch and also applies to anything earlier.

What changed and what did not, as of 2026-10-31 (from each vendor's own release notes and pricing page): GPT-5.6 launched 2026-07-09; Terra and Luna were cut on 2026-07-30; Sol went to the promotional $4/$20 on 2026-08-21; Claude Sonnet 5.5's cache reads went from 0.1× to 0.05× on 2026-10-07. Opus 5.5 and Fable 5.1 launched at today's price. `claude-sonnet-5`'s introductory $2/$10 was made permanent on 2026-08-10 and the planned $3/$15 never took effect, so it has no history. `gpt-5.5` has been $5/$30 since its 2026-04-23 launch — this card carried $1.25/$10 until 2026-10-31, which was a plain error, not a change.

The dashboard's **Prices** page draws this history, per lab and per model line: see [Price-Trends](Price-Trends.md).

**Not modelled:** what a *gateway* (LiteLLM, OpenRouter, a company's own) bills, which can differ from the vendor's list and take effect at its own time; the vendor's long-prompt tiers (GPT-5.6 above 272K input, Haiku 5.5 above 100K) and Fast mode, which a transcript does not record.

## Maintaining the price list

`pricing.json` is meant to be edited. On update, set `_verified_on` — the dashboard footer surfaces that date so a stale model is visible rather than silently wrong. `_verified_on` is the *oldest* check; `_verified_by_vendor` records the vendors that were checked more recently, so adding Anthropic's rates does not make Moonshot's look fresh.

Verified 2026-10-31 against Anthropic's and OpenAI's own pricing pages and release notes; every other vendor as of `_verified_on`.

## Confidence levels

| Level | When |
|---|---|
| `high` | Exact token counts; ratios and shares derived only from counts |
| `medium` | Cost-derived findings using a current price list, or a behavioural proxy |
| `low` | Unknown model priced from the fallback, or a saving estimate with an assumed delegable share |

Saving estimates are scaled from the observed window to a 30-day rate and are deliberately conservative — e.g. `premium-tier-light-turns` assumes only 40% of light turns are genuinely delegable.
