-- 0006: pseudonymise old calls even when they never had transcript turns.
--
-- 0005 only nulled summary/caller_number when a batch deleted turns. A completed call with no
-- turns (e.g. silence/abuse) kept the caller number forever. Purge metadata in every batch.

CREATE OR REPLACE FUNCTION purge_expired_transcripts(p_batch_size integer DEFAULT 1000)
RETURNS TABLE (clinic_id uuid, deleted integer)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
  r record;
  n integer;
  pseudonymised integer;
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

    GET DIAGNOSTICS pseudonymised = ROW_COUNT;

    IF n > 0 OR pseudonymised > 0 THEN
      INSERT INTO public.audit_log
        (clinic_id, user_id, action, resource_type, resource_id, ip)
      VALUES
        (r.clinic_id, NULL, 'retention.transcripts', 'clinic', r.clinic_id::text, NULL);
    END IF;

    RETURN QUERY SELECT r.clinic_id, n;
  END LOOP;
END $$;

GRANT CREATE ON SCHEMA public TO triavoz_definer;
ALTER FUNCTION purge_expired_transcripts(integer) OWNER TO triavoz_definer;
REVOKE CREATE ON SCHEMA public FROM triavoz_definer;
REVOKE ALL ON FUNCTION purge_expired_transcripts(integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION purge_expired_transcripts(integer) TO triavoz_ops;
