# Known Limitations

Honest list. Anything here is a constraint to plan around, not a bug to file.

## Data the source does not contain

| Missing | Consequence |
|---|---|
| **Per-turn wall-clock duration** | Cannot measure latency or wait time. Timestamps give turn *start* only. |
| **Human think-time** | Gaps between turns conflate thinking, meetings, and lunch. Session "duration" is start→end, not effort. |
| **Account identity** | No account field exists in any transcript. See "Account and lane" below — partly worked around, not solved. PRD 01 F9 and PRD 03 F9 remain blocked. |
| **Quota / rate-limit state** | No quota forecasting is possible (PRD 03 F8). |
| **Whether the work was any good** | The deepest gap — see below. |

## Account and lane

Three separate questions, with three different answers.

**Does personal claude.ai chat show up here? No, and it cannot.** Browser and
desktop-*chat* conversations are stored server-side; nothing on this machine holds
their token counts. `~/Library/Application Support/Claude` is an Electron shell —
caches and cookies, no usage record. Every number in this tool comes from an
agentic tool that writes a local transcript: Claude Code and Codex. There is no
collector to write, only an API that does not exist locally.

**If Claude Code itself is run under a personal login, does it show up? Yes —
silently blended.** `~/.claude/projects/**` is written the same way regardless of
which account is signed in, and the transcript records no account. `~/.claude.json`
holds exactly one `oauthAccount`: whoever is logged in *right now*. Historical turns
carry nothing.

**What can be distinguished.** `entrypoint` is real and recorded per turn —
`desktop`, `cli`, `ide`, `sdk`. So "desktop app vs everything else" is a fact.
`lane` is a rule, not a fact: the mapping in `engine/topology.json` assigns a lane
from repository, entrypoint, and provider, and defaults to `work`. It is exactly as
correct as the rules written into it. See
[Surface-Attribution](../specs/Surface-Attribution.md).

## Coverage gaps by provider

- **Kimi Code's record schema is verified as of 2026-08-10 — and the first
  version of it was wrong.** The collector shipped on 2026-08-10 assumed
  `wire.jsonl` held API-response records with a `usage` object and an ISO
  `ts`. It does not: it is an *event-sourced op log*
  (`{"type": <op>, "time": <epoch_ms>, …}`) where token usage rides on the
  `step.end` loop event as the engine's own four-component `TokenUsage`
  (`inputOther` / `output` / `inputCacheRead` / `inputCacheCreation`), and
  the model is carried by separate `config.update` records. The result was a
  collector that parsed every file and emitted **zero** turns — Kimi Code
  simply never appeared in the dashboard, indistinguishable from not using
  it. Re-derived on 2026-08-10 from readable source strings in the installed
  `kimi` binary (wire protocol 1.4/1.5) and pinned by
  `engine/tests/test_kimi_code.py`. Still worth re-checking on a Kimi CLI
  major upgrade: the wire protocol version is stamped in each log's
  `metadata` record.
- **Kimi Code reports no cache-TTL split.** The wire carries a single
  `inputCacheCreation` counter with no 1h/5m breakdown, so `cache_1h` and
  `cache_5m` are always 0 and `analyze.py`'s unsplit-write guard prices the
  writes at the cheaper 5m rate rather than overstating cost.
- **Codex is a historical archive, not a live feed.** `~/.codex/sessions/` holds 31
  rollouts spanning 2026-05-02 → 2026-07-07 and nothing since. `logs_2.sqlite` keeps
  running to the present, but it is tracing output with no token accounting. If Codex
  is being used now and not appearing, the rollout store is the thing to check first.
- **Codex reports no cache writes.** `cache_create` is always 0, so cache-efficiency
  findings apply to Claude Code only.
- **Codex turn boundaries are inferred** from the delta between consecutive
  cumulative token totals. Repeated snapshots are dropped; a turn that genuinely
  spent nothing is indistinguishable from a repeat and is also dropped.

## Deliberate blind spots (ADR-006)

Because content is never stored, these are out of reach:

- "You read the same file five times in one session" — needs tool arguments.
- "This session produced the BRD" — needs to know what was written.
- "This prompt was badly framed" — needs prompt text.

Proxies are used instead (writes-to-reads, peak context, session shape) and labelled as proxies. This trade is intentional and not up for revision.

## The pooled comparison is pseudonymous, not anonymous (ADR-010)

The community server's comparison page pools per-day counts from everyone opted in,
keyed by `auid = HMAC("analytics", email)` — a second id, distinct from the
`uid` that keys a person's own consent record, so the two cannot be joined by
anyone reading the tables. That is real, and it is also not the same claim as
"anonymous."

`auid` is **stable across syncs on purpose** — trends require it. A reader with
table access, no email, and no folder name still sees one consistent stranger's
day-by-day pattern: which models, which hours, how much. A colleague who already
knows something distinguishing — "the only person on this team who runs a
2 a.m. schedule," a tool mix mentioned in standup — could match that pattern to
a name. Accepted deliberately in ADR-010 trade-off 1: rotating the key would
stop this, and would also destroy the product, since a row-set that cannot be
sequenced cannot show a trend. Not mitigated further here; stated as a known
position rather than left as an unstated assumption.

This is also why an org-scoped cohort slice was considered and dropped rather
than shipped at a higher floor ([ADR-010](../adr/ADR-010-Cohort-Analytics-Store.md)
trade-off 2, restated in [ADR-011](../adr/ADR-011-Community-Layer.md)) — a
numeric floor bounds group *size*, not whether a colleague can *name* the
group's members.

