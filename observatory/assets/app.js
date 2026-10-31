/* AI Observatory — client. Re-aggregates the inlined fact cube for whatever
   date range and slicers are selected. No network, no dependencies. */
(function () {
"use strict";

var D = JSON.parse(document.getElementById("digest").textContent);
var $ = function (id) { return document.getElementById(id); };

var MON_EN = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
/* Read per call, like the weekday names: an axis label drawn before the reader
   picks a language would otherwise stay in English until the next redraw. */
function mon(m) { return t18("mon", MON_EN.join(",")).split(",")[m] || MON_EN[m]; }
var DOW_EN = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
/* Read per call rather than cached: the language switches without a reload,
   and every caller is already inside a redraw. */
function dow(w) { return t18("dow", DOW_EN.join(",")).split(",")[w] || DOW_EN[w]; }

function esc(s) {
  return String(s == null ? "—" : s).replace(/[&<>"']/g, function (c) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
  });
}
function num(n) {
  n = Number(n) || 0;
  var u = [[1e9,"B"],[1e6,"M"],[1e3,"k"]];
  for (var i = 0; i < u.length; i++) {
    if (Math.abs(n) >= u[i][0]) {
      return (n / u[i][0]).toFixed(2).replace(/\.?0+$/, "") + u[i][1];
    }
  }
  return n.toLocaleString(undefined, {maximumFractionDigits: 0});
}
/* Money is always computed in USD and displayed in the user's currency. The
   conversion is a display lens, not accounting — see plans.json. Named `usd`
   still because every call site passes a USD amount; only the output moves. */
var CUR = D.settings || {symbol: "$", per_usd: 1, decimals: 2, currency: "USD",
                         tz_label: "UTC"};
function usd(n) {
  n = (Number(n) || 0) * (CUR.per_usd || 1);
  var d = CUR.decimals == null ? 2 : CUR.decimals;
  if (Math.abs(n) >= 100000) return CUR.symbol + num(n);
  /* Cents only where they are still signal. An estimate that is itself good to a
     few percent has no business printing "$7,618.54" — the Hangar port rounds
     everything from ten up to the dollar, and so does this. */
  var f = Math.abs(n) < 10 ? d : 0;
  return CUR.symbol + n.toLocaleString(undefined,
    {minimumFractionDigits: f, maximumFractionDigits: f});
}
function count(n) {
  return (Number(n) || 0).toLocaleString(undefined, {maximumFractionDigits: 0});
}
function pctOf(a, b) { return b ? (100 * a / b) : 0; }
/* OpenCode's Zen catalog suffixes every free community model's id with `-free`
   — the same convention pricing.py keys off. Kept in sync with that rule, not
   derived from it: the cube carries a cost, never a tier. */
function isFree(model) { return /-free$/i.test(String(model || "")); }
/* One-off lookup for strings used inside a chart, where re-rendering on a
   language switch is cheaper than tagging every generated node. */
function t18(key, fallback) {
  if (typeof I18N === "undefined") return fallback;
  var v = I18N.dict(document.documentElement.getAttribute("data-lang") || "en")[key];
  return v || fallback;
}

/* Same lookup with %TOKEN% substitution, for the interface lines that carry a
   number. Values arrive already formatted (and escaped where the result meets
   innerHTML); this only seats them inside the translated frame, so a language
   can put the number where its own grammar wants it. */
function tf(key, fallback, vals) {
  var out = t18(key, fallback);
  for (var k in vals) out = out.split("%" + k + "%").join(vals[k]);
  return out;
}

/* ---- metric explainers ---------------------------------------------------
   Every behavioral metric gets a small ⓘ affordance carrying its own formula
   and intent, via the same data-tt tooltip every chart already uses. One
   copy per metric, reused everywhere that metric appears so wording never
   drifts between the KPI tile and its trend sparkline. */
var INFO = {
  turnsPerSession: "How many exchanges a typical task takes. Total turns ÷ sessions. Falling over time = you're resolving things in fewer round-trips.",
  toolCallsPerTurn: "How often each turn actually does something vs. just talks. Total tool calls ÷ total turns. Near zero = chatbot-style use; higher = agentic use.",
  modelSwitchShare: "Share of sessions that used more than one model. Sessions with >1 distinct model ÷ all sessions. Subagent turns count, so a session where only a subagent ran a smaller model reads as a switch; zero-token `<synthetic>` placeholder turns do not. High and rising can mean you're matching model to task; high and flat can mean indecision.",
  writeRead: "Edits made per file looked at. Write-tool calls ÷ read-tool calls. Low = mostly exploring; high = mostly producing.",
  heatmap: "When turns actually happen, by hour in " + CUR.tz_label + " \u2014 darker means more turns in that hour, on that weekday, across the selected range."
};
function info(key) {
  var t = INFO[key];
  if (!t) return "";
  return ' <span class="info" tabindex="0" role="img" aria-label="What this measures" data-tt="'
    + esc(t) + '">i</span>';
}

/* ---- findings, in whatever language is selected --------------------------
   render.py bakes the findings panel once, in English, from insights.py's own
   sentences — the same sentences a downstream reader of the raw digest still
   gets. Every other locale rewrites that panel's text after paint rather than
   asking Python to compose 13 versions of 25 detectors: the numbers already
   travel in `D.findings[i].i18n_params`, put there by the same locals each
   detector built its English sentence from, so translating is substitution
   into assets/i18n.js's f_<id>_* templates rather than re-deriving anything.
   A JS failure (I18N missing, a key absent) leaves the English that render.py
   already wrote — this only ever overwrites, it never blanks a card. */

// One shared vocabulary of param names across all 25 detectors, and one
// formatter per name, rather than a bespoke mapping per finding. Two
// exceptions (marked below) carry a shape `tf()`'s plain substitution can't
// express — a conditional sentence and a conditional word — and are composed
// by hand instead of through this table.
function findPct(v) { return String(v) + "%"; }
function findMult(v) { return String(v) + "x"; }
function findNum(v, dec) {
  var n = Number(v) || 0;
  return n.toLocaleString(undefined,
    {minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0});
}
function findPad2(v) { return String(v).padStart(2, "0"); }
var FIND_FMT = {
  "cache-healthy": {pct: findPct},
  "cache-cold": {pct: findPct, floor: function (v) { return findNum(v, 0); }},
  "cache-write-never-read": {
    n: function (v) { return findNum(v, 0); }, wasted: function (v) { return findNum(v, 0); }},
  "premium-tier-light-turns": {
    turns: function (v) { return findNum(v, 0); }, avg: function (v) { return findNum(v, 0); },
    threshold: function (v) { return findNum(v, 0); }},
  // `cost` here stays a bare number (the English reads "12.34 USD", not
  // "$12.34") — the one detector that named its own currency instead of
  // using the page's, so it is the one param that skips usd().
  "read-heavy-no-change": {
    n: function (v) { return findNum(v, 0); }, reads: function (v) { return findNum(v, 0); },
    cost: function (v) { return findNum(v, 2); }},
  "context-bloat": {
    n: function (v) { return findNum(v, 0); }, threshold: function (v) { return findNum(v, 0); },
    worst: function (v) { return findNum(v, 0); }},
  "session-churn": {
    short: function (v) { return findNum(v, 0); }, total: function (v) { return findNum(v, 0); },
    pct: findPct, turns: function (v) { return findNum(v, 0); }},
  "no-delegation": {},
  "subagent-fanout": {pct: findPct},
  "delegation-balanced": {pct: findPct},
  "cache-1h-justified": {pct: findPct, ratio: function (v) { return findNum(v, 1); }},
  "cache-1h-underused": {pct: findPct, ratio: function (v) { return findNum(v, 1); }},
  "tool-concentration": {
    tool: String, calls: function (v) { return findNum(v, 0); }, pct: findPct,
    total: function (v) { return findNum(v, 0); }},
  "where-the-time-goes": {
    ws: String, pct: findPct, n: function (v) { return findNum(v, 0); }, pct3: findPct},
  "working-rhythm": {
    peak: findPad2, turns: function (v) { return findNum(v, 0); }, pct: findPct},
  "peak-window-healthy": {pct: findPct, vendors: String, premium: usd},
  "peak-window-immaterial": {pct: findPct, vendors: String, monthly: usd},
  "peak-window-arbitrage": {pct: findPct, vendors: String, premium: usd},
  "plan-under-used": {
    label: String, days: function (v) { return findNum(v, 0); }, api: usd, paid: usd},
  "plan-value-realised": {
    label: String, mult: findMult, days: function (v) { return findNum(v, 0); },
    api: usd, paid: usd},
  "vendor-mix-healthy": {top: String, pct: findPct, n: function (v) { return findNum(v, 0); }},
  "vendor-concentration": {top: String, pct: findPct},
  // `days` (dev-day equivalent) is conditional — composed by hand below.
  "local-currency": {usd: usd},
  "duplicated-turns": {
    dupes: function (v) { return findNum(v, 0); }, total: function (v) { return findNum(v, 0); },
    share: findPct},
  // `named`/`more` are composed by hand below.
  "unpriced-models": {
    share: findPct, cost: usd, turns: function (v) { return findNum(v, 0); },
    fb_in: usd, fb_out: usd}
};

function translateFindings() {
  var findings = D.findings || [];
  if (!findings.length) return;
  findings.forEach(function (f) {
    var el = document.querySelector('.find[data-fid="' + f.id + '"]');
    if (!el) return;
    var key = "f_" + f.id.replace(/-/g, "_");
    var raw = f.i18n_params || {}, fmt = FIND_FMT[f.id] || {}, vals = {};
    for (var k in raw) {
      if (raw[k] == null) continue;
      var fn = fmt[k];
      vals[k.toUpperCase()] = fn ? fn(raw[k]) : String(raw[k]);
    }
    // The two shapes plain %TOKEN% substitution cannot express: a sentence
    // that only sometimes exists, and a word that only sometimes appears.
    // Both are handed a fully-formed value under a token like any other —
    // the templates below never see the conditional, only its result.
    if (f.id === "local-currency") {
      vals.TAIL = (raw.days != null)
        ? " " + tf("f_local_currency_tail", "That is roughly %D% days of a median local "
            + "contract rate — the comparison that decides whether this is cheap.",
            {D: findNum(raw.days, 1)})
        : "";
    }
    if (f.id === "unpriced-models") {
      vals.NAMED = (raw.named || "") + (raw.more
        ? " " + t18("f_and_others", "and others") : "");
    }
    var ttl = el.querySelector(".ttl");
    if (ttl) ttl.textContent = tf(key + "_title", f.title, vals);
    var body = el.querySelector(".body");
    if (body) body.textContent = tf(key + "_body", f.finding, vals);
    // "Do this." leads the recommendation. It is an attribute the stylesheet
    // reads, not a child node, because the two lines below overwrite this
    // element's text and a child would go with it.
    var lead = el.querySelector(".act");
    if (lead) lead.setAttribute("data-lead", t18("f_dothis", "Do this."));
    var actP = el.querySelector(".act:not(.acts)");
    if (actP) actP.textContent = tf(key + "_action", f.action, vals);
    var items = el.querySelectorAll(".acts li");
    if (items.length) {
      items.forEach(function (li, i) {
        var en = Array.isArray(f.action) ? f.action[i] : "";
        li.textContent = tf(key + "_action" + (i + 1), en, vals);
      });
    }
    var sev = el.querySelector(".sev");
    if (sev) sev.textContent = t18("sev_" + f.severity, f.severity);
    var conf = el.querySelector(".conf");
    if (conf && f.confidence) {
      conf.textContent = t18("conf_label", "Confidence:") + " "
        + t18("conf_" + f.confidence, f.confidence);
    }
    var saving = f.est_monthly_saving_usd;
    var save = el.querySelector(".save");
    if (save && saving) {
      save.textContent = tf("save_permo", "\u2248%V%/mo", {V: usd(saving)});
    }
    var demoted = el.querySelector(".demoted");
    if (demoted && saving != null) {
      demoted.textContent = tf("demoted_note",
        "Real but immaterial at this volume (~%V%/month). Kept so you can see "
        + "the pattern before it grows.", {V: usd(saving)});
    }
  });
}

/* ---- behavioral metrics ---------------------------------------------------
   Favor these over raw volume: they say whether AI collaboration is getting
   more effective, not just how much of it happened. Whole-range turns/session
   and model-switch share are computed per-day instead, inside
   sessionSeries()/behavioralTrends() below, now that the scoreboard only
   shows their trend rather than a whole-window snapshot. */
function toolCallsPerTurn(t) { return t.turns ? t.tool_calls / t.turns : 0; }

/* ---- dates: everything is a plain YYYY-MM-DD string in UTC ---- */
function parse(iso) { return new Date(iso + "T00:00:00Z"); }
/* Guards every entry point that reaches `parse`. The filters are the only
   place a string arrives from outside the digest, and the only place one can
   be blank. */
function validDay(s) {
  return typeof s === "string" && /^\d{4}-\d{2}-\d{2}$/.test(s)
    && !isNaN(parse(s).getTime());
}
function iso(d) { return d.toISOString().slice(0, 10); }
function shift(isoStr, days) {
  var d = parse(isoStr); d.setUTCDate(d.getUTCDate() + days); return iso(d);
}
function span(from, to) {
  if (!validDay(from) || !validDay(to)) return [];
  var out = [], cur = from;
  while (cur <= to && out.length < 800) { out.push(cur); cur = shift(cur, 1); }
  return out;
}
function dayInfo(isoStr) {
  var d = parse(isoStr);
  return {dow: dow(d.getUTCDay()), dom: String(d.getUTCDate()).padStart(2, "0"),
          mon: mon(d.getUTCMonth())};
}
function longDate(isoStr) {
  var p = dayInfo(isoStr);
  return p.dow + " " + p.dom + " " + p.mon + " " + isoStr.slice(0, 4);
}
/* Rows run Monday to Sunday, as they do on the Hangar port — a working week
   reads top to bottom, and the weekend sits together at the bottom instead of
   being split across both ends. Indices stay `getUTCDay()` (Sunday = 0), so
   every lookup keyed that way is unchanged; only the drawing order moves. */
var WEEK = [1, 2, 3, 4, 5, 6, 0];

/* ---- cube query ---------------------------------------------------------
   Every cube is dictionary-encoded: a row is [dim codes…, metric values…].
   `index` maps a name to its column so lookups stay O(1) per row. ---------- */
function index(c) {
  var ix = {};
  c.dims.forEach(function (d, i) { ix[d] = i; });
  c.metrics.forEach(function (m, i) { ix["@" + m] = c.dims.length + i; });
  return ix;
}
var CUBE = index(D.cube), HOURS = index(D.hours), TOOLS = index(D.tools);

// `except` lets a chart ignore the filter it is itself the picker for, so the
// repo chart keeps showing every repo while one of them is selected.
function keep(c, ix, row, F, except) {
  var date = c.vals.date[row[ix.date]];
  if (date < F.from || date > F.to) return false;
  var keys = ["provider", "lane", "repo"];
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i];
    if (k === except || F[k] === "All" || ix[k] === undefined) continue;
    if (c.vals[k][row[ix[k]]] !== F[k]) return false;
  }
  return true;
}

function agg(c, ix, F, by, except) {
  var map = Object.create(null), out = [];
  for (var r = 0; r < c.rows.length; r++) {
    var row = c.rows[r];
    if (!keep(c, ix, row, F, except)) continue;
    var vals = by.map(function (d) { return c.vals[d][row[ix[d]]]; });
    var key = vals.join(""), acc = map[key];
    if (!acc) {
      acc = map[key] = {};
      by.forEach(function (d, i) { acc[d] = vals[i]; });
      c.metrics.forEach(function (m) { acc[m] = 0; });
      out.push(acc);
    }
    for (var m = 0; m < c.metrics.length; m++) {
      acc[c.metrics[m]] += row[ix["@" + c.metrics[m]]];
    }
  }
  out.forEach(function (a) { if ("cost_micro" in a) a.cost = a.cost_micro / 1e6; });
  return out;
}

function totals(F) {
  var t = {turns: 0, input: 0, output: 0, cache_create: 0, cache_read: 0,
           cache_1h: 0, cache_5m: 0, cost: 0, writes: 0, reads: 0, tool_calls: 0,
           sub_turns: 0, sub_output: 0, days: 0};
  var days = Object.create(null);
  agg(D.cube, CUBE, F, ["date", "agent"]).forEach(function (r) {
    ["turns","input","output","cache_create","cache_read","cache_1h","cache_5m",
     "writes","reads","tool_calls"].forEach(function (k) { t[k] += r[k]; });
    t.cost += r.cost;
    if (r.agent !== "main thread") { t.sub_turns += r.turns; t.sub_output += r.output; }
    days[r.date] = 1;
  });
  t.days = Object.keys(days).length;
  return t;
}

