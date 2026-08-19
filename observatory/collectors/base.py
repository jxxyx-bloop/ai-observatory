"""Provider collector interface.

Every provider implements `Collector`. Downstream code (normalize, analyze,
insights, render) never imports a provider module directly — it only consumes
the normalized event dicts produced here. See docs/specs/Provider-Interface.md.

Hard rules for every collector:
  1. READ-ONLY. Never write to, move, or truncate a provider's own files.
  2. METADATA-ONLY. Never emit prompt text, completion text, file contents,
     shell command strings, or absolute paths. Counts and names only. Paths may
     be *read* to derive a repo name and a coarse surface label, then dropped —
     the label is emitted, the path never is (ADR-008).
  3. INCREMENTAL. Honour the cursor passed in so re-runs are cheap.
"""

from __future__ import annotations

SCHEMA_VERSION = 2


class Collector:
    """Base class. Subclasses set `provider` and implement `collect`."""

    provider: str = "unknown"

    def available(self) -> bool:
        """True when this provider's data source exists on this machine."""
        raise NotImplementedError

    def sources(self) -> list:
        """List of opaque source handles (usually file paths) to scan."""
        raise NotImplementedError

    def collect(self, source, cursor: dict) -> tuple:
        """Parse one source from `cursor` onward.

        Returns (events, new_cursor) where `events` is a list of normalized
        event dicts and `new_cursor` is a JSON-serialisable dict recording how
        far this source was consumed.
        """
        raise NotImplementedError


def blank_event(provider: str) -> dict:
    """Canonical event shape. Keys stay stable across schema versions;
    new keys may be added, existing keys are never repurposed (ADR-006)."""
    return {
        "v": SCHEMA_VERSION,
        "provider": provider,
        "ts": None,             # ISO-8601 UTC, start of the turn
        "session": None,        # short opaque session id
        "workspace": None,      # basename of working dir — never a full path
        "repo": None,           # resolved repository name (ADR-008) — a label, not a path
        "surfaces": [],         # coarse in-repo buckets this turn touched, e.g. "project:sls"
        "branch": None,
        "entrypoint": None,     # desktop app | cli | sdk — the surface the turn came from
        "lane": None,           # work | personal — inferred, see engine/topology.json
        "model": None,
        "effort": None,         # reasoning effort, when the provider reports it
        "tier": None,           # service tier
        "speed": None,          # standard | fast — fast mode is priced differently
        "sidechain": False,     # True when the turn belongs to a subagent
        "agent": None,          # subagent type/slug, when the provider names it
        "turn": 0,              # 1-based index of this turn within the session
        "input": 0,             # uncached input tokens
        "output": 0,
        "cache_create": 0,
        "cache_read": 0,
        "cache_1h": 0,          # of cache_create, written at 1h TTL
        "cache_5m": 0,          # of cache_create, written at 5m TTL
        "tools": [],            # tool names invoked in this turn
        "web_search": 0,
        "web_fetch": 0,
        "stop": None,           # stop_reason
    }
