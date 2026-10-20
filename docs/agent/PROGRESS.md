# PROGRESS

> Single status board for all agents. Update after every session. Be honest: "implemented" means **run and passing**.

## Legend
`[x]` done and verified · `[~]` partially done / needs follow-up · `[ ]` not started

## Phase board
| Phase | Prompt | Status |
|---|---|---|
| F00 Bootstrap & context | P01 | [x] deps/lint/tests/build pass; Docker stack validated from a clean volume; lock files + Graphify integration added; GitHub Actions runs #1/#2 green (api/agent/web/secrets) |
| F01 Database + RLS + isolation tests | P02 | [x] migration 0001+0002, roles, forced RLS, routing functions, double-booking constraint, `refresh_tokens` + `clinic_settings`, isolation/role suite (mutation-tested), idempotent demo seed, CI green |
| F02 Backend core | P03 | [x] auth cookies/rotation/reuse/lockout, RBAC, requests+calls+agenda+agent-config+dashboard, SSE, team, blocked numbers, voice session, internal service-request + idempotent book/cancel/reschedule, CI green |
| F03 Voice agent | P04.1 | [x] live LiveKit Cloud pipeline validated (booking, exact-time confirmed reschedule, cancel, urgency, two-misunderstanding handoff); barge-in/latency/cost stored; SIP transfer code-complete but untested live |
| F04 Anti-abuse & cost | P05 | [ ] |
| F05 Frontend | P06 | [~] Next.js base, design tokens, i18n, route placeholders, StatusBadge · [ ] real pages, demo voice UI |
| F06 Observability, evals, (RAG) | P07 | [ ] |
| F07 Tests & E2E | P08 | [ ] |
| F08 Security audit | P09 | [ ] (run only AFTER F05–F07) |
| F09 Deploy, docs, demo | P10 | [ ] |

