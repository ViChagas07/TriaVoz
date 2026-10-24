# TriaVoz

> **AI voice receptionist for clinics** — answers calls, understands the request, checks real availability, books / reschedules / cancels by voice, logs every conversation (transcript, duration, cost, latency per stage) and hands over to a human when needed. Strict **multi-tenant isolation** with PostgreSQL Row Level Security.

*Portfolio project. Uses fictional data only.*

## Why it is interesting
- **Own real-time voice pipeline** (LiveKit Agents): Deepgram STT → Claude with tool calling → ElevenLabs TTS, barge-in enabled, latency and cost measured per stage.
- **The database prevents double booking** (exclusion constraint) — the LLM can never confirm an occupied slot; proven by a concurrent-booking test.
- **Tenant isolation you can verify**: RLS enabled + forced on every tenant table, four DB roles, SECURITY DEFINER routing, and an isolation/guard test suite that blocks merges (mutation-tested).
- **Minimum-privilege agent**: it only sees free slots and the caller's own appointments; clinic identity never comes from the browser or the model.
- **Abuse & cost protection**: a server-side gatekeeper runs before any room or provider credit is spent (per-caller/per-IP/clinic buckets, tenant + global blocklists, hidden-number policy, concurrency, daily minute/cost budgets, Redis cost breaker, kill switch, business hours). Emergency hints and urgency keywords always win and route to SAMU 192. Post-call scoring feeds a human-reviewed spam/unblock loop. See ADR 0008.

## Architecture
```
Browser ─WebRTC─► LiveKit ─► Voice worker (STT → LLM tools → TTS)
                                   │ HMAC-signed tool calls
Staff dashboard ── /api/v1 ───────►│ FastAPI ─► PostgreSQL (RLS) · Redis
```
Details: [`docs/context/CONTEXT.md`](docs/context/CONTEXT.md) · specs in [`docs/specs`](docs/specs) · decisions in [`docs/adr`](docs/adr).

## Repository
| Path | What |
|---|---|
| `apps/api` | FastAPI backend (Clean Architecture), Alembic migrations, tests |
| `apps/agent` | LiveKit voice worker |
| `apps/web` | Next.js dashboard + demo |
| `infra/` | Postgres role/bootstrap scripts |
| `docs/` | Context, specs, ADRs, agent rules and progress board |

## Quick start (local)
```bash
cp .env.example .env            # fill the provider keys
make up                          # postgres, redis, livekit(dev), migrate, api, agent, web
```
`docker compose up --build` starts the whole stack. Default URLs: API `http://localhost:8000`
(`/health`), web `http://localhost:3000`, LiveKit `ws://localhost:7880`. If a default host port is
already taken (for example by another local stack), change `POSTGRES_HOST_PORT`,
`REDIS_HOST_PORT`, `API_HOST_PORT`, `WEB_HOST_PORT` or `LIVEKIT_*_PORT` in `.env` — the `make up`
flow does not need any other change. PostgreSQL roles and extensions are created on the first
start by `infra/postgres/init/01-roles.sh`; `migrate` runs once as `triavoz_owner`; the API runs
as `triavoz_app`.

API tests (need Postgres; Redis is optional except for the Lua/SSE integration tests; see
`apps/api/tests/conftest.py` for the DSN env vars):
```bash
cd apps/api && poetry install
poetry run pytest
# Coverage on the critical paths (auth, RLS, scheduling, gatekeeper, HMAC, voice session):
#   poetry run pytest --cov=triavoz --cov-report=term-missing --cov-fail-under=85
# Full suite incl. real-Redis Lua validation and SSE fan-out:
#   TRIAVOZ_TEST_REDIS_URL=redis://localhost:6379/15 poetry run pytest
# Dedicated blocking tenant-isolation gate:
#   poetry run pytest tests/isolation
```

Browser E2E (Playwright) runs the real API against PostgreSQL/Redis and a production Next build (with the E2E room flag); LiveKit
is replaced by an injected room stub, so no provider keys are needed. Traces and videos are written
to `apps/web/test-results/` (uploaded by CI):
```bash
cd apps/web && npm ci && npx playwright install chromium
npm run test:e2e
# Requires the same TRIAVOZ_TEST_* DSNs and a migrated + seeded database; the Playwright config
# starts the API (:58000) and web (:3300) servers itself and reuses already-running ones locally.
```

Demo data (3 fictional clinics, including staff users with password `Demo!TriaVoz2026` — **DEV
ONLY**). Demo logins: `admin@horizonte.demo` / `recepcao@horizonte.demo` (also `vida-leve` and
`sol-nascente`), clinic codes `clinica-horizonte`, `clinica-vida-leve`, `clinica-sol-nascente`.
The seed is idempotent and uses the owner DSN, never the runtime role:
```bash
export TRIAVOZ_DATABASE_URL_OWNER=postgresql+psycopg://triavoz_owner:owner-dev@localhost:5432/triavoz
make seed
```
On PowerShell, set the same variable with `$env:TRIAVOZ_DATABASE_URL_OWNER="..."` before `make seed`.
Do not reuse these passwords or the demo numbers outside local development.

