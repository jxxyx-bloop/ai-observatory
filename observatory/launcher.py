"""Launch surface — how a non-technical person opens this thing twice.

The dashboard is a file, not a server ([ADR-002], [ADR-013]). That is the right
call and this module does not relitigate it: a server's failure mode is a blank
`ERR_CONNECTION_REFUSED` page, which a beginner cannot recover from, while a
file's failure mode is *stale numbers* — a page that is still there and can
therefore explain itself. Everything below exists to make the second failure
mode visible and the first one impossible.

Three jobs:

1. **Open the report.** A command's last act should be a browser window, never a
   printed path. `observe.py report` used to end by telling a human to go find a
   file; now it opens it.

2. **Generate a launcher.** On macOS this writes `~/Applications/AI
   Observatory.app` — a shell script in a bundle, about 3 KB, no Electron and no
   GUI stack. The load-bearing detail is that it is *generated locally rather
   than downloaded*: `com.apple.quarantine` is set by the downloading agent, so
   an app written by a local process launches with no Gatekeeper prompt, no code
   signing, no notarisation and no Apple Developer account. That is the entire
   cost ADR-013 priced desktop packaging at, avoided by not shipping a binary.

3. **Diagnose.** `doctor()` returns the same structured checks that `observe.py
   doctor` prints and that `error_page()` renders. When the launcher fails, the
   user gets a styled page explaining what broke and what to click — never a
   traceback. A person who double-clicks an icon has no terminal open and no
   reason to acquire one.

Nothing here runs at import time and every filesystem write is inside `$HOME`,
reversible with `observe.py install --remove`. The one network call is
`update()`, which `setup` runs once and which delegates to `updater` — the
generated launcher and the daily agent call `observe.py` directly for that,
so nothing on the collect → analyse → render path reaches out.
"""

from __future__ import annotations

import os
import platform
import plistlib
import shutil
import struct
import subprocess
import sys
import urllib.parse
import webbrowser
import zlib
from datetime import datetime
from pathlib import Path

import home

import normalize
import pricing
import settings
import updater

APP_NAME = "AI Observatory"
LAUNCHD_LABEL = "dev.aiobservatory.sync"
ACCENT = (79, 70, 229)          # --accent, docs/design/DESIGN-SYSTEM.md
LOG = Path.home() / "Library" / "Logs" / "ai-observatory.log"


# ── paths and commands ──────────────────────────────────────────────────────

def tilde(path: Path) -> str | None:
    """`/Users/someone/code/x` -> `~/code/x`, or None when outside $HOME.

    Absolute paths carry the account name, and the rendered dashboard is meant
    to be e-mailable and attachable to a PR (ADR-013). Anything this module
    stamps into the page goes through here first, so a shared report says
    `~/code/x` rather than naming its author. Outside `$HOME` there is no safe
    abbreviation, so callers fall back to a generic instruction instead.
    """
    try:
        rel = path.resolve().relative_to(Path.home().resolve())
    except (ValueError, OSError):
        return None
    return "~/" + rel.as_posix()


def refresh_command(root: Path) -> str:
    """The one line that re-collects and re-renders, safe to show anyone.

    Installed from PyPI there is no `observe.py` to `cd` to, and printing a
    path that does not exist is worse than printing nothing — the line appears
    on a stale dashboard, where the reader's whole job is to copy it.
    """
    if not home.is_checkout():
        return "ai-observatory all"
    short = tilde(root / "observatory")
    if short is None:
        return "python3 observe.py all"
    return f"cd {short} && python3 observe.py all"


def report_path(root: Path) -> Path:
    return root / "dist" / "observatory.html"


def open_report(path: Path) -> bool:
    """Open the rendered file in the default browser.

    `webbrowser` is stdlib and picks the right thing on all three platforms.
    A failure here is never fatal — the file is still on disk and the caller
    prints where — so this reports rather than raises.
    """
    try:
        return bool(webbrowser.open(path.resolve().as_uri()))
    except Exception:
        return False


# ── doctor ──────────────────────────────────────────────────────────────────

