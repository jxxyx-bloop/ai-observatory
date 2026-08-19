# Community server — reference sketch

**Status: design sketch. Not a running service. Do not deploy this and point
real users at it.**

The local product needs no server and never will. This directory exists so the
community layer's design is reviewable *before* anything is built, rather than
after — which is the order that mistake usually happens in.

## What it must be

- **Stateless over three small tables.** No joins, no aggregates in the request
  path. Everything is a keyed read or an upsert.
- **Incapable of receiving a raw value.** The client sends bucket indices. The
  server cannot invert them, so a breach leaks what the aggregates already
  published.
- **Trivially self-hostable.** For users under Indonesia's PDP Law, Vietnam's
  PDPL, Thailand's PDPA or China's PIPL, a regional or in-house instance may be
  the only acceptable option. A project that treats that as an enterprise upsell
  has misread its market.

## Tables

| Table | Row id | Holds |
|---|---|---|
| `accounts` | `uid = HMAC("uid", oidc_sub)[:24]` | handle, sealed email, consent record, counters |
| `facts` | `auid.YYYY-MM-DD` where `auid = HMAC("analytics", oidc_sub)[:24]` | one submission: bucket indices, mix, finding ids, declared cohorts |
| `cohorts` | `slice.YYYY-MM-DD` | participant count, summed bucket histograms, categorical shares |

`uid` and `auid` are not derivable from one another without the server secret,
and **must never appear on the same row**. That unlinkability is what lets fact
rows stay in plaintext.

**Nothing summable may live on `accounts`.** A person's fact rows sum to exactly
such a total, which recovers the link the two-salt design exists to prevent —
needing only one figure said out loud to attach a name to a full history. This
is the single most important rule in this directory, and it was learned the hard
way; see [ADR-010](../docs/adr/ADR-010-Cohort-Analytics-Store.md).

## Endpoints

```
POST   /v1/submit     Bearer token. Body: the share payload. Validates ranges,
                      rejects future dates, rate-limits per account. Writes one
                      `facts` row per day, upserted by deterministic id.
GET    /v1/cohort     ?slice=vendor:deepseek&window=30d
                      Reads `cohorts` only. Never touches `facts`.
GET    /v1/me         The caller's own account row and submission count.
DELETE /v1/me         Removes the account row and every fact row. No soft
                      delete, no grace period, no "we keep the aggregates".
```

A nightly job rebuilds `cohorts` from `facts` for the previous two days — two,
not one, so a late submission still lands. Suppression happens at **write**
time: a slice below the floor is never written, so a thin slice does not exist
to be leaked by a rendering bug.

## Why histograms, not percentiles

Percentiles do not compose; histograms do. A 30-day cohort p50 cannot be
recovered by averaging thirty daily p50s, but it is exact from thirty summed
bucket-count arrays. That is what makes any window — 7, 30, 90 days — answerable
in O(days × slices) reads instead of O(users × days).

Since the client already sends bucket indices, the server's histogram is
elementwise addition of one-hot vectors. There is no arithmetic to get wrong.

## Cohort floors

Minimum 5 participants per slice, minimum 7 active days each. Slices allowed:
`all`, `vendor:*`, `plan:*`, and self-declared `cohort:*`. **No org slice and no
IP-derived location slice** — an enumerable roster defeats any numeric floor, and
a raised floor only changes how many names an attacker has to rule out. Dropped
rather than tuned; see
[ADR-011](../docs/adr/ADR-011-Community-Layer.md).

## Before this accepts a byte

1. The consent flow is reviewed by someone who is not the author.
2. `PRIVACY.md` exists with a plain-language data map.
3. Deletion is tested end to end, including fact rows.
4. A second maintainer exists. Do not operate a service only one person can fix.

## See also

- [Community-Share-Protocol](../docs/specs/Community-Share-Protocol.md)
- [Auth](../docs/specs/Auth.md)
- [ADR-011](../docs/adr/ADR-011-Community-Layer.md)
