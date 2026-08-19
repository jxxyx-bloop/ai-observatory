# Spec — Insight Catalogue

Every detector in `insights.py`. Thresholds live in the `T` dict at the top of that file — one place, so recalibration is a single reviewable diff.

## Detectors

| id | Fires when | Severity | Why it is actionable |
|---|---|---|---|
| `cache-cold` | Cache-read share of read tokens < 55% | high | Rebuilding context costs ~12.5× reading it. The fix is session habits, not settings. |
| `cache-healthy` | Cache-read share ≥ 55% | info | Confirms the habit works; the number to watch for regression. |
| `cache-write-never-read` | A session wrote ≥ 20k cache tokens and read back 0 | high | The write premium paid for nothing — a session abandoned right after its first big load. |
| `premium-tier-light-turns` | ≥ 20 premium-tier turns, mean output < 150 tokens | medium | Mechanical work on a frontier model. Route it to a cheaper tier or lower effort. |
| `read-heavy-no-change` | Session with ≥ 6 reads, 0 writes, ≥ $0.50 | medium | Hunting instead of asking. Delegate the search so file bodies never enter main context. |
| `context-bloat` | A session turn exceeded 300k tokens of context | medium | Every later turn in that session re-reads all of it. |
| `session-churn` | ≥ 40% of sessions ended within 3 turns | medium | Short sessions never amortise their own context load. |
| `no-delegation` | Subagent output share = 0 | low | Delegation keeps bulk reading out of main context. |
| `subagent-fanout` | Subagent output share > 50% | medium | Fan-out where each agent re-establishes context costs more than one agent reading once. |
| `delegation-balanced` | Subagent share between 0 and 50% | info | Confirms proportionate delegation. |
| `cache-1h-underused` | ≥ 50% of writes at 1h TTL, < 3 reads per written token | medium | The 2× write premium needs ~3 reads to beat the 5m TTL. |
| `cache-1h-justified` | Same TTL mix, ≥ 3 reads per written token | info | Confirms the long TTL is paying off. |
| `tool-concentration` | One tool is > 40% of ≥ 50 total calls | low | A dominant tool often marks a workflow that could be one step. |
| `where-the-time-goes` | ≥ 3 workspaces with cost | info | Ranked investment, to compare against stated priorities. |
| `working-rhythm` | ≥ 50 turns recorded | info | Peak hour and out-of-hours share. |

## Finding shape

```json
{
  "id": "cache-cold",
  "severity": "high|medium|low|info",
  "title": "...",
  "finding": "what was observed, with the numbers in the prose",
  "action": "what to do about it",
  "evidence": { "...": "the numbers that triggered it" },
  "confidence": "high|medium|low",
  "est_monthly_saving_usd": 42.0,
  "demoted": "present only when the materiality gate downgraded it"
}
```

## The materiality gate

A cost-driven finding worth less than `T["material_monthly_usd"]` (currently $15/month) is demoted to `low` and annotated with `demoted`. It is never deleted — the pattern stays visible before it grows (ADR-007).

This exists because the first build produced a genuine `cache-write-never-read` finding at HIGH severity worth $0.02/month. True, and useless at the top of the list.

## Adding a detector

1. Write `def my_detector(digest, pricing) -> list` returning `_f(...)` findings.
2. Put every threshold in `T`, never inline.
3. Append to `DETECTORS`.
4. Add a row to the table above.

A detector that raises is silently skipped, so a bad rule cannot cost the owner the report. That also means a silent detector may simply be broken — check that it returns findings on data you know should trigger it.
