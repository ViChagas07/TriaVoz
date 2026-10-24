# Testing and E2E

## Commands

```bash
# API (needs PostgreSQL; Redis unlocks Lua + SSE tests)
cd apps/api
poetry run pytest
poetry run pytest --cov=triavoz --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=85
poetry run pytest tests/isolation      # blocking tenant-isolation gate
poetry run pytest tests/contracts      # internal agent OpenAPI snapshot

# Browser smoke (starts API :58000 and a production web build :3300, reusing running servers locally)
cd apps/web
npm run test:e2e
```

`TRIAVOZ_TEST_OWNER_DSN`, `TRIAVOZ_TEST_APP_DSN`, `TRIAVOZ_TEST_OPS_DSN` and
`TRIAVOZ_TEST_REDIS_URL` are read by `apps/api/tests/conftest.py`. The Playwright config converts
the app DSN for asyncpg, starts both servers, and passes the same secrets to the API. Seed the demo
clinics once with `poetry run python scripts/seed_demo.py` (owner DSN).

## Coverage on the critical paths

Latest local run: **114 tests, 89.4% total**, floor enforced at 85% in CI. Coverage is measured with
`concurrency = ["greenlet", "thread"]`; without the greenlet entry, coverage silently loses lines
after SQLAlchemy's first awaited DB call.

| Critical path | Module | Coverage |
|---|---|---:|
| Auth / refresh rotation | `application/auth/service.py` | 91% |
| Refresh persistence | `infrastructure/db/auth_repo.py` | 94% |
| RLS / tenant isolation | `tests/isolation` (functional gate) | green |
| Scheduling rules | `application/scheduling/use_cases.py` | 94% |
| Scheduling persistence | `infrastructure/db/scheduling_repo.py` | 93% |
| Slot engine | `domain/scheduling/slots.py` | 100% |
| Gatekeeper | `application/abuse/gatekeeper.py` | 91% |
| HMAC signing/replay | `infrastructure/security/hmac_auth.py` | 100% |
| Voice session | `application/voice/service.py` | 90% |
| LiveKit adapter | `infrastructure/voice/livekit_service.py` | 100% |
| Redis SSE bus | `infrastructure/events/redis_events.py` | 77% |
| Internal agent API | `interfaces/http/internal_agent.py` | 87% (plus contract snapshot) |

## What the new tests defend

- **`free_slots` properties (Hypothesis):** every returned slot is inside a window, aligned to the
  step grid, clear of all busy intervals (mixed timezones) and after `now + min_notice`; every
  candidate that satisfies those rules is returned. Non-positive duration/step and negative notice
  raise instead of looping.
- **Concurrency:** double booking (existing), two reschedules racing for one target, reschedule
  racing a new booking, two refreshes with the same cookie (one 200, one 401, family revoked), two
  simultaneous logins (independent families), SSE fan-out on two real Redis tenant channels.
  Scheduling writers take a per-professional transaction-scoped advisory lock before reading
  availability; this serialises the exclusion-index race that otherwise deadlocks. A 40P01
  fallback maps to `SlotUnavailable` for any writer that bypasses the lock.
- **Contract:** every `/internal/agent/*` operation has an explicit response model. The checked-in
  snapshot covers routes plus recursively referenced schemas. Update it only with
  `UPDATE_CONTRACT_SNAPSHOTS=1` and review the diff.
- **Voice failure:** provider failure commits `calls.status='failed'` and returns 503; it no longer
  rolls the failed call back with the request transaction.
- **E2E:** login → pending queue → request panel → transcript → complete; agent edit → draft →
  publish → restore; demo connect → captions → tool chip → end (LiveKit stubbed); clinic A cannot
  open clinic B's call URL (UI not-found + API 404). Traces and videos are always recorded under
  `apps/web/test-results/` and uploaded by CI.

## Flake control

- Function-scoped `isolated_clinic` fixture for concurrency/auth tests; seed and cleanup run under
  the owner role with `app.current_clinic_id` set, so RLS never hides rows from cleanup.
- Scheduling tests use explicit future Mondays and deterministic slot arithmetic; `free_slots`
  takes an explicit `now`.
- Playwright runs with one worker, no retries, English locale cookie; every run creates fresh
  requests with unique titles and caller numbers.
- CI runs the API suite three times and E2E once, then uploads coverage, eval and Playwright
  artifacts. `isolation` and `e2e` are blocking jobs.

## Not covered on purpose

- Real LiveKit media in E2E (provider keys, camera/mic permissions, network); the room is stubbed
  while the API, auth, DB and Redis are real.
- Firefox/WebKit/mobile browsers; CI installs Chromium only.
- Live telephony/SIP and Deepgram/LLM/TTS providers (P04/P05 manual drills).

