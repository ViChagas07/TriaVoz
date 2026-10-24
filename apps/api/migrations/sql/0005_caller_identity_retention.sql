-- 0005: verified caller ownership for the public demo + LGPD retention/expurgo.
--
-- Why this exists: `/api/v1/voice/session` is public, so a browser-supplied phone number is NOT
-- proof that the caller owns that number. Phone-channel caller IDs are provider-verified; web
-- calls get an opaque, httpOnly browser identity cookie instead. Appointment ownership checks use
-- the identity hash for web calls and the verified phone for phone calls.

ALTER TABLE calls
  ADD COLUMN caller_verified boolean NOT NULL DEFAULT false,
  ADD COLUMN caller_identity_hash bytea
    CHECK (caller_identity_hash IS NULL OR octet_length(caller_identity_hash) = 32);

-- Existing telephony calls received their number from the provider, so keep them self-service.
UPDATE calls SET caller_verified = true
WHERE channel = 'phone' AND caller_number IS NOT NULL;

CREATE INDEX calls_clinic_identity_idx
  ON calls (clinic_id, caller_identity_hash)
  WHERE caller_identity_hash IS NOT NULL;

-- Retention: delete transcript turns for completed calls older than the clinic's policy, then
-- pseudonymise the remaining call metadata (summary/phone) once no turns remain. The function is
-- owned by triavoz_definer (BYPASSRLS) and exposes only bounded, clinic-scoped work to triavoz_ops.
CREATE OR REPLACE FUNCTION purge_expired_transcripts(p_batch_size integer DEFAULT 1000)
RETURNS TABLE (clinic_id uuid, deleted integer)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
  r record;
  n integer;
BEGIN
  IF p_batch_size IS NULL OR p_batch_size < 1 OR p_batch_size > 10000 THEN
    RAISE EXCEPTION 'p_batch_size must be between 1 and 10000'
      USING ERRCODE = '22023';
  END IF;

  FOR r IN
    SELECT c.id AS clinic_id, s.transcript_retention_days AS days
    FROM public.clinics c
    JOIN public.clinic_settings s ON s.clinic_id = c.id
    WHERE c.is_active
    ORDER BY c.id
  LOOP
    WITH doomed AS (
      SELECT ct.id
      FROM public.call_turns ct
      JOIN public.calls c ON c.id = ct.call_id
      WHERE ct.clinic_id = r.clinic_id
        AND c.clinic_id = r.clinic_id
        AND c.status <> 'in_progress'
        AND COALESCE(c.ended_at, c.started_at)
            < now() - make_interval(days => r.days)
      ORDER BY ct.id
      LIMIT p_batch_size
    )
    DELETE FROM public.call_turns ct
    USING doomed d
    WHERE ct.id = d.id;

    GET DIAGNOSTICS n = ROW_COUNT;

    IF n > 0 THEN
      -- Only once the transcript is gone, remove the free-text summary and caller identifier.
      UPDATE public.calls c
      SET summary = NULL,
          caller_number = NULL
      WHERE c.clinic_id = r.clinic_id
        AND c.status <> 'in_progress'
        AND COALESCE(c.ended_at, c.started_at)
            < now() - make_interval(days => r.days)
        AND (c.summary IS NOT NULL OR c.caller_number IS NOT NULL)
        AND NOT EXISTS (
          SELECT 1 FROM public.call_turns ct WHERE ct.call_id = c.id
        );

      INSERT INTO public.audit_log
        (clinic_id, user_id, action, resource_type, resource_id, ip)
      VALUES
        (r.clinic_id, NULL, 'retention.transcripts', 'clinic', r.clinic_id::text, NULL);
    END IF;

    RETURN QUERY SELECT r.clinic_id, n;
  END LOOP;
END $$;

-- Expired/revoked refresh tokens are credentials, not analytics: keep the table small and bound
-- the blast radius of an old database dump.
CREATE OR REPLACE FUNCTION purge_expired_refresh_tokens(
  p_revoked_before timestamptz DEFAULT now() - interval '30 days',
  p_batch_size integer DEFAULT 5000
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
  n integer;
BEGIN
  IF p_batch_size IS NULL OR p_batch_size < 1 OR p_batch_size > 50000 THEN
    RAISE EXCEPTION 'p_batch_size must be between 1 and 50000'
      USING ERRCODE = '22023';
  END IF;

  WITH doomed AS (
    SELECT ctid
    FROM public.refresh_tokens
    WHERE expires_at < now() - interval '1 day'
       OR (revoked_at IS NOT NULL AND revoked_at < p_revoked_before)
    LIMIT p_batch_size
  )
  DELETE FROM public.refresh_tokens rt
  USING doomed d
  WHERE rt.ctid = d.ctid;

  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$;

-- Minimal privileges for the definer owner. The functions above are the only entry points; the
-- role is NOLOGIN and cannot be used directly.
GRANT SELECT (id, is_active) ON clinics TO triavoz_definer;
GRANT SELECT (clinic_id, transcript_retention_days) ON clinic_settings TO triavoz_definer;
GRANT SELECT, DELETE ON call_turns TO triavoz_definer;
GRANT SELECT, UPDATE ON calls TO triavoz_definer;
GRANT SELECT, DELETE ON refresh_tokens TO triavoz_definer;
GRANT INSERT ON audit_log TO triavoz_definer;
GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO triavoz_definer;

-- PostgreSQL requires the new owner to hold CREATE on the schema while ownership changes.
GRANT CREATE ON SCHEMA public TO triavoz_definer;
ALTER FUNCTION purge_expired_transcripts(integer) OWNER TO triavoz_definer;
ALTER FUNCTION purge_expired_refresh_tokens(timestamptz, integer) OWNER TO triavoz_definer;
REVOKE CREATE ON SCHEMA public FROM triavoz_definer;
REVOKE ALL ON FUNCTION purge_expired_transcripts(integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION purge_expired_refresh_tokens(timestamptz, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION purge_expired_transcripts(integer) TO triavoz_ops;
GRANT EXECUTE ON FUNCTION purge_expired_refresh_tokens(timestamptz, integer) TO triavoz_ops;
