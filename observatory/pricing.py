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

4. **A price is only right for a moment in time.** A vendor cuts a model's
   price, or ends an introductory rate; a flat card then makes every month
   before the change look as cheap (or dear) as the month after. `pricing.json`
   keeps the superseded rates in `history`, each with the window it applied for,
   and `cost_of` prices a turn at the rate in force at its own timestamp. Every
   boundary is written in Singapore time (`+08:00`) — one benchmark for the whole
   card, enforced by `validate_card`. See "Dated rates" in
   docs/specs/Cost-Estimation.md.

See docs/specs/Cost-Estimation.md and docs/specs/Peak-Off-Peak-Pricing.md.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import home

PRICING_PATH = home.config_path("pricing.json")
PLANS_PATH = home.config_path("plans.json")

# Dated snapshots (`claude-haiku-4-5-20251001`) and the model's alias
# (`claude-haiku-4-5`) are the same model at the same price.
_DATE_SUFFIX = re.compile(r"-\d{8}$")

# A gateway (LiteLLM, OpenRouter, a company's own) can hand the model back wrapped:
# `llm-gateway--gpt-5.6-sol` or `openai/gpt-5.6-sol`. The wrapper names the road the
# request took, not the model, and left in place it makes one model two rows that
# neither match the card.
#
# An explicit list, not a pattern: this runs on the label of every turn, so
# over-stripping silently renames a real model id (`some--model` is a legitimate,
# if odd, name) while under-stripping only leaves one gateway spelling as its own
# row until it is added here - and a model the card does not recognise is disclosed
# as unpriced rather than guessed at. A new gateway's prefix is one line below, once
# it has actually been seen.
GATEWAY_WRAPPERS = ("llm-gateway--",)
_VENDOR_SLASH = re.compile(r"^(?:openai|anthropic|google|azure|bedrock|vertex)/")

# The rate card's own time zone. See `instant`.
SGT = timezone(timedelta(hours=8), "SGT")
# Keys that describe a rate rather than price with it.
_NOTES = {"from", "until", "recheck_after", "source", "precision", "note"}

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


def strip_gateway(model):
    """`llm-gateway--gpt-5.6-sol` and `openai/gpt-5.6-sol` -> `gpt-5.6-sol`.

    Only a KNOWN wrapper goes (see `GATEWAY_WRAPPERS`); the name is left as the vendor
    spelled it, so this is safe to apply to what is *displayed* and grouped, not just
    to what is priced. A wrapper with nothing after it is left alone.
    """
    if not isinstance(model, str):
        return model
    s = model.strip()
    for wrapper in GATEWAY_WRAPPERS:
        if s.startswith(wrapper) and len(s) > len(wrapper):
            s = s[len(wrapper):]
    m = _VENDOR_SLASH.match(s)
    return (s[m.end():] if m and len(s) > m.end() else s) or None


def canonical_model(model):
    """Strip a gateway prefix and a date snapshot, then follow one alias hop."""
    if not isinstance(model, str):
        return model
    name = _DATE_SUFFIX.sub("", strip_gateway(model) or "")
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


@lru_cache(maxsize=None)
def instant(value) -> datetime:
    """A rate-card boundary -> an aware UTC datetime.

    Strict on purpose: a boundary with no UTC offset is an error, not a guess.
    The card is kept in Singapore time, and a naive time silently read as UTC
    would move a price change by eight hours.
    """
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("rate-card time has no UTC offset: %r" % (value,))
    return dt.astimezone(timezone.utc)


def _event_instant(ts):
    """An event stamp -> an aware UTC datetime, or None when unusable.

    Events are UTC by convention (the collectors write `...Z`), so — unlike a
    card boundary — a stamp with no offset is read as UTC rather than refused.
    """
    if isinstance(ts, datetime):
        dt = ts
    else:
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _rates_at(base: dict, history: list, when: datetime) -> dict:
    """The version of `base` in force at `when`.

    `history` is superseded versions, oldest first, each ending where the next
    begins (`validate_card` checks that), and `base` is the version after the
    last. So the answer is the first version that has not yet ended. The first
    entry's `from` is the model's launch and is informational: it applies to
    anything earlier too.
    """
    for h in history:
        if when < instant(h["until"]):
            return dict(base, **{k: v for k, v in h.items() if k not in _NOTES})
    return base