## Verified so far
- Alembic migrations 0001+0002 apply on PostgreSQL 16 as `triavoz_owner`, both on an empty DB and from 0001 with data. 40 API tests pass (unit + DB), incl. concurrent-booking race, cross-tenant read/write denial, no-context = no rows, pooled-connection leak test, role-privilege checks, new refresh-token/settings constraints, runtime-role cross-tenant `clinics`/`phone_numbers` reads, and definer column-grant checks. Re-verified on Python 3.11 (CI version) and 3.12.
- RLS mutation gate is reproducible: `scripts/verify_rls_mutations.py` applies a permissive policy, `NO FORCE RLS`, and `BYPASSRLS` on `triavoz_app`; each makes the targeted test fail for the expected reason, then the script restores and re-verifies green. All three detected and restored.
- Demo seed `apps/api/scripts/seed_demo.py` creates 3 fictional clinics (6 users, 8 services, 6 professionals, 60 availability rules, 3 phones, 3 published agent configs, 3 settings). Ran twice with identical counts; all users use DEV-only password `Demo!TriaVoz2026` (Argon2). Routing resolves the demo phone/slug.
- Query plans on a synthetic 50k-appointment/10k-time-off DB: the new `appointments_clinic_prof_starts_idx` returns 48 rows without scanning 2,352 (1.29ms → 0.66ms); `time_off_clinic_prof_span_idx` replaces a 10k-row seq scan (1.65ms → 0.10ms). Existing request-queue and call-list indexes matched their predicates. Availability rules are 250 rows/0.13ms; no index added without evidence.
- New tenant tables (`refresh_tokens`, `clinic_settings`) have ENABLE+FORCE RLS and tenant policies; 19/20 public tables are forced-RLS (the exception is `alembic_version`). `triavoz_ops` still cannot read them. The worker no longer receives DB credentials (explicit least-privilege compose env).
- Worker imports against `livekit-agents` 1.8.8 and its 5 unit tests pass on Python 3.11/3.12; ruff + mypy clean. The API created a **real LiveKit room and short-lived token** against the dev server (375-char token, `calls` row `in_progress`); no provider STT/LLM/TTS call yet.
- Next.js app type-checks and builds (17 routes); `npm ci` reports 0 vulnerabilities. **Not** exercised in a browser.
- `docker compose up --build` validated end-to-end from a removed `pgdata` volume: postgres/redis healthy, `migrate` exits 0, API `/health` returns `{"status":"ok"}`, web returns HTTP 200, agent registers with the LiveKit dev server. Host ports were remapped locally (55433/56379/58000/3300) because another local stack owns 5432/6379/8000; defaults remain unchanged for clean machines.
- Lock files committed: `apps/api/poetry.lock`, `apps/agent/poetry.lock`, `apps/web/package-lock.json`. Dockerfiles use Poetry 2.4.1 (lock-version 2.1) and ignore host `node_modules`/env files.
- Graphify graph refreshed after P04.1 (1151 nodes, 3068 edges, 86 communities); agent integration installed (`AGENTS.md`, `.kilo/plugins/graphify.js`). The SQL migrations are not indexed because `tree_sitter_sql` is not installed.
- GitHub Actions runs #1/#2 (P01 commits `cc8a67f`, `db1718f`), run #4 (P02 commit `7f09264`, run `39266266940`), run `39284190560` (P03 commit `8195df8`) and run `39351318965` (P04 commit `c535ce7`) passed: `api`, `agent`, `web` and `secrets`. `act`/`gh` are not installed locally; the remote runs are the CI evidence.
- P03: **53 API tests** pass (13 new HTTP tests) plus 5 worker tests; ruff/format/mypy clean. Covered: login generic errors, progressive lockout, cookie flags, refresh rotation + family reuse revocation (the first implementation rolled the revocation back on 401; fixed at the transaction boundary), `/me`, logout, RBAC, cross-tenant 404 for every resource family, request filters/cursor/events/mark-spam→blocklist, transcript audit, calls/dashboard, agenda create/move/cancel, config draft/publish/rollback/validation, team/self-deactivation, SSE auth + frame relay, voice metadata, idempotent book/service-request, OpenAPI (40 paths).
- Docker smoke: API image rebuilt with `livekit-api`; demo login (`admin@horizonte.demo`), `/me`, `/requests`, `/dashboard`, authenticated SSE `retry:` frame, and real LiveKit room/token creation all work. Internal idempotency and event publishing use the Redis service when present.
- P04: **real LiveKit Cloud voice calls** were run with four different outcomes. Booking call `7efc806d` (88s) offered 3 slots, confirmed name/service/professional/day/time, saved appointment `bd71c202` at 08:00 local, persisted redacted tool payloads, TTFA p50 1,629ms / p95 2,697ms, cost 3.36¢. Cancel call `59765a00` canceled `bd71c202`, TTFA p50 1,424 / p95 2,342ms, 2.73¢, 2 interruptions. Urgency call `f5627f18` spoke SAMU 192, set `handoff_requested=true`, and created a callback request (1.75¢).
- P04.1 exact-time reschedule: call `86faa52b` moved appointment `f3c8e49e` from 10:00 to **10:30 local**; the agent restated the new time, asked “Posso confirmar?”, received the confirmation, and only then called `reschedule_appointment` (99s, 4.00¢, TTFA p50 1,498 / p95 1,773ms). The earlier 09:30 run is retained only as history.
- P04.1 two-misunderstanding handoff: call `8084229b` created a callback and set `handoff_requested=true` (2.63¢); the trigger is now a pure `HandoffPolicy` with unit tests.
- Barge-in: adaptive interruption reported **1–2 interruptions per call** (detection p50 ~250–1,850ms). No pre-tuning baseline was captured; ADR 0007 records the tuned profile and this gap.
- Turn persistence is incremental; `function_tools_executed` turns include redacted arguments and output length only. Latency includes `time_to_first_audio = EOU + LLM TTFT + TTS TTFB`; full table in ADR 0007.
- Providers: Deepgram Nova-3 key verified; the supplied ElevenLabs key returns **401**, so the demo defaults to LiveKit Inference/Cartesia TTS; the LLM uses LiveKit Inference `openai/gpt-4.1-mini` (no Anthropic key supplied). Prices are in `.env.example` with sources; cost ≈1.75–3.55¢/call.
- Tests: **53 API + 10 worker** tests green; ruff/format/mypy clean. The API/worker suite covers slot-taken and wrong-owner cancel at the tool layer, plus redaction/latency/handoff-policy unit logic.
- NOT validated live: SIP transfer (no trunk/number), browser UI, Render `/voice/session` (returned 500), and post-call summary content. Two-consecutive-misunderstanding handoff is now verified live.

