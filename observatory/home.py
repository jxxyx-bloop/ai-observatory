"""Where the tool keeps its files — a checkout, or a home directory.

The engine was written to run out of a git clone: `data/` and `dist/` sit
beside `observatory/`, and the four JSON config files are edited in place. That
is the right layout for someone who intends to contribute, and the wrong one
for someone typing `uvx ai-observatory` to look around — there, the package
lives in a read-only cache that a later upgrade will replace, and writing a
60 MB event store into it would be both rude and futile.

So there are two modes, and exactly one thing distinguishes them: whether the
code is sitting in its own source tree.

    checkout    ROOT = the repo             (unchanged, byte for byte)
    installed   ROOT = ~/.ai-observatory    (created on first use)

Checkout mode is detected, not configured, because the person running from a
clone never asked for a second layout and should not have to know one exists.
`AI_OBSERVATORY_HOME` overrides both — it is how the tests pin a location, and
how someone moves the store onto another disk.

Config resolution differs by *kind* of file, which matters more than it looks:

    settings.json, topology.json   yours. Seeded into the home directory on
                                   first run so there is something to edit.
    pricing.json, plans.json       ours. Read from the package so an upgrade
                                   delivers corrected rates, and overridable
                                   by dropping a file of the same name in the
                                   home directory.

A user file that shadowed the rate card would silently freeze prices at
whatever they were the day it was written, and the resulting numbers would be
wrong in a way nobody could see. Shipped data stays shipped.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

PKG = Path(__file__).resolve().parent

# The two files the README tells a new user to edit. Everything else is either
# shipped data or written by the engine.
SEEDED = ("settings.json", "topology.json")


def _looks_like_checkout(parent: Path) -> bool:
    """True when `parent` is this project's source tree rather than a cache.

    Two markers, both required. `observatory/observe.py` alone is satisfied by
    the installed package itself under some layouts; a sibling `LICENSE` or
    `.git` is what makes it a clone somebody chose to make. Writability is
    checked last because a read-only clone — a CI cache, a Nix store path —
    cannot host `data/` and should fall through to the home directory.
    """
    if not (parent / "observatory" / "observe.py").is_file():
        return False
    if not ((parent / ".git").exists() or (parent / "LICENSE").is_file()):
        return False
    return os.access(parent, os.W_OK)


def is_checkout() -> bool:
    return _env_home() is None and _looks_like_checkout(PKG.parent)


def _env_home():
    raw = os.environ.get("AI_OBSERVATORY_HOME", "").strip()
    return Path(os.path.expanduser(raw)).resolve() if raw else None


def root() -> Path:
    """The directory `data/` and `dist/` live under."""
    override = _env_home()
    if override is not None:
        return override
    parent = PKG.parent
    return parent if _looks_like_checkout(parent) else Path.home() / ".ai-observatory"


def data() -> Path:
    return root() / "data"


def dist() -> Path:
    return root() / "dist"


def seed() -> list:
    """Copy the editable config into the home directory, once.

    Returns the paths it created, so a first run can say where the settings it
    just made are — a config file nobody can find is a config file nobody
    edits. Never overwrites: a file that exists is one the user may have
    changed, and this runs on every launch.
    """
    if is_checkout():
        return []
    home = root()
    written = []
    for name in SEEDED:
        target = home / name
        if target.exists():
            continue
        source = PKG / name
        if not source.is_file():
            continue
        home.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        written.append(target)
    return written


def retarget(text: str) -> str:
    """Rewrite `python3 observe.py …` into `ai-observatory …` when installed.

    Every fix `doctor` prints, and every action a finding suggests, is a line
    the reader is expected to paste. Installed from PyPI there is no
    `observe.py` on disk to paste it at, so the advice would be worse than
    silence — it sends a stuck person somewhere that does not exist.

    Done as one substitution at the point of display rather than by threading a
    prefix through forty string literals: the invocation is a property of how
    the program was installed, not of what any individual message means, and
    the messages stay readable in the source as the thing a contributor types.
    """
    if is_checkout():
        return text
    return text.replace("python3 observe.py", "ai-observatory")


def config_path(name: str) -> Path:
    """Where to read `name` from.

    In a checkout, always the package copy — that is the file the contributor
    has open. Installed, a copy in the home directory wins when it exists, and
    the shipped one answers otherwise. That single rule covers both the seeded
    files (which will exist) and the rate card (which will not, until someone
    deliberately overrides it).

    Callers resolve this once, at import, and hold the answer for the life of
    the process — so a seeded file that does not exist yet is created here
    rather than reported missing. Otherwise the answer would depend on whether
    the module happened to be imported before or after the first run seeded
    the directory, which is not a thing anyone should have to reason about.
    """
    if is_checkout():
        return PKG / name
    target = root() / name
    if name in SEEDED and not target.is_file():
        seed()
    return target if target.is_file() else PKG / name
