# Spec — authentication and accounts

## The constraint that shapes everything

The strongest line in every competing README is *"no account, no API keys."*
TokenTracker leads with it. It is the reason people try these tools.

So auth must be **invisible until it is needed**, and it is needed for exactly
one thing: the community layer. Everything else — collection, the digest, the
dashboard, every finding, the demo — works with no account, no network, and no
sign-in prompt, forever. A tool that asks who you are before it has shown you
anything has already lost the comparison.

| Surface | Auth | Network |
|---|---|---|
| `observe.py sync / digest / report / insights / demo / share` | none | none |
| The rendered dashboard | none | none — zero external requests |
| Submitting to a cohort | account | one POST |
| Reading cohort comparisons | account | one GET |
| A public profile page or README embed | account | — |

## Provider choice

**Google and GitHub, OIDC, both.** No passwords, ever.

- **GitHub** is the developer-native option and the one tokscale chose. It also
  gives a natural public handle for profile pages and embeds.
- **Google** is the broader option, and in Southeast Asia it is often the more
  universal one — plenty of developers in the target market do not have an
  active GitHub identity but everyone has a Google account.

Both, from the start, because forcing GitHub excludes part of the intended
audience and forcing Google feels wrong to the rest.

### The China problem, stated rather than ignored

Google OAuth is not reachable from mainland China without a VPN, and GitHub is
intermittent. A community layer gated solely on Google auth excludes a large
part of the user base this project is explicitly built for.

Three responses, in order of preference:

1. **The local product needs no account at all.** This is the real answer. A
   developer in Chengdu gets the entire coaching product, offline, forever.
2. **A device-code flow** (`observe.py login --device`) that works over a slow
   or intermittent connection and does not require a browser callback to
   `localhost`.
3. **A self-hosted or regionally-hosted community server.** Documented as a
   first-class path, not an enterprise tier. WeChat or Alipay OIDC could be
   added by whoever needs it; the account layer is deliberately provider-agnostic
   so that is a config change.

## What an account stores

| Field | Notes |
|---|---|
| `uid` | `HMAC("uid", sub)[:24]` — the row id. The provider's raw subject is never stored. |
| `handle` | User-chosen, 3–24 chars, unique. The only public identifier. |
| `display_name` | Optional. Defaults to the handle, never to the OIDC name claim. |
| `email_sealed` | Encrypted under a **server-derived** key, so the backend can answer "who opted out" while no browser session can read the roster. |
| `email_hmac` | Confirms a guessed address; cannot enumerate. |
| `share`, `share_changed`, `consent_version` | The consent record. |
| `created_at`, `last_seen`, `submit_count` | |

**No numeric aggregate lives here.** A person's fact rows sum to exactly such a
total, which would recover the `uid` ↔ `auid` link the two-salt design exists to
prevent. See [Community-Share-Protocol](Community-Share-Protocol.md#identity).

The OIDC `name` and `picture` claims are **discarded at the callback**. We ask
for `openid email` and nothing else. A real name is not needed to compare cache
hit rates, and the safest place for data is not to have it.

## Tokens

```
observatory login          # opens a browser, or prints a device code
                           # -> ~/.config/ai-observatory/credentials.json, chmod 600
observatory logout         # deletes the file and revokes server-side
```

- Submission tokens are **scoped to submit and read-own** — never to read
  another account, never to administer.
- Long-lived and revocable, refreshed on use. A daily cron must not need a
  browser.
- `AI_OBSERVATORY_TOKEN` in the environment overrides the file, for CI.
- Stored outside the repo, so a token can never be committed. `.gitignore`
  covers the repo-local path too, belt and braces.

## Account lifecycle

| Action | Effect |
|---|---|
| Sign in | Account row created. **No facts pooled on the first submission** — see the protocol spec. |
| Change handle | Allowed; old handle released after 30 days so links do not silently re-point at someone else. |
| Opt out | Fact rows deleted, not merely stopped. |
| `DELETE /v1/me` | Account row and every fact row removed. No soft delete, no grace period, no "we keep aggregates". |
| Provider revoked upstream | Token invalid at next refresh; local data untouched and the dashboard keeps working. |

## What auth is never used for

- **Never a gate on the local product.** No "sign in to see your dashboard."
- **Never to identify a person in a cohort.** Facts are keyed by `auid`, which
  is unlinkable to the account row.
- **Never sold, shared, or used for a mailing list** without a separate,
  specific opt-in.
- **Never a team-management surface.** An org that wants aggregate figures for
  its own developers can run its own server; this project will not ship a
  manager view that ranks named employees, because that is the fastest way to
  make developers uninstall it.

## Implementation note

Standard OIDC authorization-code flow with PKCE. No custom crypto. The reference
server sketch is in [`server/`](../../server/) — a design sketch, not a running
service, and it must not accept a byte of real data until the consent flow has
been reviewed by someone who is not the author
([R1](../strategy/05-RISKS.md)).

## See also

- [Community-Share-Protocol](Community-Share-Protocol.md)
- [ADR-011 — the community layer](../adr/ADR-011-Community-Layer.md)
- [ADR-013 — form factor](../adr/ADR-013-Form-Factor.md)
