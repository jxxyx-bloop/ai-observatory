# ADR-001 — NDJSON as the store format

**Status:** accepted · **Date:** 2026-08-02

## Context

The event store needs to be appendable, inspectable, and cheap to migrate. Candidates: SQLite, Parquet, a single JSON array, NDJSON.

At current volume the whole store is 5.7 MB for 18,095 events — a full scan takes well under a second in pure Python. There is no query-performance problem to solve yet.

## Decision

Newline-delimited JSON, one normalized event per line, partitioned by month: `data/events-YYYY-MM.ndjson`. Full-word keys, not abbreviations.

## Consequences

**Good**
- Append is a file write. No schema, no migration, no locking.
- `head`, `grep`, `wc -l`, and `jq` all work. A corrupted line costs one event, not the file.
- Monthly partitions bound file size and make archival or deletion a per-month operation.
- Migration to SQLite/Parquet later is a read-and-insert loop, not a rewrite.

**Bad / accepted**
- No indexes; every aggregation is a full scan. Fine at this size, not forever.
- Larger on disk than a columnar format. Accepted: legibility beats compression at this scale (Principle 6).
- No transactional guarantee across a multi-file write. Accepted: the store is derived data reconstructible from source with `--full`.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| SQLite | Solves a performance problem that does not exist; adds schema migration cost to every new field; not readable with `head` |
| Parquet | Requires a dependency (Principle 7); opaque to inspection |
| One JSON array | Cannot append without rewriting the whole file; a single syntax error loses everything |

## Revisit when

A full digest rebuild exceeds ~10 seconds, or ad-hoc querying across the store becomes a routine need rather than an occasional one. Migration path is deliberately cheap — that is half the reason for choosing this format.
