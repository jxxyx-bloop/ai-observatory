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

`.github/workflows/deploy.yml` is written so that **a commit made before any
account exists cannot fail**:

- The **build** job always runs. If the site is broken, that fails — which is
  what you want.
- The **deploy** job is gated on `CLOUDFLARE_API_TOKEN` and
  `CLOUDFLARE_ACCOUNT_ID` both being present. Without them it is skipped, with a
  notice in the run summary saying so.

So the safe order is: **merge first, watch it build-and-skip, add secrets when
you're ready.** Nothing is red in between, and there is no window where the repo
is broken.

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

### 1.2 A Pages project

Dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.

- Repository: `ai-observatory`
- Project name: **`ai-observatory`** — this must match `--project-name` in
  `.github/workflows/deploy.yml`, or change both together
- Build command: leave **empty**
- Build output directory: leave **empty**

Leave the build settings empty on purpose: GitHub Actions builds the site and
pushes the finished directory, so Cloudflare never needs to run Python. One
build system, not two.

### 1.3 An API token

Dashboard → **My Profile** → **API Tokens** → **Create Token** → **Custom token**.

| Setting | Value |
|---|---|
| Permissions | `Account` · `Cloudflare Pages` · **Edit** |
| Account resources | Include · your account |
| TTL | Whatever you're comfortable with; you can rotate it later |

**Scope it to Pages only.** A token that can edit your whole account is stored
in GitHub, and the blast radius of a leak should be one static site.

Copy the token — it is shown **once**.

### 1.4 Two GitHub secrets

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

| Name | Value |
|---|---|
| `CLOUDFLARE_API_TOKEN` | the token from 1.3 |
| `CLOUDFLARE_ACCOUNT_ID` | the account id from 1.1 |

Both must exist before the deploy job will run. Add one and not the other and it
stays skipped — deliberately, so a half-finished setup never half-deploys.

### 1.5 Trigger it

Push to `main`, or run the workflow manually from the **Actions** tab. The site
appears at `https://ai-observatory.pages.dev`.

### 1.6 A domain (optional)

Buy it at **Cloudflare Registrar** — wholesale price, no markup, and critically
**no renewal hike** (about $9.77–10.44/yr for a `.com`, versus roughly $15 at
renewal from registrars that discount year one). Over five years the renewal
column is the only one that matters.

Then Pages project → **Custom domains** → **Set up a domain**. DNS is automatic
if the domain is already in your Cloudflare account.

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
| Deploy job says "skipped" | Secrets not set, or you pushed to a branch other than `main`. Working as designed. |
| `Project not found` | Pages project name ≠ `--project-name` in the workflow. |
| `Authentication error` | Token lacks `Cloudflare Pages: Edit`, or was scoped to the wrong account. |
| Build fails on "no external requests" | Something in `site/index.html` loads a remote asset. That check is deliberate — the page advertises zero external requests, so it must not make any. |
| Site deploys but the demo 404s | `site/build.py` didn't produce `dist/demo/index.html`. Run it locally and look. |

## See also

- [ADR-015](../adr/ADR-015-Hosting-And-Data-Residency.md) — the hosting decision and what was rejected
- [ADR-011](../adr/ADR-011-Community-Layer.md) — why the community layer is gated
- [server/README.md](../../server/README.md) — the API design sketch
- [Community-Share-Protocol](../specs/Community-Share-Protocol.md) — exactly what a payload contains
