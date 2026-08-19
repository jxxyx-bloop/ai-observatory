# Spec — community share protocol

What leaves the machine when someone opts in, what the server may do with it,
and what neither side is allowed to hold. Reasoning lives in
[ADR-011](../adr/ADR-011-Community-Layer.md); this is the field list and the
wire contract.

The governing rule: **[`observatory/share.py`](../../observatory/share.py) is
short enough to read in full before you consent.** If it ever stops being that,
the consent has stopped being informed and the file needs splitting, not the
policy relaxing.

## The payload

Built by `share.build(digest)`. Complete example — this is the entire thing,
under a kilobyte:

```json
{
  "v": 1,
  "generated_at": "2026-08-19T09:00:00+00:00",
  "window_days": 60,
  "cohorts": ["id", "solo"],
  "plan": "glm-coding-lite",
  "currency": "IDR",
  "buckets_version": 1,
  "metrics": {
    "turns_per_day": 4, "sessions_per_day": 3, "output_per_day": 5,
    "cost_per_day_usd": 3, "cache_reuse_pct": 8, "turns_per_session": 3,
    "calls_per_turn": 2, "peak_share_pct": 3, "write_read_ratio": 2
  },
  "mix": {
    "vendor": {"deepseek": 41, "anthropic": 30, "zhipu": 18, "moonshot": 11},
    "tier": {"frontier": 52, "mini": 33, "opus": 15}
  },
  "findings": ["cache-healthy", "peak-window-arbitrage", "vendor-mix-healthy"]
}
```

| Field | Type | Notes |
|---|---|---|
| `v` | int | Payload schema version. |
| `generated_at` | iso | Day granularity is enough; the time is not used for anything. |
| `window_days` | int | How many days the metrics summarise. |
| `cohorts` | str[≤4] | **Self-declared**, typed by the user, ≤24 chars each. Never derived from the data — a derived cohort is an inference nobody consented to. |
| `plan` | str | A plan id from `plans.json`, or `"none"`. |
| `currency` | str | ISO code, for regional aggregates. |
| `buckets_version` | int | Which bucket-edge table produced `metrics`. |
| `metrics` | map | **Bucket indices only.** Never a raw value. |
| `mix` | map | Vendor and model-tier shares as integer percentages. |
| `findings` | str[] | Which detector ids fired. Ids only, never their numbers. |
| `repo_shape` | int[] | Only when `include_repo_names` is on, and even then a 64-way hash bucket — never a name. |

### Never present, at any setting

Repository names · folder names · branch names · workspace names · session ids ·
file paths · tool names · tool arguments · prompts · completions · email ·
machine identifier · IP-derived location · any raw token count · any raw dollar
amount.

`share.FORBIDDEN_KEYS` encodes this list and `share.audit()` walks a built
payload against it. The test suite runs that audit and additionally asserts that
no fixture repository name appears anywhere in the serialised payload.

## Why bucket on the device

A server that receives a raw value and promises to bucket it is a server you
have to trust. A server that never receives the raw value is not. Bucketing
before transmission also means a breach of the store leaks bucket indices, which
are the same thing the store was already publishing in aggregate.

Bucket edges are **fixed and versioned**. Changing one in place silently
corrupts every comparison against previously-submitted data; a revision adds
`buckets_version: 2` alongside. Log-spaced because usage across a developer
population spans four orders of magnitude.

## Identity

The account exists for one reason: so a person can be recognised across two
machines and can delete their own data. It is deliberately not used to key the
facts.

```
sub      = the OIDC subject from the identity provider (Google, GitHub)
uid      = HMAC("uid",       sub)[:24]    # account row id
auid     = HMAC("analytics", sub)[:24]    # fact row id
```

`uid` and `auid` are not derivable from one another without the server secret,
and **they must never appear on the same row**. A reader with full table access
therefore cannot join a person's submissions to the account row holding their
consent record. That unlinkability is what lets the fact rows stay in plaintext.

This inherits directly from
[ADR-010](../adr/ADR-010-Cohort-Analytics-Store.md), including the trap it
documents: an earlier design kept plaintext totals on the account row, and those
totals were a join key — a person's fact rows sum to exactly them, so one figure
said out loud in a standup would attach a name to a full history. **Nothing
summable may live on the account row.** This is not cleanup; it is load-bearing.

## Cohort suppression

| Rule | Value | Why |
|---|---|---|
| Minimum participants per slice | 5 | Below this a percentile describes an individual. |
| Minimum active days per participant | 7 | A one-day submission is not a habit. |
| Suppression happens at | **write** time | A thin slice never exists to be leaked by a rendering bug. |
| Slices allowed | `all`, `vendor:*`, `plan:*`, `cohort:*` (self-declared) | |
| Slices forbidden | anything derived from an org, employer, or inferred location | An enumerable roster defeats any numeric floor — see ADR-010 trade-off 2. |

