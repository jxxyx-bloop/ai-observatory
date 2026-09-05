"""Draft a collector spec from a tool on this machine — and a fixture safe to publish.

Coverage is the one thing this project cannot buy with effort. A maintainer
cannot write a collector for a tool they do not run: the format is only half
knowable from a vendor's source, and the half that decides whether the numbers
are true — whether an input count already contains its cached count — usually
is not written down anywhere. The person who uses the tool has the answer
sitting on their disk and no reason to spend an afternoon finding it.

So this reads their disk instead, and hands back the two files a pull request
needs: a draft spec, and a fixture. It infers what it can, states plainly what
it guessed, and refuses to guess the one field that would silently misprice
somebody's month.

## The dangerous half

A fixture goes into a public repository. That makes this the only command here
that prepares private data for publication, and it inherits `share.py`'s rule
without softening it: **the fixture is built by allow-list.** A value survives
because its shape was named safe, not because a filter failed to catch it.

  numbers        kept — token counts are the point, and they name nobody
  strings        dropped, unless the *key* is one of SAFE_KEYS below
  paths          replaced with a synthetic path, so `path_args` stays testable
  ids            replaced with a stable synthetic id
  times          replaced with synthetic times that keep the original *format*
  everything else  becomes "<redacted>"

Text is never kept. Not truncated, not hashed — dropped, because a prompt
fragment is the thing most likely to carry an employer's confidential project
and the one thing nobody can un-publish.

Nothing is uploaded. This writes files and prints where they are.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── what a fixture may contain ──────────────────────────────────────────────

# String values survive only under these keys. Each one names a mechanism — a
# record type, a model, a tool — never a person, a project, or a prompt. Adding
# a key here is a decision to publish that field for every future contributor,
# so it belongs in a diff a reviewer can see.
SAFE_KEYS = {
    "type", "role", "kind", "status", "state", "finish", "finish_reason",
    "stop", "stop_reason", "reason", "model", "modelid", "model_id",
    "name", "tool", "tool_name", "provider", "agent", "entrypoint",
    "version", "unit", "currency", "effort", "speed", "tier", "source",
}

# Argument names that hold a path, in the tools we have seen. Read only long
# enough to derive a repo label, per ADR-008.
PATH_ARGS = ("file_path", "path", "filePath", "absolute_path", "dir_path")

# Keys whose value is a time. Gated on the key rather than sniffed from the
# number, so a token count is never mistaken for a date and rewritten.
TIME_KEYS = ("time", "timestamp", "ts", "created", "started", "completed",
             "updated", "date", "at")



def _is_time_key(leaf: str) -> bool:
    """True for a key that names a clock reading.

    Deliberately not a substring test. `cache_creation_tokens` contains "at",
    and a loose match here silently picks a token count as the timestamp — a
    draft that looks finished and reads nothing.
    """
    return (leaf in TIME_KEYS
            or leaf.endswith(("_at", "_ts", "_time", "_timestamp", "_date"))
            or leaf.startswith(("timestamp", "created_", "started_", "updated_")))


SAFE_STRING = re.compile(r"^[A-Za-z0-9 ._:@+-]{1,64}$")
LOOKS_LIKE_PATH = re.compile(r"^(/|~/|[A-Za-z]:\\\\)")

# The synthetic values a redacted fixture is rebuilt from. The path matches the
# topology `tests/test_specs.py` declares, so a generated fixture resolves to a
# real repo and surface the moment it is dropped into the test suite.
FAKE_PATH = "/home/dev/code/my-app/src/api/handler.ts"
FAKE_ID = "ses-0001"
BASE_TIME = datetime(2026, 8, 19, 1, 2, 11, tzinfo=timezone.utc)

# ── where to look ───────────────────────────────────────────────────────────

# Providers with a collector already. A directory under one of these is not a
# discovery, it is the thing we shipped.
KNOWN = ("/.claude/", "/.codex/", "/.kimi-code/", "/.gemini/antigravity/",
         "/.gemini/tmp/", "/.ai-observatory/")

# Bounded on purpose. Walking a whole home directory to find four files is how
# a "quick look" turns into a minute of disk churn on somebody's laptop.
SEARCH_ROOTS = ("~", "~/.config", "~/.local/share",
                "~/Library/Application Support")
MAX_DEPTH = 6
MAX_FILES_PER_DIR = 200


def _is_known(path: str) -> bool:
    posix = Path(path).as_posix()
    return any(k in posix for k in KNOWN)


def scan(limit: int = 40) -> list:
    """Directories holding JSON or JSONL that no collector claims yet.

    Returns `{dir, files, ext, sample}` per candidate, most files first — the
    store a tool actually writes to is nearly always the biggest one it owns.
    """
    seen, out = set(), {}
    for root in SEARCH_ROOTS:
        base = Path(os.path.expanduser(root))
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            depth = len(Path(dirpath).relative_to(base).parts)
            if depth >= MAX_DEPTH:
                dirnames[:] = []
                continue
            # Only ever descend into dot-directories and their children: an
            # agent keeps its transcripts in one, and Documents is not ours.
            if depth == 0:
                dirnames[:] = [d for d in dirnames if d.startswith(".")
                               or d in ("Application Support",)]
            dirnames[:] = [d for d in dirnames
                           if d not in ("node_modules", ".git", "Cache", "cache")]
            if dirpath in seen or _is_known(dirpath):
                continue
            seen.add(dirpath)
            hits = [f for f in filenames[:MAX_FILES_PER_DIR]
                    if f.endswith((".jsonl", ".json"))]
            if not hits:
                continue
            ext = ".jsonl" if any(f.endswith(".jsonl") for f in hits) else ".json"
            candidate = [f for f in hits if f.endswith(ext)]
            out[dirpath] = {"dir": dirpath, "files": len(candidate), "ext": ext,
                            "sample": str(Path(dirpath) / candidate[0])}
    ranked = sorted(out.values(), key=lambda c: -c["files"])
    return [c for c in ranked if _has_tokens(c["sample"])][:limit]


def _has_tokens(sample: str) -> bool:
    """True when the file mentions something token-shaped.

    The cheap filter that makes a scan useful: a machine has thousands of JSON
    files and perhaps two that are transcripts. Reading a slice of each and
    looking for the word is enough to tell them apart.
    """
    try:
        with open(sample, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(200_000).lower()
    except OSError:
        return False
    return ("token" in head or "usage" in head) and (
        "input" in head or "prompt" in head or "output" in head)


# ── reading a candidate ─────────────────────────────────────────────────────

def read_records(source: str, limit: int = 400):
    """(records, format) for a file, whichever of the three shapes it is."""
    path = Path(source)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], "jsonl"

    if path.suffix == ".jsonl":
        out = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
            if len(out) >= limit:
                break
        return out, "jsonl"

    try:
        doc = json.loads(text)
    except ValueError:
        return [], "json"
    if isinstance(doc, list):
        return doc[:limit], "json-array"
    if isinstance(doc, dict):
        # A document that holds one long list of records is that list; a
        # document that holds none is itself the record.
        for key, value in doc.items():
            if isinstance(value, list) and len(value) > 1 and \
                    all(isinstance(v, dict) for v in value[:5]):
                return value[:limit], "json-array:" + key
        return [doc], "json"
    return [], "json"


def _walk(node, prefix=""):
    """Every dotted path in a record, with its leaf value."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, f"{prefix}.{key}" if prefix else str(key))
    else:
        yield prefix, node


