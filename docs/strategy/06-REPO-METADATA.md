# Repository metadata — the description and the topics

GitHub indexes the repository **description** and **topics** alongside the name,
and topic pages are their own browse surface. Both were empty until this
document; an empty description is a search result with nothing in it.

They are set in the GitHub UI (**About** → gear), not in this repository, so
they are recorded here to stop them drifting or being lost.

## What the category actually does

Sixteen repositories carrying `topic:token-usage`, from 116 to 9,611 stars,
measured rather than eyeballed:

| Trait | Share |
|---|---|
| Contains "token" | **93%** |
| Names at least one tool (Claude Code, Codex, Cursor…) | **87%** |
| Opens with a qualifier + a category noun | **81%** |
| Contains "cost" | 62% |
| Ends on a differentiator clause | 56% |
| Says "local" / "local-first" | 50% |
| Contains a digit | 25% |

**Median length 155 characters**; 160 across the repos above 600 stars.
[`token-optimizer`](https://github.com/alexgreensh/token-optimizer)'s
80-character *"Find the ghost tokens. Fix them…"* is the shortest in the set and
an outlier, not the pattern — imitating it means dropping the three traits that
nearly everyone else keeps.

The recurring shape, clearest in
[`TokenTracker`](https://github.com/xiufengsun/TokenTracker) (159 chars) and
[`token-monitor`](https://github.com/Javis603/token-monitor) (179):

> **[qualifier] [what it measures] [category noun] for [tools] — [differentiator]**

"AI coding" appears in 43%, but always as a concrete category noun — *AI coding
**agents***, *AI coding **tools***. Never as a bare possessive. "your AI coding"
is the vague version and is what to avoid, not the phrase itself.

## Description

> Local-first token usage & cost tracker that says what to change, not just what you spent. 15 checks, each priced. Claude Code, Codex, Kimi, Antigravity.

152 characters, against a category median of 155.

**The first sentence is 89 characters, and that is deliberate.** GitHub's About
box truncates around ninety; `token-monitor`'s tool list is cut mid-word there.
Everything past that point is indexed by search but never read by a human, so
the ordering is forced: the claim no competitor can make goes first, and the
tool names — which are also topics, and so indexed twice over — take the tail.

That first sentence is the whole product. Every other tracker in the table above
reports *what you spent*. This one says *what to change*. Putting the contrast
inside the visible window is worth more than putting the tool list there.

Rejected, and why:

- *"Find the waste in your AI coding. Price it. Fix it. Runs on your machine."*
  — 73 characters, no "token", no "cost", no tool named. Three of the category's
  strongest traits dropped at once, in exchange for a rhythm copied from the one
  repo that is an outlier.
- A version leading with the tool list — conventional, but it spends the visible
  ninety characters on the half a reader could get from thirty other repos.

## Topics

Frequency across the fourteen top repos in the category, which is what decides
the first nine:

```
token-usage 13/14 · claude-code 12/14 · developer-tools 10/14 · cli 8/14
codex 8/14 · cost-tracking 7/14 · observability 6/14 · local-first 6/14
dashboard 6/14
```

The twenty to set, at the cap:

```
token-usage      claude-code      developer-tools   cli
codex            cost-tracking    observability     local-first
dashboard        privacy-first    python
token-tracker    usage-tracker    ai-cost
kimi             antigravity      deepseek          glm
peak-pricing     plan-value
```

Four groups, and only the last is a guess.

**Proven by frequency** (row 1–3 above). `cost-tracking` — not `cost-tracker`,
which one repo in fourteen uses. `observability` is included on the evidence
even though it also means LLM tracing elsewhere: six of fourteen here use it,
including the two largest, and the data beats the worry.

**The tools we actually read** — `claude-code`, `codex`, `kimi`, `antigravity`,
and no others, checked against `observatory/collectors/`. A topic for a tool
with no collector draws a visitor who bounces on the first paragraph, and not
overclaiming is this project's whole argument.

**The vendors we price by the hour** — `deepseek`, `glm`. Both are implemented
in [`pricing.py`](../../observatory/pricing.py), not aspirational.

**Terms to own** — `peak-pricing`, `plan-value`. Nothing in the category uses
either. Speculative by construction: an uncontested topic is a page this project
sits alone on, and both name a real differentiator rather than a slogan. The
same move `token-optimizer` makes with `ghost-tokens`.

Dropped after measuring: `token-cost` and `cost-optimization` (rare), and
`llm-cost` (rarer). Reserve, if a slot frees: `ai-coding`, `anthropic`, `llm`,
`ai-tools`.

## Homepage

Set the **Website** field to the live site. It renders as a link in the About
box and is one of the few outbound links GitHub gives a repository.
