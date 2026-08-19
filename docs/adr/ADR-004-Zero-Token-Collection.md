# ADR-004 — Collect from provider transcripts; never instrument the conversation

**Status:** accepted · **Date:** 2026-08-02 · **Supersedes:** —

## Context

The obvious way to track AI usage is to instrument it: a hook that logs each turn, a wrapper that records requests, or — worst — asking the model to summarise its own usage into a log. Every one of those spends the resource being measured. A tracker that costs tokens per turn taxes exactly the behaviour it wants to observe, so it gets switched off during the heavy sessions that matter most.

Investigation found the cost avoidable entirely. Claude Code already writes an append-only JSONL transcript per session under `~/.claude/projects/`, and every assistant turn already carries the accounting the API returned:

- `message.model`, `message.stop_reason`
- `message.usage.input_tokens`, `output_tokens`
- `message.usage.cache_creation_input_tokens`, `cache_read_input_tokens`
- `message.usage.cache_creation.{ephemeral_1h,ephemeral_5m}_input_tokens` — the TTL split
- `message.usage.service_tier`, `speed`, `server_tool_use`
- `cwd`, `gitBranch`, `sessionId`, `timestamp`, `effort`, `isSidechain`, `slug`
- `tool_use` blocks in `message.content` — every tool name invoked

Measured at adoption: 245 transcript files, 241 MB, 18,095 assistant turns over 56 days.

## Decision

Collect by reading provider-written files. Emit **no** model calls, prompts, hooks, or wrappers in the collect → analyse → render path. Tokens are spent only when the owner explicitly asks a model to reason about the digest.

## Consequences

**Good**
- Daily marginal cost is zero, so measurement is continuous instead of rationed.
- Retroactive: the first run produced 56 days of history no instrumentation could have recovered.
- No observer effect on prompts, caching, or latency.
- Nothing installed into the observed tool; no failure mode where the tracker breaks the workflow.

**Bad / accepted**
- Coupled to an undocumented internal format. A provider change can break parsing — mitigated by defensive parsing (unknown lines skipped, missing keys tolerated) and an append-only store, so a break loses new data, never history.
- Limited to what the provider records. Per-turn wall-clock duration and human think-time are unavailable.
- Only providers with a local passive source can ever be supported (Principle 2).

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Hooks writing a log per turn | Adds latency to every turn, only captures usage after installation, can break the host workflow |
| An API proxy in front of the provider | Large operational surface; breaks auth; a single point of failure for real work |
| Asking the model to self-report usage | Costs tokens per turn, and self-reported counts are unreliable by construction |
| Provider billing dashboard export | Org-level, no session/project/tool granularity, no cache-TTL split, not local |

## Revisit when

A provider worth supporting writes no local transcript, or a stable documented usage export ships — then prefer the documented surface and keep this collector as fallback.