def _leaf(path: str) -> str:
    return path.rsplit(".", 1)[-1].lower()


# Ordered: the first pattern that matches a numeric field claims it. Cache
# patterns come first because `cache_read_input_tokens` also contains "input".
COUNTERS = (
    ("cache_read", re.compile(r"cache.*read|cached|cache_read")),
    ("cache_create", re.compile(r"cache.*(write|creat)|cache_creation")),
    ("output", re.compile(r"^(output|completion|candidates).*token|^output$|^completion$")),
    ("input", re.compile(r"^(input|prompt).*token|^input$|^prompt$")),
)


def infer(records: list, fmt: str) -> dict:
    """A draft spec from a handful of real records. Guesses, clearly labelled."""
    numeric, strings, lists = {}, {}, {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        for path, value in _walk(rec):
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                numeric.setdefault(path, 0)
                numeric[path] += 1
            elif isinstance(value, str):
                strings.setdefault(path, set()).add(value[:64])
        for key, value in rec.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                lists.setdefault(key, 0)
                lists[key] += 1

    fields, used = {}, set()
    for name, pattern in COUNTERS:
        for path in sorted(numeric, key=len):
            if path in used or not pattern.search(_leaf(path)):
                continue
            fields[name] = path
            used.add(path)
            break

    # Strings first: a tool that writes both an ISO stamp and an epoch number
    # is better read from the stamp, which needs no `ts_unit` to be right.
    for path in sorted(strings) + sorted(numeric):
        if path not in used and _is_time_key(_leaf(path)):
            fields["ts"] = path
            break
    for path in sorted(strings):
        if "model" in _leaf(path):
            fields["model"] = path
            break

    # `where` wants a short, low-cardinality string that separates a priced
    # record from the rest — a `type` or `role` marker, in practice.
    where = {}
    for path, values in sorted(strings.items()):
        if _leaf(path) in ("type", "role", "kind") and len(values) <= 8:
            priced = [r for r in records
                      if isinstance(r, dict) and _priced(r, fields)]
            marker = {_dig(r, path) for r in priced if _dig(r, path)}
            if len(marker) == 1:
                where[path] = marker.pop()
                break

    spec = {
        "_doc": "DRAFT, written by `observe.py contribute`. Every value below "
                "was inferred from records on one machine. Read the checklist "
                "beside this file before opening a pull request.",
        "provider": "CHANGEME",
        "roots": ["CHANGEME"],
        "where": where,
        "default_entrypoint": "cli",
        "fields": fields,
    }
    if fmt != "jsonl":
        spec["format"] = "json"
        if fmt.startswith("json-array:"):
            spec["records"] = fmt.split(":", 1)[1]
    if fields.get("ts") and isinstance(_first(records, fields["ts"]), (int, float)):
        value = _first(records, fields["ts"])
        spec["ts_unit"] = "millis" if value and value > 1e11 else "seconds"
    if lists:
        best = max(lists, key=lambda k: lists[k])
        sample = next((r[best][0] for r in records
                       if isinstance(r, dict) and isinstance(r.get(best), list)
                       and r[best] and isinstance(r[best][0], dict)), {})
        # An OpenAI-shaped tool call keeps both a step down, under `function`.
        name = _find(sample, lambda k, v: k == "name" and isinstance(v, str))
        args = _find(sample, lambda k, v: isinstance(v, dict)
                     and any(a in v for a in PATH_ARGS))
        spec["tools"] = {"list": best, "name": name or "name",
                         "args": args or "input", "path_args": list(PATH_ARGS)}
    return spec


def _find(node, pred, prefix=""):
    """Dotted path of the first value satisfying `pred`, breadth-first."""
    if not isinstance(node, dict):
        return None
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        if pred(key, value):
            return path
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        hit = _find(value, pred, path)
        if hit:
            return hit
    return None


def _dig(node, path):
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
        if node is None:
            return None
    return node


def _first(records, path):
    for rec in records:
        value = _dig(rec, path) if isinstance(rec, dict) else None
        if value is not None:
            return value
    return None


def _priced(rec, fields) -> bool:
    return any(isinstance(_dig(rec, fields[k]), (int, float)) and _dig(rec, fields[k])
               for k in ("input", "output", "cache_read", "cache_create")
               if fields.get(k))


# ── redaction ───────────────────────────────────────────────────────────────

def redact(node, index: int = 0, key: str = ""):
    """Rebuild a record from values whose shape was named safe. Allow-list."""
    if isinstance(node, dict):
        return {k: redact(v, index, k) for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v, index, key) for v in node[:8]]
    if node is None or isinstance(node, bool):
        return node

    low = key.lower()
    is_time = _is_time_key(low)

    if isinstance(node, (int, float)):
        # A number under a time-shaped key is a clock reading, and a clock
        # reading is when this person works. Everything else is a count.
        if is_time and node > 1e8:
            stamp = BASE_TIME + timedelta(seconds=60 * index)
            return int(stamp.timestamp() * 1000) if node > 1e11 \
                else int(stamp.timestamp())
        return node

    if isinstance(node, str):
        if is_time:
            return (BASE_TIME + timedelta(seconds=60 * index)) \
                .isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if LOOKS_LIKE_PATH.match(node):
            return FAKE_PATH
        if low in SAFE_KEYS and SAFE_STRING.match(node) and "/" not in node:
            return node
        if low.endswith("id") or low == "session":
            return FAKE_ID
        return "<redacted>"
    return "<redacted>"


