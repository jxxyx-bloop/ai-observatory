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
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analyze          # noqa: E402
import demo             # noqa: E402
import insights         # noqa: E402
import normalize        # noqa: E402
import paths as topo    # noqa: E402
import pricing          # noqa: E402
import share            # noqa: E402
import launcher         # noqa: E402
import updater          # noqa: E402

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


# --- shipped page ----------------------------------------------------------

def test_hidden_guards():
    """Every element that ships `hidden` must actually stay hidden.

    An author `display` rule beats the browser's own `[hidden]{display:none}`,
    so a class that sets `display` turns the attribute into decoration and the
    element renders on every page. That is how the sample-data chip came to sit
    on dashboards built from real numbers. The dashboard smoke test stands up a
    stub DOM with no CSS at all and cannot see it, so the check is here: read
    the markup, read the stylesheet, and fail on the combination.
    """
    print("\nhidden-attribute guards")
    assets = Path(__file__).resolve().parent.parent / "assets"
    html = (assets / "page.html").read_text(encoding="utf-8")
    css = "\n".join((assets / f).read_text(encoding="utf-8")
                    for f in ("tokens.css", "app.css"))
    # Selectors and bodies. A body cannot contain a brace, so this walks past
    # @media wrappers on its own rather than needing a real parser.
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css)

    hidden = re.findall(r"<\w+([^>]*\shidden(?:\s[^>]*)?)>", html)
    ok("markup still ships hidden elements", len(hidden) > 0)
    for attrs in hidden:
        classes = re.search(r'class="([^"]*)"', attrs)
        eid = re.search(r'id="([^"]*)"', attrs)
        who = eid.group(1) if eid else (classes.group(1) if classes else "?")
        for name in ["." + c for c in (classes.group(1).split() if classes else [])]:
            sets_display = any(
                re.search(re.escape(name) + r"(?![\w-])", sel) and "display:" in body
                and "[hidden]" not in sel
                for sel, body in rules)
            guarded = any(
                name + "[hidden]" in sel and "display:none" in body.replace(" ", "")
                for sel, body in rules)
            ok("%s (%s) stays hidden" % (who, name), guarded or not sets_display,
               "%s sets display, so [hidden] needs a %s[hidden]{display:none} guard"
               % (name, name))


# --- updates ---------------------------------------------------------------

def _git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=T",
         "-c", "commit.gpgsign=false", "-C", str(cwd), *args],
        capture_output=True, text=True, timeout=60)


