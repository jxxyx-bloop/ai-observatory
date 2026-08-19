# ADR-012 — Price models from configuration, and model peak/off-peak windows first-class

**Status:** accepted · **Date:** 2026-08-19 · **Extends:** [ADR-003](ADR-003-Provider-Abstraction.md)

## Context

Two things about pricing turned out to be structurally different from what the
incumbents assume.

**First, vendors reprice constantly and sometimes change the billing *shape*.**
DeepSeek moved V4 to peak/off-peak billing on 2026-08-16: peak 01:00–04:00 and
06:00–10:00 UTC, half rate everywhere else. Z.ai's GLM peaks 14:00–18:00 UTC+8
on weekdays only. Kimi K2.6 prices cache hits at a floor of $0.07/M against a
$0.95/M input rate — about 0.074×, not the 0.1× Anthropic convention every
tracker hardcodes.

**Second, a flat rate is simply wrong for those vendors.** Multiplying tokens by
one number misprices a DeepSeek user by up to 2×, and — worse — hides the
largest lever they have. For a developer in UTC+7 or +8, ordinary afternoon
working hours land inside DeepSeek's 06:00–10:00 UTC window. They are paying
peak rates by accident, every day, and no tool tells them.

ccusage handles the staleness half by leaning on LiteLLM's price database. That
is a good answer to *drift* and no answer at all to *shape*: a flat per-token
table cannot express a schedule.

## Decision

### 1. The rate card is data, not code

`pricing.json` carries every model, its tier, its vendor, an optional
`cache_read_mult`, and an optional `window`. `plans.json` carries subscription
prices, quota units and reset windows, plus the currency table. Neither is
compiled in; correcting one is a one-line PR.

This is deliberately a **contribution surface**. Prices go stale faster than any
maintainer can track, and the only durable fix is enough contributors that
correction outpaces decay. So "fix a price" is designed to be the easiest
possible PR in the repo: edit a line, move `_verified_on`, cite the vendor page.

### 2. Peak/off-peak windows are first-class

A `windows` block declares schedules in **UTC**, with an optional weekday
restriction and an off-peak multiplier. Vendor-local schedules are converted to
UTC in the config, so no code ever has to know a timezone.

Each turn resolves to one of three phases:

- `peak` — inside a published peak window
- `off-peak` — outside one, on a vendor that publishes a schedule
- `flat` — the vendor does not price by time

**`flat` is not `off-peak`, and conflating them would be a lie.** A user on
Anthropic and OpenAI only has nothing to shift; a dashboard implying they had
scheduled well would be inventing a compliment.

### 3. The counterfactual rides in the fact cube

`cost_floor_micro` — what the same tokens would have cost at that vendor's
off-peak rate — is computed per turn and stored alongside `cost_micro`. The
difference across any slice is exactly the money on the table, so the dashboard
can show a premium for an arbitrary date range without knowing a rate card, and
the detector's number is arithmetic on the user's own tokens rather than a
projection.

### 4. Cost is a lens; the plan is the bill

For a user on a flat monthly plan the dollar estimate is a **shadow price** —
what the same work would have cost metered. `plans.json` plus
`pricing.plan_value()` turn it into the number that matters: what the plan
returned, and whether it is worth its tier. When the multiple falls below 1.0
the tool says "downgrade", because a mirror that only ever congratulates you is
not a mirror.

## Options considered

| Option | Verdict |
|---|---|
| Depend on LiteLLM's price DB (ccusage's approach) | Rejected. Adds a dependency to a stdlib-only engine, and cannot express windows, plan prices or quota units — the three things this product needs most. Worth revisiting as an *import* to seed `pricing.json`. |
| Hardcode rates in Python | Rejected. Makes the single most common correction a code change, which is exactly backwards for the contribution loop. |
| **Config file with a window vocabulary** ← chosen | Prices, plans and schedules are all one-line edits. Cost: a config format to document and validate. |
| Fetch live prices at runtime | Rejected. Breaks the zero-network promise, and a tracker that phones home to price your tokens has given up the thing that makes it trustworthy. |

## Trade-offs accepted

1. **Rates will still go stale**, just more cheaply fixed. `_verified_on` is
   shown in the report footer so a reader can judge for themselves.
2. **Windows are approximated to whole hours.** DeepSeek's legacy V3/R1 window
   ran 16:30–00:30 UTC; the config expresses whole hours, so a half-hour edge is
   mispriced for turns landing in it. The error is bounded and small, and the
   alternative is a minutes-resolution schedule language nobody needs yet.
3. **No account-level discounts, committed-spend tiers, or batch-API rates.**
   The card is list price. Anyone on a negotiated rate should edit their own
   copy, and the file is designed to make that trivial.
4. **`price_epoch` is bumped by hand.** Deriving it from file contents would
   make every whitespace change rewrite history.

## See also

- [Cost-Estimation](../specs/Cost-Estimation.md)
- [Peak-Off-Peak-Pricing](../specs/Peak-Off-Peak-Pricing.md)
- [Plan-And-Quota-Model](../specs/Plan-And-Quota-Model.md)
- [03-SEA-CHINA-PRODUCT-THESIS](../strategy/03-SEA-CHINA-PRODUCT-THESIS.md)
