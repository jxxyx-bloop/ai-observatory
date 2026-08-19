# ADR-006 — Store metadata only; never prompt or completion content

**Status:** accepted · **Date:** 2026-08-02 · **Amended by:** [ADR-008](ADR-008-Derived-Path-Labels.md), [ADR-010](ADR-010-Cohort-Analytics-Store.md)

> **Amendment (2026-08-10).** ADR-010 *tightens* this ADR for pooled data
> without relaxing anything here. Every prohibition below still holds for the
> personal store. Rows that leave the personal store and enter the company
> comparison additionally drop the working-directory basename and the session
> id, which ADR-006 and ADR-008 permit locally — because a folder name is a team
> name once it is pooled.

> **Amendment (2026-08-03).** ADR-008 narrows one clause below. Path-shaped tool
> arguments may now be *read* to derive two coarse labels — a repository name and
> a folder bucket — which are stored in place of the path. Argument **values** are
> still never stored, and every other prohibition here stands unchanged.

## Context

The source transcripts contain everything: full prompts, full completions, file contents that were read, shell commands that were run, absolute paths, and — for work in a corporate repo — potentially confidential material and personal data.

A tool that copies any of that into a second store doubles the exposure surface for no analytical gain. Every question in `00-VISION.md` is answerable from counts and names.

## Decision

Events carry counts, model names, tool **names**, timestamps, and the working-directory **basename**. They never carry:

- prompt text or completion text
- file contents, diffs, or code
- shell command strings or tool arguments
- absolute paths (basename only — `acme-platform`, not `/Users/…/GitHub/acme-platform`)
- session titles or user-authored labels

The collector enforces this at the parse boundary: `_turn()` reads `usage`, `model`, `stop_reason`, and tool-use `name` fields only. Tool *arguments* are never touched.

## Consequences

**Good**
- Privacy by construction, not by policy. There is no redaction step to forget, because the sensitive data never enters the store.
- 40× smaller than the source (241 MB → 5.7 MB), which is what makes the digest tier possible.
- The store and the rendered HTML are safe to share, screenshot, or archive without a review pass.
- Removes the temptation to build content-dependent features that would later have to be walked back.

**Bad / accepted**
- Some desirable insights are out of reach. "You re-read the same file five times" needs tool arguments; "this session was low-value" needs to know what was produced. Proxies are used instead — writes-to-reads ratio, peak context, session shape — and are labelled as proxies.
- Cannot reconstruct what happened in a session from the store alone. Correct: that is what the transcripts are for.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Store content, redact on export | One forgotten export path leaks everything; redaction is never complete |
| Store hashes of file paths to detect re-reads | A hash of a path is still a stable identifier of private structure; the insight is not worth it |
| Store first N characters of prompts | "A little content" is content. No principled place to stop |

## Revisit when

Never for content. If a specific insight genuinely requires an argument-derived signal, prefer deriving a **non-reversible counter at collection time** (e.g. "distinct read targets in this session: 7") over storing the arguments themselves — and record that as its own ADR.
