"""Event store — append-only NDJSON, partitioned by month (ADR-001).

`data/events-YYYY-MM.ndjson`  one normalized turn per line
`data/.cursors.json`          how far each source was consumed (local only)

Incremental by construction: a re-run seeks each transcript to its recorded
byte offset, so a daily sync reads only what changed. Nothing here is ever
rewritten in place — the history is append-only.

Two rules keep an append-only store honest when a sync does not finish, which
is the common case rather than the rare one — laptops sleep, people quit the
app, and the launchd agent and a double-clicked icon can start in the same
second:

1. **Durable before recorded.** Events are flushed and fsynced, and only then
   is the cursor that consumed them written. The reverse order loses events;
   doing both at the end of the run duplicates every event already written
   when anything interrupts it, permanently and invisibly, because nothing
   downstream deduplicates.

2. **One writer.** A whole-store lock, held for the run. Two syncs reading the
   same cursor collect the same turns and both append them.

A collector that raises takes itself out of the run and nothing else. One
vendor changing their transcript format must never stop collection for the
other three.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
from pathlib import Path

from collectors.antigravity import AntigravityCollector
from collectors.claude_code import ClaudeCodeCollector
from collectors.codex import CodexCollector
from collectors.generic import load_specs
from collectors.kimi_code import KimiCodeCollector

# Hand-written modules first, then every declarative spec in collectors/specs/.
# A provider only earns a module when its format defeats the spec language —
# see collectors/generic.py for why that bar is set deliberately high.
COLLECTORS = [ClaudeCodeCollector(), CodexCollector(), AntigravityCollector(),
              KimiCodeCollector()] + load_specs()


def _cursor_path(data_dir: Path) -> Path:
    return data_dir / ".cursors.json"


def load_cursors(data_dir: Path) -> dict:
    p = _cursor_path(data_dir)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def save_cursors(data_dir: Path, cursors: dict) -> None:
    tmp = _cursor_path(data_dir).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cursors, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(_cursor_path(data_dir))


def _partition(ts) -> str:
    """`2026-08-02T09:15:22.000Z` -> `2026-08`. Undated events go to `unknown`."""
    if isinstance(ts, str) and len(ts) >= 7 and ts[4] == "-":
        return ts[:7]
    return "unknown"


@contextlib.contextmanager
def store_lock(data_dir: Path):
    """Hold the store for one run, or yield False and let the caller stand down.

    `flock` is released by the kernel when the process dies, so an interrupted
    sync leaves nothing to clean up and no stale lock to time out. Where it is
    unavailable — Windows, an exotic filesystem — this yields True and the tool
    behaves exactly as it did before rather than refusing to run. A lock that
    can stop somebody collecting their own data is worse than the race it
    prevents.
    """
    try:
        import fcntl
    except ImportError:
        yield True
        return
    data_dir.mkdir(parents=True, exist_ok=True)
    fh = open(data_dir / ".sync.lock", "w", encoding="utf-8")
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        fh.write(str(os.getpid()))
        fh.flush()
        yield True
    finally:
        fh.close()


class _Writer:
    """Append events, and know how to make what was written durable.

    Kept as a class only so `sync` can flush every open partition at a commit
    point without tracking which ones a given source touched.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.handles: dict = {}
        self.written = 0

    def add(self, ev: dict) -> None:
        part = _partition(ev.get("ts"))
        fh = self.handles.get(part)
        if fh is None:
            fh = (self.data_dir / f"events-{part}.ndjson").open("a", encoding="utf-8")
            self.handles[part] = fh
        fh.write(json.dumps(ev, separators=(",", ":")) + "\n")
        self.written += 1

    def flush(self) -> None:
        """Get the bytes onto the disk, not just out of Python's buffer.

        Without the fsync a power cut can leave a cursor pointing past events
        that never landed — the same double-count in the other direction.
        """
        for fh in self.handles.values():
            fh.flush()
            with contextlib.suppress(OSError):
                os.fsync(fh.fileno())

    def close(self) -> None:
        for fh in self.handles.values():
            with contextlib.suppress(OSError):
                fh.close()
        self.handles.clear()


