# Graph Report - Triavoz  (2026-10-19)

## Corpus Check
- 154 files · ~37,967 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 18 file(s) not represented in the graph (top: (none) 13, .example 2, .ini 1)

## Summary
- 1140 nodes · 3041 edges · 85 communities (46 shown, 39 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 396 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8d22748b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- entrypoint
- SchedulingRepository
- package.json
- PgSchedulingRepository
- internal_agent.py
- triavoz/config.py
- Test Fixtures
- triavoz/main.py
- Dashboard Pages
- AppShell.tsx
- Agent Tool Definitions
- TypeScript Configuration
- ADR 0005 — Refresh tokens, per-clinic limits and transcript retention
- seed_demo.py
- System Architecture
- redis_events.py
- Frontend API Client
- Voice Worker Specs
- Documentation Tools
- PostCSS Configuration
- Multi-tenancy Specs
- Database Role Scripts
- StaffRepository
- Dashboard Overview
- Security Baseline ADR
- Voice Pipeline ADR
- Booking Integrity ADR
- StaffService
- Scheduling Specs
- Abuse Protection Specs
- Agent Service
- API Service
- PgStaffRepository
- Redis Infrastructure
- Web Frontend
- schemas.py
- PgVoiceSessionRepository
- auth.py
- dataclasses
- use_cases.py
- deps.py
- scheduling_repo.py
- session.py
- Principal
- triavoz_agent/main.py
- test_scheduling_db.py
- PgCallRepository
- dependencies
- next-intl
- devDependencies
- StatusBadge.tsx
- AppointmentView
- scripts
- ADR 0006 — Auth cookies, rotation and SSE
- app/layout.tsx
- request.ts
- ui.ts
- test_agent_units.py
- agenda.py
- telemetry.py
- agent.py
- requests.py
- blocked.py
- triavoz_agent/config.py
- prompts.py
- ADR 0007 — Live voice pipeline, turn tuning, turn persistence and handoff
- redact_tool_arguments

## God Nodes (most connected - your core abstractions)
1. `StaffRepository` - 62 edges
2. `Principal` - 49 edges
3. `NotFound` - 44 edges
4. `StaffService` - 40 edges
5. `PgSchedulingRepository` - 40 edges
6. `PgStaffRepository` - 39 edges
7. `get_settings()` - 36 edges
8. `SchedulingRepository` - 35 edges
9. `tenant_session()` - 32 edges
10. `entrypoint()` - 31 edges

## Surprising Connections (you probably didn't know these)
- `Handoff` --references--> `SipHandoff`  [INFERRED]
  docs/adr/0007-voice-pipeline-turns-handoff.md → apps/agent/src/triavoz_agent/handoff.py
- `API Service (FastAPI)` --references--> `Tenant Isolation Policy`  [INFERRED]
  docker-compose.yml → docs/agent/RULES.md
- `CallContext` --uses--> `TriaVozApi`  [INFERRED]
  apps/agent/src/triavoz_agent/agent.py → apps/agent/src/triavoz_agent/api_client.py
- `test_web_handoff_records_callback_and_reports_fallback()` --uses--> `CallContext`  [INFERRED]
  apps/agent/tests/test_agent_units.py → apps/agent/src/triavoz_agent/agent.py
- `Receptionist` --uses--> `ApiError`  [INFERRED]
  apps/agent/src/triavoz_agent/agent.py → apps/agent/src/triavoz_agent/api_client.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-tenant Security Framework** — docs_adr_0003, docs_specs_01 [EXTRACTED 1.00]
- **Triavoz Application Stack** — api_service, agent_service, web_service, postgres_service, redis_service, livekit_service [EXTRACTED 1.00]
- **Voice AI Pipeline** — apps_agent, apps_api [EXTRACTED 1.00]
- **Security & Isolation Enforcement** — tenant_isolation, postgres_service, github_workflows_ci [INFERRED 0.90]

## Communities (85 total, 39 thin omitted)

### Community 0 - "entrypoint"
Cohesion: 0.21
Nodes (7): TriaVozApi, entrypoint(), add_turn(), on_item(), on_tools(), persist_turn(), trigger_handoff()

### Community 1 - "SchedulingRepository"
Cohesion: 0.09
Nodes (3): SchedulingRepository, ServiceInfo, ListServices

### Community 2 - "package.json"
Cohesion: 0.13
Nodes (14): name, private, version, livekit-client, @livekit/components-react, postcss, react, react-dom (+6 more)

### Community 3 - "PgSchedulingRepository"
Cohesion: 0.17
Nodes (4): _is_overlap(), PgSchedulingRepository, SlotTaken, raw_insert()

### Community 4 - "internal_agent.py"
Cohesion: 0.12
Nodes (26): tenant_session(), get_idempotency_store(), IdempotencyStore, add_turns(), AppointmentIn, _aware(), book(), BookIn (+18 more)

### Community 5 - "triavoz/config.py"
Cohesion: 0.06
Nodes (18): InMemoryRateLimiter, RedisRateLimiter, RedisTokenBucket, sign(), verify(), verify_internal_signature(), TokenBucket, future_monday() (+10 more)

### Community 6 - "Test Fixtures"
Cohesion: 0.07
Nodes (52): app_conn(), drop_clinic(), pytest_collection_modifyitems(), seed_clinic(), _set_ctx(), tenants(), _hash(), test_clinic_settings_defaults_and_kill_switch_are_tenant_scoped() (+44 more)

### Community 7 - "triavoz/main.py"
Cohesion: 0.13
Nodes (12): dispose_engine(), _body(), register_exception_handlers(), domain_error(), http_error(), unhandled(), health(), register_request_middleware() (+4 more)

### Community 8 - "Dashboard Pages"
Cohesion: 0.12
Nodes (16): Page(), Page(), Page(), Page(), Page(), Page(), Page(), Page() (+8 more)

### Community 9 - "AppShell.tsx"
Cohesion: 0.33
Nodes (7): AppLayout(), Landing(), AppShell(), NAV, LocaleSwitcher(), OPTIONS, next

### Community 11 - "TypeScript Configuration"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 12 - "ADR 0005 — Refresh tokens, per-clinic limits and transcript retention"
Cohesion: 0.40
Nodes (4): ADR 0005 — Refresh tokens, per-clinic limits and transcript retention, Decision, Rejected, Retention (design only; implementation is TODO P07/P09)

### Community 13 - "seed_demo.py"
Cohesion: 0.05
Nodes (26): main(), _synthesize(), _turns(), _wait_agent_turn(), _agent_config(), ClinicSeed, _dsn(), _id() (+18 more)

### Community 14 - "System Architecture"
Cohesion: 0.18
Nodes (11): Voice Agent Service, API Service (FastAPI), Docker Compose Configuration, Project Progress Board, Agent Rules and Conventions, TriaVoz Context (Single Source of Truth), CI Workflow, LiveKit Server (+3 more)

### Community 15 - "redis_events.py"
Cohesion: 0.13
Nodes (6): _channel(), get_event_bus(), NullEventBus, RedisEventBus, stream_events(), get_event_stream()

### Community 17 - "Voice Worker Specs"
Cohesion: 0.67
Nodes (3): TriaVoz Voice Worker (LiveKit), TriaVoz API (FastAPI), Spec 03: Voice Agent

### Community 27 - "StaffRepository"
Cohesion: 0.07
Nodes (16): StaffRepository, cancel_appointment(), create_appointment(), list_agenda(), move_appointment(), get_agent_config(), list_versions(), list_blocked() (+8 more)

### Community 40 - "StaffService"
Cohesion: 0.18
Nodes (7): StaffService, publish_version(), rollback_version(), save_draft(), generate_summary(), AgentConfigIn, ConfigVersionOut

### Community 45 - "PgStaffRepository"
Cohesion: 0.13
Nodes (5): _percentile(), PgStaffRepository, _row(), _rows(), Conflict

### Community 48 - "schemas.py"
Cohesion: 0.15
Nodes (18): AgentConfigSchema, AgentConfigStateOut, AppointmentCreate, AppointmentMove, AssignIn, CallDetailOut, CallEventOut, CallListOut (+10 more)

### Community 50 - "auth.py"
Cohesion: 0.07
Nodes (27): AuthRepository, PasswordHasher, RefreshRecord, UserRecord, AuthService, LoginResult, new_refresh_token(), parse_refresh_clinic() (+19 more)

### Community 51 - "dataclasses"
Cohesion: 0.14
Nodes (7): VoiceRoom, VoiceRoomService, VoiceSessionRepository, StartVoiceSession, VoiceSessionResult, LiveKitVoiceService, ServiceUnavailable

### Community 52 - "use_cases.py"
Cohesion: 0.20
Nodes (11): BookAppointment, CancelAppointment, CancelStaffAppointment, ListAvailableSlots, MoveStaffAppointment, RescheduleAppointment, Slot, _slots_for() (+3 more)

### Community 53 - "deps.py"
Cohesion: 0.12
Nodes (15): ClinicResolver, RateLimiter, EventPublisher, CallSummaryGenerator, get_limiter(), UnconfiguredCallSummaryGenerator, create_voice_session(), client_ip() (+7 more)

### Community 54 - "scheduling_repo.py"
Cohesion: 0.20
Nodes (11): ProfessionalInfo, free_slots(), Interval, WorkWindow, at(), test_busy_interval_blocks_overlapping_slots_only(), test_duration_longer_than_window_yields_nothing(), test_longer_service_only_fits_where_it_ends_before_the_busy_block() (+3 more)

### Community 55 - "session.py"
Cohesion: 0.12
Nodes (8): run_migrations_offline(), run_migrations_online(), _url(), RoutingClinicResolver, resolve_clinic_by_phone(), resolve_clinic_by_slug(), get_engine(), _session_factory()

### Community 56 - "Principal"
Cohesion: 0.19
Nodes (12): AccessTokenIssuer, decode_principal(), JwtAccessTokenIssuer, create_access_token(), decode_access_token(), Principal, TeamUserCreate, UserOut (+4 more)

### Community 57 - "triavoz_agent/main.py"
Cohesion: 0.14
Nodes (7): find_caller_identity(), SipHandoff, sip_transfer(), _livekit_http_url(), prewarm(), _today_label(), Handoff

### Community 58 - "test_scheduling_db.py"
Cohesion: 0.41
Nodes (9): _book(), local(), _slots(), test_booked_slot_disappears_and_cancel_brings_it_back(), test_booking_requires_an_offered_slot(), test_concurrent_bookings_of_the_same_slot_yield_exactly_one_winner(), test_db_constraint_rejects_overlap_even_if_the_use_case_is_bypassed(), test_reschedule_moves_the_booking_and_refuses_taken_or_invalid_times() (+1 more)

### Community 60 - "dependencies"
Cohesion: 0.20
Nodes (10): dependencies, clsx, livekit-client, @livekit/components-react, lucide-react, next, next-intl, react (+2 more)

### Community 61 - "next-intl"
Cohesion: 0.22
Nodes (4): nextConfig, securityHeaders, withNextIntl, next-intl

### Community 62 - "devDependencies"
Cohesion: 0.25
Nodes (8): devDependencies, postcss, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom, typescript

### Community 63 - "StatusBadge.tsx"
Cohesion: 0.33
Nodes (4): RequestStatus, STYLES, clsx, lucide-react

### Community 65 - "scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, start, typecheck

### Community 66 - "ADR 0006 — Auth cookies, rotation and SSE"
Cohesion: 0.40
Nodes (4): ADR 0006 — Auth cookies, rotation and SSE, Context, Decision, Rejected

### Community 68 - "request.ts"
Cohesion: 0.50
Nodes (3): defaultLocale, Locale, locales

### Community 69 - "ui.ts"
Cohesion: 0.50
Nodes (3): UiState, useUi, zustand

### Community 75 - "test_agent_units.py"
Cohesion: 0.23
Nodes (6): sign(), _client(), test_api_errors_expose_a_stable_code(), test_requests_are_signed_and_carry_server_side_ids(), handler(), test_web_handoff_records_callback_and_reports_fallback()

### Community 76 - "agenda.py"
Cohesion: 0.23
Nodes (5): current_principal(), _extract_token(), get_auth_repo(), get_staff_repo(), tenant_db()

### Community 77 - "telemetry.py"
Cohesion: 0.24
Nodes (5): LatencyTracker, percentile(), TurnLatencyTracker, test_percentiles_and_latency_summary(), test_turn_latency_computes_time_to_first_audio()

### Community 79 - "requests.py"
Cohesion: 0.44
Nodes (6): assign_request(), complete_request(), mark_spam(), patch_request(), RequestDetailOut, RequestOut

### Community 80 - "blocked.py"
Cohesion: 0.31
Nodes (4): add_blocked(), delete_blocked(), BlockedCreate, BlockedOut

### Community 81 - "triavoz_agent/config.py"
Cohesion: 0.32
Nodes (4): _f(), WorkerConfig, estimate_cost_cents(), test_cost_estimate_uses_configured_prices_only()

### Community 82 - "prompts.py"
Cohesion: 0.48
Nodes (4): build_greeting_instructions(), build_instructions(), greeting_text(), test_instructions_contain_the_non_negotiable_rules()

### Community 83 - "ADR 0007 — Live voice pipeline, turn tuning, turn persistence and handoff"
Cohesion: 0.29
Nodes (6): ADR 0007 — Live voice pipeline, turn tuning, turn persistence and handoff, Known limitations, Latency target and measurements, Persistence, Providers actually used, Turn handling (measured profile)

### Community 84 - "redact_tool_arguments"
Cohesion: 0.50
Nodes (3): _redact(), redact_tool_arguments(), test_redaction_removes_patient_identifiers()

## Knowledge Gaps
- **30 isolated node(s):** `triavoz-agent`, `triavoz-api`, `@livekit/components-react`, `livekit-client`, `react` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 311 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PgStaffRepository` connect `PgStaffRepository` to `internal_agent.py`, `use_cases.py`, `deps.py`, `agenda.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `StaffRepository` (e.g. with `StaffService` and `cancel_appointment()`) actually correct?**
  _`StaffRepository` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `triavoz-agent`, `triavoz-api`, `@livekit/components-react` to the rest of the system?**
  _30 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SchedulingRepository` be split into smaller, more focused modules?**
  _Cohesion score 0.0946969696969697 - nodes in this community are weakly interconnected._
- **Why does `StaffRepository` connect `StaffRepository` to `StaffService`, `agenda.py`, `seed_demo.py`, `requests.py`, `schemas.py`, `blocked.py`, `deps.py`, `Principal`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `Principal` (e.g. with `AccessTokenIssuer` and `AuthService`) actually correct?**
  _`Principal` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Should `package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._