function pickSessions(F) {
  return D.sessions.filter(function (s) {
    var d = (s.start || "").slice(0, 10);
    if (d < F.from || d > F.to) return false;
    if (F.provider !== "All" && s.provider !== F.provider) return false;
    if (F.lane !== "All" && s.lane !== F.lane) return false;
    if (F.repo !== "All" && (s.repo || "unattributed") !== F.repo) return false;
    return true;
  });
}
/* ---- charts -------------------------------------------------------------
   Hand-built SVG. Labels live in their own gutters and long ones are
   truncated, so no text can overflow the plot or collide with a bar. ------- */
// Horizontal bars are HTML, not SVG: an SVG scales its text down with its
// container, and in a half-width panel a 12.5px label renders at under 8px.
// Real text stays the size it says it is, truncates with an ellipsis, and
// keeps its full value in the title.
/* Eight rows at most, so every card in a grid row is the same height. `fmt`
   gets the row as well as the value: a free model has no cost to print, and the
   honest word for it is "Free", not "$0". `keepZero` lets such a row through the
   `value > 0` filter that otherwise drops empty ones. */
function bars(rows, label, value, fmt, pickable, keepZero) {
  rows = rows.filter(function (r) {
    return (value(r) || 0) > 0 || (keepZero && keepZero(r));
  }).slice(0, 8);
  if (!rows.length) return '<p class="empty">' + esc(t18("e_none", "Nothing in this range.")) + "</p>";
  var peak = Math.max.apply(null, rows.map(value)) || 1;
  return '<div class="hbars">' + rows.map(function (r) {
    var v = value(r) || 0, full = String(label(r));
    return '<div class="hbar' + (pickable ? " hit" : "") + '" data-pick="' + esc(full)
      + '" data-tt="' + esc(full + " — " + fmt(v, r)) + '">'
      + '<span class="hl">' + esc(full) + "</span>"
      + '<span class="ht"><i style="width:' + Math.max(1.5, 100 * v / peak).toFixed(1)
      + '%"></i></span>'
      + '<span class="hv">' + esc(fmt(v, r)) + "</span></div>";
  }).join("") + "</div>";
}

function daily(days, byDate, metric, fmt, picked) {
  if (!days.length) return '<p class="empty">' + esc(t18("e_none", "Nothing in this range.")) + "</p>";
  /* The canvas is measured, not fixed, so the viewBox and the rendered box
     agree 1:1 and nothing on the chart is scaled.

     A 720-wide viewBox stretched to fill a 1175px panel is a 1.63x scale, and
     an SVG scales everything — so the axis labels came out at 18px on a page
     whose body text is 15px, and the gridline hairlines at 1.6px. Measuring the
     container instead means more days fit in the same space at the type size
     the design actually chose.

     560 is the floor: below it the card scrolls horizontally, which is what
     `#daily{overflow-x:auto}` and the svg's min-width have always done.

     The geometry is the Hangar port's TrendChart, number for number: 220 tall,
     46px of axis on the left, bars no wider than 18px, five gridlines. */
  var host = $("daily");
  var avail = host ? host.clientWidth : 0;
  var W = Math.max(560, Math.round(avail) || 960);
  var L = 46, R = 12, TOP = 16, H = 220, PH = H - TOP - 26;
  var base = TOP + PH, plotW = W - L - R, step = plotW / days.length;
  var bw = Math.max(1, Math.min(18, step - 1.5));
  var vals = days.map(function (d) { return (byDate[d] || 0); });
  var peak = Math.max.apply(null, vals) || 1;
  var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" '
    + 'width="' + W + '" height="' + H + '" preserveAspectRatio="xMinYMin meet">';

  if (picked) {
    var pi = days.indexOf(picked);
    if (pi >= 0) {
      s += '<rect x="' + (L + pi * step).toFixed(1) + '" y="' + TOP + '" width="'
        + step.toFixed(1) + '" height="' + PH + '" fill="var(--sel)"/>';
    }
  }

  /* Five gridlines is enough to read a value off; more is ink without data. A
     small integer maximum collapses quarter steps onto the same label once
     formatted — a count axis topping out at 1 would read "0 0 1 1 1", which
     looks like a rendering fault — so a gridline whose label repeats the one
     below it is dropped. */
  var seen = null;
  [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
    var label = fmt(peak * f);
    if (label === seen) return;
    seen = label;
    var gy = TOP + PH * (1 - f);
    s += '<line class="gridline" x1="' + L + '" y1="' + gy.toFixed(1) + '" x2="' + (W - R)
      + '" y2="' + gy.toFixed(1) + '"/>'
      + '<text x="' + (L - 8) + '" y="' + (gy + 4).toFixed(1) + '" text-anchor="end" '
      + 'class="axis">' + esc(label) + "</text>";
  });

  // Bars, each a click target (drill into that day) carrying its own tooltip.
  var every = Math.max(1, Math.ceil(days.length / 8));
  days.forEach(function (d, i) {
    var v = vals[i], h = PH * (v / peak), isPicked = d === picked;
    var x = L + i * step + (step - bw) / 2;
    s += '<g class="daycol" data-day="' + d + '" data-tt="'
      + esc(longDate(d) + " — " + fmt(v) + " " + metric) + '">'
      + '<rect class="daybar' + (isPicked ? " picked" : "") + '" x="' + x.toFixed(1)
      + '" y="' + (base - h).toFixed(1) + '" width="' + bw.toFixed(1)
      + '" height="' + Math.max(h, v ? 1.2 : 0).toFixed(1) + '"/>'
      + '<rect x="' + (L + i * step).toFixed(1) + '" y="' + TOP + '" width="'
      + step.toFixed(1) + '" height="' + PH + '" fill="transparent"/></g>';
    if (i % every === 0) {
      var p = dayInfo(d);
      s += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (H - 8)
        + '" text-anchor="middle" class="axis">' + esc(String(+p.dom) + " " + p.mon) + "</text>";
    }
  });
  s += rollingMean(vals, L, step, base, PH, peak);
  return s + "</svg>";
}

/* Seven-day trailing mean — the trend under the weekday sawtooth. Early days
   average over the days there are, so the line starts with the first bar rather
   than a week in, which is how the Hangar port draws it. */
function rollingMean(vals, L, step, base, PH, peak) {
  if (vals.length < 2) return "";
  var pts = [], sum = 0;
  for (var i = 0; i < vals.length; i++) {
    sum += vals[i];
    if (i >= 7) sum -= vals[i - 7];
    var y = base - PH * ((sum / Math.min(i + 1, 7)) / peak);
    pts.push((L + i * step + step / 2).toFixed(1) + "," + y.toFixed(1));
  }
  // The accent lives on the mean, not on the bars. Ninety bars drawn in the
  // accent are ninety equally loud marks; the trend under them is the only
  // thing on this chart that answers "is this going up?". One protagonist per
  // chart.
  return '<polyline points="' + pts.join(" ") + '" fill="none" stroke="var(--accent-data)" '
    + 'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
}

/* ---- the meter: your hours against your vendors' clocks -------------------
   The single most actionable view on this page, and the one the rest of the
   product argues for. The working-hours heatmap already showed *when* you
   work. On its own that is trivia. Drawn against the hours your vendors
   actually charge more for, the same grid answers "which of my habits is
   costing me money" — and, because the off-peak columns are right there,
   "where would I move it to".

   Deliberately 2D. A third axis here would encode nothing the colour ramp does
   not already carry, and would make neighbouring cells occlude each other —
   the comparison this chart exists to support. */
function peakHoursSet(F) {
  /* A 7x24 mask of which of YOUR local hours are peak-priced, built only from
     the vendors present in the current filter.

     Two things this must get right, and an earlier version got neither:

     1. **Only vendors you use.** Most people never touch a time-priced model.
        Drawing DeepSeek's window over their week would invent a problem they
        cannot have — and the honest answer, "no hour you worked cost more than
        another", is itself useful.
     2. **Weekdays are part of the window.** GLM peaks 14:00-18:00 UTC+8 on
        weekdays *only*; weekends are entirely off-peak. Treating the window as
        a plain set of hours ringed Saturday and Sunday cells that were never
        charged a premium — the exact false positive this product cannot
        afford. Hence a mask over (weekday, hour), not over hour alone. */
  var wins = D.windows || {}, tz = Number(CUR.tz_offset_hours || 0);
  var used = {};
  agg(D.cube, CUBE, F, ["provider"]).forEach(function (r) { used[r.provider] = true; });

  var mask = [], vendors = [];
  for (var i = 0; i < 7; i++) mask.push(new Array(24).fill(null));

  Object.keys(wins).forEach(function (name) {
    var w = wins[name];
    // The engine resolved which providers bill on this window. Matching on the
    // vendor name here would silently drop GLM, whose events carry provider
    // "glm" against a window keyed to vendor "zhipu".
    var mine = (w.providers || []).filter(function (p) { return used[p]; });
    if (!mine.length) return;
    mine.forEach(function (p) { if (vendors.indexOf(p) < 0) vendors.push(p); });

    // `days` are UTC weekdays; absent means every day.
    var days = w.days && w.days.length ? w.days : [0, 1, 2, 3, 4, 5, 6];
    (w.peak_utc || []).forEach(function (pair) {
      for (var h = pair[0]; h < pair[1]; h++) {
        days.forEach(function (d) {
          // A timezone shift moves the weekday as well as the hour: 23:00 UTC
          // Monday is 07:00 Tuesday at UTC+8. Floor, because the hour a turn
          // is bucketed into is the one that decides its price.
          var shifted = Math.floor(h + tz);
          var lh = ((shifted % 24) + 24) % 24;
          var ld = ((d + Math.floor(shifted / 24)) % 7 + 7) % 7;
          mask[ld][lh] = (mask[ld][lh] || []);
          mine.forEach(function (p) {
            if (mask[ld][lh].indexOf(p) < 0) mask[ld][lh].push(p);
          });
        });
      }
    });
  });
  return {mask: mask, vendors: vendors};
}

function meter(F) {
  var pk = peakHoursSet(F);
  var hasPeak = pk.vendors.length > 0;
  var grid = [], total = 0;
  for (var w = 0; w < 7; w++) grid.push(new Array(24).fill(0));
  agg(D.hours, HOURS, F, ["date", "hour"]).forEach(function (r) {
    var h = parseInt(r.hour, 10);
    if (isNaN(h) || h < 0 || h > 23) return;
    grid[parse(r.date).getUTCDay()][h] += r.turns;
    total += r.turns;
  });
  if (!total) {
    return {svg: '<p class="empty">' + esc(t18("e_none", "Nothing in this range.")) + "</p>", note: "",
            hasPeak: false};
  }

  var peak = 1, inPeak = 0;
  for (var a = 0; a < 7; a++) for (var b = 0; b < 24; b++) {
    if (grid[a][b] > peak) peak = grid[a][b];
    if (pk.mask[a][b]) inPeak += grid[a][b];
  }

  /* Measured, not stretched — the same rule as the daily chart (see the
     "Charts are measured, never scaled" note in DESIGN-SYSTEM.md) and the
     one chart this pass missed the first time round.

     A fixed 760-wide viewBox rendered at `width:100%` inside a panel that
     is actually ~1175px wide is a 1.5x scale, and an SVG scales EVERYTHING —
     the 20px cells this function asks for came out around 30px on screen,
     which is what made a seven-row weekday grid tall enough to fill most of
     a laptop screen. Measuring the container and using that as the viewBox
     width renders at 1:1, so the cell height below is the height a cell
     actually gets.

     CH/GAP themselves are also turned down here to match the density of the
     Wingman port's HeatmapStrip (16px cell, 3px gap) — the two products drew
     the same chart, and the more legible default is the smaller one: two
     numbers on a 24-hour, 7-day grid can afford to be modest, and a grid this
     dense reads as a texture at a glance rather than as 168 things to look at
     one by one. */
  var host = $("meter");
  var avail = host ? host.clientWidth : 0;
  var W = Math.max(480, Math.round(avail) || 760), L = 36;
  var TOP = hasPeak ? 30 : 18, CH = 16, GAP = 2;
  var cw = (W - L - 2) / 24;
  var H = TOP + 7 * (CH + GAP) + 22;
  var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" '
    + 'width="' + W + '" height="' + H + '" '
    + 'preserveAspectRatio="xMinYMin meet" aria-label="'
    + (hasPeak ? "Turns by weekday and hour, with peak-priced hours marked"
               : "Turns by weekday and hour") + '">';

  if (hasPeak) {
    // Tinted per cell rather than as a full-height column: GLM's window is
    // weekdays only, so a column band would wash Saturday and Sunday in a
    // premium they were never charged. Adjacent tints touch, so where a window
    // does run all week it still reads as one band.
    for (var r0 = 0; r0 < 7; r0++) {
      for (var h0 = 0; h0 < 24; h0++) {
        if (!pk.mask[WEEK[r0]][h0]) continue;
        s += '<rect x="' + (L + h0 * cw - 1).toFixed(1) + '" y="'
          + (TOP + r0 * (CH + GAP) - 1) + '" width="' + (cw + 0).toFixed(1)
          + '" height="' + (CH + 2) + '" fill="var(--high)" opacity="0.10"/>';
      }
    }
    s += '<text x="' + L + '" y="' + (TOP - 12) + '" class="axis" '
      + 'fill="var(--high)">' + esc(t18("m_peak", "PEAK — full rate") + " · "
      + pk.vendors.join(", ")) + "</text>";
  }

  for (var r2 = 0; r2 < 7; r2++) {
    var w2 = WEEK[r2], y = TOP + r2 * (CH + GAP);
    s += '<text x="' + (L - 8) + '" y="' + (y + CH / 2 + 3.5).toFixed(1)
      + '" text-anchor="end" class="axis">' + dow(w2) + "</text>";
    for (var h2 = 0; h2 < 24; h2++) {
      var v = grid[w2][h2], x = L + h2 * cw, hot = pk.mask[w2][h2];
      var tip = dow(w2) + " " + String(h2).padStart(2, "0") + ":00 " + CUR.tz_label
        + " — " + num(v) + " turns";
      // No phase suffix at all when nothing you use is time-priced: labelling
      // every cell "off-peak" implies a peak somewhere that does not exist.
      if (hasPeak) {
        tip += hot
          ? " · " + t18("m_at_peak", "at peak rate") + " (" + hot.join(", ") + ")"
          : " · " + t18("m_off", "off-peak");
      }
      // A single hue, darker for more: ordered data gets ordered colour. Empty
      // cells stay a visible neutral square so the grid's shape always reads,
      // even on a quiet week.
      s += '<rect class="heatcell' + (v ? "" : " empty0") + '" data-tt="' + esc(tip)
        + '" x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="'
        + Math.max(1, cw - 2).toFixed(1) + '" height="' + CH + '" rx="1"'
        + (v ? ' opacity="' + Math.max(0.15, v / peak).toFixed(2) + '"' : "") + "/>";
      // The ring, not a second fill: volume stays encoded by opacity alone, so
      // "busy" and "expensive" never compete for the same visual channel.
      if (hot && v) {
        s += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="'
          + Math.max(1, cw - 2).toFixed(1) + '" height="' + CH
          + '" rx="1" fill="none" stroke="var(--high)" stroke-width="1.6" '
          + 'pointer-events="none"/>';
      }
    }
  }
  // 00 06 12 18 23, as on the Hangar port: enough to read an hour off, and the
  // last cell is named rather than left to be counted.
  var by = TOP + 7 * (CH + GAP) + 12;
  [0, 6, 12, 18, 23].forEach(function (h3) {
    s += '<text x="' + (L + h3 * cw + (cw - 2) / 2).toFixed(1) + '" y="' + by.toFixed(1)
      + '" text-anchor="middle" class="axis">' + String(h3).padStart(2, "0") + "</text>";
  });
  s += "</svg>";

  if (!hasPeak) {
    // Worth saying out loud rather than leaving a plain grid to be read as a
    // missing feature.
    return {svg: s, hasPeak: false,
            note: t18("m_none", "None of the vendors you used price by the hour, "
                      + "so no hour here cost more than another.")};
  }

  var pct = pctOf(inPeak, total);
  var byHour = new Array(24).fill(0), offHour = new Array(24).fill(0);
  for (var c = 0; c < 7; c++) for (var d = 0; d < 24; d++) {
    byHour[d] += grid[c][d];
    if (!pk.mask[c][d]) offHour[d] += grid[c][d];
  }
  var best = [];
  for (var e = 0; e < 24; e++) if (offHour[e]) best.push({h: e, v: offHour[e]});
  best.sort(function (m, n) { return n.v - m.v; });
  best = best.slice(0, 3).sort(function (m, n) { return m.h - n.h; })
    .map(function (o) { return String(o.h).padStart(2, "0") + ":00"; });

  var note = t18("m_share", "%P% of your turns on time-priced vendors land in a peak window.")
    .replace("%P%", pct.toFixed(0) + "%");
  if (best.length) {
    note += " " + t18("m_move", "You already work at %H% — those hours are off-peak.")
      .replace("%H%", best.join(", "));
  }
  return {svg: s, note: note, hasPeak: true};
}

