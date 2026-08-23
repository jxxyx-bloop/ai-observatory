"""Synthetic event generator — `observe.py demo`.

Every tool in this category has the same onboarding problem: the dashboard is
the pitch, and you cannot see the dashboard until you have weeks of your own
usage. So the README shows a screenshot and the first run shows an empty page.

`demo` fills the store with a plausible 60 days of usage from four providers so
the whole pipeline — digest, detectors, dashboard — can be seen, screenshotted,
and reviewed in one command, on a machine that has never run an AI coding tool.
It is also how the tests get deterministic input.

Deterministic on purpose: seeded, no clock reads beyond the anchor date, so two
people running `demo` see the same numbers and can talk about them.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from collectors.base import blank_event

SEED = 20260819

# A deliberately mixed diet: a frontier model on everything, a cheap regional
# model doing the bulk work, and a time-priced vendor used at the wrong hours.
# The fixture is built so several detectors have something true to say — an
# all-healthy fixture would make the insight tier untestable.
# Weighted toward the regional vendors on purpose: the demo should look like
# the user this project is built for — a developer whose daily driver is a
# cheap time-priced Chinese model with a frontier Western model kept for the
# hard turns — not like a US enterprise seat. It is also the only way the
# peak-window detector has anything real to say in the fixture.
MODELS = [
    ("claude-code", "claude-opus-5", "high", 0.08),
    ("claude-code", "claude-sonnet-5", "medium", 0.14),
    ("claude-code", "claude-haiku-4-5", None, 0.05),
    ("codex", "gpt-5-codex", "medium", 0.08),
    ("kimi-code", "kimi-k2.7-code", None, 0.13),
    ("deepseek", "deepseek-v4-pro", None, 0.28),
    ("deepseek", "deepseek-v4-flash", None, 0.09),
    ("glm", "glm-5.1", None, 0.15),
]

REPOS = [("checkout-service", 0.34), ("growth-web", 0.24), ("data-platform", 0.18),
         ("infra-tooling", 0.14), ("scratchpad", 0.10)]
SURFACES = {
    "checkout-service": ["api", "payments", "tests", "docs"],
    "growth-web": ["app/landing", "app/pricing", "components", "e2e"],
    "data-platform": ["pipelines", "models", "notebooks"],
    "infra-tooling": ["terraform", "ci", "scripts"],
    "scratchpad": ["scratch files"],
}
READ_TOOLS = ["Read", "Grep", "Glob"]
WRITE_TOOLS = ["Edit", "Write", "MultiEdit"]
OTHER_TOOLS = ["Bash", "Task", "WebSearch", "TodoWrite"]


def _pick(rng, weighted):
    r = rng.random()
    acc = 0.0
    for item in weighted:
        acc += item[-1]
        if r <= acc:
            return item
    return weighted[-1]


def generate(days: int = 60, anchor: str = "2026-08-19") -> list:
    """Return a list of normalized events ending on `anchor`."""
    rng = random.Random(SEED)
    end = datetime.fromisoformat(anchor).replace(tzinfo=timezone.utc)
    events = []
    session_no = 0

    for back in range(days - 1, -1, -1):
        day = end - timedelta(days=back)
        weekend = day.weekday() >= 5
        n_sessions = rng.randint(0, 2) if weekend else rng.randint(2, 6)

        for _ in range(n_sessions):
            session_no += 1
            sid = "d%05x" % (rng.getrandbits(20))
            repo, _w = _pick(rng, REPOS)
            surface = rng.choice(SURFACES[repo])
            provider, model, effort, _p = _pick(rng, MODELS)
            # Working hours cluster 09:00-23:00 local (UTC+8) = 01:00-15:00 UTC,
            # which lands a good share of turns inside DeepSeek's peak window —
            # the thing the peak-shift detector should notice.
            start_hour = rng.choices(range(24), weights=(
                [3, 5, 7, 6, 5, 4, 6, 8, 9, 8, 6, 5, 4, 4, 3, 2, 1, 1, 1, 1, 2, 2, 3, 3]
            ))[0]
            ts = day.replace(hour=start_hour, minute=rng.randint(0, 55), second=0)

            # One in six sessions is a churn session: one big context load, a
            # couple of turns, gone. That is the pattern the cache detectors
            # exist to name.
            churn = rng.random() < 0.17
            turns = rng.randint(1, 3) if churn else rng.randint(4, 26)
            cached = 0

            for turn in range(1, turns + 1):
                ev = blank_event(provider)
                # Self-identifying, because a sentinel file next to the store is
                # not enough: `sync` clears it the moment real events arrive, and
                # the synthetic rows stay behind forever, indistinguishable and
                # silently driving vendor-specific panels (peak windows, model
                # mix) for vendors the reader has never used.
                ev["synthetic"] = True
                ts = ts + timedelta(minutes=rng.randint(1, 7))
                ev["ts"] = ts.isoformat().replace("+00:00", "Z")
                ev["session"] = sid
                ev["workspace"] = repo
                ev["repo"] = repo
                ev["surfaces"] = [surface]
                ev["surface"] = surface
                ev["branch"] = "main" if rng.random() < 0.4 else "feat/demo"
                ev["entrypoint"] = rng.choice(["cli", "cli", "cli", "ide", "desktop"])
                ev["lane"] = "personal" if repo == "growth-web" and rng.random() < 0.25 else "work"
                ev["model"] = model
                ev["effort"] = effort
                ev["turn"] = turn
                ev["sidechain"] = rng.random() < 0.12
                if ev["sidechain"]:
                    ev["agent"] = rng.choice(["explore", "general-purpose", "code-reviewer"])

                ev["output"] = rng.randint(40, 220) if rng.random() < 0.45 else rng.randint(400, 3200)
                if turn == 1:
                    ev["input"] = rng.randint(1200, 4000)
                    ev["cache_create"] = rng.randint(9000, 45000)
                    ev["cache_5m"] = ev["cache_create"]
                    cached = ev["cache_create"]
                else:
                    ev["input"] = rng.randint(120, 900)
                    ev["cache_read"] = int(cached * rng.uniform(0.85, 1.0))
                    if rng.random() < 0.22:
                        add = rng.randint(3000, 20000)
                        ev["cache_create"] = add
                        ev["cache_5m"] = add
                        cached += add

                n_tools = rng.randint(0, 4)
                for _t in range(n_tools):
                    roll = rng.random()
                    pool = (READ_TOOLS if roll < 0.55 else
                            WRITE_TOOLS if roll < 0.82 else OTHER_TOOLS)
                    ev["tools"].append(rng.choice(pool))
                ev["stop"] = "end_turn"
                events.append(ev)

    events.sort(key=lambda e: e["ts"])
    return events