def build(source: str) -> dict:
    """Everything a pull request needs, from one file. Reads only."""
    records, fmt = read_records(source)
    spec = infer(records, fmt)
    keep = [r for r in records if isinstance(r, dict)][:6]
    fixture = [redact(r, i) for i, r in enumerate(keep)]
    return {"spec": spec, "fixture": fixture, "format": fmt,
            "records_seen": len(records)}


CHECKLIST = """# Before you open the pull request

`observe.py contribute` inferred everything in `spec.json` from records on one
machine. Three of those guesses it cannot check for you, and the second one
decides whether anybody's costs come out true.

## 1. Name it, and point it at the real files

Set `provider` to a short slug and `roots` to the glob that finds these files
on any machine — `~` is expanded for you. Then prove the glob works, because a
spec whose glob matches nothing passes every test while reading nothing:

    python3 -c "import json,sys; sys.path.insert(0,'observatory'); \\
      from collectors.generic import SpecCollector; \\
      print(SpecCollector(json.load(open('SPEC.json'))).sources()[:5])"

## 2. Decide `input_is_total` — this is the one that matters

Does this tool's input count **already include** its cached count? Add up one
turn by hand, or find where the tool writes the number in its own source. If
input already contains cache, set `"input_is_total": true`. Guess it wrong in
that direction and every user's spend is inflated by the size of their cache
hits, which for most people is most of their reading.

It is deliberately absent from the draft. There is no safe default.

## 3. Read the fixture

It was rebuilt by allow-list: numbers kept, paths and ids replaced with
synthetic ones, times shifted, every other string dropped. Read it anyway
before it goes into a public repository — you know what is sensitive on your
machine and this file does not.

Then move the two files into place, add a test to `tests/test_specs.py`
asserting an exact turn count, and run `observatory/tests/run.sh`.
"""
