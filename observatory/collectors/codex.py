"""Codex collector — zero-token, read-only.

Codex writes an append-only rollout per thread under
`~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<id>.jsonl`. Token accounting rides
along as `event_msg/token_count` records carrying a running total, so a turn's
true cost is the delta between consecutive totals — which is also what makes
this safe against the duplicate snapshots Codex emits.

Same contract as every collector: names and counts only. `function_call`
arguments are parsed solely to pull path-shaped values through the topology
classifier; the values themselves are dropped (ADR-008).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paths as topo  # noqa: E402

from .base import Collector, blank_event  # noqa: E402

ROOT = Path.home() / ".codex" / "sessions"

_PATH_KEYS = ("path", "file_path", "workdir", "cwd", "notebook_path")
_COUNTERS = ("input_tokens", "cached_input_tokens", "output_tokens",
             "reasoning_output_tokens")

# Rollout `source` -> the surface a human would name.
_ENTRYPOINT = {"exec": "cli", "vscode": "ide", "cli": "cli", "app": "desktop"}


def _blank_totals() -> dict:
    return dict.fromkeys(_COUNTERS, 0)


def _delta(now: dict, prev: dict) -> dict:
    """Per-turn usage. Clamped at zero so a reset total can never go negative."""
    return {k: max(0, int(now.get(k) or 0) - int(prev.get(k) or 0)) for k in _COUNTERS}


class CodexCollector(Collector):
    provider = "codex"

    def available(self) -> bool:
        return ROOT.is_dir()

    def sources(self) -> list:
        if not self.available():
            return []
        return sorted(str(p) for p in ROOT.glob("**/rollout-*.jsonl"))

    def collect(self, source, cursor: dict):
        path = Path(source)
        try:
            size = path.stat().st_size
        except OSError:
            return [], cursor

        state = {
            "offset": int(cursor.get("offset", 0)),
            "turn": int(cursor.get("turn", 0)),
            "prev": dict(cursor.get("prev") or _blank_totals()),
            "meta": dict(cursor.get("meta") or {}),
            "ctx": dict(cursor.get("ctx") or {}),
        }
        if size < state["offset"]:  # rewritten underneath us — reparse
            state = {"offset": 0, "turn": 0, "prev": _blank_totals(),
                     "meta": {}, "ctx": {}}
        if size == state["offset"]:
            return [], state

        events, pending = [], {"tools": [], "touched": []}
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(state["offset"])
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (ValueError, TypeError):
                    continue
                ev = self._record(rec, state, pending)
                if ev:
                    events.append(ev)
            state["offset"] = fh.tell()

        return events, state

    def _record(self, rec: dict, state: dict, pending: dict):
        payload = rec.get("payload")
        if not isinstance(payload, dict):
            return None

        if rec.get("type") == "session_meta":
            state["meta"] = {
                "id": payload.get("id") or "",
                "cwd": payload.get("cwd") or "",
                "source": payload.get("source"),
            }
            return None

        if rec.get("type") == "turn_context":
            state["ctx"] = {
                "model": payload.get("model"),
                "effort": payload.get("effort") or payload.get("reasoning_effort"),
                "cwd": payload.get("cwd") or "",
            }
            return None

        kind = payload.get("type")
        if kind in ("function_call", "custom_tool_call", "local_shell_call"):
            name = payload.get("name")
            if name:
                pending["tools"].append(name)
            self._args(payload.get("arguments"), pending)
            return None
        if kind == "web_search_call":
            pending["tools"].append("WebSearch")
            return None
        if kind == "token_count":
            return self._turn(rec, payload, state, pending)
        return None

    def _args(self, raw, pending: dict) -> None:
        """Read path-shaped arguments, keep the label, drop the value."""
        if not isinstance(raw, str) or len(raw) > 200_000:
            return
        try:
            args = json.loads(raw)
        except (ValueError, TypeError):
            return
        if isinstance(args, dict):
            for key in _PATH_KEYS:
                self._note(args.get(key), pending)

    @staticmethod
    def _note(value, pending: dict) -> None:
        repo, surface = topo.classify(value)
        if repo and (repo, surface) not in pending["touched"]:
            pending["touched"].append((repo, surface))

    def _turn(self, rec: dict, payload: dict, state: dict, pending: dict):
        totals = (payload.get("info") or {}).get("total_token_usage") or {}
        if not totals:
            return None
        used = _delta(totals, state["prev"])
        state["prev"] = {k: int(totals.get(k) or 0) for k in _COUNTERS}
        if not any(used.values()):
            return None  # repeated snapshot — no work happened in between

        meta, ctx = state["meta"], state["ctx"]
        cwd = ctx.get("cwd") or meta.get("cwd") or ""
        source = meta.get("source")
        agent = _subagent(source)
        state["turn"] += 1

        ev = blank_event(self.provider)
        ev["ts"] = rec.get("timestamp")
        ev["session"] = (meta.get("id") or "")[:8] or None
        ev["workspace"] = os.path.basename(cwd.rstrip("/")) or None
        ev["model"] = ctx.get("model")
        ev["effort"] = ctx.get("effort")
        ev["entrypoint"] = _ENTRYPOINT.get(source) if isinstance(source, str) else None
        ev["sidechain"] = agent is not None
        ev["agent"] = agent
        ev["turn"] = state["turn"]

        # Codex reports cached input inside the input count, and reasoning
        # inside the output count — so neither is added again here.
        cached = used["cached_input_tokens"]
        ev["input"] = max(0, used["input_tokens"] - cached)
        ev["cache_read"] = cached
        ev["output"] = used["output_tokens"]
        ev["tools"] = list(pending["tools"])

        cwd_repo, _ = topo.split(cwd)
        touched = pending["touched"]
        ev["repo"] = topo.pick_repo(cwd_repo, touched)
        ev["surfaces"] = sorted({s for r, s in touched if r == ev["repo"] and s})
        ev["lane"] = topo.lane_of(repo=ev["repo"], entrypoint=ev["entrypoint"],
                                  provider=self.provider)
        pending["tools"].clear()
        pending["touched"].clear()
        return ev


def _subagent(source):
    """Codex tags delegated threads with a `subagent` source. Returns its name,
    or None for an ordinary thread."""
    if isinstance(source, str) and source.startswith("{"):
        try:
            source = json.loads(source)
        except (ValueError, TypeError):
            return None
    if not isinstance(source, dict):
        return None
    sub = source.get("subagent")
    if isinstance(sub, dict):
        return next((str(v) for v in sub.values() if v), "unnamed")
    return str(sub) if sub else None