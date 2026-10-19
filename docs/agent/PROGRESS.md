# PROGRESS

> Single status board for all agents. Update after every session. Be honest: "implemented" means **run and passing**.

## Legend
`[x]` done and verified · `[~]` partially done / needs follow-up · `[ ]` not started

## Phase board
| Phase | Prompt | Status |
|---|---|---|
| F00 Bootstrap & context | P01 | [x] deps/lint/tests/build pass; Docker stack validated from a clean volume; lock files + Graphify integration added; GitHub Actions runs #1/#2 green (api/agent/web/secrets) |
| F01 Database + RLS + isolation tests | P02 | [x] migration, roles, RLS, routing functions, double-booking constraint, isolation suite (mutation-tested) · [ ] demo seed script |
| F02 Backend core | P03 | [~] settings, tenant session, security primitives, scheduling domain/use cases/repo, internal agent API (HMAC) · [ ] auth endpoints, requests, calls read API, agent-config, dashboard, SSE, team, blocked numbers, voice session endpoint |
| F03 Voice agent | P04 | [~] LiveKit worker skeleton, tools, prompt, metrics, cost estimate · [ ] real end-to-end call, handoff, barge-in tuning, latency measurements |
| F04 Anti-abuse & cost | P05 | [ ] |
| F05 Frontend | P06 | [~] Next.js base, design tokens, i18n, route placeholders, StatusBadge · [ ] real pages, demo voice UI |
| F06 Observability, evals, (RAG) | P07 | [ ] |
| F07 Tests & E2E | P08 | [ ] |
| F08 Security audit | P09 | [ ] (run only AFTER F05–F07) |
| F09 Deploy, docs, demo | P10 | [ ] |

## Verified so far
- Alembic migration applies on PostgreSQL 16 as `triavoz_owner`; 33 API tests pass (unit + DB), incl. concurrent-booking race, cross-tenant read/write denial, no-context = no rows, pooled-connection leak test, role-privilege checks. Mutation checks (permissive policy, NO FORCE RLS, BYPASSRLS on runtime role) make the suite FAIL as intended. Re-verified on Python 3.11 (CI version) and 3.12.
- Worker imports against `livekit-agents` 1.8.8 and its 5 unit tests pass on Python 3.11/3.12; ruff + mypy clean. **Not** run against a live LiveKit room (no provider keys).
- Next.js app type-checks and builds (17 routes); `npm ci` reports 0 vulnerabilities. **Not** exercised in a browser.
- `docker compose up --build` validated end-to-end from a removed `pgdata` volume: postgres/redis healthy, `migrate` exits 0, API `/health` returns `{"status":"ok"}`, web returns HTTP 200, agent registers with the LiveKit dev server. Host ports were remapped locally (55433/56379/58000/3300) because another local stack owns 5432/6379/8000; defaults remain unchanged for clean machines.
- Lock files committed: `apps/api/poetry.lock`, `apps/agent/poetry.lock`, `apps/web/package-lock.json`. Dockerfiles use Poetry 2.4.1 (lock-version 2.1) and ignore host `node_modules`/env files.
- Graphify graph built (560 nodes, 1156 edges, 48 communities) and agent integration installed (`AGENTS.md`, `.kilo/plugins/graphify.js`). The SQL migration is not indexed because `tree_sitter_sql` is not installed.
- GitHub Actions runs #1/#2 (commits `cc8a67f`, `db1718f`, 2026-10-19) passed: `api`, `agent`, `web` and `secrets`. `act`/`gh` are not installed locally; the remote runs are the CI evidence.
- NOT validated: browser voice UI, any real provider call.

## Open decisions / proposals
- Host ports in `docker-compose.yml` are env-overridable (`POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`, `API_HOST_PORT`, `WEB_HOST_PORT`, `LIVEKIT_*_PORT`) with the original defaults. Needed to run alongside other local stacks without stopping them.

## Blockers
- (none)

## Session log
- Scaffolding session: created repo base, prompts, docs.
- 2026-10-19 P01: installed Poetry/npm deps and lock files; fixed Dockerfile Poetry pin + added `.dockerignore`; parameterized host ports; validated full compose stack from a clean volume (`/health` 200, web 200, agent registered); verified API on Python 3.11 (33 tests) and agent (5 tests); rebuilt Graphify graph and installed the Kilo integration; pinned Poetry 2.4.1 in CI. Pushed `cc8a67f`; GitHub Actions run #1 green (api, agent, web, secrets).
