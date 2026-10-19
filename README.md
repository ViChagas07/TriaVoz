# TriaVoz

> **AI voice receptionist for clinics** — answers calls, understands the request, checks real availability, books / reschedules / cancels by voice, logs every conversation (transcript, duration, cost, latency per stage) and hands over to a human when needed. Strict **multi-tenant isolation** with PostgreSQL Row Level Security.

*Portfolio project. Uses fictional data only.*

## Why it is interesting
- **Own real-time voice pipeline** (LiveKit Agents): Deepgram STT → Claude with tool calling → ElevenLabs TTS, barge-in enabled, latency and cost measured per stage.
- **The database prevents double booking** (exclusion constraint) — the LLM can never confirm an occupied slot; proven by a concurrent-booking test.
- **Tenant isolation you can verify**: RLS enabled + forced on every tenant table, four DB roles, SECURITY DEFINER routing, and an isolation/guard test suite that blocks merges (mutation-tested).
- **Minimum-privilege agent**: it only sees free slots and the caller's own appointments; clinic identity never comes from the browser or the model.
- **Abuse & cost protection** (gatekeeper, rate limits, circuit breaker, kill switch) so a public demo can't drain credits.

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

API tests (need Postgres; see `apps/api/tests/conftest.py` for the DSN env vars):
```bash
cd apps/api && poetry install && poetry run pytest
```

Demo data (3 fictional clinics, including staff users with password `Demo!TriaVoz2026` — **DEV
ONLY**). The seed is idempotent and uses the owner DSN, never the runtime role:
```bash
export TRIAVOZ_DATABASE_URL_OWNER=postgresql+psycopg://triavoz_owner:owner-dev@localhost:5432/triavoz
make seed
```
On PowerShell, set the same variable with `$env:TRIAVOZ_DATABASE_URL_OWNER="..."` before `make seed`.
Do not reuse these passwords or the demo numbers outside local development.

## Status
See [`docs/agent/PROGRESS.md`](docs/agent/PROGRESS.md) — it states exactly what is verified and what is not.

## LGPD / privacy notes for production
Health data is sensitive personal data: lawful basis and consent, call-recording notice, data-processing agreements with voice/LLM providers, retention limits, access logging and encryption are required before any real use. This repository ships fictional data only.

## Next steps
Phone numbers (Twilio/SIP) and warm human transfer · per-clinic RAG (pgvector + RLS) · WhatsApp reminders · integrations with clinic management systems · billing.
