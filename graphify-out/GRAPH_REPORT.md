# Graph Report - Triavoz  (2026-10-21)

## Corpus Check
- 181 files · ~52,086 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 18 file(s) not represented in the graph (top: (none) 13, .example 2, .ini 1)

## Summary
- 1507 nodes · 4116 edges · 110 communities (64 shown, 46 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 565 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b8012733`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- entrypoint
- SchedulingRepository
- package.json
- PgSchedulingRepository
- EventPublisher
- test_abuse_flow.py
- Test Fixtures
- triavoz/main.py
- Dashboard Pages
- next-intl
- Agent Tool Definitions
- TypeScript Configuration
- ADR 0005 — Refresh tokens, per-clinic limits and transcript retention
- seed_demo.py
- System Architecture
- deps.py
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
- time
- auth/service.py
- CircuitBreaker
- use_cases.py
- get_settings
- scheduling_repo.py
- routing.py
- shared_kernel/errors.py
- triavoz_agent/main.py
- test_scheduling_db.py
- triavoz/config.py
- dependencies
- next.config.ts
- devDependencies
- typing
- AppointmentView
- scripts
- ADR 0006 — Auth cookies, rotation and SSE
- test_gatekeeper.py
- score_call
- ui.ts
- test_agent_units.py
- agenda.py
- telemetry.py
- calls.py
- voice.py
- internal_agent.py
- test_agent_units.py
- prompts.py
- stream_events
- redact_tool_arguments
- replay_guard.py
- breaker.py
- auth/ports.py
- agenda.py
- entrypoint
- Gatekeeper
- abuse/policy.py
- GateStore
- asyncio
- Principal
- blocked.py
- voice_smoke.py
- PgAbuseRepository
- PgCallRepository
- PasswordHasher
- tenant_session
- AlertService
- test_alerts.py
- verify_rls_mutations.py
- json
- sqlalchemy
- ServiceInfo
- end_call

## God Nodes (most connected - your core abstractions)
1. `StaffRepository` - 62 edges
2. `get_settings()` - 51 edges
3. `Principal` - 50 edges
4. `NotFound` - 45 edges
5. `StaffService` - 44 edges
6. `entrypoint()` - 42 edges
7. `PgSchedulingRepository` - 40 edges
8. `PgStaffRepository` - 39 edges
9. `SchedulingRepository` - 35 edges
10. `tenant_session()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `Handoff` --references--> `SipHandoff`  [INFERRED]
  docs/adr/0007-voice-pipeline-turns-handoff.md → apps/agent/src/triavoz_agent/handoff.py
- `P04.1 quality pass` --references--> `HandoffPolicy`  [INFERRED]
  docs/adr/0007-voice-pipeline-turns-handoff.md → apps/agent/src/triavoz_agent/policy.py
- `1. Gatekeeper before any spend` --references--> `StartVoiceSession`  [INFERRED]
  docs/adr/0008-abuse-and-cost-protection.md → apps/api/src/triavoz/application/voice/service.py
- `1. Gatekeeper before any spend` --references--> `Gatekeeper`  [INFERRED]
  docs/adr/0008-abuse-and-cost-protection.md → apps/api/src/triavoz/application/abuse/gatekeeper.py
- `1. Gatekeeper before any spend` --references--> `GateDecision`  [INFERRED]
  docs/adr/0008-abuse-and-cost-protection.md → apps/api/src/triavoz/application/abuse/policy.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-tenant Security Framework** — docs_adr_0003, docs_specs_01 [EXTRACTED 1.00]
- **Triavoz Application Stack** — api_service, agent_service, web_service, postgres_service, redis_service, livekit_service [EXTRACTED 1.00]
- **Voice AI Pipeline** — apps_agent, apps_api [EXTRACTED 1.00]
- **Security & Isolation Enforcement** — tenant_isolation, postgres_service, github_workflows_ci [INFERRED 0.90]

## Communities (110 total, 46 thin omitted)

### Community 2 - "package.json"
Cohesion: 0.10
Nodes (18): name, private, version, RequestStatus, STYLES, clsx, livekit-client, @livekit/components-react (+10 more)

### Community 3 - "PgSchedulingRepository"
Cohesion: 0.18
Nodes (3): _is_overlap(), PgSchedulingRepository, SlotTaken

### Community 4 - "EventPublisher"
Cohesion: 0.21
Nodes (8): EventPublisher, IdempotencyStore, book(), cancel(), create_service_request(), _http(), _idem_key(), reschedule()

### Community 5 - "test_abuse_flow.py"
Cohesion: 0.06
Nodes (27): concurrent_key(), InMemoryGateStore, RedisGateStore, get_limiter(), InMemoryRateLimiter, RedisRateLimiter, RedisTokenBucket, get_limiter_dep() (+19 more)

### Community 6 - "Test Fixtures"
Cohesion: 0.06
Nodes (60): app_conn(), drop_clinic(), future_monday(), pytest_collection_modifyitems(), seed_clinic(), _set_ctx(), tenants(), _hash() (+52 more)

### Community 7 - "triavoz/main.py"
Cohesion: 0.14
Nodes (11): dispose_engine(), _body(), register_exception_handlers(), domain_error(), http_error(), unhandled(), health(), register_request_middleware() (+3 more)

### Community 8 - "Dashboard Pages"
Cohesion: 0.12
Nodes (16): Page(), Page(), Page(), Page(), Page(), Page(), Page(), Page() (+8 more)

### Community 9 - "next-intl"
Cohesion: 0.13
Nodes (12): AppLayout(), metadata, Landing(), AppShell(), NAV, LocaleSwitcher(), OPTIONS, defaultLocale (+4 more)

### Community 10 - "Agent Tool Definitions"
Cohesion: 0.12
Nodes (10): Receptionist, ADR 0007 — Live voice pipeline, turn tuning, turn persistence and handoff, Handoff, Known limitations, Latency target and measurements, P04.1 quality pass, Persistence, Providers actually used (+2 more)

### Community 11 - "TypeScript Configuration"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 12 - "ADR 0005 — Refresh tokens, per-clinic limits and transcript retention"
Cohesion: 0.40
Nodes (4): ADR 0005 — Refresh tokens, per-clinic limits and transcript retention, Decision, Rejected, Retention (design only; implementation is TODO P07/P09)

### Community 13 - "seed_demo.py"
Cohesion: 0.23
Nodes (9): _agent_config(), ClinicSeed, _dsn(), _id(), main(), ProfessionalSeed, _seed_clinic(), ServiceSeed (+1 more)

### Community 14 - "System Architecture"
Cohesion: 0.18
Nodes (11): Voice Agent Service, API Service (FastAPI), Docker Compose Configuration, Project Progress Board, Agent Rules and Conventions, TriaVoz Context (Single Source of Truth), CI Workflow, LiveKit Server (+3 more)

### Community 15 - "deps.py"
Cohesion: 0.10
Nodes (11): _channel(), get_event_bus(), NullEventBus, RedisEventBus, UnconfiguredCallSummaryGenerator, current_principal(), _extract_token(), get_auth_repo() (+3 more)

### Community 17 - "Voice Worker Specs"
Cohesion: 0.67
Nodes (3): TriaVoz Voice Worker (LiveKit), TriaVoz API (FastAPI), Spec 03: Voice Agent

### Community 27 - "StaffRepository"
Cohesion: 0.13
Nodes (3): StaffRepository, dashboard(), get_request()

### Community 45 - "PgStaffRepository"
Cohesion: 0.13
Nodes (5): _percentile(), PgStaffRepository, _row(), _rows(), Conflict

### Community 48 - "schemas.py"
Cohesion: 0.13
Nodes (19): AgentConfigSchema, assign_request(), complete_request(), list_requests(), mark_spam(), patch_request(), AgentConfigStateOut, AssignIn (+11 more)

### Community 49 - "time"
Cohesion: 0.13
Nodes (11): Argon2PasswordHasher, decode_principal(), JwtAccessTokenIssuer, hash_password(), verify_password(), create_access_token(), decode_access_token(), test_access_token_roundtrip_and_rejects_garbage() (+3 more)

### Community 50 - "auth/service.py"
Cohesion: 0.18
Nodes (7): AuthRepository, AuthService, LoginResult, new_refresh_token(), refresh_hash(), RefreshResult, TooManyAttempts

### Community 51 - "CircuitBreaker"
Cohesion: 0.06
Nodes (21): VoiceRoom, VoiceRoomService, ResilientVoiceRoomService, TurnstileVerifier, LiveKitVoiceService, get_voice_room_service(), Bulkhead, BulkheadFullError (+13 more)

### Community 52 - "use_cases.py"
Cohesion: 0.22
Nodes (10): BookAppointment, CancelAppointment, CancelStaffAppointment, ListAvailableSlots, MoveStaffAppointment, RescheduleAppointment, Slot, _slots_for() (+2 more)

### Community 53 - "get_settings"
Cohesion: 0.20
Nodes (15): parse_refresh_clinic(), RefreshRejected, get_settings(), login(), logout(), me(), refresh(), _user_out() (+7 more)

### Community 54 - "scheduling_repo.py"
Cohesion: 0.18
Nodes (11): ProfessionalInfo, free_slots(), Interval, WorkWindow, at(), test_busy_interval_blocks_overlapping_slots_only(), test_duration_longer_than_window_yields_nothing(), test_longer_service_only_fits_where_it_ends_before_the_busy_block() (+3 more)

### Community 55 - "routing.py"
Cohesion: 0.26
Nodes (4): RoutingClinicResolver, resolve_clinic_by_phone(), resolve_clinic_by_slug(), get_engine()

### Community 56 - "shared_kernel/errors.py"
Cohesion: 0.23
Nodes (7): VoiceSessionOutcome, VoiceSessionResult, list_slots(), DomainError, Forbidden, InvalidRequest, ServiceUnavailable

### Community 57 - "triavoz_agent/main.py"
Cohesion: 0.15
Nodes (6): find_caller_identity(), SipHandoff, sip_transfer(), _livekit_http_url(), prewarm(), _today_label()

### Community 58 - "test_scheduling_db.py"
Cohesion: 0.36
Nodes (10): _book(), local(), _slots(), test_booked_slot_disappears_and_cancel_brings_it_back(), test_booking_requires_an_offered_slot(), test_concurrent_bookings_of_the_same_slot_yield_exactly_one_winner(), test_db_constraint_rejects_overlap_even_if_the_use_case_is_bypassed(), raw_insert() (+2 more)

### Community 59 - "triavoz/config.py"
Cohesion: 0.12
Nodes (8): Settings, build_alert_service(), CompositeAlertNotifier, EmailAlertNotifier, LoggingAlertNotifier, get_gate_store(), get_alert_service(), get_gate_store_dep()

### Community 60 - "dependencies"
Cohesion: 0.20
Nodes (10): dependencies, clsx, livekit-client, @livekit/components-react, lucide-react, next, next-intl, react (+2 more)

### Community 61 - "next.config.ts"
Cohesion: 0.50
Nodes (3): nextConfig, securityHeaders, withNextIntl

### Community 62 - "devDependencies"
Cohesion: 0.25
Nodes (8): devDependencies, postcss, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom, typescript

### Community 63 - "typing"
Cohesion: 0.11
Nodes (5): CircuitOpenError, AbuseRepository, AlertNotifier, VoiceSessionRepository, StartVoiceSession

### Community 65 - "scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, start, typecheck

### Community 66 - "ADR 0006 — Auth cookies, rotation and SSE"
Cohesion: 0.40
Nodes (4): ADR 0006 — Auth cookies, rotation and SSE, Context, Decision, Rejected

### Community 67 - "test_gatekeeper.py"
Cohesion: 0.17
Nodes (15): ClinicPolicy, GateAction, GateReason, DailyUsage, DenyingStore, FakeRepo, _gatekeeper(), test_blocklist_kill_switch_hidden_and_business_hours() (+7 more)

### Community 68 - "score_call"
Cohesion: 0.12
Nodes (18): score_call(), ScoreResult, _inputs(), test_abusive_language_and_threshold_override(), test_clean_call_is_not_flagged(), test_repeat_caller_and_low_confidence_are_scored(), test_score_is_clamped_to_100(), test_very_short_empty_call_crosses_review_threshold() (+10 more)

### Community 69 - "ui.ts"
Cohesion: 0.50
Nodes (3): UiState, useUi, zustand

### Community 75 - "test_agent_units.py"
Cohesion: 0.15
Nodes (3): CallContext, ApiError, test_web_handoff_records_callback_and_reports_fallback()

### Community 76 - "agenda.py"
Cohesion: 0.14
Nodes (6): CallSummaryGenerator, TeamUserCreate, UserOut, create_user(), deactivate_user(), list_team()

### Community 77 - "telemetry.py"
Cohesion: 0.15
Nodes (9): _f(), WorkerConfig, estimate_cost_cents(), LatencyTracker, percentile(), TurnLatencyTracker, test_cost_estimate_uses_configured_prices_only(), test_percentiles_and_latency_summary() (+1 more)

### Community 78 - "calls.py"
Cohesion: 0.35
Nodes (7): get_call(), get_events(), get_turns(), list_calls(), CallDetailOut, CallListOut, CallOut

### Community 79 - "voice.py"
Cohesion: 0.14
Nodes (9): ClinicResolver, PgVoiceSessionRepository, VoiceSessionIn, VoiceSessionOut, create_voice_session(), _fallback_response(), get_clinic_resolver(), get_demo_clinic_slug() (+1 more)

### Community 80 - "internal_agent.py"
Cohesion: 0.16
Nodes (13): get_idempotency_store(), add_turns(), AppointmentIn, _aware(), BookIn, Ctx, EndIn, list_services() (+5 more)

### Community 81 - "test_agent_units.py"
Cohesion: 0.20
Nodes (11): sign(), contains_emergency(), HandoffPolicy, _client(), test_api_errors_expose_a_stable_code(), test_emergency_overrides_abuse_and_turn_limits(), test_handoff_policy_detects_urgency_fail_open(), test_handoff_policy_triggers_after_two_clarifications_and_resets() (+3 more)

### Community 82 - "prompts.py"
Cohesion: 0.48
Nodes (4): build_greeting_instructions(), build_instructions(), greeting_text(), test_instructions_contain_the_non_negotiable_rules()

### Community 84 - "redact_tool_arguments"
Cohesion: 0.50
Nodes (3): _redact(), redact_tool_arguments(), test_redaction_removes_patient_identifiers()

### Community 85 - "replay_guard.py"
Cohesion: 0.14
Nodes (8): replay_key(), sign(), verify(), get_replay_guard(), InMemoryReplayGuard, RedisReplayGuard, ReplayGuard, verify_internal_signature()

### Community 86 - "breaker.py"
Cohesion: 0.27
Nodes (7): breaker_key(), BreakerCheck, BreakerSnapshot, CostCircuitBreaker, parse_breaker_state(), probe_key(), test_cost_breaker_state_is_shared_and_half_open()

### Community 87 - "auth/ports.py"
Cohesion: 0.21
Nodes (4): RefreshRecord, UserRecord, PgAuthRepository, _user()

### Community 88 - "agenda.py"
Cohesion: 0.22
Nodes (9): cancel_appointment(), create_appointment(), list_agenda(), move_appointment(), AppointmentCreate, AppointmentMove, AppointmentOut, get_staff_repo() (+1 more)

### Community 89 - "entrypoint"
Cohesion: 0.27
Nodes (14): entrypoint(), add_turn(), close_after_handoff(), close_call(), on_item(), on_session_error(), on_tools(), persist_turn() (+6 more)

### Community 90 - "Gatekeeper"
Cohesion: 0.18
Nodes (6): Gatekeeper, gatekeeper_for(), _retry_seconds(), GateDecision, RateLimitBudget, 1. Gatekeeper before any spend

### Community 91 - "abuse/policy.py"
Cohesion: 0.14
Nodes (6): clinic_policy_from_context(), is_hidden_caller(), _with_emergency(), within_business_hours(), test_business_hours_weekday_window(), test_clinic_policy_applies_demo_caps()

### Community 93 - "asyncio"
Cohesion: 0.22
Nodes (6): Bulkhead, ProviderTimeoutError, with_timeout(), test_breaker_opens_recovers_half_open_and_closes(), test_bulkhead_caps_concurrency_and_times_out(), test_provider_deadline_raises_timeout()

### Community 94 - "Principal"
Cohesion: 0.29
Nodes (9): Principal, get_agent_config(), list_versions(), publish_version(), rollback_version(), save_draft(), AgentConfigIn, ConfigVersionOut (+1 more)

### Community 95 - "blocked.py"
Cohesion: 0.22
Nodes (7): add_blocked(), delete_blocked(), list_blocked(), unblock(), BlockedCreate, BlockedOut, get_staff_service()

### Community 96 - "voice_smoke.py"
Cohesion: 0.29
Nodes (7): _last_seq(), main(), speak(), _print_and_save(), _synthesize(), _turns(), _wait_agent()

### Community 100 - "PasswordHasher"
Cohesion: 0.20
Nodes (3): AccessTokenIssuer, PasswordHasher, RateLimiter

### Community 101 - "tenant_session"
Cohesion: 0.22
Nodes (6): _session_factory(), tenant_session(), start_call(), StartCall, telephony_incoming(), TelephonyIn

### Community 103 - "test_alerts.py"
Cohesion: 0.39
Nodes (4): RecordingNotifier, _service(), test_alerts_fire_once_per_hour_at_threshold(), test_cost_and_prank_alerts_use_integer_counters()

### Community 104 - "verify_rls_mutations.py"
Cohesion: 0.36
Nodes (5): main(), mutate(), Mutation, pytest_run(), require_env()

### Community 105 - "json"
Cohesion: 0.54
Nodes (3): room_metadata_json(), decode_cursor(), encode_cursor()

### Community 106 - "sqlalchemy"
Cohesion: 0.47
Nodes (3): run_migrations_offline(), run_migrations_online(), _url()

## Knowledge Gaps
- **30 isolated node(s):** `triavoz-agent`, `triavoz-api`, `@livekit/components-react`, `livekit-client`, `react` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 404 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **46 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `entrypoint()` connect `entrypoint` to `entrypoint`, `json`, `Agent Tool Definitions`, `test_agent_units.py`, `telemetry.py`, `test_agent_units.py`, `prompts.py`, `time`, `triavoz_agent/main.py`, `asyncio`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `StaffRepository` (e.g. with `StaffService` and `cancel_appointment()`) actually correct?**
  _`StaffRepository` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `triavoz-agent`, `triavoz-api`, `@livekit/components-react` to the rest of the system?**
  _30 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SchedulingRepository` be split into smaller, more focused modules?**
  _Cohesion score 0.11396011396011396 - nodes in this community are weakly interconnected._
- **Why does `StaffRepository` connect `StaffRepository` to `StaffService`, `agenda.py`, `calls.py`, `deps.py`, `schemas.py`, `agenda.py`, `Principal`, `blocked.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `Principal` (e.g. with `AccessTokenIssuer` and `AuthService`) actually correct?**
  _`Principal` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Should `package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._