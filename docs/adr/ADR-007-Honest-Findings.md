# ADR-007 — Rule-based findings, with confidence and a materiality gate

**Status:** accepted · **Date:** 2026-08-02 · **Amended by:** [ADR-009](ADR-009-Collectors-Ship-With-A-Fixture.md)

> **Amendment (2026-08-10).** This ADR's honesty claim assumed a collector
> that finds nothing is telling the truth. ADR-009 closes the gap it missed:
> a collector silently parsing the wrong schema also reports zero, and looked
> identical to an honest finding until a user asked why his tool was missing.

## Context

An insight engine has a strong incentive to appear useful. If it reports nothing, it looks broken; so the easy path is to always surface something, phrase it urgently, and let the user sort out whether it matters. That produces a tool its owner learns to ignore — the worst outcome, because the data is genuinely good.

A second temptation is to generate findings with a model at report time. That is expensive, non-reproducible run to run, and capable of producing confident prose with no arithmetic behind it.

The first real build surfaced the failure mode concretely: a detector flagged a genuine pattern (a session that wrote 57k tokens to cache and never read them back) at **HIGH** severity, worth **$0.02/month**. Technically true, practically noise, and it occupied the top of the list.

## Decision

Three rules:

1. **Deterministic detectors.** Findings come from thresholded rules in `insights.py`, not from a model. They run in milliseconds, cost nothing, and produce the same output for the same input.
2. **Evidence and confidence on every finding.** Each carries the numbers that triggered it, a named action, and a `confidence` level. A finding that cannot cite its evidence is deleted, not softened.
3. **Materiality gate.** A cost-driven finding worth less than a threshold (currently $15/month) is **demoted to `low`** and annotated, not deleted. The pattern stays visible before it grows; the top of the list stays meaningful.

Healthy usage is reported as healthy, with severity `info` and the action "no action".

## Consequences

**Good**
- The top of the list can be trusted, which is the only property that matters for a tool used repeatedly.
- Reproducible: same data, same findings. Threshold changes are reviewable as a diff.
- Free to run, so findings regenerate on every report rather than being rationed.
- A model asked to reason about usage starts from arithmetic it does not have to redo.

**Bad / accepted**
- Rules only find what they were written to look for; a novel pattern is invisible until someone adds a detector.
- Thresholds are judgement calls tuned on one person's data. They are collected in a single `T` dict specifically so they are easy to find and re-tune.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Model-generated findings at report time | Costs tokens on every report, not reproducible, can assert without arithmetic |
| Report every detected pattern at face severity | Produces the $0.02 HIGH finding — trains the owner to ignore the list |
| Suppress immaterial findings entirely | Loses the early-warning value of a pattern that is small now and growing |

## Revisit when

A detector fires often and is repeatedly dismissed — that means the threshold is wrong, and the fix is the threshold, not the wording. Recalibrate `T` once several months of baseline exist.
