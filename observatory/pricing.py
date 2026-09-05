"""Cost model — rate card resolution, peak/off-peak windows, currency, plan value.

Split out of `analyze.py` because three separate things need the same answer:
the local digest, the optional community server (which re-prices what it is
given rather than trusting an uploaded number), and the tests.

Three things here are not in any other open-source token tracker, and they are
the reason this file exists:

1. **Peak/off-peak.** Chinese vendors bill tokens like electricity — DeepSeek
   charges full rate 01:00-04:00 and 06:00-10:00 UTC and half rate the rest of
   the day; Z.ai's GLM peaks only 14:00-18:00 UTC+8 on weekdays. A tracker that
   multiplies tokens by one flat rate is simply wrong for those vendors, and it
   cannot see the single biggest lever those users have: move the batch.
2. **Per-vendor cache economics.** The 0.1x cache-hit discount is an Anthropic
   convention, not a law. Moonshot prices cache hits at ~0.074x-0.2x depending
   on the model. Getting this wrong misprices the metric that matters most.
3. **Plan value.** Most of our users never pay per token. The dollar figure is
   a *shadow price* — what the same work would have cost on metered API — and
   its job is to be divided by what they actually paid.

See docs/specs/Cost-Estimation.md and docs/specs/Peak-Off-Peak-Pricing.md.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import home

PRICING_PATH = home.config_path("pricing.json")
PLANS_PATH = home.config_path("plans.json")

# Dated snapshots (`claude-haiku-4-5-20251001`) and the model's alias
# (`claude-haiku-4-5`) are the same model at the same price.
_DATE_SUFFIX = re.compile(r"-\d{8}$")

_PRICING = None
_PLANS = None


def load_pricing() -> dict:
    global _PRICING
    if _PRICING is None:
        _PRICING = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    return _PRICING


def load_plans() -> dict:
    global _PLANS
    if _PLANS is None:
        _PLANS = json.loads(PLANS_PATH.read_text(encoding="utf-8"))
    return _PLANS


def canonical_model(model):
    """Strip a date snapshot, then follow one alias hop."""
    if not isinstance(model, str):
        return model
    name = _DATE_SUFFIX.sub("", model)
    return load_pricing().get("aliases", {}).get(name, name)


def is_priced(model, pricing: dict) -> bool:
    """True when the rate card names this model, rather than guessing at it.

    `rates_for` falls back to a generic rate for anything it does not know,
    which is the right behaviour — a missing model should not silently cost
    nothing — but it makes an estimate that is a guess look exactly like one
    that is not. Everything downstream that wants to disclose the difference
    asks here.
    """
    return canonical_model(model) in (pricing.get("models") or {})


def rates_for(model, pricing: dict, speed=None) -> dict:
    """The rate card entry for a model, before any window adjustment."""
    name = canonical_model(model) or ""
    rates = pricing["models"].get(name) or pricing["fallback"]
    override = pricing.get("speed_overrides", {}).get("%s:%s" % (name, speed))
    if override:
        rates = dict(rates, **override)
    return rates


# --- peak / off-peak -------------------------------------------------------

def _hour_and_weekday(ts):
    """`2026-08-19T14:03:11Z` -> (14, 3). None when the stamp is unusable.

    Windows are evaluated in **UTC** on purpose: the event stamp is UTC, the
    vendor's schedule is converted to UTC in `pricing.json`, and nothing in
    between has to know where the laptop is.
    """
    if not isinstance(ts, str) or len(ts) < 13:
        return None, None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None, None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.hour, dt.weekday() + 1


def window_phase(model, ts, pricing: dict):
    """'peak' | 'off-peak' | 'flat' for one turn.

    'flat' is the honest answer for every vendor that does not run a schedule —
    it is not the same as 'peak', and the dashboard must not imply a user could
    have saved money by moving work that was never time-priced.
    """
    rates = rates_for(model, pricing)
    win_key = rates.get("window")
    if not win_key:
        return "flat"
    win = pricing.get("windows", {}).get(win_key)
    if not win:
        return "flat"
    hour, weekday = _hour_and_weekday(ts)
    if hour is None:
        return "unknown"
    days = win.get("days")
    if days and weekday not in days:
        return "off-peak"
    for start, end in win.get("peak_utc", []):
        if start <= hour < end:
            return "peak"
    return "off-peak"


def _window_mult(model, ts, pricing: dict) -> float:
    phase = window_phase(model, ts, pricing)
    if phase != "off-peak":
        return 1.0
    rates = rates_for(model, pricing)
    win = pricing.get("windows", {}).get(rates.get("window"), {})
    return float(win.get("off_peak_mult", 1.0))


# --- the cost of one turn --------------------------------------------------

def cost_of(ev: dict, pricing: dict) -> float:
    """USD estimate for one turn, at the rate in force when the turn happened."""
    model = ev.get("model") or ""
    rates = rates_for(model, pricing, ev.get("speed"))
    m = pricing["multipliers"]

    mult = _window_mult(model, ev.get("ts"), pricing)
    per_tok_in = rates["input"] / 1_000_000 * mult
    per_tok_out = rates["output"] / 1_000_000 * mult

    # The 0.1x cache-hit discount is Anthropic's convention, not a universal.
    cache_read_mult = rates.get("cache_read_mult", m["cache_read"])

    # The TTL split is only present when the provider reports it; when absent,
    # price the whole write at the cheaper 5m rate rather than overstating.
    c1h = ev.get("cache_1h") or 0
    c5m = ev.get("cache_5m") or 0
    if c1h + c5m == 0:
        c5m = ev.get("cache_create") or 0

    return (
        (ev.get("input") or 0) * per_tok_in
        + (ev.get("output") or 0) * per_tok_out
        + (ev.get("cache_read") or 0) * per_tok_in * cache_read_mult
        + c5m * per_tok_in * m["cache_write_5m"]
        + c1h * per_tok_in * m["cache_write_1h"]
    )


def counterfactual_cost(ev: dict, pricing: dict, phase: str) -> float:
    """What this turn would have cost had it run in `phase` instead.

    Used by the peak-shift detector so the saving it quotes is arithmetic on
    the user's own tokens, not a hand-wave. Returns the same number as
    `cost_of` for any model that is not time-priced.
    """
    model = ev.get("model") or ""
    rates = rates_for(model, pricing, ev.get("speed"))
    win = pricing.get("windows", {}).get(rates.get("window"))
    if not win:
        return cost_of(ev, pricing)
    now = _window_mult(model, ev.get("ts"), pricing)
    want = 1.0 if phase == "peak" else float(win.get("off_peak_mult", 1.0))
    base = cost_of(ev, pricing)
    return base / now * want if now else base


# --- currency and plan lenses ---------------------------------------------

def convert(usd: float, code: str, plans: dict = None):
    """USD -> (amount, symbol, decimals) in a display currency."""
    plans = plans or load_plans()
    cur = plans["currencies"].get(code) or plans["currencies"]["USD"]
    return usd * cur["per_usd"], cur["symbol"], cur["decimals"]


def plan_value(observed_usd: float, plan_id: str, days: int, plans: dict = None) -> dict:
    """What a flat plan actually returned over `days` of observed usage.

    `multiple` is the honest headline for a subscriber: API-equivalent value
    divided by what they paid. Below 1.0 it is an argument to downgrade, and
    the tool says so — a tool that only ever congratulates you is not a mirror.
    """
    plans = plans or load_plans()
    plan = plans["plans"].get(plan_id)
    if not plan:
        return {}
    monthly = observed_usd * 30.0 / max(1, days)
    price = float(plan.get("price_usd_month") or 0)
    out = {
        "plan": plan_id,
        "label": plan["label"],
        "price_usd_month": price,
        "api_equivalent_usd_month": round(monthly, 2),
    }
    if price > 0:
        out["multiple"] = round(monthly / price, 2)
        out["verdict"] = (
            "under-used" if monthly < price
            else "fair" if monthly < price * 3
            else "excellent"
        )
    return out
