# Repository metadata — the description and the topics

GitHub indexes the repository **description** and **topics** as well as the
name, and topic pages are their own browse surface. Both were empty until this
document; an empty description is a search result with nothing in it.

They are set in the GitHub UI (**About** → gear, and Settings → General), not in
this repository, so they are recorded here to stop them drifting or being lost.

## The split

The two fields do different jobs, and the strongest repos in this category do
not make them do the same one.

| Field | Job |
|---|---|
| **Description** | Sell. Short imperative sentences a stranger reads in one pass. |
| **Topics** | Carry the keywords. Exact-match browse surfaces, no prose. |

[`token-optimizer`](https://github.com/alexgreensh/token-optimizer) (1.9k stars)
is the clearest example: its description — *"Find the ghost tokens. Fix them.
Survive compaction. Avoid context quality decay."* — is 80 characters, four
imperatives, and names **no tool at all**. `claude-code`, `token-usage` and
`context-window` are topics instead. The description does not have to carry the
search terms, so it is free to be a sentence rather than a keyword list.

## Description

> Find the waste in your AI coding. Price it. Fix it. Runs on your machine.

Seventy-two characters, four clauses, one idea each. It states the loop the
product actually performs — find, price, fix — and closes on the local-first
promise that is table stakes in this category and the first thing a reader
checks for.

Deliberately absent: "token", "cost", "Claude Code". Those are topics. Spending
description characters on words that are already indexed elsewhere buys nothing
and costs the sentence its rhythm.

## Topics

```
token-usage      token-tracker    token-cost       ai-cost
cost-tracker     cost-optimization
claude-code      codex            kimi             antigravity
deepseek         glm
peak-pricing     plan-value
local-first      privacy-first
```

Four groups, and each is there for a different reason.

**The category words** (`token-usage`, `token-tracker`, `token-cost`, `ai-cost`,
`cost-tracker`, `cost-optimization`) are what someone types when they do not yet
know this project exists. `token-usage` in particular is carried by every
serious competitor — [`token-monitor`](https://github.com/Javis603/token-monitor),
[`TokenTracker`](https://github.com/xiufengsun/TokenTracker), `token-optimizer`
— which is the evidence that it is the browse path that matters.

**The tools we actually read** (`claude-code`, `codex`, `kimi`, `antigravity`)
and no others. A topic for a tool without a collector would draw a visitor who
bounces on the first paragraph, and this project's whole argument is that it
does not overclaim.

**The vendors we price by the hour** (`deepseek`, `glm`). Defensible because
peak/off-peak billing for exactly these two is implemented in
[`pricing.py`](../../observatory/pricing.py), not aspirational.

**The terms we would like to own** (`peak-pricing`, `plan-value`). Nothing else
in this category uses either. A topic nobody competes for is a page this project
sits alone on, and both name a real differentiator rather than a slogan —
the same move `token-optimizer` makes with `ghost-tokens`.

Held in reserve, if a slot frees up: `usage-tracker`, `llm-cost`,
`developer-tools`, `cli`, `python`, `dashboard`. All real browse paths, all
lower signal than the sixteen above. The cap is twenty.

## Homepage

Set the **Website** field to the live site. It renders as a link in the About
box and is one of the few outbound links GitHub gives a repository.
