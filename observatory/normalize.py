"""Event store — append-only NDJSON, partitioned by month (ADR-001).

`data/events-YYYY-MM.ndjson`  one normalized turn per line
`data/.cursors.json`          how far each source was consumed (local only)

Incremental by construction: a re-run seeks each transcript to its recorded
byte offset, so a daily sync reads only what changed. Nothing here is ever
rewritten in place — the history is append-only.
"""

from __future__ import annotations

import json
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


def sync(data_dir: Path, full: bool = False) -> dict:
    """Collect every available provider into the store. Returns a run summary."""
    data_dir.mkdir(parents=True, exist_ok=True)
    cursors = {} if full else load_cursors(data_dir)
    handles: dict = {}
    written = 0
    scanned = 0

    try:
        for collector in COLLECTORS:
            if not collector.available():
                continue
            for source in collector.sources():
                scanned += 1
                key = f"{collector.provider}:{source}"
                events, cursor = collector.collect(source, cursors.get(key, {}))
                cursors[key] = cursor
                for ev in events:
                    part = _partition(ev.get("ts"))
                    fh = handles.get(part)
                    if fh is None:
                        fh = (data_dir / f"events-{part}.ndjson").open(
                            "a", encoding="utf-8"
                        )
                        handles[part] = fh
                    fh.write(json.dumps(ev, separators=(",", ":")) + "\n")
                    written += 1
    finally:
        for fh in handles.values():
            fh.close()

    save_cursors(data_dir, cursors)
    return {
        "sources_scanned": scanned,
        "events_written": written,
        "partitions": sorted(handles.keys()),
        "mode": "full" if full else "incremental",
    }


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
