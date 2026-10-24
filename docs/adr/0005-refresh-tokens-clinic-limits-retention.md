# ADR 0005 — Refresh tokens, per-clinic limits and transcript retention

**Status:** accepted (P02) · **Migration:** `0002_refresh_tokens_clinic_settings`

## Decision
- **Refresh tokens are stored as a SHA-256 hash**, never as the raw token. Each login starts a
  `family_id`; rotation revokes the used row (`revoked_reason='rotated'`) and inserts a replacement.
  If a token that is already revoked is presented again, the API revokes the whole family
  (`revoked_reason='reuse_detected'`) — this is the reuse-detection contract P03 implements.
- The token row carries `clinic_id` plus a composite FK `(clinic_id, user_id) → clinic_users
  (clinic_id, id)`, so a token can never point at a user from another tenant. RLS is ENABLE+FORCED
  and the runtime role gets only SELECT/INSERT/UPDATE/DELETE.
- **`clinic_settings`** holds the operational limits the gatekeeper and cost protection need:
  daily minute/cost budgets, concurrent-call cap, hard call duration, kill switch and transcript
  retention days. Existing clinics receive defaults in the migration; new clinics must insert a row
  when they are created (self-service onboarding is out of scope).
- **Index evidence:** `appointments (clinic_id, professional_id, starts_at) WHERE booked` and
  `time_off (clinic_id, professional_id, starts_at, ends_at)` were added after a synthetic 50k-row
  plan check. The same plan returned 48 rows after filtering 2,352 (appointments, 1.29 ms → 0.66 ms)
  and scanned 10,000 rows for time off (1.65 ms → 0.10 ms). Existing request-queue and call-list
  indexes already matched their predicates.

## Retention (implemented in P09: migrations 0005/0006)
Transcripts are the sensitive part of a call. The retention job (`purge_expired_transcripts`,
called by `scripts/purge_retention.py`) does:
1. read `clinic_settings.transcript_retention_days` per active clinic;
2. run as `triavoz_ops` and call `purge_expired_transcripts(p_batch_size)`, a `SECURITY DEFINER`
   function owned by `triavoz_definer`, which deletes `call_turns` in bounded batches, writes an
   `audit_log` summary, and pseudonymises `summary`/`caller_number` once no turns remain;
3. leave `calls` cost/latency aggregates intact, and never run on an emergency/active
   call.

The function is deliberately **not** added in P02: it changes the ops grant surface (ops should get
`EXECUTE` only, not table access) and must be tested with observability in P07. Today `triavoz_ops`
still has access only to global `blocked_numbers`.

## Rejected
- Storing raw refresh tokens (a DB leak becomes account takeover).
- A separate database per tenant (operational overhead at this scale).
- Granting `triavoz_ops` blanket SELECT/DELETE on call tables just to purge (wider blast radius).
