#!/usr/bin/env python3
"""Check the `_headers` a site build wrote, and the policy it declares.

    python3 site/tools/check_headers.py site/dist

Three things, in one place because they are one question — does the deployment
protect the pages it is about to serve:

  1. every response carries the headers this site owes its readers,
  2. the Content-Security-Policy in each block has the shape it must have,
  3. the hashes that policy pins are exactly the inline scripts on disk.

(3) is recomputed from the built pages rather than trusted from the build, so a
build that wrote `_headers` before a page — the one ordering bug that fails
silently in CI and blanks the page in a browser — is caught here.

`_headers` may declare more than one block since the site gained an optional
visitor counter: the marketing pages reach one host, and `/demo/*` gets a
policy that reaches nothing. So this reads blocks rather than a flat file, and
the rule that matters most is (2c) below — a policy naming a remote host must
not be the one that lands on the demo.
"""

from __future__ import annotations

import base64
import hashlib
import re
import sys
from pathlib import Path

REQUIRED = ("Strict-Transport-Security", "X-Frame-Options",
            "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy",
            "Content-Security-Policy", "Cross-Origin-Opener-Policy",
            "Cross-Origin-Resource-Policy", "X-Permitted-Cross-Domain-Policies")

DIRECTIVES = ("default-src", "script-src", "frame-ancestors", "base-uri",
              "form-action")

# Where a wildcard host is tolerated, and nowhere else. Google collects on
# regional hostnames it adds without announcing them, so `connect-src` and
# `img-src` cannot be enumerated and stay working. The directives that decide
# what may *execute* are not on this list and must never be.
WILDCARD_OK = ("connect-src", "img-src")

# Every host allowed to appear in any policy here. A new one is a decision, and
# a decision belongs in a diff — not in whatever a template happened to inline.
ALLOWED_HOSTS = ("https://www.googletagmanager.com",
                 "https://*.googletagmanager.com",
                 "https://*.google-analytics.com",
                 "https://*.analytics.google.com")

# Blocks whose policy must name no remote host at all, matched as prefixes
# against the block's path pattern. `/*` matches the demo too, so it is listed:
# a `/*` policy that reaches a host is only acceptable alongside a narrower
# block that takes the demo back, which is what `covers_demo` checks for.
DEMO = "/demo/"


def blocks(text: str) -> list[tuple[str, dict[str, str]]]:
    """`_headers` as (path pattern, headers) pairs, in file order."""
    out: list[tuple[str, dict[str, str]]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if not line[0].isspace():
            out.append((line.strip(), {}))
            continue
        if not out:
            continue                      # a header before any pattern
        name, _, value = line.partition(":")
        out[-1][1][name.strip().lower()] = value.strip()
    return out


def directives_of(csp: str) -> dict[str, str]:
    return {d.strip().split(" ")[0]: d.strip() for d in csp.split(";") if d.strip()}


def matches_demo(pattern: str) -> bool:
    """Whether a `_headers` path pattern lands on the demo dashboard."""
    prefix = pattern.rstrip("*")
    return DEMO.startswith(prefix) or prefix.startswith(DEMO)


def check_policy(pattern: str, csp: str, fail: list[str]) -> None:
    directives = directives_of(csp)
    for name in DIRECTIVES:
        if name not in directives:
            fail.append(f"{pattern}: CSP is missing {name}")

    script = directives.get("script-src", "")
    if "'unsafe-inline'" in script or "'unsafe-eval'" in script:
        fail.append(f"{pattern}: script-src must not allow 'unsafe-inline' "
                    f"or 'unsafe-eval'")
    if "sha256-" not in script:
        fail.append(f"{pattern}: script-src must pin this build's inline "
                    f"scripts by hash")

    for name, body in directives.items():
        for source in body.split()[1:]:
            if source.startswith("'") or source in ("data:", "blob:"):
                continue
            if source not in ALLOWED_HOSTS:
                fail.append(f"{pattern}: {name} names {source}, which is not "
                            f"on this site's allowed-host list")
            elif "*" in source and name not in WILDCARD_OK:
                fail.append(f"{pattern}: {name} must not use a wildcard host "
                            f"({source})")


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else "site/dist")
    path = root / "_headers"
    if not path.is_file():
        print(f"::error::{path} is missing — did the build run?")
        return 1

    found = blocks(path.read_text(encoding="utf-8"))
    if not found:
        print(f"::error::{path} declares no rules")
        return 1

    fail: list[str] = []
    for pattern, headers in found:
        for name in REQUIRED:
            if name.lower() not in headers:
                fail.append(f"{pattern}: missing header {name}")

        # Present but zeroed reads as configured while switching HSTS off.
        hsts = headers.get("strict-transport-security", "")
        age = re.search(r"max-age=(\d+)", hsts)
        if not age or int(age.group(1)) < 31536000:
            fail.append(f"{pattern}: Strict-Transport-Security needs "
                        f"max-age >= 31536000, got {hsts!r}")
        # Joining the browsers' preload list is close to irreversible, and not
        # something to acquire in a refactor.
        if "preload" in hsts:
            fail.append(f"{pattern}: Strict-Transport-Security must not claim "
                        f"preload without a deliberate decision")
        if headers.get("referrer-policy") != "no-referrer":
            fail.append(f"{pattern}: Referrer-Policy must stay no-referrer, "
                        f"got {headers.get('referrer-policy')!r}")
        check_policy(pattern, headers.get("content-security-policy", ""), fail)

    # The one that guards the promise. Any block that can land on the demo has
    # to reach nothing, and the narrower block has to exist to take it back.
    reaching = [p for p, h in found
                if "https://" in h.get("content-security-policy", "")]
    if reaching:
        covers_demo = [p for p, h in found
                       if matches_demo(p) and "https://" not in
                       h.get("content-security-policy", "")]
        if not covers_demo:
            fail.append(f"{', '.join(reaching)} reaches a remote host and "
                        f"nothing narrower takes {DEMO} back — the demo would "
                        f"be served under a policy that permits one")

    # Recomputed from the pages, never read back from the build.
    tag = re.compile(r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", re.I | re.S)
    shipped = set()
    for page in sorted(root.rglob("*.html")):
        for body in tag.findall(page.read_text(encoding="utf-8")):
            shipped.add("'sha256-" + base64.b64encode(
                hashlib.sha256(body.encode("utf-8")).digest()).decode() + "'")
    declared = set(re.findall(r"'sha256-[A-Za-z0-9+/=]+'",
                              path.read_text(encoding="utf-8")))
    if shipped - declared:
        fail.append("inline scripts the CSP would block: "
                    + ", ".join(sorted(shipped - declared)))
    if declared - shipped:
        fail.append("the CSP authorises scripts that are on no page: "
                    + ", ".join(sorted(declared - shipped)))

    if fail:
        for line in fail:
            print(f"::error::{line}")
        return 1
    print(f"check: {len(found)} header block(s), {len(shipped)} inline "
          f"scripts, every one pinned"
          + (f"; {DEMO} reaches nothing" if reaching else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
