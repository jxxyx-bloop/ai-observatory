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
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# rel values that cause the browser to go and get something.
FETCHING_REL = {"stylesheet", "preload", "prefetch", "preconnect",
                "dns-prefetch", "icon", "shortcut icon", "apple-touch-icon",
                "manifest", "modulepreload", "prerender"}

TAG = re.compile(r"<(script|link|img|iframe|source|video|audio|embed|object|use)\b"
                 r"([^>]*)>", re.I)
ATTR = re.compile(r'\b(src|srcset|href|data|xlink:href)\s*=\s*"([^"]*)"', re.I)
REMOTE = re.compile(r"^\s*(?:https?:)?//", re.I)


def offenders(html: str) -> list[str]:
    out = []
    for tag, attrs in TAG.findall(html):
        rels = re.findall(r'\brel\s*=\s*"([^"]*)"', attrs, re.I)
        rel = rels[0].strip().lower() if rels else ""
        if tag.lower() == "link" and rel not in FETCHING_REL:
            continue                      # alternate, canonical, author…
        for name, value in ATTR.findall(attrs):
            for url in value.split(","):
                if REMOTE.match(url.strip()):
                    out.append(f"<{tag} {name}=\"{url.strip()[:80]}\">")
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
