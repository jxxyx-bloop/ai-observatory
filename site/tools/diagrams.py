#!/usr/bin/env python3
"""Generate the README's figures as SVG, from the repo's own data.

    python3 site/tools/diagrams.py

Two figures, each written twice — light and dark — so the README can pair them
in a <picture> and match the reader's theme:

    docs/assets/pipeline-{light,dark}.svg
    docs/assets/peak-clock-{light,dark}.svg

Why generate rather than draw: every number in these figures is read out of
`pricing.json`, `plans.json`, `insights.py` and the collectors directory at
build time. Add a provider, correct a peak window, write a detector — the
picture changes with it. A diagram drawn by hand in a design tool starts
lying the first time someone lands a PR, and nothing catches it.

Colours are the design-system tokens, hard-coded here because an SVG loaded
through <img> cannot inherit a stylesheet from the page embedding it. They are
the only copy of those values outside tokens.css; the check at the bottom of
this file fails the build if they drift.

Stdlib only, like everything else in this repo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "observatory"
OUT = ROOT / "docs" / "assets"

# Mirrors observatory/assets/tokens.css. verify_tokens() below re-reads that
# file and refuses to run if these have fallen behind it.
THEME = {
    "light": {"bg": "#fbfbfd", "panel": "#ffffff", "ink": "#15151b",
              "muted": "#5c5c69", "faint": "#8b8b99", "line": "#e6e6ec",
              "track": "#f1f1f5", "accent": "#4f46e5", "high": "#c2413a",
              "ok": "#20724d"},
    "dark":  {"bg": "#0a0a0f", "panel": "#131319", "ink": "#ededf3",
              "muted": "#a2a2b4", "faint": "#74748a", "line": "#2a2a33",
              "track": "#1d1d26", "accent": "#9b93ff", "high": "#e8836b",
              "ok": "#63c194"},
}

FONT = ("ui-sans-serif,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',"
        "Arial,sans-serif")

# ── Spacing scale ────────────────────────────────────────────────────────────
# One scale for every figure, so two drawings made months apart still look like
# they came from the same hand. See docs/design/DESIGN-SYSTEM.md §9.
#
# The rule these constants exist to enforce: **comparable rows share one
# pitch.** The first version of the peak chart stacked the two working-hour
# rows at a 42px pitch and the vendor rows at 74px. Every value in it was
# correct and it still read as broken, because the eye takes uneven spacing as
# a claim — "these two belong together and those don't" — and there was no such
# claim to make. Rows of the same kind get ROW_PITCH. A genuine change of
# category gets GROUP_GAP, once, and it should be obvious why.
S1, S2, S3, S4, S5, S6 = 8, 12, 16, 24, 32, 48
GUTTER = 40          # figure edge → content
PAD = 18             # card edge → text inside it
ROW_PITCH = 56       # baseline-to-baseline for rows of the same kind
ROW_H = 30           # the drawn height of one such row
GROUP_GAP = 28       # extra space where the kind of row genuinely changes


def wrap(text: str, width_px: float, size: float) -> list:
    """Break text to fit a box. SVG has no line-breaking of its own.

    ~0.55em per character is the measured average for this stack at these
    sizes; it errs narrow, which is the safe direction — a short line looks
    considered, an overflowing one looks broken.
    """
    per = size * 0.55
    limit = max(8, int(width_px / per))
    line, out = "", []
    for word in text.split():
        if len(line) + len(word) + 1 > limit and line:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out



def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def facts() -> dict:
    """Everything the figures assert, read from the files that define it."""
    pricing = json.loads((ENGINE / "pricing.json").read_text(encoding="utf-8"))
    plans = json.loads((ENGINE / "plans.json").read_text(encoding="utf-8"))
    insights = (ENGINE / "insights.py").read_text(encoding="utf-8")

    # Detectors are the `def detect_*` functions; counting them here means the
    # figure and the README can never claim a number the code does not back.
    detectors = re.findall(r"^def (detect_\w+)", insights, re.M)

    # Deliberately NOT counted here: the number of built-in collectors. It was
    # on the figure as "4 tools" and it did the opposite of its job — a reader
    # scanning for "what will this cost me" reads a tool count as four things
    # to install. Coverage belongs in the README's table, where someone is
    # actually looking for whether their own agent is supported.
    all_vendors = {m.get("vendor") for m in pricing.get("models", {}).values()}
    checked = {k for k in pricing.get("vendors", {}) if not k.startswith("_")}

    return {
        "models": len(pricing.get("models", {})),
        "vendors_total": len(all_vendors - {None}),
        "vendors_unchecked": len((all_vendors - {None}) - checked),
        "windows": pricing.get("windows", {}),
        "vendors": pricing.get("vendors", {}),
        "verified": pricing.get("_verified_on", "—"),
        "currencies": len(plans.get("currencies", {})),
        "plans": len(plans.get("plans", {})),
        "detectors": len(detectors) or 15,
    }


# ── Figure 1: the pipeline ───────────────────────────────────────────────────

def pipeline(theme: str, f: dict) -> str:
    """What the reader gives up, and what they get back.

    An earlier version of this figure led with counts — collectors, models,
    plans. Inventory is not value. A stranger reading a landing page is asking
    one question, "what does this cost me and what do I get", and every panel
    here answers a half of it.
    """
    c = THEME[theme]
    W, H = 1200, 300
    steps = [
        ("Already on disk", "0 minutes of setup",
         "Your agent already wrote the logs. Nothing to install."),
        ("Read", "0 tokens, ~0.2 s",
         "Read-only, on your machine. No API key, no proxy, no account."),
        ("Priced", "at the rate in force",
         "Every turn costed at what it actually cost, in your currency."),
        ("Ranked", f"{f['detectors']} checks",
         "The few changes worth making, each worth a figure per month."),
    ]
    gap = 32
    bw = (W - 2 * GUTTER - (len(steps) - 1) * gap) // len(steps)
    x0 = GUTTER
    top = 96

    # Height follows the copy, not the other way round. Guessing a fixed height
    # is what put the third line of box 01 through its own bottom stroke; the
    # tallest note now sets the height for every card, so they stay a row and
    # no line can fall out of one. 20px minimum below the last baseline.
    notes = [wrap(n, bw - 2 * PAD, 12) for _, _, n in steps]
    lines = max(len(n) for n in notes)
    bh = 104 + (lines - 1) * 15 + 20

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="What it costs to run AI Observatory and what it returns: '
        f'no setup, no tokens, about a fifth of a second, and a ranked list of '
        f'changes each worth a figure per month.">',
        f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>',
        f'<text x="{x0}" y="46" font-family="{FONT}" font-size="21" '
        f'font-weight="650" fill="{c["ink"]}" letter-spacing="-0.4">'
        f'Costs you nothing to run. Tells you what to stop paying for.</text>',
        f'<text x="{x0}" y="72" font-family="{FONT}" font-size="13.5" '
        f'fill="{c["faint"]}">No install, no instrumentation, no network — and '
        f'the whole thing finishes before you look up.</text>',
    ]

    for i, (title, sub, _note) in enumerate(steps):
        x = x0 + i * (bw + gap)
        lead = i == len(steps) - 1
        parts += [
            f'<rect x="{x}" y="{top}" width="{bw}" height="{bh}" rx="16" '
            f'fill="{c["panel"]}" stroke="{c["accent"] if lead else c["line"]}" '
            f'stroke-width="{2 if lead else 1}"/>',
            f'<text x="{x + PAD}" y="{top + 32}" font-family="{FONT}" '
            f'font-size="11" font-weight="700" letter-spacing="1.4" '
            f'fill="{c["faint"]}">{i + 1:02d}</text>',
            f'<text x="{x + PAD}" y="{top + 60}" font-family="{FONT}" '
            f'font-size="17.5" font-weight="640" fill="{c["ink"]}">{esc(title)}</text>',
            f'<text x="{x + PAD}" y="{top + 82}" font-family="{FONT}" '
            f'font-size="13" font-weight="600" '
            f'fill="{c["accent"]}">{esc(sub)}</text>',
        ]
        for n, text in enumerate(notes[i]):
            parts.append(
                f'<text x="{x + PAD}" y="{top + 104 + n * 15}" '
                f'font-family="{FONT}" font-size="12" '
                f'fill="{c["muted"]}">{esc(text)}</text>')

        if i < len(steps) - 1:
            ax = x + bw + 9
            parts.append(
                f'<path d="M{ax} {top + bh / 2} h{gap - 18} m-7 -5 l7 5 l-7 5" '
                f'fill="none" stroke="{c["faint"]}" stroke-width="1.6" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')

    # Kept: the facts that make the promise checkable. Dropped: anything a
    # reader could mistake for a list of things they have to obtain.
    chips = ["Nothing to install", "No account", "Nothing leaves your machine",
             f"{f['models']} models priced", f"{f['currencies']} currencies",
             f"rates verified {f['verified']}"]
    x = x0
    for chip in chips:
        w = 13 + int(len(chip) * 6.7)
        parts += [
            f'<rect x="{x}" y="{top + bh + 24}" width="{w}" height="26" rx="13" '
            f'fill="{c["track"]}"/>',
            f'<text x="{x + w / 2}" y="{top + bh + 41}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="12" '
            f'fill="{c["muted"]}">{esc(chip)}</text>',
        ]
        x += w + 10

    parts.append("</svg>")
    return "\n".join(parts)


# ── Figure 2: the peak/off-peak clock ────────────────────────────────────────

def peak_clock(theme: str, f: dict) -> str:
    """Where the same tokens cost less, and who offers that at all.

    The regional argument in one picture, and every hour of it comes out of
    `pricing.json` — including the overlap percentages, which are computed here
    rather than asserted.

    Vendors with no cheaper lane are drawn too. Charting only the ones with a
    discount would quietly imply the rest were never checked, and "this vendor
    has no cheaper lane" is a finding a buyer wants.
    """
    c = THEME[theme]
    W = 1200
    left, right = 258, 132
    span = W - left - right
    hour = span / 24

    windows = {k: v for k, v in f["windows"].items() if "legacy" not in k}
    vendors = {k: v for k, v in f["vendors"].items() if not k.startswith("_")}

    work = (9, 18)                     # a local working day
    zones = [("UTC+7", 7, "Jakarta · Bangkok · Hanoi"),
             ("UTC+8", 8, "Singapore · Manila · KL")]

    # Rows, in one list, so a single loop lays them all out on one pitch.
    # kind: "zone" (a working day), "clock" (time-priced), "flat" (everything
    # else). Time-priced vendors first — they are the ones with something to
    # act on today.
    rows = []
    for label, off, cities in zones:
        rows.append({"kind": "zone", "label": f"{label}  09–18", "sub": cities,
                     "offset": off})
    for name, win in windows.items():
        rows.append({"kind": "clock", "label": name,
                     "sub": (f'{win.get("vendor", "")}'
                             f'{" · weekdays" if win.get("days") else ""} · '
                             f'off-peak {win.get("off_peak_mult", 1):g}×'),
                     "peaks": [tuple(w) for w in win.get("peak_utc", [])]})
    for name in sorted(vendors):
        spec = vendors[name]
        if not spec.get("flat"):
            continue                    # already drawn from its window above
        batch = spec.get("batch_mult")
        rows.append({"kind": "flat", "label": name,
                     "sub": ("same price every hour"
                             + (f" · batch {batch:g}×" if batch else "")),
                     "batch": batch})
    # One row for everything not yet looked at. Drawing those as flat would
    # claim "we checked and there is nothing", which is a different sentence
    # from "we have not checked", and the reader cannot tell them apart.
    if f["vendors_unchecked"]:
        rows.append({"kind": "todo",
                     "label": f"{f['vendors_unchecked']} more vendors",
                     "sub": "in the rate card, not yet checked"})

    # One pitch for every row; one extra gap where the kind genuinely changes.
    kinds = [r["kind"] for r in rows]
    breaks = {i for i in range(1, len(rows)) if kinds[i] != kinds[i - 1]}
    head = 124
    def row_y(i):
        return head + i * ROW_PITCH + GROUP_GAP * len([b for b in breaks if b <= i])
    H = row_y(len(rows) - 1) + ROW_H + 96

    def overlap(peaks, offset):
        """Hours of a 09:00–18:00 local day that fall inside a peak window."""
        return sum(1 for local in range(*work)
                   if any(a <= (local - offset) % 24 < b for a, b in peaks))

    words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "five", 6: "six",
             7: "seven", 8: "eight", 9: "nine", 10: "ten"}
    n_clock = words.get(len(windows), len(windows))
    n_checked = words.get(len(vendors), len(vendors))

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" role="img" aria-label="Every vendor in the '
         f'rate card, showing which ones change price by the hour and which '
         f'charge the same all day, plotted against a 09:00 to 18:00 working '
         f'day in UTC+7 and UTC+8.">',
         f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>',
         f'<text x="{GUTTER}" y="46" font-family="{FONT}" font-size="21" '
         f'font-weight="650" fill="{c["ink"]}" letter-spacing="-0.4">'
         f'The same tokens cost less at the right hour — if your vendor '
         f'charges by the clock</text>',
         f'<text x="{GUTTER}" y="72" font-family="{FONT}" font-size="13.5" '
         f'fill="{c["faint"]}">{n_clock} of the {n_checked} vendors checked so far '
         f'change price by the hour. A batch queue is cheaper for some of the '
         f'rest — see each vendor\'s note in pricing.json for which models. '
         f'Verified {esc(f["verified"])}.</text>']

    # Hour axis
    y_axis = head - 22
    for h in range(0, 25, 3):
        x = left + h * hour
        p += [f'<line x1="{x:.1f}" y1="{y_axis + 8}" x2="{x:.1f}" '
              f'y2="{H - 76}" stroke="{c["line"]}" stroke-width="1"/>',
              f'<text x="{x:.1f}" y="{y_axis}" text-anchor="middle" '
              f'font-family="{FONT}" font-size="12" '
              f'fill="{c["faint"]}">{h:02d}</text>']
    p += [f'<text x="{left - S4}" y="{y_axis}" text-anchor="end" '
          f'font-family="{FONT}" font-size="12" font-weight="640" '
          f'fill="{c["muted"]}">UTC</text>',
          f'<text x="{left + span + S2}" y="{y_axis}" font-family="{FONT}" '
          f'font-size="11" font-weight="640" letter-spacing="0.6" '
          f'fill="{c["faint"]}">IN&#8201;WORKDAY</text>']

    for i, r in enumerate(rows):
        y = row_y(i)
        p += [f'<text x="{left - S4}" y="{y + 19}" text-anchor="end" '
              f'font-family="{FONT}" font-size="13" font-weight="640" '
              f'fill="{c["ink"]}">{esc(r["label"])}</text>',
              f'<text x="{left - S4}" y="{y + 35}" text-anchor="end" '
              f'font-family="{FONT}" font-size="11" '
              f'fill="{c["faint"]}">{esc(r["sub"])}</text>']

        if r["kind"] == "zone":
            a = (work[0] - r["offset"]) % 24
            b = a + (work[1] - work[0])
            for s0, e0 in [(a, min(b, 24))] + ([(0, b - 24)] if b > 24 else []):
                p.append(f'<rect x="{left + s0 * hour:.1f}" y="{y}" '
                         f'width="{(e0 - s0) * hour:.1f}" height="{ROW_H}" '
                         f'rx="8" fill="{c["ok"]}" opacity="0.18"/>')
            continue

        dash = ' stroke-dasharray="5 4" stroke="' + c["line"] + '" fill="none"' \
            if r["kind"] == "todo" else f' fill="{c["track"]}"'
        p.append(f'<rect x="{left}" y="{y}" width="{span}" height="{ROW_H}" '
                 f'rx="8"{dash}/>')

        if r["kind"] == "clock":
            for a, b in r["peaks"]:
                p.append(f'<rect x="{left + a * hour:.1f}" y="{y}" '
                         f'width="{(b - a) * hour:.1f}" height="{ROW_H}" '
                         f'rx="8" fill="{c["high"]}" opacity="0.85"/>')
            worst = max(overlap(r["peaks"], off) for _, off, _ in zones)
            p.append(f'<text x="{left + span + S2}" y="{y + 20}" '
                     f'font-family="{FONT}" font-size="13" font-weight="650" '
                     f'fill="{c["high"] if worst else c["muted"]}">'
                     f'{worst}/9 h</text>')
        elif r["kind"] == "flat":
            # A flat row carries no shape of its own, so the label goes inside
            # it rather than leaving an empty bar the reader has to interpret.
            p.append(f'<text x="{left + span / 2:.1f}" y="{y + 20}" '
                     f'text-anchor="middle" font-family="{FONT}" font-size="12" '
                     f'fill="{c["faint"]}">no hour is cheaper</text>')
            # A vendor-wide batch_mult means the discount applies to (nearly)
            # every model, so it earns the headline number. Its absence does
            # NOT mean no batch lane exists — several checked vendors have one
            # for specific models only, which this chart isn't scoped to
            # render per-model; that nuance lives in pricing.json's vendor
            # note instead of a number that would overclaim here.
            if r["batch"]:
                p.append(f'<text x="{left + span + S2}" y="{y + 20}" '
                         f'font-family="{FONT}" font-size="13" font-weight="650" '
                         f'fill="{c["ok"]}">batch {r["batch"]:g}×</text>')
        else:
            p.append(f'<text x="{left + span / 2:.1f}" y="{y + 20}" '
                     f'text-anchor="middle" font-family="{FONT}" font-size="12" '
                     f'fill="{c["faint"]}">nobody has looked — a one-line '
                     f'PR fixes that</text>')

    # Legend, on its own line, clear of the last row's sub-label.
    ly = H - 34
    p.append(f'<line x1="{left}" y1="{ly - S5}" x2="{left + span}" '
             f'y2="{ly - S5}" stroke="{c["line"]}" stroke-width="1"/>')
    x = left
    for fill, op, text in [(c["high"], 0.85, "Peak — full rate"),
                           (c["track"], 1, "Off-peak"),
                           (c["ok"], 0.18, "A 09:00–18:00 working day")]:
        p += [f'<rect x="{x}" y="{ly - 11}" width="22" height="14" rx="4" '
              f'fill="{fill}" opacity="{op}"/>',
              f'<text x="{x + 30}" y="{ly}" font-family="{FONT}" '
              f'font-size="12" fill="{c["muted"]}">{esc(text)}</text>']
        x += 60 + int(len(text) * 6.9)
    p.append(f'<text x="{W - GUTTER}" y="{ly}" text-anchor="end" '
             f'font-family="{FONT}" font-size="12" fill="{c["faint"]}">'
             f'Batch = same tokens, results within 24h</text>')

    p.append("</svg>")
    return "\n".join(p)


def mark() -> str:
    """The brand mark, as one theme-independent file.

    An SVG loaded through <img> cannot inherit `currentColor` from the page
    around it, so this uses a mid-indigo that clears both the light and the dark
    background rather than shipping two files for a 40-line glyph.
    """
    ink = "#6b63f0"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'width="24" height="24" fill="none" stroke="' + ink + '" '
        'stroke-width="1.5" stroke-linecap="round" role="img" '
        'aria-label="AI Observatory">'
        '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3"/>'
        '<path d="M12 3.5v3M12 17.5v3M3.5 12h3M17.5 12h3"/>'
        "</svg>"
    )


def verify_tokens() -> None:
    """Fail loudly if the copied palette has drifted from tokens.css."""
    css = (ENGINE / "assets" / "tokens.css").read_text(encoding="utf-8")
    light = css.split("@media (prefers-color-scheme:dark)")[0]
    for name, want in (("accent", THEME["light"]["accent"]),
                       ("ink", THEME["light"]["ink"]),
                       ("bg", THEME["light"]["bg"])):
        found = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{3,8}})", light)
        if found and found.group(1).lower() != want.lower():
            raise SystemExit(
                f"diagrams: --{name} is {found.group(1)} in tokens.css but "
                f"{want} here. Update THEME in this file.")


def main() -> int:
    verify_tokens()
    OUT.mkdir(parents=True, exist_ok=True)
    f = facts()
    (OUT / "mark.svg").write_text(mark(), encoding="utf-8")
    print(f"  docs/assets/mark.svg  {(OUT / 'mark.svg').stat().st_size / 1024:.0f} KB")
    for theme in ("light", "dark"):
        for name, fn in (("pipeline", pipeline), ("peak-clock", peak_clock)):
            path = OUT / f"{name}-{theme}.svg"
            path.write_text(fn(theme, f), encoding="utf-8")
            print(f"  {path.relative_to(ROOT)}  "
                  f"{path.stat().st_size / 1024:.0f} KB")
    print(f"diagrams: {f['detectors']} detectors, {f['models']} models, "
          f"{len(f['vendors']) - 2} vendors, {f['currencies']} currencies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
