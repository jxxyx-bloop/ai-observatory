"""Aggregation tier — turns the event stream into a small digest (ADR-005).

This module exists so the expensive raw store is never what an analyst (human
or model) reads. `digest.json` is a few tens of KB and answers every question
the dashboard and the insight rules ask.

Pure stdlib, single pass over the events, no network.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import paths as topo
import pricing as price
import settings

# Claude Code writes this in place of a model name on internal turns.
PLACEHOLDER_MODEL = "<synthetic>"

# Tool names that mean "produced a change" vs "looked at something".
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit", "apply_patch",
               "create_file", "edit_file", "str_replace_editor",
               "replace_file_content", "multi_replace_file_content", "write_to_file", "generate_image"}
READ_TOOLS = {"Read", "Grep", "Glob", "NotebookRead", "read_file", "search",
              "grep", "list_dir", "view_file", "read_url_content", "search_web",
              "manage_task", "manage_subagents", "invoke_subagent", "run_command"}

# Providers stamp every turn in UTC. Dates, hour-of-day and session spans are
# all shown on the reader's own clock instead (settings.json ->
# timezone_offset_hours, "auto" by default). Raw events on disk stay untouched;
# only the digest — the presentation tier — is shifted.
#
# Resolved per timestamp rather than once at import, because "the machine's
# offset" is not a constant: a zone that observes DST was an hour off itself six
# months ago, and bucketing a January session with a July offset puts turns in
# the wrong hour and occasionally the wrong day. The stdlib does this without a
# tz database — `astimezone()` asks the OS for the offset in force at that
# instant — so the no-dependencies promise holds. Costs ~14ms over 30k events.
def _local_ts(ts: str) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return ts
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return (dt.replace(tzinfo=None) + settings.local_offset(dt)).isoformat()


load_pricing = price.load_pricing
cost_of = price.cost_of


def resolve_attribution(events) -> list:
    """Give every turn one repo and one surface.

    Only turns that name a file can be attributed directly, and plenty of turns
    (thinking, planning, running a command) name none. Within a session the
    subject barely changes from turn to turn, so an unattributed turn inherits
    the nearest attributed one — forward first, then backward for the run of
    turns before the session's first file touch. Turns in a session that never
    touched anything stay honestly unattributed.
    """
    rows = [dict(e) for e in events]
    rows.sort(key=lambda e: (e.get("session") or "", e.get("ts") or ""))

    by_session: dict = defaultdict(list)
    for i, ev in enumerate(rows):
        by_session[ev.get("session") or ""].append(i)

    for idx in by_session.values():
        # Real repos get first refusal on the whole session; a scratch or config
        # repo only fills the gaps no real repo can reach.
        for real_only in (True, False):
            for order in (idx, list(reversed(idx))):
                repo = surface = None
                for i in order:
                    ev = rows[i]
                    own = ev.get("surfaces") or []
                    here = ev.get("repo")
                    if here and not (real_only and topo.is_incidental(here)):
                        if here != repo:
                            surface = None
                        repo = here
                        if own:
                            surface = own[0]
                    if not here and repo:
                        ev["repo"] = here = repo
                        ev["inferred"] = True
                    if own:
                        ev["surface"] = own[0]
                    elif surface and here == repo and not ev.get("surface"):
                        ev["surface"] = surface
                        ev["inferred"] = True
    return rows


def _blank_bucket() -> dict:
    return {
        "turns": 0, "input": 0, "output": 0, "cache_create": 0, "cache_read": 0,
        "cache_1h": 0, "cache_5m": 0, "cost": 0.0, "sessions": set(),
    }


def _add(bucket: dict, ev: dict, cost: float) -> None:
    bucket["turns"] += 1
    for k in ("input", "output", "cache_create", "cache_read", "cache_1h", "cache_5m"):
        bucket[k] += ev.get(k) or 0
    bucket["cost"] += cost
    if ev.get("session"):
        bucket["sessions"].add(ev["session"])


def _finish(bucket: dict, key_name: str, key: str) -> dict:
    out = {key_name: key}
    out.update({k: v for k, v in bucket.items() if k != "sessions"})
    out["cost"] = round(out["cost"], 4)
    out["sessions"] = len(bucket["sessions"])
    return out


class Cube:
    """Dictionary-encoded fact table.

    Every dimension value becomes a small integer code and every metric an
    integer, so the whole history ships to the browser as a few thousand short
    arrays. That is what lets the dashboard re-aggregate for an arbitrary date
    range without a server or a second data file.
    """

    def __init__(self, dims, metrics):
        self.dims, self.metrics = list(dims), list(metrics)
        self.vals = {d: [] for d in self.dims}
        self._index = {d: {} for d in self.dims}
        self._rows: dict = {}

    # What a missing value is called, per dimension — "unset effort" and
    # "unattributed repo" are different kinds of absence and read differently.
    MISSING = {"repo": "unattributed", "surface": "unattributed",
               "effort": "unset", "hour": "unknown", "phase": "flat"}

    def _code(self, dim: str, value) -> int:
        value = self.MISSING.get(dim, "unknown") if value in (None, "") else str(value)
        idx = self._index[dim]
        if value not in idx:
            idx[value] = len(self.vals[dim])
            self.vals[dim].append(value)
        return idx[value]

    def add(self, key: dict, metrics) -> None:
        code = tuple(self._code(d, key.get(d)) for d in self.dims)
        row = self._rows.get(code)
        if row is None:
            row = self._rows[code] = [0] * len(self.metrics)
        for i, value in enumerate(metrics):
            row[i] += value

    def dump(self) -> dict:
        return {"dims": self.dims, "metrics": self.metrics, "vals": self.vals,
                "rows": [list(k) + v for k, v in sorted(self._rows.items())]}


# `phase` is peak | off-peak | flat — see pricing.window_phase. It rides in the
# cube rather than being recomputed client-side so the dashboard and the
# detectors can never disagree about which turns were time-priced.
CUBE_DIMS = ("date", "provider", "lane", "entrypoint", "repo", "surface",
             "model", "effort", "agent", "phase")
# `cost_floor_micro` is what the same turn would have cost at that vendor's
# off-peak rate. For a flat-priced model it equals `cost_micro`, so the
# difference across any slice is exactly the money on the table from moving
# work — no modelling, just arithmetic on the user's own tokens.
CUBE_METRICS = ("turns", "input", "output", "cache_create", "cache_read",
                "cache_1h", "cache_5m", "cost_micro", "cost_floor_micro",
                "writes", "reads", "tool_calls")


def _cube_row(ev: dict, cost: float, ts_local: str, pricing: dict) -> tuple:
    writes = reads = calls = 0
    for name in ev.get("tools") or []:
        calls += 1
        if name in WRITE_TOOLS:
            writes += 1
        elif name in READ_TOOLS:
            reads += 1
    key = {d: ev.get(d) for d in CUBE_DIMS}
    key["date"] = ts_local[:10]
    key["agent"] = ev.get("agent") if ev.get("sidechain") else "main thread"
    key["phase"] = ev.get("phase")
    floor = price.counterfactual_cost(ev, pricing, "off-peak")
    metrics = [1] + [ev.get(k) or 0 for k in
                     ("input", "output", "cache_create", "cache_read", "cache_1h", "cache_5m")]
    metrics += [round(cost * 1_000_000), round(floor * 1_000_000), writes, reads, calls]
    return key, metrics


def build_digest(events, pricing: dict) -> dict:
    """Single pass over events -> digest dict."""
    totals = _blank_bucket()
    by_day: dict = defaultdict(_blank_bucket)
    by_model: dict = defaultdict(_blank_bucket)
    by_workspace: dict = defaultdict(_blank_bucket)
    by_effort: dict = defaultdict(_blank_bucket)
    by_agent: dict = defaultdict(_blank_bucket)
    by_repo: dict = defaultdict(_blank_bucket)
    by_surface: dict = defaultdict(_blank_bucket)
    by_lane: dict = defaultdict(_blank_bucket)
    by_provider: dict = defaultdict(_blank_bucket)
    by_entrypoint: dict = defaultdict(_blank_bucket)
    by_hour = [0] * 24
    by_phase: dict = defaultdict(_blank_bucket)
    peak_premium = 0.0
    tool_counts: dict = defaultdict(int)
    # window key -> the providers in THIS dataset that bill on it. A window is
    # keyed by vendor ("zhipu") and an event carries a provider ("glm"); those
    # are two names for one company and nothing downstream can bridge them.
    window_providers: dict = defaultdict(set)
    sessions: dict = {}
    sidechain = _blank_bucket()
    first_ts = last_ts = None
    synthetic_events = 0
    # Turns whose model the rate card does not name. Their cost is the
    # fallback rate, which is a guess wearing the same typeface as a fact.
    unpriced_turns = 0
    unpriced_cost = 0.0
    unpriced_models: dict = defaultdict(int)

    cube = Cube(CUBE_DIMS, CUBE_METRICS)
    hours = Cube(("date", "provider", "lane", "repo", "hour"), ("turns",))
    tools = Cube(("date", "provider", "lane", "repo", "tool"), ("calls",))

    events = resolve_attribution(events)
    for ev in events:
        if ev.get("synthetic"):
            synthetic_events += 1
        cost = cost_of(ev, pricing)
        # A turn with no tokens costs nothing at any rate, and the placeholder
        # above is not a model the user picked. Neither is something the rate
        # card is missing, and reporting them as such produced a "part of this
        # estimate is a guess" finding about 0.0% of the spend.
        if (not price.is_priced(ev.get("model"), pricing)
                and ev.get("model") != PLACEHOLDER_MODEL and cost > 0):
            unpriced_turns += 1
            unpriced_cost += cost
            unpriced_models[price.canonical_model(ev.get("model")) or "unknown"] += 1
        ev["phase"] = price.window_phase(ev.get("model"), ev.get("ts"), pricing)
        if ev["phase"] == "peak":
            peak_premium += cost - price.counterfactual_cost(ev, pricing, "off-peak")
        ts = _local_ts(ev.get("ts") or "")
        _add(totals, ev, cost)
        if ts:
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts
            _add(by_day[ts[:10]], ev, cost)
            try:
                by_hour[int(ts[11:13])] += 1
            except (ValueError, IndexError):
                pass
        _add(by_model[ev.get("model") or "unknown"], ev, cost)
        _add(by_workspace[ev.get("workspace") or "unknown"], ev, cost)
        _add(by_effort[ev.get("effort") or "unset"], ev, cost)
        _add(by_repo[ev.get("repo") or "unattributed"], ev, cost)
        _add(by_surface[ev.get("surface") or "unattributed"], ev, cost)
        _add(by_lane[ev.get("lane") or "unknown"], ev, cost)
        _add(by_provider[ev.get("provider") or "unknown"], ev, cost)
        _add(by_entrypoint[ev.get("entrypoint") or "unknown"], ev, cost)
        _add(by_phase[ev.get("phase") or "unknown"], ev, cost)
        if ev.get("sidechain"):
            _add(sidechain, ev, cost)
            _add(by_agent[ev.get("agent") or "unnamed"], ev, cost)

        slice_key = {"date": ts[:10], "provider": ev.get("provider"),
                     "lane": ev.get("lane"), "repo": ev.get("repo")}
        cube.add(*_cube_row(ev, cost, ts, pricing))
        hours.add(dict(slice_key, hour=ts[11:13] or "??"), [1])
        _win = (pricing.get("models", {}).get(ev.get("model"), {}) or {}).get("window")
        if _win:
            window_providers[_win].add(ev.get("provider"))

        for name in ev.get("tools") or []:
            tool_counts[name] += 1
            tools.add(dict(slice_key, tool=name), [1])
        _session_roll(sessions, ev, cost, ts)

    return {
        "schema": 1,
        # Carried in the digest so the "this is sample data" banner survives the
        # hop to `report`, which runs as its own process and would otherwise
        # have only a sentinel file that `sync` is free to delete.
        "demo": synthetic_events > 0,
        "synthetic_events": synthetic_events,
        # Carried so the page and the findings can say which part of the
        # estimate rests on a published rate and which part does not.
        "unpriced": {
            "turns": unpriced_turns,
            "cost": round(unpriced_cost, 4),
            "models": sorted(unpriced_models, key=lambda m: -unpriced_models[m])[:8],
        },
        # The peak schedules travel with the digest so the dashboard can draw
        # them over the reader's own hours. A few hundred bytes, and without
        # them the page can say *when* you work but not *what that hour costs*
        # — which is the only reason the hour matters.
        "windows": {
            name: {
                "vendor": w.get("vendor"),
                "peak_utc": w.get("peak_utc") or [],
                "days": w.get("days"),
                "off_peak_mult": w.get("off_peak_mult", 1),
                "providers": sorted(p for p in window_providers.get(name, ()) if p),
            }
            for name, w in (pricing.get("windows") or {}).items()
            if "legacy" not in name and window_providers.get(name)
        },
        "window": {
            "first": first_ts, "last": last_ts,
            "days": len(by_day),
            "active_days": sorted(by_day.keys()),
        },
        "totals": _finish(totals, "scope", "all"),
        "sidechain": _finish(sidechain, "scope", "subagents"),
        "by_day": [_finish(v, "date", k) for k, v in sorted(by_day.items())],
        "by_model": sorted(
            (_finish(v, "model", k) for k, v in by_model.items()),
            key=lambda r: -r["output"],
        ),
        "by_workspace": sorted(
            (_finish(v, "workspace", k) for k, v in by_workspace.items()),
            key=lambda r: -r["cost"],
        ),
        "by_effort": sorted(
            (_finish(v, "effort", k) for k, v in by_effort.items()),
            key=lambda r: -r["turns"],
        ),
        "by_agent": sorted(
            (_finish(v, "agent", k) for k, v in by_agent.items()),
            key=lambda r: -r["output"],
        ),
        "by_tool": sorted(
            ({"tool": k, "calls": v} for k, v in tool_counts.items()),
            key=lambda r: -r["calls"],
        ),
        "by_repo": sorted(
            (_finish(v, "repo", k) for k, v in by_repo.items()),
            key=lambda r: -r["cost"],
        ),
        "by_surface": sorted(
            (_finish(v, "surface", k) for k, v in by_surface.items()),
            key=lambda r: -r["cost"],
        ),
        "by_lane": sorted(
            (_finish(v, "lane", k) for k, v in by_lane.items()),
            key=lambda r: -r["cost"],
        ),
        "by_provider": sorted(
            (_finish(v, "provider", k) for k, v in by_provider.items()),
            key=lambda r: -r["cost"],
        ),
        "by_entrypoint": sorted(
            (_finish(v, "entrypoint", k) for k, v in by_entrypoint.items()),
            key=lambda r: -r["cost"],
        ),
        "by_hour": by_hour,
        "by_phase": sorted(
            (_finish(v, "phase", k) for k, v in by_phase.items()),
            key=lambda r: -r["cost"],
        ),
        # What the peak-priced turns cost above their own vendor's off-peak
        # rate. Zero for anyone using only flat-priced vendors, which is the
        # honest answer — see docs/specs/Peak-Off-Peak-Pricing.md.
        "peak_premium_usd": round(peak_premium, 4),
        "sessions": _rank_sessions(sessions),
        "cube": cube.dump(),
        "hours": hours.dump(),
        "tools": tools.dump(),
    }


def _session_roll(sessions: dict, ev: dict, cost: float, ts_local: str) -> None:
    sid = ev.get("session") or "unknown"
    s = sessions.get(sid)
    if s is None:
        s = sessions[sid] = {
            "session": sid, "workspace": ev.get("workspace"),
            "provider": ev.get("provider"), "lane": ev.get("lane"),
            "entrypoint": ev.get("entrypoint"), "repo": ev.get("repo"),
            "branch": ev.get("branch"), "start": ts_local, "end": ts_local,
            "turns": 0, "input": 0, "output": 0, "cache_create": 0, "cache_read": 0,
            "cost": 0.0, "models": set(), "reads": 0, "writes": 0,
            "tool_calls": 0, "sidechain_turns": 0, "peak_context": 0,
            "surface_turns": defaultdict(int),
        }
    if not s.get("repo") and ev.get("repo"):
        s["repo"] = ev["repo"]
    if ev.get("surface"):
        s["surface_turns"][ev["surface"]] += 1
    if ts_local:
        if not s["start"] or ts_local < s["start"]:
            s["start"] = ts_local
        if not s["end"] or ts_local > s["end"]:
            s["end"] = ts_local
    s["turns"] += 1
    for k in ("input", "output", "cache_create", "cache_read"):
        s[k] += ev.get(k) or 0
    s["cost"] += cost
    # `<synthetic>` is Claude Code's placeholder for a zero-token internal turn,
    # not a model anyone chose. Counting it as one made every session that
    # contained a compaction look like a session that switched models, which is
    # the single input to model-switch share.
    if ev.get("model") and ev["model"] != PLACEHOLDER_MODEL:
        s["models"].add(ev["model"])
    if ev.get("sidechain"):
        s["sidechain_turns"] += 1
    # Context size for this turn = everything the model had to read.
    ctx = (ev.get("input") or 0) + (ev.get("cache_read") or 0) + (ev.get("cache_create") or 0)
    if ctx > s["peak_context"]:
        s["peak_context"] = ctx
    for name in ev.get("tools") or []:
        s["tool_calls"] += 1
        if name in WRITE_TOOLS:
            s["writes"] += 1
        elif name in READ_TOOLS:
            s["reads"] += 1


def _rank_sessions(sessions: dict) -> list:
    out = []
    for s in sessions.values():
        r = dict(s)
        r["models"] = sorted(s["models"])
        r["cost"] = round(s["cost"], 4)
        # What the session was mostly about, and how single-minded it was.
        surfaces = s.pop("surface_turns", {})
        ranked = sorted(surfaces.items(), key=lambda kv: -kv[1])
        r.pop("surface_turns", None)
        r["surface"] = ranked[0][0] if ranked else None
        r["surfaces"] = len(ranked)
        out.append(r)
    out.sort(key=lambda r: -r["output"])
    return out
