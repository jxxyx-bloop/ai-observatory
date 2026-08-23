#!/usr/bin/env python3
"""AI Observatory — single entrypoint.

    python3 observe.py sync      # collect new events into data/  (zero tokens)
    python3 observe.py digest    # aggregate  -> data/digest.json
    python3 observe.py report    # render     -> dist/observatory.html
    python3 observe.py all       # sync + digest + report
    python3 observe.py insights  # print findings as text (for reading in a session)
    python3 observe.py demo      # fill the store with 60 days of synthetic usage
    python3 observe.py demo --purge   # remove that synthetic usage again
    python3 observe.py share     # build the opt-in community payload (never uploads)
    python3 observe.py setup      # the whole install, one command, ends in your browser
    python3 observe.py install    # create a double-clickable launcher + daily sync
    python3 observe.py doctor     # check the setup and say how to fix what is wrong

Flags: --no-open (never launch a browser or the app)  --notify (desktop notification)
       --remove (with `install`, undo it)
       --no-dock (with `install`/`setup`, do not pin to the Dock)
       --no-daily (with `install`, skip the scheduled refresh)
       --html (with `doctor`, emit a page instead of text)

Stdlib only. No network. Read-only against every provider.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import analyze  # noqa: E402
import demo as demo_mod  # noqa: E402
import insights as insights_mod  # noqa: E402
import launcher  # noqa: E402
import normalize  # noqa: E402
import pricing as price  # noqa: E402
import render  # noqa: E402
import settings  # noqa: E402
import share as share_mod  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
DIST = ROOT / "dist"
DIGEST = DATA / "digest.json"

# A command's third answer, alongside 0 and a failing code: it declined to do
# its own work and nothing is wrong. `main` prints the reason and carries on
# down the argv line rather than dropping the commands typed after it.
DECLINED = 3


def _write_atomic(path, text: str) -> None:
    """Write through a temporary file in the same directory, then rename.

    Two refreshes can now land on the same second — the login-time agent and a
    double-clicked launcher both run `sync digest report`. Two processes writing
    digest.json a chunk at a time can leave a half-file that neither would
    recognise; os.replace is atomic within a filesystem, so the worst case
    becomes one of the two complete versions winning.
    """
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def cmd_sync(argv) -> int:
    summary = normalize.sync(DATA, full="--full" in argv)
    if summary["events_written"]:
        (DATA / ".demo").unlink(missing_ok=True)
    print(f"sync: {summary['events_written']} new events from "
          f"{summary['sources_scanned']} sources ({summary['mode']})")
    return 0


def cmd_demo(argv) -> int:
    """Seed the store with synthetic usage so the dashboard can be seen at once.

    Writes to a separate partition prefix and refuses to mix with real events —
    a demo that quietly contaminates someone's own history would be worse than
    no demo at all. `--purge` is the way back out for a store that took the
    `--force` route anyway.
    """
    if "--purge" in argv or "--clear" in argv:
        removed = normalize.purge_synthetic(DATA)
        print(f"demo: removed {removed:,} synthetic events. "
              f"Re-run `python3 observe.py digest report` to rebuild.")
        return 0
    if any(DATA.glob("events-*.ndjson")) and "--force" not in argv:
        print("demo: data/ already holds real events — leaving them alone. "
              "Sample data is only ever for an empty store, and a dashboard "
              "built from your own numbers is the better one. `demo --force` "
              "seeds synthetic events on top anyway; `demo --purge` removes "
              "them again.")
        return DECLINED
    DATA.mkdir(parents=True, exist_ok=True)
    events = demo_mod.generate()
    written = normalize.write_events(DATA, events)
    # A sentinel rather than a flag inside the events: `digest` and `report` are
    # separate processes on the cron path, and sample data that stops announcing
    # itself between two of them is the worst bug this tool could ship.
    (DATA / ".demo").write_text("synthetic usage — safe to delete\n", encoding="utf-8")
    print(f"demo: wrote {written:,} synthetic events across 60 days. "
          f"Now run `python3 observe.py digest report`.")
    return 0


def cmd_share(argv) -> int:
    digest = _load_digest()
    if digest is None:
        return 1
    payload = share_mod.build(digest)
    out = DATA / "share-payload.json"
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(share_mod.describe(payload))
    print(f"\nWritten to {out.relative_to(ROOT)}. Nothing has been uploaded — "
          f"`share` only ever writes a file. See docs/specs/Community-Share-Protocol.md.")
    return 0


def cmd_digest(argv) -> int:
    pricing = analyze.load_pricing()
    digest = analyze.build_digest(normalize.read_events(DATA), pricing)
    if not digest["totals"]["turns"]:
        print("digest: no events found — run `observe.py sync` first")
        return 1
    digest["findings"] = insights_mod.generate(digest, pricing)
    digest["settings"] = _display_settings(digest)
    digest["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    digest["pricing_verified_on"] = pricing.get("_verified_on")
    DATA.mkdir(parents=True, exist_ok=True)
    _write_atomic(DIGEST, json.dumps(digest, indent=1))
    kb = DIGEST.stat().st_size / 1024
    # `setup` narrates its own phases; a second voice printing over them turns a
    # guided install back into a wall of output.
    if "--quiet" in argv:
        return 0
    print(f"digest: {digest['totals']['turns']:,} turns, "
          f"{len(digest['sessions']):,} sessions, {len(digest['findings'])} findings "
          f"-> {DIGEST.relative_to(ROOT)} ({kb:.0f} KB)")
    return 0


def _display_settings(digest: dict) -> dict:
    """Everything the rendered page needs to speak the user's units.

    Resolved here, once, rather than in the browser: the HTML is a
    self-contained artefact that may be opened on a machine that has never seen
    settings.json, and a dashboard that silently falls back to USD-in-UTC on
    someone else's laptop is a dashboard that lies.
    """
    cfg = settings.load()
    plans = price.load_plans()
    code = cfg.get("currency", "USD")
    cur = plans["currencies"].get(code) or plans["currencies"]["USD"]
    # Anchored to the newest event rather than to now, so the axis is labelled
    # with the offset the data was actually recorded under. They differ only
    # across a DST changeover, which is exactly when a page rendered in
    # November would otherwise mislabel a summer heatmap.
    last = (digest.get("window") or {}).get("last")
    at = None
    if last:
        try:
            at = datetime.fromisoformat(last).replace(tzinfo=timezone.utc)
        except ValueError:
            at = None
    offset = settings.local_offset(at).total_seconds() / 3600
    out = {
        "tz_offset_hours": offset,
        "tz_label": settings.timezone_label(at),
        "tz_auto": settings.timezone_is_auto(),
        "tz_name": settings.timezone_name() if settings.timezone_is_auto() else None,
        "currency": code,
        "symbol": cur["symbol"],
        "per_usd": cur["per_usd"],
        "decimals": cur["decimals"],
        "plan": cfg.get("plan", "none"),
    }
    plan_id = cfg.get("plan", "none")
    if plan_id and plan_id != "none":
        out["plan_value"] = price.plan_value(
            digest["totals"]["cost"], plan_id, digest["window"].get("days") or 1, plans)
    return out


def _load_digest():
    if not DIGEST.exists():
        print("no digest yet — run `observe.py digest` first")
        return None
    return json.loads(DIGEST.read_text(encoding="utf-8"))


def cmd_report(argv) -> int:
    """Render, then open.

    A command whose last act is printing a path asks a human to go find a file,
    which is the single largest piece of friction in this tool's first run. It
    now ends with a browser window instead. `--no-open` is for the unattended
    paths — cron, launchd, CI — where a browser must never appear.
    """
    digest = _load_digest()
    if digest is None:
        return 1
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / "observatory.html"
    _write_atomic(out, render.render(
        digest, refresh=launcher.refresh_command(ROOT),
        demo=(DATA / ".demo").exists()))
    kb = out.stat().st_size / 1024
    if "--no-open" in argv:
        print(f"report: {out} ({kb:.0f} KB)")
    elif launcher.open_report(out):
        print(f"report: {out} ({kb:.0f} KB) — opened in your browser")
    else:
        print(f"report: {out} ({kb:.0f} KB) — open it in a browser")
    if "--notify" in argv:
        totals = digest.get("totals") or {}
        launcher.notify(
            "AI Observatory",
            f"Dashboard refreshed — {totals.get('turns', 0):,} turns, "
            f"{len(digest.get('findings') or [])} findings.")
    return 0


def cmd_doctor(argv) -> int:
    """Check the setup and say, in order, how to fix whatever is wrong.

    `--html` emits the same checks as a page. That is what the generated
    launcher shows when it cannot run: somebody who double-clicked an icon has
    no terminal open, so a traceback is not a message they can act on.
    """
    problems = launcher.doctor(ROOT)
    if "--html" in argv:
        print(launcher.error_page(problems, ROOT))
        return 0
    bad = 0
    for p in problems:
        print(f"{'✓' if p['ok'] else '✕'} {p['title']}\n    {p['detail']}")
        if not p["ok"]:
            bad += 1
            if p["fix"]:
                print(f"    -> {p['fix']}")
    print(f"\n{len(problems) - bad}/{len(problems)} checks passed.")
    if not bad:
        print(f"Refresh anytime with: {launcher.refresh_command(ROOT)}")
    return 0


def cmd_install(argv) -> int:
    """Create the launcher, then actually start it.

    The first version of this printed three lines and exited, which is the same
    mistake `report` used to make one level up: a setup command whose only
    evidence of success is a receipt. Nobody can tell a working install from a
    silent no-op that way. So it now ends by revealing the app in Finder and
    launching it — the dashboard opens, and the icon they will click tomorrow is
    on screen, selected, ready to drag to the Dock.

    Everything written lives under `$HOME`, nothing is downloaded, and
    `--remove` undoes all of it. See `launcher.py` for why a generated bundle
    needs no code signing.
    """
    if "--remove" in argv:
        for line in launcher.uninstall():
            print(line)
        return 0

    created = launcher.install(ROOT, daily="--no-daily" not in argv)
    print("Installed:")
    for line in created:
        print(f"  {line}")
    if "--no-dock" not in argv:
        print(f"  {launcher.add_to_dock()}")

    if "--no-open" in argv:
        print("\nOpen it from ~/Applications, or run this command without "
              "--no-open to have it launch itself.")
        return 0

    launcher.reveal()
    print("\nOpening it now — this is exactly what a double-click does.")
    if not launcher.launch():
        print("Could not launch it automatically. Open ~/Applications and "
              "double-click AI Observatory.")
        return 0

    print("\nFrom now on: click the AI Observatory icon. It refreshes, then opens.")
    if not launcher.in_dock():
        print("It is not in your Dock — drag it there from the Finder window "
              "to keep it one click away.")
    print("Undo everything:  python3 observe.py install --remove")
    return 0


def cmd_setup(argv) -> int:
    """The whole install, as one command, ending in a browser.

    Anyone who reaches this has already seen the demo — that is what the demo is
    for. So setup does not mean "look at sample data", it means "put this on my
    machine, with my numbers", and asking for three separate pastes to get there
    was three chances to stop.

    It narrates each phase as it goes. A command that prints nothing for eight
    seconds while it reads three hundred transcript files is indistinguishable
    from one that has hung, and the person watching cannot tell which.

    Nothing here deletes anything. A store seeded by an earlier `demo` run is
    reported, not rewritten.
    """
    step = [0]

    def phase(title):
        step[0] += 1
        print(f"\n{step[0]}/5  {title}")

    def ok(msg):
        print(f"      \u2713 {msg}")

    def warn(msg):
        print(f"      ! {msg}")

    print("AI Observatory \u2014 setting up")

    # 1 ── the machine ------------------------------------------------------
    phase("Checking your machine")
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 9):
        print(f"      \u2717 Python {major}.{minor} is too old \u2014 3.9 or newer is "
              f"needed.\n        Install a current Python from python.org, then "
              f"run this again.")
        return 1
    ok(f"Python {major}.{minor}")
    # Worth its own line: the most common reason people put off a Python tool is
    # expecting a dependency mess that never arrives.
    ok("Nothing to install \u2014 standard library only")
    tools = next((c for c in launcher.doctor(ROOT)
                  if c["title"].startswith("At least one")), None)
    if tools and tools["ok"]:
        ok(tools["detail"])
    else:
        warn("No AI coding tools found here yet \u2014 continuing anyway")

    # 2 ── the code ---------------------------------------------------------
    phase("Updating to the latest version")
    ok(launcher.update(ROOT))

    # 3 ── collection, the slow part ----------------------------------------
    phase("Reading the transcripts already on this disk")
    print("      nothing is uploaded, and no tokens are spent")
    if (DATA / ".demo").exists():
        warn("Sample data from an earlier look is still here \u2014 your dashboard "
             "will keep saying so")
    summary = normalize.sync(DATA, full="--full" in argv)
    ok(f"{summary['events_written']:,} new events from "
       f"{summary['sources_scanned']:,} sources")

    if not any(DATA.glob("events-*.ndjson")):
        # Ending on an empty page would defeat the one promise this command
        # makes, which is that you finish it looking at something.
        warn("Nothing to read yet \u2014 adding 60 days of sample data so you have "
             "a dashboard to look at")
        normalize.write_events(DATA, demo_mod.generate())
        (DATA / ".demo").write_text("synthetic usage \u2014 safe to delete\n",
                                    encoding="utf-8")

    # 4 ── the dashboard ----------------------------------------------------
    phase("Building your dashboard")
    if cmd_digest(argv + ["--quiet"]):
        return 1
    digest = _load_digest()
    ok(f"{digest['totals']['turns']:,} turns, {len(digest['sessions']):,} sessions, "
       f"{len(digest.get('findings') or [])} findings")

    # 5 ── keeping it -------------------------------------------------------
    phase("Putting it in your Dock")
    for line in launcher.install(ROOT, daily="--no-daily" not in argv):
        ok(" ".join(line.split()))
    if "--no-dock" not in argv:
        ok(launcher.add_to_dock().replace("dock", "", 1).strip())

    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / "observatory.html"
    _write_atomic(out, render.render(digest, refresh=launcher.refresh_command(ROOT),
                                     demo=(DATA / ".demo").exists()))

    print("\nDone. Opening your dashboard now.")
    if not launcher.open_report(out):
        print(f"Could not open a browser \u2014 the file is at {out}")
    print("\nTomorrow: click the AI Observatory icon in your Dock. It refreshes, "
          "then opens.")
    print("Undo everything:  python3 observe.py install --remove")
    return 0


def cmd_insights(argv) -> int:
    digest = _load_digest()
    if digest is None:
        return 1
    for f in digest.get("findings", []):
        saving = f.get("est_monthly_saving_usd")
        tag = f" (~${saving}/mo)" if saving else ""
        print(f"\n[{f['severity'].upper()}] {f['title']}{tag}")
        print(f"  {f['finding']}")
        print(f"  -> {f['action']}")
    return 0


def cmd_all(argv) -> int:
    return cmd_sync(argv) or cmd_digest(argv) or cmd_report(argv)


COMMANDS = {
    "sync": cmd_sync, "digest": cmd_digest, "report": cmd_report,
    "insights": cmd_insights, "all": cmd_all, "demo": cmd_demo,
    "share": cmd_share, "doctor": cmd_doctor, "install": cmd_install,
    "setup": cmd_setup,
}


def main(argv) -> int:
    """Run every command named on the argv line, in order.

    `observe.py digest report` is one process and one import of the pricing
    tables rather than two, which matters on the daily cron path.

    A command that fails still stops the line — rendering a report over a failed
    sync would publish a number nobody can stand behind. What it no longer does
    is stop quietly: it names the commands it dropped. A chain that prints one
    line and returns to the prompt is indistinguishable from a chain that hung,
    and leaves the reader guessing which half of what they typed actually ran.

    `DECLINED` is the third answer, for a command that refused its own work with
    nothing wrong — `demo` against a store that already holds real events. The
    rest of the line is still exactly what was asked for, so it runs. The exit
    code is the last command's, so a bare `demo` still reports the refusal to a
    script while `demo digest report` exits 0 on the dashboard it built.
    """
    names = [a for a in argv[1:] if not a.startswith("-")] or ["all"]
    rc = 0
    for i, name in enumerate(names):
        fn = COMMANDS.get(name)
        if fn is None:
            print(__doc__)
            return 2
        rc = fn(argv)
        if rc == DECLINED:
            continue
        if rc:
            dropped = names[i + 1:]
            if dropped:
                print(f"stopped at `{name}` (exit {rc}) — "
                      f"did not run: {', '.join(dropped)}")
            return rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