def event_key(ev: dict) -> str:
    """A natural identity for one turn, for the two places that must not double it.

    The store has no event ids — ADR-001 chose append-only NDJSON and nothing
    ever needed to ask "have I seen this before" until a re-read could happen.
    Provider, session, timestamp, turn number and the token counts are enough:
    two turns that agree on all of those are indistinguishable in every number
    this tool computes, so treating them as one loses nothing even in the
    theoretical case where they were genuinely separate.
    """
    return "|".join(str(ev.get(k) or "") for k in
                    ("provider", "session", "ts", "turn", "input", "output",
                     "cache_read", "model"))


def existing_keys(data_dir: Path) -> set:
    """Every turn already in the store, by natural key."""
    return {event_key(ev) for ev in read_events(data_dir)}


def dedupe(data_dir: Path) -> dict:
    """Rewrite the store keeping the first copy of each turn. Returns a summary.

    The repair path for a store inflated before the collection fixes landed:
    an interrupted sync, two syncs at once, or any `sync --full` could each
    leave a second copy of turns that were already recorded, and nothing
    downstream deduplicated — so every number on the dashboard was quietly
    too big, with no way for its owner to tell.

    Partition by partition, through a temp file and an atomic replace, so an
    interrupted repair leaves the original intact.
    """
    seen: set = set()
    removed = kept = 0
    for path in sorted(data_dir.glob("events-*.ndjson")):
        tmp = path.with_suffix(".ndjson.tmp")
        with tmp.open("w", encoding="utf-8") as out:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    key = event_key(ev)
                    if key in seen:
                        removed += 1
                        continue
                    seen.add(key)
                    out.write(line + "\n")
                    kept += 1
            out.flush()
            with contextlib.suppress(OSError):
                os.fsync(out.fileno())
        tmp.replace(path)
    return {"kept": kept, "removed": removed}


def sync(data_dir: Path, full: bool = False) -> dict:
    """Collect every available provider into the store. Returns a run summary.

    Commits after each source that produced anything: events flushed and
    fsynced first, then the cursor that consumed them. An interruption can
    therefore cost at most one source's worth of re-reading, and a re-read is
    only ever wasted work — never a second copy of yesterday.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    summary = {"sources_scanned": 0, "events_written": 0, "partitions": [],
               "mode": "full" if full else "incremental", "failed": [],
               "skipped": None, "duplicates_skipped": 0}

    with store_lock(data_dir) as mine:
        if not mine:
            # The 09:00 agent and a double-clicked icon at login. Whoever holds
            # the lock is already collecting exactly these events.
            summary["skipped"] = "another sync is already running"
            return summary

        cursors = {} if full else load_cursors(data_dir)
        # `--full` re-reads every transcript from byte zero. Appending that to
        # a store that already holds those turns doubled it, every single run —
        # and `--full` is exactly what somebody reaches for when they suspect
        # their numbers are wrong. It reconciles against what is already here
        # instead. Incremental runs do not pay this read: their cursors are the
        # answer to the same question.
        seen_keys = existing_keys(data_dir) if full else None
        writer = _Writer(data_dir)
        seen_parts: set = set()
        try:
            for collector in COLLECTORS:
                provider = getattr(collector, "provider", "unknown")
                try:
                    if not collector.available():
                        continue
                    sources = list(collector.sources())
                except Exception as exc:               # noqa: BLE001
                    summary["failed"].append(
                        {"provider": provider, "source": None,
                         "error": f"{type(exc).__name__}: {exc}"})
                    continue

                for source in sources:
                    summary["sources_scanned"] += 1
                    key = f"{provider}:{source}"
                    try:
                        events, cursor = collector.collect(source, cursors.get(key, {}))
                    except Exception as exc:           # noqa: BLE001
                        # One unreadable transcript, or one vendor's format
                        # changing under us, must not cost the other providers
                        # their run. The cursor is left alone, so the next sync
                        # tries this source again from where it was.
                        summary["failed"].append(
                            {"provider": provider, "source": str(source),
                             "error": f"{type(exc).__name__}: {exc}"})
                        continue

                    fresh = []
                    for ev in events:
                        if seen_keys is not None:
                            key = event_key(ev)
                            if key in seen_keys:
                                summary["duplicates_skipped"] += 1
                                continue
                            seen_keys.add(key)
                        writer.add(ev)
                        fresh.append(ev)
                    events = fresh
                    if events:
                        # Durable, then recorded. Never the other way round.
                        writer.flush()
                        cursors[key] = cursor
                        save_cursors(data_dir, cursors)
                        seen_parts.update(writer.handles)
                    else:
                        cursors[key] = cursor
        finally:
            writer.close()
            # Whatever was flushed above is already recorded; this catches the
            # sources that read to the end and produced nothing.
            save_cursors(data_dir, cursors)

        summary["events_written"] = writer.written
        summary["partitions"] = sorted(seen_parts)
    return summary


def write_events(data_dir: Path, events) -> int:
    """Append already-normalized events to the store, partitioned as usual.

    Used by `observe.py demo` and by tests. Collectors never call this — they
    go through `sync`, which owns the cursors.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    handles: dict = {}
    written = 0
    try:
        for ev in events:
            part = _partition(ev.get("ts"))
            fh = handles.get(part)
            if fh is None:
                fh = (data_dir / f"events-{part}.ndjson").open("a", encoding="utf-8")
                handles[part] = fh
            fh.write(json.dumps(ev, separators=(",", ":")) + "\n")
            written += 1
    finally:
        for fh in handles.values():
            fh.close()
    return written


