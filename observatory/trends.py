"""Price trends — how each lab's model lines got cheaper or dearer, as data.

The page this feeds answers one question: *what is going up and what is going
down?* Two things make that harder than reading a price list.

**A model's four prices are not one price.** Input, output, cache read and cache
write each moved on their own schedule, and for an agentic coding session the
cache read is nearly all of the bill (97% of the tokens, on the maintainer's own
store). Anthropic's Opus 5 -> 5.5 is a 20% cut in list price and a 46% cut for
that workload, because cache reads went from 0.1x to 0.05x of the input price.
So every line is also reduced to ONE number: the cost of 1M tokens of a
reference mix (`reference_mix` in `pricing.json`), or of the reader's own mix.

**A lab's flagship is replaced, not repriced.** Opus 4.8 -> Opus 5 is a new model
at the same price; Opus 5 -> 5.5 is a new model at a lower one. A chart of
"Opus 5" alone would stop on the day it was succeeded. So prices are charted per
*line* (`lines` in `pricing.json`): the model a lab offered in a tier, and when
the next one took over.

Everything here is a pure function of the rate card, so the dashboard, the
tests and any other front end read the same numbers. Prices are piecewise
constant, so a line is a short list of change points, not a daily series; the
reader draws steps between them. Dates are Singapore-time calendar days — the
benchmark the rest of the rate card is kept in.

See docs/specs/Price-Trends.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pricing as price

SGT = price.SGT

# The four prices of a model, as $ per 1M tokens of that kind of token.
COMPONENTS = ("input", "output", "cache_read", "cache_write")
# Below this, a move is noise (rounding in a vendor's own announcement).
FLAT_PCT = 1.0


def _day(dt: datetime) -> str:
    return dt.astimezone(SGT).strftime("%Y-%m-%d")


def components(model: str, pricing: dict, at) -> dict:
    """The model's four prices, as in force at `at`, in $ per 1M tokens of each kind."""
    r = price.rates_for(model, pricing, at=at)
    m = pricing["multipliers"]
    i = r["input"]
    return {"input": i, "output": r["output"],
            "cache_read": i * r.get("cache_read_mult", m["cache_read"]),
            "cache_write": i * m["cache_write_5m"]}


def effective(c: dict, mix: dict) -> float:
    """$ per 1M tokens of a workload with token shares `mix`."""
    return (mix["input"] * c["input"] + mix["cache_write"] * c["cache_write"]
            + mix["cache_read"] * c["cache_read"] + mix["output"] * c["output"])


def mix_from_totals(totals: dict):
    """The reader's own token mix, from a digest's `totals`. None when empty."""
    parts = {"input": totals.get("input") or 0, "cache_write": totals.get("cache_create") or 0,
             "cache_read": totals.get("cache_read") or 0, "output": totals.get("output") or 0}
    n = sum(parts.values())
    return {k: v / n for k, v in parts.items()} if n else None


def _instants(line: dict, pricing: dict, today: str) -> list:
    """Every moment this line's price could have changed: each model taking
    over, and each model's own repricing while it held the line."""
    entries = line["models"]
    when = []
    for i, e in enumerate(entries):
        start = price.instant(e["from"])
        end = price.instant(entries[i + 1]["from"]) if i + 1 < len(entries) else None
        when.append((start, e["model"]))
        for h in (pricing.get("history") or {}).get(e["model"], []):
            t = price.instant(h["until"])
            if t > start and (end is None or t < end):
                when.append((t, e["model"]))
    return sorted(w for w in when if _day(w[0]) <= today)


def _line(line: dict, pricing: dict, mixes: dict, today: str) -> dict:
    points = {}
    for at, model in _instants(line, pricing, today):
        # The model in charge is whichever the line says holds it at that moment.
        holder = [e["model"] for e in line["models"] if price.instant(e["from"]) <= at][-1]
        c = components(holder, pricing, at)
        pt = {"date": _day(at), "model": holder}
        pt.update({k: round(v, 6) for k, v in c.items()})
        pt["eff_ref"] = round(effective(c, mixes["reference"]), 6)
        if mixes.get("yours"):
            pt["eff_you"] = round(effective(c, mixes["yours"]), 6)
        points[pt["date"]] = pt          # two changes on one day: the later one stands
    pts = [points[d] for d in sorted(points)]
    return {"id": line["id"], "lab": line["lab"], "label": line["label"], "tier": line["tier"],
            "headline": bool(line.get("headline")),
            "models": [e["model"] for e in line["models"]
                       if _day(price.instant(e["from"])) <= today],
            "points": pts}


