"""Opt-in community payload — what leaves the machine, and nothing else.

The design rule is that this file is short enough to read in full before you
tick the box. If you cannot hold the whole of what gets shared in your head,
the consent is not informed, and a privacy policy is not a substitute for a
readable function.

Three properties it must have, in priority order:

1. **Allow-list, not deny-list.** The payload is built by naming every field
   that goes in. A new metric added upstream cannot leak by default; someone
   has to add it here on purpose, in a diff a reviewer can see.
2. **No free text, ever.** Repository names, folder names, branch names,
   workspace names and session ids are the fields most likely to carry an
   employer's confidential project name — so none of them cross the boundary.
   `settings.community.include_repo_names` exists and is honoured, but even
   when true it only opts you into *hashed* buckets, never the literal string.
3. **Coarse before it leaves, not after it arrives.** Metrics are bucketed on
   this machine. A server that receives a raw value and promises to bucket it
   is a server you have to trust; a server that never receives the raw value
   is not.

See docs/specs/Community-Share-Protocol.md for the wire format and
docs/adr/ADR-011-Community-Layer.md for why this exists at all.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pricing as price
import settings

PAYLOAD_VERSION = 1

# Every metric shared is bucketed to one of these edges before it leaves. The
# edges are fixed and versioned: changing one in place silently corrupts every
# comparison against previously-submitted data, so a revision adds `_v2` rather
# than editing a list. Log-spaced because usage across a developer population
# spans four orders of magnitude and a linear bucket wastes all its resolution
# at the top.
BUCKETS = {
    "turns_per_day":      [0, 5, 10, 20, 40, 80, 160, 320, 640, 1280],
    "sessions_per_day":   [0, 1, 2, 4, 8, 16, 32, 64],
    "output_per_day":     [0, 1e3, 5e3, 2e4, 8e4, 3e5, 1e6, 4e6, 1.6e7],
    "cost_per_day_usd":   [0, 0.1, 0.5, 2, 8, 25, 75, 200, 600],
    "cache_reuse_pct":    [0, 10, 20, 30, 40, 50, 60, 70, 80, 90],
    "turns_per_session":  [0, 2, 4, 8, 16, 32, 64],
    "calls_per_turn":     [0, 0.25, 0.5, 1, 2, 4, 8],
    "peak_share_pct":     [0, 10, 25, 50, 75, 90],
    "write_read_ratio":   [0, 0.1, 0.25, 0.5, 1, 2, 4],
}


def bucket(value, edges) -> int:
    """Index of the bucket `value` falls in. Never the value itself."""
    idx = 0
    for i, edge in enumerate(edges):
        if value >= edge:
            idx = i
    return idx


def _hash_bucket(name: str, salt: str, mod: int = 64) -> int:
    """A stable, non-reversible bucket for a name we will not transmit.

    Lets two people discover they work in a similarly-shaped repo without
    either name being recoverable. `mod` is small on purpose: a 64-way bucket
    over a large namespace is not an identifier.
    """
    digest = hashlib.sha256((salt + "\x00" + name).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % mod


def _pct(a, b):
    return 0.0 if not b else round(100.0 * a / b, 1)


def build(digest: dict) -> dict:
    """The complete share payload. Read this function to know what is shared."""
    cfg = settings.load()
    community = cfg.get("community", {})
    totals = digest["totals"]
    days = max(1, digest["window"].get("days") or 1)
    sessions = digest.get("sessions", [])
    pricing = price.load_pricing()

    read_total = totals["cache_read"] + totals["cache_create"] + totals["input"]
    phases = {r["phase"]: r for r in digest.get("by_phase", [])}
    timed = phases.get("peak", {}).get("cost", 0.0) + phases.get("off-peak", {}).get("cost", 0.0)

    per_day = {
        "turns_per_day": totals["turns"] / days,
        "sessions_per_day": len(sessions) / days,
        "output_per_day": totals["output"] / days,
        "cost_per_day_usd": totals["cost"] / days,
        "cache_reuse_pct": _pct(totals["cache_read"], read_total),
        "turns_per_session": totals["turns"] / max(1, len(sessions)),
        "calls_per_turn": totals.get("tool_calls", 0) / max(1, totals["turns"]),
        "peak_share_pct": _pct(phases.get("peak", {}).get("cost", 0.0), timed),
        "write_read_ratio": (sum(s.get("writes", 0) for s in sessions)
                             / max(1, sum(s.get("reads", 0) for s in sessions))),
    }

    # Vendor and tier mixes as shares, not counts — a count is a volume, and a
    # volume is a fingerprint. A share is a habit.
    vendors: dict = {}
    tiers: dict = {}
    for row in digest.get("by_model", []):
        meta = pricing["models"].get(row["model"]) or {}
        vendors[meta.get("vendor", "unknown")] = vendors.get(meta.get("vendor", "unknown"), 0) + row["output"]
        tiers[meta.get("tier", "unknown")] = tiers.get(meta.get("tier", "unknown"), 0) + row["output"]
    out_total = sum(vendors.values()) or 1

    payload = {
        "v": PAYLOAD_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_days": days,
        # Declared cohorts are the user's own words about themselves — a
        # country code, "solo", "agency". They are never derived from the data,
        # because a derived cohort is an inference the user did not consent to.
        "cohorts": [str(c)[:24] for c in community.get("cohorts", [])][:4],
        "plan": cfg.get("plan", "none"),
        "currency": cfg.get("currency", "USD"),
        "buckets_version": 1,
        "metrics": {k: bucket(v, BUCKETS[k]) for k, v in per_day.items()},
        "mix": {
            "vendor": {k: round(100.0 * v / out_total) for k, v in sorted(
                vendors.items(), key=lambda kv: -kv[1])[:6]},
            "tier": {k: round(100.0 * v / out_total) for k, v in sorted(
                tiers.items(), key=lambda kv: -kv[1])[:6]},
        },
        # Which findings fired, by id only. This is what makes the community
        # layer worth having: "62% of solo developers on a GLM plan have
        # peak-window-arbitrage open" is a fact no individual dashboard can
        # produce, and it carries no individual's numbers.
        "findings": sorted({f["id"] for f in digest.get("findings", [])}),
    }

    if community.get("include_repo_names"):
        payload["repo_shape"] = sorted({
            _hash_bucket(r["repo"], "repo-shape")
            for r in digest.get("by_repo", [])
            if r["repo"] not in ("unattributed", "unknown")
        })[:12]

    return payload


# Fields that must never appear in a payload, asserted rather than assumed.
# The test suite walks a built payload against this list; adding a field
# upstream cannot quietly defeat it.
FORBIDDEN_KEYS = {
    "repo", "repos", "by_repo", "surface", "surfaces", "by_surface",
    "workspace", "by_workspace", "session", "sessions", "branch", "path",
    "paths", "email", "handle", "cwd", "prompt", "completion", "content",
    "tools", "by_tool", "endpoint", "hostname", "user", "machine_id",
}


def audit(payload: dict) -> list:
    """Return every forbidden key found anywhere in the payload. Empty is a pass."""
    hits = []

    def walk(node, trail):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in FORBIDDEN_KEYS:
                    hits.append("/".join(trail + [k]))
                walk(v, trail + [str(k)])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, trail + [str(i)])

    walk(payload, [])
    return hits


def describe(payload: dict) -> str:
    """A plain-language summary printed before anything is ever uploaded."""
    lines = [
        "This is the complete payload. Nothing else would be sent.",
        "",
        json.dumps(payload, indent=1),
        "",
        "In words:",
        f"  · {len(payload['metrics'])} metrics, each as a BUCKET INDEX, never a raw value",
        f"  · vendor and model-tier mix as percentages",
        f"  · which finding ids fired ({len(payload['findings'])} of them), not their numbers",
        f"  · your declared cohorts: {payload['cohorts'] or '(none)'}",
        f"  · your plan id and display currency",
        "",
        "Not included: repository names, folder names, branch names, session ids,",
        "workspace names, file paths, tool arguments, prompts, completions, your",
        "email, your machine, or any raw token count.",
    ]
    problems = audit(payload)
    if problems:
        lines += ["", "!! AUDIT FAILED — forbidden keys present: " + ", ".join(problems)]
    return "\n".join(lines)
