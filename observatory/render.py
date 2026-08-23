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
REPO = "https://github.com/jxxyx-bloop/ai-observatory"

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


def render(digest: dict, home: str | None = None, refresh: str | None = None,
           demo: bool = False, setup: str | None = None) -> str:
    """Assemble the page from the templates in `engine/assets/`.

    `home` is where the breadcrumb points. The hosted demo passes "../" so the
    crumb leads back to the landing page; a dashboard rendered on your own
    machine passes nothing and gets a link to the repository instead, because
    there is no site next to it to return to.

    `refresh` is the shell line the freshness strip offers when the report has
    aged. It must already be safe to show a stranger — `launcher.refresh_command`
    abbreviates `$HOME` to `~` precisely because this page is meant to be
    e-mailable, and an absolute path would name its author. `demo` marks the
    sample-data build so the page can say so on every visit, and `setup` is
    where its call to action leads — the hosted demo has a guide to point at,
    a dashboard on someone's laptop does not.
    """
    page = (ASSETS / "page.html").read_text(encoding="utf-8")
    crumb_href = home or REPO
    crumb_key = "crumb_home" if home else "crumb_repo"
    crumb_label = "Home" if home else "Repository"
    # Only the hosted copy has sibling locale directories to point at.
    crumb_attr = ' data-locale-home="1"' if home else ""
    # A "set up" tile only means something where there is a guide to reach.
    rail_setup = (
        f'<a class="railcta" href="{esc(setup)}">'
        '<svg viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 19h14"></path></svg>'
        '<span data-i18n="nav_setup">Set up</span></a>') if setup else ""
    # Tokens first, then layout — the same order the landing page uses, so the
    # two surfaces cannot drift apart. See docs/design/DESIGN-SYSTEM.md.
    css = ((ASSETS / "tokens.css").read_text(encoding="utf-8") + "\n"
           + (ASSETS / "app.css").read_text(encoding="utf-8"))
    return (
        page.replace("/*CSS*/", css)
            .replace("/*I18N*/", (ASSETS / "i18n.js").read_text(encoding="utf-8"))
            .replace("/*JS*/", (ASSETS / "app.js").read_text(encoding="utf-8"))
            .replace("<!--HOMEATTR-->", crumb_attr)
            .replace("<!--HOMEKEY-->", crumb_key)
            .replace("<!--HOMELABEL-->", crumb_label)
            .replace("<!--HOME-->", crumb_href)
            .replace("<!--RAILSETUP-->", rail_setup)
            .replace("<!--FINDINGS-->", findings_html(digest))
            .replace("<!--VERIFIED-->", esc(digest.get("pricing_verified_on") or "—"))
            .replace("<!--GENERATED-->",
                     esc((digest.get("generated_at") or "")[:16].replace("T", " ")))
            .replace("/*META*/", json.dumps({
                "generated_at": digest.get("generated_at"),
                "refresh": refresh or "python3 observatory/observe.py all",
                "demo": bool(demo or digest.get("demo")),
                "setup": setup,
            }, separators=(",", ":")).replace("</", "<\\/"))
            .replace("/*PAYLOAD*/",
                     json.dumps(digest, separators=(",", ":")).replace("</", "<\\/"))
    )
