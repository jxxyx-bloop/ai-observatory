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


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def facts() -> dict:
    """Everything the figures assert, read from the files that define it."""
    pricing = json.loads((ENGINE / "pricing.json").read_text(encoding="utf-8"))
    plans = json.loads((ENGINE / "plans.json").read_text(encoding="utf-8"))
    insights = (ENGINE / "insights.py").read_text(encoding="utf-8")

    collectors = sorted(
        p.stem for p in (ENGINE / "collectors").glob("*.py")
        if p.stem not in {"__init__", "base", "generic"}
    )
    specs = sorted(p.stem for p in (ENGINE / "collectors" / "specs").glob("*.json"))
    # Detectors are the `def detect_*` functions; counting them here means the
    # figure and the README can never claim a number the code does not back.
    detectors = re.findall(r"^def (detect_\w+)", insights, re.M)

    return {
        "collectors": collectors,
        "specs": specs,
        "models": len(pricing.get("models", {})),
        "windows": pricing.get("windows", {}),
        "verified": pricing.get("_verified_on", "—"),
        "currencies": len(plans.get("currencies", {})),
        "plans": len(plans.get("plans", {})),
        "detectors": len(detectors) or 15,
    }


# ── Figure 1: the pipeline ───────────────────────────────────────────────────

def pipeline(theme: str, f: dict) -> str:
    c = THEME[theme]
    W, H = 1200, 300
    steps = [
        ("Transcripts", f"{len(f['collectors'])} tools, on disk",
         "Files your agent already wrote"),
        ("Collect", "read-only, ~0.2 s", "Zero tokens. No API, no proxy"),
        ("Normalise", "counts only", "No prompts, code or paths stored"),
        ("Detect", f"{f['detectors']} checks",
         f"Priced from {f['models']} models, {f['currencies']} currencies"),
        ("Decide", "ranked list", "Evidence, action, value per month"),
    ]
    bw, gap = 200, 40
    x0 = (W - (len(steps) * bw + (len(steps) - 1) * gap)) // 2
    top, bh = 84, 128

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="How AI Observatory turns local agent transcripts into a '
        f'ranked list of changes: {" then ".join(s[0] for s in steps)}.">',
        f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>',
        f'<text x="{x0}" y="42" font-family="{FONT}" font-size="19" '
        f'font-weight="650" fill="{c["ink"]}" letter-spacing="-0.3">'
        f'From files you already have to a decision you can act on</text>',
        f'<text x="{x0}" y="65" font-family="{FONT}" font-size="13" '
        f'fill="{c["faint"]}">Nothing on this line touches the network.</text>',
    ]

    for i, (title, sub, note) in enumerate(steps):
        x = x0 + i * (bw + gap)
        lead = i == len(steps) - 1
        parts += [
            f'<rect x="{x}" y="{top}" width="{bw}" height="{bh}" rx="14" '
            f'fill="{c["panel"]}" stroke="{c["accent"] if lead else c["line"]}" '
            f'stroke-width="{2 if lead else 1}"/>',
            f'<text x="{x + 18}" y="{top + 30}" font-family="{FONT}" '
            f'font-size="11" font-weight="700" letter-spacing="1.4" '
            f'fill="{c["faint"]}">{i + 1:02d}</text>',
            f'<text x="{x + 18}" y="{top + 58}" font-family="{FONT}" '
            f'font-size="17" font-weight="640" fill="{c["ink"]}">{esc(title)}</text>',
            f'<text x="{x + 18}" y="{top + 80}" font-family="{FONT}" '
            f'font-size="13" font-weight="600" '
            f'fill="{c["accent"]}">{esc(sub)}</text>',
        ]
        # Wrap the note by hand: ~26 characters is what fits inside the box at
        # 12px, and an SVG has no line-breaking of its own.
        line, lines = "", []
        for word in note.split():
            if len(line) + len(word) + 1 > 26:
                lines.append(line); line = word
            else:
                line = f"{line} {word}".strip()
        lines.append(line)
        for n, text in enumerate(lines[:2]):
            parts.append(
                f'<text x="{x + 18}" y="{top + 102 + n * 16}" '
                f'font-family="{FONT}" font-size="12" '
                f'fill="{c["muted"]}">{esc(text)}</text>')

        if i < len(steps) - 1:
            ax = x + bw + 10
            parts.append(
                f'<path d="M{ax} {top + bh / 2} h{gap - 20} m-7 -5 l7 5 l-7 5" '
                f'fill="none" stroke="{c["faint"]}" stroke-width="1.6" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')

    chips = [f"{len(f['collectors'])} built-in collectors",
             "+ any tool via one JSON spec",
             f"{f['models']} models priced",
             f"{f['plans']} plans",
             f"{f['currencies']} currencies",
             f"rates verified {f['verified']}"]
    x = x0
    for chip in chips:
        w = 11 + int(len(chip) * 6.7)
        parts += [
            f'<rect x="{x}" y="248" width="{w}" height="26" rx="13" '
            f'fill="{c["track"]}"/>',
            f'<text x="{x + w / 2}" y="265" text-anchor="middle" '
            f'font-family="{FONT}" font-size="12" '
            f'fill="{c["muted"]}">{esc(chip)}</text>',
        ]
        x += w + 10

    parts.append("</svg>")
    return "\n".join(parts)


