/* AI Observatory — client. Re-aggregates the inlined fact cube for whatever
   date range and slicers are selected. No network, no dependencies. */
(function () {
"use strict";

var D = JSON.parse(document.getElementById("digest").textContent);
var $ = function (id) { return document.getElementById(id); };

var MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
var DOW = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

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
  return CUR.symbol + n.toLocaleString(undefined,
    {minimumFractionDigits: d, maximumFractionDigits: d});
}
function pctOf(a, b) { return b ? (100 * a / b) : 0; }

/* ---- metric explainers ---------------------------------------------------
   Every behavioral metric gets a small ⓘ affordance carrying its own formula
   and intent, via the same data-tt tooltip every chart already uses. One
   copy per metric, reused everywhere that metric appears so wording never
   drifts between the KPI tile and its trend sparkline. */
var INFO = {
  spend: "List-price estimate from token counts \u00d7 the rate card, at the rate in force when each turn ran. If you are on a flat monthly plan this is a shadow price \u2014 what the same work would have cost metered \u2014 not a bill you received.",
  peak: "Share of your time-priced spend that landed inside a vendor's peak window. Vendors that bill one flat rate all day are excluded from both sides of this, so 0% here means \u201cnothing you use is time-priced\u201d, not \u201cperfectly scheduled\u201d.",
  turnsPerSession: "How many exchanges a typical task takes. Total turns ÷ sessions. Falling over time = you're resolving things in fewer round-trips.",
  cache: "Share of read tokens served from cache instead of resent at full price. cache_read ÷ (input + cache_read + cache_create).",
  toolCallsPerTurn: "How often each turn actually does something vs. just talks. Total tool calls ÷ total turns. Near zero = chatbot-style use; higher = agentic use.",
  modelSwitchShare: "Share of sessions that used more than one model. Sessions with >1 distinct model ÷ all sessions. High and rising can mean you're matching model to task; high and flat can mean indecision.",
  writeRead: "Edits made per file looked at. Write-tool calls ÷ read-tool calls. Low = mostly exploring; high = mostly producing."
};
function info(key) {
  var t = INFO[key];
  if (!t) return "";
  return ' <span class="info" tabindex="0" role="img" aria-label="What this measures" data-tt="'
    + esc(t) + '">i</span>';
}

/* ---- behavioral metrics ---------------------------------------------------
   Favor these over raw volume: they say whether AI collaboration is getting
   more effective, not just how much of it happened. */
function turnsPerSession(t, sessions) { return sessions.length ? t.turns / sessions.length : 0; }
function toolCallsPerTurn(t) { return t.turns ? t.tool_calls / t.turns : 0; }
function modelSwitchShare(sessions) {
  if (!sessions.length) return 0;
  var n = sessions.filter(function (s) { return (s.models || []).length > 1; }).length;
  return 100 * n / sessions.length;
}
function medianMinutes(sessions) {
  var mins = sessions.map(function (s) {
    if (!s.start || !s.end) return 0;
    return Math.max(0, (new Date(s.end) - new Date(s.start)) / 60000);
  }).sort(function (a, b) { return a - b; });
  if (!mins.length) return 0;
  var mid = Math.floor(mins.length / 2);
  return mins.length % 2 ? mins[mid] : (mins[mid - 1] + mins[mid]) / 2;
}

/* ---- dates: everything is a plain YYYY-MM-DD string in UTC ---- */
function parse(iso) { return new Date(iso + "T00:00:00Z"); }
function iso(d) { return d.toISOString().slice(0, 10); }
function shift(isoStr, days) {
  var d = parse(isoStr); d.setUTCDate(d.getUTCDate() + days); return iso(d);
}
function span(from, to) {
  var out = [], cur = from;
  while (cur <= to && out.length < 800) { out.push(cur); cur = shift(cur, 1); }
  return out;
}
function dayInfo(isoStr) {
  var d = parse(isoStr), w = d.getUTCDay();
  return {dow: DOW[w], initial: DOW[w][0], weekend: w === 0 || w === 6,
          dom: String(d.getUTCDate()).padStart(2, "0"), mon: MON[d.getUTCMonth()],
          first: d.getUTCDate() === 1};
}
function longDate(isoStr) {
  var p = dayInfo(isoStr);
  return p.dow + " " + p.dom + " " + p.mon + " " + isoStr.slice(0, 4);
}

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
function bars(rows, label, value, fmt, pickable) {
  rows = rows.filter(function (r) { return (value(r) || 0) > 0; });
  if (!rows.length) return '<p class="empty">Nothing in this range.</p>';
  var peak = Math.max.apply(null, rows.map(value)) || 1;
  return '<div class="hbars">' + rows.map(function (r) {
    var v = value(r) || 0, full = String(label(r));
    return '<div class="hbar' + (pickable ? " hit" : "") + '" data-pick="' + esc(full)
      + '" data-tt="' + esc(full + " — " + fmt(v)) + '">'
      + '<span class="hl">' + esc(full) + "</span>"
      + '<span class="ht"><i style="width:' + Math.max(1.5, 100 * v / peak).toFixed(1)
      + '%"></i></span>'
      + '<span class="hv">' + esc(fmt(v)) + "</span></div>";
  }).join("") + "</div>";
}

function daily(days, byDate, metric, fmt, picked) {
  if (!days.length) return '<p class="empty">Nothing in this range.</p>';
  var W = 720, L = 50, R = 8, TOP = 18, PH = 112, H = 218;
  var base = TOP + PH, plotW = W - L - R, step = plotW / days.length;
  var bw = Math.max(1.5, Math.min(step * 0.68, 26));
  var vals = days.map(function (d) { return (byDate[d] || 0); });
  var peak = Math.max.apply(null, vals) || 1;
  var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" preserveAspectRatio="xMinYMin meet">';

  // Weekend bands first, so every mark sits on top of them.
  days.forEach(function (d, i) {
    if (dayInfo(d).weekend) {
      s += '<rect x="' + (L + i * step).toFixed(1) + '" y="' + TOP + '" width="'
        + step.toFixed(1) + '" height="' + PH + '" fill="var(--track)" opacity=".45"/>';
    }
    if (d === picked) {
      s += '<rect x="' + (L + i * step).toFixed(1) + '" y="' + TOP + '" width="'
        + step.toFixed(1) + '" height="' + PH + '" fill="var(--sel)"/>';
    }
  });
  [0, 0.5, 1].forEach(function (f) {
    var gy = TOP + PH * (1 - f);
    s += '<line x1="' + L + '" y1="' + gy.toFixed(1) + '" x2="' + (W - R) + '" y2="'
      + gy.toFixed(1) + '" stroke="var(--line)" stroke-width="1"/>'
      + '<text x="' + (L - 8) + '" y="' + (gy + 4).toFixed(1) + '" text-anchor="end" '
      + 'class="axis">' + esc(fmt(peak * f)) + "</text>";
  });

  // Bars, each a click target (drill into that day) carrying its own tooltip.
  days.forEach(function (d, i) {
    var v = vals[i], h = PH * (v / peak), isPicked = d === picked;
    var x = L + i * step + (step - bw) / 2;
    s += '<g class="daycol" data-day="' + d + '" data-tt="'
      + esc(longDate(d) + " — " + fmt(v) + " " + metric) + '">'
      + '<rect x="' + x.toFixed(1) + '" y="' + (base - h).toFixed(1) + '" width="' + bw.toFixed(1)
      + '" height="' + Math.max(h, v ? 1.2 : 0).toFixed(1) + '" rx="2" fill="var(--accent)"'
      + (isPicked ? ' stroke="var(--ink)" stroke-width="1.2"' : '') + '/>'
      + '<rect class="hitcol" x="' + (L + i * step).toFixed(1) + '" y="' + TOP + '" width="'
      + step.toFixed(1) + '" height="' + PH + '" fill="transparent"/></g>';
  });
  s += rollingMean(vals, L, step, base, PH, peak);
  s += dayAxis(days, L, step, base, W, R);
  return s + "</svg>";
}

// Seven-day trailing mean — the trend under the weekday sawtooth.
function rollingMean(vals, L, step, base, PH, peak) {
  if (vals.length < 7) return "";
  var pts = [];
  for (var i = 6; i < vals.length; i++) {
    var sum = 0;
    for (var j = i - 6; j <= i; j++) sum += vals[j];
    var y = base - PH * ((sum / 7) / peak);
    pts.push((L + i * step + step / 2).toFixed(1) + "," + y.toFixed(1));
  }
  return '<polyline points="' + pts.join(" ") + '" fill="none" stroke="var(--med)" '
    + 'stroke-width="1.6" stroke-linejoin="round" opacity=".9"/>';
}
/* Per-day axis: a weekday initial under every column, and a dated label on as
   many as will fit without touching. Month starts always keep their label and
   get a divider, so "which day of which month" is never ambiguous. */
function dayAxis(days, L, step, base, PH) {
  var n = days.length, every = Math.max(1, Math.ceil(17 / step));
  var minGap = Math.max(1, Math.ceil(15 / step)), want = {}, s = "";
  for (var i = 0; i < n; i += every) want[i] = 1;
  days.forEach(function (d, k) { if (dayInfo(d).first) want[k] = 1; });
  want[n - 1] = 1;

  var shown = [];
  Object.keys(want).map(Number).sort(function (a, b) { return a - b; })
    .forEach(function (k) {
      if (!shown.length || k - shown[shown.length - 1] >= minGap) shown.push(k);
      else if (k === n - 1) shown[shown.length - 1] = k;  // the last day wins its slot
    });
  var label = {};
  shown.forEach(function (k) { label[k] = 1; });

  days.forEach(function (d, k) {
    var p = dayInfo(d), cx = L + k * step + step / 2;
    if (step >= 9) {
      s += '<text x="' + cx.toFixed(1) + '" y="' + (base + 14) + '" text-anchor="middle" '
        + 'class="axis" style="font-size:9.5px' + (p.weekend ? ";fill:var(--med)" : "")
        + '">' + p.initial + "</text>";
    }
    if (label[k]) {
      var y = base + (step >= 9 ? 26 : 16);
      s += '<text x="' + cx.toFixed(1) + '" y="' + y + '" text-anchor="end" class="axis" '
        + 'transform="rotate(-55 ' + cx.toFixed(1) + " " + y + ')" style="font-size:10px">'
        + esc(p.dom + " " + p.mon) + "</text>";
    }
    if (p.first && k > 0) {
      var mx = (L + k * step).toFixed(1);
      s += '<line x1="' + mx + '" y1="' + (base - PH) + '" x2="' + mx + '" y2="' + (base + 4)
        + '" stroke="var(--line)" stroke-width="1" stroke-dasharray="2 3"/>';
    }
  });
  return s;
}

// Weekday x hour heatmap — replaces the old flat 24-bar chart with a richer
// view of the same `hours` cube: single-hue accent ramp, empty cells stay a
// visible neutral track rather than vanishing, so the grid shape always reads.
function heatmap(F) {
  var grid = [];
  for (var w = 0; w < 7; w++) grid.push(new Array(24).fill(0));
  var total = 0;
  agg(D.hours, HOURS, F, ["date", "hour"]).forEach(function (r) {
    var h = parseInt(r.hour, 10);
    if (isNaN(h) || h < 0 || h > 23) return;
    grid[parse(r.date).getUTCDay()][h] += r.turns;
    total += r.turns;
  });
  if (!total) return '<p class="empty">Nothing in this range.</p>';
  var peak = 1;
  grid.forEach(function (row) { row.forEach(function (v) { if (v > peak) peak = v; }); });

  var W = 720, L = 40, TOP = 18, CH = 17, GAP = 3, cw = (W - L - 8) / 24;
  var H = TOP + 7 * (CH + GAP) + 18;
  var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" preserveAspectRatio="xMinYMin meet">'
    + '<text x="' + (W - 4) + '" y="12" text-anchor="end" class="axis">'
    + "turns by weekday × hour, " + esc(CUR.tz_label) + "</text>";
  for (var w2 = 0; w2 < 7; w2++) {
    var y = TOP + w2 * (CH + GAP);
    s += '<text x="' + (L - 8) + '" y="' + (y + CH / 2 + 3.5).toFixed(1)
      + '" text-anchor="end" class="axis">' + DOW[w2] + "</text>";
    for (var h2 = 0; h2 < 24; h2++) {
      var v = grid[w2][h2], x = L + h2 * cw;
      var fill = v ? "var(--accent)" : "var(--track)";
      var op = v ? Math.max(0.15, v / peak).toFixed(2) : "1";
      s += '<rect class="heatcell" data-tt="' + esc(DOW[w2] + " " + String(h2).padStart(2, "0")
        + ":00 " + CUR.tz_label + " — " + num(v) + " turns") + '" x="' + x.toFixed(1) + '" y="' + y.toFixed(1)
        + '" width="' + Math.max(1, cw - 1.5).toFixed(1) + '" height="' + CH + '" rx="2" fill="'
        + fill + '" opacity="' + op + '"/>';
    }
  }
  var by = TOP + 7 * (CH + GAP) + 12;
  for (var h3 = 0; h3 < 24; h3 += 3) {
    s += '<text x="' + (L + h3 * cw + cw / 2).toFixed(1) + '" y="' + by.toFixed(1)
      + '" text-anchor="middle" class="axis">' + String(h3).padStart(2, "0") + "</text>";
  }
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
      return {turns_per_session: null, tool_calls_per_turn: null, model_switch: null};
    }
    var turns = 0, calls = 0, switched = 0;
    list.forEach(function (s) {
      turns += s.turns || 0;
      calls += s.tool_calls || 0;
      if ((s.models || []).length > 1) switched++;
    });
    return {turns_per_session: turns / list.length,
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
  var ys = idx.map(function (i) { return vals[i]; });
  var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys);
  if (hi === lo) { hi += 1; lo -= 1; }
  var step = (W - PAD * 2) / Math.max(1, idx.length - 1);
  var pts = idx.map(function (i, k) {
    var x = PAD + k * step, y = H - PAD - (vals[i] - lo) / (hi - lo) * (H - PAD * 2);
    return x.toFixed(1) + "," + y.toFixed(1);
  });
  var last = pts[pts.length - 1].split(",");
  return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMinYMin meet" role="img">'
    + '<polyline points="' + pts.join(" ") + '" fill="none" stroke="var(--accent)" '
    + 'stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>'
    + '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="2.6" fill="var(--accent)"/></svg>';
}
function sparkCard(title, infoKey, vals, fmt) {
  var rolled = rollingAvg(vals, 7), lastVal = lastNonNull(rolled);
  return '<div class="spark"><div class="sk">' + esc(title) + info(infoKey) + "</div>"
    + '<div class="sv">' + (lastVal == null ? "—" : esc(fmt(lastVal))) + "</div>"
    + sparkline(rolled) + "</div>";
}
function behavioralTrends(F) {
  var days = span(F.from, F.to), series = sessionSeries(pickSessions(F), days);
  var html = sparkCard("Turns / session", "turnsPerSession",
      series.map(function (r) { return r.turns_per_session; }),
      function (v) { return v.toFixed(1); })
    + sparkCard("Tool calls / turn", "toolCallsPerTurn",
      series.map(function (r) { return r.tool_calls_per_turn; }),
      function (v) { return v.toFixed(2); })
    + sparkCard("Model-switch share", "modelSwitchShare",
      series.map(function (r) { return r.model_switch; }),
      function (v) { return v.toFixed(0) + "%"; });
  return '<div class="sparks">' + html + "</div>";
}

