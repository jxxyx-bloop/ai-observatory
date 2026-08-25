# ADR-019 — Staying current: fetch daily, apply at launch, and say so on the page

**Status:** accepted · **Date:** 2026-08-24

## Context

[ADR-018](ADR-018-Launch-Surface-And-First-Run.md) split the two questions this
product has to answer about being out of date:

| Question | Answered by |
|---|---|
| Am I out of date? | the page, offline, from its own render stamp |
| Does a newer version exist? | the launcher, or `setup` |

Only the first was finished. `setup` fast-forwarded the checkout once, at
install time, and nothing afterwards ever asked again — so a person who
installed in July and clicked the icon every morning since was still running
July's code, with no surface anywhere that could tell them otherwise. Every
pricing correction, every new collector, every fix to the dashboard stopped at
the machine of whoever happened to re-run `setup`.

That is worse here than in most tools. A stale rate card does not degrade the
product, it makes it *confidently wrong*: `pricing.json` is the difference
between a dollar figure that means something and one that does not, and
CONTRIBUTING.md already calls a stale price "worse than silent".

The obvious fix — pull on every launch — buys the problem it is trying to
solve. It puts a network round trip in the click path, so the icon hangs on a
hotel wifi; and it applies code the moment it is downloaded, at the exact
moment somebody is waiting to look at a chart.

## Decision

### 1. Fetch and apply are separate, and days apart

    check   daily, unattended, from the launchd agent. `git fetch` writes
            objects and moves remote-tracking refs. It executes nothing.
    apply   at the next launch, from the generated runner, as a local
            fast-forward with no network in it.

By the time anybody clicks, the objects are already on the disk and applying is
a pointer move. This is the mechanism every update system that feels effortless
uses, and it is the only one that keeps a slow connection out of the path
between a person and their dashboard.

The two halves also have different trust profiles, and separating them is what
makes the automatic default defensible: fetching changes nothing that will ever
run, so it needs no permission. Applying does, so it happens at a moment that
was already a restart — and never while the user is looking at the result.

### 2. Auto-apply is the default, and it is never silent

`settings.json -> updates` takes `auto` (default), `notify`, or `off`.

Default-on is consistent with what `setup` already did without asking, and with
what these users chose when they typed `git clone`. What makes it acceptable is
the receipt: after an update lands, the freshness strip says what arrived, in
the words of the commits that arrived. A silent code change on somebody's
machine is not something this project should ever do; a visible one is just
maintenance.

**The receipt retires when the reader acts on it.** *(Amended 2026-08-25; the
original rule was a flat 24-hour clock.)*

A plain seen-once flag cannot work, because the 09:00 agent renders the page
while nobody is watching: the flag would be burned by a render no human ever
saw, and the one person it was written for would never see it. That is what
the clock was for.

But a plain clock could not work either, and shipping it taught us why. The
strip outlasted the thing it was reporting: somebody who read the receipt, ran
the refresh command the strip itself handed them, and watched the page rebuild
got the same sentence back — because re-rendering re-reads the same unexpired
state. Worse, the only thing that can retire a receipt is a render, and the
only scheduled render is the agent's at 09:00 local. An update applied at any
time after 09:00 therefore survived the *next* morning's render too, so the
effective window was 24–48 hours rather than the 24 the ADR claimed.

So the flag is scoped to renders a human is actually present for. `attended`
is true for any render that ends by opening a browser, and false for the
unattended paths that pass `--no-open` — cron, launchd, CI. The first attended
render earns the receipt and marks it seen; the next one retires it, because
by then the reader has both seen it and acted. An unattended render still
shows an unseen receipt and never burns it, which preserves the property the
clock existed to protect. `RECEIPT_HOURS` survives underneath as the backstop
for a reader who never refreshes by hand, and a render past it sweeps the dead
receipt out of `update.json` rather than carrying it for the life of the
install.

A notice that outlives its news is how you teach people to stop reading
notices, and this is the one notice the project cannot afford ignored.

### 3. A fast-forward or nothing, and dirty means *tracked* dirty

Never a merge, never a rebase, never a stash. When the tree has modified
tracked files the update is held and the *page says why* — the old best-effort
pull skipped silently, which is indistinguishable from being up to date.

Untracked files deliberately do not count. `data/` and `dist/` live inside the
checkout and anyone may leave a note beside them; treating that as "somebody is
working here" would switch updates off for most real installs and never explain
itself. Where an incoming commit genuinely collides with an untracked path, git
refuses per-file and that refusal is reported.

`settings.local.json` now actually overlays `settings.json`. .gitignore has
promised that file since the beginning and nothing read it, so the documented
way to set your own timezone left a modified tracked file in the checkout —
which is the one condition under which nothing fast-forwards. **Configuring the
tool switched its updates off.**

### 4. The page renders what it is handed

`updater.for_render` decides, in Python, which of two sentences applies — "a
newer version is ready" or "here is what last night's brought" — and the page
draws it in the strip that already exists. A `file://` document cannot compare
a clock to a repository and should not try. A waiting update outranks a fresh
receipt: both can be true within one day, and the one that needs an action is
the more useful sentence.

### 5. Version identity is whatever the repository decides

`git describe --tags --always` — so the day this project starts tagging
releases the page shows `v1.4` with no code change, and until then it shows a
short commit, which is honest rather than invented. The "what changed" lines
are commit subjects, which in this repository are already written as
user-facing sentences.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Pull on every launch | A network round trip in the click path. The icon hangs on bad wifi, and the failure lands on the person least able to diagnose it |
| Apply inside the daily agent | Rewrites the code of a running interpreter, at 09:00, with nobody watching. The runner applies in its own process, which exits before the engine starts |
| Ask before each update | The question is unanswerable — nobody can evaluate a diff from a Dock icon — and asking daily trains people to dismiss it |
| A version-check HTTP call to the GitHub API | A second network dependency and a second thing to rate-limit, for information `git fetch` already has. Revisit only for installs with no `.git` |
| Telemetry on version adoption | Contradicts ADR-002. The opt-in `share` payload is the only honest channel, and a `version` field there is the upgrade path if this ever needs measuring |

## Consequences

**Good.** A person who installed once is on the current version without ever
thinking about it, and finds out what changed from the page they already open.
Pricing corrections reach the people whose numbers depend on them.

**Bad / accepted.** The daily agent now makes one network call. ADR-004's
promise is about *collection* and is untouched — `sync`, `digest` and `report`
still reach nothing — but "this tool never touches the network" is no longer
true without a footnote, and the footnote is in `observe.py`'s docstring.

**Accepted.** Installs from a downloaded zip have no `.git` and cannot update
or be told they are behind. `doctor` reports the version it can see and stops
there rather than inventing a check it cannot perform.

**Accepted.** The new strings ship English-only, through the same `t18(key,
fallback)` path the rest of the freshness strip already uses.

## Revisit when

- Release tags exist, at which point the strip should show a curated line per
  release (`docs/whats-new.json`) rather than commit subjects.
- A zip-install population is shown to exist, which is what would justify the
  GitHub API fallback.

## See also

- [ADR-018 — launch surface and first run](ADR-018-Launch-Surface-And-First-Run.md)
- [ADR-002 — local-first](ADR-002-Local-First.md)
- [ADR-004 — zero-token collection](ADR-004-Zero-Token-Collection.md)
