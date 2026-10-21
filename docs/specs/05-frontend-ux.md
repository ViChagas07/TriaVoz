# 05 — Frontend UX (v2, nine lean routes)

Status: implemented in P06. This file is the route/layout source of truth. The product intentionally
has **nine routes**; metadata endpoints (`robots.txt`, `sitemap.xml`, icons, OG image) and auth
utility endpoints are infrastructure, not product pages.

## Routes

| Route | Access | Purpose |
|---|---|---|
| `/` | public | Landing page: hero orb, how it works, features, FAQ, CTA, JSON-LD |
| `/demo` | public | Live voice demo: LiveKit token, connect, captions, tool chips, booking card, timer |
| `/login` | public | Clinic code + email + password; demo chips; generic error / lockout feedback |
| `/painel` | staff | KPIs, latency, cost, today's schedule, SSE activity with toasts |
| `/chamadas` | staff | Call table, URL filters, review badge, pagination |
| `/chamadas/[id]` | staff | Transcript, tool chips, summary, metrics, appointment, events |
| `/agendamentos` | staff | Tabs: schedule (grouped by day), pending queue, history; filters in URL; side panel |
| `/agente` | admin | Greeting/tone/emergency message, versions, publish/rollback, in-browser test |
| `/configuracoes` | admin | Clinic + hours, services, professionals, blocked numbers, team |

Legacy skeleton URLs (`/agenda`, `/historico`, `/solicitacoes`, `/equipe`, `/agente/*`) redirect to
the routes above in `next.config.ts`; they are not pages.

## Layout

- Public pages use `PublicHeader` (logo, locale, theme, sign-in) and the same brand tokens.
- Authenticated pages use `AppShell`: desktop sidebar, mobile top bar + bottom tab bar, clinic name,
  role-filtered navigation (`/agente` and `/configuracoes` are admin-only), pending counter, sign-out.
- No tokens in `localStorage`. The API sets httpOnly cookies; the browser only calls same-origin
  `/api/v1`. The `(app)` server layout validates `/auth/me`; the proxy rotates the refresh cookie
  before redirecting to `/login`.
- Cross-tenant URLs render the 404 page because the API returns 404 under RLS.

## `/demo` behaviour

1. `POST /api/v1/voice/session` (same-origin proxy) with a per-tab synthetic caller number.
2. Handle gatekeeper outcomes before touching LiveKit: `blocked`, `rate_limited`, `concurrency`,
   `budget`, `breaker`, `kill_switch`, `after_hours`, `emergency`. Every fallback shows the API
   message and SAMU 192 guidance.
3. Connect with `livekit-client`; attach remote audio; enable mic (permission errors are a distinct
   state), start audio, subscribe to `TranscriptionReceived` and `DataReceived` (`triavoz.events`).
4. Orb state is bound to active speakers; captions are a live region; tool chips and the booking card
   come from PII-free worker events.
5. Countdown uses the server's `max_call_seconds`; ending disconnects and shows a local summary with
   a link to `/chamadas/{id}` (requires staff auth).
6. Network drop/reconnect and provider errors have explicit states. `?preview=` states exist **only**
   in development (`NODE_ENV !== "production"`); production ignores them.

## Data and states

Every data view has loading (`loading.tsx`/skeletons), empty and error states. URL search params are
the source of truth for filters so links/share/back all work. Mutations refresh the server component
and optimistically update safe local state where it helps (request status/assignment, settings rows).

## i18n

- Locales: `pt-BR` (default) and `en`, cookie-based. `?lang=pt-BR|en` sets the cookie and redirects
  to the clean URL; metadata declares hreflang alternates.
- Server components use `getTranslations`; client islands are wrapped by `ScopedMessages` so each
  route only ships the namespaces it needs. `messages/pt-BR.json` and `en.json` must keep the same
  keys (checked by script in P06).

## Accessibility and motion

- Skip link, landmarks, one h1 per page, visible focus, `aria-current` navigation, labelled fields.
- Dialogs/side panel: focus on open, Escape closes, focus trap in the request panel.
- Captions and toasts are live regions; status uses icon + text + color (never color alone).
- `prefers-reduced-motion` disables orb/halo/skeleton animations.

## SEO / AEO / GEO

- `metadataBase`, title template, description, Open Graph/Twitter, per-page titles, `robots.ts`,
  `sitemap.ts`.
- JSON-LD `SoftwareApplication` + `FAQPage` on the landing page; `public/llms.txt` for answer engines.
- No medical claims, no real data, no invented ratings.

## Out of scope for P06

- Path-based locales (cookie + `?lang` was chosen to keep exactly nine routes; revisit only with an
  ADR).
- Frontend dashboard badge on the request list is data-ready (`suspicion_flags`/`needs_review`) but
  the visual polish is part of this P06 page, not a new route.
