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

Nothing here runs at import time, nothing here touches the network, and every
filesystem write is inside `$HOME` and reversible with `observe.py install
--remove`.
"""

from __future__ import annotations

import os
import platform
import shutil
import struct
import subprocess
import sys
import webbrowser
import zlib
from pathlib import Path

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
    """The one line that re-collects and re-renders, safe to show anyone."""
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

    return out


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


def _mark(size: int = 512) -> bytes:
    """The observatory mark: two rings and four ticks, on an indigo field.

    Drawn arithmetically rather than converted from `docs/assets/mark.svg`,
    because every SVG rasteriser on macOS is either a separate install or a
    QuickLook side effect, and an icon is not worth a dependency.
    """
    px = bytearray(size * size * 4)
    cx = cy = (size - 1) / 2
    radius = size * 0.46
    ring_o, ring_i = size * 0.30, size * 0.115
    stroke = size * 0.035

    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, y - cy
            d = (dx * dx + dy * dy) ** 0.5
            if d > radius:
                continue
            i = (y * size + x) * 4
            on_ring = (abs(d - ring_o) < stroke / 2) or (d < ring_i)
            tick = (abs(dy) < stroke / 2 or abs(dx) < stroke / 2) \
                and ring_o + stroke < d < radius * 0.86
            if on_ring or tick:
                px[i:i + 4] = bytes((255, 255, 255, 255))
            else:
                px[i:i + 4] = bytes((*ACCENT, 255))
    return _png(size, px)


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
    <string>sync</string><string>digest</string><string>report</string>
    <string>--no-open</string><string>--notify</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><false/>
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
    """Windows and Linux: a script beside the project, not a bundle.

    ADR-013 already accepts that Windows users carry more friction than macOS
    users. This keeps the promise minimal and true rather than half-shipping a
    Start Menu integration that only works on some machines.
    """
    windows = platform.system() == "Windows"
    name = "Open AI Observatory." + ("cmd" if windows else "sh")
    path = root / name
    body = (
        "@echo off\r\n"
        f'python "{root / "observatory" / "observe.py"}" sync digest report\r\n'
        if windows else
        "#!/bin/sh\n"
        f'exec python3 "{root / "observatory" / "observe.py"}" sync digest report\n')
    path.write_text(body, encoding="utf-8")
    if not windows:
        path.chmod(0o755)
    return [f"launcher   {tilde(path) or path}",
            "note       double-click it, or pin it to your taskbar"]


def uninstall() -> list[str]:
    """Remove everything `install` created. Never touches `data/`."""
    done = []
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


def launch() -> bool:
    """Start the generated app, exactly as a double-click would.

    This is what `install` ends with. A setup command that prints three lines
    and exits leaves the user holding a receipt instead of a product — they have
    no way to know whether it worked, and nothing to look at if it did.
    """
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
    if platform.system() != "Darwin":
        return False
    try:
        return subprocess.run(["open", "-R", str(app_dir())],
                              capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def in_dock() -> bool:
    try:
        out = subprocess.run(["defaults", "read", "com.apple.dock", "persistent-apps"],
                             capture_output=True, text=True, timeout=30)
        return APP_NAME in out.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def add_to_dock() -> str:
    """Pin the app to the Dock. Opt-in — this edits the user's own Dock.

    Kept behind `--dock` rather than done by default: rearranging somebody's
    Dock and restarting it is not a side effect anyone should discover.
    """
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
