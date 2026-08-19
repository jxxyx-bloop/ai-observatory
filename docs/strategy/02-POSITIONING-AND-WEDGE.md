# Positioning and wedge

## The one-line difference

> Every other tracker tells you **how much** you spent.
> This one tells you **what to change**, priced in **your** currency, against
> **your** plan, on **your** vendor's clock — and then shows you how developers
> like you are doing it better.

## Positioning statement

**For** developers and small teams in Southeast Asia and China who run AI coding
agents daily on a tight budget,
**who** cannot tell whether their AI spend is going anywhere useful,
**the AI Observatory** is a local-first usage analyser
**that** turns their own transcripts into ranked, evidence-backed changes with a
number attached,
**unlike** ccusage, tokscale and TokenTracker, which report volume and leave
interpretation to the reader,
**because** it models the economics those users actually face — flat monthly
plans, time-priced tokens, per-vendor cache rules, and a currency that is not
the dollar.

## The wedge, in order

A wedge is not a feature list; it is the order in which you earn the right to
the next thing.

### 1. Be an odometer as good as theirs (table stakes)

Local-first, one command, no account, broad tool support, a good screenshot.
If we lose here nothing else is read. This is why the engine is stdlib-only
Python with zero dependencies and why `observe.py demo` exists — a stranger can
see the whole product in one command on a machine that has never run an AI
coding tool.

### 2. Be the only *coach* (the differentiator)

Fifteen deterministic detectors, each producing a finding with evidence, an
action, a confidence level, and — where defensible — a monthly value. A
materiality gate demotes anything worth less than $15/month so the top of the
list always means something. Healthy usage is reported as healthy.

The rule that makes this credible: **the tool never invents a problem to look
useful.** A tracker that always finds something wrong is a tracker you stop
believing, and belief is the entire product.

### 3. Be right about money in a way they cannot be (the moat)

Three things the incumbents get wrong for our users, all of them arithmetic
rather than opinion:

- **Peak/off-peak.** DeepSeek's peak windows are 01:00–04:00 and 06:00–10:00
  UTC; Z.ai's GLM peaks 14:00–18:00 UTC+8 on weekdays only. We price each turn
  at the rate in force when it ran, carry the off-peak counterfactual through
  the fact cube, and quote the premium as arithmetic on the user's own tokens.
- **Per-vendor cache economics.** The 0.1× cache-hit discount is an Anthropic
  convention. Moonshot's Kimi models sit anywhere from 0.074× to 0.2×. Cache is
  where most of the money is, so getting the multiplier wrong misprices the most
  important metric.
- **Plan value.** The headline for a subscriber is not "$412 spent" but
  "$18 paid, $412 of API-equivalent work, 23× return" — or, when the number goes
  the other way, "you are paying for headroom you never use; drop a tier."

None of this is hard. It is simply invisible to anyone who has never bought
tokens outside the US.

### 4. Be a community they can safely join (the flywheel)

Cohort comparison with a real privacy mechanism, not a promise: bucketed metrics
computed on-device, a k-anonymity floor enforced at write time, two-salt
unlinkability between the consent record and the fact rows, and an allow-listed
payload short enough to read in full before you tick the box. See
[Community-Share-Protocol](../specs/Community-Share-Protocol.md).

The comparison people want — *"how do I compare to other solo developers in
Indonesia on a GLM plan"* — is exactly the one no vendor dashboard can answer,
because no vendor sees across vendors.

## The strategic inversion: rank efficiency, not consumption

This is the single most important product decision in the repo, so it is stated
plainly.

| | Consumption leaderboard (tokscale, viberank) | Efficiency leaderboard (ours) |
|---|---|---|
| Top of the board | Whoever spent the most | Whoever wastes the least |
| Fair across budgets? | No — rank tracks wallet | Yes — rank tracks skill |
| Reason to return | None; your rank is your budget | Every improvement moves you |
| Aligned with the user? | No; it celebrates waste | Yes; it is why they installed it |
| Works in a price-sensitive market? | No | Yes — it is the point |
| Gameable by burning tokens? | That *is* the game | No; burning tokens lowers your rank |

Concretely, the ranked metrics are **cache reuse %**, **tokens per merged
change**, **cost per active hour**, **peak-window discipline**, and
**plan-value multiple** — never total spend, which is displayed but never
ranked.

There is a second-order effect worth naming: an efficiency board is
*defensible against the obvious counter-launch*. If tokscale adds an efficiency
tab tomorrow, it sits inside a product whose identity is "trillions of tokens
tracked." The metric and the brand fight each other. Ours do not.

## What we are deliberately not

- **Not a proxy or gateway.** We never sit in the request path. LiteLLM,
  Helicone and Langfuse own that; being in the path means being blamed for
  latency, and it is a hard sell to anyone whose employer's code is involved.
- **Not a team surveillance tool.** No manager dashboard, no per-employee
  ranking. This is the fastest way to lose a developer audience, and every
  request for it should be refused on the record.
- **Not a billing reconciliation tool.** Token counts are exact; dollars are a
  lens. Anyone who needs an invoice should read the vendor's.
- **Not a chat-usage tracker.** claude.ai and ChatGPT web usage leave no local
  token record. It cannot be measured, and pretending otherwise is the kind of
  small lie that costs the credibility everything else depends on.

## The name and the frame

*Observatory*, not *monitor* or *tracker*. A monitor is a gauge you glance at; an
observatory is where you go to understand something. The category the incumbents
occupy is "monitor". We are not trying to win it — we are trying to make it
look like the shallow end.

## See also

- [01-COMPETITIVE-TEARDOWN.md](01-COMPETITIVE-TEARDOWN.md)
- [03-SEA-CHINA-PRODUCT-THESIS.md](03-SEA-CHINA-PRODUCT-THESIS.md)
- [04-GROWTH-FLYWHEEL.md](04-GROWTH-FLYWHEEL.md)
