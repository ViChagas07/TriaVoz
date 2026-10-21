-- 0003: abuse/cost protection state.
-- Keeps the tenant contract: no new tenant table; only additive columns on forced-RLS tables.
-- `blocked_numbers` already supports clinic and global rows with expiry; `clinic_settings` holds
-- the per-clinic limits. This migration adds the fields the gatekeeper and post-call scoring need.

-- Hidden/unknown caller policy. Default is allow: the policy must never reject on unverifiable
-- data alone (the clinic can opt into rejecting hidden numbers).
ALTER TABLE clinic_settings
  ADD COLUMN hidden_caller_policy text NOT NULL DEFAULT 'allow'
    CHECK (hidden_caller_policy IN ('allow', 'reject')),
  -- NULL = 24/7. Shape: {"days":[1,2,3,4,5],"start":"08:00","end":"18:00"}
  -- Interpreted in the clinic's timezone. Invalid JSON fails open (voice stays available).
  ADD COLUMN business_hours jsonb;

-- Persisted flags behind the dashboard "review" badge. abuse_score already exists (0..100).
ALTER TABLE calls
  ADD COLUMN suspicion_flags jsonb NOT NULL DEFAULT '[]'::jsonb;

-- Repeat-caller detection and dedupe of identical requests are time-window queries.
CREATE INDEX calls_clinic_caller_started_idx
  ON calls (clinic_id, caller_number, started_at DESC);
CREATE INDEX service_requests_clinic_phone_created_idx
  ON service_requests (clinic_id, patient_phone, created_at DESC);

-- Runtime role already has table-level DML grants on both tables; new columns inherit them.
