# Graph Report - Triavoz  (2026-10-21)

## Corpus Check
- 206 files · ~203,500 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 18 file(s) not represented in the graph (top: (none) 13, .example 2, .ini 1)

## Summary
- 1763 nodes · 4942 edges · 107 communities (68 shown, 39 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 612 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b0ef05e1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- entrypoint
- SchedulingRepository
- package.json
- PgSchedulingRepository
- schemas.py
- test_abuse_flow.py
- test_staff_api.py
- triavoz/main.py
- agendamentos/page.tsx
- next
- Agent Tool Definitions
- TypeScript Configuration
- ADR 0005 — Refresh tokens, per-clinic limits and transcript retention
- seed_demo.py
- System Architecture
- deps.py
- types.ts
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
- Principal
- auth/service.py
- CircuitBreaker
- gate_store.py
- configuracoes/page.tsx
- scheduling_repo.py
- verify_rls_mutations.py
- shared_kernel/errors.py
- triavoz_agent/main.py
- test_scheduling_db.py
- triavoz/config.py
- pytest
- lucide-react
- conftest.py
- voice.py
- test_internal_api.py
- DemoStage.tsx
- ADR 0006 — Auth cookies, rotation and SSE
- test_gatekeeper.py
- score_call
- time
- .subscribe
- agenda.py
- telemetry.py
- calls.py
- telephony_incoming
- internal_agent.py
- test_agent_units.py
- prompts.py
- stream_events
- redact_tool_arguments
- replay_guard.py
- breaker.py
- uuid
- agenda.py
- entrypoint
- Gatekeeper
- abuse/policy.py
- GateStore
- asyncio
- Principal
- RedisGateStore
- voice_smoke.py
- dataclasses
- PgCallRepository
- TriaVoz brand
- app/layout.tsx
- proxy.ts
- opengraph-image.tsx
- RequestPanel
- 0009 — Locale strategy: cookie + `?lang`, not path prefixes
- apple-icon.tsx

## God Nodes (most connected - your core abstractions)
1. `StaffRepository` - 83 edges
2. `Principal` - 58 edges
3. `get_settings()` - 51 edges
4. `PgStaffRepository` - 51 edges
5. `NotFound` - 48 edges
6. `entrypoint()` - 47 edges
7. `StaffService` - 44 edges
8. `PgSchedulingRepository` - 40 edges
9. `SchedulingRepository` - 35 edges
10. `tenant_session()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `Decision` --references--> `ScopedMessages()`  [INFERRED]
  docs/adr/0009-locale-strategy.md → apps/web/src/components/ScopedMessages.tsx
- `i18n` --references--> `ScopedMessages()`  [INFERRED]
  docs/specs/05-frontend-ux.md → apps/web/src/components/ScopedMessages.tsx
- `Handoff` --references--> `SipHandoff`  [INFERRED]
  docs/adr/0007-voice-pipeline-turns-handoff.md → apps/agent/src/triavoz_agent/handoff.py
- `P04.1 quality pass` --references--> `HandoffPolicy`  [INFERRED]
  docs/adr/0007-voice-pipeline-turns-handoff.md → apps/agent/src/triavoz_agent/policy.py
- `4. Post-call scoring` --references--> `score_call()`  [INFERRED]
  docs/adr/0008-abuse-and-cost-protection.md → apps/api/src/triavoz/application/abuse/scoring.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-tenant Security Framework** — docs_adr_0003, docs_specs_01 [EXTRACTED 1.00]
- **Triavoz Application Stack** — api_service, agent_service, web_service, postgres_service, redis_service, livekit_service [EXTRACTED 1.00]
- **Voice AI Pipeline** — apps_agent, apps_api [EXTRACTED 1.00]
- **Security & Isolation Enforcement** — tenant_isolation, postgres_service, github_workflows_ci [INFERRED 0.90]

## Communities (107 total, 39 thin omitted)

### Community 0 - "entrypoint"
Cohesion: 0.26
Nodes (3): CallContext, sign(), TriaVozApi

### Community 1 - "SchedulingRepository"
Cohesion: 0.07
Nodes (13): SchedulingRepository, ServiceInfo, BookAppointment, CancelAppointment, CancelStaffAppointment, ListAvailableSlots, ListMyAppointments, ListServices (+5 more)

### Community 2 - "package.json"
Cohesion: 0.05
Nodes (37): dependencies, clsx, livekit-client, @livekit/components-react, lucide-react, next, next-intl, react (+29 more)

### Community 4 - "schemas.py"
Cohesion: 0.11
Nodes (18): AgentConfigSchema, BusinessHours, ClinicSettingsIn, ClinicSettingsOut, ProfessionalCreate, ProfessionalOut, ProfessionalPatch, ServiceCreate (+10 more)

### Community 5 - "test_abuse_flow.py"
Cohesion: 0.10
Nodes (19): InMemoryGateStore, _client(), FakeRooms, _internal(), _login(), _owner_update(), _passwords(), _signed() (+11 more)

### Community 6 - "test_staff_api.py"
Cohesion: 0.18
Nodes (24): _app(), _app_client(), _bearer(), client(), _create_attendant(), _future_slot(), _internal(), _login() (+16 more)

### Community 7 - "triavoz/main.py"
Cohesion: 0.14
Nodes (5): dispose_engine(), health(), register_request_middleware(), create_app(), lifespan()

### Community 8 - "agendamentos/page.tsx"
Cohesion: 0.12
Nodes (37): AppointmentsPage(), one(), PRIORITY_KEYS, RequestTable(), Tab, tabsHref(), TYPE_KEYS, CallDetailPage() (+29 more)

### Community 9 - "next"
Cohesion: 0.08
Nodes (34): nextConfig, securityHeaders, withNextIntl, DemoPage(), LoginPage(), safeNext(), NotFound(), FAQ_KEYS (+26 more)

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
Cohesion: 0.12
Nodes (13): _agent_config(), ClinicSeed, _dsn(), _id(), main(), ProfessionalSeed, _seed_clinic(), ServiceSeed (+5 more)

### Community 14 - "System Architecture"
Cohesion: 0.18
Nodes (11): Voice Agent Service, API Service (FastAPI), Docker Compose Configuration, Project Progress Board, Agent Rules and Conventions, TriaVoz Context (Single Source of Truth), CI Workflow, LiveKit Server (+3 more)

### Community 15 - "deps.py"
Cohesion: 0.15
Nodes (11): get_event_bus(), RedisEventBus, get_limiter(), UnconfiguredCallSummaryGenerator, get_auth_repo(), get_clinic_resolver(), get_event_stream(), get_events_dep() (+3 more)

### Community 16 - "types.ts"
Cohesion: 0.06
Nodes (43): Strings, BlockedPanel(), ClinicForm(), DAY_KEYS, ProfessionalBody, ProfessionalsPanel(), Section(), ServiceBody (+35 more)

### Community 17 - "Voice Worker Specs"
Cohesion: 0.67
Nodes (3): TriaVoz Voice Worker (LiveKit), TriaVoz API (FastAPI), Spec 03: Voice Agent

### Community 27 - "StaffRepository"
Cohesion: 0.10
Nodes (3): StaffRepository, deactivate_professional(), deactivate_service()

### Community 40 - "StaffService"
Cohesion: 0.22
Nodes (3): StaffService, generate_summary(), NotFound

### Community 45 - "PgStaffRepository"
Cohesion: 0.11
Nodes (5): _percentile(), PgStaffRepository, _row(), _rows(), Conflict

### Community 48 - "schemas.py"
Cohesion: 0.20
Nodes (14): assign_request(), complete_request(), get_request(), list_requests(), mark_spam(), patch_request(), AssignIn, MarkSpamIn (+6 more)

### Community 49 - "Principal"
Cohesion: 0.18
Nodes (16): RefreshResult, decode_principal(), JwtAccessTokenIssuer, create_access_token(), decode_access_token(), Principal, me(), _user_out() (+8 more)

### Community 50 - "auth/service.py"
Cohesion: 0.08
Nodes (18): AccessTokenIssuer, AuthRepository, PasswordHasher, RateLimiter, RefreshRecord, UserRecord, AuthService, LoginResult (+10 more)

### Community 51 - "CircuitBreaker"
Cohesion: 0.07
Nodes (19): VoiceRoom, ResilientVoiceRoomService, TurnstileVerifier, LiveKitVoiceService, Bulkhead, BulkheadFullError, CircuitBreaker, CircuitOpenError (+11 more)

### Community 52 - "gate_store.py"
Cohesion: 0.11
Nodes (7): InMemoryRateLimiter, RedisRateLimiter, RedisTokenBucket, TokenBucket, redis(), test_bucket_burst_refill_and_expiry(), test_token_bucket_burst_then_refill()

### Community 53 - "configuracoes/page.tsx"
Cohesion: 0.15
Nodes (14): AgentPage(), SettingsPage(), Tab, TABS, AppLayout(), AgentEditor(), Card(), PageHeader() (+6 more)

### Community 54 - "scheduling_repo.py"
Cohesion: 0.17
Nodes (12): AppointmentView, ProfessionalInfo, free_slots(), Interval, WorkWindow, at(), test_busy_interval_blocks_overlapping_slots_only(), test_duration_longer_than_window_yields_nothing() (+4 more)

### Community 55 - "verify_rls_mutations.py"
Cohesion: 0.08
Nodes (12): run_migrations_offline(), run_migrations_online(), _url(), RoutingClinicResolver, resolve_clinic_by_phone(), resolve_clinic_by_slug(), get_engine(), main() (+4 more)

### Community 56 - "shared_kernel/errors.py"
Cohesion: 0.21
Nodes (14): _body(), register_exception_handlers(), domain_error(), http_error(), unhandled(), current_request_id(), AuthenticationError, DomainError (+6 more)

### Community 57 - "triavoz_agent/main.py"
Cohesion: 0.10
Nodes (7): ApiError, find_caller_identity(), SipHandoff, sip_transfer(), _livekit_http_url(), prewarm(), _today_label()

### Community 58 - "test_scheduling_db.py"
Cohesion: 0.41
Nodes (9): _book(), local(), _slots(), test_booked_slot_disappears_and_cancel_brings_it_back(), test_booking_requires_an_offered_slot(), test_concurrent_bookings_of_the_same_slot_yield_exactly_one_winner(), test_db_constraint_rejects_overlap_even_if_the_use_case_is_bypassed(), raw_insert() (+1 more)

### Community 59 - "triavoz/config.py"
Cohesion: 0.10
Nodes (13): get_settings(), Settings, build_alert_service(), CompositeAlertNotifier, EmailAlertNotifier, LoggingAlertNotifier, get_gate_store(), clear_auth_cookies() (+5 more)

### Community 60 - "pytest"
Cohesion: 0.22
Nodes (16): app_conn(), _tenant_tables(), test_audit_log_is_append_only_for_the_runtime_role(), test_concurrent_requests_of_different_tenants_never_mix(), read(), test_cross_tenant_insert_is_rejected_by_rls(), test_cross_tenant_update_and_delete_touch_zero_rows(), test_each_tenant_sees_only_its_own_rows_in_every_table() (+8 more)

### Community 61 - "lucide-react"
Cohesion: 0.16
Nodes (8): AppLoading(), Skeleton(), LoginForm(), DEMO_ACCOUNTS, DEMO_PASSWORD, DemoAccount, lucide-react, react

### Community 62 - "conftest.py"
Cohesion: 0.22
Nodes (6): drop_clinic(), pytest_collection_modifyitems(), seed_clinic(), _set_ctx(), tenants(), test_every_tenant_table_has_enabled_and_forced_rls_with_a_policy()

### Community 63 - "voice.py"
Cohesion: 0.13
Nodes (11): GateAction, ClinicResolver, VoiceRoomService, VoiceSessionRepository, StartVoiceSession, VoiceSessionOutcome, VoiceSessionOut, create_voice_session() (+3 more)

### Community 64 - "test_internal_api.py"
Cohesion: 0.28
Nodes (9): future_monday(), client(), _post(), _signed(), test_full_voice_booking_flow_over_http(), test_health_is_public(), test_internal_routes_reject_missing_or_bad_signature(), test_naive_datetimes_are_rejected() (+1 more)

### Community 65 - "DemoStage.tsx"
Cohesion: 0.15
Nodes (14): Caption, start(), ErrorKind, FALLBACK_LABEL, getDemoPhone(), newDemoPhone(), Phase, PreviewPhase (+6 more)

### Community 66 - "ADR 0006 — Auth cookies, rotation and SSE"
Cohesion: 0.40
Nodes (4): ADR 0006 — Auth cookies, rotation and SSE, Context, Decision, Rejected

### Community 67 - "test_gatekeeper.py"
Cohesion: 0.16
Nodes (14): ClinicPolicy, GateReason, DailyUsage, DenyingStore, FakeRepo, _gatekeeper(), test_blocklist_kill_switch_hidden_and_business_hours(), test_budget_exhaustion_trips_breaker_and_recovery_closes_it() (+6 more)

### Community 68 - "score_call"
Cohesion: 0.09
Nodes (18): 0008 — Abuse, cost protection and emergency override, 2. Emergency override, 3. In-call limits (worker), 4. Post-call scoring, 5. Feedback loop, 6. Resilience and fallbacks, 7. Demo hardening, Consequences / risks (+10 more)

### Community 69 - "time"
Cohesion: 0.24
Nodes (6): replay_key(), sign(), verify(), verify_internal_signature(), test_hmac_rejects_replayed_old_timestamp(), test_hmac_roundtrip_and_tamper_detection()

### Community 76 - "agenda.py"
Cohesion: 0.08
Nodes (16): CallSummaryGenerator, add_blocked(), delete_blocked(), list_blocked(), unblock(), dashboard(), BlockedCreate, BlockedOut (+8 more)

### Community 77 - "telemetry.py"
Cohesion: 0.15
Nodes (9): _f(), WorkerConfig, estimate_cost_cents(), LatencyTracker, percentile(), TurnLatencyTracker, test_cost_estimate_uses_configured_prices_only(), test_percentiles_and_latency_summary() (+1 more)

### Community 78 - "calls.py"
Cohesion: 0.20
Nodes (12): room_metadata_json(), get_call(), get_events(), get_turns(), list_calls(), CallDetailOut, CallEventOut, CallListOut (+4 more)

### Community 80 - "internal_agent.py"
Cohesion: 0.11
Nodes (26): _session_factory(), tenant_session(), get_idempotency_store(), IdempotencyStore, add_turns(), AppointmentIn, _aware(), book() (+18 more)

### Community 81 - "test_agent_units.py"
Cohesion: 0.18
Nodes (11): contains_emergency(), HandoffPolicy, _client(), test_api_errors_expose_a_stable_code(), test_emergency_overrides_abuse_and_turn_limits(), test_handoff_policy_detects_urgency_fail_open(), test_handoff_policy_triggers_after_two_clarifications_and_resets(), test_in_call_limits_abuse_warning_then_end_and_max_turns() (+3 more)

### Community 82 - "prompts.py"
Cohesion: 0.48
Nodes (4): build_greeting_instructions(), build_instructions(), greeting_text(), test_instructions_contain_the_non_negotiable_rules()

### Community 84 - "redact_tool_arguments"
Cohesion: 0.50
Nodes (3): _redact(), redact_tool_arguments(), test_redaction_removes_patient_identifiers()

### Community 85 - "replay_guard.py"
Cohesion: 0.21
Nodes (4): get_replay_guard(), InMemoryReplayGuard, RedisReplayGuard, ReplayGuard

### Community 86 - "breaker.py"
Cohesion: 0.27
Nodes (7): breaker_key(), BreakerCheck, BreakerSnapshot, CostCircuitBreaker, parse_breaker_state(), probe_key(), test_cost_breaker_state_is_shared_and_half_open()

### Community 87 - "uuid"
Cohesion: 0.42
Nodes (6): _hash(), test_clinic_settings_defaults_and_kill_switch_are_tenant_scoped(), test_refresh_token_can_be_inserted_and_revoked_for_own_tenant(), test_refresh_token_hash_is_unique_and_exactly_32_bytes(), test_refresh_token_rejects_a_user_from_another_clinic(), test_refresh_token_revocation_fields_move_together()

### Community 88 - "agenda.py"
Cohesion: 0.19
Nodes (8): EventPublisher, cancel_appointment(), create_appointment(), list_agenda(), move_appointment(), AppointmentCreate, AppointmentMove, AppointmentOut

### Community 89 - "entrypoint"
Cohesion: 0.26
Nodes (15): entrypoint(), add_turn(), close_after_handoff(), close_call(), on_item(), on_session_error(), on_tools(), persist_turn() (+7 more)

### Community 90 - "Gatekeeper"
Cohesion: 0.13
Nodes (10): Gatekeeper, gatekeeper_for(), rate_limits_from_settings(), _retry_seconds(), GateDecision, is_hidden_caller(), RateLimitBudget, AbuseRepository (+2 more)

### Community 91 - "abuse/policy.py"
Cohesion: 0.15
Nodes (5): clinic_policy_from_context(), _with_emergency(), within_business_hours(), test_business_hours_weekday_window(), test_clinic_policy_applies_demo_caps()

### Community 92 - "GateStore"
Cohesion: 0.12
Nodes (4): AlertService, hour_bucket(), AlertNotifier, GateStore

### Community 93 - "asyncio"
Cohesion: 0.13
Nodes (9): Bulkhead, CircuitBreaker, CircuitOpenError, guarded_call(), ProviderTimeoutError, with_timeout(), test_breaker_opens_recovers_half_open_and_closes(), test_bulkhead_caps_concurrency_and_times_out() (+1 more)

### Community 94 - "Principal"
Cohesion: 0.28
Nodes (8): get_agent_config(), list_versions(), publish_version(), rollback_version(), save_draft(), AgentConfigIn, AgentConfigStateOut, ConfigVersionOut

### Community 95 - "RedisGateStore"
Cohesion: 0.40
Nodes (3): concurrent_key(), RedisGateStore, test_concurrency_slots_are_atomic_and_reusable()

### Community 96 - "voice_smoke.py"
Cohesion: 0.26
Nodes (7): _last_seq(), main(), speak(), _print_and_save(), _synthesize(), _turns(), _wait_agent()

### Community 97 - "dataclasses"
Cohesion: 0.16
Nodes (11): ScoringInputs, score_call(), ScoreResult, PgAbuseRepository, end_call(), _inputs(), test_abusive_language_and_threshold_override(), test_clean_call_is_not_flagged() (+3 more)

### Community 99 - "TriaVoz brand"
Cohesion: 0.25
Nodes (7): Color tokens (source: `apps/web/src/app/globals.css`), Iconography, Identity, Logo, Shape and motion, TriaVoz brand, Type

### Community 100 - "app/layout.tsx"
Cohesion: 0.38
Nodes (4): inter, metadata, RootLayout(), ThemeScript()

### Community 101 - "proxy.ts"
Cohesion: 0.33
Nodes (6): API_ORIGIN, config, isProtected(), LOCALES, PROTECTED, proxy()

### Community 102 - "opengraph-image.tsx"
Cohesion: 0.40
Nodes (3): alt, contentType, size

### Community 103 - "RequestPanel"
Cohesion: 0.70
Nodes (5): RequestPanel(), assign(), complete(), markSpam(), run()

### Community 104 - "0009 — Locale strategy: cookie + `?lang`, not path prefixes"
Cohesion: 0.40
Nodes (4): 0009 — Locale strategy: cookie + `?lang`, not path prefixes, Consequences, Context, Decision

## Knowledge Gaps
- **29 isolated node(s):** `triavoz-agent`, `triavoz-api`, `@livekit/components-react`, `react-dom`, `zustand` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 488 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `05 — Frontend UX (v2, nine lean routes)` connect `score_call` to `next`?**
  _High betweenness centrality (0.280) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `StaffRepository` (e.g. with `StaffService` and `cancel_appointment()`) actually correct?**
  _`StaffRepository` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `triavoz-agent`, `triavoz-api`, `@livekit/components-react` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SchedulingRepository` be split into smaller, more focused modules?**
  _Cohesion score 0.07393483709273183 - nodes in this community are weakly interconnected._
- **Why does `ScopedMessages()` connect `next` to `agendamentos/page.tsx`, `0009 — Locale strategy: cookie + `?lang`, not path prefixes`, `configuracoes/page.tsx`, `score_call`?**
  _High betweenness centrality (0.210) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `Principal` (e.g. with `AccessTokenIssuer` and `AuthService`) actually correct?**
  _`Principal` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Should `package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.05263157894736842 - nodes in this community are weakly interconnected._