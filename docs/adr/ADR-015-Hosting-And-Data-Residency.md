# ADR-015 — Hosting: static site on Cloudflare, cohort reads as CDN files, one small write DB

**Status:** accepted · **Date:** 2026-08-19 · **Relates to:** [ADR-011](ADR-011-Community-Layer.md), [ADR-013](ADR-013-Form-Factor.md)

> **Prices below were gathered on 2026-08-19 from secondary sources** (vendor
> docs were not directly reachable from the machine this was researched on).
> They are the right order of magnitude and the right shape, but **verify each
> against the vendor's own pricing page before committing money.** The
> reasoning does not depend on any figure being exact.

## Context

The community layer needs somewhere to live. The obvious framing — "Cloudflare
or Vercel, Supabase or something JSON-shaped" — turns out to be the wrong
starting question, because this workload is unusual in three ways that
disqualify most of the received wisdom about hosting a web app.

### 1. Almost nothing needs a server

Per [ADR-013](ADR-013-Form-Factor.md), collection, the digest, the dashboard,
every detector and the demo all run locally with no network. The only thing
that needs hosting is the opt-in community layer: a submission endpoint, a
cohort read endpoint, an account, and a nightly rollup.

### 2. The payload is tiny and the write rate is trivial

Measured, not estimated — `share.build()` emits **633 bytes**. Steady-state
writes are bounded by the fingerprint skip in
[Community-Share-Protocol](../specs/Community-Share-Protocol.md): only days
whose metrics actually changed get rewritten, so about 1.5 row-writes per user
per day.

| Opted-in users | Row writes / month | Server storage @ 35-day retention | @ 400-day |
|---:|---:|---:|---:|
| 1,000 | 45,000 | 22 MB | 253 MB |
| 10,000 | 450,000 | 222 MB | 2.5 GB |
| 100,000 | 4,500,000 | 2.2 GB | 25.3 GB |

At 100,000 opted-in users this is **0.12 writes per second**. That is not a
scaling problem; it is a rounding error. Any database in the comparison below
handles it on a free tier.

### 3. The audience includes people the big platforms cannot serve

Vercel is blocked in mainland China. Cloudflare's IPs are, at best,
intermittently interfered with by the GFW. Hosting *inside* mainland China
requires an ICP filing (备案), which requires a Chinese business entity — not
something a solo open-source maintainer can obtain.

Meanwhile Indonesia's PDP Law, Vietnam's PDPL, Thailand's PDPA, Malaysia's
amended PDPA and China's PIPL all constrain where data derived from a
developer's employer's codebase may be transferred.

## Decision

### 1. Website and docs → **Cloudflare Pages**

| | Cloudflare Pages | Vercel Hobby | Vercel Pro |
|---|---|---|---|
| Bandwidth | **unlimited** | 100 GB/mo | 1 TB, then $0.15/GB |
| Builds | 500/mo | 100 build-minutes/mo | more |
| Commercial use on free tier | **allowed** | **prohibited** | n/a |
| Cost | $0 | $0 | $20/seat/mo |

Two things decide it, and neither is DX.

**The bandwidth cap is a launch-day risk.** The entire growth plan
([04-GROWTH-FLYWHEEL](../strategy/04-GROWTH-FLYWHEEL.md)) is built on spiky
referral traffic — Show HN, V2EX, Juejin, Xiaohongshu. A 100 GB cap is exactly
the wrong failure mode on the one day traffic matters, and the remedy is a
forced upgrade mid-spike.

**The Hobby plan forbids commercial use.** An unmonetised open-source project is
probably fine today, but "probably fine" plus a GitHub Sponsors button is a
policy question nobody wants to litigate. Cloudflare's free tier permits
commercial use outright, so the question never arises.

Vercel's genuine advantages — Next.js DX, preview deployments — do not pay for
themselves on a static docs site and a marketing page.

### 2. Cohort reads → **static JSON on the CDN, not a database query**

This is the decision that makes everything else cheap, and it falls out of the
design rather than being bolted on.

