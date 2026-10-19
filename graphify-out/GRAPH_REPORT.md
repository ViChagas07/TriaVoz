# Graph Report - Triavoz  (2026-10-19)

## Corpus Check
- 151 files · ~35,175 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 18 file(s) not represented in the graph (top: (none) 13, .example 2, .ini 1)

## Summary
- 1090 nodes · 2906 edges · 75 communities (38 shown, 37 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 370 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f8771d89`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Voice Agent Entrypoint
- SchedulingRepository
- package.json
- PgSchedulingRepository
- internal_agent.py
- test_staff_api.py
- Test Fixtures
- triavoz/main.py
- Dashboard Pages
- AppShell.tsx
- Agent Tool Definitions
- TypeScript Configuration
- ADR 0005 — Refresh tokens, per-clinic limits and transcript retention
- seed_demo.py
- System Architecture
- triavoz/config.py
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
- NotFound
- Scheduling Specs
- Abuse Protection Specs
- Agent Service
- API Service
- PgStaffRepository
- Redis Infrastructure
- Web Frontend
- schemas.py
- PgAuthRepository
- auth/service.py
- dataclasses
- use_cases.py
- deps.py
- scheduling_repo.py
- auth.py
- Principal
- api_v1/agent_config.py
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

## God Nodes (most connected - your core abstractions)
1. `StaffRepository` - 62 edges
2. `Principal` - 49 edges
3. `NotFound` - 44 edges
4. `StaffService` - 40 edges
5. `PgSchedulingRepository` - 39 edges
6. `PgStaffRepository` - 39 edges
7. `get_settings()` - 36 edges
8. `SchedulingRepository` - 35 edges
9. `tenant_session()` - 32 edges
10. `PagePlaceholder()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `API Service (FastAPI)` --references--> `Tenant Isolation Policy`  [INFERRED]
  docker-compose.yml → docs/agent/RULES.md
- `Receptionist` --uses--> `ApiError`  [INFERRED]
  apps/agent/src/triavoz_agent/agent.py → apps/agent/src/triavoz_agent/api_client.py
- `LoginResult` --uses--> `UserRecord`  [INFERRED]
  apps/api/src/triavoz/application/auth/service.py → apps/api/src/triavoz/application/auth/ports.py
- `RefreshResult` --uses--> `UserRecord`  [INFERRED]
  apps/api/src/triavoz/application/auth/service.py → apps/api/src/triavoz/application/auth/ports.py
- `login()` --uses--> `AuthRepository`  [INFERRED]
  apps/api/src/triavoz/interfaces/http/api_v1/auth.py → apps/api/src/triavoz/application/auth/ports.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-tenant Security Framework** — docs_adr_0003, docs_specs_01 [EXTRACTED 1.00]
- **Triavoz Application Stack** — api_service, agent_service, web_service, postgres_service, redis_service, livekit_service [EXTRACTED 1.00]
- **Voice AI Pipeline** — apps_agent, apps_api [EXTRACTED 1.00]
- **Security & Isolation Enforcement** — tenant_isolation, postgres_service, github_workflows_ci [INFERRED 0.90]

## Communities (75 total, 37 thin omitted)

### Community 0 - "Voice Agent Entrypoint"
Cohesion: 0.06
Nodes (20): CallContext, ApiError, sign(), TriaVozApi, _f(), WorkerConfig, entrypoint(), prewarm() (+12 more)

### Community 1 - "SchedulingRepository"
Cohesion: 0.10
Nodes (4): SchedulingRepository, ServiceInfo, CancelAppointment, ListServices

### Community 2 - "package.json"
Cohesion: 0.13
Nodes (14): name, private, version, livekit-client, @livekit/components-react, postcss, react, react-dom (+6 more)

### Community 3 - "PgSchedulingRepository"
Cohesion: 0.17
Nodes (5): ProfessionalInfo, _is_overlap(), PgSchedulingRepository, SlotTaken, raw_insert()

### Community 4 - "internal_agent.py"
Cohesion: 0.11
Nodes (26): _session_factory(), tenant_session(), IdempotencyStore, add_turns(), AppointmentIn, _aware(), book(), BookIn (+18 more)

### Community 5 - "test_staff_api.py"
Cohesion: 0.09
Nodes (36): sign(), verify(), verify_internal_signature(), future_monday(), client(), _post(), _signed(), test_full_voice_booking_flow_over_http() (+28 more)

### Community 6 - "Test Fixtures"
Cohesion: 0.10
Nodes (28): app_conn(), drop_clinic(), pytest_collection_modifyitems(), seed_clinic(), _set_ctx(), tenants(), _hash(), test_clinic_settings_defaults_and_kill_switch_are_tenant_scoped() (+20 more)

### Community 7 - "triavoz/main.py"
Cohesion: 0.08
Nodes (15): RoutingClinicResolver, resolve_clinic_by_phone(), resolve_clinic_by_slug(), dispose_engine(), get_engine(), _body(), register_exception_handlers(), domain_error() (+7 more)

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
Cohesion: 0.07
Nodes (18): _agent_config(), ClinicSeed, _dsn(), _id(), main(), ProfessionalSeed, _seed_clinic(), ServiceSeed (+10 more)

### Community 14 - "System Architecture"
Cohesion: 0.18
Nodes (11): Voice Agent Service, API Service (FastAPI), Docker Compose Configuration, Project Progress Board, Agent Rules and Conventions, TriaVoz Context (Single Source of Truth), CI Workflow, LiveKit Server (+3 more)

### Community 15 - "triavoz/config.py"
Cohesion: 0.06
Nodes (13): Settings, _channel(), get_event_bus(), NullEventBus, RedisEventBus, get_idempotency_store(), InMemoryRateLimiter, RedisRateLimiter (+5 more)

### Community 17 - "Voice Worker Specs"
Cohesion: 0.67
Nodes (3): TriaVoz Voice Worker (LiveKit), TriaVoz API (FastAPI), Spec 03: Voice Agent

### Community 27 - "StaffRepository"
Cohesion: 0.06
Nodes (19): EventPublisher, CallSummaryGenerator, StaffRepository, cancel_appointment(), create_appointment(), list_agenda(), move_appointment(), get_agent_config() (+11 more)

### Community 40 - "NotFound"
Cohesion: 0.10
Nodes (17): StaffService, delete_blocked(), generate_summary(), list_calls(), assign_request(), complete_request(), get_request(), list_requests() (+9 more)

### Community 45 - "PgStaffRepository"
Cohesion: 0.13
Nodes (5): _percentile(), PgStaffRepository, _row(), _rows(), Conflict

### Community 48 - "schemas.py"
Cohesion: 0.12
Nodes (24): add_blocked(), AgentConfigStateOut, AssignIn, BlockedCreate, BlockedOut, CallDetailOut, CallEventOut, CallListOut (+16 more)

### Community 49 - "PgAuthRepository"
Cohesion: 0.10
Nodes (8): run_migrations_offline(), run_migrations_online(), _url(), RefreshRecord, UserRecord, PgAuthRepository, _user(), PgVoiceSessionRepository

### Community 50 - "auth/service.py"
Cohesion: 0.14
Nodes (9): AuthRepository, AuthService, LoginResult, new_refresh_token(), refresh_hash(), RefreshRejected, me(), AuthenticationError (+1 more)

### Community 51 - "dataclasses"
Cohesion: 0.11
Nodes (9): VoiceRoom, VoiceRoomService, VoiceSessionRepository, room_metadata_json(), StartVoiceSession, VoiceSessionResult, LiveKitVoiceService, ServiceUnavailable (+1 more)

### Community 52 - "use_cases.py"
Cohesion: 0.15
Nodes (11): BookAppointment, CancelStaffAppointment, ListAvailableSlots, MoveStaffAppointment, RescheduleAppointment, Slot, _slots_for(), Forbidden (+3 more)

### Community 53 - "deps.py"
Cohesion: 0.14
Nodes (12): AccessTokenIssuer, ClinicResolver, PasswordHasher, RateLimiter, get_limiter(), create_voice_session(), get_auth_repo(), get_clinic_resolver() (+4 more)

### Community 54 - "scheduling_repo.py"
Cohesion: 0.19
Nodes (10): free_slots(), Interval, WorkWindow, at(), test_busy_interval_blocks_overlapping_slots_only(), test_duration_longer_than_window_yields_nothing(), test_longer_service_only_fits_where_it_ends_before_the_busy_block(), test_naive_now_is_rejected() (+2 more)

### Community 55 - "auth.py"
Cohesion: 0.26
Nodes (13): parse_refresh_clinic(), RefreshResult, get_settings(), login(), logout(), refresh(), _user_out(), clear_auth_cookies() (+5 more)

### Community 56 - "Principal"
Cohesion: 0.28
Nodes (8): decode_principal(), JwtAccessTokenIssuer, create_access_token(), decode_access_token(), Principal, current_principal(), _extract_token(), test_access_token_roundtrip_and_rejects_garbage()

### Community 57 - "api_v1/agent_config.py"
Cohesion: 0.20
Nodes (6): AgentConfigSchema, publish_version(), rollback_version(), save_draft(), AgentConfigIn, ConfigVersionOut

### Community 58 - "test_scheduling_db.py"
Cohesion: 0.42
Nodes (8): _book(), local(), _slots(), test_booked_slot_disappears_and_cancel_brings_it_back(), test_booking_requires_an_offered_slot(), test_concurrent_bookings_of_the_same_slot_yield_exactly_one_winner(), test_db_constraint_rejects_overlap_even_if_the_use_case_is_bypassed(), test_reschedule_moves_the_booking_and_refuses_taken_or_invalid_times()

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

## Knowledge Gaps
- **30 isolated node(s):** `triavoz-agent`, `triavoz-api`, `@livekit/components-react`, `livekit-client`, `react` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 295 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `StaffRepository` connect `StaffRepository` to `NotFound`, `api_v1/agent_config.py`, `schemas.py`, `deps.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `StaffRepository` (e.g. with `StaffService` and `cancel_appointment()`) actually correct?**
  _`StaffRepository` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `triavoz-agent`, `triavoz-api`, `@livekit/components-react` to the rest of the system?**
  _30 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Voice Agent Entrypoint` be split into smaller, more focused modules?**
  _Cohesion score 0.0574400723654455 - nodes in this community are weakly interconnected._
- **Why does `PgStaffRepository` connect `PgStaffRepository` to `NotFound`, `schemas.py`, `internal_agent.py`, `deps.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `Principal` (e.g. with `AccessTokenIssuer` and `AuthService`) actually correct?**
  _`Principal` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Should `SchedulingRepository` be split into smaller, more focused modules?**
  _Cohesion score 0.10080645161290322 - nodes in this community are weakly interconnected._