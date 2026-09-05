"""The `ai-observatory` console entry point.

Everything real lives in `observe.py`, which is also the file a contributor
runs directly. This exists so that `uvx ai-observatory demo digest report`
and `python3 observe.py demo digest report` are the same program reached two
ways, rather than two programs that have to be kept in agreement.

`observe` puts its own directory on `sys.path` as its first act, so importing
it here is what makes the bare-name imports inside it resolve.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import observe  # noqa: E402  — the sys.path line above is what makes this work

    return observe.main(["ai-observatory", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
