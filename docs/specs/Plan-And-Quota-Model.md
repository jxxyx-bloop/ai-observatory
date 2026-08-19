# Spec — plan and quota model

## The problem this exists to fix

Every tracker in this category headlines an "estimated cost". For a developer on
a flat monthly plan that number is not a bill, a budget, or a warning. It is a
**shadow price** — what the same work would have cost on metered API — and its
only useful role is to be divided by what they actually paid.

This matters more here than anywhere else. Coding plans dominate the target
market: GLM Coding Lite at $18/month, Pro at $80, Max at $168; Qwen's
ModelStudio Coding Plan around $50; Claude Pro at $20. Against a regional senior
contract rate of roughly $85–130/day, the difference between an $18 plan and a
$200 seat is a real decision, made monthly, with no data behind it.

## Two questions a subscriber actually has

1. **Was this worth it?** → plan-value multiple.
2. **How much is left?** → quota headroom.

Neither is answerable from a token total, and neither is answered by any
competing tool.

## Plan value

```python
pricing.plan_value(observed_usd, plan_id, days) -> {
  "plan", "label", "price_usd_month",
  "api_equivalent_usd_month",   # observed, scaled to 30 days
  "multiple",                   # api_equivalent / price
  "verdict"                     # under-used | fair | excellent
}
```

| Multiple | Verdict | What the tool says |
|---|---|---|
| < 1.0 | `under-used` | You are buying headroom you never use. Drop a tier, or move work onto the plan deliberately — it is already paid for. |
| 1.0 – 3.0 | `fair` | Reasonable. |
| > 3.0 | `excellent` | The plan is returning several times its price. |

The `under-used` branch is deliberate. A tool that only ever congratulates you
is not a mirror, and "you are paying for air" is the single most valuable thing
this file can say to someone on a tight budget.

Detector: `insights.plan_value_realised`, active only when `settings.plan` is
set to something other than `"none"`.

## Quota units are not tokens

This is the part every tracker gets structurally wrong. Vendors meter in
different units on different clocks, and several publish no number at all.

| Vendor | Unit | Windows |
|---|---|---|
| Anthropic (Pro / Max) | prompts | rolling 5h **and** weekly; amounts unpublished |
| Z.ai (GLM Coding) | credits | weekly (10,000 on Lite; 6× on Pro; 14× on Max), plus ~400 prompts per 5h on Pro |
| Alibaba (ModelStudio) | credits | monthly |
| Moonshot, MiniMax | prompts | rolling 5h |
| GitHub Copilot | premium requests | monthly (300 on Pro) |
| Metered API | none | — |

`plans.json` models `unit`, and a list of `windows` each with `kind`
(`rolling` | `calendar`), a length, and an `amount` that may be `null`.

### When a vendor publishes nothing

Fall back to a **self-calibrated p90** of the user's own history in that window
— the technique
[Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor)
uses, and worth copying outright. It answers "am I unusually heavy this week
*for me*", which is the question anyway, and it degrades honestly: with two
weeks of history it says so rather than inventing a limit.

## Currency

Thirteen currencies in `plans.json → currencies`, including IDR, VND, THB, PHP,
MYR, SGD, CNY, TWD, HKD, INR, JPY and KRW. `settings.currency` selects one;
every figure on the dashboard converts.

Rates are **indicative and hand-maintained**. They are a display lens, not
accounting — most vendors settle in USD. The point of showing IDR is not
precision; it is that `$412/month` means something very different in Jakarta
than in San Francisco.

### The local-rate framing

Each currency carries an optional `daily_dev_rate_usd` — a coarse median local
contract rate — used for exactly one sentence:

> About Rp 6,674,400 a month ($412). That is roughly 4.6 days of a median local
> contract rate.

A conversion is a feature. A comparison against local opportunity cost is an
argument, and arguments are what get shared. It is explicitly a
conversation-starter, not a salary benchmark, and the detector says so.

## Known limits

- **Plan prices vary by region and promotion**, and annual billing changes them
  again. `price_usd_month_annual` is carried where known.
- **Multi-plan users are not yet modelled.** `settings.plan` is a single id. The
  multi-vendor pragmatist — three subscriptions, no idea which is carrying its
  weight — is the most interesting user here and the least well served today.
  Per-vendor plan attribution is on the roadmap.
- **Quota consumption is inferred from turns**, not read from a vendor API.
  Where a vendor exposes a live limit (Claude Code's statusline `rate_limits`,
  for one), reading it directly is strictly better and is on the roadmap.
- **Credits are not tokens.** A GLM "credit" has a vendor-defined conversion we
  do not model. Credit-based headroom is currently an estimate flagged as such.

## See also

- [Cost-Estimation](Cost-Estimation.md)
- [ADR-012](../adr/ADR-012-Rate-Card-As-Config.md)
- [03-SEA-CHINA-PRODUCT-THESIS](../strategy/03-SEA-CHINA-PRODUCT-THESIS.md)
