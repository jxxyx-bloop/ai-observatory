# Spec — Surface Attribution

How a turn gets a `repo` and a `surface`. Config lives in `engine/topology.json`;
the classifier is `engine/paths.py`. Policy is [ADR-008](../adr/ADR-008-Derived-Path-Labels.md).

## The pipeline

Four stages, two at collection time and two at digest time.

**1. Split (`paths.split`)** — an absolute path becomes `(repo, repo_relative_path)`.
Checked in order: scratch prefixes → worktree marker (resolves to the parent
repository) → special roots (`~/.claude` → `claude-config`) → code roots
(`~/GitHub/<repo>/…`). A path matching none of these returns `(None, None)`.

**2. Surface (`paths.surface`)** — the repo-relative path becomes one bucket. The
repo's own rules are tried first, then the `*` rules, then a fallback of "the top
folder", or `(root)` for a file sitting at the repository root.

**3. Pick (`paths.pick_repo`)** — a turn may touch several repositories. Where it
*ran* wins; otherwise the first real repository it touched. Repositories listed in
`incidental_repos` lose every tie, so a session that happens to write a scratch
file is still credited to the work it was actually doing.

**4. Resolve (`analyze.resolve_attribution`)** — turns that named no file inherit
the nearest attributed turn in the same session, forward first and then backward
for the run before the session's first file touch. Real repositories get a full
pass before incidental ones fill any remaining gaps. Turns in a session that
touched nothing at all stay `unattributed`.

Stages 1–3 run per turn at collection time and are written to the event. Stage 4
runs over the whole store at digest time and is never written back.

## topology.json

| Key | Meaning |
|---|---|
| `code_roots` | Folders whose immediate children are repositories. `~` is expanded; longest match wins. |
| `worktree_marker` | Directory name that marks a worktree, so `<repo>/.claude-worktrees/<name>/…` credits `<repo>`. |
| `special_roots` | Absolute prefixes that *are* a repository in their own right, mapped to a name. |
| `scratch_prefixes` | Throwaway locations. Everything under them collapses to `scratchpad` / `scratch files`. |
| `incidental_repos` | Infrastructure repositories that lose attribution ties (stage 3) and go last in the fill (stage 4). |
| `surface_rules` | Per repository, an ordered list of `[pattern, label]`. |
| `lanes` | `default` plus ordered `rules`. |

A pattern matches leading path segments; `*` matches exactly one segment. A label
may interpolate `{n}` — segment *n* of the matched path, 0-based.

```json
["projects/active/*", "project:{2}"]
```

`projects/active/ai-observatory/engine/render.py` → `app:checkout`.

## Editing the rules

Rules are data. Edit `topology.json`, then rebuild — a rule change only affects
labels already written to the store after a full resync:

```bash
python3 engine/observe.py sync --full && python3 engine/observe.py digest
```

Two constraints when adding a rule:

- **Never bottom out at a filename.** `["docs/people/*", "people"]`
  is correct; a rule yielding `people/{2}` would put a person's name in the
  store. The cap on depth is the entire privacy safeguard (ADR-008).
- **Prefer few, stable buckets.** A repository with forty surfaces answers nothing.
  If a bucket never appears in the top ten, it did not need its own rule.

## Lanes

A lane splits usage into `work` and `personal`. It is **inferred, not observed** —
no transcript carries an account identity, and there is no field to read.

A rule matches on `repo`, `entrypoint`, and/or `provider`; all stated conditions
must hold, first match wins, anything unmatched takes `default`.

```json
{ "repo": "career-os", "lane": "personal" }
```

Two things this cannot do, and the dashboard says so in its footer:

- **Separate two accounts using the same tool in the same repository.** If Claude
  Code is run under a personal login in a work repository, those turns land in the
  `work` lane. Nothing local distinguishes them.
- **See claude.ai chat at all.** Browser and desktop-chat conversations leave no
  local token record, so no collector can reach them. The lane covers agentic tools
  only. See [Known-Limitations](../context/Known-Limitations.md).
