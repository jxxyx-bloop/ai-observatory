"""Insight rules — deterministic detectors over the digest (PRD 03).

Every finding carries: what was observed, the numbers behind it, what to do,
and a confidence level. No finding without evidence — see
docs/specs/Insight-Catalogue.md for the catalogue and the thresholds.

Deliberately rule-based, not model-generated: the rules run in milliseconds,
cost nothing, and are reproducible. A model reads these findings later to
reason about them; it does not have to derive them.
"""

from __future__ import annotations

import pricing as price
import settings

# Tuning knobs. Raise or lower these as your own baseline becomes clear.
T = {
    "cold_cache_min_tokens": 20_000,   # cache written in a session before we care
    "cache_read_share_floor": 0.55,    # below this, context is being rebuilt too often
    "light_turn_output": 150,          # output tokens that count as a "light" turn
    "light_turn_share": 0.30,          # share of premium turns that must be light to flag
    "explore_min_reads": 6,            # reads before a zero-write session is notable
    "explore_min_cost": 0.50,          # and it has to have cost something
    "context_bloat_tokens": 300_000,   # peak per-turn context worth flagging
    "short_session_turns": 3,          # a session this small is probably a restart
    "short_session_share": 0.40,
    "subagent_share_high": 0.50,
    "tool_concentration": 0.40,
    # Materiality gate. A cost-driven finding worth less than this per month is
    # real but not worth acting on — it gets demoted rather than deleted, so the
    # top of the list always means something.
    "material_monthly_usd": 15.0,
    # Regional thresholds.
    "peak_share_floor": 0.35,          # share of time-priced spend inside peak
    "peak_min_monthly_usd": 5.0,       # below this the shift isn't worth the habit change
    "plan_underuse_ratio": 1.0,        # API-equivalent below plan price = paying for air
    "concentration_floor": 0.85,       # single-vendor share that counts as lock-in
}

PREMIUM_TIERS = {"frontier", "opus"}


def _f(id_, severity, title, finding, action, evidence, confidence, saving=None):
    out = {
        "id": id_, "severity": severity, "title": title, "finding": finding,
        "action": action, "evidence": evidence, "confidence": confidence,
    }
    if saving is not None:
        out["est_monthly_saving_usd"] = round(saving, 2)
    return out


def _pct(n, d):
    return 0.0 if not d else round(100.0 * n / d, 1)


def generate(digest: dict, pricing: dict) -> list:
    """Run every detector. Returns findings sorted most-severe first."""
    findings = []
    for fn in DETECTORS:
        try:
            findings.extend(fn(digest, pricing) or [])
        except (KeyError, TypeError, ZeroDivisionError):
            continue  # a detector that can't run on this data stays silent
    for f in findings:
        saving = f.get("est_monthly_saving_usd")
        if saving is not None and saving < T["material_monthly_usd"] and f["severity"] in ("high", "medium"):
            f["severity"] = "low"
            f["demoted"] = (
                f"Real but immaterial at this volume (~${saving:.2f}/month). Kept so you can "
                f"see the pattern before it grows."
            )
    rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
    findings.sort(key=lambda f: (rank.get(f["severity"], 9), -(f.get("est_monthly_saving_usd") or 0)))
    return findings


def _days(digest):
    return max(1, digest["window"].get("days") or 1)


def _monthly(amount, digest):
    """Scale an observed amount to a 30-day rate."""
    return amount * 30.0 / _days(digest)


def cache_efficiency(digest, pricing):
    t = digest["totals"]
    served = t["cache_read"]
    read_total = served + t["cache_create"] + t["input"]
    share = served / read_total if read_total else 0
    if share >= T["cache_read_share_floor"]:
        return [_f(
            "cache-healthy", "info",
            "Cache is doing its job",
            f"{_pct(served, read_total)}% of everything the models read came from cache "
            f"rather than being re-billed at full input rate.",
            "No action. Watch this number — a fall means sessions are being restarted more often.",
            {"cache_read_share_pct": _pct(served, read_total),
             "cache_read": served, "cache_create": t["cache_create"], "fresh_input": t["input"]},
            "high",
        )]
    # Every token re-created instead of read costs 12.5x the read price.
    m = pricing["multipliers"]
    excess = t["cache_create"] * (m["cache_write_5m"] - m["cache_read"]) * 5.0 / 1_000_000
    return [_f(
        "cache-cold", "high",
        "Context is being rebuilt more than it is reused",
        f"Only {_pct(served, read_total)}% of read tokens came from cache — below the "
        f"{int(T['cache_read_share_floor']*100)}% floor. Cache writes cost 1.25x input; "
        f"cache reads cost 0.1x. Rebuilding is ~12x the price of reusing.",
        "Keep working sessions alive instead of starting fresh ones. Batch related "
        "questions into one session, and avoid re-opening the same large files in new sessions.",
        {"cache_read_share_pct": _pct(served, read_total),
         "cache_create": t["cache_create"], "cache_read": served, "fresh_input": t["input"]},
        "high", _monthly(excess, digest),
    )]


