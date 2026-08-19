<h1 align="center">AI Observatory</h1>

<p align="center">
  <strong>Your AI coding usage, measured locally — and told what to change.</strong><br>
  <sub>Built for the way developers in Southeast Asia and China actually buy AI:
  flat monthly plans, tokens priced by the hour, and a currency that isn't the dollar.</sub>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#what-makes-this-different">What's different</a> ·
  <a href="#privacy">Privacy</a> ·
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="README.zh-Hans.md">简体中文</a>
</p>

---

Every other token tracker is an **odometer** — it tells you how much you spent.
This one is a **coach**: fifteen deterministic detectors turn your own
transcripts into ranked findings, each with the evidence behind it, an action,
a confidence level, and — where it can be defended — what a fix is worth per
month.

Collection costs **zero tokens**. It reads the JSONL transcripts your coding
agent already wrote to disk. No API keys, no proxy, no account, no network.

## Quick start

```bash
git clone https://github.com/jxxyx-bloop/ai-observatory
cd ai-observatory/observatory

# See the whole product on 60 days of synthetic data, right now
python3 observe.py demo digest report
```

Open `dist/observatory.html`. Python 3 standard library only — **no dependencies,
no install, no build step, no account, no network.**

> `demo` exists because every tool in this category has the same problem: the
> dashboard is the pitch, and you can't see it until you have weeks of your own
> data. This fills that gap deterministically, so everyone sees the same numbers
> and can argue about them in an issue.

### Your first five minutes

**1. Run it on your own usage.**

```bash
rm -rf ../data ../dist        # clear the demo data first — it must not mix with yours
python3 observe.py all        # sync -> digest -> report
```

`observe.py demo` refuses to run once real events exist, but the reverse is on
you: clear `data/` before your first real sync.

**2. Tell it where your repos live.** Open
[`topology.json`](observatory/topology.json) and put your actual code
directories in `code_roots`. This is the one edit worth making on day one —
without it, work shows as `unattributed` rather than by project.

```bash
python3 observe.py sync --full digest report   # --full is needed after a topology change
```

**3. Set three things in [`settings.json`](observatory/settings.json).**

| Field | Set it to |
|---|---|
| `timezone_offset_hours` | `8` for SG/CN/MY/PH/HK, `7` for ID/TH/VN, `9` for JP/KR, `5.5` for IN |
| `currency` | `IDR`, `VND`, `THB`, `PHP`, `MYR`, `SGD`, `CNY` … or leave `USD` |
| `plan` | your subscription id from [`plans.json`](observatory/plans.json), or `none` if you pay per token |

Setting `plan` is what turns the dollar figure from a number you don't
recognise into *"your $18 plan returned 23× what you paid."*

**4. Read the top finding and do something about it.**

```bash
python3 observe.py insights
```

The list is sorted most-material first. If the top item is `info`, your usage
is healthy and the tool will say so rather than inventing a problem.

**5. Make it a habit.** A daily cron costs nothing to run (zero tokens, ~0.2 s):

```cron
0 9 * * *  cd /path/to/ai-observatory/observatory && python3 observe.py all
```

### What it can read

Collection is read-only and costs zero tokens — it parses transcripts these
tools already wrote to disk.

| Tool | Reads from |
|---|---|
| Claude Code | `~/.claude/projects/**/*.jsonl` |
| Codex | `~/.codex/sessions/**/*.jsonl` |
| Kimi Code | `~/.kimi-code/sessions/**/wire.jsonl` |
| Antigravity | `~/.gemini/antigravity/brain/**` |
| Anything else | a [declarative spec](observatory/collectors/specs/README.md) — one JSON file |

**Your tool missing?** If it writes JSONL with token counts on a record, adding
it needs no Python — see [CONTRIBUTING.md](CONTRIBUTING.md). You have the
transcripts to test against, which the maintainers do not.

### If something looks wrong

| Symptom | Cause |
|---|---|
| `no events found` | None of the paths above exist. Check with `ls ~/.claude/projects`. |
| Everything is `unattributed` | `code_roots` in `topology.json` doesn't match where your repos are. |
| Repo names look wrong after editing `topology.json` | Attribution is baked in at sync time — re-run with `sync --full`. |
| Costs look implausible | Check `_verified_on` in [`pricing.json`](observatory/pricing.json). Rates go stale; correcting one is a one-line PR. |
| A finding seems wrong | That's a bug worth an issue — credibility is the whole product. |

