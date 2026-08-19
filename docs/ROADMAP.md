# Roadmap

Phases are gated on evidence, not dates. A phase does not start because the
previous one finished; it starts because its trigger fired.

Phases 0–3 happened in a private workspace before extraction; they are kept
because the gates they passed are why the rest is worth building.

## Phase 0 — Prove the data exists ✅

Establish that usage can be measured at zero marginal cost.

- [x] Confirm coding agents write complete per-turn token accounting locally
- [x] Confirm the cache TTL split, effort, tier, speed and tool names are present
- [x] Confirm subagent turns are recoverable and attributable to a parent session

**Outcome:** 18,095 turns across 56 days recovered retroactively, zero tokens spent.

## Phase 1 — Collect, aggregate, see ✅

- [x] Read-only incremental collector (3.5 s full, 0.15 s no-op)
- [x] NDJSON store, month-partitioned, append-only
- [x] Digest tier with cost model and confidence
- [x] Rule-based detectors with evidence, confidence and a materiality gate
- [x] Self-contained HTML report — light/dark, mobile/desktop, zero external requests

## Phase 2 — Make it a habit ✅

**Exit condition, and it was met:** at least one finding changed the author's
own behaviour, visibly, in a later digest. **This was the gate for everything
below**, and it is the reason the detectors are trusted enough to generalise.

- [x] Scheduled daily `sync` so collection never depends on remembering
- [x] Weekly read ritual

## Phase 3 — Multi-provider ✅

- [x] Second, third and fourth providers — the real test of
      [ADR-003](adr/ADR-003-Provider-Abstraction.md)
- [x] Per-vendor cache multipliers

## Phase 4 — Open source ✅ *this release*

**Trigger:** the tool had been used unprompted for a full quarter.

- [x] Extract into a standalone repository, scrubbed of workspace specifics
- [x] Zero-config first run — `observe.py demo` renders the whole product with
      no usage history
- [x] Thresholds, prices, plans and topology as user config rather than constants
- [x] Peak/off-peak pricing ([ADR-012](adr/ADR-012-Rate-Card-As-Config.md))
- [x] Plan value and quota model
- [x] Local currency, thirteen of them
- [x] Declarative collectors ([ADR-014](adr/ADR-014-Declarative-Collectors.md))
- [x] Test suite: engine, specs, fixtures, headless dashboard
- [x] EN + 简体中文 README
- [x] Community share payload built and auditable locally, never transmitted

## Phase 5 — Shareable *(next)*

**Trigger:** now. A dashboard nobody can show anyone does not spread.

- [ ] **Efficiency Grade (A–F)** — one letter from cache reuse, tokens per
      change and peak discipline. Improvable, unlike a spend total.
- [ ] **Monthly Receipt card** — a single image: what you spent, what it
      returned, the one finding that mattered. An image because that is what
      travels on Xiaohongshu, WeChat and Telegram, where a GitHub link does not.
- [ ] **README embed** — SVG badge with grade and plan multiple.
- [ ] `uvx` / `npx`-style one-liner install
- [ ] More providers, contributed — Qwen Code, Lingma, CodeBuddy, Comate, Trae
- [ ] Quota headroom with self-calibrated p90 where a vendor publishes no limit
- [ ] Weekly/monthly rollups; trend direction per finding

## Phase 6 — Community

**Trigger:** Phase 5 shipped **and** enough installs that a cohort floor of five
is comfortably met **and** the consent flow has been reviewed by someone who is
not the author. All three, not any one.

- [ ] Accounts — Google and GitHub OIDC, device-code flow for slow connections
- [ ] Submission endpoint; cohort read endpoint
- [ ] Efficiency percentiles by vendor, plan and self-declared cohort
- [ ] Self-hosting guide as a first-class path, not an enterprise tier
- [ ] `PRIVACY.md` with a plain-language data map

Deliberately last. A leaderboard with fifty participants is embarrassing, and
launching it first would file this project under "another vanity board" —
the exact category it exists to escape.

## Phase 7 — Ambient

**Trigger:** retention data shows people who install do not return in week two
*despite* useful findings. That would be evidence the missing loop is presence,
not insight.

- [ ] Native shell (menu bar / tray) wrapping the same HTML — a wrapper, not a
      rewrite ([ADR-013](adr/ADR-013-Form-Factor.md))
- [ ] MCP server so an agent can read your usage mid-session
- [ ] Statusline hook; GitHub Action posting a per-PR usage delta

## Explicitly not roadmapped

An org or manager dashboard · ranking named individuals · sitting in the request
path · real-time streaming · productivity scoring · ranking by total spend. See
[00-VISION.md](00-VISION.md) → What this is not.
