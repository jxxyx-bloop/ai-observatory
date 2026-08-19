# Contributing

Three things make this project useful, and all three are things a maintainer
cannot do alone: **correct prices**, **broad tool coverage**, and **honest
findings**. Each has a deliberately cheap contribution path.

## The three easiest useful PRs

### 1. Fix a price (5 minutes)

Vendors reprice constantly and sometimes change the billing *shape*. A stale
rate card makes every number on the page confidently wrong, which is worse than
silent.

1. Edit the entry in [`observatory/pricing.json`](observatory/pricing.json).
2. Move `_verified_on` to today.
3. In the PR body, link the vendor's public pricing page.

That is the whole review. No tests to run, no code to touch.

### 2. Add a plan (10 minutes)

Subscription plans, quota units and reset windows live in
[`observatory/plans.json`](observatory/plans.json). Include the price, the quota
unit (`credits` | `prompts` | `messages` | `tokens`), and each reset window the
vendor enforces — several vendors enforce more than one at a time. Use
`"amount": null` when the vendor publishes no number; we fall back to a
self-calibrated p90 rather than inventing a limit.

### 3. Add your coding tool (an hour)

**This is the most valuable contribution in the repo.** Coverage is what makes
the tool relevant to a stranger, and if you use Lingma, Qwen Code, CodeBuddy,
Comate or Trae, you are the only person positioned to add it correctly — you have
the transcripts to test against and the maintainers do not.

If your tool writes JSONL with token counts on a record, it needs **no Python**:

1. Copy
   [`observatory/collectors/specs/example-openai-jsonl.json`](observatory/collectors/specs/example-openai-jsonl.json)
   and point it at your tool's transcripts.
2. Add a fixture at `observatory/tests/fixtures/<provider>.jsonl` — a handful of
   records in the vendor's **real** shape.
3. Add a test to `observatory/tests/test_specs.py` asserting an **exact turn
   count** and the parsed token fields.
4. Run `observatory/tests/run.sh`.

See [`collectors/specs/README.md`](observatory/collectors/specs/README.md) for
the spec vocabulary and
[ADR-014](docs/adr/ADR-014-Declarative-Collectors.md) for why it works this way.

A format the spec language cannot express (running totals, event-sourced logs)
earns a hand-written module — see `collectors/codex.py` and
`collectors/kimi_code.py` for the two that did.

**A collector without a fixture is not merged.** This is
[ADR-009](docs/adr/ADR-009-Collectors-Ship-With-A-Fixture.md): a parser asserted
against what the parser happens to expect will pass forever while reading
nothing.

## Adding a detector

Detectors live in [`observatory/insights.py`](observatory/insights.py). Every
finding must carry:

- **what was observed**, with the numbers behind it
- **an action** a person could actually take tomorrow
- **a confidence level**
- **an estimated monthly value**, where one can be defended

Three rules, from [ADR-007](docs/adr/ADR-007-Honest-Findings.md):

1. **No finding without evidence.** If you cannot show the numbers, it is not a
   finding.
2. **Report healthy as healthy.** A detector that only ever fires negatively is
   a detector that trains people to ignore it.
3. **Never invent a problem to look useful.** The materiality gate demotes
   anything under $15/month rather than deleting it, so the top of the list
   always means something.

If a finding's action is "use a cheaper model", think again. The useful version
is almost always "route *this specific class of work* down a tier" — telling a
developer to stop using good models is advice they will correctly ignore.

## House style

- **Python 3 standard library only** in `observatory/`. No dependencies, ever.
  This is what makes the tool run untouched for years, and it is not negotiable.
- **The engine never writes to a provider's files.** Read-only, always.
- **The parse boundary is the privacy boundary.** No prompt text, completion
  text, file contents, tool argument values, shell commands or absolute paths
  may enter an event — enforced where the data is parsed, not by later
  redaction ([ADR-006](docs/adr/ADR-006-Metadata-Only.md)).
- **`render.py` may not compute a metric the digest does not define.** Otherwise
  the text output and the HTML will disagree.
- **Comments explain why, not what.** The codebase is deliberately dense with
  reasoning; match that.

## Changes to the share payload

Anything touching [`observatory/share.py`](observatory/share.py) gets extra
scrutiny, and rightly:

- The payload is an **allow-list**. A new upstream metric must not be able to
  leak by default; someone has to add it here on purpose, in a visible diff.
- **No free text, ever.** No repo, folder, branch, workspace or session name,
  at any setting.
- Metrics are **bucketed on the device**. The server must never receive a raw
  value.
- Update `FORBIDDEN_KEYS` and the tests when the shape changes.
- Bucket edges are **fixed and versioned**. Never edit one in place — that
  silently corrupts every comparison against previously-submitted data. Add
  `buckets_version: 2` alongside.

## Tests

```bash
observatory/tests/run.sh
```

Engine, collector specs, provider fixtures, and a headless execution of the
dashboard. No framework — a contributor on a fresh machine with nothing
installed should be able to run these.

## What will be declined

- **Anything that ranks named individuals.** No manager view, no employee
  leaderboard. This is the fastest way to make developers uninstall a tool that
  reads their transcripts.
- **Default-on telemetry**, "share to unlock", or any dark-pattern consent.
- **Ranking by total spend.** Displayed, never ranked — see
  [ADR-011](docs/adr/ADR-011-Community-Layer.md) for why the leaderboard is
  built on efficiency instead.
- **A runtime dependency** in the engine.
- **A network call** anywhere in the local path.

## Reporting a wrong finding

If a detector fires on something healthy, that is a bug worth an issue —
credibility is the entire product. Include the finding id, the evidence block
it printed, and what you think the right answer is.

## Code of conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