## Open decisions / proposals
- Host ports in `docker-compose.yml` are env-overridable (`POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`, `API_HOST_PORT`, `WEB_HOST_PORT`, `LIVEKIT_*_PORT`) with the original defaults. Needed to run alongside other local stacks without stopping them.
- ADR 0005: hashed rotating refresh tokens with `family_id` reuse detection, per-clinic limits, and transcript-retention design. Retention purge is deliberately TODO (P07/P09) because it needs a narrow SECURITY DEFINER function instead of broad `triavoz_ops` grants.
- ADR 0006: httpOnly access/refresh cookies, `SameSite=Lax` same-origin proxy, refresh-family revocation on reuse/logout/deactivation, and cookie-authenticated SSE. Access tokens remain valid for at most 15 minutes after deactivation (documented).
- `knowledge_documents` was **not** added: RAG remains optional and is not accepted (CONTEXT §2/§Scope).
- Post-call summaries are wired behind `CallSummaryGenerator` but the shipped implementation is a stub; the endpoint returns 503 until a reviewed provider/prompt/cost guard exists (P07).
- ADR 0007 records the voice provider choices, turn tuning, latency target, cost basis and handoff design. The supplied ElevenLabs key must be replaced (401); the demo falls back to LiveKit Inference/Cartesia.
- **Credentials supplied in chat are not committed**; `.env` is ignored. Rotate every exposed key before making the repository/service public.

## Blockers
- (none)

## Session log
- Scaffolding session: created repo base, prompts, docs.
- 2026-10-19 P01: installed Poetry/npm deps and lock files; fixed Dockerfile Poetry pin + added `.dockerignore`; parameterized host ports; validated full compose stack from a clean volume (`/health` 200, web 200, agent registered); verified API on Python 3.11 (33 tests) and agent (5 tests); rebuilt Graphify graph and installed the Kilo integration; pinned Poetry 2.4.1 in CI. Pushed `cc8a67f`; GitHub Actions run #1 green (api, agent, web, secrets).
- 2026-10-19 P02: re-verified isolation and mutation checks; added migration 0002 (`refresh_tokens`, `clinic_settings`, two evidence-backed indexes) without touching 0001; added idempotent 3-clinic demo seed; verified empty-DB and 0001→0002 upgrades; added runtime/definer role tests; removed DB credentials from the worker container. 40 API tests green; seed run twice unchanged. Pushed `7f09264`; GitHub Actions run #4 green (api, agent, web, secrets).
- 2026-10-19 P03: built `/api/v1` auth/requests/calls/agenda/agent-config/dashboard/SSE/team/blocked/voice; added rotating refresh cookies with family reuse detection, generic auth errors + lockout, RBAC, audit-on-transcript-read, request events, config versioning, Redis event bus, server-side LiveKit rooms, idempotency for voice tools, request IDs/error model. 53 API tests + 5 worker tests green; Docker smoke with real LiveKit room/token and demo login. ADR 0006 added. Pushed `8195df8`; GitHub Actions run `39284190560` green.
- 2026-10-20 P04: switched LLM to LiveKit Cloud Inference (`openai/gpt-4.1-mini`) and TTS fallback to Cartesia (ElevenLabs key 401); tuned semantic turn detection, endpointing, adaptive barge-in and preemptive generation; added incremental turn/tool persistence with redaction, web callback handoff + SIP adapter, latency/TTFA and cost capture. Ran real cloud calls (booking, cancel, reschedule, urgency). 53 API + 8 worker tests green; ADR 0007 added.
- 2026-10-20 P04.1: exact-time reschedule now requires and receives an explicit confirmation before the tool; verified 10:00 → 10:30 local (`86faa52b`); two-misunderstanding handoff verified live (`8084229b`) and extracted into a tested `HandoffPolicy`; 10 worker tests green.
