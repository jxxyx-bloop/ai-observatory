# Security policy

## Reporting a vulnerability

Please report privately via
[GitHub Security Advisories](https://github.com/jxxyx-bloop/ai-observatory/security/advisories/new)
rather than opening a public issue.

Include what you found, how to reproduce it, and what you think the impact is.
Expect an acknowledgement within a few days — this is a small project, not a
staffed security team, and setting that expectation honestly is better than
implying an SLA that does not exist.

## What counts as a vulnerability here

This project's threat model is unusual, so it is worth being specific. The
following are **in scope and treated as serious**:

- **Anything that gets sensitive content into an event.** Prompt text,
  completion text, file contents, tool argument values, shell commands, or an
  absolute path reaching `data/events-*.ndjson`. The parse boundary is the
  privacy boundary; a leak past it is a bug regardless of how it happens.
- **Anything that gets identifying data into a share payload.** A repository
  name, folder name, branch, workspace, session id, or a raw metric value
  crossing into `share.build()` output at any setting.
- **A path that transmits without consent.** Any code path that performs a
  network request when `settings.community.share` is `false`.
- **Cohort re-identification.** A way to link a fact row to an account row, or
  to isolate an individual within a suppressed slice.
- **Writes to a provider's files.** Collectors are read-only. Any write, move or
  truncation of a transcript is a bug.
- **Code execution from parsed data.** Anything in a transcript, spec file or
  config that can cause execution.

## Not vulnerabilities

- **Stale prices in `pricing.json`.** Wrong, and worth a PR, but not a security
  issue. Cost is a lens, not a bill.
- **The stable `auid`.** Submissions are pseudonymous, not anonymous, and this
  is a documented, accepted trade-off — see
  [Community-Share-Protocol](docs/specs/Community-Share-Protocol.md#threat-model-stated-plainly).
  Rotating the key would remove it and would also destroy the product.
- **A local user reading their own `data/` directory.** It is their data, on
  their machine, by design.

## Scope

This repository. There is no hosted service yet; when one exists, this file will
name it and its scope. No hosted instance will accept a byte of real data until
the consent flow has been reviewed by someone other than the author.

## Handling secrets

The engine requires no API key, token or credential to do anything, which is the
best available defence. If you ever find this project asking for a provider API
key, something has gone badly wrong — please report it.
