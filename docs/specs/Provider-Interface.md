# Spec — Provider Interface

How to add a provider. The contract is `collectors/base.py::Collector`.

## The three methods

```python
class MyCollector(Collector):
    provider = "my-provider"

    def available(self) -> bool:
        """True when this provider's data exists on this machine."""

    def sources(self) -> list:
        """Opaque source handles (usually file paths) to scan."""

    def collect(self, source, cursor: dict) -> tuple:
        """Parse one source from `cursor` onward.
        Returns (events, new_cursor)."""
```

Register it in `normalize.py::COLLECTORS`. Nothing else changes.

Two collectors implement this today: `claude_code.py` (byte-offset cursor over an
append-only JSONL) and `codex.py` (byte-offset cursor plus carried token totals,
because Codex reports cumulative usage rather than per-turn). Between them they are
the proof the abstraction holds — see ADR-003.

Set `repo`, `surfaces`, and `lane` by passing path-shaped arguments through
`paths.classify`, `paths.pick_repo`, and `paths.lane_of`; never store the path
itself (ADR-008, [Surface-Attribution](Surface-Attribution.md)).

## The three hard rules

**1. Read-only.** Never write to, move, rename, or truncate a provider's files. A bug here must not be able to damage the user's real work.

**2. Metadata only.** Emit counts, model names, tool names, timestamps, and the working-directory basename. Never prompt text, completion text, tool arguments, file contents, shell commands, or absolute paths (ADR-006). Enforce this at the parse boundary — read only the specific fields you need, rather than copying a record and deleting keys.

**3. Incremental.** Honour the cursor. `collect()` must be cheap when nothing changed. For append-only files a byte offset is enough:

```python
if size == offset:
    return [], cursor          # nothing new
if size < offset:
    offset = 0                 # file shrank: rotation/compaction, reparse
```

## Normalize at the edge

Provider quirks are resolved in the collector, never tolerated downstream (ADR-003). The existing collector does two of these:

- **Model aliasing** — `claude-haiku-4-5-20251001` → `claude-haiku-4-5`, so one model is one row in every breakdown and matches one price-list entry.
- **Delegated turns** — subagent transcripts live in a subdirectory but carry the parent `sessionId`, so they roll up into the parent session rather than appearing as phantom sessions.

If your provider reports a field the schema lacks, add a key (additive only) and document it in `Event-Schema.md`.

## Defensive parsing

Assume the format is undocumented and will change. Skip unparseable lines; tolerate missing keys; never let one bad record abort a file. A format change should cost new data for that provider, never the existing store.

```python
try:
    rec = json.loads(line)
except (ValueError, TypeError):
    continue
```

A format change should cost new data, but it must not do so *silently*. Every
skipped line is invisible; a parser that skips them all is indistinguishable
from a provider nobody uses. That is what the fixture in the checklist below
is for (ADR-009), and why a parser rewrite bumps its cursor schema marker — the
previous version advanced its offsets whether or not it emitted anything.

## Checklist before merging a collector

- [ ] **`tests/test_<provider>.py` exists, runs the real parser over a fixture
      in the vendor's actual record format, and asserts an exact non-zero turn
      count** (ADR-009). Where the schema came from — a live transcript, or the
      vendor's own shipped source — is stated in the collector docstring with a
      date
- [ ] Zero writes to provider files (verified, not assumed)
- [ ] No content, arguments, or absolute paths in any emitted event
- [ ] Second run with an unchanged source emits zero events
- [ ] Shrinking a source file triggers a clean reparse
- [ ] A truncated or corrupt line does not abort the run
- [ ] `available()` returns False cleanly on a machine without the provider
- [ ] No downstream module needed a change
