# Engineering Principles

Rules every contributor — human or agent — follows. When a change violates one of these, say so and stop; do not quietly relax the rule.

## 1. Local-first

All data stays on the machine that produced it. No network calls in the collect → analyse → render path. No account, no sync, no telemetry about the telemetry. The tool must work fully offline and on a plane.

## 2. Automatic collection

If usage has to be logged by hand, it will not be logged. Collection reads what providers already write. A new provider is only supported once a passive source is found — never by asking the user to record anything.

## 3. Zero-cost measurement

The measurement path must not consume the resource being measured. No model call is made to collect, normalise, aggregate, or render. Tokens are spent only when the owner explicitly asks a model to reason about the digest.

## 4. Read-only at the source

Collectors never write to, move, rename, or truncate a provider's own files. A bug in this project must never be able to damage a Claude Code transcript.

## 5. Metadata only, never content

Store counts, names, and timestamps. Never prompt text, completion text, file contents, shell command strings, or absolute paths. This is both a privacy rule and the reason the store is 40× smaller than its source.

## 6. Human-readable storage

NDJSON with full-word keys. The store must be greppable, diffable, and inspectable with `head`. If a format choice trades legibility for a marginal size win, legibility wins.

## 7. Simplicity over cleverness

Standard library only. No dependencies to install, audit, or keep current. No database until queries are measurably too slow. No framework for a page that renders once a day.

## 8. Progressive enhancement

Each layer works without the one above it. NDJSON is useful without the digest; the digest is useful without the HTML. A broken renderer must never block collection.

## 9. Vendor-agnostic downstream

Only collectors know about a provider. Everything after normalisation consumes the unified event schema. A provider-specific `if` outside `collectors/` is a bug.

## 10. Confidence on every estimate

Anything derived, modelled, or assumed carries a confidence level and says what it assumed. Exact numbers and estimates are never presented in the same visual register without labels.

## 11. No finding without evidence

Every insight names the numbers that produced it and the action it implies. A finding that cannot cite its evidence is deleted, not softened. Healthy usage is reported as healthy — the tool does not invent problems to appear useful.

## 12. Backward compatibility

The event schema adds keys; it never repurposes or removes them. `v` is bumped on breaking change and old partitions stay readable. History is append-only.