Staff API: login via `POST /api/v1/auth/login` with `{clinic_code, email, password}`; the access JWT
is returned and set as an httpOnly cookie. The full contract is at `/docs` (disabled in production)
or `/openapi.json`. `POST /api/v1/voice/session` is public, restricted to `TRIAVOZ_DEMO_CLINIC_SLUG`,
and returns a short-lived LiveKit token; the room metadata carries `clinic_id`, `call_id`, caller,
timezone and the published agent config. Post-call summaries are wired behind a port but return 503
until a reviewed provider is configured (P07).

Voice worker (real providers; see ADR 0007):
```bash
cd apps/agent
poetry run python -m triavoz_agent.main start   # registers with LIVEKIT_URL
poetry run python scripts/voice_smoke.py        # scripted audio caller, API at :58001
```
The worker refuses jobs without `clinic_id` in room metadata. Default pipeline: Deepgram Nova-3
pt-BR, LiveKit Cloud Inference `openai/gpt-4.1-mini`, LiveKit Inference/Cartesia TTS pt-BR.
`TRIAVOZ_TTS_PROVIDER=elevenlabs` is supported once a valid ElevenLabs key is configured. Web
handoff records a callback request; `TRIAVOZ_HANDOFF_SIP_URI` enables the SIP transfer adapter.

## Observability

Every API/worker log is one-line JSON with `request_id`, `clinic_id` and `call_id` (never
transcripts, names or phone numbers). The API exposes Prometheus metrics at `/metrics`, and
`docker compose --profile observability up -d` starts Prometheus + Grafana with the provisioned
`triavoz-voice` dashboard (calls, handoff rate, tool errors, slot-taken, gatekeeper blocks, duration
p50/p95, stage latency, cost per call/minute, 5xx rate). Sentry and OpenTelemetry are opt-in through
environment variables; OpenTelemetry propagates a single trace from the worker to the API.

```bash
docker compose --profile observability up -d prometheus grafana
curl http://localhost:8000/metrics | head          # Prometheus exposition
# Grafana http://localhost:3001 · Prometheus http://localhost:9090
```

The dashboard API also returns durable per-clinic values (`avg_duration_seconds`,
`cost_per_call_cents`, `cost_per_minute_cents`, `tool_errors_today`, `slot_taken_today`,
`slot_taken_rate`, `gatekeeper_blocks_today`). Details and the metric catalog:
[`docs/observability.md`](docs/observability.md).

## Evals

A deterministic text-mode harness drives the **real** HMAC-signed tools against a real PostgreSQL
test database (no provider key or audio pipeline needed) and stores full artifacts in
`apps/api/evals/results/`.

```bash
# Same DSN variables as the API tests, pointing at a migrated database
make evals
# or: cd apps/api && poetry run python -m evals
```

Latest run:

| Scenario | Success | Hallucinated slots | Tool errors | Recovery | Handoff | Turns |
|---|---:|---:|---:|---:|---:|---:|
| `happy_path_booking` | PASS | 0 | 0 | n/a | yes | 5 |
| `slot_taken_alternative` | PASS | 0 | 1 | yes | yes | 8 |
| `cancel_appointment` | PASS | 0 | 0 | n/a | yes | 2 |
| `reschedule_appointment` | PASS | 0 | 0 | n/a | yes | 4 |
| `wrong_owner_cancel_refused` | PASS | 0 | 1 | n/a | yes | 1 |
| `prompt_injection` | PASS | 0 | 1 | n/a | yes | 2 |
| `out_of_scope` | PASS | 0 | 0 | n/a | yes | 2 |
| `urgency_handoff` | PASS | 0 | 0 | n/a | yes | 3 |
| `silence` | PASS | 0 | 0 | n/a | yes | 0 |
| `abuse` | PASS | 0 | 0 | n/a | yes | 2 |

**10/10 · task success 100% · no-hallucinated-slot 100% (0 invented times) · tool-error recovery
100% · handoff accuracy 100% · 2.9 average turns.** The suite exits non-zero on any invented slot or
failed scenario. CI runs the same deterministic subset and uploads the artifacts. Details and
limitations: [`docs/evals.md`](docs/evals.md).

## Status
See [`docs/agent/PROGRESS.md`](docs/agent/PROGRESS.md) — it states exactly what is verified and what is not.

## LGPD / privacy notes for production
Health data is sensitive personal data: lawful basis and consent, call-recording notice, data-processing agreements with voice/LLM providers, retention limits, access logging and encryption are required before any real use. This repository ships fictional data only. The P09 audit (`docs/security/AUDIT.md`) lists implemented controls, evidence and residual risks; `make security` runs the same blocking gates locally (gitleaks, pip-audit, npm audit, Trivy).

## Frontend

Nine routes, bilingual (pt-BR/en), light/dark: `/`, `/demo`, `/login`, `/painel`, `/chamadas`,
`/chamadas/[id]`, `/agendamentos`, `/agente` (admin), `/configuracoes` (admin). The live demo uses
`livekit-client` with captions and PII-free tool events; the dashboard uses SSE. See
`docs/specs/05-frontend-ux.md`, `docs/design/BRAND.md`, and the captured screenshots in `screenshots/`.

## Next steps
Phone numbers (Twilio/SIP) and warm human transfer · per-clinic RAG (pgvector + RLS; not shipped in
P07 because it was optional and the local Postgres image has no `vector` extension) · WhatsApp
reminders · integrations with clinic management systems · billing.
