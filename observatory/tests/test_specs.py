#!/usr/bin/env python3
"""Fixture tests for declarative collector specs (ADR-009).

Every spec in `collectors/specs/` must have a fixture here in the vendor's real
record shape, and the test must assert an exact turn count. A parser asserted
against what the parser happens to expect passes forever while reading nothing,
which is the failure mode this file exists to prevent.

    python3 tests/test_specs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import paths as topo                        # noqa: E402
import pricing                              # noqa: E402
from collectors.generic import SpecCollector  # noqa: E402

# Attribution is the one part of the engine whose answer depends on the machine
# it runs on: `~/code` is a different directory for every user and every CI
# runner. Fixtures therefore carry a fixed absolute path and the test declares
# the roots that make it meaningful, so the assertion means the same thing
# everywhere. Reset in main().
FIXTURE_TOPOLOGY = {
    "code_roots": ["/home/dev/code"],
    "special_roots": {},
    "scratch_prefixes": ["/tmp/"],
    "worktree_marker": ".worktrees",
    "incidental_repos": [],
    "surface_rules": {"*": [["src/*", "src/{1}"]]},
    "lanes": {"default": "work", "rules": []},
}

FAILURES = []


def check(label, got, want):
    if got == want:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s\n         got:  %r\n         want: %r" % (label, got, want))
        FAILURES.append(label)


def collector_for(spec_name):
    spec = json.loads((HERE.parent / "collectors" / "specs" / spec_name).read_text())
    return SpecCollector(spec)


def test_example_openai_jsonl():
    """The worked example, against a fixture in the shape it documents."""
    print("\nspec: example-openai-jsonl.json")
    c = collector_for("example-openai-jsonl.json")
    events, cursor = c.collect(str(HERE / "fixtures" / "example.jsonl"), {})

    # Two assistant records carry usage; the system and user records do not.
    check("exactly the priced turns are emitted", len(events), 2)
    check("the cursor records the turn count", cursor["turn"], 2)
    check("re-reading from the cursor yields nothing new",
          c.collect(str(HERE / "fixtures" / "example.jsonl"), cursor)[0], [])

    a, b = events
    check("timestamp", a["ts"], "2026-08-19T01:02:11Z")
    check("session id is truncated, never the full conversation id", a["session"], "conv-abc")
    check("workspace is a basename, never a path", a["workspace"], "my-app")
    check("repo resolved from cwd", a["repo"], "my-app")
    check("surface resolved from the file the turn touched", a["surfaces"], ["src/api"])
    check("model", a["model"], "deepseek-v4-pro")
    check("tool names collected", a["tools"], ["read_file", "edit_file"])
    # input_is_total: 52000 total - 48000 cached - 3000 created = 1000 fresh.
    check("input has the cache components subtracted out", a["input"], 1000)
    check("cache_read", a["cache_read"], 48000)
    check("cache_create", a["cache_create"], 3000)
    check("output", a["output"], 880)
    check("stop reason", a["stop"], "tool_calls")
    check("entrypoint falls back to the spec default", a["entrypoint"], "cli")

    # No path may survive into an event, anywhere.
    blob = json.dumps(events)
    check("no absolute path reaches the event", "/root/code" in blob, False)

    # And the phase must follow the vendor's real schedule: 01:02 UTC is inside
    # DeepSeek's peak window, 12:05 UTC is not.
    p = pricing.load_pricing()
    check("first turn prices as peak", pricing.window_phase(a["model"], a["ts"], p), "peak")
    check("second turn prices as off-peak", pricing.window_phase(b["model"], b["ts"], p), "off-peak")


def test_gemini_cli():
    """Gemini CLI, against fixtures in the shape @google/gemini-cli-core declares.

    The record shape here is taken from that package's own `chatRecordingTypes`
    (MessageRecord / TokensSummary / ToolCallRecord) and the code in
    `chatRecordingService.recordMessageTokens` that fills it, at version 0.58.0
    — not from this parser, and not from memory. The two facts worth stating
    plainly, because everything else follows from them:

      * `tokens.input` is the API's `promptTokenCount`, which *includes*
        `cachedContentTokenCount`. Gemini CLI's own telemetry computes fresh
        input as `prompt - cached`, so the spec sets `input_is_total`.
      * No message record carries the session id. It is in the filename, and a
        subagent's transcript is nested under its parent session id — which is
        what `from_path` exists to read.
    """
    print("\nspec: gemini-cli.json")
    c = collector_for("gemini-cli.json")
    chats = HERE / "fixtures" / "gemini-cli" / "chats"
    main_file = str(chats / "session-2026-08-19T01-02-a1b2c3d4.jsonl")
    events, cursor = c.collect(main_file, {})

    # Six records: metadata, a user turn, two priced gemini turns, one gemini
    # turn with no usage yet, and a `$set` metadata update. Two are priced.
    check("exactly the priced turns are emitted", len(events), 2)
    check("the cursor records the turn count", cursor["turn"], 2)
    check("re-reading from the cursor yields nothing new",
          c.collect(main_file, cursor)[0], [])

    a, b = events
    check("timestamp", a["ts"], "2026-08-19T01:02:11.000Z")
    check("session comes from the filename, not the record", a["session"], "a1b2c3d4")
    check("model", a["model"], "gemini-2.5-pro")
    check("second turn keeps its own model", b["model"], "gemini-2.5-flash")
    check("tool names collected", a["tools"], ["read_file", "list_directory"])
    # input_is_total: 52000 prompt - 48000 cached - 0 created = 4000 fresh.
    check("input has the cached component subtracted out", a["input"], 4000)
    check("cache_read", a["cache_read"], 48000)
    check("output", a["output"], 880)
    check("no cache-creation concept, so it stays zero", a["cache_create"], 0)
    check("repo resolved from a tool argument, since no cwd is recorded",
          a["repo"], "my-app")
    # Two labels, because the turn touched that area two ways: `read_file` named
    # a file under src/api, and `list_directory` named the directory itself.
    # ADR-008 will not interpolate a path's last segment — in the case the rule
    # was written for that segment is a filename — so a directory argument lands
    # one level coarser. Both labels are true; asserting the pair keeps the
    # behaviour visible rather than letting a change to it pass unnoticed.
    check("surfaces resolved from what the turn touched",
          a["surfaces"], ["src", "src/api"])
    check("a main-session turn is not delegated work", a["sidechain"], False)
    check("entrypoint falls back to the spec default", a["entrypoint"], "cli")

    # A subagent transcript is nested under the parent session id, so its turns
    # roll up to the session that delegated them rather than inventing a new one.
    sub_file = str(chats / "9f8e7d6c-parent-session" / "subagent-explorer.jsonl")
    sub, _ = c.collect(sub_file, {})
    check("the subagent's priced turn is emitted", len(sub), 1)
    check("subagent rolls up to the parent session", sub[0]["session"], "9f8e7d6c")
    check("subagent turns are marked as delegated", sub[0]["sidechain"], True)
    check("subagent input is net of cache", sub[0]["input"], 2000)

    # No path may survive into an event, anywhere.
    blob = json.dumps(events + sub)
    check("no absolute path reaches the event", "/home/dev/code" in blob, False)


def test_example_json_per_file():
    """A whole JSON document per file — the shape one-file-per-message tools use.

    Three things this proves that the JSONL path never exercises: the document
    itself is the record, an epoch-millisecond time becomes the ISO-8601 stamp
    everything downstream parses, and the session id is read from the directory
    because no field in the record carries it.
    """
    print("\nspec: example-json-per-file.json")
    c = collector_for("example-json-per-file.json")
    box = HERE / "fixtures" / "example-json" / "storage" / "message" / "ses_9a8b7c6d"

    # A user message carries no usage, so it is never a priced turn.
    empty, _ = c.collect(str(box / "msg_0000.json"), {})
    check("a record with no usage is not a turn", empty, [])

    priced = str(box / "msg_0001.json")
    events, cursor = c.collect(priced, {})
    check("the document itself is the record", len(events), 1)
    check("the cursor records the turn count", cursor["turn"], 1)
    check("re-reading an unchanged file yields nothing new",
          c.collect(priced, cursor)[0], [])

    a = events[0]
    check("epoch millis became an ISO-8601 stamp", a["ts"], "2026-08-19T01:02:11.000Z")
    check("session comes from the directory, not the record", a["session"], "ses_9a8b")
    check("model", a["model"], "gemini-2.5-pro")
    check("stop reason", a["stop"], "tool-calls")
    # No input_is_total on this spec, so the counts are taken as reported.
    check("input", a["input"], 4000)
    check("cache_read", a["cache_read"], 48000)
    check("cache_create", a["cache_create"], 3000)
    check("output", a["output"], 880)
    check("tool name read out of the content array", a["tools"], ["read"])
    check("repo resolved from the tool argument", a["repo"], "my-app")
    check("surface resolved from the file the turn touched", a["surfaces"], ["src/api"])
    blob = json.dumps(events)
    check("no absolute path reaches the event", "/home/dev/code" in blob, False)


def test_example_json_array():
    """One document holding an array of records, resumed by count not offset."""
    print("\nspec: example-json-array.json")
    c = collector_for("example-json-array.json")
    hist = str(HERE / "fixtures" / "example-json-array" / "tasks" /
               "task-5f4e3d2c" / "api_conversation_history.json")

    events, cursor = c.collect(hist, {})
    # Four records: a user turn, two priced assistant turns, and one assistant
    # turn with no usage on it yet.
    check("exactly the priced turns are emitted", len(events), 2)
    check("the cursor counts priced records, not bytes", cursor["turn"], 2)
    check("re-reading an unchanged file yields nothing new",
          c.collect(hist, cursor)[0], [])
    check("a cursor from mid-file skips what it already emitted",
          len(c.collect(hist, {"offset": 0, "turn": 1})[0]), 1)

    a, b = events
    check("epoch seconds became an ISO-8601 stamp", a["ts"], "2026-08-19T02:00:07.000Z")
    check("session comes from the path", a["session"], "task-5f4")
    # input_is_total: 20000 prompt - 16000 cached - 0 created = 4000 fresh.
    check("input has the cached component subtracted out", a["input"], 4000)
    check("cache_read", a["cache_read"], 16000)
    check("second priced turn is the third record, not the second",
          b["ts"], "2026-08-19T02:05:30.000Z")
    check("entrypoint falls back to the spec default", a["entrypoint"], "ide")
    check("repo resolved from the tool argument", a["repo"], "my-app")
    blob = json.dumps(events)
    check("no absolute path reaches the event", "/home/dev/code" in blob, False)


def main():
    topo.use(FIXTURE_TOPOLOGY)
    try:
        for fn in (test_example_openai_jsonl, test_gemini_cli,
                   test_example_json_per_file, test_example_json_array):
            fn()
    finally:
        topo.use(None)
    print()
    if FAILURES:
        print("%d FAILURE(S): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