def doctor(root: Path) -> list[dict]:
    """Every failure we have an actual answer for, checked in order.

    Each entry is `{ok, title, detail, fix}`. The list is the single source for
    three surfaces: the `doctor` command, the generated app's error page, and
    the troubleshooting section of the docs. One definition, three renderings —
    the same rule ADR-013 applies to metrics.
    """
    out = []

    def add(ok, title, detail, fix=""):
        out.append({"ok": bool(ok), "title": title, "detail": detail, "fix": fix})

    major, minor = sys.version_info[:2]
    add(major == 3 and minor >= 9,
        "Python 3.9 or newer",
        f"Found Python {major}.{minor}.",
        "macOS ships Python 3. If this fails you are likely on an old system "
        "Python — install a current one from python.org and try again.")

    # Only meaningful for the generated launcher, which calls `observe.py` by
    # path. Installed from PyPI the entry point is resolved by the shell and a
    # missing checkout is not a fault to report.
    if home.is_checkout():
        engine = root / "observatory" / "observe.py"
        add(engine.exists(),
            "The engine is where the launcher expects it",
            f"Looking for {tilde(engine) or engine}.",
            "The project folder was moved or renamed after install. Re-run "
            "`python3 observe.py install` from its new location to repoint the app.")

    data = root / "data"
    events = sorted(data.glob("events-*.ndjson")) if data.exists() else []
    add(bool(events),
        "Collected usage exists",
        f"{len(events)} month file(s) in {tilde(data) or data}."
        if events else "No events collected yet.",
        "Run `python3 observe.py sync` to read your local transcripts, or "
        "`python3 observe.py demo` to fill the store with 60 sample days.")

    add((data / "digest.json").exists(),
        "A digest has been built",
        "data/digest.json is present." if (data / "digest.json").exists()
        else "data/digest.json is missing.",
        "Run `python3 observe.py digest`.")

    rp = report_path(root)
    add(rp.exists(),
        "A dashboard has been rendered",
        f"{tilde(rp) or rp}" if rp.exists() else "dist/observatory.html is missing.",
        "Run `python3 observe.py report`.")

    # Collection reads provider transcript directories. When every one of them
    # is absent the sync is not broken, it is simply looking at a machine that
    # has never run an AI coding tool — which is a different message.
    homes = [Path.home() / ".claude" / "projects",
             Path.home() / ".codex" / "sessions",
             Path.home() / ".kimi", Path.home() / ".gemini"]
    seen = [h for h in homes if h.exists()]
    add(bool(seen),
        "At least one AI coding tool has run on this machine",
        f"{len(seen)} provider directory(ies) found." if seen
        else "No provider transcript directories found.",
        "Nothing to collect yet — this is expected on a fresh machine. Use "
        "`python3 observe.py demo` to see the product with sample data.")

    # Damage from before the collection fixes does not repair itself, and its
    # only symptom is numbers that are too big — which looks exactly like a
    # busy month. Cheap enough to check here, where somebody is already asking
    # what is wrong.
    try:
        keys, rows = set(), 0
        for ev in normalize.read_events(data):
            rows += 1
            keys.add(normalize.event_key(ev))
        dupes = rows - len(keys)
    except OSError:
        dupes = 0
    add(not dupes,
        "Every turn is counted once",
        f"{dupes:,} duplicate turn(s) in the store — every number is that much "
        f"too big." if dupes else "No duplicate turns.",
        "Run `python3 observe.py dedupe`, then `python3 observe.py digest report`.")

    # Every dollar figure rests on the rate card. A promotional rate whose
    # documented end has passed keeps pricing - the vendor has not said what
    # replaced it - but somebody has to look, and nothing else on the page will
    # tell them. A malformed boundary is worse: it silently mis-dates a price.
    try:
        card = pricing.load_pricing()
        broken = pricing.validate_card(card)
        overdue = pricing.review_due(card)
    except (OSError, ValueError, KeyError) as exc:
        broken, overdue = ["the rate card could not be read (%s)" % exc], []
    if broken:
        detail = "; ".join(broken[:3]) + (" ..." if len(broken) > 3 else "")
    elif overdue:
        detail = "; ".join("%s: a rate documented to end %s has not been re-checked"
                           % (m, t[:10]) for m, t in overdue)
    else:
        detail = "No rate is past its re-check date and every price change is dated."
    add(not broken and not overdue,
        "The rate card is current",
        detail,
        "Check the vendor's pricing page, update observatory/pricing.json (move the old "
        "rate into `history` if the price changed), and move `_verified_on`. "
        "CONTRIBUTING.md has the five-minute version.")

    _install_checks(root, add)

    # Reads refs already on disk — `check-update` is what puts them there, and
    # doctor must stay runnable on a plane. A checkout with no git, or no
    # upstream to compare against, is not a fault: it is somebody who installed
    # from a zip, and there is nothing here for them to act on.
    waiting = updater.pending(root)
    add(not waiting["behind"],
        "Running the latest version",
        f"{waiting['behind']} update(s) downloaded and waiting."
        if waiting["behind"] else f"Version {updater.version(root)}.",
        "Open the app from your Dock — it applies on launch. Or run "
        "`python3 observe.py update`."
        + (" Commit or stash your local changes first."
           if waiting.get("blocked") == "local changes" else ""))

    # One rewrite here covers the `doctor` command, the app's error page and
    # the docs, because all three read this list.
    for check in out:
        check["detail"] = home.retarget(check["detail"])
        check["fix"] = home.retarget(check["fix"])
    return out


def runner_root(script: str) -> str | None:
    """The checkout an installed runner is pointed at, read back out of it.

    The path is baked in at install time, which is what makes the launcher
    independent of any shell PATH — and also what makes a moved project folder
    silent: the icon still opens, still refreshes, and refreshes something
    else. Parsed rather than assumed, because the whole point is to catch the
    case where it disagrees with where we are now.
    """
    for line in script.splitlines():
        line = line.strip()
        if line.startswith("ROOT="):
            return line[5:].strip().strip('"').strip("'") or None
    return None


