# ADR-010 — Store per-user analytics facts to power cohort comparison

**Status:** accepted · **Date:** 2026-08-10 · **Extends:** [ADR-006](ADR-006-Metadata-Only.md) · **Extended by:** [ADR-011](ADR-011-Community-Layer.md)

> **Provenance.** This record was written for a single-employer deployment where
> the server operator and every participant shared an employer, and it is kept
> because its reasoning — the join-key flaw, the backfill-before-consent flaw,
> why histograms compose and percentiles do not, and why an org-scoped cohort was
> dropped rather than tuned — is the intellectual basis of this project's
> community layer. Platform specifics have been generalised.
> [ADR-011](ADR-011-Community-Layer.md) states where the public design departs
> from it: metrics are now bucketed **on the device**, because in a public
> project the operator is a stranger rather than a colleague.

## Context

The Observatory's comparative panel shares **four numbers** and holds them back
below five participants. It is the least useful part of a product whose whole
premise is that a mirror changes behaviour, because a four-metric percentile
against an anonymous median tells nobody what to do differently.

The blocker is not collection. `observatory_agent.py build_digest()` already
uploads the full cube — 7 dimensions (`date, provider, workspace, model, effort,
entrypoint, agent`) × 10 metrics (`turns, input, output, cache_create,
cache_read, cache_1h, cache_5m, writes, reads, calls`), plus an hours cube, a
tools cube, and up to 400 sessions. Every metric on the wish list — model,
effort, turns, context reuse, read/write, tool calls, spend, time-of-day
pattern — is **already in the payload today**.

The blocker is what `_store()` in `backend/main.py:673` does with it: it reduces
that payload to nine plaintext scalars for the benchmark and seals the rest into
a `blob` readable only by a key derived from the uploader's own email. One row
per person, overwritten on every sync. So the store holds **a snapshot, not a
history**, and nothing at a grain that supports comparison.

Two hard constraints shape any fix:

- **The store is a record store, not a database.** `table(name)` offers
  `get / list(page, perPage, sort) / create / update / upsert / delete`. There is
  no `GROUP BY`, no aggregate function, no server-side percentile. Every
  aggregation happens in Python over rows we listed ourselves.
