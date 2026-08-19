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

# Or run it on your own usage
python3 observe.py all
```

Then open `dist/observatory.html`. Python 3 standard library only — **no
dependencies, no install, no build step.**

> `demo` exists because every tool in this category has the same problem: the
> dashboard is the pitch, and you can't see it until you have weeks of your own
> data. This fills that gap deterministically, so everyone sees the same numbers
> and can argue about them in an issue.

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
| [`docs/adr/`](docs/adr/) | Fourteen decision records, including what was rejected and why |
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

Early. The engine, dashboard, detectors and privacy boundary work and are
tested. The community layer is specified and not yet built. See
[ROADMAP.md](docs/ROADMAP.md).

## Licence

[MIT](LICENSE).
