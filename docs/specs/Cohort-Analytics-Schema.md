# Spec — Cohort analytics schema

Companion to [ADR-010](../adr/ADR-010-Cohort-Analytics-Store.md), which carries
the reasoning. This file is the field list.

Store: the server's record store (`table(name)` — `get / list / create / update / upsert /
delete`). No joins, no aggregates. All arithmetic happens in `backend/main.py`.

## Key derivation

All from `OBSERVATORY_HMAC_SECRET`; nothing stored.

```
uid   = HMAC("uid",       email)[:24]   # profiles row id      (exists today)
auid  = HMAC("analytics", email)[:24]   # daily row id prefix   (new)
ehash = HMAC("email",     email)[:32]   # confirm a guess, cannot enumerate
bkey  = b64(HMAC("blob",  email))       # personal blob key     (exists today)
skey  = b64(HMAC("server-seal", "v1"))  # server-only seal for email_sealed
```

`uid` ↔ `auid` are not derivable from each other without the secret. Keep it
that way: never store both on the same row.

## T1 `profiles` — one row per person, mutable

Existing fields keep their names and meaning. Additions marked **new**.

| Field | Type | Notes |
|---|---|---|
| `uid` | str | row id |
| `updated` | iso | last sync |
| `agent_version` | str | installed collector |
| `share` | bool | default `true` |
| `blob` | str | Fernet(zlib(digest)) under `bkey`, as today |
| `email_sealed` | str | **new** Fernet(email) under `skey` |
| `email_hmac` | str | **new** `ehash` |
| `share_changed` | iso | **new** when `share` last flipped |
| `consent_version` | int | **new** which copy they agreed to; bump when wording changes materially |
| `first_seen` | iso | **new** |
| `sync_count` | int | **new** |
| `pooling_from` | date | **new** first date eligible to be written to `daily`; set one day ahead on the first sync (see C2 below) |
| `backfilled` | bool | **new** whether the historical window has been written yet |

**Every plaintext numeric aggregate is removed — this is load-bearing, not
cleanup.** The table used to hold `days / turns / input / output / cache_read /
cache_create / sessions / cost_micro` in the clear for the old benchmark. A
person's `daily` rows sum to exactly those numbers, so keeping them would let
anyone who can list both tables match a summed `auid` row-set against a profile
row and recover the `auid` ↔ `uid` link that the two-salt design exists to
prevent. One leaked figure ("I burned about $400 last month") would then attach a
name to a full day-by-day history. Nothing summable may be added back here.

`sync_count` / `first_seen` / `updated` remain, and are weak correlates at best —
almost everyone syncs daily, so they do not single anyone out. The eligibility
gate (≥7 active days) is counted from `daily` rows in the nightly job, not from a
stored total, precisely so no total needs to exist.

## T2 `daily` — one row per person per day, append-only

Row id **`<auid>.<YYYY-MM-DD>`** — deterministic, so a re-uploaded window
upserts in place instead of duplicating.

| Field | Type | Notes |
|---|---|---|
| `auid` `date` | str | |
| `tool_cohort` | str | provider with most turns that day |
| `fingerprint` | str | collector's per-day metric hash; skip the write only when this **and** `price_epoch` match |
| `price_epoch` | int | `pricing.EPOCH` at the time `cost_micro` was computed |
| `turns` `sessions` `input` `output` `cache_create` `cache_read` `cache_1h` `cache_5m` `writes` `reads` `calls` | int | |
| `cost_micro` | int | priced server-side at ingest |
| `active_minutes` | int | summed session spans |
| `models_used` | int | distinct models that day |
| `switch_sessions` | int | sessions using >1 model |
| `peak_context` | int | max `input+cache_read+cache_create` on any turn |
| `by_model` | map | `{model: [turns, in, out, cache_create, cache_read, cost_micro]}` |
| `by_effort` `by_provider` `by_entrypoint` | map | `{value: [turns, out, cost_micro]}` |
| `by_agent_kind` | map | `{"main"\|"sub": [turns, out]}` |
| `by_hour` | int[24] | UTC, as collected |
| `by_tool` | map | `{tool: calls}`, top 25 by calls |

Deliberately **absent**: `workspace`, `session`, `uid`, `org_bucket`, any email
form. A folder name is a team name once pooled, and an org attribute is a named,
bounded roster once pooled — see ADR-010 trade-off 2 for why the latter was
dropped rather than tuned.

## T3 `cohort_daily` — one row per slice per day

Row id **`<slice>.<YYYY-MM-DD>`**. This is the only table the analytics page
reads. Written by a nightly job over the previous day's `daily` rows.

| Field | Type | Notes |
|---|---|---|
| `slice` | str | `all` \| `tool:<provider>` |
| `date` | str | |
| `n` | int | distinct `auid` active that day in this slice |
| `sums` | map | every flat int from T2, summed |
| `hist` | map | `{metric: int[nbuckets]}` — see below |
| `cat` | map | `{dim: {value: turns}}` for model / effort / provider / entrypoint / tool |
| `computed` | iso | |

Not written at all when `n` is below the slice's floor. Suppression happens on
**write**, so a thin slice never exists to be leaked by a rendering bug.

## T4 `key_epochs` — unchanged

`{uid, epoch, updated}`. Hashes and integers only.

## Histogram buckets

Per-metric, fixed, log-spaced, 20 buckets, edges pinned in
`backend/histograms.py` and **never changed in place** — a changed edge silently
corrupts every stored row. To revise, add `hist_v2` alongside.

Metrics bucketed (all per-active-day unless noted): `cost`, `output`, `input`,
`turns`, `sessions`, `calls_per_turn`, `turns_per_session`, `cache_reuse_pct`,
`write_read_ratio`, `active_minutes`, `peak_context`, `models_used`,
`switch_share_pct`, `output_per_turn`, `cost_per_turn`.

Merging a window is elementwise addition of the arrays. Quantile read-off:
accumulate counts to `q × total`, then linear-interpolate inside the landing
bucket. The viewer's own value is never read from a histogram — it comes from
their own `daily` rows, exact.

## Write path

`POST /ingest` (public, signed key — unchanged):

1. `parse_key` → email → `uid`, `auid`. Upsert `profiles` with the sealed blob,
   `email_sealed` / `email_hmac` / `sync_count` — and no numeric aggregate.
2. If `share` is false → stop. Nothing else is written; delete any `daily` rows
   still present for this `auid`.
3. **If this is the first sync ever** (no prior profile) → set
   `pooling_from = tomorrow`, write **no** `daily` rows, and stop. See C2 below.
4. If `today < pooling_from` → stop. Otherwise determine the write set: the
   **last 14 days** always, plus the whole window once if `backfilled` is false.
   Skip any day whose stored `fingerprint` **and** `price_epoch` both match.
5. Upsert those `daily` rows. Set `backfilled = true`.

Bounding step 4 is what keeps steady-state writes at ~14 rows per person per
day instead of 180.

**C2 — the first sync pools nothing, on purpose.** `/me/share` used to 404 when
no profile existed, so consent could only be changed *after* the first upload —
and that upload is what backfills the history. There was no moment at which
someone could decline before their data was pooled, which made the checkbox
decorative for exactly the window that mattered. Now the first sync stores only
the personal blob; pooling begins on the next run, a day later, by which time the
person has seen their dashboard and the consent control on it. `/me/share` also
upserts instead of 404ing, so the choice is recordable at any time.

**Skip-writes must compare a price epoch, not just the collector's
fingerprint.** `fingerprint` covers the day's token counts; it says nothing about
the rate card. A day skipped as "unchanged" after a pricing update would keep a
stale `cost_micro` forever. `price_epoch` is bumped by hand in `pricing.py`
whenever a rate changes, and a mismatch forces a rewrite.

**No `filter` in the documented Python table API** — only `list(page, perPage,
sort)`. So "delete this person's rows" (step 2, and `DELETE /me/data`) must not
be written as a query. It works because row ids are deterministic: iterate the
dates from `backfilled_through` to today and `delete("<auid>.<date>")` each,
ignoring misses. Anything that needs to find rows by a non-id field belongs in
the nightly job's full sweep, not in a request path.

Nightly job (in-process scheduler, idempotent — it may run twice after a
deploy): for each of yesterday and the day before, rebuild every
`cohort_daily` row from `daily`. Two days, not one, so a late sync still lands.

## Read path

`GET /me/analytics?window=30d&slice=all`:

1. `auid` from session email → list this person's `daily` rows in the window
   (≤90 rows). Their own numbers, exact.
2. List `cohort_daily` for `slice` over the same dates (≤90 rows). Sum the
   `hist` arrays, sum `sums`, union `cat`.
3. Return `you` / `cohort` pairs per metric with percentile rank, plus the
   distribution shares for the categorical dims.
4. `cohort.available: false` when the merged `n` is below the floor — one code
   path, not a per-metric one.

`GET /me/dashboard` is unchanged and keeps reading the blob. The personal
dashboard must not depend on the pooled tables, so an opted-out user's page
behaves exactly as it does today.

Owner-only: `GET /admin/optouts` → decrypt `email_sealed` for `share == false`.
Gated on the app owner's email, not merely on being signed in.

## Cohort floors

| Slice | Floor | Also requires |
|---|---|---|
| `all` | 5 | ≥7 active days per participant |
| `tool:*` | 5 | ≥7 active days per participant |

Both at 5, the owner's instruction and today's `MIN_COHORT`. No org-scoped
slice exists to need a separate, higher floor — see ADR-010 trade-off 2 for why
that slice was dropped rather than given one.

## Retention

> **Superseded for the public build.** This section describes the
> single-employer deployment. The open-source design prunes per-user rows at
> **35 days**, because the client holds full history — see
> [Community-Share-Protocol](Community-Share-Protocol.md) and
> [ADR-015](../adr/ADR-015-Hosting-And-Data-Residency.md).


`daily` — prune rows older than **400 days**. `cohort_daily` — keep
indefinitely; it is the company's own trend record and is not reconstructible
once `daily` is pruned. `profiles` — until the user calls
`DELETE /me/data`, which must now also delete that person's `daily` rows
(derivable from their session email) and not merely the profile row.

## See also

- [ADR-010](../adr/ADR-010-Cohort-Analytics-Store.md) — the reasoning, the
  options rejected, and the trade-offs accepted for everything above.
- [ADR-006](../adr/ADR-006-Metadata-Only.md) — the metadata-only rule this
  extends. Every prohibition there still holds.
- [Event-Schema](Event-Schema.md) — the per-turn shape the collector produces,
  upstream of every field here.
- [Cost-Estimation](Cost-Estimation.md) — how `cost_micro` is derived.
- [Known-Limitations](../context/Known-Limitations.md) — where the pseudonymity
  limit belongs once this ships.
