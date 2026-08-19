# Future Ideas

Parking lot. Nothing here is committed. Each entry names what would make it worth building — an idea without a trigger stays an idea.

## High value, blocked on a signal

**Outcome attribution.** The project's biggest gap (PRD 03). Correlate sessions with git activity in the same window — commits, lines changed, PRs opened — to distinguish "read a lot and produced" from "read a lot and circled". Git is local, passive, and already on the machine, so it fits Principle 2 without new instrumentation. *Build when:* Phase 2's exit condition is met, so there is a habit to improve rather than a metric to admire.

**Before/after verification.** Diff two digests to answer "did the change I made actually work". Turns every finding from advice into a testable claim. *Build when:* at least one finding has been acted on.

**Trend direction per finding.** Is this pattern improving or degrading? A finding with an arrow is far more actionable than a snapshot. *Build when:* ~3 months of history exists, so a trend is signal rather than noise.

## Plausible, unproven

**Distinct-read counter.** A per-session count of *distinct* read targets, computed at collection time and stored as an integer — never the paths themselves. Would enable "you re-read the same thing repeatedly" without violating ADR-006. Needs its own ADR, because it derives from tool arguments even though it does not store them.

**Session-shape classification.** Cluster sessions into recognisable shapes (deep build, exploration, quick fix, abandoned). Useful only if the labels change a decision, rather than being a nicer way to say the same thing.

**Effort-level effectiveness.** Compare output-per-token across effort levels for similar work, to find where high effort is not earning its cost. Currently blocked: `effort` is `null` on most collected turns, so there is nothing to compare.

**Second provider.** Codex, Cursor, ChatGPT export, Gemini — the real test of ADR-003. Gated on a passive local source existing (Principle 2), not on wanting the breadth.

## Interesting, probably not

**Quota forecasting.** Needs quota state the transcripts do not carry. Viable only if a provider exposes it locally.

**Per-task model routing suggestions.** Requires knowing what the task *was*, which means content (ADR-006). The tier-level finding already captures most of the value.

**Threshold notifications.** Turns a weekly reflective habit into an interrupt stream. The value of this tool is that it is read deliberately.

**Publishing the dashboard.** Rejected in ADR-002. Listed only so the decision is not silently reopened.

## Rejected outright

- **Productivity scoring / leaderboards** — measures the wrong thing and would make the data adversarial to its owner.
- **Storing prompt or completion text** — ADR-006, not up for revision.
- **A model call in the collect path** — ADR-004; it would undo the property the product rests on.
