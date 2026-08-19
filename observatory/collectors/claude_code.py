"""Claude Code collector — zero-token, read-only (ADR-004).

Claude Code already writes a full append-only JSONL transcript per session
under ~/.claude/projects/<slug>/<session-id>.jsonl. Every assistant turn in
there carries the exact token accounting the API returned. So there is nothing
to instrument and no prompt overhead: we read what already exists.

Reads nothing but token/metadata fields. Prompt and completion text are never
touched — see `_turn`, which only ever looks at `usage`, `model`,
`stop_reason`, and tool-use *names*.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paths as topo  # noqa: E402

from .base import Collector, blank_event  # noqa: E402

ROOT = Path.home() / ".claude" / "projects"

# Tool arguments that name a file. Read to derive a repo/surface label, then
# discarded — see ADR-008. Every other argument is ignored entirely.
_PATH_ARGS = ("file_path", "notebook_path", "path")

# Raw entrypoint values -> the surface a human would name.
_ENTRYPOINT = {"claude-desktop": "desktop", "cli": "cli", "sdk-cli": "sdk",
               "vscode": "ide", "jetbrains": "ide"}

# Dated snapshots (`claude-haiku-4-5-20251001`) and the same model's alias
# (`claude-haiku-4-5`) are the same model at the same price. Normalize to the
# alias so downstream grouping and pricing don't fragment.
_DATE_SUFFIX = re.compile(r"-\d{8}$")


def canonical_model(model):
    if not isinstance(model, str):
        return model
    return _DATE_SUFFIX.sub("", model)


class ClaudeCodeCollector(Collector):
    provider = "claude-code"

    def available(self) -> bool:
        return ROOT.is_dir()

    def sources(self) -> list:
        # Main sessions live at <project>/<session>.jsonl; delegated subagent
        # turns live at <project>/<session>/subagents/agent-*.jsonl and carry
        # the parent sessionId, so both land under the same session rollup.
        if not self.available():
            return []
        return sorted(str(p) for p in ROOT.glob("**/*.jsonl"))

    def collect(self, source, cursor: dict):
        path = Path(source)
        try:
            size = path.stat().st_size
        except OSError:
            return [], cursor

        offset = int(cursor.get("offset", 0))
        turn = int(cursor.get("turn", 0))
        # Transcript shrank (compaction / rotation) — reparse from the top.
        if size < offset:
            offset, turn = 0, 0
        if size == offset:
            return [], {"offset": offset, "turn": turn}

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
                if rec.get("type") != "assistant":
                    continue
                turn += 1
                ev = self._turn(rec, turn)
                if ev:
                    events.append(ev)
            offset = fh.tell()

        return events, {"offset": offset, "turn": turn}

    def _turn(self, rec: dict, turn: int):
        msg = rec.get("message") or {}
        usage = msg.get("usage") or {}
        if not usage:
            return None

        ev = blank_event(self.provider)
        ev["ts"] = rec.get("timestamp")
        sid = rec.get("sessionId") or ""
        ev["session"] = sid[:8] or None
        cwd = rec.get("cwd") or ""
        ev["workspace"] = os.path.basename(cwd.rstrip("/")) or None
        ev["branch"] = rec.get("gitBranch") or None
        ev["entrypoint"] = _ENTRYPOINT.get(rec.get("entrypoint"), rec.get("entrypoint"))
        ev["model"] = canonical_model(msg.get("model"))
        ev["effort"] = rec.get("effort")
        ev["tier"] = usage.get("service_tier")
        ev["speed"] = usage.get("speed")
        ev["sidechain"] = bool(rec.get("isSidechain"))
        ev["agent"] = rec.get("slug")  # subagent type, when this is a delegated turn
        ev["turn"] = turn
        ev["stop"] = msg.get("stop_reason")

        ev["input"] = int(usage.get("input_tokens") or 0)
        ev["output"] = int(usage.get("output_tokens") or 0)
        ev["cache_create"] = int(usage.get("cache_creation_input_tokens") or 0)
        ev["cache_read"] = int(usage.get("cache_read_input_tokens") or 0)
        cc = usage.get("cache_creation") or {}
        ev["cache_1h"] = int(cc.get("ephemeral_1h_input_tokens") or 0)
        ev["cache_5m"] = int(cc.get("ephemeral_5m_input_tokens") or 0)

        stu = usage.get("server_tool_use") or {}
        ev["web_search"] = int(stu.get("web_search_requests") or 0)
        ev["web_fetch"] = int(stu.get("web_fetch_requests") or 0)

        # Tool names, plus file-naming arguments read only long enough to
        # derive a repo/surface label. No argument value is ever emitted.
        touched = []
        for block in msg.get("content") or []:
            if not (isinstance(block, dict) and block.get("type") == "tool_use"):
                continue
            name = block.get("name")
            if name:
                ev["tools"].append(name)
            args = block.get("input")
            if not isinstance(args, dict):
                continue
            for key in _PATH_ARGS:
                repo, surface = topo.classify(args.get(key))
                if repo and (repo, surface) not in touched:
                    touched.append((repo, surface))

        # Where the turn *ran* wins over what it touched; a turn launched from a
        # parent folder (cwd `~/GitHub`) has no repo of its own, so the files it
        # edited are the only honest attribution available.
        cwd_repo, _ = topo.split(cwd)
        ev["repo"] = topo.pick_repo(cwd_repo, touched)
        ev["surfaces"] = sorted({s for r, s in touched if r == ev["repo"] and s})
        ev["lane"] = topo.lane_of(repo=ev["repo"], entrypoint=ev["entrypoint"],
                                  provider=self.provider)
        return ev
