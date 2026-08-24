# Decision Log

Index of Architectural Decision Records. Full record for each in `adr/`. Status: **accepted** unless noted.

| ADR | Decision | Why it mattered | Status |
|---|---|---|---|
| [001](adr/ADR-001-NDJSON.md) | NDJSON for the store, not SQLite | Inspectable with `head`, appendable without a schema migration, trivially migratable later | accepted |
| [002](adr/ADR-002-Local-First.md) | Local-first; no server, no sync, no account | The data is a behavioural record of its owner. Anything that leaves the machine needs a justification that does not exist yet | accepted |
| [003](adr/ADR-003-Provider-Abstraction.md) | One `Collector` interface; unified event schema | The second provider is what proves the abstraction. Building it after three providers hard-code their quirks costs 10× | accepted |
| [004](adr/ADR-004-Zero-Token-Collection.md) | Read provider transcripts; never instrument the conversation | **The decision the product rests on.** Collection is free, so measurement can be continuous rather than rationed | accepted |
| [005](adr/ADR-005-Digest-Tier.md) | Pre-aggregate to a ~60 KB digest | Makes model-assisted analysis affordable: kilobytes read, not megabytes | accepted |
| [006](adr/ADR-006-Metadata-Only.md) | Store metadata, never content | Privacy by construction, and the reason the store is 40× smaller than its source | accepted |
| [007](adr/ADR-007-Honest-Findings.md) | Rule-based findings with confidence and a materiality gate | A tool that manufactures problems to look useful destroys its own credibility | accepted |
| [008](adr/ADR-008-Derived-Path-Labels.md) | Read paths to derive a repo + folder label; store neither path | The top spend bucket was `GitHub` — the folder holding every repo. Amends ADR-006: argument *values* are still never stored | accepted |
| [009](adr/ADR-009-Collectors-Ship-With-A-Fixture.md) | No collector ships without a fixture test asserting a non-zero event count | The Kimi collector parsed a schema that doesn't exist and returned an empty list on every machine. A collector that finds nothing looks exactly like a provider you don't use | accepted |
| [010](adr/ADR-010-Cohort-Analytics-Store.md) | Add `daily` (per-person-day facts, unlinkable salt) + `cohort_daily` (pre-aggregated histograms) tables to power a dedicated cohort-comparison page | The four-number benchmark, held back below 5 participants, was the least useful part of the product — everything on the wish list was already in the uploaded cube, just discarded at store time | accepted |
| [016](adr/ADR-016-Design-System-And-Localisation.md) | One token file for every surface; a static page per locale; every README figure generated | Two stylesheets had already copied the same palette by hand, the regional wedge shipped in English only, and the README's counts were restated in four places | accepted |
| [017](adr/ADR-017-Dashboard-Shell-And-The-Meter.md) | A side rail, one weekday×hour grid with peak windows drawn on it, a calendar heatmap — and no 3D | The page had no landmarks, two charts answered the same question in different panels, and the daily bars structurally cannot show a year | accepted |
| [018](adr/ADR-018-Launch-Surface-And-First-Run.md) | One command installs everything; the launcher is a locally *generated* app, not a downloaded one; the page dates itself | Setup was three pastes and a printed file path, there was no way back to the dashboard tomorrow, and a `file://` page could not say it was a week old | accepted |
| [019](adr/ADR-019-Staying-Current.md) | Fetch daily and unattended; fast-forward at the next launch; show what arrived | An install from July was still running July's code, and a stale rate card does not degrade the product, it makes it confidently wrong | accepted |

## Deferred decisions

Recorded so they are not silently re-litigated. Each has a named trigger for revisiting.

| Deferred | Revisit when |
|---|---|
| SQLite / DuckDB backing store | A full digest rebuild exceeds ~10 s, or ad-hoc querying becomes a routine need |
| PostgreSQL, cloud sync | Never for a single user. Only if multi-device history genuinely matters |
| Additional providers (Cursor, ChatGPT export, Gemini) | A passive local source is confirmed to exist for that provider (Principle 2). Codex shipped 2026-08-03 — `~/.codex/sessions/` rollouts |
| Merging personal claude.ai chat usage | A local token record for browser/desktop-chat conversations exists. None does today, so this is not deferred — it is unreachable |
| Packaging for other people | The tool has demonstrably changed the owner's own behaviour at least once (see `00-VISION.md` → Audience) |
| Real-time / streaming ingest | A daily cadence proves insufficient in practice, not in theory |
| Per-outcome value attribution (ROI) | A trustworthy signal for "this session produced value" exists. Writes/reads is a proxy, not the thing |

## How to add an ADR

New file `adr/ADR-NNN-<Kebab-Title>.md` using the existing format: Context → Decision → Consequences → Alternatives considered → Revisit when. Add a row above. Never edit an accepted ADR's decision — supersede it with a new one and mark the old `superseded by ADR-NNN`.
