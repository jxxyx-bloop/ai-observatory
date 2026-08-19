# Vision

## Mission

A local-first AI usage observatory that helps a developer understand, optimise
and trust their own AI usage across providers — built for the way developers in
Southeast Asia and China actually buy AI.

## The problem it solves

AI usage has become a significant, compounding input to knowledge work, and it
is almost entirely unmeasured at the individual level. Vendor dashboards answer
"how much did this organisation spend on us"; they do not answer "where did *my*
effort go, what did it produce, and what am I wasting" — and no vendor can
answer it across vendors, which is where most of this audience actually lives.

The tools that do exist answer the first half. Every popular open-source token
tracker is an **odometer**: it reports volume and leaves interpretation to the
reader. A number that goes up teaches nothing.

## Success

The Observatory succeeds when it can answer, without being asked twice:

1. **Where did usage go?** By project, model, session, tool, hour, vendor.
2. **What created value?** Which sessions produced a change versus circled.
3. **Where is the leakage?** Context rebuilt instead of reused, premium models on
   mechanical work, exploration that never landed, tokens bought at peak rates
   that did not have to be.
4. **Was the plan worth it?** What a flat monthly subscription actually returned.
5. **When should something change?** A named action with the evidence behind it
   and an estimate of what it is worth.
6. **Am I unusual?** How this compares to developers with a similar setup —
   without anyone having to hand over their history to find out.

## The three constraints that shape everything

**It must cost nothing to run.** A measurement tool that consumes the resource it
measures is self-defeating. Collection is a local file read of data the provider
already wrote — zero tokens, zero prompts, zero daily overhead
([ADR-004](adr/ADR-004-Zero-Token-Collection.md)).

**It must be honest.** The tool's value is that its user believes it. Visible
confidence levels, estimates labelled as estimates, no finding without evidence,
and healthy usage reported as healthy. A tool that manufactures problems to look
useful is worse than no tool ([ADR-007](adr/ADR-007-Honest-Findings.md)).

**Nothing may leave the machine by default.** Not a preference — a design
constraint that shapes the community layer's whole architecture. The data here
is derived from an employer's codebase, and in this user base the blast radius
of a leak is somebody's job.

## Audience, in order

1. **The plan-constrained solo developer** in Jakarta, Ho Chi Minh City, Manila,
   Chengdu. Pays $10–30/month for one coding plan. Hits quota walls mid-task and
   has no idea why.
2. **The multi-vendor pragmatist.** Claude Code for hard reasoning, GLM or
   DeepSeek for bulk work, Qwen for anything with Chinese in it. Three
   subscriptions, no idea which is carrying its weight, and invisible to every
   vendor dashboard.
3. **The small agency.** 3–20 people billing clients by project. Needs to know
   which client is burning the seats — and must not become a surveillance tool
   while answering it.
4. **Everyone else.** The design generalises; it is simply not optimised for a
   US enterprise seat, because that user is already well served.

## What this is not

- **Not a billing reconciliation tool.** Token counts are exact; dollar figures
  are a lens, not an invoice.
- **Not a productivity score.** It measures where effort went, not whether the
  person was good.
- **Not a surveillance tool.** No prompt text, no completion text, no file
  contents, no commands ([Event-Schema](specs/Event-Schema.md)). No manager view,
  no ranking of named individuals — ever, on request or otherwise.
- **Not a proxy or gateway.** It never sits in the request path.
- **Not a consumption leaderboard.** Total spend is displayed and never ranked;
  the community layer ranks efficiency
  ([ADR-011](adr/ADR-011-Community-Layer.md)).
- **Not a chat-usage tracker.** claude.ai and ChatGPT web usage leave no local
  token record. It cannot be measured, and pretending otherwise would cost the
  credibility everything else depends on.

## Non-goals

Real-time streaming view · a SQL query surface · an org/manager dashboard ·
sitting in the request path · anything requiring an account to see your own data.

## Provenance

Extracted from a private single-user workspace where it ran daily against real
usage before any of it was generalised. That order matters: the detectors exist
because they changed one person's behaviour first, not because they seemed like
good ideas. What was added on extraction — peak/off-peak pricing, the plan and
quota model, local currency, declarative collectors, and an efficiency-ranked
community layer — is documented in
[ADR-011](adr/ADR-011-Community-Layer.md) through
[ADR-014](adr/ADR-014-Declarative-Collectors.md), and argued in
[docs/strategy/](strategy/).
