# PRD 02 — Analytics Dashboard

**Status:** v1 shipped 2026-08-02

## Vision

Turn raw telemetry into actionable understanding — a page that tells you what to change before it shows you a chart.

## Product philosophy

- **Insight before charts.** The first full section is "What to change". Charts are evidence for the findings, not the point of the page.
- **Default to the current story.** The page opens on the whole observed window with findings already ranked; nothing to configure before it is useful.
- **Make uncertainty visible.** Token counts are exact; dollar figures are labelled estimates, with the price-list verification date in the footer.
- **Concise over complete.** Every number has to earn its place. A metric nobody would act on is removed.

## Functional requirements

| # | Requirement | v1 status |
|---|---|---|
| F1 | Daily view of activity | ✅ column chart over active days |
| F2 | Usage by model, repository, in-repo project, tool, subagent, effort, hour | ✅ seven breakdowns |
| F2b | Date-range filter and provider / lane / repository slicers, re-aggregated client-side | ✅ 2026-08-03 |
| F3 | Session history with per-session shape | ✅ turns, output, cost, writes/reads, peak context |
| F4 | Estimated costs with confidence | ✅ labelled; methodology in footer |
| F5 | Findings surfaced above the charts | ✅ severity-ordered, with evidence and action |
| F6 | Self-contained, offline artefact | ✅ 80 KB, zero external requests (verified) |
| F7 | Light and dark, desktop and mobile | ✅ verified 375 px → desktop, both schemes |
| F8 | Weekly and monthly views | ⛔ not in v1 |
| F9 | Search and filters | ⛔ deliberately deferred — see below |

## Architectural constraints

- Reads the digest only, never the event store (ADR-005). A metric not in the digest goes into `analyze.py` first, so text and HTML can never disagree.
- No provider-specific logic.
- **No CDN, no external fonts, no third-party scripts, no analytics, no tracking pixels.** Verified zero external requests.
- Charts are hand-built inline SVG, labels in their own column outside the plot, so no data can cause overflow or collision.
- Wide content scrolls inside its own container; the body never scrolls horizontally.
- `no-referrer` and `noindex` meta tags set — local today, safe if ever served.

## Decision records

- The dashboard is **read-only**. Fixing a number means fixing the artefact upstream, never the page.
- Costs may be estimated and must display that they are estimates.
- **Search and filters were deliberately dropped from v1.** They are the reflex dashboard feature, but this page is read start-to-finish weekly, not interrogated. Filters would add JavaScript, state, and surface area for a need the single-user case has not shown. Revisit if a "show me only X" question is genuinely asked twice.
- **No deployment target.** Local `file://` only (ADR-002).

## Future evolution

Weekly/monthly rollups · a sparkline per finding showing the trend behind it · diffing two windows to see whether an action actually worked · custom dashboards, team analytics, and scheduled reports (all out of scope while the audience is one).
