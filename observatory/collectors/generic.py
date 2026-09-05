"""Spec-driven collector — add a provider with a JSON file, not a Python module.

Every tracker in this space grows the same way: someone wants their CLI
supported, opens an issue, and waits for a maintainer who owns none of the
tools to reverse-engineer a format they cannot test. That queue is where these
projects go to die, and it is the single biggest constraint on how fast one can
cover a fragmented market — which the Asian tool market emphatically is.

So the common case is declarative. A provider whose transcript is JSONL with
token counts on a record is described by a file in `collectors/specs/`, and the
contributor who actually uses that tool can add it, with a fixture, in one PR
touching no engine code. Only a genuinely odd format (Codex's running totals,
Kimi's event-sourced op log) still earns a hand-written module.

A spec names, in dotted paths:
  where          which records are priced turns
  fields         ts / session / cwd / model / usage counters
  tools          where tool-call names and path-shaped arguments live

Same three hard rules as every collector: read-only, metadata-only, incremental.
The path-shaped arguments are read to derive a repo label and then dropped; the
path itself never reaches the store (ADR-008).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paths as topo   # noqa: E402
import pricing         # noqa: E402

from .base import Collector, blank_event  # noqa: E402

SPEC_DIR = Path(__file__).with_name("specs")


def dig(node, path):
    """Dotted path lookup: `message.usage.input_tokens`, `content.0.name`.

    Returns None for any missing or wrongly-typed hop rather than raising — a
    provider that renames a field should cost that field, not the whole sync.
    """
    if not path:
        return None
    for part in path.split("."):
        if isinstance(node, dict):
            node = node.get(part)
        elif isinstance(node, list) and part.isdigit():
            idx = int(part)
            node = node[idx] if idx < len(node) else None
        else:
            return None
        if node is None:
            return None
    return node


def _from_path(source: str, spec: dict) -> dict:
    """What the *file* knows that its records do not.

    Several tools put the session id in the filename and never repeat it on a
    turn — Gemini CLI writes `chats/session-<ts>-<id8>.jsonl`, and nests a
    subagent's transcript under `chats/<parent session id>/`. Without this the
    whole provider collapses into one giant session, and every per-session
    detector (context carried per turn, cache paid for and abandoned) reads a
    number that means nothing.

    `from_path.session` is an ordered list of patterns; the first to match wins
    and its first capture group is the id. `from_path.sidechain` is a single
    pattern whose match marks the turn as delegated work.
    """
    cfg = spec.get("from_path") or {}
    out = {}
    posix = Path(source).as_posix()

    patterns = cfg.get("session") or []
    if isinstance(patterns, str):
        patterns = [patterns]
    for pattern in patterns:
        try:
            hit = re.search(pattern, posix)
        except re.error:
            continue          # a bad pattern costs that field, never the sync
        if hit and hit.groups():
            out["session"] = hit.group(1)
            break

    side = cfg.get("sidechain")
    if side:
        try:
            out["sidechain"] = bool(re.search(side, posix))
        except re.error:
            pass
    return out


def _matches(rec, where) -> bool:
    return all(dig(rec, k) == v for k, v in (where or {}).items())


def _int(node, path) -> int:
    value = dig(node, path)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


class SpecCollector(Collector):
    """One provider, described by a spec dict."""

    def __init__(self, spec: dict):
        self.spec = spec
        self.provider = spec["provider"]
        self.roots = [os.path.expanduser(r) for r in spec.get("roots", [])]

    # -- discovery ----------------------------------------------------------

    def available(self) -> bool:
        return any(self.sources())

    def sources(self) -> list:
        out = []
        for pattern in self.roots:
            # Split the fixed prefix from the glob so we only walk a directory
            # that actually exists — globbing from `/` on a laptop is slow.
            base, _, tail = pattern.partition("*")
            base_dir = Path(base).parent if not base.endswith("/") else Path(base)
            if not base_dir.is_dir():
                continue
            rel = pattern[len(str(base_dir)):].lstrip("/")
            try:
                out.extend(str(p) for p in base_dir.glob(rel) if p.is_file())
            except (OSError, ValueError):
                continue
        return sorted(set(out))

    # -- parsing ------------------------------------------------------------

    def collect(self, source, cursor: dict):
        path = Path(source)
        try:
            size = path.stat().st_size
        except OSError:
            return [], cursor

        offset = int(cursor.get("offset", 0))
        turn = int(cursor.get("turn", 0))
        if size < offset:          # rotated or compacted — reparse from the top
            offset, turn = 0, 0
        if size == offset:
            return [], {"offset": offset, "turn": turn}

        spec = self.spec
        where = spec.get("where") or {}
        f = spec.get("fields") or {}
        from_path = _from_path(source, spec)
        events = []

        with path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(offset)
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if not _matches(rec, where):
                    continue
                # A record with no token counts at all is a transcript entry,
                # not a priced turn. Skipping it here keeps `turn` honest.
                if not any(_int(rec, f.get(k)) for k in
                           ("input", "output", "cache_create", "cache_read")):
                    continue
                turn += 1
                events.append(self._turn(rec, turn, from_path))
            offset = fh.tell()

        return events, {"offset": offset, "turn": turn}

    def _turn(self, rec: dict, turn: int, from_path: dict = None) -> dict:
        spec, f = self.spec, self.spec.get("fields") or {}
        from_path = from_path or {}
        ev = blank_event(self.provider)
        ev["ts"] = dig(rec, f.get("ts"))
        # The record wins when it carries a session; the filename answers for
        # the tools that only write it there.
        sid = dig(rec, f.get("session")) or from_path.get("session") or ""
        ev["session"] = str(sid)[:8] or None
        cwd = dig(rec, f.get("cwd")) or ""
        ev["workspace"] = os.path.basename(str(cwd).rstrip("/")) or None
        ev["branch"] = dig(rec, f.get("branch"))
        raw_entry = dig(rec, f.get("entrypoint"))
        ev["entrypoint"] = spec.get("entrypoint_map", {}).get(
            raw_entry, raw_entry or spec.get("default_entrypoint"))
        ev["model"] = pricing.canonical_model(
            dig(rec, f.get("model")) or spec.get("default_model"))
        ev["effort"] = dig(rec, f.get("effort"))
        ev["speed"] = dig(rec, f.get("speed"))
        ev["sidechain"] = bool(dig(rec, f.get("sidechain"))
                               or from_path.get("sidechain"))
        ev["agent"] = dig(rec, f.get("agent"))
        ev["turn"] = turn
        ev["stop"] = dig(rec, f.get("stop"))

        for key in ("input", "output", "cache_create", "cache_read", "cache_1h", "cache_5m"):
            ev[key] = _int(rec, f.get(key))
        # Some vendors report a grand total that already includes the cache
        # components. Subtracting here rather than downstream keeps every
        # consumer of the event store on one meaning of `input`.
        if spec.get("input_is_total"):
            ev["input"] = max(0, ev["input"] - ev["cache_read"] - ev["cache_create"])

        ev["tools"], touched = self._tools(rec)
        cwd_repo, _ = topo.split(str(cwd))
        ev["repo"] = topo.pick_repo(cwd_repo, touched)
        ev["surfaces"] = sorted({s for r, s in touched if r == ev["repo"] and s})
        ev["lane"] = topo.lane_of(repo=ev["repo"], entrypoint=ev["entrypoint"],
                                  provider=self.provider)
        return ev

    def _tools(self, rec: dict):
        cfg = self.spec.get("tools") or {}
        names, touched = [], []
        blocks = dig(rec, cfg.get("list")) or []
        if not isinstance(blocks, list):
            return names, touched
        for block in blocks:
            if not isinstance(block, dict) or not _matches(block, cfg.get("where")):
                continue
            name = dig(block, cfg.get("name", "name"))
            if name:
                names.append(str(name))
            args = dig(block, cfg.get("args", "input"))
            if not isinstance(args, dict):
                continue
            for key in cfg.get("path_args", ("file_path", "path")):
                repo, surface = topo.classify(args.get(key))
                if repo and (repo, surface) not in touched:
                    touched.append((repo, surface))
        return names, touched


def load_specs() -> list:
    """Every spec in `collectors/specs/`, skipping any that fails to parse.

    A broken third-party spec must not be able to stop a sync — it costs that
    provider, and the sync reports the rest.
    """
    out = []
    if not SPEC_DIR.is_dir():
        return out
    for path in sorted(SPEC_DIR.glob("*.json")):
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if spec.get("provider") and spec.get("roots"):
            out.append(SpecCollector(spec))
    return out
