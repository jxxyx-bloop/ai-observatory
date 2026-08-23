# Visitor analytics on aiobservatory.dev

**Who this is for:** whoever runs the deployment at
[aiobservatory.dev](https://aiobservatory.dev). Nothing here touches the tool
people install. It is about one thing — counting visits to the marketing pages,
and knowing where those visits come from.

**Status:** the mechanism is in the repo and switched **off**. It turns on for
one deployment when that deployment sets `ANALYTICS_ID`, and for no other.

---

## 1. Read this first: the honest version of what you get

The question behind the request is usually "who are these people?" Analytics
answers a narrower question than that, and it is worth knowing which parts are
solid before wiring anything up.

| You want to know | You will get | How good is it |
|---|---|---|
| How many people came | Sessions, users, page views | **Solid.** Bot filtering is decent; ad blockers cost you roughly 10–30% of technical audiences, and this is a developer-tool site, so assume the high end |
| Where they are | Country, region, city | **Solid.** Derived from IP, then the IP is discarded |
| What language they read in | The locale page they landed on, plus browser language | **Solid, and unusually useful here** — the site ships thirteen locales, so the landing path *is* an audience signal |
| How they found you | Referrer, source/medium, search vs. direct vs. social | **Good**, with two known holes: Reddit and many apps strip referrers, and a lot of real traffic lands as "direct" |
| What they did | Scroll depth, outbound clicks to GitHub, time on page | **Good**, and the closest thing to intent you will get |
| Their **age, gender, interests** | The demographics report | **Weak, and the reason to set expectations now.** See below |

**On demographics specifically.** GA4 shows age, gender and interests only if
you turn on *Google Signals*, and even then it only knows them for visitors who
are signed in to a Google account *and* have ads personalisation switched on.
Google then applies a data threshold: below a certain volume the rows are hidden
entirely, to stop you identifying individuals. A young site typically sees a
demographics report that is mostly empty or marked "thresholded"
([Analytics Mania](https://www.analyticsmania.com/post/missing-demographic-data-in-google-analytics-4/),
[Google Signals explained](https://www.optimizesmart.com/google-signals-for-ga4-how-to-see-gender-interest-and-age-data-in-google-analytics-4/)).

So: **country + language + referrer + behaviour is the audience picture you will
actually get.** Age and gender are a bonus that may never arrive. That matters
because Google Signals is also the part that costs the most in consent and
optics — it is worth knowing you are paying for the least reliable field.

---

## 2. Why this needed engineering at all

Most sites paste a snippet into `<head>` and are done. This one could not, for
three reasons that are all deliberate:

1. **The README says "no analytics."** In thirteen languages, on the landing
   page, in the PRD, and in ADR-002. That claim is the product's whole pitch.
2. **CI enforces it.** `site/tools/check_no_remote.py` fails the build on any
   remote `src`. The CSP is `default-src 'none'` with per-script hashes.
3. **The measurement id cannot be committed** — not because it is secret, but
   because this repo gets forked (§4).

The resolution is a boundary rather than an exception:

> **The marketing pages may count visits. The product never phones home.**

"Marketing pages" means the landing page in its thirteen locales and
`/setup/`. It does not mean `/demo/`, and it does not mean the dashboard
`render.py` writes onto your laptop. That line is enforced in four places, so it
cannot be crossed by forgetting:

| Guard | What it refuses |
|---|---|
| `site/build.py` | The demo is rendered by the engine's own renderer, which is never passed a tag |
| `site/tools/check_no_remote.py` | `--allow` never applies to anything under `demo/` |
| `site/tools/check_headers.py` | A policy that names a remote host must not be the one that lands on `/demo/` |
| `.github/workflows/site.yml` | Builds the analytics shape too, and greps the demo for the tag |

And the privacy copy is switched by the same variable as the tag, in all
thirteen locales — so the page cannot end up promising one thing while doing
another.

---

## 3. The options, weighed

You asked for Google Analytics. Here is what it is being chosen over, because
the trade is real.

| | What it costs | What you learn | Verdict |
|---|---|---|---|
| **A. GA4 on marketing pages** *(implemented)* | Copy amendment in 13 locales · CSP widened · consent posture · the optics of "the privacy tool uses Google" | Everything in §1, including the weak demographics | **Recommended if you want one tool and Search Console linkage.** The copy change is the real price, not the code |
| **B. Cloudflare Web Analytics** | A beacon script — still a remote request, so the same copy amendment · CSP change · no consent banner needed | Views, referrers, country, device, Core Web Vitals. **No demographics** | **The purist's choice.** Cookieless, free, already in your stack. Costs everything A costs except consent and the Google optics |
| **C. Cloudflare zone analytics (no script)** | **Nothing.** No code, no CSP change, no copy change, no consent | Requests and countries in the dashboard; path/referrer/user-agent via the GraphQL Analytics API. Sampled, shorter retention on Free | **The only option that keeps "zero external requests" literally true.** Coarse, but free and invisible |
| **D. Plausible / Fathom / Umami** | Money or a server to run · same script and copy costs as B | Views, sources, countries, devices, goals. No demographics | Sensible if you would rather not hand the data to Google, but it buys little that B does not |
| **E. GA4 server-side (Measurement Protocol from a Worker)** | A Worker, an API secret to hold, real complexity | Poor. No client-side geo signal, no demographics at all | **Not worth it.** It looks like the privacy-preserving option and delivers the least data |

**The recommendation, in order:**

1. **Turn on C today.** It is a toggle in the Cloudflare dashboard, it changes
   no code, no copy and no promise, and it will tell you within a week whether
   anyone is arriving at all. If the answer is "twelve people," you have learned
   what you needed and A was not worth the copy change yet.
2. **Then A when you have a reason** — a launch, a Show HN, a post you want to
   attribute. That is the moment referrer detail and landing-page attribution
   start paying for themselves. The switch is one environment variable (§5).
3. **Do not run two beacons.** If you add A, the page carries one tag, not two.

The rest of this document is how to do A, since that is the part that needed
building.

---

## 4. The measurement id and this public repo

**A GA4 measurement id (`G-XXXXXXXXXX`) is not a credential.** It is in the
HTML source of every site that runs one. Anyone can view-source
aiobservatory.dev and read it. It cannot read your reports, and there is no
version of client-side analytics where it is hidden from visitors. Any advice
that promises otherwise is describing something else.

What keeping it out of git *does* buy is worth having anyway:

- **Forks don't inherit your tag.** This is the real reason. An id committed to
  a public repo follows every fork and every self-hoster. Their readers' visits
  would land in your property, and they would have no idea they were sending
  them. Reading it from the environment means the tag exists on exactly one
  deployment: the one whose owner set the variable.
- **Nobody can casually spam your property.** Copying an id out of a repo is
  easier than copying it out of a page; neither is hard, but the floor is
  higher.
- **The default stays honest.** A clone of this repo builds a site that makes
  zero external requests, and says so, because that is true for that build.

So the id lives in **Cloudflare's build environment variables**, and is marked
as a secret there. It is never in a commit, a PR, an issue or a log.

---

## 5. Step by step

### 5.1 Create the GA4 property (~10 minutes)

1. Go to [analytics.google.com](https://analytics.google.com) and sign in with
   the Google account that should **own** this data long term. Not a throwaway.
2. **Admin → Create → Property.**
   - Property name: `aiobservatory.dev`
   - Reporting time zone: pick the one you will read reports in, and never
     change it — GA does not retroactively re-bucket days.
   - Currency: USD (matches the site's own default).
3. Answer the business questions. Nothing here affects collection.
4. **Choose a platform → Web.**
   - Website URL: `https://aiobservatory.dev`
   - Stream name: `Landing page`
5. GA shows you a **measurement id** shaped `G-` followed by ten characters.
   **Copy it.** That is the only value you need from this screen.
6. Ignore the installation instructions it offers. The snippet is already in
   the repo; you are only supplying the id.

### 5.2 Decide two settings before any traffic arrives

Both are in **Admin → Data collection and modification → Data collection**:

- **Google Signals** — off by default. Turning it on is what unlocks age,
  gender and interests, at the cost described in §1 and the consent implications
  in §6. **Recommendation: leave it off for now.** You can turn it on later;
  the data starts from the day you do, so there is no penalty for waiting until
  you have enough traffic for the report to show anything.
- **Data retention** (**Admin → Data retention**) — the default is 2 months for
  event data. Change it to **14 months**, the maximum on the free tier. This is
  the setting people most regret leaving alone, because it cannot be applied
  retroactively.

Also worth doing once, in **Admin → Data streams → your stream**:

- **Enhanced measurement** is on by default and gives you scroll depth, outbound
  clicks and site search for free. Keep it. Outbound clicks are how you will see
  people leaving for GitHub, which on this site is the closest thing to a
  conversion.

### 5.3 Put the id into Cloudflare (~2 minutes)

The deployment builds from this repo on every push; the id is supplied as a
build variable, not a commit.

1. Cloudflare dashboard → **Workers & Pages** → the `ai-observatory` project.
2. **Settings → Variables and Secrets** (build-time variables — the ones the
   build command can see, not runtime bindings).
3. Add, for the **Production** environment:
   - Name: `ANALYTICS_ID`
   - Value: the `G-…` id from §5.1
   - Type: **Secret** if offered. It is not really a secret (§4), but there is
     no reason to have it printed in build logs.
4. Leave **Preview** without the variable. Preview deployments then build the
   no-tag shape, which means branch previews never pollute your numbers — a
   thing that otherwise takes months to notice.
5. Redeploy: push any commit, or use **Deployments → Retry deployment**.

That is the whole switch. No dashboard configuration in GA, no code change, no
second push.

### 5.4 Verify (~5 minutes, do not skip)

In order, because each step rules out a different failure:

1. **The tag is on the page.** `curl -s https://aiobservatory.dev | grep -c
   googletagmanager` → expect `1`. If it is `0`, the build did not see the
   variable.
2. **The tag is *not* on the demo.** `curl -s https://aiobservatory.dev/demo/ |
   grep -c googletagmanager` → expect `0`. This is the one that matters.
3. **The CSP allows it.** Open the site, DevTools → Console. A CSP violation
   mentioning `googletagmanager` means the headers and the page disagree —
   check that `_headers` deployed alongside the HTML.
4. **GA is receiving.** GA4 → **Reports → Realtime**, then load the site in a
   private window. A user should appear within about 30 seconds. If the tag is
   on the page and Realtime stays empty, the usual cause is your own ad
   blocker.
5. **A non-English locale reports separately.** Load
   `https://aiobservatory.dev/ja/` and confirm it shows up in Realtime as its
   own page path. This is what makes the locale-as-audience-signal work.
6. **Exclude yourself.** GA4 → **Admin → Data streams → your stream →
   Configure tag settings → Define internal traffic**, add your own IP, then
   **Admin → Data filters** and set the *Internal Traffic* filter to **Active**.
   Left alone, it stays on "Testing" and does nothing. On a low-traffic site
   your own visits are otherwise a meaningful fraction of the numbers.

### 5.5 Turning it off

Delete the `ANALYTICS_ID` variable and redeploy. The tag disappears, the CSP
narrows back, the privacy copy reverts in all thirteen locales, and the site is
byte-for-byte the zero-network build again. No code change, nothing to revert.

---

## 6. Consent, and what is already built in

The site ships **Consent Mode v2** with regional defaults, in
`site/build.py`:

- In the **EEA, the UK and Switzerland**, storage defaults to *denied*. GA4
  then sends cookieless pings: you get a count and a country, no `_ga` cookie,
  no returning-visitor identity.
- **Everywhere else**, analytics storage defaults to *granted*.

This is a defensible posture for a site with no ads, no remarketing and no
cross-site anything, and it means **no cookie banner is required today**.

It stops being sufficient the moment you turn on **Google Signals**, which is
advertising-adjacent processing. If you want demographics, you need a real
consent banner for EEA/UK visitors that calls `gtag('consent', 'update', …)` —
in thirteen languages, on a site whose whole aesthetic is the absence of that
sort of thing. Weigh that against §1's warning that the resulting report may
still be empty.

Two smaller notes:

- GA4 discards IP addresses after deriving geography; there is no
  `anonymize_ip` setting to turn on, and any guide telling you to set one is
  describing Universal Analytics.
- The site sends `Referrer-Policy: no-referrer`, which governs requests *out*
  of these pages. It does not hide *inbound* referrers from GA — those come from
  `document.referrer`, set by the site that linked to you.

---

## 7. What to actually look at, monthly

Resist the dashboard. Four numbers answer the question you asked:

1. **Reports → Acquisition → Traffic acquisition**, grouped by session
   source/medium. *Where did they come from?*
2. **Reports → User → Demographic details**, switched to **Country** — not age.
   *Where are they?* Cross-read it against the locale paths in **Pages and
   screens**: someone in Japan reading the English page is a different signal
   from someone reading `/ja/`.
3. **Pages and screens**, filtered to outbound clicks to GitHub. *Did anyone
   want the thing?*
4. **Engagement rate on `/setup/`.** People reach that page only on purpose. It
   is the narrowest, highest-intent number on the site.

If a month's answer is "nobody came," no analytics configuration fixes that, and
no further setup is worth your time until distribution changes.

---

## See also

- [DEPLOY.md](DEPLOY.md) — the deployment this configures
- [ADR-002](../adr/ADR-002-Local-First.md) — why the product itself never phones
  home, which none of this changes
- [DESIGN-SYSTEM.md §7](../design/DESIGN-SYSTEM.md) — the zero-network rule and
  the boundary this document draws in it
