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

import base64
import hashlib
import html
import json
import re
from pathlib import Path

ASSETS = Path(__file__).with_name("assets")
REPO = "https://github.com/jxxyx-bloop/ai-observatory"

SEV_COLOR = {"high": "var(--high)", "medium": "var(--med)",
             "low": "var(--low)", "info": "var(--info)"}


# Inline <script> bodies, for the page's own Content-Security-Policy.
SCRIPT_TAG = re.compile(r"<script(?![^>]*\bsrc\s*=)([^>]*)>(.*?)</script>",
                        re.I | re.S)


def csp_meta(page: str) -> str:
    """The policy this page carries with it.

    The hosted copy of this dashboard gets its headers from `site/dist/_headers`.
    A dashboard on someone's laptop gets nothing: it is opened from `file://`,
    where there is no server and no response headers, and it is exactly the copy
    that holds real data. So the policy travels inside the document instead.

    It matters because this page renders strings this project did not write —
    repository and folder names, model ids, and the names of tools and agents
    that arrive from whatever MCP servers the reader has configured. Every one
    of those goes through `esc()` on the way in, and that remains the actual
    defence; this is the second line, for the day one path misses.

    script-src is hashes of the scripts this render produced, so injected markup
    cannot execute even if it reaches the document. The hashes are computed from
    the assembled page rather than stored, because the payload is inlined into a
    script tag and therefore differs for every reader.

    `frame-ancestors` is deliberately absent: it is ignored in a <meta> policy,
    and listing a directive that does nothing invites someone to trust it. The
    hosted copy gets that one from `_headers`, where it works.
    """
    hashes = sorted({
        "'sha256-" + base64.b64encode(
            hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii") + "'"
        for _attrs, body in SCRIPT_TAG.findall(page)
    })
    if not hashes:
        raise RuntimeError("render: no inline scripts to authorise — a CSP "
                           "written now would blank the dashboard")
    policy = "; ".join((
        "default-src 'none'",
        "script-src " + " ".join(hashes),
        # Data-driven bar widths and severity colours are style="" attributes,
        # which no hash can cover. See the same note in site/build.py.
        "style-src 'unsafe-inline'",
        "img-src 'self' data:",
        "form-action 'none'",
        "base-uri 'none'",
    ))
    return f'<meta http-equiv="Content-Security-Policy" content="{policy}">'


def esc(v) -> str:
    return html.escape(str(v if v is not None else "—"), quote=True)


def usd(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    return f"${n:,.0f}" if abs(n) >= 100 else f"${n:,.2f}"


def _action_html(action) -> str:
    """The recommendation, as a paragraph or as numbered steps.

    A detector returns a list when the advice is genuinely more than one move.
    Numbering them is not decoration: a reader scanning for what to do next can
    count the steps before reading them, and a step they have already taken is
    findable again. Prose hides that structure inside a sentence.
    """
    if isinstance(action, (list, tuple)):
        items = "".join(f"<li>{esc(step)}</li>" for step in action)
        return f'<ol class="act acts">{items}</ol>'
    return f'<p class="act">{esc(action)}</p>'


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
            f'<div class="find" data-sev="{esc(f["severity"])}" style="--c:{c}">'
            f'<div class="top"><span class="sev">{esc(f["severity"])}</span>'
            f'<span class="ttl">{esc(f["title"])}</span>{save}</div>'
            f'<p>{esc(f["finding"])}</p>'
            f'{_action_html(f["action"])}'
            f'{meta}<p class="meta">Confidence: {esc(f.get("confidence", "—"))}</p></div>'
        )
    # One flow, in severity order, with width carrying the priority — see the
    # `.finds` rules. Splitting the list into a hero plus a column-flowed tail
    # read the order out of it: three columns of mixed severity put a MEDIUM, a
    # LOW and an INFO side by side at equal weight, and the reader lost the
    # thread of what to do first.
    return '<div class="finds">' + "".join(out) + "</div>"


def render(digest: dict, home: str | None = None, refresh: str | None = None,
           demo: bool = False, setup: str | None = None,
           star: str | None = None, update: dict | None = None) -> str:
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

    `update` is what `updater.for_render` decided the reader should be told
    about their version, already reduced to "a newer one is waiting" or "here
    is what last night's brought". The page renders what it is handed and
    resolves nothing itself: a file opened from `file://` cannot check a clock
    against a repository, and should not try.
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
    page = (
        page.replace("/*CSS*/", css)
            .replace("/*I18N*/", (ASSETS / "i18n.js").read_text(encoding="utf-8"))
            .replace("/*JS*/", (ASSETS / "app.js").read_text(encoding="utf-8"))
            .replace("<!--HOMEATTR-->", crumb_attr)
            .replace("<!--HOMEKEY-->", crumb_key)
            .replace("<!--HOMELABEL-->", crumb_label)
            .replace("<!--HOME-->", esc(crumb_href))
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
                # Only the hosted demo passes this. A dashboard rendered on
                # somebody's own machine belongs to someone who already
                # installed the thing — they are owed a tool, not another ask.
                "star": star,
                "update": update or None,
            }, separators=(",", ":")).replace("</", "<\\/"))
            .replace("/*PAYLOAD*/",
                     json.dumps(digest, separators=(",", ":")).replace("</", "<\\/"))
    )
    # Last: the policy is a hash of the scripts above, so they have to be final.
    return page.replace("<!--CSP-->", csp_meta(page))
