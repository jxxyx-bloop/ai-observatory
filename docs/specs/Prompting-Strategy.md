# Spec — Prompting Strategy

The engine itself makes **no model calls** (Principle 3). This spec covers the other direction: how a model should be prompted when *you* ask it to reason about your usage.

## The rule

**Feed the digest, never the store.** `data/digest.json` is ~60 KB and holds every number the analysis needs. The store is 5.7 MB and the source is 241 MB. Reading either of those to answer "how should I change my usage" is the exact waste the tool exists to find.

```
Read data/digest.json and answer: <question>
```

## Why the findings are pre-computed

`digest.findings` already contains deterministic, evidence-backed conclusions (ADR-007). A model asked about usage should **start from those and reason past them**, not re-derive them. Re-deriving costs tokens, is non-reproducible, and risks arithmetic the rules already got right.

Good: *"Given these findings, which one should I act on first given that I mostly work in short bursts?"*
Poor: *"Analyse my usage and tell me what's wrong."* — this invites recomputation of what is already computed.

## Determinism, where it matters

Anything that feeds a stored artefact must be reproducible:

- Thresholds live in `insights.py::T`, not in a prompt.
- Severity and materiality are arithmetic, not judgement.
- The same digest produces the same findings on every run.

Model reasoning is for interpretation and trade-offs — the parts that genuinely need judgement — and its output belongs in a conversation or a note, never silently back into the digest.

## Useful prompt shapes

| Question | Prompt shape |
|---|---|
| Which finding matters most for me? | Digest + your constraints (time, focus pattern, what you are optimising for) |
| Did last month's change work? | Two digests, ask for the delta on named metrics |
| Is this workspace ranking consistent with my priorities? | `by_workspace` + your own stated priority order |
| Why is this session so expensive? | The single `sessions[]` row, not the whole digest |

For the last one, pass only the relevant slice. Sending 60 KB to answer a question about one session is the same mistake at smaller scale.

## What not to do

- **Don't** ask a model to generate the findings at report time — that is ADR-007's rejected alternative.
- **Don't** paste raw transcripts into a session to "get more detail". They contain the content this tool deliberately never stores (ADR-006), and reintroducing it into a prompt undoes that guarantee.
- **Don't** ask for a productivity verdict. The digest measures where effort went, not whether the person was good. A model asked to score a person from this data will oblige, and the answer will be unfounded.

## If a model ever generates findings

Not planned. If it happens, the output must be labelled as model-generated, carry its own confidence, and be stored separately from rule-based findings — never merged into `digest.findings`, so the reproducible set stays reproducible.