def cold_cache_sessions(digest, pricing):
    victims = [s for s in digest["sessions"]
               if s["cache_create"] >= T["cold_cache_min_tokens"] and s["cache_read"] == 0]
    if not victims:
        return []
    wasted = sum(s["cache_create"] for s in victims)
    cost = sum(s["cost"] for s in victims)
    return [_f(
        "cache-write-never-read", "high",
        "Sessions that paid to cache and then ended",
        f"{len(victims)} session(s) wrote {wasted:,} tokens to cache and never read one "
        f"back — the 1.25x write premium paid for nothing.",
        "Ask the follow-ups in the same session — the second turn is where caching starts "
        "paying. These were closed right after the first big context load.",
        {"sessions": len(victims), "tokens_written_unused": wasted,
         "observed_cost_usd": round(cost, 2),
         "examples": [{"session": s["session"], "workspace": s["workspace"],
                       "turns": s["turns"], "cache_create": s["cache_create"]}
                      for s in sorted(victims, key=lambda x: -x["cache_create"])[:5]]},
        "high", _monthly(cost * 0.2, digest),
    )]


def premium_model_on_light_work(digest, pricing):
    prem, light_out, prem_out, prem_turns, light_turns = [], 0, 0, 0, 0
    for row in digest["by_model"]:
        tier = (pricing["models"].get(row["model"]) or pricing["fallback"]).get("tier")
        if tier in PREMIUM_TIERS and row["turns"]:
            prem.append(row)
            prem_turns += row["turns"]
            prem_out += row["output"]
    if prem_turns < 20:
        return []
    avg = prem_out / prem_turns
    if avg >= T["light_turn_output"]:
        return []
    # Rough: the same work on Sonnet would cost input/output at Sonnet rates.
    sonnet = pricing["models"].get("claude-sonnet-5") or pricing["fallback"]
    opus = pricing["models"].get("claude-opus-5") or pricing["fallback"]
    delta = (opus["output"] - sonnet["output"]) / 1_000_000
    saving = prem_out * delta * 0.4  # assume only 40% is genuinely delegable
    return [_f(
        "premium-tier-light-turns", "medium",
        "Premium models are handling a lot of very short turns",
        f"Across {prem_turns:,} premium-tier turns the mean output is {avg:.0f} tokens — "
        f"below {T['light_turn_output']}. Short turns are usually acknowledgements, "
        f"lookups, or mechanical edits, which a cheaper tier handles identically.",
        "Route mechanical work (file reads, renames, single-line edits, status checks) to "
        "Sonnet or Haiku, or run them at low effort. Keep the premium tier for the turns "
        "where reasoning depth actually changes the answer.",
        {"premium_turns": prem_turns, "mean_output_tokens": round(avg, 1),
         "models": [r["model"] for r in prem]},
        "medium", _monthly(saving, digest),
    )]


