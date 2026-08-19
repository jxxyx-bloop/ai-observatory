# ADR-008 — Derive repository and folder labels from paths, store neither path

**Status:** accepted · **Date:** 2026-08-03 · **Amends:** ADR-006

## Context

ADR-006 attributes a turn by the working-directory basename. That works only when the working directory *is* the repository. In practice the largest single bucket on this machine was `GitHub` — 1,849 turns and an estimated $533 — because those sessions were launched from `~/GitHub`, the folder that holds every repository. The label was accurate and useless: it named a parent directory, not a piece of work.

The same problem repeats one level down. A monorepo's folder taxonomy *is* its structure — `apps/<name>/`, `packages/<name>/`, `services/<name>/`. "I spent $1.1k on acme-platform" is not a finding. "$255 went to `app:checkout` and $14 to `docs`" is.

The signal needed to close both gaps is the file paths the turn touched, which live in tool-use arguments — exactly what ADR-006 says the collector never reads.

## Decision

Path-shaped tool arguments (`file_path`, `path`, `notebook_path`, `workdir`, `cwd`) may be **read in memory** and passed through a classifier that returns two coarse labels. The labels are stored; the path is not, and never leaves the parse function.

- `repo` — a repository name, e.g. `acme-platform`. Worktrees resolve to their parent repository.
- `surface` — a bucket inside that repository, e.g. `app:checkout`, `people`, `kb/core`, `tooling/skills`. Depth is capped by the rules in `engine/topology.json`; a filename never becomes a label.

This narrows ADR-006's blanket "tool arguments are never touched" to **"argument values are never stored"**. Everything else in ADR-006 stands unchanged: no prompt text, no completion text, no file contents, no shell command strings, no absolute paths.

Three rules keep the labels honest:

1. **Coarse by construction.** Rules match on leading path segments only. `docs/people/jane-doe.md` yields `people`, never the person's name.
2. **Where it ran beats what it touched.** A turn is credited to its working-directory repository when there is one; touched files are the fallback, which is what rescues the `~/GitHub` sessions.
3. **Unattributed is a valid answer.** Paths outside every configured root return nothing rather than a guess, and turns that name no file inherit the nearest attributed turn *in the same session* only.

## Consequences

**Good**

- The largest bucket stops being a parent folder. `GitHub` disappeared entirely; its spend redistributed to the repositories that actually did the work.
- Project-level spend inside a workspace repo becomes visible, which is the question the dashboard was built to answer.
- The store stays small and shareable — two short strings per event, both drawn from a bounded vocabulary.
- The rules are data, not code. Adding a repository or a folder taxonomy is an edit to `topology.json`.

**Bad / accepted**

- A label is an inference, not a fact. A turn credited to `app:checkout` is credited because it edited a file there or sat next to one that did. The dashboard says so in its footer.
- Only tools that name a file contribute. `Bash` does not, so command-driven work relies on the session carry-forward.
- The vocabulary leaks *structure* — someone reading the store learns this repo has a folder called `people`. Judged acceptable: the folder taxonomy is already in the repo's README.
- Schema bumped to v2; a full `sync --full` is required to backfill.

## Privacy check

The strongest test is what an exported page reveals about a specific person. Under ADR-006 alone: nothing, and also nothing useful. Under this ADR: that the people folder were touched for 3 turns and ~$14. Still no name, no file, no content. That is the intended stopping point — one level above the filename, permanently.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Leave ADR-006 alone; live with `GitHub` as the top bucket | The headline chart was measuring the shell's starting directory. A dashboard that cannot answer "which project" is not worth publishing |
| Store the repo-relative path, redact on render | Same failure mode ADR-006 already rejected — one forgotten export path leaks the structure. Classify at the parse boundary instead |
| Hash the paths | A stable hash is still a stable identifier, and it is unreadable. ADR-006 rejected this for re-read detection; it is no better here |
| Infer the project from the git branch instead | Branches are named for changes, not projects, and 3,652 turns in the `~/GitHub` sessions carried the branch `HEAD` |
| Ask the user to tag sessions manually | Tagging that depends on discipline stops happening in week two |

## Revisit when

- A rule starts producing labels that identify a person, a customer, or a vendor. Coarsen the rule; the cap on depth is the whole safeguard.
- The `unattributed` bucket grows past ~10% of spend — the carry-forward is failing and the attribution needs a better signal, not a wider net.
- Someone proposes storing a filename "just for this one insight." That is a new ADR, and the answer starts at no.
