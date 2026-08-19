# ADR-009 — A collector ships only with a fixture that proves it parses

**Status:** accepted · **Date:** 2026-08-10 · **Amends:** ADR-003, ADR-007

## Context

The Kimi Code collector shipped on 2026-08-10 and collected nothing. It was
written without a live transcript to read — no Kimi login existed on the
building machine — so its record schema was inferred from the vendor's
directory-layout docs plus token-field string constants pulled out of the
installed binary. The inference was wrong in four independent ways at once:
`wire.jsonl` is an event-sourced op log, not a log of API responses, so
`usage` was on a nested loop event rather than the record, the token fields
were the engine's own four-component names, `time` was epoch milliseconds
rather than an ISO `ts`, and the model lived on entirely separate records.

None of that produced an error. The parser read every line, matched nothing,
and returned an empty list. The gap only surfaced when a user asked why his
tool was missing from the published dashboard.

That is the failure mode worth designing against. **A collector that finds
nothing is indistinguishable from a provider you do not use.** Every other
class of bug in this engine is loud — a bad price shows up as an absurd
number, a bad label shows up in a chart. A silent parser looks exactly like
an honest zero, which is the one thing ADR-007 promises the dashboard will
never quietly get wrong.

## Decision

No collector is registered in `normalize.py` or the hosted collector without a
committed fixture test that runs the real parser over a transcript in the
vendor's actual format and asserts a non-zero event count.

1. **The fixture is a specimen, not a mock.** It is a byte-level copy of the
   vendor's record shapes — captured from a real transcript, or reconstructed
   from the vendor's own source when no transcript is reachable. It never
   encodes what the parser happens to expect.
2. **The provenance of the schema is written into the collector docstring**,
   with the date and the source it was read from. "Verified against a live
   transcript" and "read out of the shipped binary" are different claims and
   are stated as different claims.
3. **Zero events is an assertion failure**, not a pass. Every fixture asserts
   an exact turn count, including the turns that must be *excluded*.
4. **Cursors carry a schema marker.** A parser rewrite that changes what
   counts as a turn resets its cursors, because the previous parser advanced
   its offsets whether or not it emitted anything.

`engine/tests/test_kimi_code.py` is the reference implementation: stdlib
only, no framework, `python3` it and read the exit code.

## Consequences

**Good**

- The dashboard's central honesty claim survives contact with a new provider.
  A provider that is present but unparsed now fails loudly at commit time.
- The fixture doubles as the schema documentation. When Kimi's wire protocol
  moves, the diff to the fixture *is* the changelog entry.
- Cheap. The Kimi fixture is one file, 18 assertions, and runs instantly.

**Bad / accepted**

- Slower to add a provider, and slowest exactly where it hurts most — a tool
  the author cannot log into. Accepted: that is the case that already failed.
- A fixture pins the format as understood *today*. It cannot catch a vendor
  adding a field the parser should have read. It catches the parser reading a
  format that no longer exists, which is the failure that actually happened.
- No test runner exists in this repo, so these tests run when someone
  remembers. A pre-merge hook is the obvious next step and is not this ADR.

## Revisit when

- A third collector regression slips through with the fixture green — the
  fixtures are testing the parser against itself, and need real captures.
- Someone proposes shipping a collector "provisionally, flagged in
  Known-Limitations, fixture to follow." That was the 2026-08-10 process. The
  flag was written, was accurate, and helped no one: the dashboard still
  showed a confident zero.
