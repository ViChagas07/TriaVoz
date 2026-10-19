# Graph Report - Triavoz  (2026-10-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 560 nodes · 1156 edges · 48 communities (15 shown, 33 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 106 edges (avg confidence: 0.93)
- Token cost: 1,572 input · 504 output

## Community Hubs (Navigation)
- Voice Agent Entrypoint
- Scheduling Repository
- Frontend Dependencies
- Slot Computation Logic
- Call History Persistence
- Configuration and Security
- Test Fixtures
- Database Migrations
- Dashboard Pages
- Next.js App Layout
- Agent Tool Definitions
- TypeScript Configuration
- API Integration Tests
- Database Integration Tests
- System Architecture
- Redis Rate Limiting
- Frontend API Client
- Voice Worker Specs
- Documentation Tools
- PostCSS Configuration
- Multi-tenancy Specs
- Database Role Scripts
- Dashboard Overview
- Security Baseline ADR
- Voice Pipeline ADR
- Booking Integrity ADR
- Project Context
- Scheduling Specs
- Abuse Protection Specs
- Agent Service
- API Service
- Project Documentation
- Redis Infrastructure
- Web Frontend

## God Nodes (most connected - your core abstractions)
1. `PgSchedulingRepository` - 34 edges
2. `SchedulingRepository` - 30 edges
3. `PagePlaceholder()` - 29 edges
4. `tenant_session()` - 22 edges
5. `NotFound` - 21 edges
6. `entrypoint()` - 20 edges
7. `compilerOptions` - 17 edges
8. `free_slots()` - 16 edges
9. `PgCallRepository` - 15 edges
10. `_slots_for()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `API Service (FastAPI)` --references--> `Tenant Isolation Policy`  [INFERRED]
  docker-compose.yml → docs/agent/RULES.md
- `Receptionist` --uses--> `ApiError`  [INFERRED]
  apps/agent/src/triavoz_agent/agent.py → apps/agent/src/triavoz_agent/api_client.py
- `SchedulingRepository` --uses--> `Interval`  [INFERRED]
  apps/api/src/triavoz/application/scheduling/ports.py → apps/api/src/triavoz/domain/scheduling/slots.py
- `SchedulingRepository` --uses--> `WorkWindow`  [INFERRED]
  apps/api/src/triavoz/application/scheduling/ports.py → apps/api/src/triavoz/domain/scheduling/slots.py
- `PgSchedulingRepository` --uses--> `ServiceInfo`  [INFERRED]
  apps/api/src/triavoz/infrastructure/db/scheduling_repo.py → apps/api/src/triavoz/application/scheduling/ports.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-tenant Security Framework** — docs_adr_0003, docs_specs_01 [EXTRACTED 1.00]
- **Triavoz Application Stack** — api_service, agent_service, web_service, postgres_service, redis_service, livekit_service [EXTRACTED 1.00]
- **Voice AI Pipeline** — apps_agent, apps_api [EXTRACTED 1.00]
- **Security & Isolation Enforcement** — tenant_isolation, postgres_service, github_workflows_ci [INFERRED 0.90]

## Communities (48 total, 33 thin omitted)

### Community 0 - "Voice Agent Entrypoint"
Cohesion: 0.06
Nodes (19): CallContext, ApiError, sign(), TriaVozApi, _f(), WorkerConfig, entrypoint(), prewarm() (+11 more)

### Community 1 - "Scheduling Repository"
Cohesion: 0.08
Nodes (13): SchedulingRepository, ServiceInfo, BookAppointment, CancelAppointment, ListAvailableSlots, ListMyAppointments, ListServices, RescheduleAppointment (+5 more)

### Community 2 - "Frontend Dependencies"
Cohesion: 0.04
Nodes (44): dependencies, clsx, livekit-client, @livekit/components-react, lucide-react, next, next-intl, react (+36 more)

### Community 3 - "Slot Computation Logic"
Cohesion: 0.10
Nodes (15): AppointmentView, ProfessionalInfo, free_slots(), Interval, WorkWindow, _is_overlap(), PgSchedulingRepository, SlotTaken (+7 more)

### Community 4 - "Call History Persistence"
Cohesion: 0.11
Nodes (23): PgCallRepository, tenant_session(), add_turns(), AppointmentIn, _aware(), book(), BookIn, cancel() (+15 more)

### Community 5 - "Configuration and Security"
Cohesion: 0.08
Nodes (16): get_settings(), Settings, sign(), verify(), hash_password(), verify_password(), create_access_token(), decode_access_token() (+8 more)

### Community 6 - "Test Fixtures"
Cohesion: 0.13
Nodes (20): app_conn(), drop_clinic(), pytest_collection_modifyitems(), seed_clinic(), _set_ctx(), tenants(), test_every_tenant_table_has_enabled_and_forced_rls_with_a_policy(), _tenant_tables() (+12 more)

### Community 7 - "Database Migrations"
Cohesion: 0.08
Nodes (11): run_migrations_offline(), run_migrations_online(), _url(), resolve_clinic_by_phone(), resolve_clinic_by_slug(), dispose_engine(), get_engine(), _session_factory() (+3 more)

### Community 8 - "Dashboard Pages"
Cohesion: 0.12
Nodes (16): Page(), Page(), Page(), Page(), Page(), Page(), Page(), Page() (+8 more)

### Community 9 - "Next.js App Layout"
Cohesion: 0.11
Nodes (15): nextConfig, securityHeaders, withNextIntl, AppLayout(), metadata, Landing(), AppShell(), NAV (+7 more)

### Community 11 - "TypeScript Configuration"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 12 - "API Integration Tests"
Cohesion: 0.28
Nodes (8): future_monday(), client(), _post(), _signed(), test_full_voice_booking_flow_over_http(), test_health_is_public(), test_internal_routes_reject_missing_or_bad_signature(), test_naive_datetimes_are_rejected()

### Community 13 - "Database Integration Tests"
Cohesion: 0.37
Nodes (9): _book(), local(), _slots(), test_booked_slot_disappears_and_cancel_brings_it_back(), test_booking_requires_an_offered_slot(), test_concurrent_bookings_of_the_same_slot_yield_exactly_one_winner(), test_db_constraint_rejects_overlap_even_if_the_use_case_is_bypassed(), raw_insert() (+1 more)

### Community 14 - "System Architecture"
Cohesion: 0.22
Nodes (9): Voice Agent Service, API Service (FastAPI), Docker Compose Configuration, Project Progress Board, Agent Rules and Conventions, CI Workflow, LiveKit Server, PostgreSQL Service (+1 more)

### Community 17 - "Voice Worker Specs"
Cohesion: 0.67
Nodes (3): TriaVoz Voice Worker (LiveKit), TriaVoz API (FastAPI), Spec 03: Voice Agent

## Knowledge Gaps
- **32 isolated node(s):** `livekit-client`, `@livekit/components-react`, `postcss`, `react`, `react-dom` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 209 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Receptionist` connect `Agent Tool Definitions` to `Voice Agent Entrypoint`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `PgSchedulingRepository` (e.g. with `AppointmentView` and `ProfessionalInfo`) actually correct?**
  _`PgSchedulingRepository` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `livekit-client`, `@livekit/components-react`, `postcss` to the rest of the system?**
  _32 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Voice Agent Entrypoint` be split into smaller, more focused modules?**
  _Cohesion score 0.06060606060606061 - nodes in this community are weakly interconnected._
- **Why does `PgSchedulingRepository` connect `Slot Computation Logic` to `Scheduling Repository`, `Call History Persistence`, `Database Integration Tests`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SchedulingRepository` (e.g. with `Interval` and `WorkWindow`) actually correct?**
  _`SchedulingRepository` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `Scheduling Repository` be split into smaller, more focused modules?**
  _Cohesion score 0.08455625436757512 - nodes in this community are weakly interconnected._