`cohort_daily` is rebuilt by a nightly job. A cohort response is therefore
**already a static artefact with a 24-hour lifetime**. So the rollup job writes
files — `/cohort/all-30d.json`, `/cohort/vendor-deepseek-30d.json` — and the
read path is a CDN GET.

Consequences:

- **Read cost is zero and read scale is unlimited.** The hot path never touches
  a database, so a front-page spike costs nothing.
- **The read path cannot leak.** A file containing only suppressed-above-floor
  aggregates cannot be coaxed into returning an individual's row, because there
  is no query interface to coax.
- **Self-hosters can serve it from anywhere** — a bucket, a web server, a
  git repo.

### 3. Writes → **one small SQL database, and shorten server-side retention**

The retention row in the table above is the whole hosting question in disguise:
400-day retention at 100k users is 25 GB and forces a real database bill;
35-day retention is 2.2 GB and fits a free tier.

**The client already holds full history.** The local NDJSON store is the
system of record and never expires. The server needs per-user rows only long
enough to (a) build the nightly rollup and (b) make re-submission idempotent.
That is about five weeks, not thirteen months.

So: **server-side retention drops to 35 days.** "Is my percentile improving?"
is computed on the user's own machine, against their own complete history and
the published cohort files. The server holds strictly less, which is cheaper
*and* a better privacy story — the two rarely point the same way.

**Database choice: start on Cloudflare D1.**

| | D1 | Supabase | Neon | Turso | "JSON services" |
|---|---|---|---|---|---|
| Free storage | 5 GB (10 GB hard cap/db) | 500 MB | 0.5 GB | ~5 GB | varies |
| Free writes | ~3M rows/mo | — | — | generous | varies |
| Paid entry | **$5/mo** (Workers Paid) | $25/mo Pro | usage | usage | — |
| Pauses when idle | no | **yes, after 7 days** | no | no | varies |
| Dialect | SQLite | Postgres | Postgres | SQLite | proprietary |
| Runs offline / self-host | yes (plain SQLite) | yes (heavy) | yes (Postgres) | yes | **no** |

D1 wins here for reasons specific to this project:

- **$5/mo covers 100k users**, against $25/mo for Supabase Pro before anything
  else is added.
- **It is SQLite.** A self-hoster runs the identical schema and near-identical
  SQL against a plain `.db` file with no service at all. The lock-in is in the
  binding API, not the data — and that is a hundred lines, not a rewrite.
