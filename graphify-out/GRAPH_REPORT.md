# Graph Report - Triavoz  (2026-10-19)

## Corpus Check
- 107 files · ~22,117 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 18 file(s) not represented in the graph (top: (none) 13, .example 2, .ini 1)

## Summary
- 603 nodes · 1262 edges · 46 communities (15 shown, 31 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 106 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `50a4472f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Voice Agent Entrypoint
- Scheduling Repository
- Frontend Dependencies
- PgSchedulingRepository
- Call History Persistence
- Configuration and Security
- Test Fixtures
- Database Migrations
- Dashboard Pages
- Next.js App Layout
- Agent Tool Definitions
- TypeScript Configuration
- ADR 0005 — Refresh tokens, per-clinic limits and transcript retention
- seed_demo.py
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
- Scheduling Specs
- Abuse Protection Specs
- Agent Service
- API Service
- Redis Infrastructure
- Web Frontend

## God Nodes (most connected - your core abstractions)
1. `PgSchedulingRepository` - 34 edges
2. `SchedulingRepository` - 30 edges
3. `PagePlaceholder()` - 29 edges
4. `app_conn()` - 23 edges
5. `tenant_session()` - 22 edges
6. `NotFound` - 21 edges
7. `entrypoint()` - 20 edges
8. `compilerOptions` - 17 edges
9. `free_slots()` - 16 edges
10. `_slots_for()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `API Service (FastAPI)` --references--> `Tenant Isolation Policy`  [INFERRED]
  docker-compose.yml → docs/agent/RULES.md
- `Receptionist` --uses--> `ApiError`  [INFERRED]
  apps/agent/src/triavoz_agent/agent.py → apps/agent/src/triavoz_agent/api_client.py
- `_slots_for()` --uses--> `ServiceInfo`  [INFERRED]
  apps/api/src/triavoz/application/scheduling/use_cases.py → apps/api/src/triavoz/application/scheduling/ports.py
- `PgSchedulingRepository` --uses--> `ServiceInfo`  [INFERRED]
  apps/api/src/triavoz/infrastructure/db/scheduling_repo.py → apps/api/src/triavoz/application/scheduling/ports.py
- `PgSchedulingRepository` --uses--> `AppointmentView`  [INFERRED]
  apps/api/src/triavoz/infrastructure/db/scheduling_repo.py → apps/api/src/triavoz/application/scheduling/ports.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-tenant Security Framework** — docs_adr_0003, docs_specs_01 [EXTRACTED 1.00]
- **Triavoz Application Stack** — api_service, agent_service, web_service, postgres_service, redis_service, livekit_service [EXTRACTED 1.00]
- **Voice AI Pipeline** — apps_agent, apps_api [EXTRACTED 1.00]
- **Security & Isolation Enforcement** — tenant_isolation, postgres_service, github_workflows_ci [INFERRED 0.90]

## Communities (46 total, 31 thin omitted)

### Community 0 - "Voice Agent Entrypoint"
Cohesion: 0.06
Nodes (19): CallContext, ApiError, sign(), TriaVozApi, _f(), WorkerConfig, entrypoint(), prewarm() (+11 more)

### Community 1 - "Scheduling Repository"
Cohesion: 0.07
Nodes (15): AppointmentView, SchedulingRepository, ServiceInfo, ListMyAppointments, ListServices, free_slots(), Interval, WorkWindow (+7 more)

### Community 2 - "Frontend Dependencies"
Cohesion: 0.04
Nodes (44): dependencies, clsx, livekit-client, @livekit/components-react, lucide-react, next, next-intl, react (+36 more)

### Community 3 - "PgSchedulingRepository"
Cohesion: 0.13
Nodes (13): ProfessionalInfo, _is_overlap(), PgSchedulingRepository, _book(), local(), _slots(), test_booked_slot_disappears_and_cancel_brings_it_back(), test_booking_requires_an_offered_slot() (+5 more)

### Community 4 - "Call History Persistence"
Cohesion: 0.09
Nodes (32): BookAppointment, CancelAppointment, ListAvailableSlots, RescheduleAppointment, Slot, _slots_for(), PgCallRepository, tenant_session() (+24 more)

### Community 5 - "Configuration and Security"
Cohesion: 0.08
Nodes (21): get_settings(), Settings, sign(), verify(), create_access_token(), decode_access_token(), Principal, verify_internal_signature() (+13 more)

### Community 6 - "Test Fixtures"
Cohesion: 0.10
Nodes (28): app_conn(), drop_clinic(), pytest_collection_modifyitems(), seed_clinic(), _set_ctx(), tenants(), _hash(), test_clinic_settings_defaults_and_kill_switch_are_tenant_scoped() (+20 more)

### Community 7 - "Database Migrations"
Cohesion: 0.07
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

### Community 12 - "ADR 0005 — Refresh tokens, per-clinic limits and transcript retention"
Cohesion: 0.40
Nodes (4): ADR 0005 — Refresh tokens, per-clinic limits and transcript retention, Decision, Rejected, Retention (design only; implementation is TODO P07/P09)

### Community 13 - "seed_demo.py"
Cohesion: 0.10
Nodes (17): _agent_config(), ClinicSeed, _dsn(), _id(), main(), ProfessionalSeed, _seed_clinic(), ServiceSeed (+9 more)

### Community 14 - "System Architecture"
Cohesion: 0.18
Nodes (11): Voice Agent Service, API Service (FastAPI), Docker Compose Configuration, Project Progress Board, Agent Rules and Conventions, TriaVoz Context (Single Source of Truth), CI Workflow, LiveKit Server (+3 more)

### Community 17 - "Voice Worker Specs"
Cohesion: 0.67
Nodes (3): TriaVoz Voice Worker (LiveKit), TriaVoz API (FastAPI), Spec 03: Voice Agent

## Knowledge Gaps
- **30 isolated node(s):** `triavoz-agent`, `triavoz-api`, `@livekit/components-react`, `livekit-client`, `react` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 218 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Receptionist` connect `Agent Tool Definitions` to `Voice Agent Entrypoint`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `PgSchedulingRepository` (e.g. with `AppointmentView` and `ProfessionalInfo`) actually correct?**
  _`PgSchedulingRepository` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `triavoz-agent`, `triavoz-api`, `@livekit/components-react` to the rest of the system?**
  _30 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Voice Agent Entrypoint` be split into smaller, more focused modules?**
  _Cohesion score 0.06060606060606061 - nodes in this community are weakly interconnected._
- **Why does `entrypoint()` connect `Voice Agent Entrypoint` to `Agent Tool Definitions`, `Configuration and Security`, `seed_demo.py`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SchedulingRepository` (e.g. with `Interval` and `WorkWindow`) actually correct?**
  _`SchedulingRepository` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `Scheduling Repository` be split into smaller, more focused modules?**
  _Cohesion score 0.07017543859649122 - nodes in this community are weakly interconnected._