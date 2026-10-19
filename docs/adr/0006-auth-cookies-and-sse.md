# ADR 0006 — Auth cookies, rotation and SSE

**Status:** accepted (P03)

## Context
The browser talks only to its own origin (`/api/v1` is proxied to FastAPI). Staff need a short
access token for normal fetches and a way for `EventSource` to authenticate; the refresh token must
never be readable by JavaScript.

## Decision
- **Access token:** 15-minute HS256 JWT, returned in JSON and also set as the `triavoz_access`
  cookie (`HttpOnly`, `SameSite=Lax`, `Secure` in production, path `/`). The cookie exists so SSE and
  same-origin navigations authenticate without putting the token in a query string.
- **Refresh token:** opaque, 30 days, `HttpOnly`, `SameSite=Lax`, path `/api/v1/auth` (only the auth
  endpoints receive it). The database stores only its SHA-256 hash.
- **Rotation/reuse:** every refresh rotates the token inside the same `family_id`. A revoked token
  presented again returns 401 **and commits a family-wide revocation** before the response. The
  family revocation is deliberately returned as an outcome and executed by the caller after the
  tenant transaction commits; raising inside the transaction would roll it back.
- **Logout/deactivation:** logout revokes the refresh family; deactivating a staff user revokes their
  active refresh tokens. Access tokens already issued remain valid for at most 15 minutes.
- **CSRF:** mutations are JSON requests to the same origin; `SameSite=Lax` blocks cross-site POST
  cookies. CORS is an explicit allow-list (no `*`), and credentials are allowed only for that list.
  If a separate frontend origin is introduced, add an explicit CSRF token before loosening this.
- **SSE:** `/api/v1/events/stream` requires the access cookie (EventSource cannot set headers),
  emits a retry hint and heartbeats, and subscribes to `triavoz:clinic:{id}:events`. The Redis
  subscriber queues at most 100 frames and drops the oldest under backpressure.

## Rejected
- Refresh/access tokens in `localStorage` (XSS becomes account takeover).
- `SameSite=None` (not needed with the same-origin proxy and weaker against CSRF).
- Non-httpOnly access cookie (would expose the token to scripts).
- Revoking only the presented refresh token on reuse (an attacker could keep the stolen sibling).
