"""Standalone HTML renderer.

Emits one self-contained file: no CDN, no external fonts, no network calls, no
tracking, no analytics. The digest is inlined so the page opens from `file://`
and survives being copied or archived on its own.

Two tiers of chart. Findings are rendered server-side because they are computed
over the whole window and never change. Everything else is drawn in the browser
from the fact cube, so a date range or a repo filter re-aggregates instantly
without a server or a second file. Charts are hand-built inline SVG with labels
in their own gutters, so nothing can overflow or collide regardless of the data.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ASSETS = Path(__file__).with_name("assets")

SEV_COLOR = {"high": "var(--high)", "medium": "var(--med)",
             "low": "var(--low)", "info": "var(--info)"}


def esc(v) -> str:
    return html.escape(str(v if v is not None else "—"), quote=True)


def usd(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    return f"${n:,.0f}" if abs(n) >= 100 else f"${n:,.2f}"


def findings_html(d: dict) -> str:
    fs = d.get("findings") or []
    if not fs:
        return "<div class='panel'><p class='sub'>No findings yet — collect more days of usage.</p></div>"
    out = []
    for f in fs:
        c = SEV_COLOR.get(f["severity"], "var(--low)")
        saving = f.get("est_monthly_saving_usd")
        save = f'<span class="save">≈{usd(saving)}/mo</span>' if saving else ""
        meta = f'<p class="meta">{esc(f["demoted"])}</p>' if f.get("demoted") else ""
        out.append(
            f'<div class="find" style="--c:{c}">'
            f'<div class="top"><span class="sev">{esc(f["severity"])}</span>'
            f'<span class="ttl">{esc(f["title"])}</span>{save}</div>'
            f'<p>{esc(f["finding"])}</p>'
            f'<p class="act">{esc(f["action"])}</p>'
            f'{meta}<p class="meta">Confidence: {esc(f.get("confidence", "—"))}</p></div>'
        )
    return "".join(out)


def render(digest: dict) -> str:
    """Assemble the page from the templates in `engine/assets/`."""
    page = (ASSETS / "page.html").read_text(encoding="utf-8")
    return (
        page.replace("/*CSS*/", (ASSETS / "app.css").read_text(encoding="utf-8"))
            .replace("/*JS*/", (ASSETS / "app.js").read_text(encoding="utf-8"))
            .replace("<!--FINDINGS-->", findings_html(digest))
            .replace("<!--VERIFIED-->", esc(digest.get("pricing_verified_on") or "—"))
            .replace("<!--GENERATED-->",
                     esc((digest.get("generated_at") or "")[:16].replace("T", " ")))
            .replace("/*PAYLOAD*/",
                     json.dumps(digest, separators=(",", ":")).replace("</", "<\\/"))
    )
