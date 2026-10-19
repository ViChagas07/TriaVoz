-- 0002: rotating refresh tokens + per-clinic operational limits.
-- New tenant tables follow the same contract as 0001: clinic_id NOT NULL, ENABLE + FORCE RLS,
-- a tenant policy driven by app.current_clinic_id, and DML grants only for triavoz_app.
-- Never add the owner to runtime code paths.

-- Per-clinic limits used by the gatekeeper and cost protection (P05).
CREATE TABLE clinic_settings (
  clinic_id                  uuid PRIMARY KEY REFERENCES clinics(id) ON DELETE CASCADE,
  daily_minute_budget        integer NOT NULL DEFAULT 120 CHECK (daily_minute_budget >= 0),
  daily_cost_budget_cents    integer NOT NULL DEFAULT 500 CHECK (daily_cost_budget_cents >= 0),
  max_concurrent_calls       smallint NOT NULL DEFAULT 3 CHECK (max_concurrent_calls BETWEEN 1 AND 100),
  max_call_seconds           integer NOT NULL DEFAULT 300 CHECK (max_call_seconds BETWEEN 30 AND 3600),
  kill_switch                boolean NOT NULL DEFAULT false,
  transcript_retention_days  integer NOT NULL DEFAULT 365 CHECK (transcript_retention_days BETWEEN 1 AND 3650),
  updated_at                 timestamptz NOT NULL DEFAULT now()
);

-- Existing clinics get safe defaults before RLS is enabled (migrations run without tenant context).
INSERT INTO clinic_settings (clinic_id) SELECT id FROM clinics;

ALTER TABLE clinic_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinic_settings FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON clinic_settings
  USING (clinic_id = app_current_clinic_id())
  WITH CHECK (clinic_id = app_current_clinic_id());

-- Needed by the composite FK below: it must prove user_id belongs to the same clinic.
ALTER TABLE clinic_users ADD CONSTRAINT clinic_users_clinic_id_id_key UNIQUE (clinic_id, id);

-- Rotating refresh tokens. Store only a SHA-256 hash; the raw token never reaches the DB.
-- family_id groups one login's rotation chain. Reuse of a revoked token => revoke the family.
CREATE TABLE refresh_tokens (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id       uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL,
  family_id       uuid NOT NULL,
  token_hash      bytea NOT NULL UNIQUE CHECK (octet_length(token_hash) = 32),
  expires_at      timestamptz NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  revoked_at      timestamptz,
  revoked_reason  text CHECK (revoked_reason IN ('rotated', 'reuse_detected', 'logout', 'admin')),
  replaced_by_id  uuid REFERENCES refresh_tokens(id) ON DELETE SET NULL,
  created_ip      inet,
  user_agent      text,
  CONSTRAINT refresh_tokens_user_fk
    FOREIGN KEY (clinic_id, user_id) REFERENCES clinic_users (clinic_id, id) ON DELETE CASCADE,
  CHECK ((revoked_at IS NULL) = (revoked_reason IS NULL))
);

ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON refresh_tokens
  USING (clinic_id = app_current_clinic_id())
  WITH CHECK (clinic_id = app_current_clinic_id());

-- Reuse detection revokes a whole family; the unique token_hash handles single-token lookup.
CREATE INDEX refresh_tokens_clinic_family_idx ON refresh_tokens (clinic_id, family_id);

-- EXPLAIN evidence (see docs/agent/PROGRESS.md, P02):
-- availability reads filter booked appointments by clinic + professional + day. The existing
-- (clinic_id, starts_at) index filtered 2,352 rows to return 48; this composite index matches the
-- actual predicate. The old index stays for clinic-wide agenda date ranges.
CREATE INDEX appointments_clinic_prof_starts_idx
  ON appointments (clinic_id, professional_id, starts_at) WHERE status = 'booked';

-- Time-off overlap checks scanned all 10,000 rows in the plan check; this index narrows by
-- professional and the time span before the overlap filter.
CREATE INDEX time_off_clinic_prof_span_idx
  ON time_off (clinic_id, professional_id, starts_at, ends_at);

-- Runtime DML only. Ops gets nothing here: retention/purge needs its own explicit design.
GRANT SELECT, INSERT, UPDATE, DELETE ON clinic_settings, refresh_tokens TO triavoz_app;
