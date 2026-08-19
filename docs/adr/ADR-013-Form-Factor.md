# ADR-013 — Form factor: local CLI + self-contained HTML, with an optional hosted community layer

**Status:** accepted · **Date:** 2026-08-19

## Context

The form factor was explicitly left open: desktop app, or a local script that
publishes to a personal dashboard? The competitive field has taken both routes,
so both are viable and the choice is about sequencing rather than correctness.

| Shape | Examples | What it buys | What it costs |
|---|---|---|---|
| Terminal CLI report | ccusage, Claude-Code-Usage-Monitor | Trivial install (`npx`), scriptable, CI-friendly | No screenshot worth sharing; findings are hard to read as text |
| Native desktop app | TokenTracker, token-monitor, ai-token-monitor | Menu-bar presence, widgets, ambient glanceability, retention | Code signing per OS, an update channel, a release pipeline, a CI matrix — and a rewrite in a GUI stack |
| Local web dashboard | sniffly, aiusage | Rich visuals, no signing, cross-platform for free | Needs a local server running |
| Hosted dashboard | viberank, tokscale, WakaTime | Comparison, sharing, network effects | Requires accounts, a privacy story, and an operator |

## Decision

**Ship all four, in this order, from one engine.**

1. **CLI** — `observe.py sync | digest | report | insights | demo | share`.
   Stdlib-only Python 3, zero dependencies, zero network.
2. **A single self-contained HTML file** — `dist/observatory.html`, ~230 KB, no
   server, no CDN, no fonts, no analytics, zero external requests. Opens from
   the filesystem. This is the screenshot, and the screenshot is the pitch.
3. **An optional hosted community layer** — accounts, cohorts, embeds. Off by
   default, self-hostable.
4. **A native shell later, if retention data asks for it** — a thin wrapper
   around the same HTML, not a rewrite.

The load-bearing part is that (2) is a *file*, not a *server*. sniffly and
aiusage both need a localhost process running to show a dashboard; ours is an
artefact you can email to yourself, open on a phone, or attach to a PR.

## Why not desktop-first

It is the most impressive shape and the most expensive one. Native apps demand
code signing on macOS and Windows, an auto-update channel, a per-OS CI matrix,
and a GUI framework — before a single user has confirmed that the *findings* are
worth reading. TokenTracker and token-monitor have both done this well and both
have ~1.4k stars; ccusage, which is a terminal command, has ~18k. Packaging is
not what wins this category.

The genuine advantage of a desktop app is **ambient presence** — a menu-bar
number you see without deciding to look, which is a retention mechanism. That
matters, and it is why a native shell stays on the roadmap rather than being
refused. But it is a wrapper around a working product, not a substitute for one.

## Why not hosted-first

A hosted dashboard requires an account before it shows anything, which forfeits
the single strongest line in this category's README. It also makes the privacy
question load-bearing on day one, before the mechanism has been road-tested and
before there are enough participants to meet a cohort floor of five. A
leaderboard with fifty people is embarrassing; one with fifty people and an
untested consent flow is a liability.

## Why one engine, not three codebases

The source project ended up with three surfaces — a local engine, a rendered
report, and a separate company app — sharing "a lineage, not a codebase," which
meant a pricing change had to be made twice and nothing enforced it. That is a
real, recurring tax.

Here, `analyze.py` and `pricing.py` are the only places a metric is defined.
`render.py` may not compute a metric the digest does not already carry; the
browser re-aggregates the fact cube but never derives a new number; and the
community server re-prices nothing because it receives bucket indices it cannot
invert. One definition, three renderings.

## Consequences

- **Good.** Install is one command with no runtime to add — Python 3 ships on
  macOS and every Linux. The dashboard is a portable artefact. Nothing to
  operate until the community layer exists. A native shell later costs a
  wrapper, not a rewrite.
- **Bad.** No ambient presence until (4). No live/streaming view — this is a
  batch tool that runs on a schedule, and the "watch your tokens tick up" appeal
  of Claude-Code-Usage-Monitor is not available.
- **Accepted.** Windows users need Python installed; `uvx` and a packaged
  binary are the mitigations, on the roadmap.
- **Accepted.** A 230 KB HTML file is large for a single page. It is the price
  of zero external requests, and it is small next to the transcripts it
  summarises.

## Revisit when

Retention data exists and shows that people who install do not come back in
week two *despite* useful findings. That would be evidence that ambient presence
is the missing loop, and would justify the packaging cost of (4).

## See also

- [ADR-011 — the community layer](ADR-011-Community-Layer.md)
- [Auth](../specs/Auth.md)
- [04-GROWTH-FLYWHEEL](../strategy/04-GROWTH-FLYWHEEL.md)