/* ---- panels ------------------------------------------------------------ */
var DAILY = [{k: "turns", n: "Turns", f: num}, {k: "cost", n: "Est. cost", f: usd},
             {k: "output", n: "Output", f: num}, {k: "tool_calls", n: "Tool calls", f: num}];
var dailyMetric = "turns";
var selectedDay = null;  // click a bar in "Daily rhythm" to drill every panel into that day

function kpiCards(t, sessions) {
  var days = Math.max(1, t.days);
  var read = t.cache_read + t.cache_create + t.input;
  var ratio = (t.writes || t.reads)
    ? (t.writes / Math.max(t.reads, 1)).toFixed(2) + "×" : "—";
  var tps = turnsPerSession(t, sessions), tcpt = toolCallsPerTurn(t);
  var msw = modelSwitchShare(sessions), med = medianMinutes(sessions);
  // Behavioral signals lead; raw volume (turns, output tokens) no longer gets
  // a top-of-page tile of its own — it's still visible in the panels below.
  var cards = [
    [usd(t.cost), "Estimated spend" + info("spend"),
     "~" + usd(t.cost / days) + "/active day · notional on a seat plan", true],
    [tps.toFixed(1), "Turns / session" + info("turnsPerSession"),
     sessions.length ? "median " + med.toFixed(0) + "m per session" : "no sessions yet"],
    [pctOf(t.cache_read, read).toFixed(1) + "%", "Served from cache" + info("cache"),
     "the share of read tokens that cost 0.1× instead of 1×"],
    [tcpt.toFixed(2), "Tool calls / turn" + info("toolCallsPerTurn"),
     tcpt >= 0.5 ? "agentic use" : "mostly conversational"],
    [msw.toFixed(0) + "%", "Model-switch share" + info("modelSwitchShare"),
     "of " + num(sessions.length) + " sessions used more than one model"],
    [ratio, "Write / read" + info("writeRead"),
     num(t.writes) + " edits per " + num(t.reads) + " lookups"]
  ];
  return cards.map(function (c) {
    return '<div class="kpi' + (c[3] ? " lead" : "") + '"><div class="v">' + c[0]
      + '</div><div class="k">' + c[1] + '</div><div class="n">' + esc(c[2]) + "</div></div>";
  }).join("");
}

