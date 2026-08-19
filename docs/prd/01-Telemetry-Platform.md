# PRD 01 — Telemetry Platform

**Status:** v1 shipped 2026-08-02

## Vision

Create a local-first observability layer that collects AI usage with near-zero maintenance and zero marginal cost.

## Product philosophy

- **Automatic over manual.** A source that needs human effort is not a source.
- **Local-first.** The data never leaves the machine.
- **Prefer estimation over missing data**, with confidence stated.
- **Normalize provider differences at the edge**, never downstream.
- **Append-only history.** The store is the record; it is never rewritten in place.
- **Free to run.** Collection spends no tokens (ADR-004).

## Functional requirements

| # | Requirement | v1 status |
|---|---|---|
| F1 | Collect Claude Code usage from local transcripts | ✅ 18,095 turns, 56 days, on first run |
| F2 | Capture main-session and delegated subagent turns, attributed to the parent session | ✅ `**/*.jsonl`, `isSidechain`, agent `slug` |
| F3 | Normalize into a unified event schema | ✅ `specs/Event-Schema.md` |
| F4 | Store events as NDJSON, partitioned by month | ✅ `data/events-YYYY-MM.ndjson` |
| F5 | Incremental sync — re-read only what changed | ✅ byte cursors; 0.15 s no-op re-run |
| F6 | Fold provider aliasing so one model is one row | ✅ dated snapshots → alias |
| F7 | Survive provider format change without data loss | ✅ defensive parse; unknown lines skipped |
| F8 | Expose a lightweight read surface for consumers | ✅ `digest.json` (PRD 02) |
| F9 | Support Enterprise and Personal accounts | ⚠️ Both are collected, but the transcripts carry no account identifier — accounts are **not distinguishable**. See Known-Limitations. |

## Architectural constraints

- No SQL database in v1 (ADR-001).
- NDJSON files in `data/`; `data/` and `dist/` are gitignored — derived data is never committed.
- Provider plug-in interface; collectors are the only provider-aware code (ADR-003).
- Read-only collectors. Never write to a provider's files.
- Standard library only. No dependencies.
- Metadata only — no prompt text, completion text, tool arguments, or absolute paths (ADR-006).

## Decision records

- NDJSON chosen for inspectability, cheap append, and cheap migration — ADR-001.
- SQLite deferred until a full rebuild exceeds ~10 s — ADR-001 → Revisit.
- Zero-token collection by reading provider transcripts — ADR-004.
- Metadata-only storage — ADR-006.

## Measured baseline (2026-08-02)

| Metric | Value |
|---|---|
| Source scanned | 245 files, 241 MB |
| Events collected | 18,095 turns across 67 sessions |
| Store size | 5.7 MB (42× smaller than source) |
| Full build | 3.5 s |
| Incremental no-op | 0.15 s |
| Tokens spent collecting | 0 |

## Future evolution

SQLite when scan time justifies it · additional collectors (Codex, Cursor, ChatGPT export, Gemini) gated on a passive local source existing · per-turn wall-clock duration if a provider starts recording it · a scheduled daily sync.