def rates_for(model, pricing: dict, speed=None, at=None) -> dict:
    """The rate card entry for a model, before any window adjustment.

    With `at` (an event stamp or an aware datetime) it is the rate in force then;
    without it, the rate in force now.
    """
    name = canonical_model(model) or ""
    rates = pricing["models"].get(name) or pricing["fallback"]
    history = (pricing.get("history") or {}).get(name)
    if history and at is not None:
        when = _event_instant(at)
        if when is not None:
            rates = _rates_at(rates, history, when)
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
    rates = rates_for(model, pricing, ev.get("speed"), ev.get("ts"))
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


# --- keeping the card honest -----------------------------------------------

def validate_card(pricing: dict) -> list:
    """Problems with the card's own structure. Empty means well-formed.

    Dated rates are only trustworthy if the windows are: every boundary in
    Singapore time, no gap or overlap between one version and the next, and the
    current rate starting exactly where the last superseded one ends.
    """
    problems = []

    def check_time(where, value):
        if not isinstance(value, str) or not value.endswith("+08:00"):
            problems.append("%s: %r must be an ISO time ending +08:00 (Singapore)" % (where, value))
            return None
        try:
            return instant(value)
        except ValueError:
            problems.append("%s: %r is not a valid time" % (where, value))
            return None

    models = pricing.get("models") or {}
    for name, history in (pricing.get("history") or {}).items():
        base = models.get(name)
        if base is None:
            problems.append("history[%s]: no such model in models" % name)
            continue
        prev_until = None
        for i, h in enumerate(history):
            start = check_time("history[%s][%d].from" % (name, i), h.get("from"))
            end = check_time("history[%s][%d].until" % (name, i), h.get("until"))
            if start and end and end <= start:
                problems.append("history[%s][%d]: until is not after from" % (name, i))
            if i and start and prev_until and start != prev_until:
                problems.append("history[%s][%d]: from does not meet the previous until" % (name, i))
            prev_until = end
        cur = check_time("models[%s].from" % name, base.get("from"))
        if cur and prev_until and cur != prev_until:
            problems.append("models[%s].from does not meet history's last until" % name)
    for name, r in models.items():
        for key in ("from", "recheck_after"):
            if key in r:
                check_time("models[%s].%s" % (name, key), r[key])

    # The price-trends page reads `lines`; a line that names a missing model or
    # runs backwards would draw a wrong chart with no error to point at.
    labs, seen = pricing.get("labs") or {}, set()
    for line in pricing.get("lines") or []:
        lid = line.get("id")
        if not lid or lid in seen:
            problems.append("lines: id %r is missing or repeated" % (lid,))
        seen.add(lid)
        if line.get("lab") not in labs:
            problems.append("lines[%s]: lab %r is not in labs" % (lid, line.get("lab")))
        prev = None
        if not line.get("models"):
            problems.append("lines[%s]: no models" % lid)
        for i, entry in enumerate(line.get("models") or []):
            if entry.get("model") not in models:
                problems.append("lines[%s][%d]: %r is not on the card" % (lid, i, entry.get("model")))
            at = check_time("lines[%s][%d].from" % (lid, i), entry.get("from"))
            if at and prev and at <= prev:
                problems.append("lines[%s][%d]: from is not after the previous model's" % (lid, i))
            prev = at or prev
    mix = pricing.get("reference_mix")
    if mix is not None and abs(sum(mix.values()) - 1.0) > 0.001:
        problems.append("reference_mix sums to %.4f, not 1" % sum(mix.values()))
    return problems


def review_due(pricing: dict, now=None) -> list:
    """Rates whose documented end has passed and need a person to re-check:
    `[(model, recheck_after)]`. They keep pricing in the meantime — the vendor
    has not published a successor, and inventing one would be worse."""
    when = now or datetime.now(timezone.utc)
    return sorted((n, r["recheck_after"]) for n, r in (pricing.get("models") or {}).items()
                  if "recheck_after" in r and instant(r["recheck_after"]) <= when)