def _runner_verbs(script: str) -> set:
    """The engine subcommands an installed runner actually invokes.

    Compared instead of the file, because two things in a generated launcher
    are baked in at install time and legitimately differ from whatever is
    running `doctor`: the interpreter path and the project path. What must not
    differ is the work. A runner generated before `update` existed still
    opens the dashboard and still refreshes it — it just never applies
    anything — and every other check in this block passes while it does.
    """
    verbs = set()
    for line in script.splitlines():
        if line.strip().startswith("#"):
            continue
        _, sep, tail = line.partition("observe.py")
        if not sep:
            continue
        for token in tail.lstrip('"').lstrip("'").split():
            if not token[:1].isalpha():
                break
            verbs.add(token)
    return verbs


def _plist_verbs(text: str) -> set:
    """The same question for the scheduled job, whose args are a plist array."""
    try:
        args = plistlib.loads(text.encode("utf-8")).get("ProgramArguments") or []
    except Exception:
        return set()
    verbs, past_engine = set(), False
    for arg in (str(a) for a in args):
        if not past_engine:
            past_engine = arg.endswith("observe.py")
            continue
        if arg[:1].isalpha():
            verbs.add(arg)
    return verbs


def _launchctl_says(*args) -> str:
    try:
        done = subprocess.run(["launchctl", *args], check=False,
                              capture_output=True, text=True, timeout=30)
        return (done.stdout or "") + (done.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return ""


def _install_checks(root: Path, add) -> None:
    """Is the thing they click actually installed, wired up, and running?

    `doctor` could say everything about the data and nothing about the surface
    that fetches it. Somebody whose numbers stopped moving has no way to tell
    an empty week from an agent that never loaded, and those have opposite
    fixes. macOS only: nothing below exists on the platforms that get a script
    beside the project instead (ADR-018).
    """
    if platform.system() != "Darwin":
        return

    bundle = app_dir()
    runner = bundle / "Contents" / "MacOS" / "run"
    add(runner.exists(),
        "The launcher is installed",
        f"{tilde(bundle) or bundle}" if runner.exists()
        else "No app bundle in ~/Applications.",
        "Run `python3 observe.py install` to create it.")

    if runner.exists():
        try:
            pointed = runner_root(runner.read_text(encoding="utf-8"))
        except OSError:
            pointed = None
        same = bool(pointed) and Path(pointed).resolve() == root.resolve()
        add(same,
            "The launcher points at this checkout",
            f"It refreshes {tilde(Path(pointed)) or pointed}."
            if pointed else "Could not read the path out of the launcher.",
            "The project folder was moved or renamed after install, so the "
            "icon is refreshing somewhere else. Re-run `python3 observe.py "
            "install` from here to repoint it.")

    # A launcher generated by an older checkout keeps working, and that is what
    # makes it quiet: it opens, it refreshes, and it silently does not do
    # whatever `install` learned to do since. Every check around this one
    # passes while it happens — which is how an install kept its own updates
    # switched off for a month without a single failing check.
    stale = []
    try:
        if runner.exists():
            gap = _runner_verbs(_RUNNER) - _runner_verbs(
                runner.read_text(encoding="utf-8", errors="replace"))
            if gap:
                stale.append("the icon never runs `%s`" % "`, `".join(sorted(gap)))
        if plist_path().exists():
            want = _plist_verbs(_PLIST.format(
                label=LAUNCHD_LABEL, python=sys.executable,
                engine="observe.py", log=str(LOG)))
            gap = want - _plist_verbs(
                plist_path().read_text(encoding="utf-8", errors="replace"))
            if gap:
                stale.append("the daily job never runs `%s`"
                             % "`, `".join(sorted(gap)))
    except OSError:
        stale = []
    if runner.exists() or plist_path().exists():
        add(not stale,
            "The launcher is the one this checkout generates",
            "Both surfaces run what `install` writes today." if not stale
            else "Generated by an older checkout — %s." % "; and ".join(stale),
            "Run `python3 observe.py install` to regenerate both from the "
            "current templates. Safe to re-run, and it repoints nothing else.")

    plist = plist_path()
    loaded = LAUNCHD_LABEL in _launchctl_says("list")
    add(plist.exists() and loaded,
        "The daily refresh is scheduled",
        "Loaded — runs at 09:00 and at login."
        if loaded else ("The job is written but launchd has not loaded it."
                        if plist.exists() else "No scheduled refresh."),
        "Run `python3 observe.py install` (add `--no-daily` if you would "
        "rather refresh by hand).")

    # An agent that is loaded but has never written a line has never run, and
    # that is the failure this whole block exists to name.
    if loaded:
        try:
            when = datetime.fromtimestamp(LOG.stat().st_mtime)
            ran = when.strftime("%Y-%m-%d %H:%M")
        except OSError:
            ran = None
        add(bool(ran),
            "The daily refresh has actually run",
            f"Last wrote to its log at {ran}." if ran
            else "The job is loaded but has never written to its log.",
            f"Check {tilde(LOG) or LOG} after the next login, and run "
            f"`python3 observe.py all` in the meantime.")


def _has(problems: list[dict]) -> bool:
    return any(not p["ok"] for p in problems)


# ── the error page ──────────────────────────────────────────────────────────

_ERROR_CSS = """
:root{color-scheme:light dark;--bg:#fbfbfd;--ink:#16161c;--muted:#5c5c69;
--line:#e6e6ec;--accent:#4f46e5;--bad:#c0503a;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#0f0f14;--ink:#ecebf2;
--muted:#a0a0ae;--line:#26262f;--accent:#9b93ff;--bad:#e8836b;--card:#16161d}}
*{box-sizing:border-box}
body{margin:0;padding:48px 24px;background:var(--bg);color:var(--ink);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
main{max-width:640px;margin:0 auto}
h1{font-size:24px;letter-spacing:-.02em;margin:0 0 8px}
p.lede{color:var(--muted);margin:0 0 32px}
ol{list-style:none;padding:0;margin:0}
li{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:16px 18px;margin:0 0 12px}
li.bad{border-left:3px solid var(--bad)}
li.ok{opacity:.55}
h2{font-size:15px;margin:0 0 4px;display:flex;gap:8px;align-items:center}
.mark{font-size:13px}
.detail{color:var(--muted);font-size:13.5px;margin:0}
.fix{margin:10px 0 0;padding:10px 12px;background:var(--bg);
border-radius:7px;font-size:13.5px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;
background:var(--bg);padding:2px 5px;border-radius:4px}
footer{margin-top:28px;color:var(--muted);font-size:13px}
a{color:var(--accent)}
"""


def error_page(problems: list[dict], root: Path) -> str:
    """What the generated app shows instead of a traceback.

    A person who double-clicked an icon has no terminal and no reason to open
    one, so every failure has to arrive as a page: what is wrong, in order, and
    the exact line that fixes it.
    """
    import html as _h

    rows = []
    for p in problems:
        cls = "ok" if p["ok"] else "bad"
        mark = "✓" if p["ok"] else "✕"
        fix = (f'<p class="fix">{_h.escape(p["fix"])}</p>'
               if p["fix"] and not p["ok"] else "")
        rows.append(
            f'<li class="{cls}"><h2><span class="mark">{mark}</span>'
            f'{_h.escape(p["title"])}</h2>'
            f'<p class="detail">{_h.escape(p["detail"])}</p>{fix}</li>')

    cmd = _h.escape(refresh_command(root))
    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        f"<title>{APP_NAME} — needs attention</title><style>{_ERROR_CSS}</style>"
        "</head><body><main>"
        f"<h1>{APP_NAME} could not open your dashboard</h1>"
        "<p class=lede>Nothing is broken on your machine. One of the steps "
        "below has not run yet — work down the list.</p>"
        f"<ol>{''.join(rows)}</ol>"
        f"<footer>Most problems are fixed by running <code>{cmd}</code> in a "
        "terminal. Your collected data is untouched either way — it lives in "
        "<code>data/</code> and nothing here deletes it.</footer>"
        "</main></body></html>")