## Commands

| Command | What it does |
|---|---|
| `observe.py sync` | Collect new events into `data/` (incremental, ~0.2 s) |
| `observe.py digest` | Aggregate + run the detectors → `data/digest.json` |
| `observe.py report` | Render → `dist/observatory.html` |
| `observe.py insights` | Print the findings as text — for reading inside an agent session |
| `observe.py demo` | 60 deterministic days of synthetic usage |
| `observe.py share` | Build the community payload and **print it** — never uploads |
| `observe.py all` | sync → digest → report |

Commands compose: `observe.py sync digest report` is one process.

## What makes this different

### 1. It tells you what to change, not just what you spent

```
[HIGH] You are buying tokens at peak rates you did not have to pay        ~$34/mo
  61.4% of your spend on time-priced vendors (deepseek, zhipu) landed inside a
  peak window, where the same tokens cost up to twice the off-peak rate.
  -> Peak windows are published and narrow. Anything that does not need you
     watching — test generation, migrations, doc sweeps — can be queued for an
     off-peak hour at no cost to you.
```

A materiality gate demotes anything worth under $15/month, so the top of the
list always means something. **Healthy usage is reported as healthy** — a tool
that invents problems to look useful is a tool you stop believing.

### 2. It prices tokens the way your vendor actually does

- **Peak/off-peak windows.** DeepSeek bills full rate 01:00–04:00 and
  06:00–10:00 UTC and half rate otherwise. GLM peaks 14:00–18:00 UTC+8 on
  weekdays only. For anyone in UTC+7 to +9 that second window *is* the working
  afternoon — you are paying peak rates by accident, every day. We price each
  turn at the rate in force when it ran, and quote the premium as arithmetic on
  your own tokens. **No other open-source tracker models this.**
- **Per-vendor cache economics.** The 0.1× cache-hit discount is an Anthropic
  convention, not a law — Kimi K2.6 sits near 0.074×. Cache is where the money
  is, so a wrong multiplier misprices the most important number on the page.
- **Plan value, not fake dollars.** On a $18/month GLM plan, "you spent $412" is
  a shadow price, not a bill. The number that matters is **23× return** — or,
  when it goes the other way, *"you are paying for headroom you never use."*
- **Thirteen currencies**, including IDR, VND, THB, PHP and MYR — with the
  figure framed against a median local day rate, because `$412` means something
  very different in Jakarta than in San Francisco.

### 3. Adding your tool is a JSON file, not a pull request someone has to write

Coverage is what makes a tracker relevant to a stranger, and it is normally
bottlenecked on a maintainer reverse-engineering formats they don't use. Here a
provider is a [declarative spec](observatory/collectors/specs/README.md) plus a
fixture. If you use Lingma, Qwen Code, CodeBuddy or Comate, **you are the only
person who can add it correctly** — and it costs you one file.

### 4. The community layer ranks efficiency, not consumption

Existing leaderboards rank by total tokens burned. The top of that board is,
definitionally, whoever wasted the most — which is a novelty where a $200/month
seat is routine and an insult where the median plan is $18.

We rank **cache reuse, tokens per change, cost per active hour, peak-window
discipline and plan-value multiple.** Total spend is shown and never ranked.
Efficiency is improvable, so the board is a reason to come back; and a student
in Da Nang competes with a staff engineer in Singapore on the same axis.

*Opt-in, default off, not yet shipped —
see the [protocol](docs/specs/Community-Share-Protocol.md).*

## What it measures

Cache efficiency (the biggest lever — rebuilding context costs ~12.5× reading
it) · model mix and premium-tier usage on light work · peak vs off-peak spend ·
per-session shape and peak context · produce-to-explore ratio · subagent
delegation · tool distribution · working hours · investment by repository and by
folder inside it · plan value and vendor concentration.

## Privacy

**Nothing leaves your machine unless you edit a file to say so.**

Never stored, anywhere: prompt text · completion text · thinking content · file
contents · tool argument values · shell commands · absolute paths.

