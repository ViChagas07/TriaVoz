# RULES — rules every agent must follow in this repository

Read this file at the start of EVERY session, together with `docs/context/CONTEXT.md` and `docs/agent/PROGRESS.md`.

## Hard rules (never break)
1. **Tenant isolation is sacred.** Every table with customer data has `clinic_id NOT NULL` + `ENABLE` + `FORCE ROW LEVEL SECURITY` + a tenant policy. The runtime DB role is `triavoz_app` (NOBYPASSRLS, not the owner). Never use the owner/superuser at runtime.
2. **`clinic_id` is never taken from the browser or from the LLM.** It comes from a verified JWT (dashboard), from server-side routing (`resolve_clinic_by_phone/slug`) or from LiveKit room metadata written by the API (voice worker).
3. **The DB prevents double booking** (`appointments_no_overlap`). Never rely on the prompt or on application checks alone.
4. **The agent has minimum privilege.** It only sees free slots and the *caller's own* appointments. Ownership comes from the stored call record: a provider-verified phone for telephony, or an opaque httpOnly browser identity for the public web demo. A phone typed into a browser is contact data, never proof of ownership. It gives no clinical advice.
5. **Emergencies are never blocked** by anti-abuse rules (fail open to human/SAMU 192).
6. **No real patient data, ever.** Seeds and demos use synthetic data (fake CPFs from a generator).
7. **No secrets in git.** Credentials only via environment variables (`os.getenv` / pydantic-settings). `.env` is git-ignored; keep `.env.example` current.
8. **Never invent APIs.** For LiveKit, ElevenLabs, Deepgram, Anthropic, Twilio: read the CURRENT official docs before using a feature. If unverifiable, hide it behind an adapter and mark `TODO(verify-docs)`.
9. **Do not weaken or delete tests to make them pass.** The isolation suite blocks merge.
10. **No scope creep.** Stay inside `docs/context/CONTEXT.md §Scope`. Propose additions in `PROGRESS.md` under "Proposals".

## Engineering conventions
- Python 3.11, Poetry, FastAPI + Pydantic v2, SQLAlchemy 2 async (runtime) / psycopg (Alembic only), Clean Architecture (`domain → application → infrastructure/interfaces`), SOLID, small functions, type hints (mypy strict on `src`).
- Parameterised SQL only (no string-built SQL in `src`). Avoid N+1 (eager loading / single queries).
- Resilience: Token Bucket rate limiting, Circuit Breaker + Bulkhead around external providers, anti cache-stampede (Stale-While-Revalidate + TTL jitter + single-flight lock) on cached reads. **Never** confirm a booking from cached data — bookings always re-validate against the DB.
- Frontend: Next.js (App Router) + TypeScript strict, Tailwind v4 tokens from `globals.css`, Zustand for client state, `next-intl` for i18n (pt-BR default, en), A11y (POUR/WCAG AA), no secrets in client code, the browser only talks to its own origin (`/api/v1` proxied by Next rewrites).
- Commits: Conventional Commits, atomic, one concern each. One PR/phase.
- Add `# WHY:` comments for non-obvious decisions (Graphify indexes them) and an ADR in `docs/adr/` for architectural ones.

## Working loop (SDD + Context Engineering)
1. Read `RULES.md`, `PROGRESS.md`, `CONTEXT.md`, then the spec in `docs/specs/` for the area you touch.
2. If Graphify is installed, run `graphify .` (and `graphify <your-agent> install` once) and **query the graph before grepping files**.
3. Plan → tests first where it makes sense (TDD) → implement → run lint + type-check + tests.
4. Update `PROGRESS.md` (check boxes, decisions, blockers) and refresh the graph (`graphify .`).
5. Report: what changed, how to verify, decisions, risks, what is NOT done. Never claim something works if you did not run it. If Docker/network/keys were unavailable, say so explicitly.