# ── icon ────────────────────────────────────────────────────────────────────

def _png(size: int, rgba: bytearray) -> bytes:
    """Minimal PNG encoder — stdlib only, no Pillow, no build step."""
    rows = b"".join(b"\x00" + bytes(rgba[y * size * 4:(y + 1) * size * 4])
                    for y in range(size))

    def chunk(tag: bytes, body: bytes) -> bytes:
        blob = tag + body
        return (struct.pack(">I", len(body)) + blob
                + struct.pack(">I", zlib.crc32(blob) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + chunk(b"IEND", b""))


def _mark_rgba(size: int) -> bytearray:
    """The observatory mark as straight RGBA: white on an indigo disc.

    Same geometry as `docs/assets/mark.svg` (24-unit viewBox): an outer ring of
    radius 8.5, an inner ring of radius 3, four ticks between 3.5 and 6.5 units
    from the edge-to-centre axes, all at stroke 1.5. Drawn arithmetically rather
    than converted from the SVG, because every SVG rasteriser on macOS is either
    a separate install or a QuickLook side effect, and an icon is not worth a
    dependency. Supersampled so the small sizes a taskbar uses are not jagged.
    """
    u = size / 24.0                       # one SVG unit, in pixels
    disc, half = 11.0 * u, 0.75 * u       # backing disc radius, half the stroke
    ss = 3 if size <= 64 else (2 if size <= 256 else 1)
    c = size / 2.0
    px = bytearray(size * size * 4)

    def white(dx, dy):
        d = (dx * dx + dy * dy) ** 0.5
        if abs(d - 8.5 * u) <= half or abs(d - 3.0 * u) <= half:
            return True
        # ticks: 3 units long, centred on the axes, from 5.5 to 8.5 units out
        # (the SVG's `M12 3.5v3` and its three mirrors), with round-ish caps.
        ax, ay = abs(dx), abs(dy)
        return any(across <= half and 5.5 * u - half <= along <= 8.5 * u + half
                   for along, across in ((ax, ay), (ay, ax)))

    for y in range(size):
        for x in range(size):
            hit = cov = 0
            for sy in range(ss):
                for sx in range(ss):
                    dx = x + (sx + .5) / ss - c
                    dy = y + (sy + .5) / ss - c
                    if (dx * dx + dy * dy) ** 0.5 > disc:
                        continue
                    cov += 1
                    hit += white(dx, dy)
            if not cov:
                continue
            n = ss * ss
            w = hit / cov
            i = (y * size + x) * 4
            px[i] = round(ACCENT[0] + (255 - ACCENT[0]) * w)
            px[i + 1] = round(ACCENT[1] + (255 - ACCENT[1]) * w)
            px[i + 2] = round(ACCENT[2] + (255 - ACCENT[2]) * w)
            px[i + 3] = round(255 * cov / n)
    return px


def _mark(size: int = 512) -> bytes:
    return _png(size, _mark_rgba(size))


def _write_icon(dest: Path) -> bool:
    """PNG -> .icns via `sips`. Best effort: a generic icon is not a failure."""
    if platform.system() != "Darwin" or not shutil.which("sips"):
        return False
    png = dest.with_suffix(".png")
    try:
        png.write_bytes(_mark())
        subprocess.run(["sips", "-s", "format", "icns", str(png),
                        "--out", str(dest)],
                       check=True, capture_output=True, timeout=60)
        return dest.exists()
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        png.unlink(missing_ok=True)


# ── install ─────────────────────────────────────────────────────────────────

_RUNNER = r"""#!/bin/sh
# Generated by `observe.py install`. Safe to delete; re-create it by running
# that command again. Everything it touches lives under the project folder.
set -u
ROOT="{root}"
LOGFILE="{log}"
# Pinned at install time. A launched .app gets a minimal PATH, so `command -v`
# would silently resolve to whatever system Python happens to be on it — a
# different interpreter from the one that installed this, which is how an app
# and its own CLI start disagreeing. The fallback covers a moved Python.
PY="{python}"
[ -x "$PY" ] || PY="$(command -v python3 || true)"
REPORT="$ROOT/dist/observatory.html"
FALLBACK="$ROOT/dist/needs-attention.html"

# No Python, or the project was moved after install: show the page that says so
# rather than failing silently. A launcher that does nothing when double-clicked
# is indistinguishable from a broken machine.
if [ -z "$PY" ] || [ ! -f "$ROOT/observatory/observe.py" ]; then
  [ -f "$FALLBACK" ] && open "$FALLBACK"
  exit 0
fi

# Apply whatever last night's check already downloaded, before the engine
# starts. Local only — the objects are on disk, so this is a pointer move and
# never a network wait in the click path. Its own process, so nothing rewrites
# the modules of a live interpreter. A refusal here is silent by design: the
# dashboard it is about to open says what is waiting and why.
"$PY" "$ROOT/observatory/observe.py" update --quiet >>"$LOGFILE" 2>&1 || true

# Refresh, then open. A failed refresh still opens whatever was last rendered,
# because a stale dashboard beats no dashboard: it can say that it is stale.
if "$PY" "$ROOT/observatory/observe.py" sync digest report --no-open >>"$LOGFILE" 2>&1
then
  open "$REPORT"
else
  "$PY" "$ROOT/observatory/observe.py" doctor --html >"$FALLBACK" 2>/dev/null
  if [ -f "$REPORT" ]; then open "$REPORT"; else open "$FALLBACK"; fi
fi
"""


_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array>
    <string>{python}</string>
    <string>{engine}</string>
    <string>check-update</string>
    <string>sync</string><string>digest</string><string>report</string>
    <string>--no-open</string><string>--notify</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict></plist>
"""

_INFO = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>{name}</string>
  <key>CFBundleDisplayName</key><string>{name}</string>
  <key>CFBundleIdentifier</key><string>dev.aiobservatory.launcher</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>run</string>
  <key>CFBundleIconFile</key><string>appicon</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSUIElement</key><false/>
</dict></plist>
"""


def app_dir() -> Path:
    return Path.home() / "Applications" / f"{APP_NAME}.app"


def plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"


def _launchctl(*args) -> None:
    try:
        subprocess.run(["launchctl", *args], check=False,
                       capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass


def install(root: Path, daily: bool = True) -> list[str]:
    """Create the double-clickable launcher and (optionally) the daily job.

    Returns human-readable lines describing what was written, so the caller can
    print exactly what changed on the machine rather than claiming success in
    the abstract.
    """
    if platform.system() == "Windows":
        return _install_windows(root, daily)
    if platform.system() != "Darwin":
        return _install_generic(root)

    done = []
    bundle = app_dir()
    macos, res = bundle / "Contents" / "MacOS", bundle / "Contents" / "Resources"
    macos.mkdir(parents=True, exist_ok=True)
    res.mkdir(parents=True, exist_ok=True)

    LOG.parent.mkdir(parents=True, exist_ok=True)
    runner = macos / "run"
    runner.write_text(
        _RUNNER.format(root=root.resolve(), log=LOG, python=sys.executable),
        encoding="utf-8")
    runner.chmod(0o755)
    (bundle / "Contents" / "Info.plist").write_text(
        _INFO.format(name=APP_NAME), encoding="utf-8")
    done.append(f"launcher   {tilde(bundle) or bundle}")

    if _write_icon(res / "appicon.icns"):
        done.append("icon       generated")

    # A generated bundle carries no com.apple.quarantine, so Gatekeeper never
    # prompts. Touching it makes Finder pick up the new icon immediately.
    _launchctl("stop", LAUNCHD_LABEL)
    subprocess.run(["touch", str(bundle)], check=False, capture_output=True)

    if daily:
        # 09:00, plus once at login. launchd already runs a *missed* calendar
        # interval when the machine wakes, so a laptop asleep at nine refreshes
        # when it is opened. What that does not cover is a machine that was off
        # at nine and booted at ten: no wake, no catch-up, a dashboard a day
        # stale. RunAtLoad closes that, and costs one incremental sync.
        pl = plist_path()
        pl.parent.mkdir(parents=True, exist_ok=True)
        pl.write_text(_PLIST.format(
            label=LAUNCHD_LABEL, python=sys.executable,
            engine=str((root / "observatory" / "observe.py").resolve()),
            log=str(LOG)), encoding="utf-8")
        _launchctl("bootout", f"gui/{os.getuid()}/{LAUNCHD_LABEL}")
        _launchctl("bootstrap", f"gui/{os.getuid()}", str(pl))
        done.append(f"daily sync {tilde(pl) or pl} (09:00 local)")

    return done


def _install_generic(root: Path) -> list[str]:
    """Linux: a script beside the project, not a bundle."""
    path = root / "Open AI Observatory.sh"
    path.write_text(
        "#!/bin/sh\n"
        f'exec python3 "{root / "observatory" / "observe.py"}" sync digest report\n',
        encoding="utf-8")
    path.chmod(0o755)
    return [f"launcher   {tilde(path) or path}",
            "note       double-click it, or add it to your launcher"]


# ── windows ─────────────────────────────────────────────────────────────────
#
# The macOS answer (a bundle in ~/Applications, a tile in the Dock) has no
# direct Windows equivalent, and the previous fallback — a loose .cmd file in
# the project folder — meant nothing ever appeared in Start or on the taskbar.
# What does exist: a .lnk in the Start Menu, which Windows indexes, which has
# its own icon, and which the user can right-click -> "Pin to taskbar".
# Microsoft deliberately removed any supported API for pinning to the taskbar
# programmatically (Windows 10 1809+), so the last click is the user's.

_WIN_TASK = "AI Observatory daily refresh"

_WIN_RUNNER = '''\
# Generated by `observe.py install`. Safe to delete; re-create it by running
# that command again. Run by pythonw.exe, so no console window flashes up.
import os, subprocess, sys, webbrowser
from pathlib import Path

ROOT = Path({root!r})
PY = {python!r}
LOG = Path({log!r})
REPORT = ROOT / "dist" / "observatory.html"
FALLBACK = ROOT / "dist" / "needs-attention.html"
if not Path(PY).exists():
    PY = sys.executable
ENGINE = str(ROOT / "observatory" / "observe.py")


def run(*args, out=None):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        sink = out or open(LOG, "ab")
        return subprocess.run([PY, ENGINE, *args], stdout=sink, stderr=subprocess.STDOUT,
                              creationflags=0x08000000, cwd=str(ROOT)).returncode
    except OSError:
        return 1


if not (ROOT / "observatory" / "observe.py").exists():
    if FALLBACK.exists():
        webbrowser.open(FALLBACK.as_uri())
    sys.exit(0)

run("update", "--quiet")
if run("sync", "digest", "report", "--no-open") == 0 and REPORT.exists():
    webbrowser.open(REPORT.as_uri())
else:
    FALLBACK.parent.mkdir(parents=True, exist_ok=True)
    with open(FALLBACK, "wb") as fh:
        run("doctor", "--html", out=fh)
    webbrowser.open((REPORT if REPORT.exists() else FALLBACK).as_uri())
'''


def win_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / APP_NAME


def win_shortcut() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return (Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            / f"{APP_NAME}.lnk")


_ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _dib(size: int) -> bytes:
    """One .ico frame as a classic 32-bit BMP (BGRA, bottom-up, empty AND mask).

    The taskbar asks for 24-48 px frames, and a file whose only frame is a
    256 px PNG can render as the blank-document placeholder instead of being
    scaled. Small sizes are therefore stored in the format every shell reads.
    """
    rgba = _mark_rgba(size)
    rows = []
    for y in range(size - 1, -1, -1):
        row = rgba[y * size * 4:(y + 1) * size * 4]
        bgra = bytearray(len(row))
        bgra[0::4], bgra[1::4], bgra[2::4], bgra[3::4] = (
            row[2::4], row[1::4], row[0::4], row[3::4])
        rows.append(bytes(bgra))
    mask = b"\x00" * (((size + 31) // 32) * 4 * size)
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0,
                         size * size * 4, 0, 0, 0, 0)
    return header + b"".join(rows) + mask


def _ico() -> bytes:
    """A multi-size .ico: BMP frames up to 128 px, a PNG frame at 256 px."""
    frames = [(s, _png(s, _mark_rgba(s)) if s == 256 else _dib(s))
              for s in _ICO_SIZES]
    out = [struct.pack("<HHH", 0, 1, len(frames))]
    offset = 6 + 16 * len(frames)
    for s, blob in frames:
        out.append(struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32,
                               len(blob), offset))
        offset += len(blob)
    return b"".join(out) + b"".join(blob for _, blob in frames)


def _pythonw() -> str:
    """The windowless interpreter next to this one, so no console flashes."""
    w = Path(sys.executable).with_name("pythonw.exe")
    return str(w) if w.exists() else sys.executable


def _ps_quote(value) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _make_lnk(lnk: Path, target: str, args: str, workdir: Path, icon: Path) -> bool:
    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut(%s);"
        "$s.TargetPath=%s;$s.Arguments=%s;$s.WorkingDirectory=%s;"
        "$s.IconLocation=%s;$s.Description=%s;$s.Save()"
        % (_ps_quote(lnk), _ps_quote(target), _ps_quote(args),
           _ps_quote(workdir), _ps_quote(icon), _ps_quote(APP_NAME)))
    try:
        lnk.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-Command", script],
                       check=True, capture_output=True, timeout=60)
        return lnk.exists()
    except (OSError, subprocess.SubprocessError):
        return False


