#!/usr/bin/env python3
"""Tests for `observe.py contribute`.

Two properties, and the first one is the reason this file exists.

**Safe.** The fixture this command writes is meant to be pasted into a public
pull request. So the test plants the things a real transcript actually carries
— a prompt, an employer's project name, a branch, an email, a credential, an
absolute path, a session id, a real timestamp — and asserts that none of them
survive. Redaction is an allow-list, so a new field added upstream cannot leak
by default; this test is what keeps that true.

**Useful.** A scaffold that is safe and wrong wastes the contributor's evening
and ours. So the spec it infers is run against the fixture it redacted, and
must find the priced turns with the right numbers on them.

    python3 tests/test_contribute.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import contribute                              # noqa: E402
import paths as topo                           # noqa: E402
from collectors.generic import SpecCollector   # noqa: E402

FIXTURE_TOPOLOGY = {
    "code_roots": ["/home/dev/code"],
    "special_roots": {},
    "scratch_prefixes": ["/tmp/"],
    "worktree_marker": ".worktrees",
    "incidental_repos": [],
    "surface_rules": {"*": [["src/*", "src/{1}"]]},
    "lanes": {"default": "work", "rules": []},
}

# Everything a real transcript carries that must never reach a public repo.
SECRETS = {
    "prompt text": "refactor the ACME payroll tax calculator",
    "completion text": "The bug is in the bonus proration",
    "employer project": "acme-payroll",
    "branch name": "feature/q3-payroll-hotfix",
    "email address": "jiayi.lee@acme-internal.example",
    "credential": "sk-live-9d8f7a6b5c4d3e2f1a0b",
    "home directory path": "/Users/jiayi/work",
    "session id": "8f14e45f-ceea-467a-9f2b-3c1d7a9e0b44",
    "working hours": "2026-09-05T14:37",
}

TRANSCRIPT = [
    {"role": "user", "conversation_id": "8f14e45f-ceea-467a-9f2b-3c1d7a9e0b44",
     "created_at": "2026-09-05T14:37:25Z",
     "content": "refactor the ACME payroll tax calculator, it miscomputes Q3 bonuses",
     "author_email": "jiayi.lee@acme-internal.example"},
    {"role": "assistant", "conversation_id": "8f14e45f-ceea-467a-9f2b-3c1d7a9e0b44",
     "created_at": "2026-09-05T14:37:31Z", "model": "acme-coder-v2",
     "finish_reason": "tool_calls", "branch": "feature/q3-payroll-hotfix",
     "workspace": {"path": "/Users/jiayi/work/acme-payroll", "repo": "acme-payroll"},
     "content": "The bug is in the bonus proration.",
     "api_key": "sk-live-9d8f7a6b5c4d3e2f1a0b",
     "usage": {"prompt_tokens": 52000, "completion_tokens": 880,
               "prompt_tokens_details": {"cached_tokens": 48000,
                                         "cache_creation_tokens": 3000}},
     "tool_calls": [{"type": "function", "function": {
         "name": "read_file",
         "parsed_arguments": {"file_path": "/Users/jiayi/work/acme-payroll/src/api/tax.py"}}}]},
    {"role": "assistant", "conversation_id": "8f14e45f-ceea-467a-9f2b-3c1d7a9e0b44",
     "created_at": "2026-09-05T14:41:03Z", "model": "acme-coder-v2",
     "finish_reason": "stop", "content": "Fixed it.",
     "usage": {"prompt_tokens": 9000, "completion_tokens": 210,
               "prompt_tokens_details": {"cached_tokens": 6000,
                                         "cache_creation_tokens": 0}}},
]

FAILURES = []


def check(label, got, want):
    if got == want:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s\n         got:  %r\n         want: %r" % (label, got, want))
        FAILURES.append(label)


def _write(tmp: Path) -> str:
    source = tmp / "session-8f14e45f.jsonl"
    source.write_text("".join(json.dumps(r) + "\n" for r in TRANSCRIPT),
                      encoding="utf-8")
    return str(source)


def test_nothing_private_survives(built):
    """The property that makes this command safe to run at all."""
    print("\nredaction")
    blob = json.dumps(built["fixture"])
    for name, secret in SECRETS.items():
        check("%s is gone" % name, secret in blob, False)

    # Not merely absent — replaced. A path has to become a *usable* path or the
    # fixture cannot exercise `path_args` at all.
    check("a path became the synthetic one",
          contribute.FAKE_PATH in blob, True)
    check("free text became a placeholder", "<redacted>" in blob, True)

    # And the counts, which are the entire point, are untouched.
    priced = [r for r in built["fixture"] if r.get("usage", {}).get("prompt_tokens")]
    check("token counts are kept verbatim",
          [r["usage"]["prompt_tokens"] for r in priced], [52000, 9000])
    check("a model name is kept — it names a mechanism, not a person",
          priced[0]["model"], "acme-coder-v2")


def test_inference_is_right(built):
    """A scaffold that is safe and wrong is still a waste of an evening."""
    print("\ninference")
    fields = built["spec"]["fields"]
    check("input", fields.get("input"), "usage.prompt_tokens")
    check("output", fields.get("output"), "usage.completion_tokens")
    check("cache_read", fields.get("cache_read"),
          "usage.prompt_tokens_details.cached_tokens")
    check("cache_create", fields.get("cache_create"),
          "usage.prompt_tokens_details.cache_creation_tokens")
    # `cache_creation_tokens` contains the letters "at". A substring test for a
    # time-shaped key picks it as the timestamp and the draft reads nothing.
    check("timestamp is the stamp, not a token count named ...creation...",
          fields.get("ts"), "created_at")
    check("model", fields.get("model"), "model")
    check("where discriminates the priced record",
          built["spec"].get("where"), {"role": "assistant"})
    check("tool name found a step down, under `function`",
          built["spec"]["tools"]["name"], "function.name")
    check("tool args found the same way",
          built["spec"]["tools"]["args"], "function.parsed_arguments")
    # `jsonl` also starts with `json`; the draft must not claim a JSON document.
    check("a JSONL source is not labelled a JSON document",
          "format" in built["spec"], False)
    check("no ts_unit, because the stamp is a string",
          "ts_unit" in built["spec"], False)
    check("input_is_total is never guessed",
          "input_is_total" in built["spec"], False)


def test_round_trip(built):
    """The draft spec, run against the fixture it redacted."""
    print("\nround trip")
    spec = dict(built["spec"], provider="acme", roots=["/dev/null"])
    with tempfile.TemporaryDirectory() as box:
        path = Path(box) / "fixture.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in built["fixture"]),
                        encoding="utf-8")
        events, cursor = SpecCollector(spec).collect(str(path), {})

    check("both priced turns are found", len(events), 2)
    check("cursor counts them", cursor["turn"], 2)
    check("input", events[0]["input"], 52000)
    check("output", events[0]["output"], 880)
    check("cache_read", events[0]["cache_read"], 48000)
    check("cache_create", events[0]["cache_create"], 3000)
    check("tool name", events[0]["tools"], ["read_file"])
    # The synthetic path is the one the fixture topology resolves, so a
    # generated fixture attributes a repo the moment it is dropped into a test.
    check("repo resolves from the synthetic path", events[0]["repo"], "my-app")
    check("surface resolves too", events[0]["surfaces"], ["src/api"])


def main():
    topo.use(FIXTURE_TOPOLOGY)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            built = contribute.build(_write(Path(tmp)))
        check("every record was read", built["records_seen"], 3)
        test_nothing_private_survives(built)
        test_inference_is_right(built)
        test_round_trip(built)
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
