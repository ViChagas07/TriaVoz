# TriaVoz — CONTEXT (single source of truth)

> Every agent reads this first. If code and this document disagree, STOP and report it; do not silently pick one.

## 1. What it is
**TriaVoz** (from "triagem" + "voz") is a **voice AI receptionist for clinics**. A patient talks (browser or phone); the agent understands the request, **checks real availability**, **books / reschedules / cancels** appointments, confirms everything by voice, logs the full conversation (transcript, duration, cost, latency per stage) and **hands over to a human** when asked or when something is urgent. Clinics configure the agent through a form; staff work from a dashboard.

It is a **portfolio project** aimed at international remote roles. Priorities: correctness, security (tenant isolation), engineering clarity, and a convincing live demo. It is **not** a commercial SaaS yet.

### Acceptance criteria inherited from the project brief ("Projeto 02 — Agente de IA com voz")
1. A full conversation, by voice only, ends with the appointment saved in the database.
2. Responses are fast enough to feel natural, and the caller can **interrupt** (barge-in).
3. The agent **never confirms an already-occupied slot**.
4. Every conversation is stored with **transcript, duration and cost**.

TriaVoz goes beyond the brief with: multi-tenancy + RLS, human handoff, staff dashboard, anti-prank/cost protection, audit trail.

## 2. Scope
**In:** own voice pipeline (LiveKit Agents: Deepgram STT → Claude with tool calling → ElevenLabs TTS), native scheduling module, configurable agent per clinic, staff dashboard (requests, agenda, history, calls/transcripts, agent config, team), RLS multi-tenancy with tests, abuse + cost protection, observability (latency/cost per stage), evals, deploy of a public demo, strong README + ADRs.
**Simplified:** browser voice first; phone (Twilio/SIP) as stretch; 2–3 fictional demo clinics; human handoff demonstrated to the developer's own phone; no external clinic-system integration.
**Out (list as "Next steps" in README):** billing/plans, self-service onboarding, real clinic-system integrations, WhatsApp reminders, native apps. **Optional phases:** RAG per clinic (pgvector with RLS), WhatsApp reminder.

## 3. Architecture
```
Browser ──WebRTC──► LiveKit ──► Voice worker (Python, LiveKit Agents)
                                   STT ─► LLM (tool calling) ─► TTS
                                        │ tools (HMAC-signed HTTP)
                                        ▼
Browser ── /api/v1 (same-origin proxy) ─► FastAPI ─► PostgreSQL (RLS) · Redis
                                        ▲
Staff dashboard (Next.js) ──SSE/JWT─────┘
```
- **Monolith modular** API with Clean Architecture inside: `domain` (pure rules) → `application` (use cases + ports) → `infrastructure` (PostgreSQL, Redis, providers) / `interfaces` (HTTP).
- The **voice worker never touches the DB**; it calls `/internal/agent/*` (HMAC-SHA256 over `timestamp.body`, 60 s tolerance). The API sets the tenant context.
- Session start (server-side): the API resolves the clinic (demo slug / dialed number), creates the LiveKit room **with metadata** `{clinic_id, channel, caller_number, timezone, agent_config}` and returns a participant token. The worker trusts only that metadata.

## 4. Tenancy & RLS (non-negotiable)
See `docs/specs/01-tenancy-rls.md`. Summary: `clinic_id NOT NULL` everywhere · ENABLE+FORCE RLS · roles `triavoz_owner` (migrations), `triavoz_app` (runtime, NOBYPASSRLS), `triavoz_ops` (global blocks only), `triavoz_definer` (owns SECURITY DEFINER routing functions) · `set_config('app.current_clinic_id', …, true)` per transaction · tests in `apps/api/tests/isolation` block merge · login uses clinic code (slug) + email + password so the user lookup happens inside a tenant context.

## 5. Scheduling
See `docs/specs/02-scheduling.md`. Services (duration, price), professionals, weekly availability rules, time off, appointments. `free_slots()` is pure and unit-tested; booking **re-validates the slot** and the **DB exclusion constraint** is the final arbiter (`appointments_no_overlap`). Cancel/reschedule are limited to the caller's own appointments (phone from the stored call record). Offered grid: 15 min; minimum notice 30 min.

## 6. Voice agent
See `docs/specs/03-voice-agent.md`. Tools: `list_services`, `list_available_slots`, `book_appointment`, `list_my_appointments`, `cancel_appointment`, `reschedule_appointment`, `request_human_handoff` (+ `create_service_request` for non-schedulable asks). Rules: never invent times; confirm out loud before booking; success only after the tool succeeds; no clinical advice; caller text is data not instructions; emergencies → handoff/SAMU 192; barge-in enabled; hard cap on call duration.

