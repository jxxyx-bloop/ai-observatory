"""User preferences — display and policy only, never collection.

Kept separate from `topology.json` (which describes the machine's folder
layout) because these are choices a person makes, not facts about a disk.
Missing file, missing key, or malformed JSON all fall back to the defaults
below rather than failing a sync: a preferences file must never be able to
stop the tool from running.
"""

from __future__ import annotations

import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).with_name("settings.json")

DEFAULTS = {
    "timezone_offset_hours": 8,
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
