# Observability

Every component emits one-line JSON logs. The API exposes Prometheus metrics, Sentry is opt-in on
API/worker/web, and OpenTelemetry can join the worker → API tool calls into a single trace.

## Signals

| Signal | API | Voice worker | Web |
|---|---|---|---|
| Structured logs | `triavoz.*` loggers, JSON by default | `triavoz.agent*`, JSON by default | Next.js/Sentry |
| Request correlation | `request_id`, `clinic_id`, `call_id` | `clinic_id`, `call_id` | Sentry release/environment |
| Prometheus | `GET /metrics` | — (business outcomes are persisted by the API) | — |
| Sentry | `TRIAVOZ_SENTRY_DSN` | `TRIAVOZ_SENTRY_DSN` | `NEXT_PUBLIC_SENTRY_DSN` / `SENTRY_DSN` |
| Traces | OTLP/HTTP | OTLP/HTTP + httpx propagation | Sentry tracing (optional) |

Logs never contain transcripts, caller numbers, patient names, tool payloads or request bodies.
`request_id` comes from `X-Request-ID` (sanitized) or a UUID; `clinic_id` is bound only after the
server resolves the tenant (JWT, phone routing or LiveKit room metadata); `call_id` comes from the
server-side call record.

## Prometheus metrics

Scrape `http://api:8000/metrics` (inside Compose). Labels are low cardinality; no tenant, caller or
call identifiers are used.

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `triavoz_http_requests_total` | counter | `method`, `path`, `status` | API traffic; `path` is the route template |
| `triavoz_http_request_duration_seconds` | histogram | `method`, `path` | API latency |
| `triavoz_calls_started_total` | counter | `channel` | Rooms/calls created |
| `triavoz_calls_ended_total` | counter | `status`, `reason` | Calls finished by outcome |
| `triavoz_call_duration_seconds` | histogram | — | Call duration |
| `triavoz_call_cost_cents` | histogram | — | Estimated cost per call |
| `triavoz_call_minutes_total` | counter | — | Voice minutes processed |
| `triavoz_handoffs_total` | counter | `reason`, `completed` | Human handoff requests |
| `triavoz_tool_calls_total` | counter | `tool` | Tool calls served by the internal API |
| `triavoz_tool_errors_total` | counter | `tool`, `code` | Domain errors returned to the agent |
| `triavoz_slot_taken_total` | counter | — | Booking refused because the slot was gone |
| `triavoz_gatekeeper_blocks_total` | counter | `reason` | Sessions refused before any provider spend |
| `triavoz_stage_p50_ms` / `triavoz_stage_p95_ms` | histogram | `stage` | Per-call p50/p95 of EOU, LLM TTFT, TTS TTFB, TTFA |

`GET /api/v1/dashboard` also returns durable per-clinic values for today: `calls_today`,
`avg_duration_seconds`, `handoff_rate`, `cost_per_call_cents`, `cost_per_minute_cents`,
`tool_errors_today`, `slot_taken_today`, `slot_taken_rate`, `gatekeeper_blocks_today`, plus
`latency_p50_ms` / `latency_p95_ms` per stage. Gatekeeper refusals are aggregated in
`gatekeeper_block_stats` (clinic/day/reason/count) so they survive restarts without storing a caller
identifier.

## Grafana / Prometheus

```bash
docker compose --profile observability up -d prometheus grafana
# Prometheus: http://localhost:9090 (override with PROMETHEUS_HOST_PORT)
# Grafana:    http://localhost:3001 (override with GRAFANA_HOST_PORT)
```

Provisioning lives in `infra/observability/`: `prometheus.yml`,
`grafana/provisioning/**` and the dashboard `triavoz-voice` at
`infra/observability/grafana/dashboards/triavoz.json` (calls, handoff rate, tool errors,
slot-taken, gatekeeper blocks, duration p50/p95, stage latency, cost per call/minute, 5xx rate).

## Sentry

Set `TRIAVOZ_SENTRY_DSN` for API/worker and `NEXT_PUBLIC_SENTRY_DSN` + `SENTRY_DSN` for web.
`send_default_pii=False`, request bodies are never sent, and `before_send` removes the request,
user and breadcrumbs. Sentry is a no-op when the DSN is empty, so tests and local runs need no key.

## Traces

Set `TRIAVOZ_OTEL_EXPORTER_ENDPOINT` (for example `http://localhost:4318`) on the API and worker.
The code appends `/v1/traces` when needed. The worker instruments `httpx`, which propagates the W3C
`traceparent` header on every HMAC-signed call; the API’s FastAPI instrumentation joins the same
trace. Log records include `trace_id`/`span_id` when a span is active. `TRIAVOZ_OTEL_SAMPLE_RATIO`
controls sampling.

## Privacy / LGPD

The observability layer is deliberately PII-free: identifiers only, no transcript, no phone, no
name, no tool arguments/output. Sentry request capture is disabled. Metrics labels are aggregate.
Retention and access control for logs/traces remain deployment responsibilities.

## Limitations

- The worker is a LiveKit job process; it exports traces and errors, not a Prometheus endpoint.
  Voice business metrics are recorded by the API at call end.
- `triavoz_stage_p50_ms` / `p95` observe the per-call summary the worker computed, not raw stage
  samples; the Grafana panels show the average of those per-call percentiles.
- Default `prometheus_client` counters are per process. With multiple API replicas, enable
  Prometheus multiprocess mode or scrape each replica.