def exploration_without_output(digest, pricing):
    victims = [s for s in digest["sessions"]
               if s["reads"] >= T["explore_min_reads"] and s["writes"] == 0
               and s["cost"] >= T["explore_min_cost"]]
    if not victims:
        return []
    cost = sum(s["cost"] for s in victims)
    reads = sum(s["reads"] for s in victims)
    return [_f(
        "read-heavy-no-change", "medium",
        "Sessions that read a lot and changed nothing",
        f"{len(victims)} session(s) made {reads} read-type tool calls with no edit or "
        f"write, at {cost:.2f} USD. Some is real research; some is hunting for what a "
        f"targeted search would have found.",
        ["Delegate 'where is X' to a search subagent — the answer comes back without the "
         "file bodies.",
         "Ask the question you want answered rather than reading toward it."],
        {"sessions": len(victims), "read_calls": reads, "observed_cost_usd": round(cost, 2),
         "examples": [{"session": s["session"], "workspace": s["workspace"],
                       "reads": s["reads"], "cost_usd": s["cost"]}
                      for s in sorted(victims, key=lambda x: -x["cost"])[:5]]},
        "medium", _monthly(cost * 0.3, digest),
    )]


def context_bloat(digest, pricing):
    victims = [s for s in digest["sessions"] if s["peak_context"] >= T["context_bloat_tokens"]]
    if not victims:
        return []
    worst = max(victims, key=lambda s: s["peak_context"])
    return [_f(
        "context-bloat", "medium",
        "Some sessions carry a very large context per turn",
        f"{len(victims)} session(s) peaked above {T['context_bloat_tokens']:,} tokens on a "
        f"single turn (worst: {worst['peak_context']:,}), and every later turn re-reads it.",
        ["Finish the thread and start the next piece of work in a fresh session.",
         "Carry forward only what that work needs — an exploration transcript dragged into "
         "unrelated work is what makes context this expensive."],
        {"sessions": len(victims), "worst_peak_context": worst["peak_context"],
         "worst_session": worst["session"], "worst_workspace": worst["workspace"]},
        "medium",
    )]


def session_churn(digest, pricing):
    sessions = digest["sessions"]
    if len(sessions) < 10:
        return []
    short = [s for s in sessions if s["turns"] <= T["short_session_turns"]]
    share = len(short) / len(sessions)
    if share < T["short_session_share"]:
        return []
    return [_f(
        "session-churn", "medium",
        "A large share of sessions are only a few turns long",
        f"{len(short)} of {len(sessions)} sessions ({_pct(len(short), len(sessions))}%) ended "
        f"within {T['short_session_turns']} turns. Short sessions never amortise their own "
        f"context load — the cache write is paid, the reads never happen.",
        "Before starting a new session, check whether the question belongs to one you already "
        "have open. Treat a session as a workspace for a topic, not a container for a question.",
        {"short_sessions": len(short), "total_sessions": len(sessions),
         "share_pct": _pct(len(short), len(sessions))},
        "medium",
    )]


def subagent_leverage(digest, pricing):
    total_out = digest["totals"]["output"]
    sub_out = digest["sidechain"]["output"]
    if not total_out:
        return []
    share = sub_out / total_out
    if share == 0:
        return [_f(
            "no-delegation", "low",
            "No subagent delegation observed",
            "Every token was produced in the main conversation. Subagents keep bulk reading "
            "out of your main context — the search happens elsewhere and only the conclusion "
            "comes back.",
            "For broad 'find all the places that…' questions, delegate. The main context "
            "stays small, which keeps every later turn cheaper.",
            {"subagent_output_share_pct": 0.0},
            "medium",
        )]
    if share > T["subagent_share_high"]:
        return [_f(
            "subagent-fanout", "medium",
            "Most output is coming from subagents",
            f"{_pct(sub_out, total_out)}% of all output tokens were produced by subagents. "
            f"Delegation is good; delegation that re-establishes context per agent is not.",
            "Check whether fan-out size is matched to the work. Several agents each re-reading "
            "the same files costs more than one agent reading them once.",
            {"subagent_output_share_pct": _pct(sub_out, total_out),
             "subagent_turns": digest["sidechain"]["turns"]},
            "medium",
        )]
    return [_f(
        "delegation-balanced", "info",
        "Subagent delegation looks proportionate",
        f"{_pct(sub_out, total_out)}% of output came from subagents — enough to keep bulk "
        f"reading out of the main context without runaway fan-out.",
        "No action.",
        {"subagent_output_share_pct": _pct(sub_out, total_out)},
        "medium",
    )]


