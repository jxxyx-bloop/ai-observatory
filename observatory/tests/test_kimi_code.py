#!/usr/bin/env python3
"""Regression test for the Kimi Code collector — `python3 engine/tests/test_kimi_code.py`.

Stdlib only, no framework, exit code 0 = pass. It exists because this collector
shipped twice against a *guessed* wire.jsonl schema and silently produced zero
events both times: a collector that finds nothing looks identical to a provider
you haven't used. The fixture below is the schema verified on 2026-08-10 against
the installed `kimi` binary (wire protocol 1.4/1.5). If Kimi changes the wire
format this test fails loudly instead of the dashboard quietly losing a provider.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

T = 1754540000000
CWD = "/Users/someone/code/example-repo"
WD_KEY = "wd_example-repo_8c81e94c57a7"


def _le(t, event):
    return {"type": "context.append_loop_event", "time": t, "event": event}


def _usage(i, o, r, c):
    return {"inputOther": i, "output": o, "inputCacheRead": r,
            "inputCacheCreation": c}


def _dump(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records),
                    encoding="utf-8")


def build_fixture(home: Path) -> None:
    """A Kimi home carrying all three layouts the collector must handle."""
    (home / "workspaces.json").write_text(json.dumps({"version": 1, "workspaces": {
        WD_KEY: {"root": CWD, "name": "example-repo"}}}), encoding="utf-8")
    sess = home / "sessions" / WD_KEY / "sess-abcdef123456"

    _dump(sess / "agents" / "main" / "wire.jsonl", [
        {"type": "metadata", "protocol_version": "1.4", "created_at": T},
        {"type": "config.update", "time": T, "modelAlias": "kimi-for-coding",
         "cwd": CWD, "thinkingEffort": "off"},
        {"type": "context.append_message", "time": T + 100,
         "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}},
        _le(T + 200, {"type": "step.begin", "uuid": "s1", "step": 1, "turnId": 1}),
        _le(T + 300, {"type": "tool.call", "stepUuid": "s1", "toolCallId": "c1",
                      "name": "Read", "args": {"file_path": CWD + "/a.md"}}),
        _le(T + 900, {"type": "step.end", "uuid": "s1", "turnId": 1, "step": 1,
                      "usage": _usage(1200, 340, 8000, 500),
                      "finishReason": "tool_use"}),
        {"type": "config.update", "time": T + 1000, "modelAlias": "k3",
         "thinkingEffort": "high"},
        _le(T + 1200, {"type": "step.end", "uuid": "s2", "turnId": 2, "step": 1,
                       "usage": _usage(50, 900, 0, 0), "finishReason": "end_turn"}),
        # No usage at all: an interrupted step, not a billable turn.
        _le(T + 1300, {"type": "step.end", "uuid": "s3", "turnId": 3, "step": 1,
                       "finishReason": "cancelled"}),
    ])
    _dump(sess / "agents" / "agent-1" / "wire.jsonl", [
        {"type": "config.update", "time": T,
         "modelAlias": "kimi-for-coding-highspeed"},
        _le(T + 400, {"type": "step.end", "uuid": "x1", "turnId": 1, "step": 1,
                      "usage": _usage(10, 20, 30, 0), "finishReason": "end_turn"}),
    ])
    # v1 legacy: wire.jsonl at the session root, no agents/ directory.
    _dump(home / "sessions" / "wd_ssc-sre-skills_a2c583297438" / "sess-legacy00"
          / "wire.jsonl", [
        {"type": "config.update", "time": T, "modelAlias": "kimi-k2.6"},
        _le(T + 500, {"type": "step.end", "uuid": "l1", "turnId": 1, "step": 1,
                      "usage": _usage(7, 8, 0, 0), "finishReason": "end_turn"}),
    ])


FAILURES = []
CHECKED = []


def check(label, got, want):
    CHECKED.append(label)
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def run(home: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from collectors.kimi_code import KimiCodeCollector  # noqa: E402

    c = KimiCodeCollector()
    check("available", c.available(), True)
    sources = c.sources()
    check("sources found (2 per-agent + 1 legacy root)", len(sources), 3)

    events, cursors = [], {}
    for src in sources:
        evs, cursors[src] = c.collect(src, {})
        events.extend(evs)
    check("billable turns (the usage-less step is dropped)", len(events), 4)

    by_model = {e["model"]: e for e in events}
    check("models seen", sorted(by_model), ["kimi-k2.6", "kimi-k2.7-code",
                                            "kimi-k2.7-code-highspeed", "kimi-k3"])

    first = by_model["kimi-k2.7-code"]
    # The four TokenUsage components are already split — nothing is netted off.
    check("uncached input", first["input"], 1200)
    check("output", first["output"], 340)
    check("cache read", first["cache_read"], 8000)
    check("cache create", first["cache_create"], 500)
    check("epoch-ms time -> ISO", first["ts"], "2025-08-07T04:13:20Z")
    check("workspace", first["workspace"], "example-repo")
    check("tools", first["tools"], ["Read"])
    check("entrypoint", first["entrypoint"], "cli")

    # config.update carries the model, so a later switch must take effect.
    check("effort after switch", by_model["kimi-k3"]["effort"], "high")
    sub = by_model["kimi-k2.7-code-highspeed"]
    check("sub-agent flagged", (sub["sidechain"], sub["agent"]), (True, "agent-1"))
    check("legacy root log workspace", by_model["kimi-k2.6"]["workspace"],
          "ssc-sre-skills")

    # Incremental: a turn appended after the last config.update still prices.
    main = [s for s in sources if s.endswith("main/wire.jsonl")][0]
    with open(main, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(_le(T + 9000, {
            "type": "step.end", "uuid": "s9", "turnId": 9, "step": 1,
            "usage": _usage(5, 6, 7, 0), "finishReason": "end_turn"})) + "\n")
    more, _ = c.collect(main, cursors[main])
    check("incremental turns", len(more), 1)
    check("model carried across the cursor", more[0]["model"], "kimi-k3")
    check("turn numbering continues", more[0]["turn"], 3)


def main() -> int:
    home = Path(tempfile.mkdtemp(prefix="kimi-fixture-"))
    try:
        build_fixture(home)
        import os
        os.environ["KIMI_CODE_HOME"] = str(home)
        run(home)
    finally:
        shutil.rmtree(home, ignore_errors=True)
    for line in FAILURES:
        print("FAIL  " + line)
    print("%s — %d check(s)" % ("FAILED" if FAILURES else "ok", len(CHECKED)))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