/* ---- the long view: one square per day ------------------------------------
   The daily chart answers "what did this month look like". It cannot answer
   "am I busier than I was in March", because a range that wide compresses each
   day below a pixel. A calendar grid can hold a year without shrinking a day
   below a readable square, which is exactly the question the bar chart drops.

   Not 3D. Extruding each day into a block is the well-known version of this
   chart, and it trades the one thing the grid is good at — comparing any two
   days at a glance — for an angle that hides the back rows behind the front
   ones. See docs/design/DESIGN-SYSTEM.md; the repo's own chart rules call
   3D on a quantitative chart chartjunk, and this is why. */
function calendar() {
  var days = {}, maxv = 0;
  D.by_day.forEach(function (r) { days[r.date] = r.turns; });
  var first = parse(FIRST), last = parse(LAST);
  // Start on the Monday on or before the first day, so every column is a full
  // week and the weekday rows line up down the whole grid — and with the
  // weekday x hour grid beside it, which also runs Monday to Sunday.
  var start = new Date(first.getTime());
  start.setUTCDate(start.getUTCDate() - (start.getUTCDay() + 6) % 7);
  var weeks = Math.ceil((last - start) / 6048e5) + 1;
  if (weeks < 1) return "";

  Object.keys(days).forEach(function (k) { if (days[k] > maxv) maxv = days[k]; });
  if (!maxv) return "";

  /* Every weekday labelled, not every other one.

     GitHub labels only Mon/Wed/Fri because its squares are 10px and seven
     labels would collide. That trade buys tidiness at the cost of the reader
     counting rows to work out whether a dark square is a Tuesday or a
     Thursday — which is the one question this chart exists to answer. We take
     the extra 3px of pitch instead and label all seven. */
  var L = 34, TOP = 18, G = 2;
  /* Measured, not intrinsic — the same rule as daily()/meter() (see
     "Charts are measured, never scaled" in DESIGN-SYSTEM.md), applied a
     third way. Those two stretch width only and pin a fixed cell height,
     because neither draws a shape that has to stay square. A calendar day
     does — GitHub's whole visual grammar depends on it — so here PITCH scales
     evenly and CELL stays derived from it, keeping every cell square while
     the grid still grows to fill whatever width it is given. A short history
     in a wide panel used to leave most of the panel blank; now the same cells
     just get bigger, capped so a two-week history does not blow up into
     oversized tiles. The floor keeps a long history legible instead of
     shrinking forever — #calendar's overflow-x still catches it past that. */
  var host = $("calendar");
  // `Math.round(avail) || 300`, not `Math.max(300, avail)` — the same
  // fallback idiom daily()/meter() already use. clientWidth is undefined in
  // the headless test DOM (dashboard_smoke.js stubs getBoundingClientRect,
  // not clientWidth), and Math.max(300, undefined) is NaN, not 300: `||`
  // catches undefined/NaN/0 alike where `Math.max` only catches values
  // actually below the floor.
  var avail = host ? host.clientWidth : 0;
  var fitPitch = ((Math.round(avail) || 300) - L - 10) / weeks;
  var PITCH = Math.max(13, Math.min(18, fitPitch));
  var CELL = PITCH - G;
  var W = Math.max(L + weeks * PITCH + 10, 300);
  var H = TOP + 7 * PITCH + 26;

  // Which month owns each week column: the month of that column's first day
  // that falls inside the collected range. Label and separator both anchor
  // here, so they can never disagree about where a month starts.
  var colMonth = [];
  for (var w = 0; w < weeks; w++) {
    colMonth[w] = null;
    for (var d = 0; d < 7; d++) {
      var day = new Date(start.getTime());
      day.setUTCDate(day.getUTCDate() + w * 7 + d);
      if (day < first || day > last) continue;
      colMonth[w] = day.getUTCMonth();
      break;
    }
  }

  var s = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' '
    + H + '" role="img" preserveAspectRatio="xMinYMin meet" '
    + 'aria-label="One square per day, darker means more turns">';

  /* Month boundaries. GitHub itself draws none — it relies on the label row
     alone — which is fine at a glance and poor when you are trying to say
     "that spike was in July". A hairline costs almost nothing and removes the
     guess, so: GitHub's label placement, plus a rule.

     It sits between week columns, which is an approximation: a month starts
     mid-week about six times in seven. The rule marks the first *column* of
     the new month, which is exactly what the label above it already claims,
     so the two agree even though neither is to-the-day precise. */
  var prev = null;
  for (var w1 = 0; w1 < weeks; w1++) {
    if (colMonth[w1] === null || colMonth[w1] === prev) continue;
    var x1 = L + w1 * PITCH - G / 2;
    if (prev !== null) {
      // Starts below the label baseline: a rule running through "Aug" is
      // worse than no rule at all.
      s += '<line x1="' + x1.toFixed(1) + '" y1="' + (TOP - 4) + '" x2="'
        + x1.toFixed(1) + '" y2="' + (TOP + 7 * PITCH - G + 2)
        + '" stroke="var(--line)" stroke-width="1"/>';
    }
    s += '<text x="' + (L + w1 * PITCH + 2) + '" y="' + (TOP - 9)
      + '" class="axis">' + mon(colMonth[w1]) + "</text>";
    prev = colMonth[w1];
  }

  for (var w2 = 0; w2 < weeks; w2++) {
    for (var d2 = 0; d2 < 7; d2++) {
      var cd = new Date(start.getTime());
      cd.setUTCDate(cd.getUTCDate() + w2 * 7 + d2);
      if (cd < first || cd > last) continue;
      var key = cd.toISOString().slice(0, 10), v = days[key] || 0;
      s += '<rect class="calcell' + (v ? "" : " empty0") + '" data-tt="'
        + esc(dow(WEEK[d2]) + " " + key + " — " + num(v) + " turns")
        + '" data-day="' + key + '" x="' + (L + w2 * PITCH)
        + '" y="' + (TOP + d2 * PITCH) + '" width="' + CELL + '" height="' + CELL
        + '" rx="1"' + (v ? ' opacity="' + Math.max(0.15, v / maxv).toFixed(2) + '"' : "")
        + "/>";
    }
  }

  // All seven, aligned to the middle of their own row.
  for (var d3 = 0; d3 < 7; d3++) {
    s += '<text x="' + (L - 7) + '" y="' + (TOP + d3 * PITCH + CELL - 2)
      + '" text-anchor="end" class="axis dow">' + dow(WEEK[d3]) + "</text>";
  }

  // Ramp legend. Without it a pale square is ambiguous between "a quiet day"
  // and "no data", which are different facts.
  var ly = TOP + 7 * PITCH + 12, lx = L;
  s += '<text x="' + lx + '" y="' + ly + '" class="axis">'
    + esc(t18("c_less", "less")) + "</text>";
  lx += 30;
  [0, 0.25, 0.5, 0.75, 1].forEach(function (v) {
    s += '<rect class="calcell' + (v ? "" : " empty0") + '" x="' + lx + '" y="'
      + (ly - CELL + 2) + '" width="' + CELL + '" height="' + CELL + '" rx="1"'
      + (v ? ' opacity="' + Math.max(0.15, v).toFixed(2) + '"' : "") + "/>";
    lx += PITCH;
  });
  s += '<text x="' + (lx + 4) + '" y="' + ly + '" class="axis">'
    + esc(t18("c_more", "more")) + "</text>";
  return s + "</svg>";
}

/* ---- behavioral trends ----------------------------------------------------
   Sessions bucketed by day, then a rolling mean over only the active days in
   each trailing window — a quiet day doesn't drag the average toward zero,
   it's just absent, the same "empty stays empty" rule the daily chart uses. */