What *is* stored: counts, model names, tool names, and coarse derived labels —
a repository name and a folder bucket like `app:checkout` — enforced at the parse
boundary rather than by a later redaction step
([ADR-006](docs/adr/ADR-006-Metadata-Only.md),
[ADR-008](docs/adr/ADR-008-Derived-Path-Labels.md)).

The rendered dashboard makes **zero external requests** — no CDN, no fonts, no
analytics.

If you ever opt into the community layer, the payload is under a kilobyte,
carries bucket indices rather than values, and contains no repository name, no
session id and no identifier. `observe.py share` prints the whole thing and has
no network code path. Read
[`share.py`](observatory/share.py) — it is deliberately short enough to read
before you consent.

## Configure

| File | What it's for |
|---|---|
| [`settings.json`](observatory/settings.json) | Timezone, currency, your plan, community opt-in |
| [`topology.json`](observatory/topology.json) | Where your repos live, folder taxonomy, work/personal lanes |
| [`pricing.json`](observatory/pricing.json) | The rate card — 50 models, peak/off-peak schedules |
| [`plans.json`](observatory/plans.json) | Subscription plans, quota units, currencies |

Editing `topology.json` needs `observe.py sync --full` to take effect.

## Deploy your own

The whole local product needs no server. If you want the landing page and a
hosted demo — or a private community instance under your own jurisdiction —
[`docs/setup/DEPLOY.md`](docs/setup/DEPLOY.md) is the walkthrough, and
[ADR-015](docs/adr/ADR-015-Hosting-And-Data-Residency.md) is why the stack is
what it is (about **$1/month at launch, ~$6/month at 100k users**).

```bash
python3 site/build.py     # -> site/dist/  (landing page + live demo dashboard)
```

The deploy workflow is written so it **cannot break a commit made before you
have a Cloudflare account**: the build always runs, the deploy step skips with a
notice until the secrets exist.

Self-hosting the community layer is a first-class path, not an enterprise tier —
[`server/schema.sql`](server/schema.sql) applies unchanged to a plain
`sqlite3` file. For anyone under Indonesia's PDP Law, Vietnam's PDPL, Thailand's
PDPA or China's PIPL, that may be the only acceptable option.

## Tests

```bash
observatory/tests/run.sh
```

Engine, collector specs, provider fixtures, and a headless run of the dashboard.
No test framework — stdlib Python and one optional node script.

## Documentation

| Path | Contents |
|---|---|
| [`docs/strategy/`](docs/strategy/) | **Competitive teardown · positioning · the SEA/China thesis · growth flywheel · risks** |
| [`docs/00-*.md`](docs/) | Vision, engineering principles, architecture, decision log |
| [`docs/adr/`](docs/adr/) | Fifteen decision records, including what was rejected and why |
| [`docs/specs/`](docs/specs/) | Event schema · cost estimation · peak/off-peak · plans and quotas · community protocol · auth |
| [`docs/context/`](docs/context/) | Glossary · **known limitations** |

**Read [Known-Limitations](docs/context/Known-Limitations.md) before trusting any
finding about value.** This tool measures where effort went precisely, and what
it produced only by proxy.

## Contributing

The three most useful contributions, in ascending order of effort:

1. **Fix a stale price** in `pricing.json` — one line and a citation.
2. **Add a plan** to `plans.json`.
3. **Add your coding tool** via a [collector spec](observatory/collectors/specs/README.md)
   and a fixture.

See [CONTRIBUTING.md](CONTRIBUTING.md). Especially wanted: Qwen Code, iFlow CLI,
CodeBuddy, Trae, Lingma / 通义灵码, Comate, Doubao, CodeGeeX, Cline, Roo Code,
Aider, OpenCode, Goose, Zed.

## Status

Early, and honest about which parts are which.

| | |
|---|---|
| Engine, collectors, dashboard, 15 detectors | **working, tested** |
| Peak/off-peak pricing, plan value, currency | **working, tested** |
| Landing page + hosted demo, deploy pipeline | **working** |
| Community layer (accounts, cohorts, leaderboard) | **specified, not built** — `observe.py share` builds and audits a payload locally and has no network code path at all |

See [ROADMAP.md](docs/ROADMAP.md) and
[Known-Limitations](docs/context/Known-Limitations.md).

## Licence

[MIT](LICENSE).