- **App tables are readable by any signed-in user** through the protected
  data routes (`runtime/routing.md`: "Public apps can be opened by any signed-in
  user"). This is why encryption at rest is load-bearing today, and it does not
  stop being true because the rows get more interesting.

## Decision

Field-by-field schema in
[Cohort-Analytics-Schema](../specs/Cohort-Analytics-Schema.md); this section is
the shape and the reasons.

### 1. The collector barely changes

No new reading, no new privacy surface. Four additions, all derived from events
already parsed: `sessions_by_date`, `active_minutes` per day, `peak_context` per
day, and a per-day `fingerprint` (a short hash of that day's metrics) so the
server can upsert only the days that actually changed. Version bump to 1.4.0.
Nothing on the wish list requires a new collector capability.

### 2. Three tables, two salts

Identity stays derived, never stored — but it is now derived **twice, under
different labels**:

| Label | Value | Used as | Table |
|---|---|---|---|
| `uid` | `HMAC("uid", email)[:24]` | consent + personal blob key | `profiles` |
| `auid` | `HMAC("analytics", email)[:24]` | analytics fact key | `daily` |

`uid` and `auid` are not computable from one another without
`OBSERVATORY_HMAC_SECRET`. A reader who can list both tables therefore **cannot
join a person's fact rows to the profile row holding their consent record and
sealed email**. That unlinkability is the reason the fact rows can stay
plaintext, and it costs one extra HMAC per request.

No org attribute is stored on either table. See trade-off 2 below — an org-scoped
slice was considered and dropped before implementation, not merely deferred.

**No plaintext aggregate survives on `profiles`.** The first draft of this ADR
kept the existing benchmark totals there. That was a hole: a person's `daily`
rows sum to exactly those totals, so a reader who can list both tables recovers
the `auid` ↔ `uid` link by matching sums — defeating the whole two-salt design,
and needing only one number said out loud in a standup to attach a name to it.
Benchmarking moves to `cohort_daily`, which makes the totals redundant, so they
are deleted rather than sealed. Nothing summable goes back on that table.

### 3. The pre-aggregation ladder

A third table, `cohort_daily`, holds one row per slice per day: participant
count, metric sums, and a **fixed-bucket histogram per metric**. Reads go to
this table; the raw `daily` rows are only ever touched by the nightly job that
builds it and by the owner of those rows.

Histograms because **percentiles do not compose and histograms do**. A 30-day
cohort p50 cannot be recovered by averaging thirty daily p50s, but it is exact
from thirty summed bucket-count arrays. This is what makes any window — 7, 30,
90 days, quarter-over-quarter — answerable at O(days × slices) reads instead of
O(users × days).

### 4. Consent semantics

Opt-in (default) → blob **and** `daily` rows. Opt-out → blob only, exactly the
status quo, and any existing `daily` rows for that `auid` are deleted. The
pooled table then holds nothing of theirs, which is a consent story that can be
stated in one sentence on the checkbox.

The opt-out is recorded on `profiles` as `share: false` alongside
`email_sealed` — the email encrypted under a **server-derived** key, not the
user's own, so the backend can answer "who opted out" while no browser session
can read the roster.

## Options considered

### Grain of the fact table

| Option | Rows at 1,000 users / year | Why not / why |
|---|---|---|
| **A. Wide row per person** (extend today's `profiles`) | 1,000 | Cheapest, and wrong: no history. "Is my context reuse improving?" and every trend chart are unanswerable, and a rebuilt digest silently rewrites the past. |
| **B. `uid × date`** ← chosen | 365,000 | One row per person-day. Trends, any window, and per-day distributions all fall out. Categorical breakdowns ride as small nested maps rather than extra rows. |
| **C. `uid × date × model`** | ~2,200,000 | 5–8× B for one dimension already answerable from B's `by_model` map. Multiply again for effort and entrypoint and the fact table stops being listable at all. |

The tipping factor is checkable: option A cannot produce a rolling mean, and
option C's row count exceeds what `list(perPage=200)` can sweep for a 30-day
window (11,000+ calls) while adding no metric B lacks.

### How the cohort pool is computed

| Option | Cost per page view at 1,000 users | Verdict |
|---|---|---|
| **Live scan of `daily`** (today's `_pool()` shape) | 30-day window = 30,000 rows = **150 `list()` calls** | Rejected. `_all_profiles()` already caps at 40 pages × 200 = **8,000 rows**, a ceiling the fact table crosses at ~200 users × 40 days. A 600s cache hides it until the first cold read after a deploy. |
| **Sums-only nightly rollup** | ~30 rows | Rejected on its own: gives means, cannot give percentiles, and percentile rank is the entire point of a comparison page. |
| **Histogram ladder** ← chosen | 30 days × 19 slices ≈ **570 rows, ~3 `list()` calls** | Composes exactly across any window. Cohort p50/p90 accurate to one bucket (log-spaced, ≈12% width); the viewer's **own** value stays exact because it comes from their own row, and their percentile rank is exact except within their own bucket. |

### Cohort slices

| Option | What it unlocks | Why not / why |
|---|---|---|
| **A. Company-wide + tool cohort** ← chosen | "vs everyone" and "vs people who mostly use the same client/model as you" | Both slices are derived entirely from data already collected (`provider`/`model` per day). No new attribute is stored, so there is no new re-identification surface to defend. |
| **B. Add a coarse org bucket** (considered, then dropped) | "vs my org" — usually the comparison people actually want | Rejected before implementation. An `org` slice at any workable cohort floor is a **known, bounded group** — unlike "everyone" or "tool users," a colleague can often name the org's members. Combined with ~15 visible metrics (not the old panel's 4), that turns "you're at the 80th percentile" into "you're at the 80th percentile among these five named people," which is elimination-friendly in a way the other two slices are not. |
| **C. Company-wide only** | Status quo scope, on a richer table | Considered as the conservative fallback if B were dropped and A's tool cohort also felt too granular. Superseded by A once the tool cohort was confirmed safe — it adds real value (A) at no extra storage cost over C. |

The tipping factor for dropping B: cohort size and "is this group nameable" are
different axes, and a numeric floor only controls the first one. Raising the
floor (10, 20, higher) shrinks the group being described but does not stop a
reader who already knows the org's roster from doing elimination against
whatever floor is set — it only raises how many names they need to rule out.
Company-wide and tool-cohort slices don't have this problem because "everyone"
and "people who mostly use Claude Code" are not enumerable rosters a colleague
holds in their head.

### Where the opt-out email lives

- **Plaintext `email` column** — rejected. Any signed-in user could list
  the opt-out roster, which turns a privacy control into a disclosure.
- **`email_hmac` only** — rejected as insufficient for the stated requirement:
  it confirms a guessed address but cannot enumerate who opted out.
- **`email_sealed` under a server-derived key, plus `email_hmac`** ← chosen.
  Enumerable by the backend, opaque to every browser. Recovery after a secret
  rotation is by the user's next sync, same as the existing blob.

## Trade-offs accepted

1. **The fact rows are pseudonymous, not anonymous.** `auid` is stable across
   syncs — that is what makes trends possible. A determined reader with table
   access, no email and no folder names still sees one consistent stranger's
   day-by-day pattern, and a colleague who knows someone is the only Kimi Code
   user on a 2 a.m. schedule could guess which stranger. Accepted because the
   alternative (rotating the key, so rows cannot be sequenced) destroys the
   product. Not mitigated further; stated here so it is a known position rather
   than an assumption.
2. **No org-scoped cohort.** An earlier draft of this ADR stored `org_bucket` and
   split the cohort floor (5 company-wide, 10 for `org:*`) to manage the
   inference risk. The owner decided the risk isn't worth managing — it's worth
   removing: raising a numeric floor shrinks the *group* an org slice describes
   but does not stop a colleague who already knows the org's roster from doing
   elimination against it. **Dropped instead of tuned.** Comparison ships as
   company-wide (`all`, floor 5, per the owner's instruction) plus a tool cohort
   (`tool:<provider>`) — both derived from data already collected, neither an
   enumerable roster. What this loses: "how do I compare within my own team,"
   which is probably the comparison people want most. Revisit only if a
   materially different anonymization approach (k-anonymity beyond a raw floor,
   differential privacy noise) is judged worth the added complexity — not by
   re-adding `org_bucket` at a higher floor.
3. **Bucket-width error on cohort percentiles.** Displayed cohort medians are
   accurate to a log-spaced bucket (≈12%), not exact. Acceptable for a
   comparison ("you are around the 70th percentile"), not for an invoice — the
   same framing this project already applies to cost everywhere else.
4. **365,000 fact rows per year at 1,000 users.** `daily` is pruned at **400
   days**; `cohort_daily` is kept indefinitely (~7,000 rows/year across 19
   slices). What pruning loses: the ability to recompute a >400-day-old cohort
   slice that was never snapshotted. What it does not lose: any individual's own
   long history, which lives in their blob and on their own laptop.
5. **Backfill writes history under a consent given today** — but not before the
   person has had a chance to refuse. The first draft backfilled on the first
   sync, which was unsound: `/me/share` 404s with no profile, so consent was
   unchangeable until *after* the upload that pooled 180 days. The first sync now
   stores only the personal blob and sets `pooling_from = tomorrow`; pooling
   starts on the next run, after the dashboard and its consent control have been
   seen. Cost: one day of pooling latency per new user. The consent copy must
   still say the pool includes usage from before the box was ticked, because from
   the second sync onward it does.
6. **A skipped day can carry a stale price.** `fingerprint` alone would freeze
   `cost_micro` across a rate-card change, so `price_epoch` is compared too and a
   pricing bump forces a rewrite of every day on the next sync. That makes the
   first sync after a pricing change write the full window rather than 14 days —
   deliberate, and the reason `pricing.EPOCH` is bumped by hand rather than
   derived from the file's contents.

## Supersedes chain

The original deployment's own design document carried two privacy decisions that
this record partially reversed:

- *"Rows are keyed by an opaque id, never by email"* — **partially reversed.**
  Fact rows are still keyed by an opaque id and hold no email. The profile row
  additionally holds a server-sealed email so opt-outs are attributable.
- *"The comparison is four numbers and nothing else"* — **replaced.** The
  comparison became a full metric set against composed histograms.

[ADR-006](ADR-006-Metadata-Only.md) is **extended, not weakened.** Every
prohibition holds: no prompt text, no completions, no paths, no command strings.
Pooled rows additionally exclude workspace names and session ids, which ADR-006
and ADR-008 permit in the *personal* store, because a folder name is a team name
once it is pooled.

### Two flaws this record shipped with, found in review before any code was written

Recorded because both were introduced by its own first draft and would have been
live otherwise. They are the reason this document is worth keeping:

- **The plaintext totals on the profile row were a join key.** A person's fact
  rows sum to exactly those totals, so anyone able to list both tables could
  recover the link the two-salt design exists to prevent — needing only one
  figure said out loud in a standup to attach a name to a full history. Fixed by
  deleting them.
- **Backfill preceded any chance to opt out.** Consent could only be changed
  *after* the upload that backfilled the history, which made the checkbox
  decorative for exactly the window that mattered. Fixed by `pooling_from`.

## Carry-forward

`daily` row ids are `<auid>.<YYYY-MM-DD>` on purpose — the collector re-uploads a
180-day window every sync, so any non-deterministic id would write 180 duplicate
rows per person per day.
