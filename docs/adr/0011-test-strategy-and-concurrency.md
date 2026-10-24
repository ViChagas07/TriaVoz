# 0011 — Test strategy: real seams, property tests and a browser smoke

- Status: accepted
- Date: 2026-10-21

## Context

P08 needed confidence on the paths that can lose money or leak data: login/refresh rotation, tenant
isolation, scheduling races, the gatekeeper/HMAC boundary, the voice session and the staff UI. The
suite already had example-based tests and 12-way double booking. The gaps were concurrency,
specification-style slot tests, worker/API drift and browser flows.

## Decisions

1. **Coverage must include SQLAlchemy greenlets.** `tool.coverage.run.concurrency = ["greenlet",
   "thread"]`. Without it, line events after the first awaited DB call are silently lost and
   reports show false gaps (the voice service looked 67% covered while its success path ran).
2. **Property tests for the pure slot engine.** Hypothesis generates windows, busy intervals,
   duration/step/notice and `now`; an independent integer-minute enumerator defines the expected
   set. Non-positive duration/step and negative notice now raise `ValueError` instead of looping
   forever. No database is involved.
3. **Concurrency tests use isolated clinics.** A function-scoped `isolated_clinic` fixture seeds and
   drops its own tenant. Refresh/logins and reschedule races run there, so shared demo tenants cannot
   leak slots or lockouts between tests. The race tests exposed a deadlock between two reschedules
   moving different rows into the same range; all scheduling writers now take a PostgreSQL
   transaction-scoped advisory lock per professional before reading availability. A 40P01 fallback
   maps any bypassing writer to `SlotUnavailable` instead of a 500.
4. **Refresh rotation is an atomic compare-and-set.** `UPDATE refresh_tokens ... WHERE revoked_at IS
   NULL` returns whether the caller won. The loser revokes the family. Exactly one concurrent
   refresh can succeed; the winner's replacement is also revoked by the loser, which is the intended
   reuse response (the user signs in again).
5. **The internal agent API is a checked-in contract.** Every `/internal/agent/*` endpoint declares
   a Pydantic response model. `tests/contracts` snapshots the routes and the recursively referenced
   schemas. Snapshot updates are explicit (`UPDATE_CONTRACT_SNAPSHOTS=1`), never automatic in CI.
6. **Real Redis for SSE.** `RedisEventBus` is tested with two tenant channels and real pub/sub. The
   route test additionally asserts the subscription uses the caller's clinic. The suite skips the
   bus test only when no Redis is configured.
7. **Browser E2E stubs LiveKit, not the API.** Playwright runs the real API, PostgreSQL and Redis
   against a production Next build with `NEXT_PUBLIC_TRIAVOZ_E2E=1`. Only `Room` is replaced, through
   a `page.addInitScript` seam that is absent from normal production builds. The demo test therefore
   covers the connect → captions → tool chip → end flow without provider keys. Traces and videos are
   always recorded. The login form exposes a hydration marker and uses `method="post"`, so a submit
   before React boots can never put credentials in the URL.
8. **CI gates are explicit.** A dedicated `isolation` job, a blocking `e2e` job, coverage artifacts
   + job summary, eval summary and a 3× repeated API suite defend stability. The coverage floor is
   a floor, not a target; the property/concurrency tests exist because they find bugs, not because
   of the percentage.

## Consequences

- `greenlet` is required for coverage (already a SQLAlchemy dependency).
- Hypothesis adds a dev dependency and about one second to the suite.
- Contract snapshots are larger than hand-written assertions but catch renames, type changes and
  missing response models. The diff is reviewable in a pull request.
- The demo seam is dead code in production builds; it is gated by `NODE_ENV` and only injects a
  factory, never a network bypass.
- The voice failure path now commits `status='failed'` before returning 503. A provider failure
  leaves an auditable call row instead of rolling the transaction back.
