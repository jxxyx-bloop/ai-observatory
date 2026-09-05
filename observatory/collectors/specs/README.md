# Declarative collector specs

One JSON file per provider. If a tool writes token counts to disk in any of
three shapes, it needs no Python — drop a spec here and it is supported.

| Shape | `format` | Worked example |
|---|---|---|
| One record per line | *(default)* | [`example-openai-jsonl.json`](example-openai-jsonl.json) |
| A whole document per file | `"json"` | [`example-json-per-file.json`](example-json-per-file.json) |
| A document holding an array | `"json"` + `records` | [`example-json-array.json`](example-json-array.json) |

The second and third exist because a great many tools — anything that keeps one
file per message, and most VS Code extensions — never write JSONL at all.

**A spec without a fixture is not accepted.** Add
`tests/fixtures/<provider>.jsonl` with a handful of records in the vendor's
*real* record shape and a matching entry in `tests/test_specs.py`. This is
[ADR-009](../../../docs/adr/ADR-009-Collectors-Ship-With-A-Fixture.md): a
parser asserted against what the parser happens to expect will pass forever
while reading nothing.

Real means captured from a run, or read off the vendor's own published types
and the code that fills them — never recalled or inferred from a similar tool.
Say in the test which of those it was, and at what version. Two things the
fixture cannot prove on its own, so check them by hand before opening the PR:
that `roots` actually matches where the files live (build the directory and
call `sources()`), and whether the vendor's input count already includes its
cached count, which decides `input_is_total` and silently inflates every cost
if you get it wrong.

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
| `from_path` | What the *file* knows and its records do not — see below. |
| `format` | `"json"` to parse whole documents. Omit for JSONL. |
| `records` | With `format: "json"`, the dotted path to the array of records. Omit when the document *is* one record. |
| `ts_unit` | `"millis"` or `"seconds"` when the timestamp is a number rather than an ISO-8601 string. |

Dotted paths support numeric indices: `message.content.0.name`.

## `from_path`

Some tools write the session id in the filename and never repeat it on a turn.
Without it every turn of that provider shares one session id, and each
per-session detector — context carried per turn, cache paid for and abandoned —
reports a number that means nothing.

```json
"from_path": {
  "session": ["/chats/([^/]+)/[^/]+\\.jsonl$", "/session-.*-([^-/]+)\\.jsonl$"],
  "sidechain": "/chats/[^/]+/[^/]+\\.jsonl$"
}
```

`session` is an ordered list of patterns tried against the file's path; the
first that matches wins and its **first capture group** is the id. Put the more
specific pattern first. `sidechain` is one pattern, and a match marks the turn
as delegated work — useful where a subagent's transcript is a file nested under
its parent session rather than a flag on the record. A record that carries its
own session id always wins over the filename.

## What a spec must never do

Emit prompt text, completion text, file contents, shell command strings, or an
absolute path. `path_args` are read only to derive a repo label, and the label
is what gets stored — never the path.

## Resuming a document that has no read position

A JSONL file is resumed from a byte offset. A JSON document has to be parsed
whole, so there is nowhere to seek to: progress is instead the count of priced
records already emitted, and the file is re-read whenever its size changes.
That is exactly right for a history that only ever grows, and wrong for one
that reorders or rewrites itself — worth checking before you assume a tool
qualifies.

## Wanted

Qwen Code · iFlow CLI · CodeBuddy · Trae · Lingma / 通义灵码 · Comate · Doubao ·
CodeGeeX · MiniMax Agent · Cline · Roo Code · Aider · OpenCode · Goose · Zed.

If you use one of these, you are the only person who can add it correctly —
you have the transcripts to test against and the maintainers do not. You do not
have to start from a blank file either:

```bash
ai-observatory contribute                      # what here can we not read yet?
ai-observatory contribute --from=~/.your-tool  # a draft spec, and a fixture
```

It infers the field paths from your own transcripts and rebuilds a fixture by
allow-list, so what it hands you is safe to attach to a pull request. It leaves
`input_is_total` unset on purpose — see step 2 of the checklist it writes.

### OpenCode — most of the way there

Read off `sst/opencode` rather than a running install, so treat it as a lead
and not a finished answer:

- One JSON document per message at `<data>/storage/message/<sessionID>/<id>.json`
  — so `format: "json"`, and the session id comes from `from_path`.
- `packages/schema/src/session-message.ts` declares the assistant message:
  `type: "assistant"`, `model`, `finish`, `time.created` (epoch **milliseconds**,
  hence `ts_unit`), and `tokens: {input, output, reasoning, cache: {read, write}}`.
- Tool calls sit in the message's own content array with `type: "tool"`, a
  `name`, and arguments under `state.input`.

Two things stopped it shipping, and both need someone with OpenCode installed:
the repo carries two message shapes (`content` in `packages/schema`, `parts` in
`packages/opencode/src/session/message-v2.ts`) and only a real file says which
one that version writes; and nothing in the source settled whether
`tokens.input` already contains `tokens.cache.read`, which is what
`input_is_total` turns on. Get that second one backwards and every OpenCode
user's costs are inflated by the size of their cache hits.
