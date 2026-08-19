# PRD 03 — AI Insights Engine

**Status:** v1 shipped 2026-08-02

## Vision

Explain AI usage and recommend better decisions — the layer that turns measurement into a changed habit.

## Product philosophy

- **Explain, don't just measure.** A number without an interpretation puts the analytical work back on the reader.
- **Recommendations over raw metrics.** Every finding names an action.
- **Preserve user control.** The engine recommends; it never changes a setting or acts on its own.
- **Credibility over apparent usefulness.** "This is healthy" is a correct answer. Manufacturing a problem to justify the tool destroys the only thing that makes it worth reading (ADR-007).

## Functional requirements

| # | Requirement | v1 status |
|---|---|---|
| F1 | Detect wasteful usage patterns | ✅ 11 detectors — `specs/Insight-Catalogue.md` |
| F2 | Every recommendation references its evidence | ✅ `evidence` object on every finding |
| F3 | Rank so the top of the list is trustworthy | ✅ severity + materiality gate (ADR-007) |
| F4 | Quantify what a fix is worth | ✅ `est_monthly_saving_usd`, scaled from the window |
| F5 | State confidence | ✅ on every finding |
| F6 | Highlight where investment concentrates | ✅ `where-the-time-goes` |
| F7 | Summarise for a model to reason over cheaply | ✅ findings ride in the ~60 KB digest |
| F8 | Forecast quota exhaustion | ⛔ transcripts carry no quota or limit data |
| F9 | Recommend account switching | ⛔ accounts not distinguishable in the source |
| F10 | Weekly insight summary | ⛔ needs the weekly rollup from PRD 02 |

## Architectural constraints

- Consumes the digest only; never re-reads raw events.
- Provider agnostic — a detector must not name a provider.
- **Deterministic, not model-generated.** Rules in `insights.py`, thresholds in a single `T` dict, so recalibration is one reviewable diff (ADR-007).
- A detector that raises is skipped rather than breaking the report.
- Free to run, so findings regenerate on every report instead of being rationed.

## Decision records

- Insight generation is **separate from collection** — a broken detector cannot lose data, and a collector change cannot silently alter a finding.
- Immaterial findings are **demoted, not deleted** (ADR-007).
- Value proxies are labelled as proxies. Writes-to-reads is not "value"; it is the closest signal available without storing content (ADR-006).

## The known gap

There is no trustworthy signal for **whether a session produced something worth its cost**. The v1 proxy — writes-to-reads plus session shape — conflates "read a lot and thought" with "read a lot and circled". Closing this is the highest-value open problem: see [Known-Limitations](../context/Known-Limitations.md) → the value-attribution gap.

## Future evolution

Trend detection · before/after comparison so an action can be verified · outcome attribution via git activity in the same window · agent-generated optimisation plans grounded in the digest.