- It sits on the same platform as Pages, so there is one vendor, one dashboard,
  one bill, and one thing to learn. For a
  [single-maintainer project](../strategy/05-RISKS.md#r8--single-maintainer-bus-factor),
  operational surface area is a real cost.

**Supabase's idle-pause is a specific trap for this application.** A community
endpoint in its first months is exactly a low-traffic service; a database that
suspends after seven quiet days will suspend, and the first person to submit
after that gets an error. Supabase Pro removes the pause, but that is $25/mo
from day one for a service handling 0.01 writes per second.

**"JSON services" (JSONBin, Firebase RTDB, and the free-tier tier of the week)
are rejected**, for four reasons that apply to all of them: no atomic upsert on
a deterministic row id, no retention/pruning story, no regional control, and a
poor survival record — this category shuts down or reprices with little notice,
and it is where a project's data goes to die.

### 4. Domain → **Cloudflare Registrar**

Registered at wholesale with no markup and, critically, **no renewal hike** —
about $9.77–10.44/yr for a `.com` versus roughly $11 at Porkbun and about $15 at
renewal from registrars that discount the first year. Over five years the
renewal column is the only one that matters. It also keeps DNS, CDN, hosting and
registration under one account.

Porkbun is a fine alternative and supports more TLDs. Avoid any registrar whose
first-year price is much lower than its renewal.

### 5. Data residency → **self-hosting is the answer, not a region picker**

The hosted instance will serve from wherever the CDN puts it, and that is
acceptable *only because of what is being stored*: 633 bytes of bucket indices
per person per day, with no identifier, no repository name and no raw value.
That is a weak claim to being personal data at all.

For anyone who cannot accept even that — an employer under Indonesia's PDP Law,
a team under PIPL — the answer is a self-hosted instance, which this
architecture makes genuinely easy: static files plus a SQLite database plus a
few hundred lines of Worker-equivalent code. **Documented as a first-class path,
never sold as an enterprise tier.**

Mainland China gets the entire local product with no server at all, and loses
only the leaderboard. That is a real limitation and it is
[stated in Auth](../specs/Auth.md#the-china-problem-stated-rather-than-ignored)
rather than glossed.

## What this costs

| Stage | Website | API | Database | Domain | **Total** |
|---|---|---|---|---|---|
| Launch (0–1k sharers) | Pages $0 | Workers free | D1 free | ~$10/yr | **~$1/mo** |
| Traction (10k) | Pages $0 | Workers $5 | D1 included | ~$10/yr | **~$6/mo** |
| Scale (100k) | Pages $0 | Workers $5 | D1 included | ~$10/yr | **~$6/mo** |

The equivalent on Vercel Pro + Supabase Pro is roughly **$45/mo** for the same
0.12 writes per second, most of it buying capacity this workload will never use.

## Options considered and rejected

| Option | Why not |
|---|---|
| **Vercel Pro + Supabase Pro** | ~$45/mo for a workload that fits in free tiers. Buys Next.js DX and Postgres familiarity this project needs neither of. Reconsider only if the site becomes a real application rather than docs. |
| **Supabase free tier** | The 7-day idle pause makes it unfit for a low-traffic endpoint, which is precisely what this is at launch. |
| **Neon free tier** | 0.5 GB storage is crossed at roughly 3–5k users even at 35-day retention. Excellent if Postgres is required for another reason; here it is not. |
| **Turso** | Genuinely competitive on free-tier generosity and also SQLite. Rejected only because D1 comes with the platform already chosen for Pages, and one vendor beats two at this size. **Revisit if Cloudflare's terms move.** |
| **A $5 VPS running SQLite** | Cheapest on paper and the most portable. Rejected on maintenance: OS patching, TLS renewal, backups, monitoring and uptime become one person's problem, which is the failure mode [R8](../strategy/05-RISKS.md) names. |
| **Postgres now, for optionality** | Optionality has a price and this is not the moment to pay it. The schema is three tables of integers; migrating SQLite→Postgres later is an afternoon, and the read path is static files that do not care at all. |
| **Serving cohort reads from the database** | Turns a free, infinitely-cacheable CDN GET into a metered query, and reintroduces a query interface that suppression has to defend. |

## Trade-offs accepted

1. **Cloudflare concentration.** Registrar, DNS, CDN, hosting, compute and
   database in one account is a single point of both failure and
   business-model risk. Mitigated by the parts being individually portable —
   static files move anywhere, SQLite moves anywhere, and DNS can be moved in an
   hour. Deliberately *not* mitigated by spreading across vendors, which would
   cost more than the risk.
2. **D1's 10 GB per-database cap cannot be raised.** At 35-day retention that is
   roughly 450k opted-in users. If that ever binds, the project has much better
   problems, and sharding by cohort slice is straightforward.
3. **Cohort data is up to 24 hours stale.** Inherent to a nightly rollup, and
   correct for a comparison that is about habits rather than live state.
4. **Mainland China cannot reach the hosted community layer.** Bounded: the
   local product is unaffected, and self-hosting works.
5. **Every price here needs verifying against a vendor page.** See the note at
   the top. Free tiers in this market are marketing, and marketing changes.

## Revisit when

- Cloudflare changes free-tier terms or D1 limits materially
- The site stops being static and becomes an application
- A contributor needs Postgres for a feature that genuinely requires it
- Anyone asks for a regional deployment — at which point self-hosting docs, not
  a second hosted region, are the deliverable

## See also

- [ADR-011 — the community layer](ADR-011-Community-Layer.md)
- [ADR-013 — form factor](ADR-013-Form-Factor.md)
- [Community-Share-Protocol](../specs/Community-Share-Protocol.md)
- [server/README.md](../../server/README.md)