def _commit(repo, name, body, subject):
    (repo / name).write_text(body, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-m", subject)


def test_updater():
    """Fetch/apply against two real repositories on disk — no network.

    A clone from a local path gets a real upstream, so every branch below is
    the one that runs on somebody's laptop rather than a mock of it. The point
    of the split is that `check` never changes the working tree and `apply`
    never touches the network; both halves are asserted here because a bug in
    either one is invisible until the day somebody's checkout stops updating.
    """
    print("\nupdates")
    if not shutil.which("git"):
        print("  ok   (skipped — git not installed)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        origin, work, data = tmp / "origin", tmp / "work", tmp / "work" / "data"
        origin.mkdir()
        _git(origin, "init", "--quiet")
        _commit(origin, "a.txt", "one\n", "First commit")
        subprocess.run(["git", "clone", "--quiet", str(origin), str(work)],
                       capture_output=True, timeout=60)

        ok("a fresh clone is not behind", updater.pending(work)["behind"] == 0)
        ok("a clone has a version", updater.version(work) != "unknown")
        ok("a directory that is not a checkout says so",
           updater.pending(tmp)["blocked"] == "not a git checkout")

        _commit(origin, "b.txt", "two\n", "Second commit")
        _commit(origin, "c.txt", "three\n", "Third commit")
        # Nothing has been fetched yet, so the clone cannot know.
        check("blind to unfetched commits", updater.pending(work)["behind"], 0)

        state = updater.check(work, data)
        check("check finds both commits", state["behind"], 2)
        check("check reads their subjects", state["lines"],
              ["Second commit", "Third commit"])
        ok("check reached the remote", state.get("reachable"))
        ok("check leaves the working tree alone", not (work / "b.txt").exists())
        ok("check writes its state", (data / updater.STATE_NAME).exists())

        ready = updater.for_render(state)
        check("a waiting update renders as ready", ready["state"], "ready")
        check("and carries the count", ready["count"], 2)

        after = updater.apply(work, data)
        check("apply fast-forwards", after["behind"], 0)
        ok("apply brings the files", (work / "c.txt").exists())
        check("apply records what arrived", after["applied"]["count"], 2)

        receipt = updater.for_render(after)
        check("the receipt shows straight after", receipt["state"], "applied")
        check("and names the changes", receipt["lines"],
              ["Second commit", "Third commit"])
        stale = dict(after)
        stale["applied"] = dict(after["applied"],
                                at="2020-01-01T00:00:00Z")
        ok("but not a day later", updater.for_render(stale) is None)
        ok("and a waiting update outranks a fresh receipt",
           updater.for_render(dict(after, behind=1))["state"] == "ready")
        ok("and nothing is said when there is nothing to say",
           updater.for_render({"behind": 0}) is None)

        # A tracked edit is the one thing that must never be fast-forwarded
        # over. git refuses per-file; this asserts we surface that rather than
        # swallowing it.
        _commit(origin, "a.txt", "one, changed\n", "Fourth commit")
        (work / "a.txt").write_text("mine\n", encoding="utf-8")
        blocked = updater.check(work, data)
        check("a dirty tree is reported, not hidden", blocked["blocked"],
              "local changes")
        held = updater.apply(work, data)
        check("and the update is held", held["behind"], 1)
        check("with the local edit intact",
              (work / "a.txt").read_text(encoding="utf-8"), "mine\n")
        check("the page is told why", updater.for_render(held)["blocked"],
              "local changes")


# --- collection integrity --------------------------------------------------

class _FakeCollector:
    """A byte-offset collector, in miniature: it respects the cursor it is given.

    That is the whole point of the test. A collector that ignores its cursor
    duplicates under any sync, and one that respects it duplicates only when
    the sync forgets to record what it consumed — which is the bug this
    guards.
    """

    provider = "fake"

    def __init__(self, boom=None, sources=("A", "B")):
        self.boom = boom
        self._sources = list(sources)

    def available(self):
        return True

    def sources(self):
        return list(self._sources)

    def collect(self, source, cursor):
        if source == self.boom:
            raise RuntimeError("transcript format changed under us")
        if cursor.get("offset"):
            return [], cursor                      # already consumed
        events = [{"ts": "2026-08-0%dT10:00:00Z" % (i + 1), "provider": "fake",
                   "model": "claude-opus-5", "session": "%s%d" % (source, i),
                   "input": 10, "output": 5} for i in range(3)]
        return events, {"offset": 99}


def test_sync_integrity():
    """One failing collector, an interrupted run, and two syncs at once.

    Every assertion here is a bug that shipped: an exception in one provider
    aborted collection for all of them, an interrupted run left events on disk
    with no cursor to say they had been read, and two syncs starting in the
    same second both appended the same turns. None of the three announced
    itself — they arrive as numbers that are quietly too big.
    """
    print("\ncollection integrity")
    real = normalize.COLLECTORS
    try:
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"

            # One source raises; the other still gets collected and committed.
            normalize.COLLECTORS = [_FakeCollector(boom="B")]
            first = normalize.sync(data)
            check("a failing source does not abort the run",
                  first["events_written"], 3)
            check("and is reported rather than swallowed",
                  [f["source"] for f in first["failed"]], ["B"])
            ok("the run still succeeded", first["skipped"] is None)

            # The interrupted source is retried; the committed one is not.
            normalize.COLLECTORS = [_FakeCollector()]
            second = normalize.sync(data)
            check("the failed source is picked up next run",
                  second["events_written"], 3)
            rows = list(normalize.read_events(data))
            check("and nothing is counted twice", len(rows), 6)
            check("with every event distinct",
                  len({r["session"] for r in rows}), 6)

            # A third run has nothing left to do — the cursors were recorded.
            third = normalize.sync(data)
            check("a settled store writes nothing", third["events_written"], 0)
            check("and stays the size it was",
                  len(list(normalize.read_events(data))), 6)

            # Two syncs at once: the second stands down rather than duplicating.
            normalize.COLLECTORS = [_FakeCollector(sources=("C",))]
            with normalize.store_lock(data) as held:
                ok("the first holder gets the store", held)
                blocked = normalize.sync(data)
                check("the second stands down", blocked["skipped"],
                      "another sync is already running")
                check("and writes nothing at all", blocked["events_written"], 0)
            after = normalize.sync(data)
            check("the lock is released with the run",
                  after["events_written"], 3)

            # `--full` re-reads every transcript from byte zero. Appending that
            # to a store that already holds those turns doubled it on every
            # run — and it is the command somebody reaches for precisely when
            # they suspect their numbers are wrong.
            before = len(list(normalize.read_events(data)))
            normalize.COLLECTORS = [_FakeCollector(sources=("A", "B", "C"))]
            refull = normalize.sync(data, full=True)
            check("a full re-read writes nothing new",
                  refull["events_written"], 0)
            check("and says what it recognised",
                  refull["duplicates_skipped"], before)
            check("leaving the store the size it was",
                  len(list(normalize.read_events(data))), before)

            # The repair path, for a store damaged before any of this landed.
            normalize.write_events(data, list(normalize.read_events(data))[:4])
            check("damage is visible",
                  len(list(normalize.read_events(data))), before + 4)
            fixed = normalize.dedupe(data)
            check("dedupe removes exactly the copies", fixed["removed"], 4)
            check("and keeps every original", fixed["kept"], before)
            check("a second pass finds nothing",
                  normalize.dedupe(data)["removed"], 0)
    finally:
        normalize.COLLECTORS = real


# --- honest pricing --------------------------------------------------------

def test_unpriced_disclosure():
    """A model with no published rate must be visible as a guess.

    The fallback rate is the right default — a model missing from a JSON file
    should not silently cost nothing — but before this the guess and the
    published rate rendered identically, and 300 turns of an unknown model
    produced a confident three-figure total nobody could question.
    """
    print("\nunpriced models")
    p = pricing.load_pricing()
    ok("a known model is priced", pricing.is_priced("claude-opus-5", p))
    ok("a dated snapshot is priced", pricing.is_priced("claude-haiku-4-5-20251001", p))
    ok("an invented one is not", not pricing.is_priced("brand-new-model-9", p))

    events = [dict(e, model="brand-new-model-9") if i % 2 else e
              for i, e in enumerate(demo.generate()[:400])]
    d = analyze.build_digest(iter(events), p)
    d["findings"] = insights.generate(d, p)
    check("unpriced turns are counted", d["unpriced"]["turns"], 200)
    check("and their models named", d["unpriced"]["models"], ["brand-new-model-9"])
    ok("their cost is non-zero", d["unpriced"]["cost"] > 0)
    found = [f for f in d["findings"] if f["id"] == "unpriced-models"]
    check("the page is told", len(found), 1)
    ok("with no saving attached — it is an error bar, not a lever",
       "est_monthly_saving_usd" not in found[0])
    ok("and the share quoted",
       0 < found[0]["evidence"]["share_of_spend_pct"] <= 100)

    # The placeholder Claude Code writes on internal turns is not a model
    # anyone chose, and a turn with no tokens costs nothing at any rate. Both
    # reached the finding on a real store and produced a disclosure about
    # 0.0% of the spend.
    noise = [dict(e, model="<synthetic>", input=0, output=0, cache_create=0,
                  cache_read=0, cache_1h=0, cache_5m=0)
             for e in demo.generate()[:50]]
    quiet = analyze.build_digest(iter(noise), p)
    quiet["findings"] = insights.generate(quiet, p)
    check("the internal placeholder is not an unpriced model",
          quiet["unpriced"]["turns"], 0)
    ok("so no disclosure is raised for it",
       not [f for f in quiet["findings"] if f["id"] == "unpriced-models"])

    clean = analyze.build_digest(iter(demo.generate()[:400]), p)
    clean["findings"] = insights.generate(clean, p)
    check("a fully priced store says nothing", clean["unpriced"]["turns"], 0)
    ok("and raises no finding",
       not [f for f in clean["findings"] if f["id"] == "unpriced-models"])


# --- the launch surface ----------------------------------------------------

def _doctor_row(rows, title_starts):
    for r in rows:
        if r["title"].startswith(title_starts):
            return r
    return None


def test_doctor_install_checks():
    """The macOS-only checks, exercised from a machine that is not a Mac.

    Everything below is invisible on the platform CI runs on, which is exactly
    why it is asserted here: a check that only executes on the maintainer's
    laptop is a check nobody runs. The platform gate and the three filesystem
    facts it reads are stubbed; the logic between them is the real thing.

    The one worth having is the second: the launcher bakes its checkout path
    in at install time, so a project folder moved afterwards leaves an icon
    that still opens, still refreshes, and refreshes something else.
    """
    print("\nlaunch-surface checks")
    check("a runner's path is read back out of it",
          launcher.runner_root('#!/bin/sh\nset -u\nROOT="/Users/x/code/obs"\n'),
          "/Users/x/code/obs")
    ok("and a script without one says so",
       launcher.runner_root("#!/bin/sh\necho hi\n") is None)

    real = (launcher.platform.system, launcher.app_dir, launcher.plist_path,
            launcher.LOG, launcher._launchctl_says)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root, bundle = tmp / "checkout", tmp / "AI Observatory.app"
            runner = bundle / "Contents" / "MacOS" / "run"
            plist, log = tmp / "agent.plist", tmp / "sync.log"
            root.mkdir()

            launcher.platform.system = lambda: "Darwin"
            launcher.app_dir = lambda: bundle
            launcher.plist_path = lambda: plist
            launcher.LOG = log
            launcher._launchctl_says = lambda *a: ""

            rows = []
            launcher._install_checks(root, lambda ok_, t, d, f="":
                                     rows.append({"ok": ok_, "title": t}))
            ok("a machine with nothing installed is told so",
               _doctor_row(rows, "The launcher is installed")["ok"] is False)
            ok("and that nothing is scheduled",
               _doctor_row(rows, "The daily refresh is scheduled")["ok"] is False)

            # Installed, but pointed at a folder that has since been renamed.
            runner.parent.mkdir(parents=True)
            runner.write_text('ROOT="%s"\n' % (tmp / "somewhere-else"),
                              encoding="utf-8")
            rows = []
            launcher._install_checks(root, lambda ok_, t, d, f="":
                                     rows.append({"ok": ok_, "title": t}))
            ok("an installed launcher is found",
               _doctor_row(rows, "The launcher is installed")["ok"])
            ok("but a moved project folder is caught",
               _doctor_row(rows, "The launcher points at")["ok"] is False)

            # Everything wired up, agent loaded, and it has run at least once.
            runner.write_text('ROOT="%s"\n' % root, encoding="utf-8")
            plist.write_text("<plist/>", encoding="utf-8")
            log.write_text("ran\n", encoding="utf-8")
            launcher._launchctl_says = lambda *a: "- 0 " + launcher.LAUNCHD_LABEL
            rows = []
            launcher._install_checks(root, lambda ok_, t, d, f="":
                                     rows.append({"ok": ok_, "title": t}))
            ok("a healthy install passes every check", all(r["ok"] for r in rows))
            check("and there are four of them", len(rows), 4)

            # Loaded, but launchd has never actually fired it.
            log.unlink()
            rows = []
            launcher._install_checks(root, lambda ok_, t, d, f="":
                                     rows.append({"ok": ok_, "title": t}))
            ok("an agent that never ran is named",
               _doctor_row(rows, "The daily refresh has actually run")["ok"] is False)
    finally:
        (launcher.platform.system, launcher.app_dir, launcher.plist_path,
         launcher.LOG, launcher._launchctl_says) = real


def main():
    for fn in (test_window_phase, test_cost, test_plan_value, test_paths,
               test_share_payload, test_pipeline, test_hidden_guards,
               test_updater, test_sync_integrity, test_unpriced_disclosure,
               test_doctor_install_checks):
        fn()
    print()
    if FAILURES:
        print("%d FAILURE(S): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
