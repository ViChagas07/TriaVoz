# ADR 0001 — Stack and security baseline

**Status:** accepted · **Context:** solo portfolio project; author's usual stack; ForjaB2B conventions not available when this was written (fill the gap below if they differ).
**Decision:** Python 3.11 + Poetry + FastAPI + SQLAlchemy 2 async + PostgreSQL + Redis; Next.js (App Router) + TypeScript + Tailwind v4 + Zustand + next-intl; Docker Compose + GitHub Actions. Security baseline: Argon2, short JWT + rotating refresh in httpOnly cookies, RBAC in the API, Token Bucket rate limiting, HMAC for service-to-service calls, same-origin proxy (no CORS), security headers, secrets from env, audit log.
**Consequences:** one language family for API and voice worker (Python); migrations use a sync driver (psycopg) while runtime uses asyncpg.
**ForjaB2B alignment:** `[author to list any differences; agents must follow ForjaB2B conventions where they differ and record it here]`.