function sessionSeries(sessions, days) {
  var byDay = {};
  sessions.forEach(function (s) {
    var d = (s.start || "").slice(0, 10);
    if (d) (byDay[d] = byDay[d] || []).push(s);
  });
  return days.map(function (d) {
    var list = byDay[d];
    if (!list || !list.length) {
      return {sessions: 0, turns_per_session: null,
              tool_calls_per_turn: null, model_switch: null};
    }
    var turns = 0, calls = 0, switched = 0;
    list.forEach(function (s) {
      turns += s.turns || 0;
      calls += s.tool_calls || 0;
      if ((s.models || []).length > 1) switched++;
    });
    return {sessions: list.length,
            turns_per_session: turns / list.length,
            tool_calls_per_turn: turns ? calls / turns : 0,
            model_switch: 100 * switched / list.length};
  });
}
function rollingAvg(vals, window) {
  return vals.map(function (_, i) {
    var sum = 0, n = 0;
    for (var j = Math.max(0, i - window + 1); j <= i; j++) {
      if (vals[j] != null) { sum += vals[j]; n++; }
    }
    return n ? sum / n : null;
  });
}
function lastNonNull(arr) {
  for (var i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return arr[i];
  return null;
}
function sparkline(vals) {
  var idx = [];
  vals.forEach(function (v, i) { if (v != null) idx.push(i); });
  if (idx.length < 2) return '<p class="empty">Not enough days yet.</p>';
  var W = 220, H = 46, PAD = 3;
  /* Anchored at zero and at least 1 tall, as on the Hangar port. Scaled to its
     own min and max, a metric that drifts between 0.84 and 0.88 fills the whole
     card and reads as a mountain range; anchored, it reads as the flat line it
     is. */
  var ys = idx.map(function (i) { return vals[i]; });
  var lo = Math.min.apply(null, ys.concat(0)), hi = Math.max.apply(null, ys.concat(1));
  var step = (W - PAD * 2) / Math.max(1, idx.length - 1);
  var pts = idx.map(function (i, k) {
    var x = PAD + k * step, y = H - PAD - (vals[i] - lo) / (hi - lo) * (H - PAD * 2);
    return x.toFixed(1) + "," + y.toFixed(1);
  });
  var last = pts[pts.length - 1].split(",");
  return '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img">'
    + '<polyline points="' + pts.join(" ") + '"/>'
    + '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="2.6"/></svg>';
}
function lastWindowBasis(vals, counts, window) {
  /* Days and sessions behind the final rolling value — the same trailing slots
     rollingAvg averaged, counting only the ones that held sessions. */
  var days = 0, sessions = 0, last = -1;
  for (var i = vals.length - 1; i >= 0; i--) if (vals[i] != null) { last = i; break; }
  if (last < 0) return null;
  for (var j = Math.max(0, last - window + 1); j <= last; j++) {
    if (vals[j] == null) continue;
    days++;
    sessions += (counts && counts[j]) || 0;
  }
  return {days: days, sessions: sessions};
}
function sparkCard(title, infoKey, vals, fmt, counts) {
  var rolled = rollingAvg(vals, 7), lastVal = lastNonNull(rolled);
  var basis = lastWindowBasis(vals, counts, 7);
  // Only worth saying when the window is thin. A full week of activity behind
  // the number needs no caveat, and a caveat on every card is noise.
  var note = "";
  if (basis && basis.days > 0 && basis.days < 4) {
    note = '<div class="sb">'
      + esc(t18("k_basis", "%D% active day(s), %S% session(s)")
              .replace("%D%", String(basis.days))
              .replace("%S%", String(basis.sessions)))
      + "</div>";
  }
  return '<div class="spark"><div class="sk">' + esc(title) + info(infoKey) + "</div>"
    + '<div class="sv">' + (lastVal == null ? "—" : esc(fmt(lastVal))) + "</div>"
    + note + sparkline(rolled) + "</div>";
}
function behavioralTrends(F) {
  var days = span(F.from, F.to), series = sessionSeries(pickSessions(F), days);
  var counts = series.map(function (r) { return r.sessions; });
  var html = sparkCard(t18("k_tps", "Turns / session"), "turnsPerSession",
      series.map(function (r) { return r.turns_per_session; }),
      function (v) { return v.toFixed(1); }, counts)
    + sparkCard(t18("k_tcpt", "Tool calls / turn"), "toolCallsPerTurn",
      series.map(function (r) { return r.tool_calls_per_turn; }),
      function (v) { return v.toFixed(2); }, counts)
    + sparkCard(t18("k_msw", "Model-switch share"), "modelSwitchShare",
      series.map(function (r) { return r.model_switch; }),
      function (v) { return v.toFixed(0) + "%"; }, counts);
  return '<div class="sparks">' + html + "</div>";
}

/* ---- panels ------------------------------------------------------------ */
/* `hi`/`hn` (cost only): the section heading reads "Spend per day...", not
   "Est. cost per day..." — Est. cost is the right word on a 9-char segmented
   button, Spend is the right word in a sentence. Every other metric's button
   label already reads fine as a sentence subject, so only cost needs the
   override. */
var DAILY = [{k: "turns", i: "d_turns", n: "Turns", f: num},
             {k: "cost", i: "d_cost", n: "Est. cost", hi: "d_cost_h", hn: "Spend", f: usd},
             {k: "output", i: "d_output", n: "Output", f: num},
             {k: "tool_calls", i: "d_tools", n: "Tool calls", f: num}];
/* The English `n` stays as the fallback and as the tooltip's metric word. */
function dailyLabel(m) { return t18(m.i, m.n); }
function dailyHeadingLabel(m) { return m.hi ? t18(m.hi, m.hn) : dailyLabel(m); }
// Spend, not turns, matches the Hangar port's own default and the KPI strip's
// own lead tile — turns/output/tool-calls stay one click away on the segmented
// control, they just are not the first thing either product shows.
var dailyMetric = "cost";
var selectedDay = null;  // click a bar in "Daily rhythm" to drill every panel into that day

function kpiCards(t, totalDays) {
  var days = Math.max(1, t.days);
  var read = t.cache_read + t.cache_create + t.input;
  var wr = t.reads ? t.writes / t.reads : (t.writes ? t.writes : null);
  var tcpt = toolCallsPerTurn(t);
  // Five numbers, not six — turns/session and model-switch share still get
  // their own trend sparklines in behavioralTrends() below, so dropping them
  // here loses no view of the data, only the redundant top-of-page tile.
  // The Hangar port's scoreboard exactly (design.md, "Metrics: behavioral over
  // volume"): spend, how much context was reused, whether you are producing or
  // exploring, whether use is agentic, and how many days it was actually used.
  // Only the two behavioral ratios carry an info mark, because they are the two
  // whose formula is not obvious from the label.
  var cards = [
    [usd(t.cost), esc(t18("k_spend", "Estimated spend")),
     tf("n_spend", "%V% on an active day", {V: usd(t.cost / days)}), true],
    [pctOf(t.cache_read, read).toFixed(0) + "%",
     esc(t18("k_cache", "Context reuse")),
     tf("n_cache", "of %V% tokens read", {V: num(read)})],
    [wr == null ? "—" : wr.toFixed(2) + "×",
     esc(t18("k_wr", "Write / read")) + info("writeRead"),
     wr == null ? t18("n_noreads", "not enough reads yet")
       : wr >= 1 ? t18("n_producing", "mostly producing")
                 : t18("n_exploring", "mostly exploring")],
    [tcpt.toFixed(2), esc(t18("k_tcpt", "Tool calls / turn")) + info("toolCallsPerTurn"),
     tcpt >= 0.5 ? t18("n_agentic", "agentic use")
                 : t18("n_conversational", "mostly conversational")],
    [num(t.days), esc(t18("k_days", "Days you used AI")),
     totalDays ? tf("n_days", "across %N% calendar days", {N: num(totalDays)})
               : t18("n_noactivity", "no activity in range")]
  ];
  return cards.map(function (c) {
    // Label, then number, then the gloss. A number is only a fact once you
    // know what it counts.
    return '<div class="kpi' + (c[3] ? " lead" : "") + '"><div class="k">' + c[1]
      + '</div><div class="v">' + c[0] + '</div><div class="n">' + esc(c[2]) + "</div></div>";
  }).join("");
}

function sessionsTable(rows) {
  // Eight, not fifteen. This is the tallest panel on the page and the tail of
  // it earns nothing: rows nine to fifteen are neither the heaviest sessions
  // nor a representative sample, they are just the next seven. Eight is what
  // the subagent panel above already shows, so the two read as a pair.
  rows = rows.slice().sort(function (a, b) { return b.output - a.output; }).slice(0, 8);
  if (!rows.length) {
    return '<p class="empty">' + esc(t18("w_none", "No sessions in this range.")) + "</p>";
  }
  var peak = Math.max.apply(null, rows.map(function (r) { return r.peak_context || 0; })) || 1;
  var body = rows.map(function (r) {
    var ratio = (r.writes || r.reads) ? r.writes + "/" + r.reads : "—";
    var tag = r.surface ? ' <span class="tag">' + esc(r.surface) + "</span>" : "";
    return "<tr><td>" + esc(r.repo || "unattributed") + tag + '<br><span class="sid">'
      + esc(r.session) + " · " + esc((r.start || "").slice(0, 10)) + " · "
      + esc(r.provider) + "</span></td>"
      + '<td class="n">' + esc(num(r.turns)) + "</td>"
      + '<td class="n">' + esc(num(r.output)) + "</td>"
      + '<td class="n">' + esc(usd(r.cost)) + "</td>"
      + '<td class="n">' + esc(ratio) + "</td>"
      + '<td><div class="bar"><i style="width:' + pctOf(r.peak_context, peak).toFixed(0)
      + '%"></i></div><span class="sid">' + esc(num(r.peak_context)) + "</span></td></tr>";
  }).join("");
  var head = [t18("w_session", "Session"), t18("d_turns", "Turns"),
              t18("d_output", "Output"), t18("d_cost", "Est. cost"),
              t18("w_wr", "Writes/reads"), t18("w_peakctx", "Peak context")];
  return '<div class="scroll"><table><thead><tr>'
    + head.map(function (h) { return "<th>" + esc(h) + "</th>"; }).join("")
    + "</tr></thead><tbody>" + body + "</tbody></table></div>";
}

/* ---- peak / off-peak -----------------------------------------------------
   Hidden entirely when nothing in range is time-priced. An empty panel reading
   "0%" would imply the user had scheduled well, when the truth is that the
   question does not apply to their vendors at all. */
function drawPhase(F) {
  var rows = agg(D.cube, CUBE, F, ["phase"]);
  var timed = rows.filter(function (r) { return r.phase === "peak" || r.phase === "off-peak"; });
  var total = timed.reduce(function (a, r) { return a + r.cost; }, 0);
  var sect = $("phaseSection");
  if (!timed.length || total <= 0) { sect.hidden = true; return; }
  sect.hidden = false;

  var peakRow = timed.filter(function (r) { return r.phase === "peak"; })[0];
  var peakCost = peakRow ? peakRow.cost : 0;
  // cost_floor_micro is the same tokens at the vendor's off-peak rate, carried
  // in the cube so the page never has to know a rate card.
  var floor = timed.reduce(function (a, r) { return a + (r.cost_floor_micro || 0) / 1e6; }, 0);
  var premium = Math.max(0, total - floor);

  var label = {peak: t18("ph_peak", "Peak hours"),
               "off-peak": t18("ph_off", "Off-peak hours")};
  $("phase").innerHTML = bars(
    timed.sort(byCost),
    function (r) { return label[r.phase] || r.phase; },
    function (r) { return r.cost; }, usd);

  var pct = pctOf(peakCost, total);
  // The emphasis sits inside the translated string: which clause carries the
  // weight is a property of the sentence, not of the layout. Only the numbers
  // are interpolated, and they are escaped on the way in.
  $("phaseNote").innerHTML = tf("ph_note",
      "<strong>%P%</strong> of time-priced spend landed in a peak window. Running "
      + "the identical turns off-peak would have cost %F% instead of %T% — a premium "
      + "of <strong>%X%</strong> for the timing.",
      {P: pct.toFixed(1) + "%", F: esc(usd(floor)), T: esc(usd(total)),
       X: esc(usd(premium))})
    + (premium > 0 ? " " + esc(t18("ph_batch",
        "Batch work — test generation, migrations, doc sweeps — is the part that "
        + "does not need you watching, and so the part worth moving.")) : "");
}

function byCost(a, b) { return b.cost - a.cost; }
function byOutput(a, b) { return b.output - a.output; }
/* ---- draw --------------------------------------------------------------- */
function state() {
  return {from: $("from").value, to: $("to").value, provider: $("provider").value,
          lane: $("lane").value, repo: $("repo").value, day: selectedDay};
}

// Everything except the daily-rhythm chart itself drills into just the picked
// day when one is selected — same from/to machinery, just narrowed to one day.
function dayFilter(F) {
  return F.day ? {from: F.day, to: F.day, provider: F.provider, lane: F.lane, repo: F.repo}
               : F;
}

var drawn = false;
/* The daily chart sizes itself to the box it was given, so a window that
   changes width has to redraw or the canvas keeps the old one's measurements.
   Debounced because a drag fires this continuously and `draw()` rebuilds every
   panel on the page; 150ms is below the point a redraw reads as lag and well
   above the frame rate of a resize drag. */
var resizeTimer = null, lastWidth = 0;
function onResize() {
  var w = window.innerWidth;
  if (w === lastWidth) return;         // height-only changes move nothing
  lastWidth = w;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(function () {
    if (!drawn) return;
    draw();
    // Not part of draw(): the calendar shows the whole synced window
    // regardless of the filters draw() applies, so it has always been
    // rendered on its own (see the cold-load and language-switch call sites).
    // Now that its cell size is measured from #calendar's width too, a
    // resize has to repaint it the same way it repaints daily()/meter().
    $("calendar").innerHTML = calendar();
    if (pxVisible) drawPrices();
  }, 150);
}
window.addEventListener("resize", onResize);

function draw() {
  drawn = true;
  lastWidth = window.innerWidth;
  var F = state();
  /* A date input can be emptied — backspace in the field, or the clear control
     the browser draws — and an empty string walks straight into `parse("")`,
     whose Invalid Date throws out of `iso()` and takes every later handler on
     the page with it. The dashboard stayed dead until a reload. Anything that
     is not a real day falls back to the edge of what was collected, which is
     also the answer somebody clearing the field probably wanted. */
  if (!validDay(F.from)) { F.from = FIRST; $("from").value = FIRST; }
  if (!validDay(F.to)) { F.to = LAST; $("to").value = LAST; }
  if (F.from > F.to) { F.from = F.to; $("from").value = F.to; }
  if (F.day && (F.day < F.from || F.day > F.to)) { F.day = selectedDay = null; }
  var DF = dayFilter(F);
  var t = totals(DF), ses = pickSessions(DF), spec = DAILY.filter(function (m) {
    return m.k === dailyMetric;
  })[0];

  $("kpis").innerHTML = kpiCards(t, span(F.from, F.to).length);
  $("filtersBtn").classList.toggle("active", F.provider !== "All" || F.lane !== "All"
    || F.repo !== "All" || !!F.day || presetId === null);
  // "All" is the filter's sentinel value, never shown; the words beside it are
  // copy and translate. A provider or repo name is data and stays as written.
  var slice = [F.provider === "All" ? t18("f_scope_providers", "all providers") : F.provider,
               F.lane === "All" ? t18("f_scope_lanes", "all lanes")
                                : tf("f_scope_lane", "%L% lane", {L: F.lane}),
               F.repo === "All" ? t18("f_scope_repos", "all repositories") : F.repo]
              .join(" · ");
  $("scope").textContent = F.from + " → " + F.to + "  ·  " + slice + "  ·  "
    + tf("s_turns_est", "%N% turns, %C% estimated", {N: num(t.turns), C: usd(t.cost)})
    + (F.day ? "  ·  " + tf("s_drilled", "drilled into %D% (click it again to clear)",
                            {D: longDate(F.day)}) : "");

  if ($("dailyTitle")) {
    $("dailyTitle").textContent = tf("s_daily_metric",
      "%M% per day, with the trend underneath the noise", {M: dailyHeadingLabel(spec)});
  }
  var byDate = {};
  agg(D.cube, CUBE, F, ["date"]).forEach(function (r) { byDate[r.date] = r[dailyMetric]; });
  $("daily").innerHTML = daily(span(F.from, F.to), byDate,
                              dailyLabel(spec).toLowerCase(), spec.f, F.day);
  $("dailyLegend").innerHTML = '<i></i>'
    + esc(tf("d_per_day", "per day", {M: dailyLabel(spec)}))
    + "<i class='avg'></i>" + esc(t18("d_mean7", "7-day average"));

  var repos = agg(D.cube, CUBE, DF, ["repo"], "repo").sort(byCost);
  $("repos").innerHTML = bars(repos, function (r) { return r.repo; },
                              function (r) { return r.cost; }, usd, true);

  var focus = F.repo !== "All" ? F.repo : (repos[0] || {}).repo;
  var inside = agg(D.cube, CUBE, DF, ["repo", "surface"], "repo")
    .filter(function (r) { return r.repo === focus; }).sort(byCost);
  $("surfaceTitle").textContent = focus
    ? tf("s_inside", "Inside %R%", {R: focus})
    : tf("s_inside", "Inside %R%", {R: ""}).trim();
  $("surfaces").innerHTML = bars(inside, function (r) { return r.surface; },
                                 function (r) { return r.cost; }, usd);
  $("surfaceNote").textContent = F.repo === "All" && focus
    ? t18("n_surface", "Showing the busiest repository. Click a repository to hold it.")
    : "";

  /* Ranked by what each model cost, not by what it wrote: the card answers
     "which models did the work", and the work is paid for in dollars. A model
     that is free has no cost to rank by, so it sits last and says "Free". */
  $("models-chart").innerHTML = bars(agg(D.cube, CUBE, DF, ["model"]).sort(byCost),
    function (r) { return r.model; }, function (r) { return r.cost; },
    function (v, r) { return isFree(r.model) ? t18("l_free", "Free") : usd(v); },
    false, function (r) { return isFree(r.model); });
  var switched = ses.filter(function (x) { return (x.models || []).length > 1; }).length;
  $("modelCallout").innerHTML = ses.length
    ? tf("n_switch", "Switched models in <strong>%P%</strong> of sessions",
         {P: Math.round(pctOf(switched, ses.length)) + "%"}) + info("modelSwitchShare")
    : "";
  $("providers").innerHTML = bars(agg(D.cube, CUBE, DF, ["provider"]).sort(byCost),
    function (r) { return r.provider; }, function (r) { return r.cost; }, usd);
  $("efforts").innerHTML = bars(agg(D.cube, CUBE, DF, ["effort"])
    .sort(function (a, b) { return b.turns - a.turns; }),
    function (r) { return r.effort; }, function (r) { return r.turns; },
    function (v) { return tf("c_turns", "%V% turns", {V: count(v)}); });
  var mt = meter(DF);
  $("meter").innerHTML = mt.svg;
  $("meterNote").textContent = mt.note;
  // The panel is two panels depending on the reader's vendors: a priced meter,
  // or a plain picture of when they work. Promising "peak windows drawn over
  // them" to someone who uses none is worse than saying nothing.
  $("meterTitle").innerHTML = esc(mt.hasPeak
      ? t18("s_meter", "Your week against the meter")
      : t18("s_hours", "When you work"))
    + ' <span class="tz">' + esc(CUR.tz_label) + "</span>" + info("heatmap");
  $("meterHint").textContent = mt.hasPeak
    ? t18("n_meter", "Your own hours, with every vendor's peak window drawn over them.")
    : "";
  $("tools").innerHTML = bars(agg(D.tools, TOOLS, DF, ["tool"])
    .sort(function (a, b) { return b.calls - a.calls; }),
    function (r) { return r.tool; }, function (r) { return r.calls; }, count);
  $("toolCallout").innerHTML = t.reads
    ? tf("n_wr_call", "<strong>%V%</strong>× write / read", {V: (t.writes / t.reads).toFixed(2)})
      + info("writeRead")
    : "";
  drawPhase(DF);
  $("agents").innerHTML = bars(agg(D.cube, CUBE, DF, ["agent"]).filter(function (r) {
    return r.agent !== "main thread" && r.agent !== "unattributed";
  }).sort(byOutput), function (r) { return r.agent; },
    function (r) { return r.output; }, num);
  $("agentsNote").textContent = t.sub_turns
    ? tf("n_agents", "%P% of output came from %N% delegated turns.",
         {P: pctOf(t.sub_output, t.output).toFixed(1) + "%", N: num(t.sub_turns)})
    : t18("n_agents_none", "No delegated turns in this scope.");
  $("sessions").innerHTML = sessionsTable(ses);

  // Trends always span the full selected range, ignoring the day drill-down
  // above it — a single day has no week-over-week shape to show.
  $("trends-charts").innerHTML = behavioralTrends(F);
}

/* ---- controls ----------------------------------------------------------- */
var FIRST = (D.window.first || "").slice(0, 10), LAST = (D.window.last || "").slice(0, 10);
function later(a, b) { return a > b ? a : b; }

/* The Hangar port's four. "This month" used to sit between 30 and 90 days; it
   is still one step away — the From/To dates under Filters take any range —
   but a fifth chip made this row a different control from the one it is
   copied from. */
var PRESETS = [
  {id: "7d",  i: "p_7d",  label: "7 days",  from: function () { return later(shift(LAST, -6), FIRST); }},
  {id: "30d", i: "p_30d", label: "30 days", from: function () { return later(shift(LAST, -29), FIRST); }},
  {id: "90d", i: "p_90d", label: "90 days", from: function () { return later(shift(LAST, -89), FIRST); }},
  {id: "all", i: "p_all", label: "All",     from: function () { return FIRST; }}
];
var presetId = null;   // which chip is lit; null once the range is custom

/* The preset row and the range line under the title are written once at start,
   outside draw(), so a language switch would leave them in the old language.
   Both are re-stamped from here instead — labels only, never the values. */
function relabelChrome() {
  PRESETS.forEach(function (p) {
    var b = $("p-" + p.id);
    if (b) b.textContent = t18(p.i, p.label);
  });
  var metrics = $("dailyMetric");
  if (metrics) {
    Array.prototype.forEach.call(metrics.querySelectorAll("button[data-metric]"),
      function (b) {
        var m = DAILY.filter(function (x) {
          return x.k === b.getAttribute("data-metric");
        })[0];
        if (m) b.textContent = dailyLabel(m);
      });
  }
  /* The line under the title is the Hangar port's: how fresh, how current the
     rate card, and the one caveat that applies to every dollar on the page.
     What this line used to say — the span collected, the active days, the
     vendors — moves to the foot of the page, where it is a fact about the data
     rather than the first thing a reader has to get past. */
  var el = $("span");
  if (el) {
    el.textContent = tf("h_stamp",
      "Updated %S% · list prices verified %V% · dollar figures are estimates, not an invoice",
      {S: sinceLabel(D.generated_at), V: D.pricing_verified_on || "—"});
  }
  var cov = $("coverage");
  if (cov && D.window) {
    cov.textContent = FIRST + " → " + LAST + " · " + D.window.days + " "
      + t18("h_active_days", "active days") + " · "
      + D.by_provider.map(function (p) { return p.provider; }).join(" + ");
  }
}

/* "3 hours ago" — relative time is the honest read for a freshness stamp. The
   day-and-longer words are the ones the freshness strip already translates. */
function sinceLabel(stamp) {
  var then = Date.parse(stamp || "");
  var mins = isFinite(then) ? Math.max(0, Math.round((Date.now() - then) / 6e4)) : 0;
  if (mins < 2) return t18("ago_now", "just now");
  if (mins < 60) return tf("ago_min", "%N% minutes ago", {N: mins});
  var hrs = Math.round(mins / 60);
  if (hrs < 24) {
    return hrs === 1 ? t18("ago_hour", "an hour ago")
                     : tf("ago_hours", "%N% hours ago", {N: hrs});
  }
  var days = Math.round(hrs / 24);
  if (days < 2) return t18("fresh_yesterday", "yesterday");
  return days < 14 ? t18("fresh_days", "{n} days ago").replace("{n}", days)
                   : t18("fresh_weeks", "{n} weeks ago").replace("{n}", Math.round(days / 7));
}

function markPreset(id) {
  presetId = id;
  PRESETS.forEach(function (p) {
    $("p-" + p.id).setAttribute("aria-pressed", String(p.id === id));
  });
}
function applyPreset(p) {
  $("to").value = LAST; $("from").value = p.from(); markPreset(p.id); draw();
}
function ancestor(node, sel) {
  while (node && node !== document) {
    if (node.matches && node.matches(sel)) return node;
    node = node.parentNode;
  }
  return null;
}
function fillSelect(el, rows, key, allLabel) {
  el.innerHTML = '<option value="All">' + esc(allLabel) + "</option>"
    + rows.map(function (r) {
        return '<option value="' + esc(r[key]) + '">' + esc(r[key]) + "</option>";
      }).join("");
}

/* Re-run on a language change too: the "All providers" text inside each option
   is copy, not data, so it has to be rebuilt rather than translated in place. */
function fillSelects() {
  var t = (typeof I18N !== "undefined")
    ? I18N.dict(document.documentElement.getAttribute("data-lang") || "en")
    : {f_all_provider: "All providers", f_all_lane: "All lanes", f_all_repo: "All repos"};
  var keep = {provider: $("provider").value, lane: $("lane").value, repo: $("repo").value};
  fillSelect($("provider"), D.by_provider, "provider", t.f_all_provider);
  fillSelect($("lane"), D.by_lane, "lane", t.f_all_lane);
  fillSelect($("repo"), D.by_repo, "repo", t.f_all_repo);
  Object.keys(keep).forEach(function (k) { if (keep[k]) $(k).value = keep[k]; });
}

/* ---- rail: scroll spy ---------------------------------------------------
   Lights the tile for whatever section owns the top third of the viewport.
   IntersectionObserver rather than a scroll listener, so it costs nothing on
   a page this tall; without it the rail is a menu that never tells you where
   you are, which is worse than no rail. */
/* Clicking a day in the calendar filters to that week, matching the drill-down
   the daily chart already teaches. A whole week rather than a day: at this
   scale the target is 11px, and a mis-click that lands on the wrong single day
   shows an empty page. */
function initCalendar() {
  var el = $("calendar");
  if (!el) return;
  el.addEventListener("click", function (e) {
    var c = ancestor(e.target, "rect[data-day]");
    if (!c) return;
    var d = parse(c.getAttribute("data-day"));
    var mon = new Date(d.getTime());
    mon.setUTCDate(mon.getUTCDate() - (mon.getUTCDay() + 6) % 7);
    var sun = new Date(mon.getTime());
    sun.setUTCDate(sun.getUTCDate() + 6);
    $("from").value = mon.toISOString().slice(0, 10);
    $("to").value = min(sun.toISOString().slice(0, 10), LAST);
    markPreset(null);
    draw();
    var t = document.getElementById("overview");
    if (t) t.scrollIntoView({behavior: "smooth", block: "start"});
  });
}
function min(a, b) { return a < b ? a : b; }

function initRail() {
  var nav = $("railnav");
  if (!nav) return;
  var links = [].slice.call(nav.querySelectorAll("a[data-sec]"));

  links.forEach(function (a) {
    a.addEventListener("click", function (e) {
      var el = document.getElementById(a.getAttribute("data-sec"));
      if (!el) return;
      e.preventDefault();
      // From the Prices page, the dashboard has to be back before there is
      // anything to scroll to.
      if (pxVisible) {
        try { history.replaceState({}, "", "#" + a.getAttribute("data-sec")); } catch (err) {}
        setView("dash");
      }
      el.scrollIntoView({behavior: "smooth", block: "start"});
      try { history.replaceState({}, "", "#" + a.getAttribute("data-sec")); } catch (err) {}
    });
  });

  function light(id) {
    links.forEach(function (a) {
      if (a.getAttribute("data-sec") === id) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
  }
  light(links[0] && links[0].getAttribute("data-sec"));
  railLight = function () { light(links[0] && links[0].getAttribute("data-sec")); };

  if (!("IntersectionObserver" in window)) return;
  var seen = {};
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) { seen[en.target.id] = en.isIntersecting; });
    for (var i = 0; i < links.length; i++) {
      var id = links[i].getAttribute("data-sec");
      if (seen[id]) { light(id); return; }
    }
  }, {rootMargin: "-12% 0px -66% 0px"});
  links.forEach(function (a) {
    var el = document.getElementById(a.getAttribute("data-sec"));
    if (el) io.observe(el);
  });
}