# ── Figure 2: the peak/off-peak clock ────────────────────────────────────────

def peak_clock(theme: str, f: dict) -> str:
    """Where a published peak window lands in a Southeast Asian working day.

    The whole regional argument in one picture, and every hour of it comes out
    of `pricing.json` — including the overlap percentages, which are computed
    here rather than asserted.
    """
    c = THEME[theme]
    W = 1200
    left, right = 252, 96
    span = W - left - right
    hour = span / 24
    rows = [(k, v) for k, v in f["windows"].items() if "legacy" not in k]
    H = 150 + len(rows) * 74 + 128

    work = (9, 18)                     # a local working day
    zones = [("UTC+7", 7, "Jakarta · Bangkok · Hanoi"),
             ("UTC+8", 8, "Singapore · Manila · KL")]

    def overlap(peaks, offset):
        """Hours of a 09:00–18:00 local day that fall inside a peak window."""
        hits = 0
        for local in range(work[0], work[1]):
            utc = (local - offset) % 24
            if any(a <= utc < b for a, b in peaks):
                hits += 1
        return hits

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" role="img" aria-label="Published peak '
         f'pricing windows for time-priced vendors, plotted against a 09:00 to '
         f'18:00 working day in UTC+7 and UTC+8.">',
         f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>',
         f'<text x="{left}" y="40" font-family="{FONT}" font-size="19" '
         f'font-weight="650" fill="{c["ink"]}" letter-spacing="-0.3">'
         f'Peak pricing lands in the middle of a Southeast Asian workday</text>',
         f'<text x="{left}" y="63" font-family="{FONT}" font-size="13" '
         f'fill="{c["faint"]}">Same tokens, up to twice the price, decided by '
         f'the clock. Windows from pricing.json — verified {esc(f["verified"])}.</text>']

    # Hour axis
    y_axis = 96
    for h in range(0, 25, 3):
        x = left + h * hour
        p += [f'<line x1="{x:.1f}" y1="{y_axis + 6}" x2="{x:.1f}" '
              f'y2="{H - 74}" stroke="{c["line"]}" stroke-width="1"/>',
              f'<text x="{x:.1f}" y="{y_axis}" text-anchor="middle" '
              f'font-family="{FONT}" font-size="12" '
              f'fill="{c["faint"]}">{h:02d}</text>']
    p.append(f'<text x="{left - 20}" y="{y_axis}" text-anchor="end" '
             f'font-family="{FONT}" font-size="12" font-weight="640" '
             f'fill="{c["muted"]}">UTC</text>')
    # Header for the right-hand column, so the number below needs no caption
    # crowded in beside the legend.
    p.append(f'<text x="{left + span + 12}" y="{y_axis}" '
             f'font-family="{FONT}" font-size="11" font-weight="640" '
             f'letter-spacing="0.6" fill="{c["faint"]}">IN&#8201;WORKDAY</text>')

    # Working-day bands, one per zone
    y = y_axis + 22
    for label, off, cities in zones:
        a = (work[0] - off) % 24
        b = a + (work[1] - work[0])
        p += [f'<text x="{left - 14}" y="{y + 18}" text-anchor="end" '
              f'font-family="{FONT}" font-size="13" font-weight="640" '
              f'fill="{c["ink"]}">{esc(label)} 09–18</text>',
              f'<text x="{left - 14}" y="{y + 34}" text-anchor="end" '
              f'font-family="{FONT}" font-size="11" '
              f'fill="{c["faint"]}">{esc(cities)}</text>']
        for s, e in ([(a, min(b, 24))] + ([(0, b - 24)] if b > 24 else [])):
            p.append(f'<rect x="{left + s * hour:.1f}" y="{y}" '
                     f'width="{(e - s) * hour:.1f}" height="26" rx="6" '
                     f'fill="{c["ok"]}" opacity="0.18"/>')
        y += 42

    # One row per published window
    y += 10
    for name, win in rows:
        peaks = [tuple(w) for w in win.get("peak_utc", [])]
        days = win.get("days")
        off_mult = win.get("off_peak_mult", 1)
        p += [f'<text x="{left - 14}" y="{y + 20}" text-anchor="end" '
              f'font-family="{FONT}" font-size="13" font-weight="640" '
              f'fill="{c["ink"]}">{esc(name)}</text>',
              f'<text x="{left - 14}" y="{y + 37}" text-anchor="end" '
              f'font-family="{FONT}" font-size="11" fill="{c["faint"]}">'
              f'{esc(win.get("vendor", ""))}'
              f'{" · weekdays" if days else ""} · off-peak '
              f'{off_mult:g}×</text>',
              f'<rect x="{left}" y="{y}" width="{span}" height="30" rx="8" '
              f'fill="{c["track"]}"/>']
        for a, b in peaks:
            p.append(f'<rect x="{left + a * hour:.1f}" y="{y}" '
                     f'width="{(b - a) * hour:.1f}" height="30" rx="8" '
                     f'fill="{c["high"]}" opacity="0.85"/>')
        hits = [overlap(peaks, off) for _, off, _ in zones]
        worst = max(hits)
        p.append(f'<text x="{left + span + 12}" y="{y + 20}" '
                 f'font-family="{FONT}" font-size="13" font-weight="650" '
                 f'fill="{c["high"] if worst else c["muted"]}">'
                 f'{worst}/9 h</text>')
        y += 74

    # Legend
    ly = H - 34
    p.append(f'<line x1="{left}" y1="{ly - 34}" x2="{left + span}" '
             f'y2="{ly - 34}" stroke="{c["line"]}" stroke-width="1"/>')
    x = left
    for fill, op, text in [(c["high"], 0.85, "Peak — full rate"),
                           (c["track"], 1, "Off-peak"),
                           (c["ok"], 0.18, "A 09:00–18:00 working day")]:
        p += [f'<rect x="{x}" y="{ly - 11}" width="22" height="14" rx="4" '
              f'fill="{fill}" opacity="{op}"/>',
              f'<text x="{x + 30}" y="{ly}" font-family="{FONT}" '
              f'font-size="12" fill="{c["muted"]}">{esc(text)}</text>']
        x += 60 + int(len(text) * 6.9)

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
          f"{len(f['collectors'])} collectors, {f['currencies']} currencies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
