"""Kimi Code CLI collector — zero-token, read-only.

Kimi Code persists one append-only wire log per agent:

    ~/.kimi-code/sessions/<workDirKey>/<sessionId>/agents/<agentId>/wire.jsonl
    ~/.kimi-code/sessions/<workDirKey>/<sessionId>/wire.jsonl          (v1 legacy)

`agents/main/` is the top-level agent; any other `<agentId>` is a sub-agent.
The CLI reads "both legacy root `wire.jsonl` logs and v2 per-agent" logs, so
this collector globs both.

SCHEMA — verified 2026-08-10 against the installed `kimi` binary (v2 wire
protocol 1.4/1.5), which ships readable source. wire.jsonl is an *event-
sourced op log*, not a log of API responses. Every record is
`{"type": <op>, "time": <epoch_ms>, ...payload}`:

  metadata                    {protocol_version, created_at}
  config.update               {modelAlias?, cwd?, thinkingEffort?, ...}
  context.append_message      {message}
  context.append_loop_event   {event}   <- step.begin | step.end |
                                           content.part | tool.call | tool.result
  context.apply_compaction | context.undo | context.clear |
  context.update_token_count | full_compaction.* | micro_compaction.apply

Token usage rides on the `step.end` loop event as the engine's four-component
`TokenUsage`, already split (`inputTotal = inputOther + inputCacheRead +
inputCacheCreation`), so nothing is subtracted back out:

  {"type":"context.append_loop_event","time":1754...,
   "event":{"type":"step.end","uuid":...,"turnId":...,"step":3,
            "usage":{"inputOther":N,"output":N,
                     "inputCacheRead":N,"inputCacheCreation":N},
            "finishReason":"tool_use", ...}}

One `step.end` = one LLM request = one priced turn (the same granularity the
other collectors emit). The model is NOT on the step — it is carried by
`config.update` records, so the running model/cwd/effort are tracked across
the file and persisted in the cursor so an incremental re-read that starts
past the last `config.update` still prices its turns.

Reads nothing but token/metadata fields. Prompt and completion text are never
touched.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paths as topo  # noqa: E402

from .base import Collector, blank_event  # noqa: E402

KIMI_HOME = Path(os.environ.get("KIMI_CODE_HOME") or (Path.home() / ".kimi-code"))
ROOT = KIMI_HOME / "sessions"
SESSION_INDEX = KIMI_HOME / "session_index.jsonl"
WORKSPACES = KIMI_HOME / "workspaces.json"

# `sessions/` is keyed by workDirKey: `wd_<workspace-name>_<12 hex>`.
_WD_KEY = re.compile(r"^wd_(.+)_[0-9a-f]{8,}$")

# The CLI's own model aliases (config.toml `[models."kimi-code/*"].model`) are
# shorter than the public API's model ids and would otherwise fragment
# pricing.json entries that are keyed by the public name.
_MODEL_ALIAS = {
    "k3": "kimi-k3",
    "kimi-for-coding": "kimi-k2.7-code",
    "kimi-for-coding-highspeed": "kimi-k2.7-code-highspeed",
}

_PATH_ARGS = ("file_path", "path", "notebook_path", "cwd", "workdir")

# Bumped whenever this parser's reading of the wire changes enough that
# stored offsets can no longer be trusted. See `collect`.
KIMI_CURSOR_SCHEMA = 2


def _cursor(offset, turn, model, cwd, effort) -> dict:
    return {"schema": KIMI_CURSOR_SCHEMA, "offset": offset, "turn": turn,
            "model": model, "cwd": cwd, "effort": effort}


def canonical_model(model):
    if not isinstance(model, str) or not model:
        return None
    model = model.removeprefix("kimi-code/")
    return _MODEL_ALIAS.get(model, model)


def _iso(ms):
    """`time` is epoch milliseconds (`Date.now()`), not an ISO string."""
    if not isinstance(ms, (int, float)) or ms <= 0:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000.0, timezone.utc).isoformat(
            timespec="seconds").replace("+00:00", "Z")
    except (ValueError, OSError, OverflowError):
        return None


def _tokens(usage: dict) -> tuple:
    """(input, output, cache_read, cache_create) — uncached-input convention.

    The engine's own `TokenUsage` already reports the four components
    separately, so `inputOther` IS the uncached input. Older/foreign shapes
    (a raw provider response leaking through) are still accepted so a schema
    change degrades to partial data rather than to silence.
    """
    if "inputOther" in usage or "inputCacheRead" in usage:
        return (int(usage.get("inputOther") or 0), int(usage.get("output") or 0),
                int(usage.get("inputCacheRead") or 0),
                int(usage.get("inputCacheCreation") or 0))

    inp, out = usage.get("input_tokens"), usage.get("output_tokens")
    if inp is not None or out is not None:
        return (int(inp or 0), int(out or 0),
                int(usage.get("cache_read_input_tokens") or 0),
                int(usage.get("cache_creation_input_tokens") or 0))

    prompt = int(usage.get("prompt_tokens") or 0)
    out = int(usage.get("completion_tokens") or 0)
    details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    cache_read = int(details.get("cached_tokens") or 0)
    return max(0, prompt - cache_read), out, cache_read, 0


class KimiCodeCollector(Collector):
    provider = "kimi-code"

    def __init__(self):
        self._workdir_by_session: dict = {}
        self._workdir_by_key: dict = {}

    def available(self) -> bool:
        return ROOT.is_dir()

    def _load_indexes(self) -> None:
        """Two independent ways to name a workspace; neither is guaranteed.

        `workspaces.json` maps the workDirKey straight to its root path and is
        written on first use. `session_index.jsonl` maps each sessionId to its
        workDir (records are appended, and deletions append `{sessionId,
        deleted: true}`). When both are missing the key itself still carries
        the name — `wd_<name>_<hash>` — which is why nothing here can leave a
        session unlabelled.
        """
        self._workdir_by_session, self._workdir_by_key = {}, {}
        try:
            blob = json.loads(WORKSPACES.read_text(encoding="utf-8", errors="replace"))
            for key, meta in (blob.get("workspaces") or {}).items():
                if isinstance(meta, dict):
                    name = meta.get("name") or os.path.basename(
                        str(meta.get("root") or "").rstrip("/"))
                    if name:
                        self._workdir_by_key[key] = name
        except (OSError, ValueError, TypeError, AttributeError):
            pass

        try:
            lines = SESSION_INDEX.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except (ValueError, TypeError):
                continue
            sid, wd = rec.get("sessionId"), rec.get("workDir")
            if sid and rec.get("deleted") is True:
                self._workdir_by_session.pop(sid, None)
            elif sid and wd:
                self._workdir_by_session[sid] = wd

    def sources(self) -> list:
        if not self.available():
            return []
        self._load_indexes()
        found = set(ROOT.glob("*/*/agents/*/wire.jsonl"))
        found |= set(ROOT.glob("*/*/wire.jsonl"))  # v1 legacy root logs
        return sorted(str(p) for p in found)

    def _ids_from_path(self, path: Path):
        """-> (workDirKey, sessionId, agentId). agentId defaults to `main`
        for a v1 root `wire.jsonl`, which predates the per-agent split."""
        parts = path.parts
        try:
            idx = parts.index("sessions")
        except ValueError:
            return None, None, "main"
        if idx + 2 >= len(parts):
            return None, None, "main"
        wd_key, session_id = parts[idx + 1], parts[idx + 2]
        agent = parts[idx + 4] if idx + 4 < len(parts) - 1 else "main"
        return wd_key, session_id, agent

    def _workspace(self, wd_key, session_id):
        wd = self._workdir_by_session.get(session_id or "")
        if wd:
            return os.path.basename(str(wd).rstrip("/")) or None
        name = self._workdir_by_key.get(wd_key or "")
        if name:
            return name
        m = _WD_KEY.match(wd_key or "")
        return m.group(1) if m else None

    def collect(self, source, cursor: dict):
        path = Path(source)
        try:
            size = path.stat().st_size
        except OSError:
            return [], cursor

        # The pre-fix collector emitted nothing but still advanced its offsets,
        # so an upgrade alone would skip every turn it already walked past.
        # A cursor without the schema marker is from that era: reparse from
        # byte 0 to recover the history. Safe against duplicates precisely
        # because that collector wrote no events.
        if cursor.get("schema") != KIMI_CURSOR_SCHEMA:
            cursor = {}

        offset = int(cursor.get("offset", 0))
        turn = int(cursor.get("turn", 0))
        # Carried across runs: `config.update` sits near the top of the file,
        # so an incremental read starting past it has no other way to know
        # which model the turns it is about to read were billed against.
        model = cursor.get("model")
        cwd = cursor.get("cwd") or ""
        effort = cursor.get("effort")

        if size < offset:  # compaction / rotation — reparse from the top
            offset, turn, model, cwd, effort = 0, 0, None, "", None
        if size == offset:
            return [], _cursor(offset, turn, model, cwd, effort)

        wd_key, session_id, agent_id = self._ids_from_path(path)
        workspace = self._workspace(wd_key, session_id)

        events = []
        pending: dict = {}   # stepUuid -> {"tools": [...], "touched": [...]}

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
                if not isinstance(rec, dict):
                    continue

                rtype = rec.get("type")
                if rtype == "config.update":
                    model = canonical_model(rec.get("modelAlias")) or model
                    if isinstance(rec.get("cwd"), str) and rec["cwd"]:
                        cwd = rec["cwd"]
                    te = rec.get("thinkingEffort")
                    if isinstance(te, str) and te:
                        effort = None if te == "off" else te
                    continue
                if rtype != "context.append_loop_event":
                    continue

                event = rec.get("event")
                if not isinstance(event, dict):
                    continue
                etype = event.get("type")

                if etype == "tool.call":
                    slot = pending.setdefault(event.get("stepUuid"),
                                              {"tools": [], "touched": []})
                    name = event.get("name")
                    if name:
                        slot["tools"].append(str(name)[:40])
                    args = event.get("args")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except (ValueError, TypeError):
                            args = None
                    if isinstance(args, dict):
                        for key in _PATH_ARGS:
                            val = args.get(key)
                            if isinstance(val, str) and val.startswith("/"):
                                repo, surface = topo.classify(val)
                                if repo and (repo, surface) not in slot["touched"]:
                                    slot["touched"].append((repo, surface))
                    continue

                if etype != "step.end":
                    continue

                usage = event.get("usage")
                if not isinstance(usage, dict) or not usage:
                    # A step the wire recorded with no usage at all (an
                    # interrupted or locally-served step) costs nothing and is
                    # not a billable turn — dropping it keeps turn counts honest.
                    pending.pop(event.get("uuid"), None)
                    continue

                turn += 1
                slot = pending.pop(event.get("uuid"), None) or {"tools": [], "touched": []}
                events.append(self._turn(rec, event, usage, turn, session_id,
                                         agent_id, workspace, model, cwd,
                                         effort, slot))
            offset = fh.tell()

        return events, _cursor(offset, turn, model, cwd, effort)

    def _turn(self, rec, event, usage, turn, session_id, agent_id, workspace,
              model, cwd, effort, slot):
        ev = blank_event(self.provider)
        ev["ts"] = _iso(rec.get("time"))
        ev["session"] = (session_id or "")[:8] or None
        ev["workspace"] = workspace
        ev["model"] = model
        ev["effort"] = effort
        ev["turn"] = turn
        ev["entrypoint"] = "cli"
        ev["stop"] = event.get("finishReason")

        is_sub = bool(agent_id) and agent_id != "main"
        ev["sidechain"] = is_sub
        ev["agent"] = agent_id if is_sub else None

        inp, out, cache_read, cache_create = _tokens(usage)
        ev["input"], ev["output"] = inp, out
        ev["cache_read"], ev["cache_create"] = cache_read, cache_create
        # The wire reports one undifferentiated cache-write counter. The
        # unsplit-write guard in analyze.py::cost_of prices a bare
        # cache_create at the cheaper 5m rate rather than overstating cost.
        ev["cache_1h"] = 0
        ev["cache_5m"] = 0

        ev["tools"] = slot["tools"]
        touched = slot["touched"]
        cwd_repo, _ = topo.split(cwd or "")
        ev["repo"] = topo.pick_repo(cwd_repo, touched)
        ev["surfaces"] = sorted({s for r, s in touched if r == ev["repo"] and s})
        ev["lane"] = topo.lane_of(repo=ev["repo"], entrypoint=ev["entrypoint"],
                                  provider=self.provider)
        return ev
