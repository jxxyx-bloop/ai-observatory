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

import pricing                              # noqa: E402
from collectors.generic import SpecCollector  # noqa: E402

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


def main():
    for fn in (test_example_openai_jsonl,):
        fn()
    print()
    if FAILURES:
        print("%d FAILURE(S): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
