# Architecture

## The pipeline

```
Provider files          Collectors        Store            Aggregate       Insight        Surface
(already on disk)       (read-only)       (NDJSON)         (digest)        (rules)        (HTML / text)

~/.claude/projects/  →  claude_code.py →  data/         →  analyze.py   →  insights.py →  render.py
  **/*.jsonl            codex.py          events-        (single pass)     (detectors)     observatory.html
~/.codex/sessions/      (+ future:        YYYY-MM.ndjson  + fact cube                      + assets/app.js
  **/rollout-*.jsonl     cursor, …)        6.5 MB           digest.json ~210 KB            or `observe.py insights`
                              ↑
                         paths.py + topology.json
                         (path → repo / surface label, ADR-008)
```

Collectors are provider-specific. Everything downstream consumes only normalized events.

The last hop is split in two. `render.py` assembles `engine/assets/{page.html,app.css,app.js}`
into one self-contained file; `app.js` re-aggregates the digest's fact cube in the
browser so a date range or a slicer costs nothing to change. It re-aggregates — it
never computes a metric the digest does not already define.

## The four tiers, and why each exists

| Tier | Artefact | Size | Why it exists |
|---|---|---|---|
| **Source** | provider transcripts | 241 MB | Not ours. Read-only. Assume it can disappear. |
| **Store** | `data/events-YYYY-MM.ndjson` | 5.7 MB | Provider-independent, append-only history. Survives provider format changes and transcript deletion. |
| **Digest** | `data/digest.json` | ~60 KB | The read surface. Small enough that a model can hold all of it — this is the whole point (ADR-005). |
| **Surface** | `dist/observatory.html` | ~80 KB | Self-contained, no server, no network. |

The digest tier is the load-bearing design decision. Without it, asking a model "what should I change about my usage" means feeding it megabytes. With it, the answer costs a few thousand tokens against a pre-aggregated summary.

## Incrementality

`data/.cursors.json` records a byte offset per source file. A re-run seeks each transcript to its offset and reads only what was appended. Measured: full build 3.5 s, no-op re-run 0.15 s — which is what makes a daily cron viable.

Shrink detection: if a file is smaller than its recorded offset (compaction, rotation), the cursor resets to zero and the file is reparsed.

## Module boundaries

| Module | Owns | Must not |
|---|---|---|
| `collectors/base.py` | The `Collector` interface and canonical event shape | Know any provider detail |
| `collectors/<provider>.py` | Parsing one provider's format | Write anything, emit content, be imported downstream |
| `paths.py` + `topology.json` | Turning a path into a repo and surface label | Emit, log, or return the path itself |
| `normalize.py` | The store: partitioning, cursors, append | Know a provider's format beyond the interface |
| `analyze.py` | Aggregation, the cost model, attribution fill, the fact cube | Contain judgement about what is good or bad |
| `insights.py` | Thresholds, detectors, severity, materiality | Re-read raw events |
| `render.py` + `assets/` | HTML, CSS, SVG, and client-side re-aggregation | Compute a metric not already in the digest |
| `observe.py` | CLI wiring only | Contain logic |
| `tests/test_<provider>.py` | A fixture in the vendor's real record format, asserting an exact turn count (ADR-009) | Assert against what the parser happens to expect, or pass on zero events |

If `render.py` starts computing metrics, they belong in `analyze.py` — otherwise the text output and the HTML will disagree.

## Deferred by design

SQLite (until an NDJSON scan is measurably slow) · auth · sync · a server · a query language · streaming ingest. See `00-DECISION-LOG.md`.