function init() {
  $("presets").innerHTML = PRESETS.map(function (p) {
    return '<button type="button" id="p-' + p.id + '"></button>';
  }).join("");
  relabelChrome();
  PRESETS.forEach(function (p) {
    $("p-" + p.id).addEventListener("click", function () { applyPreset(p); });
  });

  ["from", "to"].forEach(function (id) {
    $(id).min = FIRST; $(id).max = LAST;
    $(id).addEventListener("change", function () { markPreset(null); draw(); });
  });

  fillSelects();
  $("calendar").innerHTML = calendar();
  ["provider", "lane", "repo"].forEach(function (id) {
    $(id).addEventListener("change", draw);
  });

  $("dailyMetric").innerHTML = DAILY.map(function (m) {
    return '<button type="button" data-metric="' + m.k + '" aria-pressed="'
      + (m.k === dailyMetric) + '">' + esc(dailyLabel(m)) + "</button>";
  }).join("");
  $("dailyMetric").addEventListener("click", function (e) {
    var b = ancestor(e.target, "button[data-metric]");
    if (!b) return;
    dailyMetric = b.getAttribute("data-metric");
    Array.prototype.forEach.call(this.querySelectorAll("button"), function (x) {
      x.setAttribute("aria-pressed", String(x === b));
    });
    draw();
  });

  // Clicking a repository bar holds that repository across the whole page.
  $("repos").addEventListener("click", function (e) {
    var g = ancestor(e.target, "[data-pick]");
    if (!g) return;
    var v = g.getAttribute("data-pick");
    $("repo").value = $("repo").value === v ? "All" : v;
    draw();
  });

  // Clicking a day in the daily-rhythm chart drills every other panel into
  // just that day; clicking the same day again clears it.
  $("daily").addEventListener("click", function (e) {
    var g = ancestor(e.target, "[data-day]");
    if (!g) return;
    var v = g.getAttribute("data-day");
    selectedDay = selectedDay === v ? null : v;
    draw();
  });

  $("reset").addEventListener("click", function () {
    $("provider").value = $("lane").value = $("repo").value = "All";
    selectedDay = null;
    applyPreset(PRESETS[1]);
  });

  // Filters open and close from the chip beside the range — same row, same
  // style — rather than from a bar of their own.
  $("filtersBtn").addEventListener("click", function () {
    var open = this.getAttribute("aria-expanded") !== "true";
    this.setAttribute("aria-expanded", String(open));
    $("filterPanel").hidden = !open;
  });

  initTooltip();

  // A month is the default view; fall back to everything when there is less.
  applyPreset(span(FIRST, LAST).length > 30 ? PRESETS[1] : PRESETS[3]);
}

/* ---- hover tooltip ------------------------------------------------------
   One delegated listener for every chart, HTML or SVG: any element carrying
   data-tt gets an instant floating value readout that tracks the cursor. */
function initTooltip() {
  var tip = $("tt");
  if (!tip) return;

  function place(x, y) {
    var pad = 14, vw = window.innerWidth, vh = window.innerHeight;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var left = x + pad, top = y + pad;
    if (left + w > vw - 6) left = x - w - pad;
    if (top + h > vh - 6) top = y - h - pad;
    tip.style.left = Math.max(4, left) + "px";
    tip.style.top = Math.max(4, top) + "px";
  }

  document.addEventListener("mouseover", function (e) {
    var el = ancestor(e.target, "[data-tt]");
    if (!el) return;
    tip.textContent = el.getAttribute("data-tt");
    tip.classList.add("show");
    place(e.clientX, e.clientY);
  });
  document.addEventListener("mousemove", function (e) {
    if (tip.classList.contains("show")) place(e.clientX, e.clientY);
  });
  document.addEventListener("mouseout", function (e) {
    var el = ancestor(e.target, "[data-tt]");
    if (el && !ancestor(e.relatedTarget, "[data-tt]")) tip.classList.remove("show");
  });
}

/* ---- page chrome: theme, language, breadcrumb ---------------------------
   The same two controls the landing page carries, reading and writing the same
   two localStorage keys — so a choice made on either side survives the jump to
   the other. The theme is already stamped on <html> by the inline script in
   <head>; this only wires the toggle. */
function initTheme() {
  var btn = $("themeToggle");
  if (!btn) return;
  var root = document.documentElement;
  if (!root.getAttribute("data-theme")) {
    var dark = window.matchMedia &&
               window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.setAttribute("data-theme", dark ? "dark" : "light");
  }
  btn.addEventListener("click", function () {
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("observatory-theme", next); } catch (e) { /* private mode */ }
  });
}

/* Interface strings, and — since the translateFindings() pass above —
   findings too. The method notes in the footer are the one thing left in
   English by design: they are fixed editorial copy about how the numbers
   were produced, distinct from the findings themselves, which are generated
   per-digest from live numbers and translate the same way any other
   engine-composed sentence on this page does (see the meter panel). */
function initLang() {
  if (typeof I18N === "undefined") return;      // e.g. the headless smoke test
  var root = document.documentElement;
  var sheet = $("langsheet"), code = $("langcode"), menu = $("langmenu");
  var current = root.getAttribute("data-lang");
  if (!current || !I18N.has(current)) current = I18N.detect();

  if (sheet) {
    I18N.LOCALES.forEach(function (l) {
      var a = document.createElement("a");
      a.href = "#";
      a.lang = l[0];
      a.setAttribute("data-lang", l[0]);
      a.textContent = l[1];
      a.addEventListener("click", function (e) {
        e.preventDefault();
        apply(l[0]);
        try { localStorage.setItem("observatory-lang", l[0]); } catch (err) {}
        if (menu) menu.open = false;
      });
      sheet.appendChild(a);
    });
  }

  if (menu) {
    document.addEventListener("click", function (e) {
      if (menu.open && !menu.contains(e.target)) menu.open = false;
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menu.open) menu.open = false;
    });
  }

  apply(current);

  function apply(lang) {
    var t = I18N.dict(lang);
    root.setAttribute("data-lang", lang);
    root.setAttribute("lang", lang);

    each("[data-i18n]", function (el) {
      var v = t[el.getAttribute("data-i18n")];
      if (v) el.textContent = v;
    });
    each("[data-i18n-title]", function (el) {
      var v = t[el.getAttribute("data-i18n-title")];
      if (v) el.setAttribute("title", v);
    });
    each("[data-i18n-aria]", function (el) {
      var v = t[el.getAttribute("data-i18n-aria")];
      if (v) el.setAttribute("aria-label", v);
    });
    // The footer's method notes carry inline <strong>/<code> markup, so they
    // need innerHTML rather than the textContent the plain lookup above uses.
    each("[data-i18n-html]", function (el) {
      var v = t[el.getAttribute("data-i18n-html")];
      if (v) el.innerHTML = v;
    });
    // These two footer items also carry a value out of the digest itself —
    // the price-list verification date, the render timestamp — seated into
    // the translated sentence the same way a KPI note is. Re-run even for
    // English, so a locally generated dashboard shows its own figures rather
    // than whatever render.py happened to bake into the initial HTML.
    var methCost = $("methCost");
    if (methCost) {
      methCost.innerHTML = (t.meth_2 || "").split("%V%").join(
        esc(D.pricing_verified_on || "—"));
    }
    var methGen = $("methGen");
    if (methGen) {
      methGen.innerHTML = (t.meth_4 || "").split("%G%").join(
        esc((D.generated_at || "").slice(0, 16).replace("T", " ")));
    }

    translateFindings();
    if (typeof fillSelects === "function" && $("provider")) fillSelects();
    // The preset row and the range line live outside draw(); re-stamp them too,
    // or the page switches language everywhere except its own top-left corner.
    if (typeof relabelChrome === "function" && $("presets")) relabelChrome();
    // Charts write their own text — the meter's summary sentence, the
    // calendar's ramp legend — so translating the DOM is not enough; they have
    // to be drawn again. Guarded because initLang runs before the first draw
    // on a cold load, and drawing twice there is just wasted work.
    if (drawn) { draw(); $("calendar").innerHTML = calendar(); }
    if (pxVisible) drawPrices();

    if (code) {
      I18N.LOCALES.forEach(function (l) { if (l[0] === lang) code.textContent = l[2]; });
    }

    /* A reader who arrived from the Thai landing page should get back to the
       Thai landing page, not the English one. Only rewritten on the hosted
       copy, which is the only place those sibling directories exist. */
    var crumb = $("crumbHome");
    if (crumb && crumb.getAttribute("data-locale-home")) {
      I18N.LOCALES.forEach(function (l) {
        if (l[0] === lang) crumb.href = "../" + (l[3] ? l[3] + "/" : "");
      });
    }
    if (sheet) {
      each("[data-lang]", function (el) {
        if (el.getAttribute("data-lang") === lang) el.setAttribute("aria-current", "true");
        else el.removeAttribute("aria-current");
      }, sheet);
    }
  }

  function each(sel, fn, scope) {
    var list = (scope || document).querySelectorAll(sel);
    for (var i = 0; i < list.length; i++) fn(list[i]);
  }
}


/* ── Freshness ──────────────────────────────────────────────────────────────
   A file cannot ask a server whether it is current, but it does not need to:
   the renderer stamped when it ran, so the page subtracts that from the clock
   and speaks for itself. Three states, and two of them say nothing at all —
   a banner that is always on is a banner nobody reads.

   `demo` is the exception that is always shown: sample data that quietly looks
   like your own would be the single most damaging thing this page could do. */
function initFreshness() {
  var el = $("fresh"); if (!el) return;
  var meta = {};
  try { meta = JSON.parse(document.getElementById("meta").textContent) || {}; }
  catch (e) { return; }

  var cmd = meta.refresh || "python3 observatory/observe.py all";
  var stamp = Date.parse(meta.generated_at || "");
  var hours = isFinite(stamp) ? (Date.now() - stamp) / 36e5 : 0;
  var state = null;

  /* Sample data says so on the title line, not in a banner. The strip below
     exists to hand somebody a refresh command, and on a hosted demo there is no
     local dashboard to refresh — the command was decoration with a scrollbar.
     The disclosure itself is not optional, so it moves rather than goes: a chip
     beside the heading, and the link the reader actually wants. */
  if (meta.demo) {
    var flag = $("demoFlag");
    if (flag) {
      $("demoChip").textContent = t18("demo_chip", "Sample data");
      var try_ = $("demoTry");
      if (meta.setup) {
        try_.href = meta.setup;
        try_.textContent = t18("demo_try", "Try it yourself");
      } else {
        try_.hidden = true;      /* a file:// copy has no site to point at */
      }
      flag.hidden = false;
    }
    /* The ask that comes after the value, not before it. Same demo gate as the
       chip above: a locally rendered dashboard never shows it. */
    var ask = $("starAsk");
    if (ask && meta.star) {
      $("starAskText").textContent = t18("star_ask",
        "Found something here worth changing?");
      $("starAskCta").textContent = t18("star_ask_cta", "Star it on GitHub");
      $("starAskLink").href = meta.star;
      ask.hidden = false;
    }
    /* The hosted demo stops here: there is no local dashboard to refresh and
       no checkout to update, so both strips would be decoration. A dashboard
       on somebody's own machine that happens to hold sample data is a
       different thing — `setup` seeds it when it finds no transcripts yet —
       and it still needs to be told that it is stale or that a new version is
       waiting. Suppressing that left the newest installs the least informed. */
    if (meta.setup) return;
  }
  if (hours >= 168) {
    state = { cls: "stale", head: t18("fresh_old_h", "This dashboard is out of date."),
              body: fill(t18("fresh_old_b", "Last built {a}. Refresh to pull in everything since."),
                         { a: ago(hours) }) };
  } else if (hours >= 24) {
    state = { cls: "aging", head: fill(t18("fresh_age_h", "Last built {a}."), { a: ago(hours) }),
              body: t18("fresh_age_b", "New sessions since then are not in these numbers yet.") };
  }
  /* Version, after freshness and never instead of it. When the report is also
     out of date the refresh command is the more urgent thing to hand somebody,
     and running it applies the waiting update on the way through — so the two
     never need to compete for the strip. `meta.update` is already resolved by
     `updater.for_render`; nothing here decides what is current. */
  if (!state && meta.update && meta.update.state) {
    var u = meta.update;
    var shown = (u.lines || []).slice(0, 2);
    var what = shown.join(" · ");
    var more = Math.max(0, (u.count || 0) - shown.length);
    if (more) what += fill(t18("fresh_upd_more", " · and {n} more"), { n: more });
    if (u.state === "applied") {
      state = { cls: "updated",
                head: t18("fresh_upd_h", "Updated to the latest version."),
                body: what || t18("fresh_upd_b",
                                  "This dashboard was rebuilt with it.") };
    } else {
      state = { cls: "update", head: t18("fresh_new_h", "A newer version is ready."),
                body: (u.blocked === "local changes"
                       ? t18("fresh_new_blocked",
                             "It cannot apply while the project folder has uncommitted changes.")
                       : t18("fresh_new_b",
                             "It applies the next time you open this from your Dock."))
                      + (what ? " " + what : "") };
    }
  }
  if (!state) return;                       /* fresh: say nothing, show nothing */

  el.className = "fresh " + state.cls;
  $("freshHead").textContent = state.head;
  $("freshBody").textContent = state.body;
  $("freshCmd").textContent = cmd;
  el.hidden = false;

  /* The hosted demo has somewhere to send people; a file:// copy does not, so
     the link only exists when the build supplied one. */
  var more = $("freshMore");
  if (more && meta.setup) {
    more.href = meta.setup;
    more.textContent = t18("fresh_guide", "Full setup guide");
    more.hidden = false;
  }

  var btn = $("freshCopy");
  btn.textContent = t18("fresh_copy", "Copy");
  btn.addEventListener("click", function () {
    var done = function () {
      btn.textContent = t18("fresh_copied", "Copied");
      setTimeout(function () { btn.textContent = t18("fresh_copy", "Copy"); }, 2000);
    };
    /* navigator.clipboard is undefined on file:// in several browsers, so the
       execCommand path is the primary one here rather than a legacy fallback. */
    try {
      var ta = document.createElement("textarea");
      ta.value = cmd; ta.setAttribute("readonly", "");
      ta.style.cssText = "position:absolute;left:-9999px";
      document.body.appendChild(ta); ta.select();
      document.execCommand("copy"); document.body.removeChild(ta); done();
    } catch (e) {
      if (navigator.clipboard) navigator.clipboard.writeText(cmd).then(done, function () {});
    }
  });

  function ago(h) {
    if (h < 48) return t18("fresh_yesterday", "yesterday");
    var d = Math.round(h / 24);
    return d < 14 ? fill(t18("fresh_days", "{n} days ago"), { n: d })
                  : fill(t18("fresh_weeks", "{n} weeks ago"), { n: Math.round(d / 7) });
  }
  function fill(tpl, vars) {
    return String(tpl).replace(/\{(\w+)\}/g, function (_, k) {
      return vars[k] == null ? "" : vars[k];
    });
  }
}

