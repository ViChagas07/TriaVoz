# Graph Report - Triavoz  (2026-10-24)

## Corpus Check
- 266 files · ~248,450 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: (none) 14, .example 2, .ini 1)

## Summary
- 2274 nodes · 6351 edges · 134 communities (94 shown, 40 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 829 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7281ea7c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- NotFound
- SchedulingRepository
- package.json
- PgSchedulingRepository
- schemas.py
- types.ts
- test_staff_api.py
- middleware.py
- agendamentos/page.tsx
- next
- Agent Tool Definitions
- TypeScript Configuration
- ADR 0005 — Refresh tokens, per-clinic limits and transcript retention
- pytest
- System Architecture
- 05 — Frontend UX (v2, nine lean routes)
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
- test_http_limits.py
- deps.py
- auth.py
- shared_kernel/resilience.py
- replay_guard.py
- Testing and E2E
- free_slots
- StatusPill.tsx
- conftest.py
- triavoz_agent/main.py
- test_scheduling_db.py
- test_internal_api.py
- scenarios.py
- TurnstileVerifier
- observability.py
- Bulkhead
- gate_store.py
- DemoStage.tsx
- ADR 0006 — Auth cookies, rotation and SSE
- test_gatekeeper.py
- ScriptedAgent
- hmac_auth.py
- VoiceRoom
- RedisEventBus
- abuse/ports.py
- telemetry.py
- voice.py
- internal_agent.py
- next-intl
- painel/page.tsx
- abuse/policy.py
- schemas.py
- Checklist evidence
- breaker.py
- json
- agenda.py
- entrypoint
- Gatekeeper
- shared_kernel/errors.py
- GateStore
- asyncio
- test_auth_concurrency.py
- test_abuse_flow.py
- voice_smoke.py
- HandoffPolicy
- PgCallRepository
- TriaVoz brand
- app/layout.tsx
- proxy.ts
- opengraph-image.tsx
- RequestPanel
- 0009 — Locale strategy: cookie + `?lang`, not path prefixes
- seed_demo.py
- metrics.py
- routing.py
- helpers.ts
- get_settings
- calls.py
- unit/test_resilience.py
- PgVoiceSessionRepository
- ADR 0010 — Observability, agent evals and the RAG decision
- Principal
- dependencies
- @sentry/nextjs
- logging.py
- devDependencies
- TriaVozApi
- CircuitBreaker
- json
- uuid
- scripts
- test_caller_identity.py
- verify_rls_mutations.py
- purge_retention.py
- ConfigVersionOut
- guard_internal_request
- env.py
- RequestBodyLimitMiddleware
- _FakeRoomApi

## God Nodes (most connected - your core abstractions)
1. `StaffRepository` - 83 edges
2. `get_settings()` - 68 edges
3. `Principal` - 60 edges
4. `entrypoint()` - 53 edges
5. `PgStaffRepository` - 51 edges
6. `NotFound` - 49 edges
7. `PgSchedulingRepository` - 48 edges
8. `StaffService` - 44 edges
9. `tenant_session()` - 38 edges
10. `SchedulingRepository` - 37 edges

## Surprising Connections (you probably didn't know these)
- `3. In-call limits (worker)` --references--> `silence_timeout()`  [INFERRED]
  docs/adr/0008-abuse-and-cost-protection.md → apps/api/evals/scenarios.py
- `Scope / limitations` --references--> `ToolRunner`  [INFERRED]
  docs/evals.md → apps/api/evals/tools.py
- `Decision` --references--> `ScopedMessages()`  [INFERRED]
  docs/adr/0009-locale-strategy.md → apps/web/src/components/ScopedMessages.tsx
- `i18n` --references--> `ScopedMessages()`  [INFERRED]
  docs/specs/05-frontend-ux.md → apps/web/src/components/ScopedMessages.tsx
- `Handoff` --references--> `SipHandoff`  [INFERRED]
  docs/adr/0007-voice-pipeline-turns-handoff.md → apps/agent/src/triavoz_agent/handoff.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-tenant Security Framework** — docs_adr_0003, docs_specs_01 [EXTRACTED 1.00]
- **Triavoz Application Stack** — api_service, agent_service, web_service, postgres_service, redis_service, livekit_service [EXTRACTED 1.00]
- **Voice AI Pipeline** — apps_agent, apps_api [EXTRACTED 1.00]
- **Security & Isolation Enforcement** — tenant_isolation, postgres_service, github_workflows_ci [INFERRED 0.90]

## Communities (134 total, 40 thin omitted)

### Community 0 - "NotFound"
Cohesion: 0.23
Nodes (9): BookAppointment, CancelAppointment, CancelStaffAppointment, ListAvailableSlots, MoveStaffAppointment, Slot, _slots_for(), NotFound (+1 more)

### Community 1 - "SchedulingRepository"
Cohesion: 0.08
Nodes (5): ProfessionalInfo, SchedulingRepository, ServiceInfo, ListMyAppointments, ListServices

### Community 2 - "package.json"
Cohesion: 0.09
Nodes (16): name, private, version, AppLoading(), Skeleton(), @livekit/components-react, postcss, react (+8 more)

### Community 3 - "PgSchedulingRepository"
Cohesion: 0.15
Nodes (5): AppointmentView, _is_deadlock(), _is_overlap(), PgSchedulingRepository, _sqlstate()

### Community 4 - "schemas.py"
Cohesion: 0.15
Nodes (14): ClinicSettingsIn, ClinicSettingsOut, ProfessionalOut, ServiceOut, create_professional(), create_service(), deactivate_professional(), deactivate_service() (+6 more)

### Community 5 - "types.ts"
Cohesion: 0.10
Nodes (28): Tab, TABS, Strings, api(), ApiError, apiVoid(), request(), AgentConfig (+20 more)

### Community 6 - "test_staff_api.py"
Cohesion: 0.16
Nodes (26): _app(), _app_client(), _bearer(), client(), _create_attendant(), _future_slot(), _internal(), _login() (+18 more)

### Community 7 - "middleware.py"
Cohesion: 0.15
Nodes (13): _annotate_span(), register_request_middleware(), request_context(), _route_path(), _security_headers(), observe_http(), bind_log_ids(), current_call_id() (+5 more)

### Community 8 - "agendamentos/page.tsx"
Cohesion: 0.11
Nodes (30): AppointmentsPage(), one(), PRIORITY_KEYS, RequestTable(), Tab, tabsHref(), TYPE_KEYS, AgentPage() (+22 more)

### Community 9 - "next"
Cohesion: 0.12
Nodes (20): NotFound(), Landing(), AppShell(), isActive(), NAV, NavItem, DashboardPreview(), Props (+12 more)

### Community 11 - "TypeScript Configuration"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 12 - "ADR 0005 — Refresh tokens, per-clinic limits and transcript retention"
Cohesion: 0.40
Nodes (4): ADR 0005 — Refresh tokens, per-clinic limits and transcript retention, Decision, Rejected, Retention (implemented in P09: migrations 0005/0006)

### Community 13 - "pytest"
Cohesion: 0.22
Nodes (16): app_conn(), _tenant_tables(), test_audit_log_is_append_only_for_the_runtime_role(), test_concurrent_requests_of_different_tenants_never_mix(), read(), test_cross_tenant_insert_is_rejected_by_rls(), test_cross_tenant_update_and_delete_touch_zero_rows(), test_each_tenant_sees_only_its_own_rows_in_every_table() (+8 more)

### Community 14 - "System Architecture"
Cohesion: 0.10
Nodes (19): Voice Agent Service, API Service (FastAPI), Docker Compose Configuration, Project Progress Board, Agent Rules and Conventions, TriaVoz Context (Single Source of Truth), Grafana / Prometheus, Limitations (+11 more)

### Community 15 - "05 — Frontend UX (v2, nine lean routes)"
Cohesion: 0.08
Nodes (19): 0008 — Abuse, cost protection and emergency override, 2. Emergency override, 3. In-call limits (worker), 4. Post-call scoring, 5. Feedback loop, 6. Resilience and fallbacks, 7. Demo hardening, Consequences / risks (+11 more)

### Community 16 - "types.ts"
Cohesion: 0.15
Nodes (15): BlockedPanel(), ClinicForm(), DAY_KEYS, ProfessionalBody, ProfessionalsPanel(), Section(), ServiceBody, ServicesPanel() (+7 more)

### Community 17 - "Voice Worker Specs"
Cohesion: 0.67
Nodes (3): TriaVoz Voice Worker (LiveKit), TriaVoz API (FastAPI), Spec 03: Voice Agent

### Community 27 - "StaffRepository"
Cohesion: 0.09
Nodes (4): StaffRepository, list_blocked(), dashboard(), list_team()

### Community 40 - "StaffService"
Cohesion: 0.13
Nodes (6): StaffService, add_blocked(), delete_blocked(), unblock(), create_user(), deactivate_user()

### Community 45 - "PgStaffRepository"
Cohesion: 0.11
Nodes (5): _percentile(), PgStaffRepository, _row(), _rows(), Conflict

### Community 48 - "test_http_limits.py"
Cohesion: 0.18
Nodes (8): _acquire_stream_slot(), _release_stream_slot(), stream_events(), generator(), _body(), test_oversized_body_is_rejected_with_content_length(), test_oversized_streamed_body_is_rejected(), test_sse_stream_slots_are_bounded_per_user()

### Community 49 - "deps.py"
Cohesion: 0.11
Nodes (12): EventPublisher, CallSummaryGenerator, UnconfiguredCallSummaryGenerator, LiveKitVoiceService, get_auth_repo(), get_events_dep(), get_password_hasher(), get_staff_repo() (+4 more)

### Community 50 - "auth.py"
Cohesion: 0.05
Nodes (31): AccessTokenIssuer, AuthRepository, PasswordHasher, RateLimiter, RefreshRecord, UserRecord, AuthService, LoginResult (+23 more)

### Community 51 - "shared_kernel/resilience.py"
Cohesion: 0.24
Nodes (4): guarded_call(), ProviderTimeoutError, _with_breaker(), with_timeout()

### Community 52 - "replay_guard.py"
Cohesion: 0.12
Nodes (5): get_idempotency_store(), get_replay_guard(), InMemoryReplayGuard, RedisReplayGuard, ReplayGuard

### Community 53 - "Testing and E2E"
Cohesion: 0.33
Nodes (5): Commands, Coverage on the critical paths, Not covered on purpose, Testing and E2E, What the new tests defend

### Community 54 - "free_slots"
Cohesion: 0.12
Nodes (15): free_slots(), Interval, WorkWindow, at(), busy_intervals(), test_every_slot_is_valid_and_every_valid_slot_is_returned(), test_slots_are_aligned_to_the_window_start(), windows() (+7 more)

### Community 55 - "StatusPill.tsx"
Cohesion: 0.50
Nodes (3): ICONS, KNOWN, STYLES

### Community 56 - "conftest.py"
Cohesion: 0.14
Nodes (11): drop_clinic(), isolated_clinic(), pytest_collection_modifyitems(), seed_clinic(), _set_ctx(), set_password(), tenants(), _seed_call() (+3 more)

### Community 57 - "triavoz_agent/main.py"
Cohesion: 0.10
Nodes (13): find_caller_identity(), SipHandoff, sip_transfer(), _livekit_http_url(), prewarm(), _redact(), redact_tool_arguments(), _today_label() (+5 more)

### Community 58 - "test_scheduling_db.py"
Cohesion: 0.20
Nodes (17): RescheduleAppointment, _session_factory(), tenant_session(), _book(), local(), _slots(), test_booked_slot_disappears_and_cancel_brings_it_back(), test_booking_requires_an_offered_slot() (+9 more)

### Community 59 - "test_internal_api.py"
Cohesion: 0.26
Nodes (10): future_monday(), client(), _post(), _signed(), test_full_voice_booking_flow_over_http(), test_health_is_public(), test_internal_routes_reject_missing_or_bad_signature(), test_naive_datetimes_are_rejected() (+2 more)

### Community 60 - "scenarios.py"
Cohesion: 0.07
Nodes (46): SilencePolicy, test_silence_policy_warns_once_then_closes_and_resets(), appointment_state(), ClinicFixture, drop_eval_clinic(), eval_day(), eval_phone(), iso() (+38 more)

### Community 61 - "TurnstileVerifier"
Cohesion: 0.16
Nodes (7): TurnstileVerifier, _Client, _Response, _settings(), test_turnstile_fails_closed_and_opens_the_breaker_when_unreachable(), test_turnstile_is_disabled_without_a_secret(), test_turnstile_posts_the_secret_and_rejects_a_missing_or_failed_token()

### Community 62 - "observability.py"
Cohesion: 0.12
Nodes (16): _f(), WorkerConfig, bind_call_context(), configure_logging(), ContextFilter, init_sentry(), JsonFormatter, PlainFormatter (+8 more)

### Community 63 - "Bulkhead"
Cohesion: 0.28
Nodes (6): VoiceRoomService, ResilientVoiceRoomService, get_voice_room_service(), Bulkhead, test_resilient_adapter_opens_the_breaker_and_stops_calling_the_provider(), test_resilient_adapter_times_out_and_records_a_failure()

### Community 64 - "gate_store.py"
Cohesion: 0.09
Nodes (11): InMemoryRateLimiter, RedisRateLimiter, RedisTokenBucket, TokenBucket, redis(), test_bucket_burst_refill_and_expiry(), _channel(), redis() (+3 more)

### Community 65 - "DemoStage.tsx"
Cohesion: 0.10
Nodes (23): DemoPage(), Caption, DemoStage(), start(), ErrorKind, FALLBACK_LABEL, formatPhoneDisplay(), getDemoPhone() (+15 more)

### Community 66 - "ADR 0006 — Auth cookies, rotation and SSE"
Cohesion: 0.40
Nodes (4): ADR 0006 — Auth cookies, rotation and SSE, Context, Decision, Rejected

### Community 67 - "test_gatekeeper.py"
Cohesion: 0.18
Nodes (12): GateReason, DailyUsage, DenyingStore, FakeRepo, _gatekeeper(), test_blocklist_kill_switch_hidden_and_business_hours(), test_budget_exhaustion_trips_breaker_and_recovery_closes_it(), test_caller_token_bucket_limits_then_refills() (+4 more)

### Community 68 - "ScriptedAgent"
Cohesion: 0.14
Nodes (6): ScriptedAgent, ToolEvent, _moment(), SlotLedger, ToolResult, ToolRunner

### Community 69 - "hmac_auth.py"
Cohesion: 0.36
Nodes (5): replay_key(), sign(), verify(), verify_any(), verify_internal_signature()

### Community 74 - "VoiceRoom"
Cohesion: 0.13
Nodes (5): VoiceRoom, VoiceSessionRepository, create_room(), _FailingInner, _SlowInner

### Community 75 - "RedisEventBus"
Cohesion: 0.13
Nodes (9): _channel(), get_event_bus(), NullEventBus, RedisEventBus, get_event_stream(), 0011 — Test strategy: real seams, property tests and a browser smoke, Consequences, Context (+1 more)

### Community 76 - "abuse/ports.py"
Cohesion: 0.16
Nodes (11): ScoringInputs, score_call(), ScoreResult, PgAbuseRepository, end_call(), _inputs(), test_abusive_language_and_threshold_override(), test_clean_call_is_not_flagged() (+3 more)

### Community 77 - "telemetry.py"
Cohesion: 0.24
Nodes (5): LatencyTracker, percentile(), TurnLatencyTracker, test_percentiles_and_latency_summary(), test_turn_latency_computes_time_to_first_audio()

### Community 79 - "voice.py"
Cohesion: 0.16
Nodes (12): GateAction, ClinicResolver, caller_identity_hash(), is_valid_caller_identity(), new_caller_identity(), VoiceSessionOut, create_voice_session(), _fallback_response() (+4 more)

### Community 80 - "internal_agent.py"
Cohesion: 0.10
Nodes (37): IdempotencyStore, add_turns(), AppointmentIn, _aware(), book(), BookIn, BookOut, cancel() (+29 more)

### Community 81 - "next-intl"
Cohesion: 0.12
Nodes (18): nextConfig, securityHeaders, withNextIntl, LoginPage(), safeNext(), LoginForm(), Props, ScopedMessages() (+10 more)

### Community 82 - "painel/page.tsx"
Cohesion: 0.21
Nodes (18): DashboardPage(), greetingKey(), ActivityFeed(), EVENT_LABEL, Frame, CostBars(), CostPoint, LatencyBars() (+10 more)

### Community 83 - "abuse/policy.py"
Cohesion: 0.15
Nodes (5): clinic_policy_from_context(), _with_emergency(), within_business_hours(), test_business_hours_weekday_window(), test_clinic_policy_applies_demo_caps()

### Community 84 - "schemas.py"
Cohesion: 0.11
Nodes (30): assign_request(), complete_request(), get_request(), list_requests(), mark_spam(), patch_request(), AppointmentCreate, AppointmentMove (+22 more)

### Community 85 - "Checklist evidence"
Cohesion: 0.15
Nodes (12): 1. Tenant isolation, 2. AuthN / AuthZ, 3. Service-to-service, 6. DoS / cost, 7. Secrets and supply chain, 8. LGPD / data protection, 9. Headers / TLS, Checklist evidence (+4 more)

### Community 86 - "breaker.py"
Cohesion: 0.27
Nodes (7): breaker_key(), BreakerCheck, BreakerSnapshot, CostCircuitBreaker, parse_breaker_state(), probe_key(), test_cost_breaker_state_is_shared_and_half_open()

### Community 87 - "json"
Cohesion: 0.10
Nodes (12): dispose_engine(), health(), create_app(), lifespan(), init_sentry(), _scrub_event(), setup_from_settings(), setup_tracing() (+4 more)

### Community 88 - "agenda.py"
Cohesion: 0.23
Nodes (5): cancel_appointment(), create_appointment(), list_agenda(), move_appointment(), AppointmentOut

### Community 89 - "entrypoint"
Cohesion: 0.22
Nodes (16): entrypoint(), add_turn(), close_after_handoff(), close_call(), on_item(), on_session_error(), on_tools(), persist_turn() (+8 more)

### Community 90 - "Gatekeeper"
Cohesion: 0.11
Nodes (15): Gatekeeper, gatekeeper_for(), rate_limits_from_settings(), _retry_seconds(), ClinicPolicy, GateDecision, is_hidden_caller(), RateLimitBudget (+7 more)

### Community 91 - "shared_kernel/errors.py"
Cohesion: 0.25
Nodes (13): _body(), register_exception_handlers(), domain_error(), http_error(), unhandled(), validation_error(), current_request_id(), DomainError (+5 more)

### Community 92 - "GateStore"
Cohesion: 0.12
Nodes (4): AlertService, hour_bucket(), AlertNotifier, GateStore

### Community 93 - "asyncio"
Cohesion: 0.13
Nodes (9): Bulkhead, CircuitBreaker, CircuitOpenError, guarded_call(), ProviderTimeoutError, with_timeout(), test_breaker_opens_recovers_half_open_and_closes(), test_bulkhead_caps_concurrency_and_times_out() (+1 more)

### Community 94 - "test_auth_concurrency.py"
Cohesion: 0.27
Nodes (8): _active_tokens(), _app(), _cookie(), _login(), test_concurrent_logins_create_independent_families(), login_once(), test_concurrent_refresh_rotates_once_and_revokes_the_family(), attempt()

### Community 95 - "test_abuse_flow.py"
Cohesion: 0.08
Nodes (22): concurrent_key(), InMemoryGateStore, RedisGateStore, _client(), FakeRooms, _internal(), _login(), _owner_update() (+14 more)

### Community 96 - "voice_smoke.py"
Cohesion: 0.29
Nodes (7): _last_seq(), main(), speak(), _print_and_save(), _synthesize(), _turns(), _wait_agent()

### Community 97 - "HandoffPolicy"
Cohesion: 0.13
Nodes (15): contains_emergency(), HandoffPolicy, test_emergency_overrides_abuse_and_turn_limits(), test_handoff_policy_detects_urgency_fail_open(), test_handoff_policy_triggers_after_two_clarifications_and_resets(), test_in_call_limits_abuse_warning_then_end_and_max_turns(), ADR 0007 — Live voice pipeline, turn tuning, turn persistence and handoff, Handoff (+7 more)

### Community 99 - "TriaVoz brand"
Cohesion: 0.25
Nodes (7): Color tokens (source: `apps/web/src/app/globals.css`), Iconography, Identity, Logo, Shape and motion, TriaVoice brand, Type

### Community 100 - "app/layout.tsx"
Cohesion: 0.28
Nodes (6): archivo, inter, jetmono, metadata, RootLayout(), ThemeScript()

### Community 101 - "proxy.ts"
Cohesion: 0.31
Nodes (8): API_ORIGIN, config, contentSecurityPolicy(), isProtected(), LOCALES, PROTECTED, proxy(), withNonce()

### Community 102 - "opengraph-image.tsx"
Cohesion: 0.40
Nodes (3): alt, contentType, size

### Community 103 - "RequestPanel"
Cohesion: 0.70
Nodes (5): RequestPanel(), assign(), complete(), markSpam(), run()

### Community 104 - "0009 — Locale strategy: cookie + `?lang`, not path prefixes"
Cohesion: 0.40
Nodes (4): 0009 — Locale strategy: cookie + `?lang`, not path prefixes, Consequences, Context, Decision

### Community 105 - "seed_demo.py"
Cohesion: 0.24
Nodes (9): _agent_config(), ClinicSeed, _dsn(), _id(), main(), ProfessionalSeed, _seed_clinic(), ServiceSeed (+1 more)

### Community 106 - "metrics.py"
Cohesion: 0.15
Nodes (9): get_limiter(), get_limiter_dep(), metrics_content_type(), metrics_payload(), observe_call_ended(), observe_handoff(), observe_tool_error(), metrics() (+1 more)

### Community 107 - "routing.py"
Cohesion: 0.26
Nodes (4): RoutingClinicResolver, resolve_clinic_by_phone(), resolve_clinic_by_slug(), get_engine()

### Community 108 - "helpers.ts"
Cohesion: 0.13
Nodes (15): Handler, API_URL, apiLogin(), CallItem, clinicOf(), createCall(), createQueueItem(), DEMO_PASSWORD (+7 more)

### Community 110 - "get_settings"
Cohesion: 0.11
Nodes (10): get_settings(), Settings, build_alert_service(), CompositeAlertNotifier, EmailAlertNotifier, LoggingAlertNotifier, get_gate_store(), clear_auth_cookies() (+2 more)

### Community 111 - "calls.py"
Cohesion: 0.31
Nodes (7): generate_summary(), get_call(), get_events(), get_turns(), list_calls(), CallDetailOut, CallOut

### Community 112 - "unit/test_resilience.py"
Cohesion: 0.18
Nodes (7): BulkheadFullError, CircuitOpenError, _ok(), test_breaker_call_short_circuits_and_records_success(), test_breaker_closed_open_half_open_closed(), test_bulkhead_caps_concurrency(), test_timeout_and_composed_guard()

### Community 114 - "ADR 0010 — Observability, agent evals and the RAG decision"
Cohesion: 0.40
Nodes (4): ADR 0010 — Observability, agent evals and the RAG decision, Consequences, Context, Decision

### Community 115 - "Principal"
Cohesion: 0.14
Nodes (13): Argon2PasswordHasher, decode_principal(), JwtAccessTokenIssuer, hash_password(), verify_password(), create_access_token(), decode_access_token(), Principal (+5 more)

### Community 116 - "dependencies"
Cohesion: 0.18
Nodes (11): dependencies, clsx, livekit-client, @livekit/components-react, lucide-react, next, next-intl, react (+3 more)

### Community 117 - "@sentry/nextjs"
Cohesion: 0.29
Nodes (3): onRequestError, register(), @sentry/nextjs

### Community 118 - "logging.py"
Cohesion: 0.26
Nodes (5): configure_logging(), ContextFilter, JsonFormatter, PlainFormatter, _trace_fields()

### Community 119 - "devDependencies"
Cohesion: 0.22
Nodes (9): devDependencies, @playwright/test, postcss, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom (+1 more)

### Community 120 - "TriaVozApi"
Cohesion: 0.12
Nodes (11): CallContext, ApiError, sign(), TriaVozApi, _client(), test_api_errors_expose_a_stable_code(), test_receptionist_counts_tool_errors_and_slot_taken(), test_requests_are_signed_and_carry_server_side_ids() (+3 more)

### Community 122 - "json"
Cohesion: 0.24
Nodes (7): room_metadata_json(), decode_cursor(), encode_cursor(), _contract(), _refs(), test_every_internal_operation_declares_a_json_response_schema(), test_internal_agent_contract_matches_snapshot()

### Community 123 - "uuid"
Cohesion: 0.47
Nodes (6): _hash(), test_clinic_settings_defaults_and_kill_switch_are_tenant_scoped(), test_refresh_token_can_be_inserted_and_revoked_for_own_tenant(), test_refresh_token_hash_is_unique_and_exactly_32_bytes(), test_refresh_token_rejects_a_user_from_another_clinic(), test_refresh_token_revocation_fields_move_together()

### Community 124 - "scripts"
Cohesion: 0.29
Nodes (7): scripts, build, dev, start, test:e2e, test:e2e:report, typecheck

### Community 125 - "test_caller_identity.py"
Cohesion: 0.21
Nodes (8): _app(), FakeRooms, _internal(), _signed(), test_web_caller_cannot_manage_another_phones_appointments(), test_hmac_accepts_previous_secret_only_during_rotation(), test_hmac_rejects_replayed_old_timestamp(), test_hmac_roundtrip_and_tamper_detection()

### Community 126 - "verify_rls_mutations.py"
Cohesion: 0.43
Nodes (5): main(), mutate(), Mutation, pytest_run(), require_env()

### Community 127 - "purge_retention.py"
Cohesion: 0.53
Nodes (3): _dsn(), main(), _run()

### Community 128 - "ConfigVersionOut"
Cohesion: 0.19
Nodes (10): AgentConfigSchema, get_agent_config(), list_versions(), publish_version(), rollback_version(), save_draft(), AgentConfigIn, AgentConfigStateOut (+2 more)

### Community 131 - "env.py"
Cohesion: 0.60
Nodes (3): run_migrations_offline(), run_migrations_online(), _url()

### Community 138 - "_FakeRoomApi"
Cohesion: 0.20
Nodes (3): _FakeLiveKitApi, _FakeRoomApi, test_livekit_adapter_creates_the_room_and_signs_a_room_scoped_token()

## Knowledge Gaps
- **29 isolated node(s):** `triavoz-agent`, `triavoz-api`, `@livekit/components-react`, `react-dom`, `zustand` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 634 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **40 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ScopedMessages()` connect `next-intl` to `DemoStage.tsx`, `types.ts`, `agendamentos/page.tsx`, `next`, `0009 — Locale strategy: cookie + `?lang`, not path prefixes`, `05 — Frontend UX (v2, nine lean routes)`, `painel/page.tsx`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `StaffRepository` (e.g. with `StaffService` and `cancel_appointment()`) actually correct?**
  _`StaffRepository` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `triavoz-agent`, `triavoz-api`, `@livekit/components-react` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SchedulingRepository` be split into smaller, more focused modules?**
  _Cohesion score 0.08205128205128205 - nodes in this community are weakly interconnected._
- **Why does `i18n` connect `05 — Frontend UX (v2, nine lean routes)` to `next-intl`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `Principal` (e.g. with `AccessTokenIssuer` and `AuthService`) actually correct?**
  _`Principal` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Should `package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.09486166007905138 - nodes in this community are weakly interconnected._