def cache_ttl_choice(digest, pricing):
    t = digest["totals"]
    writes = t["cache_1h"] + t["cache_5m"]
    if writes < 100_000:
        return []
    share_1h = t["cache_1h"] / writes
    if share_1h < 0.5:
        return []
    m = pricing["multipliers"]
    # 1h writes cost 2x input; they only pay off across three-plus reads.
    reads_per_write = t["cache_read"] / writes if writes else 0
    if reads_per_write >= 3:
        return [_f(
            "cache-1h-justified", "info",
            "Long-TTL caching is paying off",
            f"{_pct(t['cache_1h'], writes)}% of cache writes used the 1-hour TTL, and each "
            f"written token is read back {reads_per_write:.1f} times on average — above the "
            f"~3x break-even for the 2x write premium.",
            "No action.",
            {"cache_1h_share_pct": _pct(t["cache_1h"], writes),
             "reads_per_write": round(reads_per_write, 2)},
            "medium",
        )]
    excess = t["cache_1h"] * (m["cache_write_1h"] - m["cache_write_5m"]) * 5.0 / 1_000_000
    return [_f(
        "cache-1h-underused", "medium",
        "Long-TTL cache writes are not being read back enough to pay for themselves",
        f"{_pct(t['cache_1h'], writes)}% of cache writes used the 1-hour TTL (2x input rate) "
        f"but written tokens are only read back {reads_per_write:.1f} times. The 1-hour TTL "
        f"needs roughly three reads to beat the 5-minute one.",
        "This is a session-length signal, not a setting to change: the long TTL is there so "
        "you can come back after a gap. If you are not coming back, the gap is the problem.",
        {"cache_1h_share_pct": _pct(t["cache_1h"], writes),
         "reads_per_write": round(reads_per_write, 2)},
        "medium", _monthly(excess, digest),
    )]


def tool_concentration(digest, pricing):
    tools = digest["by_tool"]
    if not tools:
        return []
    total = sum(r["calls"] for r in tools)
    top = tools[0]
    if total < 50 or top["calls"] / total < T["tool_concentration"]:
        return []
    return [_f(
        "tool-concentration", "low",
        f"{top['tool']} accounts for a large share of all tool calls",
        f"{top['tool']} was called {top['calls']} times — {_pct(top['calls'], total)}% of all "
        f"{total} tool calls. A single dominant tool usually means a workflow that could be "
        f"one step instead of many.",
        f"Check what {top['tool']} repeats on. The same target twice in a session is "
        f"context you already had.",
        {"tool": top["tool"], "calls": top["calls"], "share_pct": _pct(top["calls"], total),
         "total_calls": total,
         "next": [{"tool": r["tool"], "calls": r["calls"]} for r in tools[1:4]]},
        "medium",
    )]


def investment_concentration(digest, pricing):
    ws = [w for w in digest["by_workspace"] if w["workspace"] != "unknown"]
    if len(ws) < 3:
        return []
    total = sum(w["cost"] for w in ws)
    if total <= 0:
        return []
    top = ws[0]
    return [_f(
        "where-the-time-goes", "info",
        "Where your AI investment is concentrated",
        f"{top['workspace']} took {_pct(top['cost'], total)}% of estimated spend across "
        f"{top['sessions']} sessions; the top three take "
        f"{_pct(sum(w['cost'] for w in ws[:3]), total)}%.",
        "Compare this ranking against where you would say your priorities are. A workspace "
        "high on this list and low on your own priority list is the finding.",
        {"top": [{"workspace": w["workspace"], "cost_usd": w["cost"],
                  "share_pct": _pct(w["cost"], total), "sessions": w["sessions"],
                  "turns": w["turns"]} for w in ws[:8]]},
        "high",
    )]


def working_rhythm(digest, pricing):
    hours = digest["by_hour"]
    total = sum(hours)
    if total < 50:
        return []
    peak = max(range(24), key=lambda h: hours[h])
    late = sum(hours[0:6]) + sum(hours[22:24])
    return [_f(
        "working-rhythm", "info",
        "When you actually use AI",
        f"Peak hour is {peak:02d}:00 ({hours[peak]} turns). {_pct(late, total)}% of turns fall "
        f"outside 06:00-22:00.",
        "Useful as a check on whether AI use is displacing focus time or filling gaps. "
        "A high out-of-hours share is worth knowing about for its own sake.",
        {"peak_hour": peak, "peak_turns": hours[peak],
         "out_of_hours_share_pct": _pct(late, total), "by_hour": hours},
        "high",
    )]




