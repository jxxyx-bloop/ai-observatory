# ADR-002 — Local-first, with no server, sync, or account

**Status:** accepted · **Date:** 2026-08-02

## Context

This store is a detailed behavioural record of one person: what they worked on, when, for how long, in which repositories, at what intensity. It is more revealing than a calendar. Any decision to move it off the machine needs a justification proportionate to that.

There is currently no such justification. The user is one person on one primary machine, and every question the tool answers can be answered locally.

## Decision

Everything runs on the machine that produced the data. No network calls in the collect → analyse → render path. No hosted dashboard, no account, no sync, no telemetry about the tool itself. The HTML output is a `file://` artefact with zero external requests.

## Consequences

**Good**
- Nothing to secure, authenticate, or breach. The threat model is "someone has your laptop", which is already true of the source data.
- Works offline and on a plane.
- No hosting cost, no uptime concern, no dependency on a service continuing to exist.
- No CSP, header, or referrer surface to get wrong — verified: the rendered page makes zero external requests.

**Bad / accepted**
- No cross-device history. Usage on a second machine is a separate store until someone merges them by hand.
- No sharing without exporting a file. Accepted: sharing is a later-phase question, not a v1 one.
- No mobile access.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Deploy the dashboard to a hosting provider | Publishes a behavioural record to a third party for a convenience the user does not need — the rendered file already opens from disk |
| A local server with a web UI | A process to run and keep patched, for no gain over a static file |
| Sync the store to private cloud storage | Solves multi-device, which is not yet a real problem; adds a credential and an exfiltration path |

## Revisit when

Multi-device usage becomes routine *and* the owner explicitly accepts the exposure. Even then, prefer syncing the **digest** (metadata aggregate) over the event store, and never the source transcripts.
