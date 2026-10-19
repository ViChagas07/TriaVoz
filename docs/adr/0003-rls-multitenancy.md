# ADR 0003 — Multi-tenancy with PostgreSQL RLS

**Status:** accepted · **Decision:** shared schema, `clinic_id` on every tenant table, ENABLE+FORCE RLS, transaction-local `app.current_clinic_id`, four DB roles (owner/app/ops/definer), SECURITY DEFINER routing functions that return only a clinic id, guard + isolation test suite as a merge gate.
**Why:** isolation must hold even if application code forgets a filter. **Trade-offs:** every query runs in a tenant transaction; some pre-context lookups need definer functions; test seeding must set context (FORCE RLS applies to the owner too).
**Rejected:** schema-per-tenant (migration overhead for a portfolio-scale system), application-only filtering (single point of failure).
