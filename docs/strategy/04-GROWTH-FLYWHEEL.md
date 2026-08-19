# Growth flywheel — how this earns stars, forks and users

The stated goal is to win on stars, forks and user base. Stars are a lagging
indicator of one thing: **how often someone shows this to someone else.** So the
question is not "what features" but "what makes a person send a link."

## The five loops

### Loop 1 — Instant proof (removes the cold-start wall)

Every tool in this category has the same defect: the dashboard is the pitch, and
you cannot see it until you have weeks of your own usage.

`python3 observatory/observe.py demo digest report` fills the store with 60
deterministic days across four providers and renders the complete dashboard, on
a machine that has never run an AI coding tool. A visitor sees the product in
under a minute, and — because the fixture is seeded — everyone sees the same
numbers, so they can be discussed in an issue.

*Ships:* done. *Measured by:* time-to-first-dashboard.

### Loop 2 — The shareable artefact (the actual distribution engine)

A dashboard is not shareable; a **card** is.

- **README embed** — an SVG card with your efficiency grade, cache reuse and
  plan multiple. tokscale proved this works; every embed is a permanent backlink
  on a developer's most-visited page.
- **Monthly Receipt** — a single image: what you spent, what it returned, the
  one finding that mattered, and your rank on efficiency. Built as an image
  because images are what travel on Xiaohongshu, WeChat and Telegram, where a
  GitHub link does not.
- **Efficiency Grade (A–F)** — one letter, derived from cache reuse, tokens per
  change, and peak discipline. A letter is the most compressible unit of pride
  there is, and unlike a token total it is *improvable*, which is what makes it
  worth posting twice.

*Ships:* v0.3. *Measured by:* embeds in the wild, referral traffic.

### Loop 3 — Contribution as onboarding (breadth without a maintainer bottleneck)

Coverage breadth is the strongest correlate with stars here, and the constraint
is that a maintainer cannot test a tool they do not use.

Three deliberately trivial first PRs:

| Contribution | Cost to contributor | Cost to maintainer |
|---|---|---|
| Fix a stale price in `pricing.json` | one line + a citation | read the citation |
| Add a plan to `plans.json` | one block | check the units |
| **Add a provider via `collectors/specs/*.json`** | one JSON file + one fixture | run the fixture |

The third is the important one. A new provider costs zero engine code, and the
person who uses Lingma or CodeBuddy is the only person on earth positioned to
add it correctly. Every merged spec brings that tool's whole user community with
it.

*Ships:* done. *Measured by:* first-time contributors per month, providers
supported.

### Loop 4 — The cohort mirror (retention, not acquisition)

A local dashboard is read once and forgotten. A dashboard that says *"you are at
the 71st percentile for cache reuse among solo developers on a GLM plan, up from
the 44th last month"* is read every week.

This is the only loop that requires a server, and the only one gated on trust —
which is why the privacy mechanism is engineered rather than promised, and why
the default is off. See
[Community-Share-Protocol](../specs/Community-Share-Protocol.md).

*Ships:* v0.4. *Measured by:* weekly-active share of installs, opt-in rate.

### Loop 5 — Ecosystem surface (be where the developer already is)

- **MCP server** — the agent reads your own usage mid-session and can be asked
  "what should I change?"
- **Statusline hook** — your efficiency grade in the Claude Code status bar.
- **GitHub Action** — post a usage delta on a PR: *"this branch cost 240k tokens
  across 6 sessions."*
- **`npx` / `uvx` one-liner** — parity with `npx ccusage@latest`.

Each is small; each puts the name somewhere it is seen daily.

*Ships:* v0.3–0.5.

## Sequencing, and the one thing not to do

The temptation is to launch the leaderboard first, because leaderboards are
loud. That would be a mistake: a leaderboard with fifty participants is
embarrassing, a cohort floor of five cannot be met, and the privacy story has
not been road-tested. Worse, it makes the first impression *"another vanity
board"* — the exact category we are trying not to be filed under.

Correct order: **be undeniably useful alone → be shareable → be comparable.**
The community layer is the reward for having a user base, not the way to get
one.

## Launch plan

| Phase | Gate to pass | Channel |
|---|---|---|
| 0. Private dogfood | The author changes their own behaviour because of a finding | — |
| 1. Soft launch | 10 providers, 15 detectors, demo mode, EN + ZH README | r/ClaudeAI, HN Show, V2EX, Juejin, 掘金 |
| 2. Embeds | Receipt card + README badge shipping | Twitter/X, Xiaohongshu, LinkedIn |
| 3. Community | 500+ installs, opt-in flow reviewed by someone who is not the author | Discord, WeChat groups, Telegram |
| 4. Ecosystem | MCP + Action + statusline | Awesome-lists, plugin registries |

Every phase gate is a capability, not a date. Shipping phase 3 before phase 2
gets a ghost town; shipping phase 1 before the detectors are honest gets a
reputation that cannot be undone.

## Anti-goals

- **No growth hacking against the privacy model.** No default-on telemetry, no
  "share to unlock", no dark-pattern consent. The trust story *is* the product
  in this market, and one violation ends it permanently.
- **No vanity metric in the product.** Total spend is displayed; it is never
  ranked, never gamified, never in an achievement.
- **No feature that only serves managers.** The moment this can rank employees,
  developers stop installing it.

## What "winning" looks like, honestly

Stars follow usefulness with a lag, and the ceiling in this category is set by
breadth and by a screenshot. A realistic 12-month shape: hundreds of stars from
soft launch and a strong README; low thousands if the peak/off-peak and
plan-value findings land with Chinese-vendor users and get written up in
Chinese; the leaderboard only matters after that. The failure mode to guard
against is not "too few stars" — it is **stars without retention**, which is
what a leaderboard-first launch buys.

## See also

- [02-POSITIONING-AND-WEDGE.md](02-POSITIONING-AND-WEDGE.md)
- [05-RISKS.md](05-RISKS.md)
- [../ROADMAP.md](../ROADMAP.md)
