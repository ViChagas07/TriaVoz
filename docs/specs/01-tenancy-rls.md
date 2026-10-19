# Spec 01 — Tenancy & RLS

## Requirements
- R1 Every table holding customer data has `clinic_id uuid NOT NULL` (including child tables) and ENABLE + FORCE RLS with a `tenant_isolation` policy (`USING` and `WITH CHECK`).
- R2 Roles: `triavoz_owner` (migrations only), `triavoz_app` (runtime; NOSUPERUSER, NOBYPASSRLS, owns nothing), `triavoz_ops` (only global `blocked_numbers`), `triavoz_definer` (NOLOGIN, BYPASSRLS, owns the SECURITY DEFINER routing functions, minimal column grants).
- R3 Context: `SELECT set_config('app.current_clinic_id', :id, true)` once per transaction, via `tenant_session(clinic_id)` — there is no session helper without a tenant. Pooled connections never leak context (transaction-local).
- R4 Routing before context: `resolve_clinic_by_phone(e164)` and `resolve_clinic_by_slug(slug)` return only a clinic id.
- R5 `audit_log` is append-only for the runtime role (no UPDATE/DELETE/TRUNCATE).
- R6 `blocked_numbers`: tenants read own + global rows, write only own; `triavoz_ops` manages only global rows.
- R7 Other tenants' resources yield `404`, never `403`.
- R8 Redis keys are prefixed `clinic:{id}:`; object storage prefix `clinics/{id}/`.

## Acceptance tests (already implemented in `apps/api/tests/isolation`)
cross-tenant SELECT = 0 rows in every table · no context = no rows · cross-tenant INSERT/UPDATE denied · audit append-only · runtime role unprivileged and owns nothing · routing functions work without context while tables stay closed · pooled connection does not leak · 50 concurrent mixed-tenant requests never mix · **guard test** (every table with `clinic_id` has ENABLE+FORCE+policy).
When adding a table: add `clinic_id`, add it to the RLS `DO` block in a NEW migration, extend the seed in `tests/conftest.py`, and run the suite.
