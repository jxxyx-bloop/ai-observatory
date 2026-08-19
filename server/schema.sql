-- Community layer schema. SQLite dialect, which is what Cloudflare D1 speaks —
-- so this file applies unchanged to a self-hosted `sqlite3 observatory.db`
-- with no service at all. That portability is the point (ADR-015).
--
--   Cloudflare:  wrangler d1 execute ai-observatory --file=server/schema.sql --remote
--   Self-host:   sqlite3 observatory.db < server/schema.sql
--
-- Three tables. No joins in the request path; every access is a keyed read or
-- an upsert. See docs/specs/Community-Share-Protocol.md for the field-level
-- reasoning and docs/adr/ADR-011-Community-Layer.md for why any of it exists.

-- One row per person. Holds the consent record and nothing summable.
--
-- NOTHING SUMMABLE MAY BE ADDED HERE. A person's `facts` rows sum to exactly
-- such a total, so storing one would let anyone able to read both tables
-- recover the uid <-> auid link that the two-salt design exists to prevent —
-- needing only one figure said out loud to attach a name to a history.
-- This is load-bearing, not tidiness. See ADR-010.
CREATE TABLE IF NOT EXISTS accounts (
  uid              TEXT PRIMARY KEY,   -- HMAC("uid", oidc_sub)[:24]
  handle           TEXT UNIQUE,        -- user-chosen, 3-24 chars, the only public id
  display_name     TEXT,
  email_sealed     TEXT,               -- encrypted under a SERVER-derived key
  email_hmac       TEXT,               -- confirms a guess; cannot enumerate
  share            INTEGER NOT NULL DEFAULT 0,   -- 0 = opted out. Default OFF.
  share_changed    TEXT,
  consent_version  INTEGER NOT NULL DEFAULT 1,
  pooling_from     TEXT,               -- first date eligible; set to tomorrow on first sync
  created_at       TEXT NOT NULL,
  last_seen        TEXT,
  submit_count     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS accounts_email_hmac ON accounts(email_hmac);

-- One row per person per day. Pruned at 35 days — the client's local store is
-- the system of record and never expires, so the server needs these only long
-- enough to build the nightly rollup and keep re-submission idempotent.
--
-- `auid` is HMAC("analytics", oidc_sub)[:24] and is NOT derivable from `uid`
-- without the server secret. The two must never appear on the same row.
--
-- Every metric is a BUCKET INDEX computed on the user's device. The server
-- cannot invert one, so a breach of this table leaks what the published cohort
-- files already say.
CREATE TABLE IF NOT EXISTS facts (
  id            TEXT PRIMARY KEY,      -- '<auid>.<YYYY-MM-DD>', deterministic
  auid          TEXT NOT NULL,
  date          TEXT NOT NULL,
  payload_v     INTEGER NOT NULL,
  buckets_v     INTEGER NOT NULL,
  metrics       TEXT NOT NULL,         -- JSON: {metric: bucket_index}
  mix           TEXT NOT NULL,         -- JSON: vendor/tier shares as percentages
  findings      TEXT NOT NULL,         -- JSON: array of finding ids that fired
  cohorts       TEXT,                  -- JSON: self-declared labels, <=4
  plan          TEXT,
  currency      TEXT,
  submitted_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS facts_date ON facts(date);
CREATE INDEX IF NOT EXISTS facts_auid ON facts(auid);

-- One row per slice per day, built nightly from `facts`, then published as
-- static JSON to the CDN. This is the only table a reader ever sees the output
-- of, and it is never written when `n` is below the suppression floor — so a
-- thin slice does not exist to be leaked by a rendering bug.
--
-- Slices: 'all' | 'vendor:<name>' | 'plan:<id>' | 'cohort:<self-declared>'.
-- Deliberately NO org slice and NO IP-derived location slice: an enumerable
-- roster defeats any numeric floor. Dropped rather than tuned — ADR-011.
CREATE TABLE IF NOT EXISTS cohorts (
  id         TEXT PRIMARY KEY,         -- '<slice>.<YYYY-MM-DD>'
  slice      TEXT NOT NULL,
  date       TEXT NOT NULL,
  n          INTEGER NOT NULL,         -- distinct auid; row absent below the floor
  hist       TEXT NOT NULL,            -- JSON: {metric: int[buckets]} — these compose
  cat        TEXT NOT NULL,            -- JSON: categorical shares
  computed   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS cohorts_slice_date ON cohorts(slice, date);