/* ---- prices ---------------------------------------------------------------
   A page of its own, switched in by `#prices`. trends.py has already done the
   arithmetic and put it in the digest as `price_trends`: each lab's model
   lines as a handful of change points (a price is constant until it changes,
   so a line is steps, not a daily series), the events between them, and the
   rates a vendor has said will end. This only draws it, which is the point:
   the tests assert those numbers, and a second copy of the formula here would
   be a second place for them to disagree.

   Read in the order a person asks the questions:
     1. AT A GLANCE   how many model lines got cheaper, dearer or stayed put,
                      and one bar per line saying by how much. Nothing to
                      decode, no legend.
     2. ONE LINE      click a row and ONE line is drawn properly, each model
        IN FOCUS      named where it took over, with the reason it moved.
                      Seven lines on one chart cannot be labelled without
                      collisions; one can.
     3. THE REST      the all-lines chart, the table of every model and the
                      full change log, tucked away until someone wants them.

   The headline price is an EFFECTIVE price: the cost of 1M tokens of a typical
   coding session, not a list price. A model has four prices and for an agentic
   session the cache read is ~97% of the tokens, so a cache discount moves the
   real price far more than the headline does (Opus 5 -> 5.5 is -20% on list
   price and -46% for that workload). The "why" panel says which of the four
   did the work. ----------------------------------------------------------- */
var PT = D.price_trends || null;
var PX = {zoom: "lines", basis: "ref", comp: "input", scale: "abs", range: "90",
          markers: true, off: {}, sel: null, evAll: false};
var pxVisible = false;
var railLight = function () {};

function pxLoad() {
  try {
    var saved = JSON.parse(window.localStorage.getItem("obs.px") || "null");
    if (saved && typeof saved === "object") {
      var ok = {zoom: ["labs", "lines", "models"], basis: ["ref", "you", "list"],
                comp: ["input", "output", "cache_read", "cache_write"],
                scale: ["abs", "index"], range: ["90", "180", "all"]};
      Object.keys(ok).forEach(function (k) {
        if (ok[k].indexOf(saved[k]) >= 0) PX[k] = saved[k];
      });
      if (typeof saved.markers === "boolean") PX.markers = saved.markers;
    }
  } catch (e) {}
}
function pxSave() {
  try {
    window.localStorage.setItem("obs.px", JSON.stringify({zoom: PX.zoom, basis: PX.basis,
      comp: PX.comp, scale: PX.scale, range: PX.range, markers: PX.markers}));
  } catch (e) {}
}

var PX_MINUS = "−";
function pxPct(v) {
  if (v == null || !isFinite(v)) return "—";
  var r = Math.round(v * 10) / 10, a = Math.abs(r);
  return (r < 0 ? PX_MINUS : r > 0 ? "+" : "") + (a >= 10 || a === Math.round(a) ? a.toFixed(0) : a.toFixed(1)) + "%";
}
function pxMoney(v) {
  if (v == null || !isFinite(v)) return "—";
  var a = Math.abs(v);
  return "$" + (a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : a >= 1 ? v.toFixed(2)
                : a >= 0.1 ? v.toFixed(3) : v.toFixed(4));
}
/* `claude-opus-5-5` -> "Opus 5.5", `gpt-5.6-sol` -> "GPT-5.6 Sol". Display only:
   nothing here is ever the key for anything. */
function pxName(m) {
  var s = String(m || "");
  if (/^gpt-/i.test(s)) {
    return s.replace(/^gpt-/i, "GPT-").replace(/-([a-z]+)$/i, function (_, w) {
      return " " + w.charAt(0).toUpperCase() + w.slice(1);
    });
  }
  return s.replace(/^claude-/, "").replace(/-(\d)-(\d)(?=$|-)/, " $1.$2")
    .replace(/-(\d+)$/, " $1").replace(/^(\w)/, function (c) { return c.toUpperCase(); });
}
function pxDay(isoStr) {
  var p = dayInfo(isoStr);
  return String(+p.dom) + " " + p.mon + " " + isoStr.slice(0, 4);
}
/* A ceiling whose quarters are clean numbers, so four gridlines read as
   $0.25 / $0.50 / $0.75 and not as fractions of whatever the maximum was. */
function pxNice(max) {
  var e = Math.pow(10, Math.floor(Math.log(max) / Math.LN10)), f = max / e;
  var steps = [1, 1.2, 1.6, 2, 2.4, 3, 4, 5, 6, 8, 10];
  for (var i = 0; i < steps.length; i++) if (f <= steps[i] + 1e-9) return steps[i] * e;
  return 10 * e;
}
function pxAxis(v) {
  if (v === 0) return "$0";
  return "$" + (v >= 10 ? v.toFixed(0) : v >= 1 ? String(+v.toFixed(2)) : String(+v.toFixed(3)));
}
function pxDays(a, b) { return (parse(b) - parse(a)) / 864e5; }

function pxKey() {
  if (PX.basis === "list") return PX.comp;
  return PX.basis === "you" && PT.mixes.yours ? "eff_you" : "eff_ref";
}
function pxAt(line, day, key) {
  var v = null;
  for (var i = 0; i < line.points.length; i++) {
    if (line.points[i].date <= day) v = line.points[i][key]; else break;
  }
  return v;
}
function pxStart() {
  if (PX.range === "all") {
    var first = null;
    PT.lines.forEach(function (l) { if (first === null || l.points[0].date < first) first = l.points[0].date; });
    return first || PT.as_of;
  }
  return shift(PT.as_of, -parseInt(PX.range, 10));
}
/* The change over [from, to]. A line that began inside the window is measured
   from its own first price, so a launch last month still has a number. */
function pxChange(line, key, from, to) {
  var base = pxAt(line, from, key);
  if (base == null && line.points[0].date <= to) base = line.points[0][key];
  var cur = pxAt(line, to, key);
  return base && cur != null ? (cur / base - 1) * 100 : null;
}
function pxDir(pct) {
  if (pct == null) return "none";
  return pct < -1 ? "down" : pct > 1 ? "up" : "flat";
}
function pxColor(line) {
  return "var(--px-" + line.lab + "-" + line.tier + ",var(--accent-data))";
}
function pxLabName(id) {
  for (var i = 0; i < PT.labs.length; i++) if (PT.labs[i].id === id) return PT.labs[i].label;
  return id;
}
function pxLineName(l) { return pxLabName(l.lab) + " " + l.label; }
function pxLine(id) {
  for (var i = 0; i < PT.lines.length; i++) if (PT.lines[i].id === id) return PT.lines[i];
  return null;
}
function pxRangeWords() {
  return PX.range === "all" ? t18("px_r_all", "since each line began")
    : tf("px_r_days", "in the last %N% days", {N: PX.range});
}
function pxModelAt(line, day) {
  var m = line.points[0].model;
  for (var i = 0; i < line.points.length; i++) if (line.points[i].date <= day) m = line.points[i].model;
  return m;
}
function pxMixText(m) {
  return tf("px_mix", "%CR%% cache reads, %CW%% cache writes, %IN%% new input, %OUT%% output", {
    CR: (m.cache_read * 100).toFixed(m.cache_read > 0.995 ? 1 : 0),
    CW: (m.cache_write * 100).toFixed(1), IN: (m.input * 100).toFixed(1),
    OUT: (m.output * 100).toFixed(1)});
}
function pxBasisWords() {
  if (PX.basis === "list") {
    return tf("px_b_list", "Showing the list price per 1M tokens of %C%.",
      {C: t18("px_c_" + PX.comp, PX.comp)});
  }
  if (PX.basis === "you" && PT.mixes.yours) {
    return tf("px_b_you", "Priced for your own mix of tokens (%M%).", {M: pxMixText(PT.mixes.yours)});
  }
  return tf("px_b_ref", "Priced for a typical coding session (%M%).", {M: pxMixText(PT.mixes.reference)});
}

/* ---- 1. at a glance ------------------------------------------------------- */

/* How many lines moved which way, and the two biggest moves with the event
   behind each. */
function pxSummary(key, from, to) {
  var rows = [], down = 0, up = 0, flat = 0;
  PT.lines.forEach(function (l) {
    var c = pxChange(l, key, from, to);
    if (c == null) return;
    rows.push({line: l, pct: c});
    var d = pxDir(c);
    if (d === "down") down++; else if (d === "up") up++; else flat++;
  });
  var sorted = rows.slice().sort(function (a, b) { return a.pct - b.pct; });
  function because(r) {
    var hit = null;
    PT.events.some(function (e) {
      if (e.line === r.line.id && e.date > from && e.date <= to && e.delta_pct != null && e.delta_pct !== 0) {
        hit = e; return true;
      }
      return false;
    });
    return hit;
  }
  var drop = sorted.length && sorted[0].pct < -1 ? sorted[0] : null;
  var rise = sorted.length && sorted[sorted.length - 1].pct > 1 ? sorted[sorted.length - 1] : null;
  return {n: rows.length, down: down, up: up, flat: flat,
          drop: drop && {line: drop.line, pct: drop.pct, event: because(drop)},
          rise: rise && {line: rise.line, pct: rise.pct, event: because(rise)}};
}

/* The bar list: one row per model line, grouped by lab, each with how far its
   price moved over the range and what it costs now. `maxAbs` scales the bars so
   the biggest move fills its half and the rest read against it. */
function pxGlance(key, from, to) {
  var lines = PX.zoom === "labs" ? PT.lines.filter(function (l) { return l.headline; }) : PT.lines;
  var rows = lines.map(function (l) {
    var p = pxChange(l, key, from, to);
    return {line: l, pct: p, dir: pxDir(p), now: pxAt(l, to, key)};
  });
  var groups = [];
  PT.labs.forEach(function (lab) {
    var mine = rows.filter(function (r) { return r.line.lab === lab.id; });
    if (mine.length) groups.push({lab: lab, rows: mine});
  });
  var max = 0;
  rows.forEach(function (r) { if (r.pct != null && Math.abs(r.pct) > max) max = Math.abs(r.pct); });
  return {groups: groups, rows: rows, maxAbs: pxNice(Math.max(10, max))};
}
/* Zero sits in the middle: cheaper grows left, dearer grows right. */
function pxBarSpan(pct, maxAbs) {
  if (pct == null) return {left: 50, width: 0};
  var w = Math.min(50, Math.abs(pct) / maxAbs * 50);
  return {left: pct < 0 ? 50 - w : 50, width: Math.max(w, Math.abs(pct) > 1 ? 1.5 : 0)};
}
/* The line the page opens on: the biggest mover among each lab's headline lines
   (the flagships people mean), falling back to any line. A -90% on a model that
   costs a cent and a half is true and a poor first impression. */
function pxBiggest(rows) {
  function pick(list) {
    var best = null;
    list.forEach(function (r) {
      if (r.pct != null && (!best || Math.abs(r.pct) > Math.abs(best.pct))) best = r;
    });
    return best;
  }
  var best = pick(rows.filter(function (r) { return r.line.headline; })) || pick(rows);
  return best ? best.line : (rows[0] && rows[0].line);
}
/* A tiny step line for a row: its own shape over the range, scaled to itself
   (the bar already says how much; this says when). */
function pxSpark(line, key, from, to) {
  var W = 84, H = 24, PAD = 3;
  var carry = pxAt(line, from, key);
  var start = carry != null ? from : line.points[0].date;
  var pts = [{date: start, v: carry != null ? carry : line.points[0][key]}];
  line.points.forEach(function (p) {
    if (p.date > start && p.date <= to) pts.push({date: p.date, v: p[key]});
  });
  var vs = pts.map(function (p) { return p.v; });
  var lo = Math.min.apply(null, vs), hi = Math.max.apply(null, vs);
  var span = Math.max(1, pxDays(from, to));
  function X(d) { return PAD + (W - PAD * 2) * Math.max(0, pxDays(from, d)) / span; }
  function Y(v) { return hi === lo ? H / 2 : PAD + (H - PAD * 2) * (1 - (v - lo) / (hi - lo)); }
  var path = "";
  pts.forEach(function (p, i) {
    path += i ? "H" + X(p.date).toFixed(1) + "V" + Y(p.v).toFixed(1)
              : "M" + X(p.date).toFixed(1) + "," + Y(p.v).toFixed(1);
  });
  return {W: W, H: H, path: path + "H" + (W - PAD).toFixed(1), flat: hi === lo};
}

function pxKpis(sm) {
  var moves = [];
  function why(r) {
    return r.event ? " (" + pxName(r.event.model) + ", " + pxDay(r.event.date) + ")" : "";
  }
  if (sm.drop) moves.push(tf("px_h_drop", "Biggest drop: %L% %P%%W%.",
    {L: pxLineName(sm.drop.line), P: pxPct(sm.drop.pct), W: why(sm.drop)}));
  if (sm.rise) moves.push(tf("px_h_rise", "Biggest rise: %L% %P%%W%.",
    {L: pxLineName(sm.rise.line), P: pxPct(sm.rise.pct), W: why(sm.rise)}));
  function tile(cls, n, key, fb) {
    return '<div class="pxkpi ' + cls + '"><b>' + n + "</b><span>" + esc(t18(key, fb)) + "</span></div>";
  }
  return tile("down", sm.down, "px_k_down", "got cheaper") + tile("up", sm.up, "px_k_up", "got dearer")
    + tile("flat", sm.flat, "px_k_flat", "unchanged")
    + '<p class="pxkof">' + esc(tf("px_k_of", "of %N% model lines, %R%", {N: sm.n, R: pxRangeWords()})
      + (moves.length ? " · " + moves.join(" ") : "")) + "</p>";
}

function pxWatch() {
  var el = $("pxWatch");
  if (!el) return;
  if (!PT.watch.length) { el.hidden = true; el.innerHTML = ""; return; }
  el.hidden = false;
  el.innerHTML = PT.watch.map(function (w) {
    var line = pxLine(w.line);
    var when = w.days_left >= 0
      ? tf("px_w_left", "%D% days left", {D: w.days_left})
      : tf("px_w_over", "%D% days overdue", {D: -w.days_left});
    return '<p><span class="pxwtag">' + esc(t18("px_w_tag", "Watch")) + "</span> "
      + esc(tf("px_w_text",
        "%L% is on a promotional price (%M%) the vendor has not said will last. Re-check after %D% — %W%.",
        {L: pxLineName(line), M: pxName(w.model), D: pxDay(w.recheck_after), W: when}))
      + "</p>";
  }).join("");
}

