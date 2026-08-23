#!/usr/bin/env python3
"""AI Observatory — single entrypoint.

    python3 observe.py sync      # collect new events into data/  (zero tokens)
    python3 observe.py digest    # aggregate  -> data/digest.json
    python3 observe.py report    # render     -> dist/observatory.html
    python3 observe.py all       # sync + digest + report
    python3 observe.py insights  # print findings as text (for reading in a session)
    python3 observe.py demo      # fill the store with 60 days of synthetic usage
    python3 observe.py share     # build the opt-in community payload (never uploads)
    python3 observe.py install    # create a double-clickable launcher + daily sync
    python3 observe.py doctor     # check the setup and say how to fix what is wrong

Flags: --no-open (never launch a browser or the app)  --notify (desktop notification)
       --remove (with `install`, undo it)   --dock (with `install`, pin to the Dock)
       --no-daily (with `install`, skip the scheduled refresh)
       --html (with `doctor`, emit a page instead of text)

Stdlib only. No network. Read-only against every provider.
"""

from __future__ import annotations

import json
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
    no demo at all.
    """
    if any(DATA.glob("events-*.ndjson")) and "--force" not in argv:
        print("demo: data/ already holds events. Re-run with --force to add "
              "synthetic ones anyway, or use a clean checkout.")
        return 1
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
    DIGEST.write_text(json.dumps(digest, indent=1), encoding="utf-8")
    kb = DIGEST.stat().st_size / 1024
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
    offset = float(cfg.get("timezone_offset_hours", 8))
    sign = "+" if offset >= 0 else "-"
    whole = int(abs(offset))
    minutes = int(round((abs(offset) - whole) * 60))
    out = {
        "tz_offset_hours": offset,
        "tz_label": "UTC%s%d%s" % (sign, whole, ":%02d" % minutes if minutes else ""),
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
    out.write_text(render.render(
        digest, refresh=launcher.refresh_command(ROOT),
        demo=(DATA / ".demo").exists()), encoding="utf-8")
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
    if "--dock" in argv:
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
    if "--dock" not in argv and not launcher.in_dock():
        print("Keep it one click away — drag it from the Finder window to your "
              "Dock, or re-run with --dock to pin it automatically.")
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
}


def main(argv) -> int:
    """Run every command named on the argv line, in order, stopping on failure.

    `observe.py digest report` is one process and one import of the pricing
    tables rather than two, which matters on the daily cron path.
    """
    names = [a for a in argv[1:] if not a.startswith("-")] or ["all"]
    for name in names:
        fn = COMMANDS.get(name)
        if fn is None:
            print(__doc__)
            return 2
        rc = fn(argv)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