## The value-attribution gap

The tool measures **where effort went** precisely and **what it produced** barely at all. `writes/reads` treats an Edit as output and a Read as input, which:

- counts a one-line typo fix the same as a substantial refactor;
- reads a long research session that correctly concluded "don't build this" as pure waste;
- cannot see work that landed outside the filesystem (a decision, a conversation, a review).

Every finding that touches value — `read-heavy-no-change` above all — inherits this. Treat those as prompts to think, not verdicts. Closing it is Phase 3.

## Measurement artefacts

- **`<synthetic>` turns** appear as a model with zero tokens — internal placeholders. Visible in the model breakdown, and excluded from a session's model set so they cannot make a compacted session read as a model switch.
- **Model-switch share counts subagent turns.** A session where only a subagent ran a smaller model counts as a switch, because the rollup sees two distinct models and cannot tell a deliberate choice from a delegation default.
- **The behavioural sparklines are a 7-*calendar*-day rolling mean.** Quiet days are skipped rather than counted as zero, so a sparse trailing week leaves the headline resting on very few days. The card names the basis when fewer than four active days are behind it; read the whole-range figure alongside it.
- **The timezone follows the machine, and a rendered page does not.** Dates and hours are resolved when the digest is
  built, per timestamp, so DST is handled correctly on both sides of a changeover. But the result is baked into the
  digest — open that same `observatory.html` on a laptop in another zone and it still shows the hours it was built
  with. Re-run `digest` there to move it. Pinning `timezone_offset_hours` to a number opts out of all of this,
  including the DST handling, which is the point of pinning.
- **Session ids are truncated to 8 characters.** Collision is unlikely, not impossible; two colliding sessions would merge in the rollup.
- **`workspace` is a directory basename**, so two unrelated directories with the same name merge (any two folders called `docs`). Deliberate — the full path is not stored. `repo` (ADR-008) is the field to group by; `workspace` is kept for continuity.
- **`repo` and `surface` are inferred, not observed.** Only tools that name a file contribute directly; `Bash`-driven work relies on the session carry-forward. A turn credited to a project sat next to one that touched it.
- **Turns before a session's first file touch are back-filled**, so the opening minutes of a session are attributed to wherever it went next. Usually right, occasionally not.
- **`turn` is per source file**, so a subagent's numbering restarts at 1 rather than continuing the parent's sequence.
- **Cost is an estimate.** See `specs/Cost-Estimation.md`.

## Operational fragility

- **Undocumented source format.** A provider change can break parsing (ADR-004, accepted). Defensive parsing limits the damage to new data, never history.
- **Thresholds tuned on one person's 56 days.** Starting points, not norms — recalibrate in Phase 2.
- **Transcript deletion is unrecoverable before a first sync.** After sync, the store holds the history independently — one of the reasons the store exists.
- **No automated tests yet.** Verification so far is manual: full rebuild, incremental no-op, and browser render at two widths in two colour schemes. A regression suite belongs in Phase 2.

## Added on open-sourcing (2026-08-19)

### Peak/off-peak schedules are hand-maintained and whole-hour

The windows in `pricing.json` are transcribed from vendors' public pricing pages
and verified on a date recorded in the file. A vendor can change one without
notice, and DeepSeek changed its billing *shape* mid-2026. Windows are also
expressed in whole UTC hours; a schedule with a half-hour edge is mispriced for
turns landing in it. The error is bounded and small, and correcting a window is
a one-line PR — but a number here can be stale, and the footer's
`_verified_on` is the honest guide to how much to trust it.

### The plan model is single-plan

`settings.plan` holds one id. The multi-vendor pragmatist — three subscriptions,
no idea which is carrying its weight — is the most interesting user this project
has and the least well served today. Per-vendor plan attribution is roadmapped,
not built.

### Quota headroom is inferred, not read

Consumption against a quota is inferred from turn counts, not read from a vendor
API. Where a vendor exposes a live limit — Claude Code's statusline `rate_limits`
being the clearest case — reading it directly is strictly better and is not yet
done. Credit-denominated quotas (GLM) additionally involve a vendor-defined
credits-per-token conversion that is not modelled at all, so credit headroom is
an estimate flagged as such.

### Currency conversion is indicative

FX rates in `plans.json` are hand-maintained and will drift. They are a display
lens; most vendors settle in USD. The `daily_dev_rate_usd` figures behind the
"that is N days of a local contract rate" framing are coarse regional medians
chosen to start a conversation, not salary data — do not cite them as such.

### Declarative collector specs can be silently wrong

A spec that reads the wrong counter produces plausible numbers rather than an
error, because dotted-path lookups return null instead of raising. Only the
fixture catches this, which is why a spec is not merged without one
([ADR-009](../adr/ADR-009-Collectors-Ship-With-A-Fixture.md)). If you contribute
a spec, the fixture is the contribution — the JSON is the easy half.

### The community layer is specified, not built

Everything in [Community-Share-Protocol](../specs/Community-Share-Protocol.md)
and [Auth](../specs/Auth.md) describes a design. `observe.py share` builds and
audits a payload locally and has no network code path at all. Nothing has been
deployed, nothing has been reviewed by a second person, and no cohort statistics
exist. Treat those documents as intent.