function pxList(g, selId) {
  var head = '<div class="pxlhead" aria-hidden="true"><span></span><span class="pxaxis"><i>'
    + esc(t18("px_g_cheaper", "← cheaper")) + "</i><i>" + esc(t18("px_g_dearer", "dearer →"))
    + '</i></span><span></span><span class="r">' + esc(t18("px_th_now", "Now"))
    + '</span><span class="c">' + esc(t18("px_g_trend", "Trend")) + "</span></div>";
  var key = pxKey(), from = pxStart(), to = PT.as_of;
  return head + g.groups.map(function (grp) {
    return '<div class="pxlab"><i class="pxsw" style="background:var(--px-' + esc(grp.lab.id)
      + '-premium,var(--px-' + esc(grp.lab.id) + '-frontier))"></i>' + esc(grp.lab.label) + "</div>"
      + grp.rows.map(function (r) {
        var span = pxBarSpan(r.pct, g.maxAbs), sp = pxSpark(r.line, key, from, to);
        var on = r.line.id === selId;
        return '<button type="button" class="pxrow' + (on ? " sel" : "") + '" data-line="' + esc(r.line.id)
          + '" aria-pressed="' + on + '">'
          + '<span class="pxnm"><i class="pxsw" style="background:' + pxColor(r.line) + '"></i>' + esc(r.line.label)
          + " <small>" + esc(t18("px_tier_" + r.line.tier, r.line.tier)) + "</small></span>"
          + '<span class="pxbar" aria-hidden="true"><i class="pxzero"></i>'
          + (r.pct != null ? '<b class="pxfill ' + r.dir + '" style="left:' + span.left.toFixed(2)
            + "%;width:" + span.width.toFixed(2) + '%"></b>' : "") + "</span>"
          + '<span class="pxpcw"><span class="pxpc ' + r.dir + '">' + esc(pxPct(r.pct)) + "</span>"
          + (r.dir === "flat" ? "<small>" + esc(t18("px_g_nochg", "no change")) + "</small>" : "") + "</span>"
          + '<span class="pxnowv">' + esc(pxMoney(r.now)) + "</span>"
          + '<svg class="pxsp" viewBox="0 0 ' + sp.W + " " + sp.H + '" width="' + sp.W + '" height="' + sp.H
          + '" aria-hidden="true"><path d="' + sp.path + '" style="stroke:' + pxColor(r.line) + '"'
          + (sp.flat ? ' class="flatline"' : "") + "/></svg></button>";
      }).join("");
  }).join("");
}

/* ---- 2. one line in focus ------------------------------------------------- */

/* A single line, drawn properly: the one chart where every model can be named
   without anything colliding, because there is only one line to name. Each model
   is written to the RIGHT of its point, over the flat stretch that follows it
   (no step of this line passes through the text), above or below when the label
   before it is in the way, or left off (its tooltip stays) when neither fits. */
function pxLineChart(line, key, from, to, width) {
  var W = Math.max(320, Math.round(width) || 640);
  var L = 52, R = 18, TOP = 30, H = 250, PH = H - TOP - 30;
  var span = Math.max(1, pxDays(from, to));
  function X(d) { return L + (W - L - R) * Math.max(0, pxDays(from, d)) / span; }
  var carry = pxAt(line, from, key);
  var start = carry != null ? from : line.points[0].date;
  var pts = [{date: start, v: carry != null ? carry : line.points[0][key], model: pxModelAt(line, from),
              carried: carry != null}];
  line.points.forEach(function (p) {
    if (p.date > start && p.date <= to) pts.push({date: p.date, v: p[key], model: p.model, point: p});
  });
  var peak = pxNice(Math.max.apply(null, pts.map(function (p) { return p.v; })) || 1);
  function Y(v) { return TOP + PH * (1 - v / peak); }

  var ticks = [], seen = null;
  [0, 0.5, 1].forEach(function (f) {
    var label = pxAxis(peak * f);
    if (label !== seen) ticks.push({y: Y(peak * f), label: label});
    seen = label;
  });
  var months = [], d0 = parse(from);
  var d = new Date(Date.UTC(d0.getUTCFullYear(), d0.getUTCMonth() + 1, 1));
  while (iso(d) <= to) {
    months.push({date: iso(d), x: X(iso(d)), jan: d.getUTCMonth() === 0});
    d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1));
  }
  var every = Math.max(1, Math.ceil(months.length / Math.max(2, Math.floor((W - L - R) / 64))));

  var path = "";
  pts.forEach(function (p, i) {
    path += i ? "H" + X(p.date).toFixed(1) + "V" + Y(p.v).toFixed(1)
              : "M" + X(p.date).toFixed(1) + "," + Y(p.v).toFixed(1);
  });
  path += "H" + X(to).toFixed(1);

  var taken = {up: -Infinity, down: -Infinity};
  var dots = pts.map(function (p, i) {
    var x = X(p.date), y = Y(p.v), w = pxName(p.model).length * 6.6 + 10;
    var named = i === 0 ? true : (p.point && p.model !== pts[i - 1].model);
    var x0 = Math.min(x + 7, W - R - w), where = null;
    if (named) {
      if (x0 >= taken.up) where = "up";
      else if (x0 >= taken.down) where = "down";
      if (where) taken[where] = x0 + w + 4;
    }
    return {x: x, y: y, date: p.date, model: p.model, value: p.v, carried: !!p.carried,
            label: where ? pxName(p.model) : null, labelY: where === "down" ? y + 20 : y - 10, anchorX: x0};
  });
  return {W: W, H: H, L: L, R: R, TOP: TOP, PH: PH, ticks: ticks, months: months.filter(function (_, i) { return i % every === 0; }),
          path: path, dots: dots};
}

function pxLineSvg(g, line) {
  var s = '<svg viewBox="0 0 ' + g.W + " " + g.H + '" width="' + g.W + '" height="' + g.H
    + '" role="img" aria-label="' + esc(t18("px_chart_aria", "Price by model line over time")) + '">';
  g.ticks.forEach(function (tk) {
    s += '<line class="gridline" x1="' + g.L + '" y1="' + tk.y.toFixed(1) + '" x2="' + (g.W - g.R)
      + '" y2="' + tk.y.toFixed(1) + '"/><text x="' + (g.L - 8) + '" y="' + (tk.y + 4).toFixed(1)
      + '" text-anchor="end" class="axis">' + esc(tk.label) + "</text>";
  });
  g.months.forEach(function (m) {
    var p = dayInfo(m.date);
    s += '<text x="' + m.x.toFixed(1) + '" y="' + (g.H - 8) + '" text-anchor="middle" class="axis">'
      + esc(p.mon + (m.jan ? " " + m.date.slice(0, 4) : "")) + "</text>";
  });
  s += '<path class="pxmain" d="' + g.path + '" style="stroke:' + pxColor(line) + '"/>';
  g.dots.forEach(function (d) {
    if (!d.carried) {
      s += '<circle class="pxdot" cx="' + d.x.toFixed(1) + '" cy="' + d.y.toFixed(1) + '" r="4.5" style="fill:'
        + pxColor(line) + '" data-tt="' + esc(pxName(d.model) + " · " + pxDay(d.date) + " · " + pxMoney(d.value)) + '"/>';
    }
    if (d.label) {
      s += '<text class="pxmname" x="' + d.anchorX.toFixed(1) + '" y="' + d.labelY.toFixed(1) + '">' + esc(d.label) + "</text>";
    }
  });
  return s + "</svg>";
}

/* Why a price moved. The page's headline number is for a typical session, and a
   session is ~97% cache reads, so a change to cache reads can be most of what you
   feel even when it is the smallest line on the vendor's price list. Each of the
   four prices gets its old and new value and its share of the effect on the
   displayed number (price change x how many tokens of that kind a session has).
   `share` is null on the list-price basis, where there is nothing to weigh. */
function pxExplain(event, key) {
  if (!event) return null;
  var mix = key === "eff_you" && PT.mixes.yours ? PT.mixes.yours : PT.mixes.reference;
  var by = {};
  (event.changed || []).forEach(function (c) { by[c.component] = c; });
  var effect = {}, total = 0;
  PT.components.forEach(function (c) {
    effect[c] = by[c] ? mix[c] * (by[c].to - by[c].from) : 0;
    total += effect[c];
  });
  var weighs = key === "eff_ref" || key === "eff_you";
  var rows = PT.components.map(function (c) {
    var ch = by[c];
    return {component: c, changed: !!ch, from: ch ? ch.from : null, to: ch ? ch.to : null,
            pct: ch && ch.from ? (ch.to / ch.from - 1) * 100 : null,
            share: weighs && ch && total ? Math.round(effect[c] / total * 100) : null};
  });
  var lead = null;
  if (weighs) {
    rows.forEach(function (r) { if (r.share != null && (!lead || r.share > lead.share)) lead = r; });
  }
  return {rows: rows, lead: lead && lead.share >= 50 ? lead : null};
}
function pxEventsFor(line, from, to) {
  return PT.events.filter(function (e) {
    return e.line === line.id && e.date > from && e.date <= to && e.kind !== "launch";
  });
}

function pxEventText(e) {
  var line = pxLine(e.line), who = pxLabName(e.lab) + " " + (line ? line.label : e.line);
  var pct = e.delta_pct == null ? "—" : pxPct(e.delta_pct);
  var parts = (e.changed || []).map(function (c) {
    return t18("px_c_" + c.component, c.component).toLowerCase() + " " + pxMoney(c.from) + " → " + pxMoney(c.to);
  }).join(", ");
  if (e.kind === "launch") {
    return tf("px_e_launch", "%W%: %M% launched at %P% for a typical session",
      {W: who, M: pxName(e.model), P: pxMoney(line ? pxAt(line, e.date, "eff_ref") : null)});
  }
  if (e.kind === "succession") {
    return tf("px_e_succ", "%W%: %M% replaced %F% — %P% for a typical session (%C%)",
      {W: who, M: pxName(e.model), F: pxName(e.from_model), P: pct,
       C: parts || t18("px_e_same", "same prices")});
  }
  return tf(e.kind === "cut" ? "px_e_cut" : "px_e_rise", e.kind === "cut"
    ? "%W%: %M% got cheaper — %P% for a typical session (%C%)"
    : "%W%: %M% got dearer — %P% for a typical session (%C%)",
    {W: who, M: pxName(e.model), P: pct, C: parts});
}
function pxEventItems(list) {
  return '<ul class="pxevents">' + list.map(function (e) {
    var d = e.delta_pct == null ? "none" : pxDir(e.delta_pct);
    return '<li class="px' + d + '"><span class="pxevd">' + esc(pxDay(e.date)) + "</span> "
      + esc(pxEventText(e)) + "</li>";
  }).join("") + "</ul>";
}

/* The focus chart is drawn at the width of the column it sits in, which is the
   page's layout talking (it shares a row with the "why" panel above 900px and
   stacks under it below that). Guessing that from the CSS would be a second copy
   of a rule, so it is measured: draw, read the real column, and draw again if
   they differ. */
var pxFocusW = 0;
function pxFitFocus(line, key, from, to) {
  var col = document.querySelector("#pxFocus .pxfchart");
  if (!col || !col.clientWidth || Math.abs(col.clientWidth - pxFocusW) < 8) return;
  pxFocusW = col.clientWidth;
  col.innerHTML = pxLineSvg(pxLineChart(line, key, from, to, pxFocusW), line);
}

function pxFocus(line, key, from, to) {
  var pct = pxChange(line, key, from, to), dir = pxDir(pct), now = pxAt(line, to, key);
  var g = pxLineChart(line, key, from, to, pxFocusW || 640);
  var evs = pxEventsFor(line, from, to);
  var last = null;
  evs.some(function (e) { if (e.changed && e.changed.length) { last = e; return true; } return false; });
  var why = last ? pxExplain(last, key) : null;

  var s = '<div class="pxfhead"><div><p class="pxfk">' + esc(t18("px_selected", "Selected")) + "</p>"
    + '<h2><i class="pxsw" style="background:' + pxColor(line) + '"></i>' + esc(pxLineName(line))
    + ' <span class="tag">' + esc(t18("px_tier_" + line.tier, line.tier)) + "</span></h2>"
    + '<p class="scope">' + esc(pxName(line.models[line.models.length - 1])) + "</p></div>"
    + '<div class="pxbig"><b>' + esc(pxMoney(now)) + '</b><span class="pxpc ' + dir + '">'
    + (pct == null ? "—" : (dir === "down" ? "▼" : dir === "up" ? "▲" : "●") + " " + esc(pxPct(pct)))
    + "</span><small>" + esc(t18("px_g_per", "per 1M tokens") + " · " + pxRangeWords()) + "</small></div></div>";

  s += '<div class="pxfbody"><div class="pxfchart">' + pxLineSvg(g, line) + "</div>";
  s += '<div class="pxwhy">';
  if (why && last) {
    s += "<h3>" + esc(tf("px_d_moved", "What moved on %D%", {D: pxDay(last.date)})) + "</h3>"
      + '<p class="scope">' + esc(pxName(last.from_model || last.model) + " → " + pxName(last.model)) + "</p><ul>";
    why.rows.forEach(function (r) {
      var lead = why.lead && why.lead.component === r.component;
      s += '<li class="' + (r.changed ? "moved" : "") + (lead ? " lead" : "") + '"><span class="pxcn">'
        + esc(t18("px_c_" + r.component, r.component)) + "</span>";
      if (r.changed) {
        s += '<span class="pxcv">' + esc(pxMoney(r.from) + " → " + pxMoney(r.to)) + ' <em class="pxpc '
          + pxDir(r.pct) + '">' + esc(pxPct(r.pct)) + "</em></span>";
        if (r.share != null) {
          s += '<span class="pxshare"><i style="width:' + Math.max(2, Math.abs(r.share)) + '%"></i></span>'
            + '<span class="pxsh">' + esc(tf("px_d_share", "%S% of the change", {S: r.share})) + "</span>";
        }
      } else {
        s += '<span class="pxcv quiet">' + esc(t18("px_g_nochg", "no change")) + "</span>";
      }
      s += "</li>";
    });
    s += "</ul>";
    if (why.lead) {
      s += '<p class="pxlead">' + esc(tf("px_d_why",
        "%C% accounts for %S%% of the change, because most tokens in a session are of that kind.",
        {C: t18("px_c_" + why.lead.component, why.lead.component), S: why.lead.share})) + "</p>";
    }
  } else {
    s += "<h3>" + esc(t18("px_d_nomove", "No price change in this range.")) + "</h3><ul>";
    var cur = line.points[line.points.length - 1];
    PT.components.forEach(function (c) {
      s += '<li><span class="pxcn">' + esc(t18("px_c_" + c, c)) + '</span><span class="pxcv">'
        + esc(pxMoney(cur[c])) + "</span></li>";
    });
    s += "</ul>";
  }
  s += "</div></div>";
  if (evs.length) {
    s += '<h3 class="pxhist">' + esc(t18("px_d_hist", "Every change to this line")) + "</h3>" + pxEventItems(evs);
  }
  return s;
}

/* ---- 3. everything else, on demand ---------------------------------------- */

/* Steps, because a price holds until it changes. Lines that end at the same
   price (Opus and the GPT flagship both sat at $5; Sonnet and Terra at $2) would
   print their names on top of each other, so they share ONE label
   ("Opus · GPT flagship"); the rest are nudged until no two are closer than
   a line of text. No model names here: at seven lines they cannot all fit, and
   the focus chart above is where they are. */
function pxAllChart(lines, key, from, to, width) {
  var W = Math.max(560, Math.round(width) || 960);
  var L = 56, R = 168, TOP = 16, H = 320, PH = H - TOP - 28;
  var span = Math.max(1, pxDays(from, to)), idx = PX.scale === "index";
  function X(d) { return L + (W - L - R) * Math.max(0, pxDays(from, d)) / span; }
  var series = [];
  lines.forEach(function (l) {
    if (PX.off[l.id]) return;
    var carry = pxAt(l, from, key);
    var base = carry != null ? carry : l.points[0][key];
    if (base == null) return;
    var start = carry != null ? from : l.points[0].date;
    var pts = [{date: start, v: base, model: pxModelAt(l, from), carried: carry != null}];
    l.points.forEach(function (p) {
      if (p.date > start && p.date <= to) pts.push({date: p.date, v: p[key], model: p.model, point: p});
    });
    pts.forEach(function (p) { p.y = idx ? p.v / base * 100 : p.v; });
    series.push({line: l, pts: pts});
  });
  if (!series.length) return {empty: true};
  var peak = 0;
  series.forEach(function (s) { s.pts.forEach(function (p) { if (p.y > peak) peak = p.y; }); });
  peak = pxNice(peak || 1);
  function Y(v) { return TOP + PH * (1 - v / peak); }

  var ticks = [], seen = null;
  [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
    var label = idx ? String(+(peak * f).toFixed(0)) : pxAxis(peak * f);
    if (label === seen) return;
    seen = label;
    ticks.push({y: Y(peak * f), label: label});
  });
  var months = [], d0 = parse(from);
  var d = new Date(Date.UTC(d0.getUTCFullYear(), d0.getUTCMonth() + 1, 1));
  while (iso(d) <= to) {
    months.push({date: iso(d), x: X(iso(d)), jan: d.getUTCMonth() === 0});
    d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1));
  }
  var every = Math.max(1, Math.ceil(months.length / Math.max(2, Math.floor((W - L - R) / 70))));

  var out = series.map(function (s) {
    var path = "";
    s.pts.forEach(function (p, i) {
      path += i ? "H" + X(p.date).toFixed(1) + "V" + Y(p.y).toFixed(1)
                : "M" + X(p.date).toFixed(1) + "," + Y(p.y).toFixed(1);
    });
    path += "H" + X(to).toFixed(1);
    return {line: s.line, path: path, pts: s.pts, last: s.pts[s.pts.length - 1].y, endY: Y(s.pts[s.pts.length - 1].y)};
  });
  var byY = out.slice().sort(function (a, b) { return a.endY - b.endY; });
  var labels = [];
  byY.forEach(function (o) {
    var prev = labels[labels.length - 1];
    if (prev && Math.abs(o.endY - prev.y) < 6) { prev.names.push(o.line.label); prev.ids.push(o.line.id); }
    else labels.push({y: o.endY, names: [o.line.label], ids: [o.line.id], line: o.line});
  });
  for (var i = 1; i < labels.length; i++) if (labels[i].y - labels[i - 1].y < 15) labels[i].y = labels[i - 1].y + 15;
  return {empty: false, W: W, H: H, L: L, R: R, TOP: TOP, PH: PH, ticks: ticks, X: X, Y: Y, idx: idx,
          months: months.filter(function (_, i) { return i % every === 0; }), series: out, labels: labels};
}

