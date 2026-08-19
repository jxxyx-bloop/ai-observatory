# Spec — Event Schema

One normalized event per **assistant turn** — the atomic billable unit. Defined in code by `collectors/base.py::blank_event()`; that function is the source of truth and this document explains it.

## Fields

| Key | Type | Meaning |
|---|---|---|
| `v` | int | Schema version. Currently `2`. |
| `provider` | str | `claude-code` \| `codex`. Set by the collector. |
| `ts` | str | ISO-8601 UTC, start of the turn. |
| `session` | str | Short opaque session id (first 8 chars). Subagent turns carry the **parent** session. |
| `workspace` | str | **Basename** of the working directory. Never a full path (ADR-006). |
| `repo` | str\|null | Repository the turn is about — where it ran, else the first real repository it touched. A derived label, never a path (ADR-008). |
| `surfaces` | list[str] | Coarse buckets inside `repo` this turn touched, e.g. `app:checkout`, `people`. Empty when the turn named no file. |
| `branch` | str | Git branch, when the provider records it. |
| `entrypoint` | str\|null | `desktop` \| `cli` \| `ide` \| `sdk` — the surface the turn came from. |
| `lane` | str | `work` \| `personal`. **Inferred** from `engine/topology.json`; no provider reports account identity. |
| `model` | str | Canonical model alias. Dated snapshots folded to the alias by the collector. |
| `effort` | str\|null | Reasoning effort, when reported. |
| `tier` | str\|null | Service tier. |
| `speed` | str\|null | `standard` \| `fast`. Fast mode is priced differently. |
| `sidechain` | bool | True when the turn belongs to a delegated subagent. |
| `agent` | str\|null | Subagent type/slug, when the provider names it. |
| `turn` | int | 1-based index of this turn within its source file. |
| `input` | int | Uncached input tokens (full rate). |
| `output` | int | Output tokens. |
| `cache_create` | int | Tokens written to cache. |
| `cache_read` | int | Tokens served from cache (0.1× rate). |
| `cache_1h` | int | Of `cache_create`, written at 1h TTL (2× rate). |
| `cache_5m` | int | Of `cache_create`, written at 5m TTL (1.25× rate). |
| `tools` | list[str] | Tool **names** invoked this turn. Argument *values* are never stored; path-shaped arguments are read only to derive `repo`/`surfaces` (ADR-008). |
| `web_search` | int | Server-side web-search requests. |
| `web_fetch` | int | Server-side web-fetch requests. |
| `stop` | str\|null | Stop reason. |

## Invariants

- **Total prompt size** for a turn = `input + cache_create + cache_read`. `input` alone is the uncached remainder, not the prompt size — reading it as the latter understates context by an order of magnitude on a cached session.
- `cache_1h + cache_5m` **may be 0 while `cache_create` > 0** when the provider does not report the split. Consumers must handle this; `analyze.py::cost_of` prices an unsplit write at the cheaper 5m rate rather than overstating cost.
- A turn with no `usage` object is dropped, not emitted with zeros.
- Subagent turns share the parent's `session`, so a session rollup includes its delegated work.
- `repo` may be null and `surfaces` empty. `analyze.py::resolve_attribution` fills the gaps at digest time from neighbouring turns **in the same session** and writes the single winning bucket to a derived `surface` key; whatever it cannot fill stays `unattributed`. The stored event is never rewritten.
- Codex reports cached input *inside* its input count and reasoning *inside* its output count. The collector subtracts the former into `cache_read` and leaves the latter in `output`, so `input`/`output` mean the same thing across providers.

## Never present, by design

Prompt text · completion text · thinking content · file contents · tool argument values · shell commands · absolute paths · session titles. See ADR-006 and ADR-008.

## Evolution rules

Additive only (Principle 12). New keys may be appended; existing keys are never renamed, removed, or repurposed. Bump `v` only on a genuine breaking change, and keep old partitions readable.
