# Competitive teardown — what the incumbents built, and what they left on the table

*Researched 2026-08-19. Star counts are point-in-time and will be wrong by the
time you read this; the structural observations are the durable part.*

## The field

| Project | Stars | Language | Shape | Community layer |
|---|---:|---|---|---|
| [ccusage](https://github.com/ryoppippi/ccusage) | ~18k | TS / Rust | CLI report over local logs, 16 agents | none |
| [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) | ~8.6k | Python | Live terminal monitor, burn-rate + P90 limit prediction | none |
| [tokscale](https://github.com/junhoyeo/tokscale) | ~5k | Rust | CLI + hosted global leaderboard | public profile, GitHub OAuth, README embeds |
| [TokenTracker](https://github.com/xiufengsun/TokenTracker) | ~1.4k | JS | Native desktop apps, 32 tools, widgets, achievements, mascot | anonymous heartbeat only |
| [token-monitor](https://github.com/Javis603/token-monitor) | ~1.4k | JS | Desktop widget, multi-device sync hub, iOS widget | none (private sync) |
| [sniffly](https://github.com/chiphuyen/sniffly) | ~1.3k | Python | Local dashboard, error taxonomy, shareable links | opt-in share links + gallery |
| [aiusage](https://github.com/juliantanx/aiusage) | ~115 | TS | Local dashboard, 25+ tools, quota pressure | opt-in signed aggregate leaderboard |
| [viberank](https://www.viberank.app/) | — | hosted | Submit-your-usage leaderboard | public, by cost and tokens |
| [WakaTime](https://wakatime.com/ai) | — | commercial | Time tracking with an AI-coding dashboard and leaderboards | mature; the format to study |

## What every one of them gets right, and we must match on day one

These are table stakes, not differentiation. Failing any of them loses the star
before the reader reaches the interesting part.

1. **Zero-friction first run.** `npx ccusage@latest`. One command, no account,
   no API key, no config. Our equivalent must be one command too.
2. **Local-first, stated loudly.** "Your conversations never leave your
   computer" is the top-three line in every README here. TokenTracker's headline
   is literally *"100% local. No account, no API keys."*
3. **Breadth of tool support.** ccusage covers 16 agents, TokenTracker 32,
   aiusage 25+. Breadth is the single strongest correlate with stars in this
   category, because it is what makes the tool relevant to a stranger.
4. **A screenshot that carries the pitch.** Heatmaps, sparklines, a KPI row.
5. **Cost estimation from a maintained rate card.** ccusage leans on LiteLLM's
   price DB — outsourcing the staleness problem.

## What they all do that is structurally weak

### 1. They are odometers, not coaches

Every tool in the table answers *how much*. None answers *what should I change*.
The closest anyone gets is Claude-Code-Usage-Monitor's burn-rate warning
("you'll hit your limit in 42 minutes"), which is a gauge, not advice, and
sniffly's error taxonomy, which is diagnostic but not economic.

This is the gap. A number that goes up teaches nothing. A finding — *"38% of
your read tokens are being rebuilt instead of reused; here is the session where
it happens; here is what it costs you a month"* — changes behaviour, and
behaviour change is what people tell their colleagues about.

### 2. Their leaderboards reward the wrong thing

tokscale and viberank rank by **total tokens and total spend**. viberank
describes itself as "the public tokenmaxxing leaderboard." The top of that board
is, definitionally, the person who wasted the most.

That works as a novelty in a market where a $200/month Max seat is a normal
expense. It is actively hostile in a market where the median developer is on an
$18/month plan and the reason they installed a tracker is that money is tight.
It also has no second act: once you have seen the leaderboard, there is no
reason to return, because your rank is a function of your budget, not your
skill.

**Ranking by efficiency instead of volume inverts this.** Efficiency is
improvable, so the board is a reason to come back. It is fair across budgets, so
a student in Da Nang and a staff engineer in Singapore compete on the same axis.
And it is aligned with the user's actual interest rather than the vendor's.

### 3. Their privacy model is a promise, not a mechanism

"No telemetry" is easy while there is no server. The moment a leaderboard
exists, the design question is what crosses the boundary, and the answers on
offer are thin: tokscale does "Level 1 validation" on submissions and publishes
a profile page; aiusage sends "signed aggregate uploads containing only token
totals"; TokenTracker sends an "anonymous daily heartbeat (one-way machine ID
hash)" that is on by default and opted out through an environment variable.

None of them publishes a threat model, a k-anonymity floor, an unlinkability
argument, or a function you can read in full before consenting. For a Chinese or
Indonesian developer uploading data derived from an employer's codebase, that
gap is not academic — it is the reason they will not install it.

### 4. They price tokens flat, which is simply wrong for Chinese vendors

DeepSeek bills peak and off-peak. Z.ai's GLM bills peak and off-peak on a
different clock. Every tracker in the table multiplies tokens by one number,
which means their cost figure for a DeepSeek user is wrong by up to 2× — and,
worse, it hides the largest single lever that user has.

### 5. Their dollar figure is fictional for most of our users

Every tool reports "estimated cost" as if it were a bill. For a developer on a
GLM Coding Lite plan at $18/month, an estimate reading $412 is not a bill, a
budget, or a warning. It is a **shadow price** — and its only useful role is to
be divided by the $18 they actually paid. Nobody frames it that way.

### 6. Contribution is bottlenecked on the maintainer

Adding a provider means reverse-engineering a format the maintainer does not
use. This is why coverage of Chinese tools is thin across the board — a Korean
or American maintainer has no Lingma transcripts to test against. The projects
that grew fastest grew by *breadth*, and breadth is exactly what this
bottleneck throttles.

## What is worth copying outright

All of these are MIT or similar, and all are good ideas we should not
re-invent out of pride:

| From | Idea | Why |
|---|---|---|
| ccusage | `npx`-style zero-install; `--json`; statusline hook; MCP server | Distribution surface, not features |
| Claude-Code-Usage-Monitor | P90 self-calibrated limit detection when a vendor publishes no number | The right answer to unpublished quotas |
| TokenTracker | Multi-language READMEs; achievements and streaks; native widgets | Reach and retention |
| token-monitor | Local-currency display; archiving usage before the vendor prunes it | Both matter more in our market |
| sniffly | Opt-in share links with a per-field toggle | The consent UI to imitate |
| aiusage | Quota pressure as a first-class metric | The subscriber's real question |
| tokscale | README embed cards | The cheapest organic distribution in open source |
| WakaTime | Separate AI and non-AI leaderboards; embeddable badges | The mature version of all of this |

## The honest read

There is no moat in parsing JSONL. Every tool here reads the same files. The
differentiation available is in **interpretation** (what the numbers mean),
**economics** (what they actually cost this specific user), and **trust** (what
leaves the machine). All three are places the incumbents chose not to compete,
and all three are places where being built by and for Asia-Pacific developers is
a structural advantage rather than a marketing line.

## See also

- [02-POSITIONING-AND-WEDGE.md](02-POSITIONING-AND-WEDGE.md) — what we build instead
- [03-SEA-CHINA-PRODUCT-THESIS.md](03-SEA-CHINA-PRODUCT-THESIS.md) — the regional case
- [04-GROWTH-FLYWHEEL.md](04-GROWTH-FLYWHEEL.md) — how it spreads
- [05-RISKS.md](05-RISKS.md) — what kills it
