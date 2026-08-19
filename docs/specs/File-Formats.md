# Spec — File Formats

Everything the tool reads and writes. Nothing here is committed to git except code and docs.

## Read (never written)

| Path | Format | Notes |
|---|---|---|
| `~/.claude/projects/<slug>/<session>.jsonl` | NDJSON | Main session transcripts. One record per line; `type: "assistant"` records carry `usage`. |
| `~/.claude/projects/<slug>/<session>/subagents/agent-*.jsonl` | NDJSON | Delegated turns. Carry the **parent** `sessionId`, plus `isSidechain: true` and an agent `slug`. |

Both are provider-owned and opened read-only.

## Written

### `data/events-YYYY-MM.ndjson` — the store

Append-only, one normalized event per line, partitioned by month of `ts`. Undated events go to `events-unknown.ndjson`. Schema in `Event-Schema.md`. Compact separators, full-word keys.

```
{"v":1,"provider":"claude-code","ts":"2026-08-02T09:15:22.000Z","session":"68ec0087",…}
```

### `data/.cursors.json` — sync state

`{"<provider>:<absolute source path>": {"offset": <bytes>, "turn": <int>}}`

Written atomically (temp file then `replace`). Local-only and never committed — it contains absolute paths, which is exactly why `data/` is gitignored. Deleting it is safe: the next `--full` run rebuilds the store from source.

### `data/digest.json` — the read surface

~210 KB aggregate plus findings. The only thing consumers read (ADR-005). Keys: `schema`, `window`, `totals`, `sidechain`, `by_day`, `by_model`, `by_workspace`, `by_repo`, `by_surface`, `by_lane`, `by_provider`, `by_entrypoint`, `by_effort`, `by_agent`, `by_tool`, `by_hour`, `sessions`, `cube`, `hours`, `tools`, `findings`, `generated_at`, `pricing_verified_on`.

The `by_*` lists are pre-rolled for the whole window — what the detectors and a
model-assisted read consume. The three cubes are for the browser.

### Cubes — `cube`, `hours`, `tools`

A dictionary-encoded fact table, so the dashboard can re-aggregate for an arbitrary
date range without a server or a second file.

```json
{ "dims":    ["date","provider","lane","entrypoint","repo","surface","model","effort","agent"],
  "metrics": ["turns","input","output","cache_create","cache_read","cache_1h",
              "cache_5m","cost_micro","writes","reads","tool_calls"],
  "vals":    { "date": ["2026-08-01", …], "repo": ["acme-platform", …], … },
  "rows":    [[0,0,0,0,1,4,2,0,0,  312, 1204, 88231, …], …] }
```

A row is `[…dim codes, …metric values]`. A dim code indexes `vals[dim]`. Costs are
integer **micro-dollars** (`cost_micro / 1e6` = USD) so a row is all integers.
`hours` and `tools` carry the coarser `(date, provider, lane, repo)` key plus `hour`
or `tool`, which is why only those four are offered as page-wide slicers.

Missing values are named per dimension: `unattributed` for `repo`/`surface`, `unset`
for `effort`, `unknown` elsewhere. Every cube reconciles exactly against `totals`.

### `dist/observatory.html` — the report

Single self-contained file, ~80 KB. Inline CSS and SVG, no scripts from another origin, zero external requests. The digest is embedded in a `<script type="application/json" id="digest">` block so the page is also a portable data carrier — one file holds both the view and the numbers behind it.

### `engine/pricing.json` — the cost model

Hand-editable. Per-MTok rates by canonical model alias, cache multipliers, fast-mode overrides, and a fallback. `_verified_on` is surfaced in the report footer. Committed, because it is configuration rather than data.

## Git policy

| Path | Committed | Why |
|---|---|---|
| `engine/`, `docs/`, `README.md` | yes | Source and documentation |
| `engine/pricing.json` | yes | Configuration the owner tunes |
| `data/` | **no** | Derived; contains absolute paths in cursors; rebuildable with `--full` |
| `dist/` | **no** | Generated on demand; already covered by the repo-wide `dist/` ignore |

The store is deliberately **not** committed even though this repo is private. It is derived data that regenerates in 3.5 s, and committing 5.7 MB of it per rebuild would bloat history for no gain.