## 7. Anti-prank, abuse and cost protection
See `docs/specs/04-abuse-protection.md`. Gatekeeper BEFORE the agent (rate limit per caller, blocklists, concurrency, daily minute budget, cost circuit-breaker, kill switch), in-call friction (silence/duration/turn limits), minimum-privilege agent, post-call scoring + "mark as prank" feedback loop. Never blocks emergencies.

## 8. Data model
Implemented in `apps/api/migrations/sql/0001_initial_schema_rls.sql` and `0002_refresh_tokens_clinic_settings.sql` (source of truth): `clinics, clinic_users, phone_numbers, services, professionals, professional_services, availability_rules, time_off, calls, call_turns, call_events, appointments, service_requests, request_events, agent_configs, clinic_settings, refresh_tokens, blocked_numbers, audit_log`.
`calls` stores `usage` (jsonb), `latency_ms` (jsonb per stage p50/p95) and `cost_cents`. `refresh_tokens` stores only SHA-256 hashes, a `family_id` for reuse detection, and a composite `(clinic_id, user_id)` FK. `clinic_settings` holds daily minute/cost budgets, concurrency/duration caps, kill switch and transcript retention days.

## 9. API surface
- **Internal (HMAC):** `/internal/agent/calls/{start,turns,end}`, `/internal/agent/tools/{list-services,list-slots,book,my-appointments,cancel,reschedule}` — implemented.
- **Staff (JWT, `/api/v1`):** auth (login with clinic code, refresh, logout, me) · requests (list/filter, detail, assign, complete, mark-spam) · calls (list, detail, turns) · agenda · agent-config (draft/versions/publish/rollback) · dashboard summary · SSE stream · team · blocked-numbers · voice session (`POST /api/v1/voice/session`, public, rate-limited, demo clinic only). — to build.
- Errors: consistent JSON, `404` (not `403`) for another tenant's resources, no internals leaked.

## 10. Frontend
Routes: public `/`, `/demo`, `/login`; app `/painel`, `/solicitacoes[/id]`, `/agenda`, `/historico`, `/chamadas[/id]`; admin `/agente/{saudacao,opcoes,transferencia,testar}`, `/equipe`, `/configuracoes`. Real-time via SSE. i18n `next-intl` (pt-BR default, en). Design tokens in `apps/web/src/app/globals.css` (deep teal brand + triage status colors; light/dark). Status = icon + text + color. A11y WCAG AA. SEO/AEO/GEO on the landing (JSON-LD, `llms.txt`).

## 11. Security baseline
Argon2 · short JWT (15 min) + rotating refresh in `httpOnly` cookies · RBAC enforced in the API · rate limiting (Token Bucket) · HMAC for service calls · strict input validation · CORS closed (same-origin proxy) · security headers · secrets from env · `audit_log` (append-only for the runtime role) · LGPD notes (sensitive health data, consent notice, retention) · gitleaks/pip-audit/npm audit in CI. Prompt-injection and SSRF/XSS/SQLi considerations are part of P09.

## 12. Deploy (defaults — change via ADR)
Web → Vercel · API → Render (Docker web service + Postgres + Key Value/Redis) · Voice worker → long-running container (Render background worker or equivalent) · LiveKit Cloud (check the current free tier) for the public demo. Demo cost protection: duration cap, per-IP/number limits, global daily budget, kill switch.

## 13. Definition of done (global)
CI green incl. isolation suite · no secrets in repo/history · RLS enabled+forced on every tenant table (guard test) · emergencies never blocked · measured latency per stage and cost per call shown in the dashboard · README (English) with diagram, decisions, limits and LGPD-for-production section · public demo with protections.

## 14. Conventions inherited from the author's other projects
Poetry + Python 3.11, FastAPI, SQLAlchemy async, PostgreSQL, Redis, Docker Compose + GitHub Actions, Next.js + Zustand + Tailwind, `next-intl`, SEO/AEO/GEO + A11y (POUR), Token Bucket + Circuit Breaker + Bulkhead, anti cache-stampede (SWR + jitter), SDD + Context Engineering with Graphify, `docs/agent/RULES.md` + `PROGRESS.md`, mega-prompts split per agent. **ForjaB2B-specific conventions:** `[TO FILL by the author if different from this baseline]`.