The last row is the important one. A numeric floor controls *cohort size*; it
does nothing about *nameability*. A colleague who already knows a team's roster
can do elimination against any floor you set. Company-wide, vendor and
self-declared slices are not enumerable rosters, so they do not have this
problem. This is why an org slice was **dropped rather than tuned**.

## Consent

1. **Default off.** `settings.community.share` is `false` in a fresh checkout.
   Nothing uploads until a person edits a file.
2. **Nothing pools on the first sync.** The first submission establishes the
   account only; pooling begins on the next run, by which time the person has
   seen their dashboard and the consent control on it. Without this, consent is
   only changeable *after* the upload that backfilled the history — which makes
   the checkbox decorative for exactly the window that matters
   ([ADR-010](../adr/ADR-010-Cohort-Analytics-Store.md) trade-off 5).
3. **Show the payload first.** `observe.py share` prints the complete payload and
   writes it to a file. It has no network code path at all.
4. **Opting out deletes.** Turning `share` off removes prior fact rows, not just
   future ones. Row ids are deterministic (`<auid>.<date>`) so deletion needs no
   query.
5. **Consent is versioned.** `consent_version` records which wording was agreed
   to; materially changed wording requires re-consent.

## Wire

```
POST /v1/submit        Bearer <token>     body: the payload above
GET  /v1/cohort?slice=vendor:deepseek&window=30d
GET  /v1/me
DELETE /v1/me          removes account row and every fact row
```

The server **re-buckets nothing and re-prices nothing** — it received bucket
indices and cannot recover the values. It validates ranges, rejects future
dates, and rate-limits per account.

## Threat model, stated plainly

| Adversary | Sees | Mitigated by |
|---|---|---|
| Network observer | TLS | — |
| Server operator | bucket indices, mix, finding ids, self-declared cohorts, plan | no identifier on fact rows; two-salt unlinkability |
| Anyone who can read every table | a consistent pseudonymous stranger's day-by-day pattern | **accepted, not solved** — see below |
| A colleague who knows the user | could guess an unusual pattern in a small slice | cohort floor; no org slice; no location slice |

**The accepted limit.** `auid` is stable across submissions, because that is
what makes trends possible. A determined reader with full table access sees one
consistent stranger's history, and a colleague who knows someone is the only
Kimi user on a 2 a.m. schedule could guess which stranger. Rotating the key
would remove this and would also destroy the product. This is a known position,
not an oversight, and it is stated here so nobody has to discover it.

## Retention, and why the server holds so little

**Server-side per-user rows are pruned at 35 days.**

The client is the system of record. The local NDJSON store never expires, so the
server needs a person's rows only long enough to build the nightly rollup and to
make a re-submitted window idempotent — about five weeks, not the thirteen months
the private-deployment design used
([ADR-010](../adr/ADR-010-Cohort-Analytics-Store.md) retention section, which
this supersedes for the public build).

"Is my percentile improving?" is therefore computed **on the user's own
machine**, against their own complete history and the published cohort files.
The server never needs a long tail of anybody's behaviour to answer it.

This is cheaper and it is a better privacy story; those two rarely point the
same way, and when they do the decision is easy. At 100,000 opted-in users it is
the difference between 2.2 GB and 25 GB of stored personal-ish data — and
between a free tier and a bill ([ADR-015](../adr/ADR-015-Hosting-And-Data-Residency.md)).

Cohort files are kept indefinitely. They are aggregates above the suppression
floor and are not reconstructible once the underlying rows are pruned.

## Where the read path lives

`cohort_daily` is rebuilt nightly, so a cohort response is already a static
artefact with a 24-hour lifetime. It is published **as a file on a CDN**, not
served from a query:

```
/cohort/all-30d.json
/cohort/vendor-deepseek-30d.json
/cohort/plan-glm-coding-lite-30d.json
```

Beyond making reads free and unlimited, this removes an entire class of risk:
a file of suppressed-above-floor aggregates cannot be coaxed into returning an
individual's row, because there is no query interface to coax. Suppression at
write time and a read path with no parameters are the same defence stated twice.

## Self-hosting

The server is a small stateless service over three tables. Self-hosting is a
first-class path, not an enterprise tier — for users under Indonesia's PDP Law,
Vietnam's PDPL, Thailand's PDPA or China's PIPL, a regional or in-house instance
may be the only acceptable option, and a project that treats that as an upsell
has misread its market.

## See also

- [ADR-011 — the community layer](../adr/ADR-011-Community-Layer.md)
- [ADR-010 — the cohort analytics store](../adr/ADR-010-Cohort-Analytics-Store.md)
- [Auth](Auth.md) — sign-in, tokens, account lifecycle
- [`observatory/share.py`](../../observatory/share.py) — the implementation
