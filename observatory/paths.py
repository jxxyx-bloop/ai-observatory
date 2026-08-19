"""Path -> (repo, surface) classifier.

Absolute paths are read in memory and thrown away. Only the two derived labels
— a repo name and a coarse surface like `project:ai-observatory` — ever reach
the event store, which is what keeps the metadata-only promise intact while
still answering "which project was I actually in?" (ADR-008).

Config lives in `topology.json` so adding a code root or a folder taxonomy is
an edit, not a code change.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("topology.json")

_CFG = None


def _prepare(cfg: dict) -> dict:
    """Expand `~` and pre-sort the roots longest-first so the most specific wins."""
    cfg = dict(cfg)
    cfg["_roots"] = sorted(
        (os.path.expanduser(r).rstrip("/") for r in cfg["code_roots"]),
        key=len, reverse=True,
    )
    cfg["_special"] = sorted(
        ((os.path.expanduser(k).rstrip("/"), v)
         for k, v in cfg.get("special_roots", {}).items()),
        key=lambda kv: -len(kv[0]),
    )
    return cfg


def config() -> dict:
    global _CFG
    if _CFG is None:
        _CFG = _prepare(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    return _CFG


def use(cfg=None) -> None:
    """Swap the active topology, or reset to `topology.json` when given None.

    Exists because attribution is the one part of the engine whose behaviour
    depends on the machine it runs on — `~/code` is a different directory for
    every user and every CI runner. A test that wants a deterministic answer has
    to state its own roots rather than inherit the host's, and anything
    embedding the engine needs the same hook.
    """
    global _CFG
    _CFG = None if cfg is None else _prepare(cfg)


def split(path):
    """Absolute path -> (repo, repo_relative_path). (None, None) when the path
    sits outside every known root — unclassified is reported, never guessed."""
    cfg = config()
    if not isinstance(path, str) or not path.startswith("/"):
        return None, None
    p = os.path.normpath(path)

    for pre in cfg["scratch_prefixes"]:
        if p.startswith(pre):
            return "scratchpad", None

    marker = "/" + cfg["worktree_marker"] + "/"
    if marker in p:
        head, tail = p.split(marker, 1)
        rel = tail.split("/", 1)[1] if "/" in tail else ""
        repo, _ = split(head)
        return (repo or os.path.basename(head) or None), rel

    for root, name in cfg["_special"]:
        if p == root or p.startswith(root + "/"):
            return name, p[len(root):].lstrip("/")

    for root in cfg["_roots"]:
        if p.startswith(root + "/"):
            rest = p[len(root) + 1:].split("/")
            if len(rest) == 1 and "." in rest[0]:
                return None, None  # a loose file in the root, not a repo
            return rest[0] or None, "/".join(rest[1:])

    return None, None


def _matches(pattern: str, parts: list) -> bool:
    seg = pattern.split("/")
    if len(seg) > len(parts):
        return False
    return all(a == "*" or a == b for a, b in zip(seg, parts))


def _fill(label: str, parts: list):
    """Interpolate `{n}` with segment n, or refuse.

    Only a *directory* may become a label. The last segment of a path is the
    filename, so a rule that would interpolate it is skipped and the next rule
    (or the generic fallback) applies — otherwise `context/*` -> `context/{1}`
    would turn a document title into a permanent bucket, which is exactly what
    ADR-008 caps.
    """
    for i, part in enumerate(parts):
        token = "{%d}" % i
        if token not in label:
            continue
        if i >= len(parts) - 1:
            return None
        label = label.replace(token, part)
    return label


def surface(repo, rel):
    """Repo-relative path -> the coarse bucket it belongs to."""
    if repo is None:
        return None
    if repo == "scratchpad":
        return "scratch files"  # one flat bucket — throwaway work has no taxonomy
    if not rel:
        return "(root)"
    parts = rel.split("/")
    rules = config()["surface_rules"]
    for key in (repo, "*"):
        for pattern, label in rules.get(key, []):
            if not _matches(pattern, parts):
                continue
            filled = _fill(label, parts)
            if filled:
                return filled
    # Generic fallback: the top folder, or "(root)" for a file at repo top level.
    return parts[0] if len(parts) > 1 else "(root)"


def classify(path):
    """Absolute path -> (repo, surface). Both None when unclassified."""
    repo, rel = split(path)
    return repo, surface(repo, rel)


def is_incidental(repo) -> bool:
    """True for infrastructure repos that should lose an attribution tie."""
    return repo in config().get("incidental_repos", [])


def pick_repo(cwd_repo, touched):
    """The repo a turn is really about.

    Where it ran wins; otherwise the first real repo it touched. A scratch file
    or a config edit only claims the turn when nothing real is in the running.
    """
    ranked = ([cwd_repo] if cwd_repo else []) + [r for r, _ in touched]
    return next((r for r in ranked if not is_incidental(r)),
                ranked[0] if ranked else None)


def lane_of(repo=None, entrypoint=None, provider=None) -> str:
    """Which usage lane this turn belongs to.

    Transcripts carry no account identity, so a lane is inferred from where and
    how the work happened, per the rules in `topology.json`. First match wins.
    """
    lanes = config()["lanes"]
    have = {"repo": repo, "entrypoint": entrypoint, "provider": provider}
    for rule in lanes.get("rules", []):
        conds = {k: v for k, v in rule.items() if k != "lane"}
        if conds and all(have.get(k) == v for k, v in conds.items()):
            return rule["lane"]
    return lanes.get("default", "work")