# --- regional and plan-aware detectors --------------------------------------
# Everything below this line exists because the user base this project is built
# for buys AI differently from the one the incumbents were built for: flat
# monthly plans instead of metered credit, vendors that price tokens by the
# hour, and a currency that is not the one on the invoice.


def peak_window_arbitrage(digest, pricing):
    """Time-priced vendors bill by the hour. Most users never notice."""
    rows = {r["phase"]: r for r in digest.get("by_phase", [])}
    peak = rows.get("peak")
    off = rows.get("off-peak")
    if not peak or not peak.get("turns"):
        return []
    timed_cost = peak["cost"] + (off["cost"] if off else 0.0)
    if timed_cost <= 0:
        return []
    premium = digest.get("peak_premium_usd") or 0.0
    share = peak["cost"] / timed_cost
    monthly = _monthly(premium, digest)
    vendors = sorted({
        (pricing["models"].get(r["model"]) or {}).get("vendor")
        for r in digest.get("by_model", [])
        if (pricing["models"].get(r["model"]) or {}).get("window")
    } - {None})

    if share < T["peak_share_floor"]:
        return [_f(
            "peak-window-healthy", "info",
            "Time-priced work is already landing off-peak",
            f"Only {_pct(peak['cost'], timed_cost)}% of your "
            f"{', '.join(vendors) or 'time-priced'} spend fell inside a peak window. The "
            f"premium you paid for the timing was about ${premium:.2f} over the period.",
            "No action. This is the number to watch if you start scheduling batch runs.",
            {"peak_share_pct": _pct(peak["cost"], timed_cost),
             "peak_premium_usd": round(premium, 2), "vendors": vendors},
            "high",
        )]

    if monthly < T["peak_min_monthly_usd"]:
        # The share is high but the money is not. Say both. A headline of
        # "already landing off-peak" over a number reading 55% is a tool
        # contradicting itself, and a tool that contradicts itself gets closed.
        return [_f(
            "peak-window-immaterial", "low",
            "Most time-priced work runs at peak, but the premium is small so far",
            f"{_pct(peak['cost'], timed_cost)}% of your {', '.join(vendors)} spend landed "
            f"inside a peak window — the same pattern as the expensive version of this "
            f"finding. At today's volume the timing only costs about ${monthly:.2f} a "
            f"month, which is not worth changing a habit over.",
            "Nothing to do now. Worth revisiting if your time-priced volume grows: the same "
            "percentage on ten times the tokens is ten times the premium.",
            {"peak_share_pct": _pct(peak["cost"], timed_cost),
             "peak_premium_usd": round(premium, 2),
             "est_monthly_premium_usd": round(monthly, 2), "vendors": vendors},
            "high",
        )]

    return [_f(
        "peak-window-arbitrage", "high",
        "You are buying tokens at peak rates you did not have to pay",
        f"{_pct(peak['cost'], timed_cost)}% of your time-priced spend "
        f"({', '.join(vendors)}) ran inside a peak window, where the same tokens cost up to "
        f"twice the off-peak rate. That timing cost about ${premium:.2f} over the period.",
        ["Queue unattended work for an off-peak hour — test generation, migrations, "
         "doc sweeps, bulk refactors.",
         "Leave interactive work where it is: the premium buys your attention, and a batch "
         "job does not need it.",
         "The windows are narrow — DeepSeek 01:00-04:00 and 06:00-10:00 UTC, GLM "
         "14:00-18:00 UTC+8 on weekdays, so weekends are free of it entirely."],
        {"peak_share_pct": _pct(peak["cost"], timed_cost),
         "peak_cost_usd": round(peak["cost"], 2),
         "off_peak_cost_usd": round(off["cost"], 2) if off else 0.0,
         "peak_premium_usd": round(premium, 2), "vendors": vendors},
        "high", monthly,
    )]


