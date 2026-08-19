# ADR-011 — Add an opt-in community comparison layer, ranked on efficiency

**Status:** accepted · **Date:** 2026-08-19 · **Extends:** [ADR-006](ADR-006-Metadata-Only.md), [ADR-010](ADR-010-Cohort-Analytics-Store.md)

## Context

A purely local tool is read once and forgotten. Every incumbent in this category
is an odometer, and odometers get read once — which is the likeliest reason this
whole product line fails (see [R9](../strategy/05-RISKS.md)).

Comparison is the strongest known retention mechanism here, and it answers a
question no vendor dashboard can: *"is 62% cache reuse good?"* has no answer
from your own data alone, and no vendor sees across vendors.

Two projects already do this. tokscale runs a global leaderboard with GitHub
OAuth, public profiles and README embeds. viberank describes itself as "the
public tokenmaxxing leaderboard." Both rank by **total tokens and total spend**.

## Decision

Ship a community layer, **opt-in, default off**, with two decisions that
distinguish it from what exists.

### 1. Rank efficiency, never consumption

The ranked metrics are cache reuse %, tokens per merged change, cost per active
hour, peak-window discipline, and plan-value multiple. Total spend is displayed
on the personal dashboard and is **never ranked, never gamified, never part of
an achievement**.

Three reasons, in order of weight:

- **A consumption board rewards waste.** Its top entry is, definitionally, the
  person who spent the most. That is a novelty in a market where a $200/month
  seat is routine and an insult in one where the median plan is $18.
- **A consumption board has no second act.** Your rank is a function of your
  budget, so there is no reason to return. An efficiency rank moves when you
  improve, which is the only mechanic that brings anyone back.
- **A consumption board cannot be fair across budgets.** A student in Da Nang
  and a staff engineer in Singapore can compete on efficiency; they cannot
  compete on spend.

There is a defensibility argument too. If tokscale adds an efficiency tab, it
sits inside a product whose identity is "trillions of tokens tracked" — the
metric and the brand fight each other. Ours do not.

### 2. Privacy as a mechanism, not a promise

Inherits the two-salt unlinkability, k-anonymity floors, write-time suppression
and histogram composition from [ADR-010](ADR-010-Cohort-Analytics-Store.md),
with one addition: **metrics are bucketed on the device**, so the server never
receives a raw value at all.

Full field list in
[Community-Share-Protocol](../specs/Community-Share-Protocol.md).

## Options considered

### What gets shared

| Option | Verdict |
|---|---|
| Raw daily rows, bucketed server-side (ADR-010's shape) | Rejected here. It was right in a single-employer deployment where the operator and the user share an employer. In a public project the operator is a stranger, and "we bucket it on arrival" is a promise rather than a mechanism. |
| **Bucket indices computed on device** ← chosen | The server cannot leak what it never received. Costs exact cohort medians (accurate to one bucket, ≈12%), which is the right trade for a comparison and the wrong one for an invoice — the framing already applied to cost everywhere else. |
| Differential privacy noise on top | Deferred. Real value at scale, but at a cohort floor of 5 the noise needed to matter would swamp the signal. Revisit above ~10k participants. |

### Cohort slices

| Slice | Status | Reason |
|---|---|---|
| `all` | ✅ | Not an enumerable roster. |
| `vendor:*`, `plan:*` | ✅ | Derived from data already shared; the comparison people actually want ("others on my plan"). |
| `cohort:*` self-declared | ✅ | The user types it. An inference nobody consented to is not acceptable; a label they wrote is. |
| `org:*` | ❌ **dropped, not tuned** | An org is a roster a colleague can recite. A numeric floor shrinks the group but does not stop elimination against it. ADR-010 established this; it is more true in public. |
| `country:*` derived from IP | ❌ | Location inferred rather than declared. Self-declared cohorts already cover the use case. |

### Auth provider

Google **and** GitHub. GitHub alone is developer-native but excludes part of the
Southeast Asian audience; Google alone feels wrong to the rest. Neither is
reachable from mainland China without help, which is why the local product needs
no account at all and self-hosting is documented as first-class rather than sold
as an enterprise tier. See [Auth](../specs/Auth.md).

## Trade-offs accepted

1. **Cohort statistics are approximate.** Accurate to one log-spaced bucket
   (≈12%). Fine for "you are around the 70th percentile"; not an invoice.
2. **`auid` is stable, so submissions are pseudonymous rather than anonymous.**
   That stability is what makes trends possible; rotating it would destroy the
   product. Stated in the threat model rather than hidden.
3. **Self-declared cohorts are unverified.** Someone can claim any label. This is
   acceptable because the alternative — deriving cohorts from the data — is
   worse, and because the incentive to lie about being a solo developer in
   Indonesia is close to zero.
4. **Default off costs adoption.** Fewer participants, slower to reach cohort
   floors. Accepted: a default-on telemetry decision in a tool that reads
   developer transcripts would be the one mistake that cannot be undone
   ([R1](../strategy/05-RISKS.md)).
5. **The efficiency board is less immediately viral than a spend board.** "I
   burned $6,000 this month" is a better tweet than "I hit 84% cache reuse."
   Accepted deliberately: the viral version attracts an audience that leaves,
   and it files us under a category we are trying to escape.

## Sequencing

The community layer ships **after** the local product is undeniably useful and
after the shareable artefacts exist. A leaderboard cannot meet a floor of five
without a user base, and launching it first makes the first impression "another
vanity board." See [04-GROWTH-FLYWHEEL](../strategy/04-GROWTH-FLYWHEEL.md).

**Gate:** no hosted instance accepts a byte until the consent flow has been
reviewed by someone who is not the author.

## See also

- [Community-Share-Protocol](../specs/Community-Share-Protocol.md)
- [ADR-010](ADR-010-Cohort-Analytics-Store.md)
- [ADR-012](ADR-012-Rate-Card-As-Config.md)
