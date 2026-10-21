# 0009 — Locale strategy: cookie + `?lang`, not path prefixes

Status: accepted · 2026-10-21 · P06

## Context

The product is deliberately limited to nine routes. The bilingual requirement (pt-BR default, en)
could be solved with path prefixes (`/pt-BR/...`, `/en/...`) or with a cookie. Path prefixes are the
most conventional SEO choice, but they would double the route table for every page and fragment the
route budget the spec fixed at nine. The landing page is the only indexable surface; authenticated
pages are `noindex` and excluded from `robots.txt`.

## Decision

- The locale lives in an `httpOnly`-free `locale` cookie (`SameSite=Lax`, one year).
- `?lang=pt-BR` / `?lang=en` is the stable share/hreflang URL. `proxy.ts` stores the value and
  redirects to the clean path, so canonical URLs stay clean.
- `metadata.alternates.languages` points to `?lang=…`; canonical stays the clean path.
- Server components use `getTranslations`; client islands receive only their route's namespaces via
  `ScopedMessages`. Both message catalogs must have identical keys (checked during P06).
- No locale prefix is added to authenticated routes. They are not indexed.

## Consequences

- One route table, no duplicated pages, no locale-aware link helper everywhere.
- A user who shares a clean URL gets the recipient's own locale, not the sender's. The `?lang` link
  exists for explicit language sharing.
- If organic acquisition in English becomes a goal, introduce `/en` with an ADR and redirects rather
  than silently doubling the app.