def plan_value_realised(digest, pricing):
    """A subscriber's real question is not 'what did I spend' but 'was it worth it'."""
    plan_id = settings.get("plan", "none")
    if not plan_id or plan_id == "none":
        return []
    days = _days(digest)
    value = price.plan_value(digest["totals"]["cost"], plan_id, days)
    if not value or not value.get("price_usd_month"):
        return []
    mult = value["multiple"]
    label = value["label"]
    api = value["api_equivalent_usd_month"]
    paid = value["price_usd_month"]

    if mult < T["plan_underuse_ratio"]:
        return [_f(
            "plan-under-used", "high",
            f"{label} is costing more than the work you are putting through it",
            f"Over {days} days your usage was worth about ${api:.2f}/month at metered API "
            f"rates. You pay ${paid:.2f}/month. You are buying headroom you are not using.",
            "Either move down a tier, or move work onto the plan deliberately — the plan is "
            "already paid for, so anything you are still doing by hand is free to delegate "
            "until you cross the line.",
            {"api_equivalent_usd_month": api, "plan_price_usd_month": paid,
             "multiple": mult, "days_observed": days},
            "high", paid - api,
        )]
    return [_f(
        "plan-value-realised", "info",
        f"{label} returned about {mult:.1f}x what you paid for it",
        f"Over {days} days your usage was worth about ${api:.2f}/month at metered API rates "
        f"against a ${paid:.2f}/month plan. The dollar figures elsewhere on this page are a "
        f"shadow price — what this work would have cost metered — not a bill you received.",
        "No action. Worth re-checking after any tier change, and worth knowing before you "
        "argue for a bigger plan.",
        {"api_equivalent_usd_month": api, "plan_price_usd_month": paid,
         "multiple": mult, "verdict": value["verdict"], "days_observed": days},
        "high",
    )]


def vendor_concentration(digest, pricing):
    """Single-vendor dependence is a resilience finding, not a cost one."""
    by_vendor = {}
    for row in digest.get("by_model", []):
        v = (pricing["models"].get(row["model"]) or {}).get("vendor", "unknown")
        by_vendor[v] = by_vendor.get(v, 0) + row["output"]
    total = sum(by_vendor.values())
    if total <= 0 or len(by_vendor) < 1:
        return []
    top, top_out = max(by_vendor.items(), key=lambda kv: kv[1])
    if top_out / total < T["concentration_floor"]:
        return [_f(
            "vendor-mix-healthy", "info",
            "Work is spread across more than one vendor",
            f"{top} is your largest at {_pct(top_out, total)}% of output tokens, across "
            f"{len(by_vendor)} vendors in total.",
            "No action. A mix is what lets you re-price or re-route without re-learning "
            "a workflow.",
            {"top_vendor": top, "share_pct": _pct(top_out, total),
             "vendors": len(by_vendor)},
            "medium",
        )]
    return [_f(
        "vendor-concentration", "medium",
        f"Almost everything runs through {top}",
        f"{_pct(top_out, total)}% of your output tokens came from {top}. Rate changes, "
        f"regional availability, and outages at one vendor are all single points of failure "
        f"for your entire workflow — and you have no measured baseline to compare a "
        f"switch against.",
        "Run one recurring, low-stakes class of work (test scaffolding, commit messages, "
        "doc updates) on a second vendor for a fortnight. The point is not to save money "
        "immediately; it is to know what switching would cost you before you are forced to.",
        {"top_vendor": top, "share_pct": _pct(top_out, total),
         "by_vendor": sorted(by_vendor.items(), key=lambda kv: -kv[1])[:6]},
        "medium",
    )]


def local_currency_context(digest, pricing):
    """A USD figure is not a number most of this project's users think in."""
    code = settings.get("currency", "USD")
    if code == "USD":
        return []
    plans = price.load_plans()
    cur = plans["currencies"].get(code)
    if not cur:
        return []
    monthly_usd = _monthly(digest["totals"]["cost"], digest)
    amount, symbol, dec = price.convert(monthly_usd, code, plans)
    out = {"currency": code, "monthly_local": round(amount, dec),
           "monthly_usd": round(monthly_usd, 2), "fx_per_usd": cur["per_usd"]}
    rate = cur.get("daily_dev_rate_usd")
    tail = ""
    if rate:
        out["equivalent_dev_days"] = round(monthly_usd / rate, 2)
        tail = (f" That is roughly {out['equivalent_dev_days']:.1f} days of a median local "
                f"contract rate — the comparison that decides whether this is cheap.")
    return [_f(
        "local-currency", "info",
        "What this costs where you are",
        f"About {symbol}{amount:,.{dec}f} a month at the rate in plans.json "
        f"(${monthly_usd:.2f}).{tail}",
        "No action. FX in this repo is indicative and hand-maintained — treat it as a "
        "sense-check, not accounting.",
        out, "medium",
    )]


