"""User preferences — display and policy only, never collection.

Kept separate from `topology.json` (which describes the machine's folder
layout) because these are choices a person makes, not facts about a disk.
Missing file, missing key, or malformed JSON all fall back to the defaults
below rather than failing a sync: a preferences file must never be able to
stop the tool from running.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

SETTINGS_PATH = Path(__file__).with_name("settings.json")

DEFAULTS = {
    "timezone_offset_hours": "auto",
    "currency": "USD",
    "plan": "none",
    "community": {"share": False, "endpoint": "", "handle": "",
                  "cohorts": [], "include_repo_names": False},
}

_CACHE = None


def load() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    cfg = dict(DEFAULTS)
    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    for key, default in DEFAULTS.items():
        value = raw.get(key, default)
        if isinstance(default, dict) and isinstance(value, dict):
            merged = dict(default)
            merged.update(value)
            value = merged
        cfg[key] = value
    _CACHE = cfg
    return cfg


def get(key, default=None):
    return load().get(key, default)


def _configured_offset():
    """The user's explicit offset in hours, or None when they want the machine's.

    Anything unparseable is treated as "auto" rather than as an error. A
    preferences file must never stop the tool from running, and a timezone that
    silently falls back to the machine is far less surprising than one that
    falls back to a number chosen for somebody else's country.
    """
    raw = get("timezone_offset_hours", "auto")
    if raw is None or (isinstance(raw, str) and raw.strip().lower() == "auto"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def local_offset(at=None) -> timedelta:
    """The UTC offset to present timestamps in, for the instant `at`.

    `at` matters. When the offset comes from the machine rather than the
    settings file it is resolved per instant, so a zone that observes DST gets
    the offset that was actually in force then — a July session and a January
    session in Europe are an hour apart and should read that way.
    """
    fixed = _configured_offset()
    if fixed is not None:
        return timedelta(hours=fixed)
    when = at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone().utcoffset() or timedelta(0)


def timezone_label(at=None) -> str:
    """`UTC+9`, `UTC-3:30` — how the offset in force at `at` is written."""
    total = local_offset(at).total_seconds() / 3600
    sign = "+" if total >= 0 else "-"
    whole = int(abs(total))
    minutes = int(round((abs(total) - whole) * 60))
    return "UTC%s%d%s" % (sign, whole, ":%02d" % minutes if minutes else "")


def timezone_is_auto() -> bool:
    """True when the offset follows the machine instead of the settings file."""
    return _configured_offset() is None


def timezone_name():
    """The machine's zone name when it has one (`Asia/Seoul`), else None.

    Only ever decoration — every calculation uses the offset. Read from the
    `/etc/localtime` symlink because that is where the name survives; `tzname()`
    gives an abbreviation like `+09` or `KST`, which is not a zone.
    """
    env = os.environ.get("TZ")
    if env:
        return env  # an explicit TZ wins; it is what the offset above obeyed
    try:
        target = os.readlink("/etc/localtime")
    except OSError:
        return None
    marker = "/zoneinfo/"
    return target.split(marker, 1)[1] if marker in target else None
