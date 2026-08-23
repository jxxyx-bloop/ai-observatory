# Domain name and discoverability

The site is live on `ai-observatory.workers.dev`. This document decides what to
buy instead, and why — optimised jointly for search engines, for AI answer
engines, and for a maintenance budget that has to stay near the
[$1/month hosting line](../adr/ADR-015-Hosting-And-Data-Residency.md).

All prices below were checked against a live registrar API on 2026-08-23 and are
**first-year** prices. Renewal is the number that actually matters — see
[Cost](#cost-what-you-are-really-buying).

## Three things that decide this, and one that does not

**Does not: keyword-matching the domain.** Exact-match domains stopped being a
ranking factor when Google shipped the EMD update in 2012. `aicodingusage.com`
does not outrank anything by virtue of its spelling. What ranks is page content,
titles, and links. So there is no reason to pay a premium, or accept an ugly
name, to get keywords into the domain.

**Does: entity consolidation, and this is the AEO argument.** An answer engine
does not rank pages, it retrieves and cites *entities*. An entity accumulates
weight when one unambiguous string resolves to one thing everywhere it appears —
the GitHub repo, the README in thirteen languages, the `meta_title`, the docs,
the domain. Every place those strings disagree is weight that does not compound.
This repo has already spent that budget: `AI Observatory` appears as the project
name in the repo slug, every README, and every locale's `meta_title`. A domain
that matches it is free reinforcement. A domain that does not is a second entity
that has to be built from zero.

**Does: what the user actually types.** Nobody searches "AI observatory". They
search `claude code usage`, `ccusage alternative`, `how much am I spending on
claude code`, `token usage tracker`, `deepseek off peak pricing`. That intent is
real and it is capturable — but the place to capture it is page titles, H1s and
dedicated URL paths, not the domain. Those cost nothing.

**Does: whether a person can say it out loud.** Hyphens are the main casualty
here. `ai-observatory.com` cannot be dictated in a conference talk, gets typed
without the hyphen, and is mangled by the models that would otherwise cite it.
Excluded on principle, along with digits and doubled letters.

## The one real tension

`AI Observatory` is the project's existing entity, and it collides with several
much higher-authority ones: the OECD's AI Policy Observatory, Stanford HAI's AI
Index, and the various national "AI observatories". Those are policy
institutions, not developer tools, and they own the head term.

This cuts both ways and it is the whole decision:

- Ranking for the bare phrase `AI observatory` is not winnable and should not be
  attempted. Every qualified variant — `ai observatory claude code`,
  `ai observatory token usage`, `ai observatory github` — is winnable and is
  what a developer actually types anyway. Brand queries for developer tools are
  nearly always qualified.
- An answer engine asked a policy question may conflate the two. A modifier in
  the name (`Token Observatory`, `Agent Observatory`) removes the collision
  entirely, at the cost of a partial rename.

Recommendation below takes the first branch, because the rename cost is real and
the collision only bites on a query the project should not be chasing. The
second branch is ranked #2 rather than dismissed.

## The shortlist

Scores are 1–5. **Intent** is how close the name sits to what a user types;
**AEO** is entity strength — uniqueness plus agreement with what is already
written; **Recall** is memorability and whether it survives being said aloud.

| # | Domain | 1st yr | Intent | AEO | Recall | Why |
|---|---|---|---|---|---|---|
| 1 | **aiobservatory.dev** | $9.99 | 2 | 5 | 4 | Exact match to the entity the repo has already built, with zero rename. `.dev` is a category signal to a developer reading a SERP and forces HTTPS, which the [zero-network CSP](../design/DESIGN-SYSTEM.md) already satisfies. |
| 2 | **tokenobservatory.com** | $11.25 | 4 | 5 | 4 | The hedge. Kills the OECD/Stanford collision, keeps the Observatory metaphor and most of the brand equity, and `token` is a word that appears in real queries. `.com` is still the highest-trust TLD and the one people type by default. Costs a partial rename across thirteen `meta_title`s. |
| 3 | **aiobservatory.app** | $9.99 | 2 | 5 | 4 | Identical entity benefit to #1. Ranked below it only because `.app` implies something you install and sign into, which is the opposite of a stdlib-only script that runs locally. Worth holding as the defensive registration. |
| 4 | **agentobservatory.dev** | $9.99 | 3 | 4 | 4 | Bets on `agent` as the term that wins the next two years, which the collector list suggests is right. The risk is category confusion: "agent observability" already means LLM tracing (Langfuse, Arize, Braintrust), and drawing that audience wastes the click — they want spans, this ships a cost coach. |
| 5 | **tokenefficiency.dev** | $9.99 | 4 | 4 | 3 | The only name that states [the strategic inversion](02-POSITIONING-AND-WEDGE.md#the-strategic-inversion-rank-efficiency-not-consumption) — rank efficiency, not consumption — in the URL. `token efficiency` is a real and growing query. Marked down for length and for being a phrase rather than a name. |
| 6 | **tokencoach.dev** | $9.99 | 2 | 5 | 5 | The most memorable option and the most accurate: the differentiator is that it coaches rather than reports. Unique entity, trivially sayable. But it carries no query intent at all, so every visitor has to arrive via content or word of mouth. |
| 7 | **tokenusage.dev** | $9.99 | 5 | 2 | 3 | The highest literal intent match on the list — `token usage` *is* the query. Two problems: it is too generic to own as an entity, and it names the project after the odometer the [vision doc](../00-VISION.md#the-problem-it-solves) is explicitly trying to beat. Buying it is arguing the competitor's case. |
| 8 | **usagecoach.com** | $11.25 | 3 | 4 | 4 | `.com` plus the coaching differentiator plus a keyword. Held back by ambiguity — with no `ai` or `token` in it, "usage coach" could be a utilities app or a phone-plan tool, which is exactly the wrong first guess for an answer engine to make. |
| 9 | **tokenaudit.dev** | $9.99 | 4 | 4 | 4 | `audit` matches the evidence-and-verdict framing well and reads as trustworthy. The mismatch is cadence: an audit is a one-off, and the product wants to be [a daily cron habit](../../README.md#quick-start). Names the first run, not the loop. |
| 10 | **aicodingusage.com** | $11.25 | 5 | 1 | 2 | Listed as the pure keyword play so it can be argued against explicitly. Post-EMD it buys no ranking, it is three words nobody will recall, and it gives an answer engine nothing to cite. Included for completeness, not recommended. |

**Also verified available, at $9.99 each:** `aiobs.dev`, `tokengrade.dev`,
`cachereuse.dev`, `tokenwaste.dev`, `whattochange.dev`,
`tokenobservatory.dev`, and at $11.25 `codingcost.com`, `aicodingspend.com`.
`tokengrade.dev` is the interesting one — it maps to the
[Efficiency Grade](04-GROWTH-FLYWHEEL.md#loop-2--the-shareable-artefact-the-actual-distribution-engine)
and would make a good short link for shared cards if that loop ever ships. It is
not worth a second renewal before then.

**Checked and gone:** `aiobservatory.com`, `.org`, `.net`, `ai-observatory.dev`,
`observatory.dev`, `agentobservatory.com`, `aiusage.dev`, `tokencost.dev`,
`agentspend.com/.dev`, `tokenspend.com`, `aispend.dev`, `tokenaudit.com`,
`tokencoach.com`, `tokenefficiency.com`, `spendlens.dev`, `tokenlens.dev`,
`offpeak.dev`, `tokenreceipt.com`, `agentledger.dev`, `codingtokens.com`,
`aitokencost.com`, `aicodingcost.com`.

## Cost: what you are really buying

First-year pricing is marketing. Renewal is the recurring line item, and it is
where this decision can quietly cost more than the hosting it fronts.

| TLD | Typical renewal | Verdict |
|---|---|---|
| `.com` | ~$10–12/yr | Fine. Highest trust, no surprises. |
| `.dev` / `.app` | ~$12–14/yr | Fine. HSTS is mandatory, which this site already meets. |
| `.co` | ~$30/yr | Skip. `aiobservatory.co` is available at $29.99 and buys nothing `.dev` does not. |
| `.io` | ~$40–60/yr | Skip. |
| `.ai` | ~$70–100/yr, two-year minimum | **Skip.** A $140 minimum outlay to front a site that costs ~$1/month to run inverts the project's own economics. |

Two things that cut the recurring cost to the floor:

1. **Register anywhere, then move the domain to Cloudflare Registrar after the
   60-day ICANN transfer lock.** Cloudflare sells renewals at wholesale with no
   markup and includes WHOIS privacy free. The project is already on Cloudflare
   for hosting, so registrar, DNS and Workers end up in one account with one
   bill and nothing to reconcile.
2. **Buy one domain, not a defensive set.** The realistic downside of not owning
   `aiobservatory.com` is somebody parking it. At this stage that is a problem
   worth having, and $11/year each to prevent it is a worse trade than the same
   money spent on nothing.

## Recommendation

Buy **`aiobservatory.dev`** — $9.99, renewing near $12.

It is the only option that costs nothing in rename, reinforces an entity the
repo has already paid to build across thirteen languages, signals "developer
tool" in the SERP itself, and stays inside the maintenance budget. Its one real
weakness — the head-term collision with the policy observatories — applies to a
query the project should not be competing for.

If the collision is judged unacceptable, take **`tokenobservatory.com`** instead
at $11.25. It is the only alternative that fixes the collision without
discarding the brand, and `.com` renewal is *cheaper* than `.dev`.

Do not buy both.

## What actually has to change in the repo

The domain is centralised, so this is a small diff:

| Location | Change |
|---|---|
| [`site/build.py`](../../site/build.py) `SITE` | Default is already overridable via `SITE_URL`; set the env var in the Cloudflare project, or change the default. Feeds `canonical`, `hreflang`, `sitemap.xml` and `robots.txt` automatically. |
| [`site/tools/readmes.py`](../../site/tools/readmes.py) `HOST` | One constant. The translated READMEs are generated, so they follow. |
| Root [`README.md`](../../README.md) | Hand-maintained links to the demo and locale pages. |
| [`docs/setup/DEPLOY.md`](../setup/DEPLOY.md) | The walkthrough names the old host. |

Keep `ai-observatory.workers.dev` alive and **301 it to the new apex** rather
than letting it serve the same pages. Two hosts serving identical content splits
the signal that took thirteen locales to earn; the existing `canonical` tags
help, but a redirect is what actually consolidates it.

## The discoverability work the domain does not do

The domain is worth perhaps a tenth of this. The rest is free, and none of it is
built yet:

**Pages that match the query.** The site is one page per locale. The intent this
project serves is long-tail and specific, and each of these is a page:
`/claude-code-usage/`, `/ccusage-alternative/`, `/deepseek-off-peak-pricing/`,
`/glm-peak-hours/`, `/claude-code-cache-hit-rate/`. Every one is a question with
real volume, and the repo already holds a defensible, numeric answer to it —
which is precisely what neither a vendor dashboard nor a competitor tracker can
publish.

**`llms.txt` at the root.** There is a `robots.txt` and a `sitemap.xml` and no
equivalent for answer engines. A short file stating what the tool is, what it
reads, what it never stores, and what makes it different is the single
cheapest AEO artefact available.

**JSON-LD.** [`site/index.html`](../../site/index.html) emits Open Graph tags
and no structured data. A `SoftwareApplication` block — name, licence, price
`0`, `operatingSystem`, `codeRepository` — is the machine-readable form of the
entity argument this whole document rests on, and it is roughly fifteen lines.

**The comparison table, as a page.** The
[teardown](01-COMPETITIVE-TEARDOWN.md) is the highest-intent content in the
repo. `ccusage alternative` is a query a person types when they are already
looking for exactly this, and an answer engine asked to compare token trackers
will cite whoever published the table.
