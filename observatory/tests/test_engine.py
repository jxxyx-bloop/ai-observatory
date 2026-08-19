#!/usr/bin/env python3
"""Engine tests — stdlib only, no framework, `python3 tests/test_engine.py`.

Covers the three things that would be expensive to get wrong and cheap to
regress: the cost model (including the peak/off-peak windows, which no other
tracker implements and so no other tracker's tests can be borrowed for), path
attribution, and the privacy boundary on the community payload.

Exit 0 is a pass. Deliberately no pytest: a contributor should be able to run
these on a fresh machine with nothing installed.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analyze          # noqa: E402
import demo             # noqa: E402
import insights         # noqa: E402
import normalize        # noqa: E402
import paths as topo    # noqa: E402
import pricing          # noqa: E402
import share            # noqa: E402

FAILURES = []


def check(label, got, want):
    if got == want:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s\n         got:  %r\n         want: %r" % (label, got, want))
        FAILURES.append(label)


def ok(label, condition, detail=""):
    check(label + (" — " + detail if detail and not condition else ""), bool(condition), True)


# --- pricing ---------------------------------------------------------------

def test_window_phase():
    print("\npeak/off-peak windows")
    p = pricing.load_pricing()
    # DeepSeek: peak 01:00-04:00 and 06:00-10:00 UTC, every day.
    check("deepseek 02:30 UTC is peak",
          pricing.window_phase("deepseek-v4-pro", "2026-08-19T02:30:00Z", p), "peak")
    check("deepseek 05:00 UTC is off-peak (the gap between windows)",
          pricing.window_phase("deepseek-v4-pro", "2026-08-19T05:00:00Z", p), "off-peak")
    check("deepseek 12:00 UTC is off-peak",
          pricing.window_phase("deepseek-v4-pro", "2026-08-19T12:00:00Z", p), "off-peak")
    # GLM: peak only 14:00-18:00 UTC+8 on weekdays == 06:00-10:00 UTC Mon-Fri.
    check("glm Wed 07:00 UTC is peak",
          pricing.window_phase("glm-5.1", "2026-08-19T07:00:00Z", p), "peak")
    check("glm Sat 07:00 UTC is off-peak (weekends are never peak)",
          pricing.window_phase("glm-5.1", "2026-08-22T07:00:00Z", p), "off-peak")
    # A vendor with no schedule is 'flat', which is NOT the same as 'off-peak':
    # nothing could have been saved by moving it.
    check("anthropic is flat, not off-peak",
          pricing.window_phase("claude-opus-5", "2026-08-19T07:00:00Z", p), "flat")
    # Offsets in the stamp must be honoured, not truncated.
    check("+08:00 stamps are converted to UTC before the window is read",
          pricing.window_phase("glm-5.1", "2026-08-19T15:00:00+08:00", p), "peak")


def test_cost():
    print("\ncost model")
    p = pricing.load_pricing()
    peak = {"model": "deepseek-v4-pro", "ts": "2026-08-19T02:30:00Z",
            "input": 1_000_000, "output": 1_000_000}
    off = dict(peak, ts="2026-08-19T12:00:00Z")
    check("peak-hour turn is priced at the listed rate", round(pricing.cost_of(peak, p), 4), 5.28)
    check("same turn off-peak is half", round(pricing.cost_of(off, p), 4), 2.64)
    check("counterfactual matches actually running it off-peak",
          round(pricing.counterfactual_cost(peak, p, "off-peak"), 4),
          round(pricing.cost_of(off, p), 4))
    flat = {"model": "claude-opus-5", "ts": "2026-08-19T02:30:00Z",
            "input": 1_000_000, "output": 1_000_000}
    check("counterfactual is a no-op for a flat-priced model",
          pricing.counterfactual_cost(flat, p, "off-peak"), pricing.cost_of(flat, p))
    # Per-vendor cache economics: Moonshot does not use Anthropic's 0.1x.
    kimi = {"model": "kimi-k2.6", "ts": "2026-08-19T12:00:00Z", "cache_read": 1_000_000}
    expect = 1_000_000 * (0.95 / 1_000_000) * 0.0737
    check("kimi cache reads use the vendor's own multiplier, not 0.1x",
          round(pricing.cost_of(kimi, p), 6), round(expect, 6))
    check("a dated model snapshot resolves to its alias",
          pricing.canonical_model("claude-haiku-4-5-20251001"), "claude-haiku-4-5")
    check("an alias hop resolves", pricing.canonical_model("deepseek-v3"), "deepseek-chat")
    unknown = {"model": "some-model-nobody-has-heard-of", "output": 1_000_000}
    ok("an unknown model falls back rather than crashing", pricing.cost_of(unknown, p) > 0)


def test_plan_value():
    print("\nplan value")
    v = pricing.plan_value(400.0, "glm-coding-lite", 30)
    check("plan multiple", v["multiple"], round(400.0 / 18.0, 2))
    check("healthy plan reads as excellent", v["verdict"], "excellent")
    under = pricing.plan_value(5.0, "claude-max-20x", 30)
    ok("a plan returning less than it costs is called under-used",
       under["verdict"] == "under-used")
    metered = pricing.plan_value(400.0, "none", 30)
    ok("pay-as-you-go still reports the API-equivalent",
       metered["api_equivalent_usd_month"] == 400.0)
    ok("pay-as-you-go has no multiple — there is no subscription to divide by",
       "multiple" not in metered)
    check("an unknown plan id yields nothing at all",
          pricing.plan_value(400.0, "no-such-plan", 30), {})


# --- attribution -----------------------------------------------------------

# A topology stated by the test rather than inherited from the host. `~/code`
# is a different directory for every user and every CI runner, and the shipped
# `scratch_prefixes` include /tmp — so a runner whose HOME sits under /tmp would
# correctly classify the whole fixture as scratch and fail a test that had
# nothing to do with scratch handling.
FIXTURE_TOPOLOGY = {
    "code_roots": ["/home/dev/code"],
    "special_roots": {"/home/dev/.claude": "claude-config"},
    "scratch_prefixes": ["/tmp/claude-", "/private/tmp/claude-"],
    "worktree_marker": ".worktrees",
    "incidental_repos": ["scratchpad", "claude-config"],
    "surface_rules": {
        "claude-config": [["skills/*", "skills"]],
        "*": [["src/*", "src/{1}"], ["packages/*", "package:{1}"]],
    },
    "lanes": {"default": "work", "rules": [{"repo": "dotfiles", "lane": "personal"}]},
}


def test_paths():
    print("\npath attribution")
    topo.use(FIXTURE_TOPOLOGY)
    try:
        check("a source file lands in its repo and folder",
              topo.classify("/home/dev/code/my-app/src/api/routes.py"), ("my-app", "src/api"))
        check("a monorepo package becomes its own bucket",
              topo.classify("/home/dev/code/my-app/packages/ui/Button.tsx"),
              ("my-app", "package:ui"))
        check("a top-level file is (root), not the filename",
              topo.classify("/home/dev/code/my-app/README.md"), ("my-app", "(root)"))
        check("a worktree is attributed to its parent repo",
              topo.classify("/home/dev/code/my-app/.worktrees/feat-x/src/db/pool.go"),
              ("my-app", "src/db"))
        check("a special root is named rather than left unattributed",
              topo.classify("/home/dev/.claude/skills/foo/SKILL.md"),
              ("claude-config", "skills"))
        check("a temp path is one flat scratch bucket",
              topo.classify("/tmp/claude-abc/notes.md"), ("scratchpad", "scratch files"))
        check("an unknown path is honestly unattributed, not guessed",
              topo.classify("/opt/somewhere/else/file.py"), (None, None))
        check("a real repo outranks an incidental one",
              topo.pick_repo("scratchpad", [("my-app", "src")]), "my-app")
        check("an incidental repo still stands alone when nothing else ran",
              topo.pick_repo("scratchpad", []), "scratchpad")
    finally:
        topo.use(None)

    # One assertion against the topology the repo actually ships, so a broken
    # default config cannot pass every test by virtue of never being loaded.
    cfg = topo.config()
    ok("the shipped topology declares code roots", len(cfg["code_roots"]) > 0)
    ok("the shipped topology expands ~ to an absolute path",
       all(r.startswith("/") for r in cfg["_roots"]))


# --- privacy boundary ------------------------------------------------------

def test_share_payload():
    print("\ncommunity payload privacy boundary")
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        normalize.write_events(data, demo.generate(days=20))
        p = pricing.load_pricing()
        digest = analyze.build_digest(normalize.read_events(data), p)
        digest["findings"] = insights.generate(digest, p)

    payload = share.build(digest)
    check("payload declares its version", payload["v"], share.PAYLOAD_VERSION)
    check("no forbidden key appears anywhere in the payload", share.audit(payload), [])

    blob = json.dumps(payload)
    for secret in ("checkout-service", "growth-web", "data-platform", "infra-tooling"):
        ok("repo name %r never reaches the payload" % secret, secret not in blob)
    ok("no session id reaches the payload",
       not any(s["session"] in blob for s in digest["sessions"][:40]))

    # Metrics must be bucket indices, never raw values. A raw turn count would
    # be a fingerprint; a bucket index is a habit.
    for name, idx in payload["metrics"].items():
        ok("%s is a bucket index" % name,
           isinstance(idx, int) and 0 <= idx < len(share.BUCKETS[name]))
    ok("the whole payload stays small enough to read before consenting",
       len(blob) < 4096, "%d bytes" % len(blob))

    # Turning on repo sharing must still not emit a name.
    import settings
    settings._CACHE = dict(settings.load())
    settings._CACHE["community"] = dict(settings._CACHE["community"], include_repo_names=True)
    opted = share.build(digest)
    ok("repo_shape carries hashed buckets, never names",
       all(isinstance(x, int) for x in opted.get("repo_shape", [])))
    ok("even opted in, no repo name appears",
       "checkout-service" not in json.dumps(opted))
    settings._CACHE = None


# --- end to end ------------------------------------------------------------

def test_pipeline():
    print("\nfull pipeline over the demo fixture")
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        events = demo.generate(days=30)
        written = normalize.write_events(data, events)
        check("every generated event is stored", written, len(events))
        p = pricing.load_pricing()
        digest = analyze.build_digest(normalize.read_events(data), p)
        check("turn count survives the round trip", digest["totals"]["turns"], len(events))
        ok("the cube carries the phase dimension", "phase" in digest["cube"]["dims"])
        ok("the cube carries the off-peak floor", "cost_floor_micro" in digest["cube"]["metrics"])
        ok("a peak premium is computed", digest["peak_premium_usd"] >= 0)

        # The floor can never exceed the actual cost: off-peak is a discount.
        ix = {d: i for i, d in enumerate(digest["cube"]["dims"])}
        n = len(digest["cube"]["dims"])
        mix = {m: n + i for i, m in enumerate(digest["cube"]["metrics"])}
        over = [r for r in digest["cube"]["rows"]
                if r[mix["cost_floor_micro"]] > r[mix["cost_micro"]] + 1]
        ok("no cube row prices off-peak above peak", not over, "%d rows" % len(over))

        findings = insights.generate(digest, p)
        ok("detectors produce findings", len(findings) > 0)
        for f in findings:
            for key in ("id", "severity", "title", "finding", "action", "evidence", "confidence"):
                ok("finding %s has %s" % (f.get("id"), key), key in f)
        ok("findings are sorted most severe first",
           [f["severity"] for f in findings] ==
           sorted((f["severity"] for f in findings),
                  key=lambda s: {"high": 0, "medium": 1, "low": 2, "info": 3}.get(s, 9)))


def main():
    for fn in (test_window_phase, test_cost, test_plan_value, test_paths,
               test_share_payload, test_pipeline):
        fn()
    print()
    if FAILURES:
        print("%d FAILURE(S): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
