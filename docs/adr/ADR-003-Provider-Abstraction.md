# ADR-003 — One collector interface, one unified event schema

**Status:** accepted · **Date:** 2026-08-02 · **Amended by:** [ADR-009](ADR-009-Collectors-Ship-With-A-Fixture.md)

> **Amendment (2026-08-10).** ADR-009 adds a merge gate the interface alone
> doesn't enforce: no collector may be registered here without a fixture test
> proving it parses a real specimen of the vendor's format and returns a
> non-zero turn count. The Kimi collector conformed to this interface and
> still shipped parsing nothing.

## Context

v1 supports one provider. The temptation is to skip the abstraction and parse Claude Code transcripts directly into the analysis code — it would be shorter today.

The cost of that shortcut is paid at the second provider, and it is not linear: by then, provider-specific assumptions have leaked into aggregation, insights, and rendering, and each has to be found and unpicked.

## Decision

A single `Collector` base class in `collectors/base.py` defines three methods (`available`, `sources`, `collect`) and the canonical event shape (`blank_event`). Everything downstream of `normalize.py` consumes only normalized events. A provider-specific branch outside `collectors/` is a bug.

Provider quirks are normalized *at the collector*, not tolerated downstream. Example already in place: dated model snapshots (`claude-haiku-4-5-20251001`) are folded to their alias (`claude-haiku-4-5`) inside the collector, so grouping and pricing never fragment on the same model appearing under two names.

## Consequences

**Good**
- Adding a provider is one file plus one registry line, with no downstream change.
- Every insight automatically becomes cross-provider the moment a second collector exists.
- The interface documents the three hard rules (read-only, metadata-only, incremental) in one place where a new collector author will see them.

**Bad / accepted**
- Slightly more code than direct parsing today.
- The schema is shaped by Claude Code's vocabulary, so it may need additive fields for a provider with a different model of sessions or delegation. Additive is cheap (Principle 12); the risk is acceptable.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Parse directly, refactor at provider two | The refactor is 10× the cost once provider assumptions have spread downstream |
| A plugin system with dynamic discovery | Over-engineering for a handful of providers; adds a failure mode for no benefit |
| Store raw provider records and normalize at read time | Every consumer would need to know every provider format — the exact coupling this avoids |

## Revisit when

A second collector is built. That is the real test of the abstraction — if it needs a downstream change, the interface was wrong and should be fixed then rather than worked around.
