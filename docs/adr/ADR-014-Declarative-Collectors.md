# ADR-014 — A provider is a JSON spec, not a Python module

**Status:** accepted · **Date:** 2026-08-19 · **Extends:** [ADR-003](ADR-003-Provider-Abstraction.md), [ADR-009](ADR-009-Collectors-Ship-With-A-Fixture.md)

## Context

Tool coverage is the strongest correlate with stars in this category: ccusage
supports 16 agents, TokenTracker 32, aiusage 25+. It is also the hardest thing
to grow, because adding a provider means reverse-engineering an undocumented
format the maintainer does not use and cannot test against.

That bottleneck falls hardest exactly where this project needs coverage most.
The Asian tool market is fragmented — Lingma with 10M+ IDE installs, Qwen Code
with 5M+ users, Comate, CodeBuddy, Trae, Kimi Code, CodeGeeX, Doubao — and it
churns (Qwen Code's free OAuth tier retired April 2026; iFlow CLI sunset the
same month). No single maintainer uses more than three of these.

## Decision

Support two kinds of collector.

**Declarative (the default).** A provider whose transcript is JSONL with token
counts on a record is described entirely by a file in `collectors/specs/`:
which records are priced turns, dotted paths to the timestamp/session/cwd/model
and each token counter, and where tool names and path-shaped arguments live.
`collectors/generic.SpecCollector` interprets it. **No engine code changes.**

**Hand-written (the exception).** A format the spec language cannot express
earns a module. Two already have: Codex reports running totals so a turn's cost
is a delta between snapshots, and Kimi Code writes an event-sourced op log where
the model rides on separate `config.update` records.

Both kinds obey the same three rules: read-only, metadata-only, incremental.
Both must ship a fixture (ADR-009).

## Why this matters more than it looks

It changes who can contribute. The person who uses Lingma is the only person
positioned to add Lingma correctly — they have the transcripts. Their cost is
one JSON file plus a fixture, reviewable by a maintainer who has never seen the
tool, because the fixture asserts an exact turn count against real records.

That converts the project's biggest structural weakness (a single maintainer in
one country, using three tools) into its growth loop. Every merged spec brings
that tool's user community with it.

## Options considered

| Option | Verdict |
|---|---|
| Python module per provider (the source project's shape) | Rejected as the default. Correct for odd formats, far too expensive as the common path — it puts every provider behind a code review by someone who cannot test it. |
| Plugin packages on PyPI | Rejected. Adds a dependency and a supply-chain surface to a stdlib-only engine, and moves the fixture out of the repo where it cannot gate a merge. |
| **JSON spec + generic interpreter** ← chosen | A provider becomes a data contribution. Cost: a spec language to document, and formats it cannot express. |
| Consume another tool's parsers (token-monitor uses tokscale for this) | Rejected. Inherits their coverage *and* their gaps, their release cadence, and their privacy posture. |

## Trade-offs accepted

1. **The spec language will not cover everything.** That is the point of keeping
   the module escape hatch. When a third format needs a module, that is
   information about the language, not a failure.
2. **Dotted paths are stringly-typed.** A renamed vendor field yields a null,
   not an error. Deliberate: a provider that renames one field should cost that
   field, not the whole sync. The fixture is what catches it.
3. **A malformed third-party spec must not break a sync.** `load_specs()` skips
   anything that fails to parse rather than raising.
4. **A spec can be written wrong in a way that is silently plausible** — reading
   the wrong counter, say. Only the fixture catches this, which is why a spec
   without one is not merged.

## See also

- [`collectors/specs/README.md`](../../observatory/collectors/specs/README.md)
- [ADR-009](ADR-009-Collectors-Ship-With-A-Fixture.md)
- [04-GROWTH-FLYWHEEL](../strategy/04-GROWTH-FLYWHEEL.md)