def _events(line: dict) -> list:
    out, pts = [], line["points"]
    for i, p in enumerate(pts):
        if i == 0:
            out.append({"date": p["date"], "line": line["id"], "lab": line["lab"],
                        "kind": "launch", "model": p["model"], "from_model": None,
                        "delta_pct": None, "changed": []})
            continue
        q = pts[i - 1]
        changed = [{"component": k, "from": q[k], "to": p[k]}
                   for k in COMPONENTS if abs(p[k] - q[k]) > 1e-9]
        delta = (p["eff_ref"] / q["eff_ref"] - 1) * 100 if q["eff_ref"] else None
        if p["model"] != q["model"]:
            kind = "succession"
        elif changed:
            kind = "cut" if p["eff_ref"] < q["eff_ref"] else "rise"
        else:
            continue
        out.append({"date": p["date"], "line": line["id"], "lab": line["lab"], "kind": kind,
                    "model": p["model"], "from_model": q["model"],
                    "delta_pct": None if delta is None else round(delta, 2), "changed": changed})
    return out


def _watch(lines: list, pricing: dict, today: str) -> list:
    """Rates the vendor has said will end, whose successor nobody has published."""
    out, now = [], datetime.fromisoformat(today)
    for line in lines:
        model = line["models"][-1]
        r = (pricing["models"].get(model) or {})
        if "recheck_after" in r:
            day = _day(price.instant(r["recheck_after"]))
            out.append({"line": line["id"], "model": model, "recheck_after": day,
                        "days_left": (datetime.fromisoformat(day) - now).days})
    return sorted(out, key=lambda w: w["recheck_after"])


def _untraced(pricing: dict, traced: set) -> list:
    """Vendors on the card with a current price and no traced history — shown as
    such, rather than drawn as a flat line that reads as 'never changed'."""
    by = {}
    for name, r in (pricing.get("models") or {}).items():
        v = r.get("vendor")
        if v and v not in traced and v != "opencode":
            by.setdefault(v, []).append(name)
    verified = pricing.get("_verified_by_vendor") or {}
    return [{"vendor": v, "models": len(ms), "examples": ms[:3],
             "verified_on": verified.get(v) or pricing.get("_verified_on")}
            for v, ms in sorted(by.items(), key=lambda kv: -len(kv[1]))]


def build(pricing: dict, totals: dict = None, today: str = None) -> dict:
    """The whole payload the Prices page reads. `totals` is a digest's totals,
    for the reader's own mix; `today` is an SGT day, for tests."""
    today = today or _day(datetime.now(SGT))
    mixes = {"reference": pricing["reference_mix"],
             "yours": mix_from_totals(totals or {})}
    lines = [_line(l, pricing, mixes, today) for l in pricing.get("lines") or []]
    lines = [l for l in lines if l["points"]]
    events = sorted((e for l in lines for e in _events(l)), key=lambda e: (e["date"], e["line"]),
                    reverse=True)
    verified = pricing.get("_verified_by_vendor") or {}
    labs = []
    for lab_id, label in (pricing.get("labs") or {}).items():
        mine = [l for l in lines if l["lab"] == lab_id]
        if mine:
            labs.append({"id": lab_id, "label": label, "lines": [l["id"] for l in mine],
                         "traced_since": min(l["points"][0]["date"] for l in mine),
                         "verified_on": verified.get(lab_id) or pricing.get("_verified_on")})
    return {"schema": 1, "as_of": today, "tz": "SGT", "components": list(COMPONENTS),
            "mixes": mixes, "labs": labs, "lines": lines, "events": events,
            "watch": _watch(lines, pricing, today),
            "untraced": _untraced(pricing, {l["lab"] for l in lines})}
