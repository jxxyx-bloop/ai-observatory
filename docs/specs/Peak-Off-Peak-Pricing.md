# Spec — peak / off-peak pricing

Several vendors bill tokens like electricity: the same request costs more at
some hours than others. No other open-source token tracker models this, which
means their cost figure for those vendors is wrong by up to 2× and — more
importantly — hides the largest single lever those users have.

Reasoning in [ADR-012](../adr/ADR-012-Rate-Card-As-Config.md). This is the
mechanism.

## Known schedules

Verified 2026-08-19. **These change.** Correcting one is a one-line PR.

| Vendor | Peak window (UTC) | Days | Off-peak rate | Notes |
|---|---|---|---|---|
| DeepSeek (V4 Flash / Pro) | 01:00–04:00 and 06:00–10:00 | every day | 50% of peak | Effective 2026-08-16. Listed rates are **peak**. |
| DeepSeek (V3 / R1, legacy) | outside 16:30–00:30 | every day | 50% of peak | Superseded generation; kept for historical events. Approximated to whole hours. |
| Z.ai / GLM | 06:00–10:00 (= 14:00–18:00 UTC+8) | Mon–Fri | 50% of peak | Weekends are entirely off-peak. |
| Anthropic, OpenAI, Google, Moonshot, Alibaba | — | — | — | Flat. Nothing to shift. |

## Why this matters most in UTC+7 to +9

06:00–10:00 UTC is 13:00–17:00 in Jakarta and Bangkok, 14:00–18:00 in Singapore,
Shanghai and Manila. That is the middle of the working afternoon.

A developer in this region using DeepSeek is paying peak rates for most of their
productive day, by accident, and no vendor dashboard tells them. The interactive
part of that work genuinely has to happen then. The *batch* part — test
generation, migrations, doc sweeps, bulk refactors, anything the developer is
not watching — does not, and moving it is free.

## The three phases

| Phase | Meaning |
|---|---|
| `peak` | Inside a published peak window for a vendor that publishes one. |
| `off-peak` | Outside one, on a vendor that publishes a schedule. |
| `flat` | The vendor does not price by time. |

**`flat` is not `off-peak`.** A user on Anthropic and OpenAI only has nothing to
shift, and a dashboard that reported them as "0% peak" would be paying them a
compliment they did not earn. The peak panel hides itself entirely when nothing
in range is time-priced.

## Configuration

```json
"windows": {
  "glm-coding": {
    "vendor": "zhipu",
    "peak_utc": [[6, 10]],
    "days": [1, 2, 3, 4, 5],
    "off_peak_mult": 0.5
  }
}
```

- `peak_utc` — list of `[start_hour, end_hour)` in **UTC**. Vendor-local
  schedules are converted here, so no code ever has to know a timezone.
- `days` — optional ISO weekday restriction (1 = Monday). Absent means every day.
- `off_peak_mult` — scales the listed (peak) rate outside those hours.

A model opts in with `"window": "glm-coding"`. A model with no `window` is flat.

## Computation

`pricing.window_phase(model, ts, pricing)` resolves the phase from the event's
own UTC timestamp. `pricing.cost_of()` applies the multiplier to input and
output rates alike.

`pricing.counterfactual_cost(ev, pricing, "off-peak")` gives what the same turn
would have cost had it run off-peak, and returns the unmodified cost for a
flat-priced model. That number is stored per turn as `cost_floor_micro` in the
fact cube, so:

```
premium over any slice = Σ cost_micro − Σ cost_floor_micro
```

is a subtraction the browser can do for an arbitrary date range without knowing
a rate card. The saving quoted by the detector is arithmetic on the user's own
tokens, not a model of what they might do.

## Detector

`insights.peak_window_arbitrage` fires in one of three forms:

| Id | When | Severity |
|---|---|---|
| `peak-window-arbitrage` | peak share ≥ 35% **and** premium ≥ $5/month | high |
| `peak-window-immaterial` | peak share ≥ 35% but premium < $5/month | low |
| `peak-window-healthy` | peak share < 35% | info |

The middle case exists because a headline of "already landing off-peak" over a
number reading 55% is a tool contradicting itself, and a tool that contradicts
itself gets closed.

## Known limits

- **Whole-hour resolution.** DeepSeek's legacy window ran to :30; turns landing
  in that half hour are mispriced. Bounded and small; a minutes-resolution
  schedule language is not yet worth its complexity.
- **No timezone-of-record.** Schedules are evaluated in UTC from the event's own
  stamp. Correct, but a user reading the panel has to translate to know *which
  hours of their day* to move — the working-hours heatmap next to it is the
  companion for that.
- **List price only.** Negotiated rates, committed-spend tiers and batch APIs are
  not modelled. Edit your own copy of `pricing.json`.

## See also

- [Cost-Estimation](Cost-Estimation.md)
- [ADR-012](../adr/ADR-012-Rate-Card-As-Config.md)
- [03-SEA-CHINA-PRODUCT-THESIS](../strategy/03-SEA-CHINA-PRODUCT-THESIS.md)
