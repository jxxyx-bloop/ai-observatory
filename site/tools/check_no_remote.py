#!/usr/bin/env python3
"""Fail if any built page would fetch something from the network.

    python3 site/tools/check_no_remote.py site/dist
    python3 site/tools/check_no_remote.py site/dist --allow www.googletagmanager.com

The dashboard's headline promise is zero external requests, and the landing
page repeats it. A page that loads a webfont while saying so is the loudest
possible contradiction, so this is a build failure rather than something to
catch in review.

`--allow` names a host the *marketing* pages may reach — today that is the one
host a visitor counter needs. It is deliberately per-host and per-invocation
rather than a flag that switches the check off: what is permitted has to be
written out where a reviewer reads it, and anything not written out still
fails.

Nothing under `demo/` is ever exempt, whatever is allowed. The demo is the
product with the promise on it, and an allowance meant for a landing page must
not be able to reach it by accident — so the exemption is refused by path here,
in the checker, rather than depending on whoever writes the next CI step
remembering to run it twice.

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


def host_of(url: str) -> str:
    """The host in a URL a browser would fetch, protocol-relative ones too."""
    rest = re.sub(r"^\s*(?:https?:)?//", "", url.strip(), flags=re.I)
    return rest.split("/")[0].split("?")[0].split("#")[0].lower()


def offenders(html: str, allowed: frozenset[str] = frozenset()) -> list[str]:
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
                url = url.strip()
                if REMOTE.match(url) and host_of(url) not in allowed:
                    out.append(f'<{tag} {name}="{url[:80]}">')
    return out


# Paths the allowance never reaches, relative to the built root.
ALWAYS_STRICT = ("demo/",)


def main(argv: list[str]) -> int:
    allowed, positional = set(), []
    expect_host = False
    for arg in argv[1:]:
        if arg == "--allow":
            expect_host = True
        elif expect_host:
            allowed.add(arg.strip().lower())
            expect_host = False
        else:
            positional.append(arg)
    if expect_host:
        print("check: --allow needs a host", file=sys.stderr)
        return 1

    root = Path(positional[0] if positional else "site/dist")
    pages = sorted(root.rglob("*.html"))
    if not pages:
        print(f"check: no HTML under {root} — did the build run?", file=sys.stderr)
        return 1

    bad = 0
    strict_pages = 0
    for page in pages:
        rel = page.relative_to(root).as_posix()
        strict = any(rel.startswith(prefix) for prefix in ALWAYS_STRICT)
        strict_pages += strict
        found = offenders(page.read_text(encoding="utf-8"),
                          frozenset() if strict else frozenset(allowed))
        for item in found:
            note = " (allowances do not apply here)" if strict and allowed else ""
            print(f"::error file={page}::loads a remote subresource{note}: {item}")
            bad += 1
    if bad:
        print(f"check: {bad} remote subresource(s) — the zero-network promise "
              f"is part of the product, not a preference", file=sys.stderr)
        return 1
    if allowed:
        print(f"check: {len(pages)} pages, no remote subresources beyond "
              f"{', '.join(sorted(allowed))} — and none at all on the "
              f"{strict_pages} page(s) under {', '.join(ALWAYS_STRICT)}")
    else:
        print(f"check: {len(pages)} pages, no remote subresources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