function pxAllSvg(g, X, Y) {
  var s = '<svg viewBox="0 0 ' + g.W + " " + g.H + '" role="img" width="' + g.W + '" height="' + g.H
    + '" preserveAspectRatio="xMinYMin meet" aria-label="' + esc(t18("px_chart_aria", "Price by model line over time")) + '">';
  g.ticks.forEach(function (tk) {
    s += '<line class="gridline" x1="' + g.L + '" y1="' + tk.y.toFixed(1) + '" x2="' + (g.W - g.R)
      + '" y2="' + tk.y.toFixed(1) + '"/><text x="' + (g.L - 8) + '" y="' + (tk.y + 4).toFixed(1)
      + '" text-anchor="end" class="axis">' + esc(tk.label) + "</text>";
  });
  g.months.forEach(function (m) {
    var p = dayInfo(m.date);
    s += '<line class="gridline" x1="' + m.x.toFixed(1) + '" y1="' + (g.TOP + g.PH) + '" x2="' + m.x.toFixed(1)
      + '" y2="' + (g.TOP + g.PH + 4) + '"/><text x="' + m.x.toFixed(1) + '" y="' + (g.H - 8)
      + '" text-anchor="middle" class="axis">' + esc(p.mon + (m.jan ? " " + m.date.slice(0, 4) : "")) + "</text>";
  });
  g.series.forEach(function (o) {
    var l = o.line, color = pxColor(l);
    s += '<g class="pxs" data-line="' + esc(l.id) + '">'
      + '<path class="pxl pxt-' + esc(l.tier) + '" d="' + o.path + '" style="stroke:' + color + '"/>'
      + '<path class="pxhit" d="' + o.path + '" data-tt="' + esc(pxLineName(l) + " — "
      + (g.idx ? o.last.toFixed(0) + " (" + t18("px_sc_idx", "Index").toLowerCase() + ")" : pxMoney(o.last))) + '"/>';
    if (PX.markers) {
      o.pts.forEach(function (p, i) {
        if (!i && p.carried) return;
        var tip = pxName(p.model) + " · " + pxDay(p.date) + " · " + (g.idx ? p.y.toFixed(0) : pxMoney(p.y));
        var ev = null;
        if (p.point) PT.events.some(function (e) { if (e.line === l.id && e.date === p.date) { ev = e; return true; } return false; });
        if (ev && ev.delta_pct != null) tip += " (" + pxPct(ev.delta_pct) + ")";
        s += '<circle class="pxdot" cx="' + X(p.date).toFixed(1) + '" cy="' + Y(p.y).toFixed(1)
          + '" r="3.4" style="fill:' + color + '" data-tt="' + esc(tip) + '"/>';
      });
    }
    s += "</g>";
  });
  g.labels.forEach(function (lb) {
    s += '<text class="pxend" data-ids="' + esc(lb.ids.join(",")) + '" x="' + (g.W - g.R + 8) + '" y="'
      + (lb.y + 4).toFixed(1) + '" style="fill:' + pxColor(lb.line) + '">' + esc(lb.names.join(" · ")) + "</text>";
  });
  return s + "</svg>";
}

/* Hovering a name, or a line, dims the others. Classes on the existing nodes
   rather than a redraw: redrawing the legend under the pointer would fire
   mouseout the instant it was replaced. */
function pxIsolate(id) {
  var host = $("pxChart");
  if (!host) return;
  [].forEach.call(host.querySelectorAll("[data-line],[data-ids]"), function (el) {
    var ids = (el.getAttribute("data-line") || el.getAttribute("data-ids") || "").split(",");
    el.classList.toggle("dim", !!id && ids.indexOf(id) < 0);
  });
}

function drawCompare() {
  var key = pxKey(), from = pxStart(), to = PT.as_of;
  var lines = PX.zoom === "labs" ? PT.lines.filter(function (l) { return l.headline; }) : PT.lines;
  var host = $("pxChart");
  var g = pxAllChart(lines, key, from, to, host ? host.clientWidth : 0);
  if (host) {
    host.innerHTML = g.empty ? '<p class="empty">' + esc(t18("px_none", "Nothing to draw with these choices.")) + "</p>"
                             : pxAllSvg(g, g.X, g.Y);
  }
  if ($("pxLegend")) {
    $("pxLegend").innerHTML = PX.zoom === "labs" ? "" : lines.map(function (l) {
      return '<button type="button" class="pxleg" data-line="' + esc(l.id) + '" aria-pressed="' + !PX.off[l.id] + '">'
        + '<i class="pxsw" style="background:' + pxColor(l) + '"></i>' + esc(pxLineName(l)) + "</button>";
    }).join("");
  }
}

/* The table of every model and the window each price applied for. */
function pxModels() {
  var eff = PX.basis === "you" && PT.mixes.yours ? "eff_you" : "eff_ref", rows = "";
  PT.lines.forEach(function (l) {
    l.points.forEach(function (p, i) {
      var next = l.points[i + 1];
      rows += "<tr><td>" + esc(pxLineName(l)) + "</td><td><strong>" + esc(pxName(p.model))
        + "</strong></td><td>" + esc(pxDay(p.date)) + "</td><td>"
        + (next ? esc(pxDay(next.date)) : esc(t18("px_now", "now"))) + "</td>"
        + '<td class="n">' + esc(pxMoney(p.input)) + '</td><td class="n">' + esc(pxMoney(p.output))
        + '</td><td class="n">' + esc(pxMoney(p.cache_read)) + '</td><td class="n">' + esc(pxMoney(p.cache_write))
        + '</td><td class="n"><strong>' + esc(pxMoney(p[eff])) + "</strong></td></tr>";
    });
  });
  var head = [t18("px_th_line2", "Line"), t18("px_th_model2", "Model"), t18("px_th_from", "From"),
              t18("px_th_until", "Until"), t18("px_c_input", "Input"), t18("px_c_output", "Output"),
              t18("px_c_cache_read", "Cache read"), t18("px_c_cache_write", "Cache write"),
              PX.basis === "you" && PT.mixes.yours ? t18("px_th_eff_you", "Your mix") : t18("px_th_eff", "Typical session")];
  return '<div class="scroll"><table class="pxtable"><thead><tr>'
    + head.map(function (h) { return "<th>" + esc(h) + "</th>"; }).join("")
    + "</tr></thead><tbody>" + rows + "</tbody></table></div>";
}

function pxNotes() {
  var notes = [
    tf("px_n_mix", "A typical session is a measured mix: %M%. Cache reads are nearly all of it, so a change in cache price moves the figure far more than a change in headline input or output price. Use “List price” to see each price alone.",
       {M: pxMixText(PT.mixes.reference)}),
    t18("px_n_list", "These are the vendors’ list prices. A gateway or reseller can bill differently, and apply a vendor’s change at its own time."),
    t18("px_n_dates", "Vendors publish a date, not an hour. A date-only change is shown from the start of that day in Singapore time, so it can be off by about a day."),
    t18("px_n_tok", "A price per token is not a price per task: Anthropic says Fable 5 and Sonnet 5 turn the same text into about 30% more tokens than earlier models, which is not reflected here."),
    t18("px_n_tiers", "Long-prompt surcharges and Fast mode are not modelled; a transcript does not record them.")
  ];
  return notes.map(function (n) { return "<li>" + esc(n) + "</li>"; }).join("");
}
function pxUntraced() {
  if (!PT.untraced.length) return "";
  var names = PT.untraced.map(function (u) { return u.vendor + " (" + u.models + ")"; }).join(", ");
  return '<p class="pxuntraced"><strong>' + esc(t18("px_u_h", "Not traced yet")) + "</strong> "
    + esc(tf("px_u_text", "We have today’s prices for %V% but not their history, so no trend is drawn for them rather than a flat line that would read as “never changed”. Adding a line to pricing.json is how one joins this page.",
             {V: names})) + "</p>";
}

/* ---- controls ------------------------------------------------------------- */
function pxChips(id, items, current, attr) {
  var el = $(id);
  if (!el) return;
  el.innerHTML = items.map(function (it) {
    return '<button type="button" ' + attr + '="' + esc(it[0]) + '" aria-pressed="' + (it[0] === current)
      + '"' + (it[2] ? " disabled" : "") + ">" + esc(it[1]) + "</button>";
  }).join("");
}
function pxChipsBool(id, items) {
  var el = $(id);
  if (!el) return;
  el.innerHTML = items.map(function (it) {
    return '<button type="button" data-flag="' + it[0] + '" aria-pressed="' + it[2] + '">' + esc(it[1]) + "</button>";
  }).join("");
}

function drawPrices() {
  if (!PT || !PT.lines || !PT.lines.length) return;
  if (PX.basis === "you" && !PT.mixes.yours) PX.basis = "ref";
  var key = pxKey(), from = pxStart(), to = PT.as_of;
  var sm = pxSummary(key, from, to), g = pxGlance(key, from, to);

  if ($("pxStamp")) {
    $("pxStamp").textContent = tf("px_stamp",
      "Prices as of %D% · history traced for %L% · list prices, not an invoice",
      {D: PT.as_of, L: PT.labs.map(function (l) { return l.label; }).join(" + ")});
  }
  pxChips("pxRange", [["90", t18("px_r90", "90 days")], ["180", t18("px_r180", "180 days")],
                      ["all", t18("px_rall", "All")]], PX.range, "data-range");

  // 1. at a glance
  $("pxKpis").innerHTML = pxKpis(sm);
  pxWatch();
  pxChips("pxBasis", [["ref", t18("px_bs_ref", "Typical session")],
                      ["you", t18("px_bs_you", "Your mix"), !PT.mixes.yours],
                      ["list", t18("px_bs_list", "List price")]], PX.basis, "data-basis");
  pxChips("pxComp", [["input", t18("px_c_input", "Input")], ["output", t18("px_c_output", "Output")],
                     ["cache_read", t18("px_c_cache_read", "Cache read")],
                     ["cache_write", t18("px_c_cache_write", "Cache write")]], PX.comp, "data-comp");
  $("pxComp").hidden = PX.basis !== "list";
  $("pxBasisNote").textContent = pxBasisWords();
  pxChips("pxZoom", [["labs", t18("px_z_labs", "Labs")], ["lines", t18("px_z_lines", "Lines")],
                     ["models", t18("px_z_models", "Models")]], PX.zoom, "data-zoom");

  // 2. one line in focus: the one asked for, else the biggest mover
  var chosen = null;
  g.rows.forEach(function (r) { if (r.line.id === PX.sel) chosen = r.line; });
  var focus = chosen || pxBiggest(g.rows);
  $("pxList").innerHTML = pxList(g, focus ? focus.id : null);
  $("pxFocus").hidden = !focus;
  if (focus) { $("pxFocus").innerHTML = pxFocus(focus, key, from, to); pxFitFocus(focus, key, from, to); }

  // 3. the rest
  pxChips("pxScale", [["abs", t18("px_sc_abs", "Dollars")], ["index", t18("px_sc_idx", "Index")]], PX.scale, "data-scale");
  pxChipsBool("pxToggles", [["markers", t18("px_t_markers", "Change markers"), PX.markers]]);
  drawCompare();
  $("pxModelsCard").hidden = PX.zoom !== "models";
  if (PX.zoom === "models") $("pxModels").innerHTML = pxModels();
  var shown = PX.evAll ? PT.events : PT.events.slice(0, 8);
  $("pxEvents").innerHTML = pxEventItems(shown);
  var more = $("pxEvMore");
  if (more) {
    more.hidden = PT.events.length <= 8;
    more.textContent = PX.evAll ? t18("px_ev_less", "Show fewer") : tf("px_ev_more", "Show all %N%", {N: PT.events.length});
  }
  $("pxUntraced").innerHTML = pxUntraced();
  $("pxNotes").innerHTML = pxNotes();
}

/* ---- the page switch ------------------------------------------------------ */
function setView(name) {
  var main = document.querySelector("main.wrap");
  pxVisible = name === "prices" && !!PT;
  if (main) {
    main.classList.toggle("on-prices", pxVisible);
    // Tag what is the dashboard once, so the switch is a class and not a pass
    // over elements that each manage their own `hidden`.
    if (!main.getAttribute("data-tagged")) {
      main.setAttribute("data-tagged", "1");
      [].forEach.call(main.children, function (el) {
        var tag = (el.tagName || "").toLowerCase();
        if (tag !== "footer" && el.id !== "pricesView" && el.id !== "fresh") el.setAttribute("data-v", "dash");
      });
    }
  }
  var pv = $("pricesView");
  if (pv) pv.hidden = !pxVisible;
  var links = document.querySelectorAll("#railnav a");
  [].forEach.call(links, function (a) {
    if (a.getAttribute("data-view") === "prices") {
      if (pxVisible) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
    } else if (pxVisible) a.removeAttribute("aria-current");
  });
  if (pxVisible) {
    drawPrices();
    try { window.scrollTo(0, 0); } catch (e) {}
  } else {
    railLight();
  }
}

function initPrices() {
  if (!PT || !PT.lines || !PT.lines.length) return;   // an older digest: no link, no page
  pxLoad();
  var rail = $("railPrices");
  if (rail) rail.hidden = false;

  function on(id, attr, fn) {
    var el = $(id);
    if (!el) return;
    el.addEventListener("click", function (e) {
      var b = ancestor(e.target, "button[" + attr + "]");
      if (!b || b.disabled) return;
      fn(b.getAttribute(attr));
      pxSave();
      drawPrices();
    });
  }
  on("pxRange", "data-range", function (v) { PX.range = v; });
  on("pxZoom", "data-zoom", function (v) { PX.zoom = v; });
  on("pxBasis", "data-basis", function (v) { PX.basis = v; });
  on("pxComp", "data-comp", function (v) { PX.comp = v; });
  on("pxScale", "data-scale", function (v) { PX.scale = v; });
  on("pxToggles", "data-flag", function (v) { PX[v] = !PX[v]; });
  on("pxLegend", "data-line", function (v) { PX.off[v] = !PX.off[v]; });
  // Choosing a row is not a setting worth remembering; it is what you are looking at.
  if ($("pxList")) $("pxList").addEventListener("click", function (e) {
    var b = ancestor(e.target, "button[data-line]");
    if (!b) return;
    PX.sel = b.getAttribute("data-line");
    drawPrices();
  });
  if ($("pxEvMore")) $("pxEvMore").addEventListener("click", function () {
    PX.evAll = !PX.evAll;
    drawPrices();
  });
  // The all-lines chart is measured, so it is drawn again once the section is
  // actually open and has a width.
  if ($("pxCmp")) $("pxCmp").addEventListener("toggle", function () { if (pxVisible) drawCompare(); });
  ["pxChart", "pxLegend"].forEach(function (id) {
    var el = $(id);
    if (!el) return;
    function hover(e) {
      var n = ancestor(e.target, "[data-line]");
      pxIsolate(n ? n.getAttribute("data-line") : null);
    }
    el.addEventListener("mouseover", hover);
    el.addEventListener("focusin", hover);
    el.addEventListener("mouseout", function () { pxIsolate(null); });
    el.addEventListener("focusout", function () { pxIsolate(null); });
  });

  function route() { setView(window.location.hash === "#prices" ? "prices" : "dash"); }
  window.addEventListener("hashchange", route);
  route();
}

initTheme();
init();
initLang();
initCalendar();
initRail();
initFreshness();
initPrices();
})();
