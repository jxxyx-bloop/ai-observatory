# Risks — what actually kills this

Ordered by expected damage, not by likelihood. Each carries the mitigation
already in the repo, or the one that is owed.

## R1 — A privacy incident ends the project permanently

**The risk.** A payload leaks a repository name, a folder name that is a client
name, or enough correlated metrics to identify one person in a small cohort.
In this user base the data is derived from an employer's codebase; the blast
radius is the user's job, not their inbox.

**Why it is first.** Every other risk is recoverable. This one is not: a privacy
failure in a developer tool is remembered for years and no amount of good
engineering afterwards undoes it.

**Mitigations in place.**
- Allow-list payload built by naming each field; a new upstream metric cannot
  leak by default ([`share.py`](../../observatory/share.py)).
- No free text ever crosses the boundary — no repo, folder, branch, workspace or
  session id, even when repo sharing is opted into (hashed 64-way buckets only).
- Metrics bucketed **on device**; the server never receives a raw value.
- `share.audit()` asserts a forbidden-key list, tested against a built payload.
- Default off. Nothing uploads until a person changes a file.
- `observe.py share` prints the entire payload and never transmits.

**Still owed.** An external review of the consent flow by someone who is not the
author, before the community server accepts its first byte. Written into the
phase-3 gate in [04-GROWTH-FLYWHEEL](04-GROWTH-FLYWHEEL.md).

## R2 — A stale rate card makes every number wrong

**The risk.** Vendors reprice constantly — DeepSeek changed its entire billing
*shape* mid-2026. A tracker quoting last quarter's rates is confidently wrong,
and confidently wrong is worse than silent.

**Mitigations.** `_verified_on` in `pricing.json`, surfaced in the report footer.
An unknown model falls back visibly rather than silently. Cost is framed as a
lens, never an invoice, everywhere in the copy.

**Still owed.** A scheduled check that flags entries older than 90 days, and —
the real fix — enough contributors that correction is faster than decay. This is
why "fix a price" is designed as the easiest possible PR.

## R3 — An incumbent copies the regional model

**The risk.** ccusage has ~18k stars and a Rust core. If it adds peak/off-peak
and plan value, our headline differentiator is gone in a release.

**Honest assessment.** They can, and any single feature here is copyable in a
week. What is not copyable in a week is the *asset*: a community-maintained rate
card, plan table and spec library contributed by people who buy from these
vendors. That compounds and it is made of other people's attention.

**The realistic outcome** is not that we beat ccusage — it is that we are the
tool people run *alongside* it, for the question it does not answer. Positioning
against a project ten times our size on breadth would be a losing fight; on
interpretation it is not.

**Mitigation.** Do not compete on parsing. Compete on findings, economics and
trust — the three places they have chosen not to play.

## R4 — A vendor breaks the format, or objects

**The risk.** Transcript formats are undocumented internals. A vendor may change
one without notice, or decide a tool reading them is unwelcome.

**Mitigations.** Collectors are read-only and touch nothing but files the vendor
already wrote — no scraping, no API keys, no ToS surface. The append-only event
store means history survives a format change; only new events stop. Every
collector ships a fixture (ADR-009) so a break is caught by a test rather than
by a user.

**Still owed.** A `sync` warning when a source produces zero events where it
previously produced some — silent breakage is the dangerous kind.

## R5 — The leaderboard becomes the product

**The risk.** Leaderboards are loud and gamification is fun to build. Six months
in, the efficiency board is the whole identity, cohort floors get relaxed
"because engagement", and the coaching tier rots.

**Mitigation.** Written into [02-POSITIONING](02-POSITIONING-AND-WEDGE.md) as an
anti-goal: total spend is displayed, never ranked. The community layer is
sequenced *last* on purpose. Cohort floors are enforced at write time, not
render time, so relaxing them requires a schema migration someone has to justify
in a PR.

## R6 — Findings are wrong, or feel like nagging

**The risk.** A detector fires on a healthy pattern, or every run produces
another lecture. Either way the user stops believing the tool, and belief is the
product.

**Mitigations.** Every finding carries evidence, confidence and an action.
Healthy patterns are reported as healthy. The materiality gate demotes anything
under $15/month rather than deleting it — so the top of the list always means
something. Detector thresholds are in one visible `T` dict, tunable per user.

**Still owed.** A "this finding is wrong" path that is cheaper than opening an
issue, and a way to mute one permanently.

## R7 — Regulatory exposure for hosted comparison

**The risk.** Indonesia's PDP Law, Vietnam's PDPL (in force since 1 Jan 2026),
Thailand's PDPA (no adequate jurisdictions designated), Malaysia's equivalence
test, China's PIPL and its CAC standard-contract requirement. A hosted server
holding per-user rows across those borders is a compliance question for the
user's employer, not just for us.

**Mitigations.** The payload is arguably not personal data at all — no
identifier, no raw values, sub-kilobyte, bucketed on device. Self-hosting is a
first-class path, not an enterprise tier. Regional deployment is possible
because the server is stateless over a small table.

**Still owed.** A plain-language data map in `PRIVACY.md`, and legal review
before any hosted instance serves users in these jurisdictions. Nothing in this
repo is legal advice.

## R8 — Single-maintainer bus factor

**The risk.** One person, a workspace extraction, a day job. The category is
littered with abandoned trackers.

**Mitigations.** Zero dependencies and stdlib-only Python, so it keeps working
untouched. Configuration over code for the parts that change most (prices,
plans, providers), so the repo stays useful even during a quiet period.
Documented architecture, ADRs, and a full test suite so a successor can pick it
up.

**Still owed.** A second maintainer before any hosted service exists. Do not
operate a server that only one person can fix.

## R9 — Nobody cares

**The risk.** Developers glance at usage once and never again. Retention in this
category is genuinely unproven — every incumbent is an odometer, and odometers
get read once.

**Honest assessment.** This is the likeliest failure, and the least discussed.
The coaching tier and the cohort mirror are both bets *against* it: a finding
that changes behaviour and a percentile that moves are the only two reasons
anyone has ever returned to a dashboard like this.

**Mitigation.** Instrument the one thing that matters — do users come back in
week two — and if they do not, the answer is not more charts. It is fewer,
better findings.

## See also

- [01-COMPETITIVE-TEARDOWN.md](01-COMPETITIVE-TEARDOWN.md)
- [03-SEA-CHINA-PRODUCT-THESIS.md](03-SEA-CHINA-PRODUCT-THESIS.md)
- [../specs/Community-Share-Protocol.md](../specs/Community-Share-Protocol.md)
