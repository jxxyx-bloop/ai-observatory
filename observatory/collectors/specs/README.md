# Declarative collector specs

One JSON file per provider. If a tool writes JSONL transcripts with token
counts on a record, it needs no Python — drop a spec here and it is supported.

**A spec without a fixture is not accepted.** Add
`tests/fixtures/<provider>.jsonl` with a handful of records in the vendor's
*real* record shape and a matching entry in `tests/test_specs.py`. This is
[ADR-009](../../../docs/adr/ADR-009-Collectors-Ship-With-A-Fixture.md): a
parser asserted against what the parser happens to expect will pass forever
while reading nothing.

## Fields

| Key | Meaning |
|---|---|
| `provider` | Short slug. Appears in the dashboard's provider filter. |
| `roots` | Glob patterns, `~` expanded. |
| `where` | Record must match all of these (dotted path → value) to be a priced turn. |
| `fields` | Dotted paths to `ts`, `session`, `cwd`, `model`, and the token counters. |
| `input_is_total` | `true` when the vendor's input count already includes the cache components. |
| `tools` | Where tool-call names live, and which argument keys are path-shaped. |
| `entrypoint_map` | Raw entrypoint value → `cli` \| `ide` \| `desktop` \| `sdk`. |
| `default_model` | Used when a record does not name one. |

Dotted paths support numeric indices: `message.content.0.name`.

## What a spec must never do

Emit prompt text, completion text, file contents, shell command strings, or an
absolute path. `path_args` are read only to derive a repo label, and the label
is what gets stored — never the path.

## Wanted

Qwen Code · iFlow CLI · CodeBuddy · Trae · Lingma / 通义灵码 · Comate · Doubao ·
CodeGeeX · MiniMax Agent · Cline · Roo Code · Aider · OpenCode · Goose · Zed.

If you use one of these, you are the only person who can add it correctly —
you have the transcripts to test against and the maintainers do not.
