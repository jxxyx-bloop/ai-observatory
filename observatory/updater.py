"""Update surface — how a checkout learns a newer one exists, and applies it.

[ADR-018] split the two questions this product has to answer. *Am I out of
date?* belongs to the page, which computes it offline from its own render
stamp. *Does a newer version exist?* belongs to the launcher, because a file
can never be told. Only `setup` ever answered the second one — so a person who
installed once and clicked the icon every morning after stayed on the version
they installed, and had no way to find out that anything had changed.

The split that makes updating feel like nothing:

    check   daily and unattended, in the launchd agent. `git fetch` downloads
            objects and executes NOTHING, so it needs no trust decision.
    apply   at the next launch, as a local fast-forward. No network in the
            click path: a slow connection can never make the icon hang, and
            the merge is a pointer move because the objects are already here.

By the time somebody clicks their Dock icon the new version is already on the
disk. That is the whole trick, and it is the one every update system that feels
effortless uses.

A fast-forward or nothing. Never a merge, never a rebase, never a stash —
anything else leaves a person staring at a conflict they did not ask for, in
a directory they think of as an app. When the tree is dirty this does not
apply and does not pretend otherwise: it records *why*, so the page can say so
instead of failing silently, which is what the old best-effort pull did.

Every failure here is a skip. No network, no git, no upstream, a moved folder
or a detached head all mean "keep the version you have" — never a traceback,
and never a blocked dashboard.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_NAME = "update.json"

# How long the "here is what changed" receipt keeps showing after an update
# lands. Deliberately a clock, not a seen-once flag: the 09:00 agent renders
# the page while nobody is watching, so a flag would be burned by a render no
# human ever saw and the one person it was written for would never see it.
RECEIPT_HOURS = 24

# Enough to show what a week of changes was about without turning the strip
# into a changelog. The count is always exact; only the list is capped.
MAX_LINES = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(at: datetime) -> str:
    return at.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git(root: Path, *args, timeout: int = 30):
    """Run one git command. Returns (ok, stdout) and never raises."""
    git = shutil.which("git")
    if not git or not (root / ".git").exists():
        return False, ""
    try:
        done = subprocess.run([git, "-C", str(root), *args],
                              capture_output=True, text=True, timeout=timeout)
        return done.returncode == 0, done.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False, ""


def is_checkout(root: Path) -> bool:
    return bool(shutil.which("git")) and (root / ".git").exists()


def version(root: Path) -> str:
    """A name for what is installed, in the units the user has chosen.

    `git describe` prefers the nearest tag, so the day this project starts
    tagging releases the page shows "v1.4" with no code change here. Until
    then it shows a short commit, which is honest rather than invented.
    """
    ok, out = _git(root, "describe", "--tags", "--always", "--dirty")
    if ok and out:
        return out
    ok, out = _git(root, "rev-parse", "--short", "HEAD")
    return out if ok else "unknown"


def _upstream(root: Path):
    ok, out = _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    return out if ok and out else None


def _dirty(root: Path) -> bool:
    """Tracked modifications only — the ones that stop a fast-forward.

    Untracked files are deliberately not counted. `data/` and `dist/` live
    inside the checkout, and anyone may leave a note or an editor file beside
    them; treating those as "you are working on this project, do not touch it"
    would switch updates off for most real installs and never say why. When an
    incoming commit genuinely collides with an untracked path, git refuses the
    merge itself and `apply` reports that.
    """
    ok, out = _git(root, "status", "--porcelain", "--untracked-files=no")
    return bool(ok and out)


def pending(root: Path) -> dict:
    """What is waiting locally — reads refs already on disk, never the network.

    Safe to call from anywhere, including the render path: it is a few
    milliseconds of git plumbing with no side effects.
    """
    if not is_checkout(root):
        return {"behind": 0, "lines": [], "blocked": "not a git checkout"}
    if _upstream(root) is None:
        return {"behind": 0, "lines": [], "blocked": "no upstream branch"}
    ok, count = _git(root, "rev-list", "--count", "HEAD..@{u}")
    if not ok or not count.isdigit():
        return {"behind": 0, "lines": [], "blocked": "could not compare"}
    behind = int(count)
    lines = []
    if behind:
        got, log = _git(root, "log", "--reverse", "--format=%s",
                        "-%d" % MAX_LINES, "HEAD..@{u}")
        if got:
            lines = [ln.strip() for ln in log.splitlines() if ln.strip()]
    return {"behind": behind, "lines": lines,
            "blocked": "local changes" if (behind and _dirty(root)) else None}


def check(root: Path, data_dir: Path) -> dict:
    """Fetch, then record what is waiting. The only step that touches the network.

    `git fetch` writes objects and moves remote-tracking refs. It runs nothing
    from the downloaded tree, which is why this half needs no permission and
    the applying half does.
    """
    state = read(data_dir)
    state["checked_at"] = _stamp(_now())
    if not is_checkout(root):
        state.update(pending(root), reachable=False)
        return write(data_dir, state)
    ok, _ = _git(root, "fetch", "--quiet", timeout=120)
    state["reachable"] = bool(ok)
    state.update(pending(root))
    state["current"] = version(root)
    return write(data_dir, state)


def apply(root: Path, data_dir: Path) -> dict:
    """Fast-forward onto what `check` already downloaded. No network.

    Returns the state it wrote. `applied` describes what arrived so the next
    render can show a receipt — an update nobody can see the effect of is
    indistinguishable from a silent code change, which is not a thing this
    project should ever do to somebody.
    """
    state = read(data_dir)
    before = pending(root)
    state.update(before)
    if not before["behind"] or before["blocked"]:
        state["current"] = version(root)
        return write(data_dir, state)

    ok, _ = _git(root, "merge", "--ff-only", "--quiet", "@{u}", timeout=60)
    if not ok:
        # git refuses per-file when a fast-forward would clobber an edit, which
        # is a better answer than any check this module could write itself.
        state["blocked"] = "local changes"
        return write(data_dir, state)

    state["applied"] = {"at": _stamp(_now()), "count": before["behind"],
                        "lines": before["lines"], "version": version(root)}
    state.update(pending(root))
    state["current"] = state["applied"]["version"]
    return write(data_dir, state)


def read(data_dir: Path) -> dict:
    try:
        got = json.loads((data_dir / STATE_NAME).read_text(encoding="utf-8"))
        return got if isinstance(got, dict) else {}
    except (OSError, ValueError):
        return {}


def write(data_dir: Path, state: dict) -> dict:
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / STATE_NAME).write_text(json.dumps(state, indent=1),
                                           encoding="utf-8")
    except OSError:
        pass
    return state


def for_render(state: dict, now: datetime | None = None) -> dict | None:
    """The half-dozen fields the page needs, or None when it should stay silent.

    Python decides which of the two things to say and the page renders what it
    is handed — the same rule the metrics follow. A browser opened from
    `file://` cannot check a clock against a repository, and should not try.
    """
    if not state:
        return None
    now = now or _now()
    # What is waiting outranks what already landed. Both can be true at once —
    # an update applies on Monday and Tuesday's arrives while the tree is dirty
    # — and in that hour the receipt is the less useful of the two sentences.
    if state.get("behind"):
        return {"state": "ready", "count": state.get("behind") or 0,
                "lines": state.get("lines") or [],
                "version": state.get("current") or "",
                "blocked": state.get("blocked")}
    applied = state.get("applied") or {}
    at = _parse(applied.get("at"))
    if at and now - at < timedelta(hours=RECEIPT_HOURS):
        return {"state": "applied", "count": applied.get("count") or 0,
                "lines": applied.get("lines") or [],
                "version": applied.get("version") or "", "blocked": None}
    return None


def _parse(stamp):
    if not stamp:
        return None
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
