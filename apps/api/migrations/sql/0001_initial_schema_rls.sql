-- Extensions are created by the migration owner so a fresh managed database (not only the
-- Docker init script) can bootstrap. All three are trusted extensions on PostgreSQL 13+.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS citext;

-- TriaVoz — initial schema with multi-tenant Row Level Security.
-- Runs as triavoz_owner. Every table that holds customer data has clinic_id NOT NULL,
-- ENABLE + FORCE ROW LEVEL SECURITY, and a tenant policy driven by app.current_clinic_id.

-- ───────────────────────── helpers ─────────────────────────
CREATE OR REPLACE FUNCTION app_current_clinic_id() RETURNS uuid
LANGUAGE sql STABLE
AS $$ SELECT nullif(current_setting('app.current_clinic_id', true), '')::uuid $$;

-- ───────────────────────── tenants & people ─────────────────────────
CREATE TABLE clinics (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  slug        text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{3,40}$'),
  timezone    text NOT NULL DEFAULT 'America/Bahia',
  is_active   boolean NOT NULL DEFAULT true,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE clinic_users (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id      uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  email          citext NOT NULL,
  password_hash  text NOT NULL,
  full_name      text NOT NULL,
  role           text NOT NULL CHECK (role IN ('admin', 'attendant')),
  is_active      boolean NOT NULL DEFAULT true,
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (clinic_id, email)
);

CREATE TABLE phone_numbers (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id   uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  e164        text NOT NULL UNIQUE CHECK (e164 ~ '^\+[1-9][0-9]{7,14}$'),
  label       text,
  is_active   boolean NOT NULL DEFAULT true
);

-- ───────────────────────── scheduling ─────────────────────────
CREATE TABLE services (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id     uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  name          text NOT NULL,
  duration_min  integer NOT NULL CHECK (duration_min > 0 AND duration_min <= 480),
  price_cents   integer NOT NULL DEFAULT 0 CHECK (price_cents >= 0),
  is_active     boolean NOT NULL DEFAULT true,
  UNIQUE (clinic_id, name)
);

CREATE TABLE professionals (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id   uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  name        text NOT NULL,
  specialty   text,
  is_active   boolean NOT NULL DEFAULT true
);

CREATE TABLE professional_services (
  clinic_id        uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  professional_id  uuid NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
  service_id       uuid NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  PRIMARY KEY (professional_id, service_id)
);

-- weekday uses ISO numbering: 1 = Monday ... 7 = Sunday
CREATE TABLE availability_rules (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id        uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  professional_id  uuid NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
  weekday          smallint NOT NULL CHECK (weekday BETWEEN 1 AND 7),
  start_time       time NOT NULL,
  end_time         time NOT NULL,
  CHECK (end_time > start_time)
);

CREATE TABLE time_off (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id        uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  professional_id  uuid NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
  starts_at        timestamptz NOT NULL,
  ends_at          timestamptz NOT NULL,
  reason           text,
  CHECK (ends_at > starts_at)
);

-- ───────────────────────── calls (conversation log) ─────────────────────────
CREATE TABLE calls (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id          uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  channel            text NOT NULL CHECK (channel IN ('web', 'phone')),
  room_name          text,
  caller_number      text,
  started_at         timestamptz NOT NULL DEFAULT now(),
  ended_at           timestamptz,
  status             text NOT NULL DEFAULT 'in_progress'
                     CHECK (status IN ('in_progress', 'completed', 'failed', 'rejected', 'transferred')),
  end_reason         text,
  duration_seconds   integer CHECK (duration_seconds >= 0),
  summary            text,
  abuse_score        integer NOT NULL DEFAULT 0 CHECK (abuse_score BETWEEN 0 AND 100),
  handoff_requested  boolean NOT NULL DEFAULT false,
  handoff_completed  boolean NOT NULL DEFAULT false,
  usage              jsonb NOT NULL DEFAULT '{}'::jsonb,   -- stt seconds, llm tokens, tts characters
  latency_ms         jsonb NOT NULL DEFAULT '{}'::jsonb,   -- per-stage percentiles
  cost_cents         numeric(12,4) NOT NULL DEFAULT 0 CHECK (cost_cents >= 0)
);

CREATE TABLE call_turns (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id       uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  call_id         uuid NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
  seq             integer NOT NULL CHECK (seq >= 0),
  speaker         text NOT NULL CHECK (speaker IN ('patient', 'agent', 'tool', 'system')),
  content         text NOT NULL DEFAULT '',
  tool_name       text,
  tool_payload    jsonb,
  started_at      timestamptz NOT NULL DEFAULT now(),
  ended_at        timestamptz,
  stt_confidence  real CHECK (stt_confidence BETWEEN 0 AND 1),
  UNIQUE (call_id, seq)
);

CREATE TABLE call_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id   uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  call_id     uuid NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
  event_type  text NOT NULL,
  payload     jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE appointments (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id        uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  call_id          uuid REFERENCES calls(id) ON DELETE SET NULL,
  professional_id  uuid NOT NULL REFERENCES professionals(id),
  service_id       uuid NOT NULL REFERENCES services(id),
  customer_name    text NOT NULL,
  customer_phone   text NOT NULL,
  starts_at        timestamptz NOT NULL,
  ends_at          timestamptz NOT NULL,
  status           text NOT NULL DEFAULT 'booked' CHECK (status IN ('booked', 'canceled')),
  created_via      text NOT NULL DEFAULT 'voice' CHECK (created_via IN ('voice', 'web', 'staff')),
  notes            text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  canceled_at      timestamptz,
  CHECK (ends_at > starts_at),
  -- The database, not the prompt, guarantees a slot is never double-booked.
  CONSTRAINT appointments_no_overlap EXCLUDE USING gist (
    clinic_id WITH =,
    professional_id WITH =,
    tstzrange(starts_at, ends_at, '[)') WITH &&
  ) WHERE (status = 'booked')
);

-- ───────────────────────── requests (non-schedulable work for the front desk) ─────────────────────────
CREATE TABLE service_requests (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id             uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  call_id               uuid REFERENCES calls(id) ON DELETE SET NULL,
  type                  text NOT NULL CHECK (type IN ('appointment', 'exam_pickup', 'message', 'callback', 'other')),
  title                 text NOT NULL,
  description           text,
  action_required       text,
  patient_name          text,
  patient_phone         text,
  patient_document_enc  bytea,                       -- application-level encryption, optional
  requested_date        date,
  due_date              date,
  status                text NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'done', 'cancelled', 'spam')),
  priority              text NOT NULL DEFAULT 'normal' CHECK (priority IN ('urgent', 'normal', 'low')),
  assigned_to           uuid REFERENCES clinic_users(id) ON DELETE SET NULL,
  suspicion_flags       jsonb NOT NULL DEFAULT '[]'::jsonb,
  completed_at          timestamptz,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE request_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id   uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  request_id  uuid NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
  user_id     uuid REFERENCES clinic_users(id) ON DELETE SET NULL,
  event_type  text NOT NULL,
  note        text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ───────────────────────── agent configuration, abuse, audit ─────────────────────────
