"""Antigravity collector — zero-token, read-only.

Antigravity writes append-only JSONL transcripts per session under
`~/.gemini/antigravity/brain/<session-id>/.system_generated/logs/transcript.jsonl`.
Assistant turns are recorded as `PLANNER_RESPONSE` steps with tool calls, timestamps,
models, and token accounting.

Reads metadata only: token counts, timestamps, session ID, workspace name, model name,
effort, and tool names. Prompt text and completion text are never emitted.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paths as topo  # noqa: E402

from .base import Collector, blank_event  # noqa: E402

ROOT = Path.home() / ".gemini" / "antigravity" / "brain"

_PATH_ARGS = ("Cwd", "DirectoryPath", "SearchPath", "AbsolutePath", "TargetFile",
              "path", "file_path", "workspace")

_DATE_SUFFIX = re.compile(r"-\d{8}$")


def canonical_model(model):
    if not isinstance(model, str):
        return model
    return _DATE_SUFFIX.sub("", model)


class AntigravityCollector(Collector):
    provider = "antigravity"

    def available(self) -> bool:
        return ROOT.is_dir()

    def sources(self) -> list:
        if not self.available():
            return []
        return sorted(str(p) for p in ROOT.glob("**/transcript.jsonl"))

    def collect(self, source, cursor: dict):
        path = Path(source)
        try:
            size = path.stat().st_size
        except OSError:
            return [], cursor

        offset = int(cursor.get("offset", 0))
        turn = int(cursor.get("turn", 0))
        sid_override = cursor.get("session")

        # Transcript shrank (compaction / rotation) — reparse from top
        if size < offset:
            offset, turn = 0, 0
        if size == offset:
            return [], {"offset": offset, "turn": turn, "session": sid_override}

        # Extract session id from path: .../brain/<session_id>/.system_generated/...
        sid = sid_override
        if not sid:
            parts = path.parts
            if "brain" in parts:
                idx = parts.index("brain")
                if idx + 1 < len(parts):
                    sid = parts[idx + 1]

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

                if rec.get("source") == "MODEL" and rec.get("type") == "PLANNER_RESPONSE":
                    turn += 1
                    ev = self._turn(rec, turn, sid)
                    if ev:
                        events.append(ev)
            offset = fh.tell()

        return events, {"offset": offset, "turn": turn, "session": sid}

    def _turn(self, rec: dict, turn: int, session_id: str | None):
        ev = blank_event(self.provider)
        ev["ts"] = rec.get("created_at") or rec.get("timestamp")
        ev["session"] = (session_id or rec.get("sessionId") or "")[:8] or None

        # Extract tool names and path-shaped arguments
        tool_calls = rec.get("tool_calls") or []
        touched = []
        cwd = None
        for tc in tool_calls:
            name = tc.get("name")
            if name:
                ev["tools"].append(str(name)[:40])
            args = tc.get("args")
            if isinstance(args, dict):
                for key in _PATH_ARGS:
                    val = args.get(key)
                    if isinstance(val, str) and val.startswith("/"):
                        if not cwd:
                            cwd = val
                        repo, surface = topo.classify(val)
                        if repo and (repo, surface) not in touched:
                            touched.append((repo, surface))

        cwd_str = cwd or ""
        ev["workspace"] = os.path.basename(cwd_str.rstrip("/")) or None
        ev["entrypoint"] = "ide"
        model_raw = rec.get("model") or rec.get("model_name") or "gemini-3.6-flash"
        ev["model"] = canonical_model(model_raw)
        ev["effort"] = rec.get("effort") or "high"
        ev["turn"] = turn
        ev["sidechain"] = bool(rec.get("is_subagent") or rec.get("sidechain"))
        ev["agent"] = rec.get("subagent") or rec.get("agent_role")

        usage = rec.get("usage") or rec.get("tokens") or {}
        inp = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)

        if not inp and not out:
            # Token estimation for turn if not directly emitted
            text_len = len(str(rec.get("content") or "")) + len(str(rec.get("thinking") or ""))
            out = max(10, text_len // 4)
            inp = 1500  # standard context window baseline

        ev["input"] = inp
        ev["output"] = out
        ev["cache_create"] = int(usage.get("cache_creation_input_tokens") or 0)
        ev["cache_read"] = int(usage.get("cache_read_input_tokens") or 0)

        cwd_repo, _ = topo.split(cwd_str)
        ev["repo"] = topo.pick_repo(cwd_repo, touched)
        ev["surfaces"] = sorted({s for r, s in touched if r == ev["repo"] and s})
        ev["lane"] = topo.lane_of(repo=ev["repo"], entrypoint=ev["entrypoint"],
                                  provider=self.provider)
        return ev