def _schtasks(*args) -> bool:
    try:
        return subprocess.run(["schtasks", *args], check=False,
                              capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _install_windows(root: Path, daily: bool = True) -> list[str]:
    done = []
    folder = win_dir()
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / "ai-observatory.log"

    runner = folder / "run.pyw"
    runner.write_text(_WIN_RUNNER.format(
        root=str(root.resolve()), python=sys.executable, log=str(log)),
        encoding="utf-8")
    icon = folder / "appicon.ico"
    icon.write_bytes(_ico())
    done.append(f"launcher   {runner}")

    lnk = win_shortcut()
    if _make_lnk(lnk, _pythonw(), f'"{runner}"', root.resolve(), icon):
        done.append("start menu AI Observatory (search for it in Start)")
    else:
        done.append("start menu could not be created — double-click "
                    f"{runner} instead")

    if daily:
        py = _pythonw()
        cmd = (f'"{py}" "{root.resolve() / "observatory" / "observe.py"}" '
               "check-update sync digest report --no-open --notify")
        # Daily at 09:00, plus once at logon — the same two triggers as the
        # macOS LaunchAgent. /F overwrites an earlier install's task.
        ok = _schtasks("/Create", "/F", "/TN", _WIN_TASK, "/SC", "DAILY",
                       "/ST", "09:00", "/TR", cmd)
        done.append("daily sync " + ("scheduled (09:00 local)" if ok
                                     else "could not be scheduled — skipped"))
    return done


def _uninstall_windows() -> list[str]:
    done = []
    if _schtasks("/Delete", "/F", "/TN", _WIN_TASK):
        done.append(f"removed scheduled task '{_WIN_TASK}'")
    lnk = win_shortcut()
    if lnk.exists():
        lnk.unlink()
        done.append(f"removed {lnk}")
    folder = win_dir()
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
        done.append(f"removed {folder}")
    return done or ["nothing to remove"]


def uninstall() -> list[str]:
    """Remove everything `install` created. Never touches `data/`."""
    if platform.system() == "Windows":
        return _uninstall_windows()
    done = []
    unpinned = remove_from_dock()
    if unpinned:
        done.append(unpinned)
    pl = plist_path()
    if pl.exists():
        _launchctl("bootout", f"gui/{os.getuid()}/{LAUNCHD_LABEL}")
        pl.unlink()
        done.append(f"removed {tilde(pl) or pl}")
    bundle = app_dir()
    if bundle.exists():
        shutil.rmtree(bundle, ignore_errors=True)
        done.append(f"removed {tilde(bundle) or bundle}")
    return done or ["nothing to remove"]


def update(root: Path) -> str:
    """Bring the checkout up to date for `setup`, best effort.

    Setup is the one place a person has explicitly asked for the newest thing,
    so this is the only path that fetches and applies in the same breath.
    Everywhere else the two halves are days apart on purpose — see `updater`.

    This project has no third-party dependencies to upgrade; it is standard
    library only, which is the whole reason install is one command. So the only
    thing that can be out of date is the code, and that is a fast-forward or
    nothing: never a merge, never a rebase, never anything that could leave
    somebody staring at a conflict they did not ask for. A dirty tree, a
    detached head, no remote or no network all mean "skip", not "fail".
    """
    if str(settings.get("updates", "auto")).lower() == "off":
        return "updates are off in settings.json — skipped"
    if not updater.is_checkout(root):
        return "not a git checkout — skipped"
    data = root / "data"
    state = updater.check(root, data)
    if not state.get("reachable", True):
        return "could not reach GitHub — using the version you have"
    if state.get("blocked") and not state.get("behind"):
        return f"{state['blocked']} — using the version you have"
    if not state.get("behind"):
        return f"already up to date ({updater.version(root)})"
    waiting = state["behind"]
    applied = updater.apply(root, data)
    if applied.get("blocked") == "local changes":
        return f"{waiting} update(s) waiting — local changes present, left alone"
    return f"updated to the latest version ({updater.version(root)})"


def launch() -> bool:
    """Start the generated app, exactly as a double-click would.

    This is what `install` ends with. A setup command that prints three lines
    and exits leaves the user holding a receipt instead of a product — they have
    no way to know whether it worked, and nothing to look at if it did.
    """
    if platform.system() == "Windows":
        runner = win_dir() / "run.pyw"
        try:
            subprocess.Popen([_pythonw(), str(runner)], creationflags=0x08000000)
            return runner.exists()
        except OSError:
            return False
    if platform.system() != "Darwin":
        return False
    try:
        return subprocess.run(["open", "-a", str(app_dir())],
                              capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def reveal() -> bool:
    """Show the app in Finder with its icon selected.

    The answer to "where do I find this tomorrow?" has to be a thing they have
    seen, not a path they were told. Finder is also where dragging it to the
    Dock starts, which is the gesture most people already know.
    """
    if platform.system() == "Windows":
        try:
            # explorer.exe returns 1 even on success, so judge by existence.
            subprocess.Popen(["explorer", f"/select,{win_shortcut()}"])
            return win_shortcut().exists()
        except OSError:
            return False
    if platform.system() != "Darwin":
        return False
    try:
        return subprocess.run(["open", "-R", str(app_dir())],
                              capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _dock_prefs() -> dict:
    """The whole com.apple.dock domain as a dict, or {} if it cannot be read."""
    try:
        blob = subprocess.run(["defaults", "export", "com.apple.dock", "-"],
                              check=True, capture_output=True, timeout=30).stdout
        return plistlib.loads(blob)
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def _tile_path(tile: dict) -> str:
    """A Dock tile's target as a plain POSIX path.

    The string that comes back out is never the string that went in: the Dock
    normalises whatever `add_to_dock` wrote into a percent-encoded file:// URL,
    so this app leaves as `AI%20Observatory.app`. Matching on the raw value
    finds nothing, which would make the tile we pinned impossible to unpin.
    """
    try:
        raw = tile["tile-data"]["file-data"]["_CFURLString"]
    except (KeyError, TypeError):
        return ""
    if raw.startswith("file://"):
        raw = urllib.parse.urlparse(raw).path
    return urllib.parse.unquote(raw).rstrip("/")


def in_dock() -> bool:
    target = str(app_dir()).rstrip("/")
    return any(_tile_path(t) == target
               for t in _dock_prefs().get("persistent-apps") or [])


def add_to_dock() -> str:
    """Pin the app to the Dock. Done by default; `--no-dock` opts out.

    This edits the user's own Dock and restarts it, which is not a side effect
    to spring on anybody — but `install` is the moment they have already said
    yes to this living on their machine, and an app they cannot find tomorrow
    is an app they will not open tomorrow. It stays reversible in both
    directions: `install --remove` takes the tile back out again.
    """
    if platform.system() == "Windows":
        # No supported API pins to the taskbar (removed in Windows 10 1809),
        # so say the one gesture that does instead of claiming success.
        return ("taskbar    right-click \"AI Observatory\" in Start -> "
                "Pin to taskbar")
    if platform.system() != "Darwin":
        return "dock       (macOS only)"
    if in_dock():
        return "dock       already there"
    tile = ("<dict><key>tile-data</key><dict><key>file-data</key><dict>"
            "<key>_CFURLString</key><string>%s</string>"
            "<key>_CFURLStringType</key><integer>0</integer>"
            "</dict></dict></dict>" % app_dir())
    try:
        subprocess.run(["defaults", "write", "com.apple.dock",
                        "persistent-apps", "-array-add", tile],
                       check=True, capture_output=True, timeout=30)
        subprocess.run(["killall", "Dock"], check=False,
                       capture_output=True, timeout=30)
        return "dock       pinned"
    except (OSError, subprocess.SubprocessError):
        return "dock       could not be updated — drag the app there instead"


def remove_from_dock() -> str:
    """Take the tile back out, so `install --remove` leaves nothing behind.

    A Dock icon that outlives its bundle is a permanent question mark on
    somebody's screen. The whole domain round-trips through plistlib because
    `defaults` has no syntax for "delete the array element that matches this",
    only for appending one.
    """
    if platform.system() != "Darwin" or not in_dock():
        return ""
    prefs = _dock_prefs()
    apps = prefs.get("persistent-apps") or []
    target = str(app_dir()).rstrip("/")
    kept = [a for a in apps if _tile_path(a) != target]
    if not prefs or len(kept) == len(apps):
        return ""
    prefs["persistent-apps"] = kept
    try:
        subprocess.run(["defaults", "import", "com.apple.dock", "-"],
                       input=plistlib.dumps(prefs), check=True,
                       capture_output=True, timeout=30)
        subprocess.run(["killall", "Dock"], check=False,
                       capture_output=True, timeout=30)
        return "unpinned from the Dock"
    except (OSError, ValueError, subprocess.SubprocessError):
        return "could not update the Dock — drag the icon out of it yourself"


def notify(title: str, message: str) -> None:
    """A Notification Centre nudge after an unattended sync.

    Deliberately not clickable: `osascript display notification` cannot carry a
    click action, and pretending otherwise would train people to click something
    that does nothing. The nudge says the dashboard is ready; the Dock icon is
    what opens it.
    """
    if platform.system() != "Darwin" or not shutil.which("osascript"):
        return
    safe = message.replace('"', "'")
    head = title.replace('"', "'")
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{safe}" with title "{head}"'],
            check=False, capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        pass