CREATE TABLE agent_configs (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id     uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  version       integer NOT NULL CHECK (version > 0),
  status        text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
  config        jsonb NOT NULL,
  created_by    uuid REFERENCES clinic_users(id) ON DELETE SET NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  published_at  timestamptz,
  UNIQUE (clinic_id, version)
);
CREATE UNIQUE INDEX agent_configs_one_published ON agent_configs (clinic_id) WHERE status = 'published';

-- clinic_id NULL = global block (set by internal jobs only).
CREATE TABLE blocked_numbers (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id   uuid REFERENCES clinics(id) ON DELETE CASCADE,
  e164        text NOT NULL,
  reason      text,
  source      text NOT NULL CHECK (source IN ('manual', 'auto_spam_flag', 'rate_limit')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz
);
CREATE UNIQUE INDEX blocked_numbers_unique ON blocked_numbers (coalesce(clinic_id, '00000000-0000-0000-0000-000000000000'::uuid), e164);

CREATE TABLE audit_log (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  clinic_id      uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  user_id        uuid REFERENCES clinic_users(id) ON DELETE SET NULL,
  action         text NOT NULL,
  resource_type  text NOT NULL,
  resource_id    text,
  ip             inet,
  created_at     timestamptz NOT NULL DEFAULT now()
);

-- ───────────────────────── indexes ─────────────────────────
CREATE INDEX ON service_requests (clinic_id, status, created_at DESC);
CREATE INDEX ON calls (clinic_id, started_at DESC);
CREATE INDEX ON call_turns (clinic_id, call_id, seq);
CREATE INDEX ON call_events (clinic_id, call_id, created_at);
CREATE INDEX ON appointments (clinic_id, starts_at) WHERE status = 'booked';
CREATE INDEX ON appointments (clinic_id, customer_phone);
CREATE INDEX ON blocked_numbers (e164);
CREATE INDEX ON audit_log (clinic_id, created_at DESC);

-- ───────────────────────── Row Level Security ─────────────────────────
-- Standard tenant policy for every table that carries clinic_id (except the special cases below).
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'clinic_users', 'phone_numbers', 'services', 'professionals', 'professional_services',
    'availability_rules', 'time_off', 'calls', 'call_turns', 'call_events', 'appointments',
    'service_requests', 'request_events', 'agent_configs', 'audit_log'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format(
      'CREATE POLICY tenant_isolation ON %I USING (clinic_id = app_current_clinic_id()) WITH CHECK (clinic_id = app_current_clinic_id())',
      t
    );
  END LOOP;
END $$;

-- clinics: a tenant sees only its own row.
ALTER TABLE clinics ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinics FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON clinics
  USING (id = app_current_clinic_id()) WITH CHECK (id = app_current_clinic_id());

-- blocked_numbers: a tenant READS its own rows + global rows, but WRITES only its own.
ALTER TABLE blocked_numbers ENABLE ROW LEVEL SECURITY;
ALTER TABLE blocked_numbers FORCE ROW LEVEL SECURITY;
CREATE POLICY blocked_select ON blocked_numbers FOR SELECT
  USING (clinic_id IS NULL OR clinic_id = app_current_clinic_id());
CREATE POLICY blocked_insert ON blocked_numbers FOR INSERT
  WITH CHECK (clinic_id = app_current_clinic_id());
CREATE POLICY blocked_update ON blocked_numbers FOR UPDATE
  USING (clinic_id = app_current_clinic_id()) WITH CHECK (clinic_id = app_current_clinic_id());
CREATE POLICY blocked_delete ON blocked_numbers FOR DELETE
  USING (clinic_id = app_current_clinic_id());

-- ───────────────────────── routing functions (SECURITY DEFINER) ─────────────────────────
-- Needed BEFORE a tenant context exists (webhook/session start, login). They return ONLY a clinic id.
CREATE FUNCTION resolve_clinic_by_phone(p_e164 text) RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public
AS $$ SELECT clinic_id FROM public.phone_numbers WHERE e164 = p_e164 AND is_active LIMIT 1 $$;

CREATE FUNCTION resolve_clinic_by_slug(p_slug text) RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public
AS $$ SELECT id FROM public.clinics WHERE slug = p_slug AND is_active LIMIT 1 $$;

-- Changing a function's owner requires the new owner to hold CREATE on the schema; grant it only for this step.
GRANT CREATE ON SCHEMA public TO triavoz_definer;
ALTER FUNCTION resolve_clinic_by_phone(text) OWNER TO triavoz_definer;
ALTER FUNCTION resolve_clinic_by_slug(text) OWNER TO triavoz_definer;
REVOKE CREATE ON SCHEMA public FROM triavoz_definer;
REVOKE ALL ON FUNCTION resolve_clinic_by_phone(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION resolve_clinic_by_slug(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION resolve_clinic_by_phone(text) TO triavoz_app;
GRANT EXECUTE ON FUNCTION resolve_clinic_by_slug(text) TO triavoz_app;
GRANT SELECT (clinic_id, e164, is_active) ON phone_numbers TO triavoz_definer;
GRANT SELECT (id, slug, is_active) ON clinics TO triavoz_definer;

-- Internal ops role: may manage GLOBAL blocks only (clinic_id IS NULL). Nothing else.
GRANT SELECT, INSERT, UPDATE, DELETE ON blocked_numbers TO triavoz_ops;
CREATE POLICY ops_global_blocks ON blocked_numbers TO triavoz_ops
  USING (clinic_id IS NULL) WITH CHECK (clinic_id IS NULL);

-- ───────────────────────── runtime grants ─────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO triavoz_app;
-- audit_log is append-only for the runtime role.
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM triavoz_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO triavoz_app;
-- Runtime must not be able to change structure or disable RLS (it is not the owner anyway).
REVOKE TRUNCATE ON ALL TABLES IN SCHEMA public FROM triavoz_app;