function sessionsTable(rows) {
  rows = rows.slice().sort(function (a, b) { return b.output - a.output; }).slice(0, 15);
  if (!rows.length) return '<p class="empty">No sessions in this range.</p>';
  var peak = Math.max.apply(null, rows.map(function (r) { return r.peak_context || 0; })) || 1;
  var body = rows.map(function (r) {
    var ratio = (r.writes || r.reads) ? r.writes + "/" + r.reads : "—";
    var tag = r.surface ? ' <span class="tag">' + esc(r.surface) + "</span>" : "";
    return "<tr><td>" + esc(r.repo || "unattributed") + tag + '<br><span class="axis">'
      + esc(r.session) + " · " + esc((r.start || "").slice(0, 10)) + " · "
      + esc(r.provider) + "</span></td>"
      + '<td class="n">' + esc(num(r.turns)) + "</td>"
      + '<td class="n">' + esc(num(r.output)) + "</td>"
      + '<td class="n">' + esc(usd(r.cost)) + "</td>"
      + '<td class="n">' + esc(ratio) + "</td>"
      + '<td><div class="bar"><i style="width:' + pctOf(r.peak_context, peak).toFixed(0)
      + '%"></i></div><span class="axis">' + esc(num(r.peak_context)) + "</span></td></tr>";
  }).join("");
  return '<div class="scroll"><table><thead><tr><th>Session</th><th>Turns</th>'
    + "<th>Output</th><th>Est. cost</th><th>Writes/reads</th><th>Peak context</th>"
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

  var label = {peak: "Peak hours", "off-peak": "Off-peak hours"};
  $("phase").innerHTML = bars(
    timed.sort(byCost),
    function (r) { return label[r.phase] || r.phase; },
    function (r) { return r.cost; }, usd);

  var pct = pctOf(peakCost, total);
  $("phaseNote").innerHTML = "<strong>" + pct.toFixed(1) + "%</strong> of time-priced spend "
    + "landed in a peak window. Running the identical turns off-peak would have cost "
    + esc(usd(floor)) + " instead of " + esc(usd(total)) + " — a premium of <strong>"
    + esc(usd(premium)) + "</strong> for the timing."
    + (premium > 0 ? " Batch work — test generation, migrations, doc sweeps — is the part "
        + "that does not need you watching, and so the part worth moving." : "");
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

function draw() {
  var F = state();
  if (F.from > F.to) { F.from = F.to; $("from").value = F.to; }
  if (F.day && (F.day < F.from || F.day > F.to)) { F.day = selectedDay = null; }
  var DF = dayFilter(F);
  var t = totals(DF), ses = pickSessions(DF), spec = DAILY.filter(function (m) {
    return m.k === dailyMetric;
  })[0];

  $("kpis").innerHTML = kpiCards(t, ses);
  var slice = [F.provider === "All" ? "all providers" : F.provider,
               F.lane === "All" ? "all lanes" : F.lane + " lane",
               F.repo === "All" ? "all repositories" : F.repo].join(" · ");
  $("scope").textContent = F.from + " → " + F.to + "  ·  " + slice
    + "  ·  " + num(t.turns) + " turns, " + usd(t.cost) + " estimated"
    + (F.day ? "  ·  drilled into " + longDate(F.day) + " (click it again to clear)" : "");

  var byDate = {};
  agg(D.cube, CUBE, F, ["date"]).forEach(function (r) { byDate[r.date] = r[dailyMetric]; });
  $("daily").innerHTML = daily(span(F.from, F.to), byDate, spec.n.toLowerCase(), spec.f, F.day);
  $("dailyLegend").innerHTML = '<i></i>' + esc(spec.n) + " per day<i class='avg'></i>7-day mean";

  var repos = agg(D.cube, CUBE, DF, ["repo"], "repo").sort(byCost);
  $("repos").innerHTML = bars(repos.slice(0, 12), function (r) { return r.repo; },
                              function (r) { return r.cost; }, usd, true);

  var focus = F.repo !== "All" ? F.repo : (repos[0] || {}).repo;
  var inside = agg(D.cube, CUBE, DF, ["repo", "surface"], "repo")
    .filter(function (r) { return r.repo === focus; }).sort(byCost);
  $("surfaceTitle").textContent = focus ? "Inside " + focus : "Inside";
  $("surfaces").innerHTML = bars(inside.slice(0, 12), function (r) { return r.surface; },
                                 function (r) { return r.cost; }, usd);
  $("surfaceNote").textContent = F.repo === "All" && focus
    ? "Showing the busiest repository. Pick one on the left to hold it."
    : "";

  $("models").innerHTML = bars(agg(D.cube, CUBE, DF, ["model"]).sort(byOutput),
    function (r) { return r.model; }, function (r) { return r.output; }, num);
  $("efforts").innerHTML = bars(agg(D.cube, CUBE, DF, ["effort"])
    .sort(function (a, b) { return b.turns - a.turns; }),
    function (r) { return r.effort; }, function (r) { return r.turns; }, num);
  $("hours").innerHTML = heatmap(DF);
  $("tools").innerHTML = bars(agg(D.tools, TOOLS, DF, ["tool"])
    .sort(function (a, b) { return b.calls - a.calls; }).slice(0, 10),
    function (r) { return r.tool; }, function (r) { return r.calls; }, num);
  drawPhase(DF);
  $("agents").innerHTML = bars(agg(D.cube, CUBE, DF, ["agent"]).filter(function (r) {
    return r.agent !== "main thread" && r.agent !== "unattributed";
  }).sort(byOutput).slice(0, 8), function (r) { return r.agent; },
    function (r) { return r.output; }, num);
  $("agentsNote").textContent = t.sub_turns
    ? pctOf(t.sub_output, t.output).toFixed(1) + "% of output came from "
      + num(t.sub_turns) + " delegated turns."
    : "No delegated turns in this scope.";
  $("sessions").innerHTML = sessionsTable(ses);

  // Trends always span the full selected range, ignoring the day drill-down
  // above it — a single day has no week-over-week shape to show.
  $("trends").innerHTML = behavioralTrends(F);
}

/* ---- controls ----------------------------------------------------------- */
var FIRST = (D.window.first || "").slice(0, 10), LAST = (D.window.last || "").slice(0, 10);
function later(a, b) { return a > b ? a : b; }

var PRESETS = [
  {id: "7d",  label: "7 days",     from: function () { return later(shift(LAST, -6), FIRST); }},
  {id: "30d", label: "30 days",    from: function () { return later(shift(LAST, -29), FIRST); }},
  {id: "mtd", label: "This month", from: function () { return later(LAST.slice(0, 8) + "01", FIRST); }},
  {id: "90d", label: "90 days",    from: function () { return later(shift(LAST, -89), FIRST); }},
  {id: "all", label: "All",        from: function () { return FIRST; }}
];

function markPreset(id) {
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
function fillSelect(el, rows, key) {
  el.innerHTML = '<option value="All">All</option>' + rows.map(function (r) {
    return '<option value="' + esc(r[key]) + '">' + esc(r[key]) + "</option>";
  }).join("");
}

function init() {
  var hn = $("hoursNote");
  if (hn) hn.textContent = "Weekday \u00d7 hour, in " + CUR.tz_label
    + " \u2014 the timezone the work actually happens in, not wherever the collecting "
    + "machine's clock is set.";
  $("span").textContent = FIRST + " → " + LAST + " · " + D.window.days
    + " active days · " + D.by_provider.map(function (p) { return p.provider; }).join(" + ");

  $("presets").innerHTML = PRESETS.map(function (p) {
    return '<button type="button" id="p-' + p.id + '">' + esc(p.label) + "</button>";
  }).join("");
  PRESETS.forEach(function (p) {
    $("p-" + p.id).addEventListener("click", function () { applyPreset(p); });
  });

  ["from", "to"].forEach(function (id) {
    $(id).min = FIRST; $(id).max = LAST;
    $(id).addEventListener("change", function () { markPreset(null); draw(); });
  });

  fillSelect($("provider"), D.by_provider, "provider");
  fillSelect($("lane"), D.by_lane, "lane");
  fillSelect($("repo"), D.by_repo, "repo");
  ["provider", "lane", "repo"].forEach(function (id) {
    $(id).addEventListener("change", draw);
  });

  $("dailyMetric").innerHTML = DAILY.map(function (m) {
    return '<button type="button" data-metric="' + m.k + '" aria-pressed="'
      + (m.k === dailyMetric) + '">' + esc(m.n) + "</button>";
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

  initTooltip();

  // A month is the default view; fall back to everything when there is less.
  applyPreset(span(FIRST, LAST).length > 30 ? PRESETS[1] : PRESETS[4]);
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

/* Interface strings only. Findings and the method notes are generated by the
   engine in English and stay that way — see the header of assets/i18n.js for
   why, and note_en, which says so on the page in any other language. */
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

    // Only shown when the interface is not in the language the engine writes.
    each(".lang-note", function (el) { el.hidden = (lang === "en"); });

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

initTheme();
initLang();
init();
})();