# Fixture rows written by `observe.py demo` before the `synthetic` flag existed.
# They are recognisable without it: the generator draws every session id as
# "d" + five hex digits and every repo from its own fixed five, and no real
# collector produces that pair. Kept so a store seeded by an older build can
# still be cleaned; new fixture rows carry the flag and never reach this.
_LEGACY_DEMO_REPOS = {"checkout-service", "growth-web", "data-platform",
                      "infra-tooling", "scratchpad"}
_LEGACY_DEMO_SID = re.compile(r"^d[0-9a-f]{5}$")


def is_synthetic(ev: dict) -> bool:
    """True for a fixture row from `observe.py demo`, flagged or legacy."""
    if ev.get("synthetic"):
        return True
    return (ev.get("workspace") in _LEGACY_DEMO_REPOS
            and bool(_LEGACY_DEMO_SID.match(ev.get("session") or "")))


def count_synthetic(data_dir: Path) -> int:
    """How many fixture rows are sitting in the store."""
    return sum(1 for ev in read_events(data_dir) if is_synthetic(ev))


def purge_synthetic(data_dir: Path) -> int:
    """Drop every fixture row from the store, partition by partition.

    Rewrites through a temp file and replaces atomically, so an interrupted
    purge leaves the original partition intact rather than a half-file.
    """
    removed = 0
    for path in sorted(data_dir.glob("events-*.ndjson")):
        tmp = path.with_suffix(".ndjson.tmp")
        kept = 0
        with path.open("r", encoding="utf-8", errors="replace") as src, \
                tmp.open("w", encoding="utf-8") as dst:
            for line in src:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    ev = json.loads(stripped)
                except (ValueError, TypeError):
                    dst.write(line)  # unparseable: not ours to delete
                    kept += 1
                    continue
                if is_synthetic(ev):
                    removed += 1
                    continue
                dst.write(line)
                kept += 1
        if kept:
            tmp.replace(path)
        else:
            tmp.unlink()
            path.unlink()
    return removed


def read_events(data_dir: Path):
    """Yield every stored event, oldest partition first."""
    for path in sorted(data_dir.glob("events-*.ndjson")):
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except (ValueError, TypeError):
                    continue
