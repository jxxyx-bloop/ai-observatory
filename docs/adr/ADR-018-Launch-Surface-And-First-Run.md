# ADR-018 — Launch surface and first run: one command, a generated app, and a page that dates itself

**Status:** accepted · **Date:** 2026-08-23

## Context

[ADR-013](ADR-013-Form-Factor.md) settled the *shape* — a CLI and a
self-contained HTML file, with a native shell deferred until retention data
asked for it. It left open the part that decides whether anyone opens the thing
twice: how a person who is not an engineer gets from "I saw the demo" to "I look
at this every morning."

The gaps were small individually and fatal together:

- `report` ended by printing a path and asking a human to go find a file.
- There was no launcher. The only way back to your dashboard was remembering a
  command and a directory.
- The published demo showed sample data without ever saying so.
- A dashboard opened from `file://` had no way to tell you it was a week old.
- Setup was three separate pastes, each one a chance to stop.

A local server was considered first and rejected — see below.

## Decision

### 1. A file, still. The page owns staleness; anything with a network owns updates

A server's failure mode is `ERR_CONNECTION_REFUSED`: a blank page, with no
recoverable thread for a beginner, and the surface that would explain the fix is
the surface that is down. A file's failure mode is *stale numbers* — a page that
is still there, and can therefore explain itself.

That asymmetry decides the split:

| Question | Answered by | Because |
|---|---|---|
| Am I out of date? | the page | It computes that offline from its own render stamp |
| Does a newer version exist? | the launcher, or `setup` | A file can never be told this |

Neither pretends to do the other's job. This is [ADR-002](ADR-002-Local-First.md)
restated, not revisited: *"a local server with a web UI — a process to run and
keep patched, for no gain over a static file."*

### 2. `observe.py setup` — the whole install as one command

Anyone reaching the setup page has already seen the demo; that is what the demo
is for. Setup therefore means "put this on my machine, with my numbers", not
"look at sample data again". Five phases, narrated as they happen:

1. Check Python and find which agents have run here
2. Fast-forward the checkout, if it can reach GitHub
3. Read the transcripts already on disk
4. Build the dashboard
5. Create the app, pin it to the Dock, and open the result

Narration is not decoration. A command that prints nothing for eight seconds
while it reads three hundred transcript files is indistinguishable from one that
has hung, and the person watching cannot tell which.

There is nothing to install, and phase 1 says so out loud: the most common
reason people put off a Python tool is expecting a dependency mess that never
arrives. Because the engine is standard-library-only, the honest answer to
"update outdated packages" is that the only thing which can be out of date is the
code itself — so phase 2 updates that, by fast-forward or not at all. Never a
merge, never a rebase; a dirty tree or no network keeps the version you have.

`setup` never deletes. A store seeded by an earlier `demo` is reported, not
rewritten. If there is genuinely nothing to read it seeds sample data rather than
finishing on an empty page, because ending on nothing defeats the one promise the
command makes.

### 3. The launcher is generated, not downloaded

`install` writes `~/Applications/AI Observatory.app`: a ~3 KB shell script in a
bundle. No Electron, no GUI stack, no rewrite — which is what ADR-013 priced
desktop packaging at.

The load-bearing detail is *generated rather than downloaded*.
`com.apple.quarantine` is set by the downloading agent, so a bundle written by a
local process launches with no Gatekeeper prompt, **no code signing, no
notarisation and no Apple Developer account**. The entire cost ADR-013 named is
avoided by not shipping a binary.

The runner pins the interpreter at install time. A launched `.app` gets a minimal
PATH, so `command -v python3` resolves to whatever system Python is on it — a
different interpreter from the one that ran the install, which is how an app and
its own CLI start disagreeing.

`--dock` pins it; without the flag the Dock is never rearranged behind anyone's
back. `--remove` undoes everything. Nothing written leaves `$HOME`, and nothing
touches `data/`.

> **Amended 2026-08-24.** Pinning is now the default on both `install` and
> `setup`, with `--no-dock` to opt out. The original reasoning protected a Dock
> from a command the user had not yet decided to trust — but by the time anyone
> runs `install` they have decided, and the launcher's whole promise is an icon
> to click tomorrow. `install --remove` now unpins as well, so the default stays
> reversible in both directions. The daily agent also gained `RunAtLoad`:
> launchd replays a missed calendar interval on wake, but not on a boot that
> happened after the scheduled time.

### 4. Failures arrive as a page, never a traceback

`doctor` returns structured checks rendered three ways: the CLI, the generated
app's error page (`--html`), and the troubleshooting section of the site. One
definition, three renderings — the same rule ADR-013 applies to metrics.

Somebody who double-clicked an icon has no terminal open and no reason to
acquire one. A traceback is not a message they can act on.

### 5. The dashboard dates itself

A freshness strip above the title: silent when fresh, dated after a day, blunt
after a week, and always present on the sample-data build. Computed in the
browser from the render stamp — no network, no server.

The refresh command it offers abbreviates `$HOME` to `~`. The rendered page is
meant to be e-mailable and attachable to a PR (ADR-013), and an absolute path
would name its author.

### 6. Ambient presence is a notification, not a menu bar

A menu-bar item needs a persistent process — reintroducing exactly what ADR-002
rejected — plus a GUI stack. The daily launchd job posts a Notification Centre
message instead. Deliberately not clickable: `osascript display notification`
cannot carry a click action, and pretending otherwise would train people to click
something that does nothing.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| `observe.py serve` on a fixed localhost port | Contradicts ADR-002 and ADR-013. Port collisions turn a working bookmark into a dead one, and the failure mode is unrecoverable by the person who hit it |
| A downloaded, signed `.app` | $99/yr, a notarisation pipeline and a per-OS CI matrix, for a bundle we can generate locally with none of it |
| Electron or a native rewrite | ADR-013 already priced this. Packaging is not what wins this category — ccusage is a terminal command with ~18k stars |
| `curl … \| sh` install | For a tool whose positioning is trust and zero-network, piping a remote script into a shell contradicts the pitch in the most visible place |
| Menu-bar app now | Its ADR-013 gate — retention data showing people do not return *despite* useful findings — has not fired |

## Consequences

**Good.** One paste from nothing to a dashboard with your own numbers in it. The
answer to "where do I find this tomorrow" is a Dock icon. Staleness is visible
without a server. A native shell, if the retention gate ever fires, is still a
wrapper around this, not a rewrite.

**Bad / accepted.** `/setup/` is English only — it is a dense procedural page of
commands, flags and paths, and `site/tools/readmes.py` already establishes that a
stale translation of a command is worse than an English one. The Dock flag and
the generated bundle are macOS-only; Windows and Linux get a script beside the
project, which ADR-013 already accepts as asymmetric.

**Accepted.** `setup` performs a `git pull`, which is the first network call in
the collect → analyse → render path's neighbourhood. It is in *setup*, never in
collection, it is best-effort, and it is skippable — ADR-004's zero-token,
zero-network collection promise is untouched.

## Revisit when

Notification click-through or Dock-pin retention shows people are returning
through the icon but not through the daily nudge — that would be the evidence
ADR-013 asks for before building real ambient presence.

## See also

- [ADR-002 — local-first](ADR-002-Local-First.md)
- [ADR-013 — form factor](ADR-013-Form-Factor.md)
- [ADR-004 — zero-token collection](ADR-004-Zero-Token-Collection.md)
- [04-GROWTH-FLYWHEEL](../strategy/04-GROWTH-FLYWHEEL.md)
