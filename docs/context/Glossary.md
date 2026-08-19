# Glossary

Vocabulary specific to this project.

## Token accounting

| Term | Meaning |
|---|---|
| **Turn** | One assistant response. The atomic unit of measurement and billing. |
| **Input tokens** | The *uncached* remainder of the prompt, billed at full rate. **Not** the prompt size. |
| **Cache write** (`cache_create`) | Tokens written to the prompt cache. 1.25× input at 5m TTL, 2× at 1h. |
| **Cache read** (`cache_read`) | Tokens served from cache at 0.1× input. |
| **Context size** | `input + cache_create + cache_read` — everything the model read that turn. |
| **Cache read share** | `cache_read ÷ (cache_read + cache_create + input)`. The headline efficiency number. |
| **Cache reuse** | `cache_read ÷ cache_create`. Reads per token written; above ~3× justifies the 1h TTL. |
| **TTL split** | How a cache write divides between 5-minute and 1-hour lifetimes. Priced differently, so tracked separately. |

## Project vocabulary

| Term | Meaning |
|---|---|
| **Store** | `data/events-*.ndjson`. Append-only normalized history. |
| **Digest** | `data/digest.json`. The ~60 KB aggregate every consumer reads (ADR-005). |
| **Surface** | A consumer of the digest — the HTML report or the text output. |
| **Cursor** | Byte offset per source file, enabling incremental sync. |
| **Collector** | Provider-specific reader implementing the `Collector` interface. |
| **Detector** | One rule in `insights.py` that emits findings. |
| **Finding** | A detector's output: observation + evidence + action + confidence. |
| **Materiality gate** | Demotes cost findings below a monthly threshold so the top of the list stays meaningful (ADR-007). |
| **Sidechain** | A turn belonging to a delegated subagent rather than the main conversation. |
| **Workspace** | Basename of the working directory — the project proxy. Not a full path. |
| **Peak context** | The largest single-turn context a session carried. |
| **Writes/reads** | Produce-to-explore ratio. A **proxy** for output, not a measure of value. |
| **Light turn** | An assistant turn under ~150 output tokens — usually mechanical. |

## Model and pricing terms

| Term | Meaning |
|---|---|
| **Canonical alias** | Undated model id (`claude-opus-5`). Dated snapshots fold to it at collection. |
| **Tier** | `frontier` / `opus` / `sonnet` / `haiku`. Groups models for premium-tier detection. |
| **Effort** | Reasoning-depth setting (`low`…`max`), when recorded. |
| **Premium tier** | `frontier` or `opus` — where routing mechanical work away actually saves. |

## Terms deliberately avoided

- **"Productivity"** — measures where effort went, not whether a person was good.
- **"Spend"** unqualified — always "estimated spend".
- **"Value"** for `writes/reads` — it is a proxy; calling it value would overclaim.
- **"Waste"** as a verdict — findings describe a pattern and an action, not a judgement.
