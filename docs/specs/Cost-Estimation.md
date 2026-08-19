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

## Maintaining the price list

`pricing.json` is meant to be edited. On update, set `_verified_on` — the dashboard footer surfaces that date so a stale model is visible rather than silently wrong.

Verified 2026-08-02 against the Anthropic public price list. Note `claude-sonnet-5` carries an introductory rate through 2026-08-31; the entry records both, and the reverted rate must be applied after that date.

## Confidence levels

| Level | When |
|---|---|
| `high` | Exact token counts; ratios and shares derived only from counts |
| `medium` | Cost-derived findings using a current price list, or a behavioural proxy |
| `low` | Unknown model priced from the fallback, or a saving estimate with an assumed delegable share |

Saving estimates are scaled from the observed window to a 30-day rate and are deliberately conservative — e.g. `premium-tier-light-turns` assumes only 40% of light turns are genuinely delegable.
