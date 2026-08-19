# ADR-005 — A pre-aggregated digest tier between store and consumer

**Status:** accepted · **Date:** 2026-08-02

## Context

The point of this tool is not the chart — it is being able to ask "what should I change about how I use AI?" and get a grounded answer. In practice that question gets asked of a model.

If the model has to read the event store to answer it, the question costs megabytes of context every time, which makes the most valuable use of the tool its most expensive one. That is the same trap ADR-004 avoids at collection time, reappearing at analysis time.

Measured: source 241 MB → store 5.7 MB → digest 61 KB. The digest is ~4,000× smaller than the source and holds every number the dashboard and the insight rules need.

## Decision

`analyze.py` makes one pass over the store and writes `data/digest.json` (~60 KB): totals, per-day, per-model, per-workspace, per-effort, per-tool, per-subagent, per-hour, and a per-session rollup — plus the generated findings.

Every consumer reads the digest, never the store. That includes the HTML renderer, the text output, and any model asked to reason about usage.

## Consequences

**Good**
- Model-assisted analysis costs a few thousand tokens instead of a few million. This is what makes the deepest layer of the product affordable to use often.
- The HTML and text surfaces cannot disagree — both read the same numbers.
- The digest is a stable contract, so the renderer does not break when the store schema gains a field.
- Small enough to commit, diff, or archive as a monthly snapshot if that ever becomes useful.

**Bad / accepted**
- Any question the digest does not pre-compute requires an `analyze.py` change and a rebuild. Accepted: rebuild is 3.5 s.
- Per-session rows are emitted for all sessions; at thousands of sessions the digest will need a top-N cut with the tail summarised. Not a problem at 67.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Query the store on demand | Every consumer re-implements aggregation; text and HTML drift apart |
| Let the model read raw NDJSON | Defeats the purpose — the highest-value question becomes the highest-cost one |
| Compute in the browser from inlined events | Would inline 5.7 MB into the page and duplicate the aggregation logic in JavaScript |

## Revisit when

The digest exceeds ~250 KB (then cut the session tail), or a genuinely ad-hoc query need emerges that pre-aggregation cannot serve — which is also the trigger for reconsidering ADR-001.
