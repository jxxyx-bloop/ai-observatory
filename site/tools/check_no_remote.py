#!/usr/bin/env python3
"""Fail if any built page would fetch something from the network.

    python3 site/tools/check_no_remote.py site/dist

The dashboard's headline promise is zero external requests, and the landing
page repeats it. A page that loads a webfont while saying so is the loudest
possible contradiction, so this is a build failure rather than something to
catch in review.

It replaces a grep that matched every `<link rel="alternate" hreflang=...>` the
moment the site went multilingual — those are metadata, not subresources, and a
check that cries wolf is a check people delete. So this one knows the
difference: a `<link>` only fetches when its `rel` says it does.

It also catches the three tags that send a *reader* elsewhere rather than
fetching something: a `<meta http-equiv=refresh>` pointing off-site, a `<base>`
that silently re-targets every relative link on the page, and a `<form>` that
would post somewhere else. None of those is a subresource, all of them turn this
site into a redirector, and the CSP that would stop them in a browser is only
sent on the hosted copy.

Attribute values are matched whether they are double-quoted, single-quoted or
bare. That is not pedantry: a guard that only understands the quoting style the
templates happen to use today is a guard that stops working the moment somebody
writes `src='...'`, and it would keep printing "no remote subresources" while
doing it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# rel values that cause the browser to go and get something.
FETCHING_REL = {"stylesheet", "preload", "prefetch", "preconnect",
                "dns-prefetch", "icon", "shortcut icon", "apple-touch-icon",
                "manifest", "modulepreload", "prerender"}

TAG = re.compile(r"<(script|link|img|iframe|source|video|audio|embed|object|use"
                 r"|meta|base|form|a)\b([^>]*)>", re.I)
# "..." | '...' | bare — anything a browser would accept as the value.
ATTR = re.compile(r'\b(src|srcset|href|data|xlink:href|action|ping|content'
                  r'|http-equiv)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)
REMOTE = re.compile(r"^\s*(?:https?:)?//", re.I)
# The URL inside `content="0; url=https://elsewhere"`.
REFRESH_URL = re.compile(r"url\s*=\s*['\"]?([^'\";]+)", re.I)


def attrs_of(raw: str) -> list[tuple[str, str]]:
    out = []
    for name, dq, sq, bare in ATTR.findall(raw):
        out.append((name.lower(), (dq or sq or bare).strip()))
    return out


def offenders(html: str) -> list[str]:
    out = []
    for tag, raw in TAG.findall(html):
        tag = tag.lower()
        attrs = attrs_of(raw)
        get = lambda k: next((v for n, v in attrs if n == k), "")

        if tag == "meta":
            # Only one kind of <meta> moves the reader, and it is this one.
            if get("http-equiv").lower() == "refresh":
                target = REFRESH_URL.search(get("content"))
                if target and REMOTE.match(target.group(1)):
                    out.append(f'<meta http-equiv="refresh" -> {target.group(1)[:80]}>')
            continue

        if tag == "a":
            # A link to GitHub is the point of several of these pages; `ping`
            # is the attribute that fires a request without being clicked.
            for url in get("ping").split():
                if REMOTE.match(url):
                    out.append(f'<a ping="{url[:80]}">')
            continue

        if tag == "link":
            rels = re.findall(r'\brel\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',
                              raw, re.I)
            rel = next((a or b or c for a, b, c in rels), "").strip().lower()
            if rel not in FETCHING_REL:
                continue                  # alternate, canonical, author…

        for name, value in attrs:
            if name in ("content", "http-equiv"):
                continue                  # only meaningful on <meta>, handled above
            for url in value.split(","):
                if REMOTE.match(url.strip()):
                    out.append(f'<{tag} {name}="{url.strip()[:80]}">')
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else "site/dist")
    pages = sorted(root.rglob("*.html"))
    if not pages:
        print(f"check: no HTML under {root} — did the build run?", file=sys.stderr)
        return 1

    bad = 0
    for page in pages:
        found = offenders(page.read_text(encoding="utf-8"))
        for item in found:
            print(f"::error file={page}::loads a remote subresource: {item}")
            bad += 1
    if bad:
        print(f"check: {bad} remote subresource(s) — the zero-network promise "
              f"is part of the product, not a preference", file=sys.stderr)
        return 1
    print(f"check: {len(pages)} pages, no remote subresources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
