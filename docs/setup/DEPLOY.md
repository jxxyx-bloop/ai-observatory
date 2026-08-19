# Deploying your own instance

Two independent things live here. **You almost certainly want only the first.**

| | What it is | Needed for |
|---|---|---|
| **The site** | Landing page + hosted demo dashboard, static files | Showing the project to other people |
| **The community API** | Accounts, submissions, cohort rollups | The leaderboard — **not built yet**, see [ADR-011](../adr/ADR-011-Community-Layer.md) |

The local product — collection, digest, dashboard, every detector — needs
**neither**. It runs offline forever with no account. Nothing below is required
to use this tool.

Reasoning for every choice here is in
[ADR-015](../adr/ADR-015-Hosting-And-Data-Residency.md).

---

## Nothing breaks if you do nothing

Worth stating first, because it is the usual worry.

`.github/workflows/site.yml` **only builds and verifies. It never deploys.** So
a commit made before any Cloudflare account exists cannot fail on the GitHub
side, and there are no secrets to add for it to start working.

Deployment is Cloudflare's own Git integration, configured in their dashboard.
Until you connect it, nothing deploys and nothing is red.

**One sharp edge, learned the hard way:** once you *do* connect the repository
in Cloudflare, their builder runs on every push — independently of GitHub
Actions. If its build command is empty it will clone the repo, build nothing,
and fail with `Could not detect a directory containing static files`. Set the
build command at the same time you connect the repo (step 1.2) and this does not
arise.

The same is true of the site build itself: `python3 site/build.py` uses only the
standard library and the repo's own engine. There is no npm, no lockfile, no
package registry that can go down mid-build.

---

## Part 1 — The site (about 20 minutes, ~$10/year)

### 1.1 A Cloudflare account

Sign up at [dash.cloudflare.com](https://dash.cloudflare.com). Free tier is
genuinely free for this — unlimited bandwidth, 500 builds/month, and
**commercial use is permitted**, which matters if you ever add a sponsors
button. (Vercel's Hobby plan forbids commercial use and caps bandwidth at
100 GB/month; on a launch-day traffic spike that cap is the wrong failure mode.)

Copy your **Account ID** from the right-hand sidebar of the dashboard home.
It is not a secret, but it identifies you.

### 1.2 Connect the repository

Dashboard → **Workers & Pages** → **Create** → **Connect to Git** → pick
`ai-observatory`.

**That is the whole setup. There is nothing to configure in the dashboard.**

The root [`wrangler.toml`](../../wrangler.toml) describes everything the deploy
needs:

```toml
[build]
command = "python3 site/build.py"     # runs as part of `wrangler deploy`

[assets]
directory = "./site/dist"             # exactly what that command writes
```

Cloudflare's default deploy command is already `npx wrangler deploy`, and
wrangler runs the `[build]` command before deploying — so the repo builds
itself. There is no `main` in that file: this is a static-assets-only project,
so no Worker code runs.

Python 3 is preinstalled in Cloudflare's build image, so there is no setup step
to add.

> **If you see `Could not detect a directory containing static files`:** you are
> on a commit from before `wrangler.toml` existed, or the project's deploy
> command was changed away from `npx wrangler deploy`. `site/dist/` is gitignored
> because it is derived, so something has to build it on the runner — and the
> `[build]` command above is that something.

### 1.3 There is no API token to create

Deliberately. Cloudflare pulls from Git and builds it itself, so **no Cloudflare
credential is ever stored in GitHub** — nothing to leak, rotate, or scope
wrongly. The GitHub Actions workflow (`.github/workflows/site.yml`) only
*verifies* that the site builds, which is what gives you a check on pull
requests, where Cloudflare's production build never runs.

### 1.4 Trigger it

Push to `main`. The site appears at `https://ai-observatory.workers.dev` (or the
`.pages.dev` host, depending on how the project was created — the dashboard
shows the real one).

### 1.5 A domain (optional)

Buy it at **Cloudflare Registrar** — wholesale price, no markup, and critically
**no renewal hike** (about $9.77–10.44/yr for a `.com`, versus roughly $15 at
renewal from registrars that discount year one). Over five years the renewal
column is the only one that matters.

Then project → **Custom domains** → **Set up a domain**. DNS is automatic if the
domain is already in your Cloudflare account.

---

## Part 2 — The community API (not yet)

**Do not deploy this.** Per [ADR-011](../adr/ADR-011-Community-Layer.md) the
community layer ships only when three things are true, not any one of them:

1. the shareable artefacts exist (Phase 5),
2. there are enough installs to meet a cohort floor of five,
3. **the consent flow has been reviewed by someone who is not the author.**

A leaderboard with fifty participants is embarrassing; one with fifty
participants and an unreviewed consent flow is a liability. The files below
exist so the design is reviewable *before* it is built.

When the time comes:

```bash
npm install -g wrangler && wrangler login

wrangler d1 create ai-observatory          # copy the database_id it prints
cp server/wrangler.toml.example server/wrangler.toml
# fill in account_id and database_id

wrangler d1 execute ai-observatory --file=server/schema.sql --remote

# secrets never go in the toml
wrangler secret put OBSERVATORY_HMAC_SECRET
```

`OBSERVATORY_HMAC_SECRET` derives every identifier. Generate it straight into
the command and never write it to a file:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Rotating it orphans every stored row — which is survivable, because each user's
next sync rebuilds theirs from the laptop that holds the source. Losing it is
not a data-loss event; it is a re-sync.

### Self-hosting instead

[`server/schema.sql`](../../server/schema.sql) is plain SQLite and applies
unchanged to a local file:

```bash
sqlite3 observatory.db < server/schema.sql
```

That portability is deliberate. For anyone under Indonesia's PDP Law, Vietnam's
PDPL, Thailand's PDPA or China's PIPL, a regional or in-house instance may be
the only acceptable option, and a project that treats that as an enterprise
upsell has misread its market.

---

## What this costs

| Stage | Site | API | Database | Domain | Total |
|---|---|---|---|---|---|
| Launch (0–1k sharers) | $0 | free tier | free tier | ~$10/yr | **~$1/mo** |
| 10k sharers | $0 | $5 | included | ~$10/yr | **~$6/mo** |
| 100k sharers | $0 | $5 | included | ~$10/yr | **~$6/mo** |

Prices were gathered 2026-08-19 from secondary sources —
**verify against Cloudflare's own pricing page before relying on them.**
Free tiers in this market are marketing, and marketing changes.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `Could not detect a directory containing static files` | The Cloudflare **build command** is empty, so nothing built `site/dist/`. Set it to `python3 site/build.py`. This is the one everyone hits. |
| Build succeeds, site serves nothing | `assets.directory` in the root `wrangler.toml` no longer matches what `site/build.py` writes. CI checks for this drift on every PR. |
| `python3: command not found` | Set the `PYTHON_VERSION` build variable (e.g. `3.12`) in the Cloudflare project's build settings. |
| Build fails on "no external requests" | Something in `site/index.html` loads a remote asset. That check is deliberate — the page advertises zero external requests, so it must not make any. |
| Site deploys but the demo 404s | `site/build.py` didn't produce `dist/demo/index.html`. Run it locally and look. |

## See also

- [ADR-015](../adr/ADR-015-Hosting-And-Data-Residency.md) — the hosting decision and what was rejected
- [ADR-011](../adr/ADR-011-Community-Layer.md) — why the community layer is gated
- [server/README.md](../../server/README.md) — the API design sketch
- [Community-Share-Protocol](../specs/Community-Share-Protocol.md) — exactly what a payload contains
