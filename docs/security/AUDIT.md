# Security audit — P09

Date: 2026-10-22 · Base revision: `2a2e85a` (working tree includes P09 fixes)
Scope: API (`apps/api`), voice worker (`apps/agent`), web (`apps/web`), PostgreSQL/Redis
isolation, Docker/CI, LGPD handling and the public demo's abuse surface.

This was a source/configuration audit plus adversarial regression tests, not an external
penetration test. Evidence was produced locally against PostgreSQL 16 + Redis 7 (host ports
55433/56379) and a production Next.js build. No live telephony trunk, Cloudflare Turnstile
challenge, Sentry DSN or OTLP collector was available.

## Verdict

- No open **Critical** or **High** findings.
- Tenant isolation and abuse/protection suites are green after the fixes.
- Supply-chain and secret scans are blocking in CI; baseline is clean.
- Residual risks are listed at the end and are intentionally not hidden.

## Findings

| ID | Severity | Finding | Evidence | Fix | Status |
|---|---|---|---|---|---|
| H-01 | High | The public web demo trusted the browser-supplied `caller_number` as proof of ownership. Anyone could POST another person's phone to `/api/v1/voice/session` and use `my-appointments`, `cancel` or `reschedule` against that phone's bookings. | Manual request with a victim phone reached `my-appointments` with that phone before the fix; new regression test `test_caller_identity.py` fails on the old code. | Web calls now receive an opaque httpOnly browser identity cookie; only its SHA-256 hash is stored (`calls.caller_identity_hash`). Ownership is `(provider-verified phone)` **or** `(booking created by a call with the same browser identity)`. A typed phone is contact data, never identity. Migration 0005; the inlined ownership predicate in `PgSchedulingRepository`; `caller_identity.py`. | Fixed; tests green |
| H-02 | High | No Content-Security-Policy on the web app (explicit `TODO(P09)`), so one XSS bug would be unmitigated. | `apps/web/next.config.ts` and headers before the fix. | Per-request nonce CSP in `src/proxy.ts` with `script-src 'nonce-…' 'strict-dynamic'`, `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `connect-src` limited to self/LiveKit/Sentry. Inline theme and JSON-LD scripts receive the nonce. API responses also send a locked-down CSP. | Fixed; production HTML verified: CSP nonce present on 18 script/JSON-LD tags |
| M-01 | Medium | No request body cap. Every route, including unauthenticated login/voice, could be made to buffer an arbitrary JSON body; `TurnsIn` accepted up to 200 arbitrary objects. | Review of `middleware.py` and `TurnsIn`. | ASGI body-limit middleware rejects `Content-Length` and chunked bodies above `TRIAVOZ_MAX_REQUEST_BODY_BYTES` (1 MiB default) with 413. `TurnsIn` now uses a bounded `TurnIn` model (content ≤ 8,000 chars, seq/confidence bounds, tool payload object). | Fixed; unit tests cover both content-length and streamed bodies |
| M-02 | Medium | No cap on concurrent SSE streams; an authenticated account could hold an unbounded number of Redis pub/sub connections. | Review of `events.py`. | Process-local per-user/per-clinic caps (`sse_max_connections_per_user=2`, `sse_max_connections_per_clinic=50`), released in the stream generator's `finally`; 429 + `Retry-After`. | Fixed; unit test |
| M-03 | Medium | `/auth/refresh`, `/metrics` and `/internal/*` had no rate limit; refresh is unauthenticated by design. | Route review. | Refresh IP token bucket (60 capacity), metrics IP bucket (120/min), internal IP bucket (6,000 capacity) before HMAC work. Login/voice already had buckets. | Fixed |
| M-04 | Medium | Production guards accepted short/default JWT/HMAC secrets, wildcard/HTTP CORS origins and the dev LiveKit key; cookies were not `__Host-`. | `Settings` review. | Production requires ≥32-char non-default JWT/HMAC secrets, HTTPS explicit origins, no wildcard, `Secure` cookies, non-default LiveKit credentials, runtime DB role, and automatically uses `__Host-` cookie names. Cookie clearing repeats `Secure`/`Path` so `__Host-` cookies can actually be deleted. | Fixed; unit tests |
| M-05 | Medium | No login timing floor; unknown clinics could answer faster than real ones, enabling clinic/account enumeration. | `auth.py` review. | Constant-time floor (`TRIAVOZ_LOGIN_MIN_SECONDS=0.25`) around every login outcome plus a dummy Argon2 verify for unknown clinics. | Fixed |
| M-06 | Medium | `GET /agent-config` and `/agent-config/versions` were readable by attendants (direct API call), although the UI is admin-only. | Route review; RBAC test. | Both reads now use `require_admin`; RBAC regression test asserts 403 for attendants. | Fixed |
| M-07 | Medium | No LGPD retention/expurgo implementation; the design was a TODO because broad `triavoz_ops` grants were undesirable. | ADR 0005 + review. | Narrow `SECURITY DEFINER` functions `purge_expired_transcripts` and `purge_expired_refresh_tokens` owned by `triavoz_definer`; `triavoz_ops` has only `EXECUTE`. The job deletes old transcript turns, pseudonymises old call metadata (including calls with no turns), writes `audit_log`, and deletes revoked/expired refresh tokens. `scripts/purge_retention.py` + `make purge-retention`. | Fixed; DB test includes an active call, old call and old call with no turns |
| M-08 | Medium | CI ran `pip-audit` and `npm audit` with `continue-on-error`, so vulnerable dependencies could merge. | `.github/workflows/ci.yml` before the fix. | Both audits are blocking; the worker is audited too. Added blocking Trivy config and image-scan jobs (HIGH/CRITICAL, ignore-unfixed). | Fixed; local baseline clean |
| M-09 | Medium | Logout cleared cookies on a `Response` object that was then discarded; the actual 204 response carried no `Set-Cookie`, so a shared device kept both tokens. | `test_login_me_refresh_rotation_and_logout` assertion before the fix; logout returned no `Set-Cookie`. | Logout builds the 204 response first and clears both cookies on it; clearing repeats `Secure`/`Path` so `__Host-` cookies are removed. Regression assertion added. | Fixed; test green |
| M-10 | Medium | FastAPI’s default 422 body echoed the submitted input, so an over-long password or transcript field was reflected in the response (and potentially client logs). | Manual validation request before the handler; regression test `test_validation_errors_do_not_echo_secrets`. | `RequestValidationError` handler returns only field locations/types plus `invalid_request`; no input values or contexts. | Fixed; test green |
| M-11 | Medium | A burst of unauthenticated logins could run many 64 MiB Argon2 verifications concurrently (memory exhaustion). | Argon2 parameter review; rate limits alone do not bound concurrency. | A semaphore bounds password verification to 4 concurrent Argon2id operations; dummy and real paths share it. | Fixed |
| L-01 | Low | Login success/failure, refresh reuse, settings/catalog and staff appointment mutations were not all in `audit_log`. | Route/service review. | Added audit entries for login success/failure, refresh reuse, settings/catalog CRUD, and staff appointment create/move/cancel. | Fixed |
| L-02 | Low | HMAC secret rotation required a flag day. | `hmac_auth.py` review. | Verification accepts `TRIAVOZ_INTERNAL_HMAC_SECRET_PREVIOUS` while the worker is rotated; signing always uses the current secret. | Fixed; unit test |
| L-03 | Low | `/internal/*` relied only on HMAC; no network allow-list. | `internal_agent.py` review. | Optional `TRIAVOZ_INTERNAL_ALLOWED_CIDRS`; empty by default because managed platforms do not expose a stable proxy CIDR. HMAC remains the authentication boundary. | Configurable; documented residual |
| L-04 | Low | Login redirect accepted crafted `next` values (`//`, backslashes, encoded paths). | `login/page.tsx` review. | Only a single-leading-slash same-origin path survives; backslashes/control chars are rejected and the value is resolved against a fixed origin. | Fixed |
| L-05 | Low | The API itself had no security headers for direct requests; only the web proxy did. | `middleware.py` review. | API adds nosniff, DENY framing, no-referrer, permissions policy, restrictive CSP, CORP and HSTS in production. | Fixed |
| L-06 | Low | `style-src 'unsafe-inline'` remains necessary for Next.js/production CSS; the CSP is not hash-based for styles. | CSP review. | Accepted; scripts remain nonce/strict-dynamic gated. | Residual |
| L-07 | Low | `audit_log` is append-only for the app role but the app role can INSERT arbitrary rows (forgery, not tampering). | Role grants review. | Accepted for the demo; production should write audit entries through a definer function or a separate principal. | Residual |
| L-08 | Low | Exception log messages may contain fragments of DB errors (possible PII); Sentry drops request/user/breadcrumbs but does not rewrite exception text. | Logging/Sentry review. | Request bodies, user identity, query strings and breadcrumbs are stripped; generic 500s. Further redaction is deployment-specific. | Residual |

## Checklist evidence

### 1. Tenant isolation

- `tests/isolation` (RLS guard, cross-tenant reads/writes, role privileges, DEFINER routing):
  **15 passed**.
- `scripts/verify_rls_mutations.py`: permissive policy, missing `FORCE ROW LEVEL SECURITY`, and
  `BYPASSRLS` on the runtime role were each **detected**, then restored and verified green.
- All new tables/columns stay inside existing forced-RLS tables (`calls.caller_verified`,
  `calls.caller_identity_hash`); no new tenant table was added.
- Retention functions are `SECURITY DEFINER` with pinned `search_path`, fully qualified tables,
  `EXECUTE` revoked from `PUBLIC`, granted only to `triavoz_ops`; the DB test confirms ops still
  cannot `SELECT` tenant tables.
- Redis keys: event channels are `triavoz:clinic:{id}:events`; rate/idempotency/replay keys either
  contain the clinic id or hold no tenant content. SSE subscribes only to the principal's clinic.
- Raw SQL is parameterized; the ownership predicate is written literally in each query (no
  string-built SQL at all). Ruff `S608` passes.
- No object storage, no cross-tenant cache, and no raw transcript/caller number in logs/metrics.

### 2. AuthN / AuthZ

- Argon2id with explicit `m=65536,t=3,p=4`, 32-byte hash, 16-byte salt; unit-tested hash prefix.
- Login uses one generic error for unknown clinic/email/password, dummy verification for unknown
  users/clinics, account + IP token buckets, and a 250 ms timing floor.
- Refresh tokens are opaque, SHA-256 hashed at rest, rotated per family; reuse revokes the family
  (concurrent test: exactly one 200) and now writes an audit entry. Refresh is IP rate-limited.
- JWT: HS256 pinned, `typ`/`exp` required, 15-minute TTL, production secret strength enforced.
- Cookies: `HttpOnly`, `SameSite=Lax`, `Secure` in production, no `Domain`, `__Host-` prefix in
  production, `Path=/` (required by `__Host-` and by the Next proxy refresh path).
- CSRF: same-origin proxy + `SameSite=Lax` on all mutations; CORS is an explicit non-wildcard list
  and rejects HTTP origins in production. No cross-site form POST carries the cookie in modern
  browsers. (If a cross-origin frontend is introduced, add a CSRF token first.)
- RBAC: admin-only writes plus agent-config reads; attendant reads of clinic settings/services are
  operationally required by the shared shell/agenda and contain no secrets.
- IDOR: every `{id}` route is tenant-scoped by RLS and returns 404 for another tenant; the new
  caller-identity tests cover cross-phone access. DB-level test for all resource families remains
  green.
- Known residual: a deactivated/demoted user's access JWT remains valid for ≤15 minutes; refresh is
  revoked immediately. Documented in ADR 0006.

### 3. Service-to-service

- HMAC-SHA256 over the exact body, timestamp ±60 s, signed single-use nonce (Redis claim, in-memory
  fallback), `hmac.compare_digest`, previous-secret rotation support.
- `/internal/*` is not exposed by the Next proxy (`matcher` excludes `/api`); optional CIDR
  allow-list. The API URL itself is public on Render, so HMAC is the boundary; see residual risks.
- Internal requests are rate-limited before body/HMAC work and bodies are size-capped.

### 4. Injection and web

- SQLi: parameterized SQLAlchemy Core/`text()` everywhere; no f-string/format SQL in runtime code.
- XSS: React escapes all tenant/user text; no `dangerouslySetInnerHTML` except a constant theme
  script and server-built JSON-LD, both nonce-gated. CSP is the second layer.
- SSRF: no user-controlled server-side URL. Turnstile/Sentry/OTLP/LiveKit endpoints come from
  environment configuration only.
- Open redirect: login `next` hardened. No file upload/path handling, no unsafe deserialization
  (JSON only), no dynamic `eval`.
- Mass assignment: explicit Pydantic models; `AgentConfigSchema` forbids extras; DB inserts list
  columns explicitly; worker `tool()` reserves `clinic_id`/`call_id` as positional-only server ids.
- CORS: explicit origins, credentials only for that list; production rejects `*` and HTTP.

### 5. Prompt injection and agent abuse

- System prompt treats caller text as data, forbids role changes/prompt disclosure/other patients,
  and requires confirmation before writes.
- Tool-side authorization does not depend on the LLM: tenant comes from the HMAC-bound call record,
  ownership from verified phone/browser identity, offered slots are re-validated, and the DB
  exclusion constraint is the final arbiter.
- Regression evals (`apps/api/evals`) now include `impersonation_and_tool_tampering` alongside
  `prompt_injection` and `wrong_owner_cancel_refused`: foreign cancel → `not_found`, reserved
  `clinic_id` argument → `reserved_tool_argument`, 10,000-char name → 422, no booking side effect.
- `make evals`: **11/11 scenarios pass**, 0 hallucinated slots, 100% recovery/handoff accuracy.
- Oversize text is bounded by body and per-turn limits; STT text is just another caller turn.

### 6. DoS / cost

- Limits on login, refresh, voice session (caller/IP/global + Turnstile when configured), metrics,
  internal endpoints and SSE connections.
- 1 MiB request cap; 200-turn cap with 8,000-char turn cap.
- Gatekeeper still enforces concurrency, daily minutes/cost, kill switch, demo caps and the cost
  circuit breaker; emergency override is preserved.
- LiveKit token TTL 600 s, `roomAdmin`/`roomCreate` false, `max_participants=2`, empty-room timeout.
- Residual: SSE caps are per process (documented); ingress-level connection limits are recommended.

### 7. Secrets and supply chain

- `gitleaks detect --source . --redact` over full history: **no leaks**.
- `.env` is ignored and was never committed; `.env.example` contains placeholders only.
- `pip-audit` on exported API and worker lockfiles: **no known vulnerabilities**.
- `npm audit` (prod and dev at audit level high): **clean**.
- `poetry.lock`, `package-lock.json` committed; Dockerfiles run as non-root and use minimal images.
- CI permissions are `contents: read`; gitleaks, pip-audit, npm audit and Trivy config are blocking.
- Trivy config scan (HIGH/CRITICAL): **no findings**. Locally built API, worker and web images scan **clean** at HIGH/CRITICAL; CI now builds all three and blocks on image CVEs.

### 8. LGPD / data protection

- Consent/transcription notice is shown before the demo starts and the agent says the call may be
  transcribed.
- `purge_expired_transcripts` uses each clinic's `transcript_retention_days`, deletes bounded
  batches, nulls summary/caller number once no turns remain (including calls that never had turns),
  and writes `audit_log`. Expired/revoked refresh tokens are purged. `make purge-retention` runs as
  `triavoz_ops`.
- `audit_log` covers transcript reads, login/failure/reuse, team, blocked numbers, config
  draft/publish/rollback, settings/catalog and staff appointment mutations.
- PII in logs/metrics/Sentry: log fields are allow-listed; metrics are aggregate with no tenant or
  caller labels; Sentry disables request/user/breadcrumbs and strips them in `beforeSend`.
- Residual: no field-level encryption (DB-at-rest depends on the provider), backups/restore drills
  are not configured in this repository, and `audit_log`/IP retention is a legal decision.

### 9. Headers / TLS

- Web: nonce CSP, HSTS, `frame-ancestors 'none'`, `X-Frame-Options: DENY`, nosniff, referrer
  policy, permissions policy (microphone only for the demo origin), COOP/CORP.
- API: locked-down CSP, nosniff, DENY, no-referrer, permissions policy, CORP, HSTS in production.
- Production cookies use the `__Host-` prefix where possible (`Secure`, `Path=/`, no `Domain`).
- TLS is terminated by the platform; both Vercel and Render provide HTTPS. No custom TLS
  configuration is stored in this repository.

## Verification commands

```text
# API
poetry run pytest -q                                  # 135 passed
poetry run pytest -q --cov=triavoz --cov-fail-under=85 # 89.54%
poetry run pytest -q tests/isolation                   # 15 passed
poetry run python ../../scripts/verify_rls_mutations.py # all 3 mutations detected/restored
poetry run python -m evals                             # 11/11 scenarios
poetry run ruff check src tests migrations scripts evals
poetry run ruff format --check src tests migrations scripts evals
poetry run mypy src

# Worker
poetry run pytest -q                                   # 20 passed
poetry run ruff check src tests && poetry run mypy src

# Web
npm run typecheck && npm run build
npx playwright test                                    # 4/4 (CSP enabled)
# production smoke: CSP header + nonce present in served HTML

# Security gates
docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:v8.28.0 detect --source /repo --redact
pip-audit -r <exported api requirements>
pip-audit -r <exported worker requirements>
npm audit --omit=dev --audit-level=high
docker run --rm -v "$PWD:/work" aquasec/trivy:0.58.1 config --severity HIGH,CRITICAL /work
docker build -t triavoz-api:ci apps/api && trivy image --severity HIGH,CRITICAL --ignore-unfixed triavoz-api:ci
# same for apps/agent and apps/web (all three: 0 HIGH / 0 CRITICAL locally)
```

## Residual risks (accepted, monitored)

1. **Proxy IP collapse.** Rate-limit keys use the peer address unless
   `TRIAVOZ_TRUST_FORWARDED_FOR=true` is set behind a proxy that overwrites XFF. If left false on
   Vercel→Render, per-IP buckets become one global bucket. If set true while the API is directly
   reachable, a client can spoof XFF (account buckets and the global budget still apply).
2. **Stale access token after deactivation/demotion** for at most 15 minutes; refresh families are
   revoked immediately.
3. **Per-process SSE caps** and **in-memory fallbacks** when Redis is unavailable; multi-replica
   deployments need an ingress cap and should treat Redis as required for replay/rate guarantees.
4. **Service-wide HMAC secret.** A compromised worker can act for any tenant. The worker has no DB
   credentials, internal routes are rate-limited/allow-listable, and the secret can be rotated with
   the previous-secret window. Per-tenant worker credentials are the next hardening step.
5. **`/internal/*` on a public API hostname.** HMAC is the boundary; restrict at the edge/private
   network and set `TRIAVOZ_INTERNAL_ALLOWED_CIDRS` when the platform provides stable egress ranges.
6. **No field-level encryption** for phone/transcript fields; rely on provider disk encryption and
   TLS. Backups/restore drills and key management are deployment responsibilities.
7. **Sentry exception text** can still contain fragments of a DB error; request/user/breadcrumbs
   are removed. Review the project's data-scrubbing rules before enabling it in production.
8. **Style CSP** allows inline styles for Next.js; scripts are nonce/strict-dynamic. Consider a
   nonce/hash style pipeline if the UI stops relying on runtime inline styles.
9. **`audit_log` insertion is not authenticated separately**; the app role can write an entry. The
   table remains append-only (no UPDATE/DELETE for the app role).
10. **Prompt injection remains a probabilistic LLM risk.** Tool-side authorization bounds the
    impact; deterministic evals cover the known attack families, not every phrasing.
11. **Phone caller ID spoofing** is provider-dependent; the telephony adapter is HMAC-signed but
    caller-ID trust ultimately depends on the carrier.
12. **No MFA, password reset or WAF**; staff accounts are demo accounts. Add MFA and a reset flow
    before real PHI.
13. **Container base images are tag-pinned, not digest-pinned** (`python:3.11-slim`, `node:22-alpine`).
    CI now builds and scans all three images (clean at HIGH/CRITICAL); pin digests for reproducible
    deploys.
14. **Demo abuse identity can be rotated** by clearing cookies/sessionStorage; per-caller/global
    budgets, concurrency and kill switch still cap cost. The goal is cost protection, not perfect
    attribution.
15. **`audit_log.ip` and `refresh_tokens.created_ip` are PII**; token rows are purged after 30 days,
    audit rows are retained. Legal retention must decide the audit period.
16. **Operational coupling of `__Host-` cookie names.** Production must set `COOKIE_PREFIX=__Host-`
    on the web service to match the API; a mismatch makes the web auth guard refresh/reload on
    every navigation. The API logs a startup warning for the proxy-IP/no-XFF case, not for this one.
17. **Service-request and appointment PII is business data.** Names/phones/notes in
    `service_requests`/`appointments` are not auto-purged; only transcripts and call metadata are.
    The retention period for operational records is a legal/business decision and must be set before
    real PHI. (The unused `patient_document_enc` column is not populated; no CPF is collected.)
