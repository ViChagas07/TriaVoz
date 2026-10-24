# ADR 0010 — Observability, agent evals and the RAG decision

- **Status:** accepted
- **Date:** 2026-10-21
- **Phase:** P07

## Context

P07 must make quality measurable: structured logs with request/tenant/call correlation, error
tracking, Prometheus metrics with a Grafana dashboard, dashboard data for P06, and an eval suite
that proves the agent never invents a slot. Per-clinic RAG was optional and required explicit author
confirmation.

## Decision

1. **Logs.** Stdlib logging is formatted as one-line JSON on API and worker. `request_id` is
   sanitized from `X-Request-ID`; `clinic_id` is bound only after server-side tenant resolution
   (JWT, phone routing, room metadata); `call_id` comes from the stored call. A mutable
   request-scoped context bag lets the HTTP middleware read identifiers resolved inside Starlette’s
   request task. No transcript, caller number, name or tool payload is logged.
2. **Errors.** Sentry is opt-in via `TRIAVOZ_SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN`. PII is off,
   request bodies are never captured and `before_send` strips request/user/breadcrumbs.
3. **Metrics.** `prometheus-client` exposes `/metrics`. Route-template labels avoid cardinality
   explosions. Business counters are incremented at the boundary that owns the fact (call start/end,
   tool endpoint, gatekeeper refusal, slot conflict). Durable per-clinic daily values come from
   PostgreSQL; gatekeeper refusals are aggregated in `gatekeeper_block_stats` (no caller data).
4. **Traces.** OpenTelemetry is opt-in via `TRIAVOZ_OTEL_EXPORTER_ENDPOINT`. The worker instruments
   httpx, so every signed tool request carries `traceparent`; FastAPI instrumentation on the API
   joins the same trace. Logs include trace/span ids when active.
5. **Evals.** A deterministic, text-mode harness drives the real tool endpoints against a real
   test DB. The scripted patient/agent is intentional: it runs in CI without provider keys and
   asserts server-side guarantees (ownership, offered-slot validation, exclusion constraint,
   handoff). The suite has a hard gate: zero hallucinated slots and 100% task success.
6. **RAG.** Not implemented in P07. It was optional, the author did not confirm it, and the local
   PostgreSQL 16 image does not ship `pgvector` (`pg_available_extensions` has no `vector` row).
   `knowledge_documents` remains out of the schema. If accepted later, it needs a migration with
   forced RLS, an embeddings port, a `lookup_clinic_info` tool and isolation/eval cases.

## Consequences

- Operators get one scrape target and a ready dashboard; logs and traces are correlated by the same
  call/tenant identifiers.
- The API remains usable without Redis, Sentry or an OTLP collector: all integrations are optional
  and fail closed to no-op.
- The eval suite protects contracts and guardrails, but not LLM phrasing/prompt adherence; the live
  voice checks remain the manual counterpart. A provider-backed LLM variant is a documented next
  step.
- Per-process Prometheus counters need multiprocess mode when the API scales horizontally.
- The new tenant table follows the existing contract: `clinic_id NOT NULL`, ENABLE+FORCE RLS,
  tenant policy, runtime grants, and a seed row so the isolation suite covers it.
