-- 0004: durable, PII-free observability counters.
-- The gatekeeper refuses calls before a `calls` row exists, so refusals need their own aggregate
-- table to be visible on the dashboard. One row per clinic/day/reason keeps replayed abuse cheap
-- and stores no caller number, IP address, transcript or free text.

CREATE TABLE gatekeeper_block_stats (
  clinic_id   uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  day         date NOT NULL,
  reason      text NOT NULL,
  count       integer NOT NULL DEFAULT 0 CHECK (count >= 0),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (clinic_id, day, reason)
);

ALTER TABLE gatekeeper_block_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE gatekeeper_block_stats FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON gatekeeper_block_stats
  USING (clinic_id = app_current_clinic_id())
  WITH CHECK (clinic_id = app_current_clinic_id());

-- New tables do not inherit the grants executed by 0001.
GRANT SELECT, INSERT, UPDATE, DELETE ON gatekeeper_block_stats TO triavoz_app;