def duplicated_turns(digest, pricing):
    """Say when the page's own totals are too big, and name the fix.

    Three shipped bugs could each write the same turn twice — an interrupted
    sync, two syncs at once, and `sync --full`. All three are fixed, but a
    store damaged before the fix stays damaged: its only symptom is numbers
    that look like a busy month, which is indistinguishable from a busy month.

    `doctor` counts these too, and a person who already suspects their
    dashboard runs `doctor`. This is for the person who does not suspect it.
    No saving is attached — the spend is not real, so neither is a saving.
    """
    d = digest.get("duplicates") or {}
    dupes = d.get("turns") or 0
    if not dupes:
        return []
    distinct = d.get("distinct") or 0
    total = dupes + distinct
    share = _pct(dupes, total)
    return [_f(
        "duplicated-turns", "high" if share >= 5 else "medium",
        "Some turns are counted more than once",
        f"{dupes:,} of {total:,} turns in the store ({share}%) are repeats of a turn "
        f"already there, so every total on this page — turns, tokens and spend — is "
        f"that much too high. This is a damaged store, not usage: an interrupted sync, "
        f"two syncs at once, or a `sync --full` run before the repair landed. The "
        f"duplicates are identical in provider, session, timestamp, turn and token "
        f"counts, which is why they can be identified at all.",
        ["Run `python3 observe.py dedupe`, then `python3 observe.py digest report`. "
         "It keeps the first copy of each turn and is safe on a healthy store.",
         f"Re-read this page afterwards — expect roughly {share}% off every total."],
        {"duplicate_turns": dupes, "distinct_turns": distinct,
         "share_of_store_pct": share},
        "high",
    )]


def unpriced_estimate(digest, pricing):
    """Say which part of the dollar figure rests on a rate nobody published.

    `rates_for` falls back to a generic rate for a model the card does not
    name, which is the right call — a model missing from a JSON file should not
    silently cost nothing — but the number it produces is rendered in the same
    typeface as one that came from a vendor's published page. New models ship
    every few weeks; this is the ordinary case, not an exotic one.

    No saving is attached. This is not a lever, it is the error bar.
    """
    u = digest.get("unpriced") or {}
    turns = u.get("turns") or 0
    if not turns:
        return []
    cost = u.get("cost") or 0.0
    total = (digest.get("totals") or {}).get("cost") or 0.0
    share = _pct(cost, total)
    models = u.get("models") or []
    named = ", ".join(models[:3]) + (" and others" if len(models) > 3 else "")
    fb = pricing.get("fallback") or {}
    return [_f(
        "unpriced-models", "medium" if share >= 10 else "info",
        "Part of this estimate is a guess",
        f"{share}% of the estimated spend (${cost:,.2f} across {turns:,} turns) came from "
        f"models the rate card does not name: {named}. Those turns are priced at the "
        f"generic fallback of ${fb.get('input', 0):g}/M in and ${fb.get('output', 0):g}/M "
        f"out, which is a placeholder, not that vendor's published rate. The rest of the "
        f"page cannot tell you which way the error runs.",
        [f"Add the model to observatory/pricing.json with the vendor's published rate and "
         f"move `_verified_on` to today — CONTRIBUTING.md calls this the five-minute PR.",
         f"Until then, read the {share}% as unmeasured rather than as spend."],
        {"unpriced_turns": turns, "unpriced_cost_usd": round(cost, 2),
         "share_of_spend_pct": share, "models": models,
         "fallback_rate": {"input": fb.get("input"), "output": fb.get("output")}},
        "high",
    )]


DETECTORS = [
    cache_efficiency,
    cold_cache_sessions,
    premium_model_on_light_work,
    exploration_without_output,
    context_bloat,
    session_churn,
    subagent_leverage,
    cache_ttl_choice,
    tool_concentration,
    investment_concentration,
    working_rhythm,
    peak_window_arbitrage,
    plan_value_realised,
    vendor_concentration,
    local_currency_context,
    unpriced_estimate,
    duplicated_turns,
]
