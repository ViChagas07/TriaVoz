# Graph Report - Triavoz  (2026-10-22)

## Corpus Check
- 266 files · ~236,484 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: (none) 14, .example 2, .ini 1)

## Summary
- 2270 nodes · 6341 edges · 127 communities (88 shown, 39 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 829 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2a2e85a3`
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
- seed_demo.py
- voice.py
- internal_agent.py
- abuse/policy.py
- calls.py
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
- PgCallRepository
- TriaVoz brand
- app/layout.tsx
- proxy.ts
- opengraph-image.tsx
- RequestPanel
- 0009 — Locale strategy: cookie + `?lang`, not path prefixes
- apple-icon.tsx
- metrics.py
- PgVoiceSessionRepository
- helpers.ts
- get_settings
- unit/test_resilience.py
- ADR 0010 — Observability, agent evals and the RAG decision
- passwords.py
- dependencies
- @sentry/nextjs
- devDependencies
- TriaVozApi
- CircuitBreaker
- test_internal_agent_contract.py
- scripts
- test_caller_identity.py
- ConfigVersionOut
- test_sse_fanout.py
- redact_tool_arguments
- RequestBodyLimitMiddleware
- _FakeRoomApi
- demo.spec.ts
- playwright.config.ts

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

## Communities (127 total, 39 thin omitted)

### Community 0 - "NotFound"
Cohesion: 0.20
Nodes (9): BookAppointment, CancelAppointment, CancelStaffAppointment, ListAvailableSlots, ListMyAppointments, MoveStaffAppointment, Slot, _slots_for() (+1 more)

### Community 1 - "SchedulingRepository"
Cohesion: 0.09
Nodes (4): ProfessionalInfo, SchedulingRepository, ServiceInfo, ListServices

### Community 2 - "package.json"
Cohesion: 0.14
Nodes (13): name, private, version, @livekit/components-react, postcss, react-dom, tailwindcss, @tailwindcss/postcss (+5 more)

### Community 3 - "PgSchedulingRepository"
Cohesion: 0.14
Nodes (6): AppointmentView, _is_deadlock(), _is_overlap(), PgSchedulingRepository, _sqlstate(), raw_insert()

### Community 4 - "schemas.py"
Cohesion: 0.09
Nodes (36): AppointmentCreate, AppointmentMove, AssignIn, BusinessHours, CallDetailOut, CallEventOut, CallListOut, CallOut (+28 more)

### Community 5 - "types.ts"
Cohesion: 0.10
Nodes (25): AgentPage(), SettingsPage(), Tab, TABS, AppLayout(), AgentEditor(), API_ORIGIN, getSession() (+17 more)

### Community 6 - "test_staff_api.py"
Cohesion: 0.15
Nodes (27): _app(), _app_client(), _bearer(), client(), _create_attendant(), _future_slot(), _internal(), _login() (+19 more)

### Community 7 - "middleware.py"
Cohesion: 0.17
Nodes (13): _annotate_span(), register_request_middleware(), request_context(), _route_path(), _security_headers(), observe_http(), bind_log_ids(), current_call_id() (+5 more)

### Community 8 - "agendamentos/page.tsx"
Cohesion: 0.12
Nodes (40): AppointmentsPage(), one(), PRIORITY_KEYS, RequestTable(), Tab, tabsHref(), TYPE_KEYS, CallDetailPage() (+32 more)

### Community 9 - "next"
Cohesion: 0.06
Nodes (41): nextConfig, securityHeaders, withNextIntl, DemoPage(), LoginPage(), safeNext(), NotFound(), FAQ_KEYS (+33 more)

### Community 10 - "Agent Tool Definitions"
Cohesion: 0.12
Nodes (10): Receptionist, ADR 0007 — Live voice pipeline, turn tuning, turn persistence and handoff, Handoff, Known limitations, Latency target and measurements, P04.1 quality pass, Persistence, Providers actually used (+2 more)

### Community 11 - "TypeScript Configuration"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 12 - "ADR 0005 — Refresh tokens, per-clinic limits and transcript retention"
Cohesion: 0.40
Nodes (4): ADR 0005 — Refresh tokens, per-clinic limits and transcript retention, Decision, Rejected, Retention (implemented in P09: migrations 0005/0006)

### Community 13 - "pytest"
Cohesion: 0.16
Nodes (22): app_conn(), _hash(), test_clinic_settings_defaults_and_kill_switch_are_tenant_scoped(), test_refresh_token_can_be_inserted_and_revoked_for_own_tenant(), test_refresh_token_hash_is_unique_and_exactly_32_bytes(), test_refresh_token_rejects_a_user_from_another_clinic(), test_refresh_token_revocation_fields_move_together(), _tenant_tables() (+14 more)

### Community 14 - "System Architecture"
Cohesion: 0.10
Nodes (19): Voice Agent Service, API Service (FastAPI), Docker Compose Configuration, Project Progress Board, Agent Rules and Conventions, TriaVoz Context (Single Source of Truth), Grafana / Prometheus, Limitations (+11 more)

### Community 15 - "05 — Frontend UX (v2, nine lean routes)"
Cohesion: 0.09
Nodes (18): 0008 — Abuse, cost protection and emergency override, 2. Emergency override, 3. In-call limits (worker), 4. Post-call scoring, 5. Feedback loop, 6. Resilience and fallbacks, 7. Demo hardening, Consequences / risks (+10 more)

### Community 16 - "types.ts"
Cohesion: 0.10
Nodes (25): NewAppointmentDialog(), Strings, BlockedPanel(), ClinicForm(), DAY_KEYS, ProfessionalBody, ProfessionalsPanel(), Section() (+17 more)

### Community 17 - "Voice Worker Specs"
Cohesion: 0.67
Nodes (3): TriaVoz Voice Worker (LiveKit), TriaVoz API (FastAPI), Spec 03: Voice Agent

### Community 27 - "StaffRepository"
Cohesion: 0.09
Nodes (5): StaffRepository, get_call(), get_events(), get_turns(), list_team()

### Community 40 - "StaffService"
Cohesion: 0.12
Nodes (9): StaffService, add_blocked(), delete_blocked(), list_blocked(), unblock(), generate_summary(), BlockedCreate, BlockedOut (+1 more)

### Community 45 - "PgStaffRepository"
Cohesion: 0.11
Nodes (5): _percentile(), PgStaffRepository, _row(), _rows(), Conflict

### Community 48 - "test_http_limits.py"
Cohesion: 0.18
Nodes (8): _acquire_stream_slot(), _release_stream_slot(), stream_events(), generator(), _body(), test_oversized_body_is_rejected_with_content_length(), test_oversized_streamed_body_is_rejected(), test_sse_stream_slots_are_bounded_per_user()

### Community 49 - "deps.py"
Cohesion: 0.09
Nodes (22): Argon2PasswordHasher, decode_principal(), JwtAccessTokenIssuer, create_access_token(), decode_access_token(), Principal, UnconfiguredCallSummaryGenerator, LiveKitVoiceService (+14 more)

### Community 50 - "auth.py"
Cohesion: 0.05
Nodes (30): AccessTokenIssuer, AuthRepository, PasswordHasher, RateLimiter, RefreshRecord, UserRecord, AuthService, LoginResult (+22 more)

### Community 51 - "shared_kernel/resilience.py"
Cohesion: 0.24
Nodes (4): guarded_call(), ProviderTimeoutError, _with_breaker(), with_timeout()

### Community 52 - "replay_guard.py"
Cohesion: 0.21
Nodes (4): get_replay_guard(), InMemoryReplayGuard, RedisReplayGuard, ReplayGuard

### Community 53 - "Testing and E2E"
Cohesion: 0.29
Nodes (6): Commands, Coverage on the critical paths, Flake control, Not covered on purpose, Testing and E2E, What the new tests defend

### Community 54 - "free_slots"
Cohesion: 0.12
Nodes (15): free_slots(), Interval, WorkWindow, at(), busy_intervals(), test_every_slot_is_valid_and_every_valid_slot_is_returned(), test_slots_are_aligned_to_the_window_start(), windows() (+7 more)

### Community 55 - "StatusPill.tsx"
Cohesion: 0.50
Nodes (3): ICONS, KNOWN, STYLES

### Community 56 - "conftest.py"
Cohesion: 0.15
Nodes (10): drop_clinic(), isolated_clinic(), pytest_collection_modifyitems(), seed_clinic(), _set_ctx(), set_password(), tenants(), _seed_call() (+2 more)

### Community 57 - "triavoz_agent/main.py"
Cohesion: 0.12
Nodes (10): find_caller_identity(), SipHandoff, sip_transfer(), _livekit_http_url(), prewarm(), _today_label(), build_greeting_instructions(), build_instructions() (+2 more)

### Community 58 - "test_scheduling_db.py"
Cohesion: 0.29
Nodes (14): RescheduleAppointment, _book(), local(), _slots(), test_booked_slot_disappears_and_cancel_brings_it_back(), test_booking_requires_an_offered_slot(), test_concurrent_bookings_of_the_same_slot_yield_exactly_one_winner(), test_concurrent_reschedules_to_the_same_target_yield_exactly_one_winner() (+6 more)

### Community 59 - "test_internal_api.py"
Cohesion: 0.26
Nodes (10): future_monday(), client(), _post(), _signed(), test_full_voice_booking_flow_over_http(), test_health_is_public(), test_internal_routes_reject_missing_or_bad_signature(), test_naive_datetimes_are_rejected() (+2 more)

### Community 60 - "scenarios.py"
Cohesion: 0.07
Nodes (52): contains_emergency(), HandoffPolicy, SilencePolicy, test_emergency_overrides_abuse_and_turn_limits(), test_handoff_policy_detects_urgency_fail_open(), test_handoff_policy_triggers_after_two_clarifications_and_resets(), test_in_call_limits_abuse_warning_then_end_and_max_turns(), test_silence_policy_warns_once_then_closes_and_resets() (+44 more)

### Community 61 - "TurnstileVerifier"
Cohesion: 0.16
Nodes (7): TurnstileVerifier, _Client, _Response, _settings(), test_turnstile_fails_closed_and_opens_the_breaker_when_unreachable(), test_turnstile_is_disabled_without_a_secret(), test_turnstile_posts_the_secret_and_rejects_a_missing_or_failed_token()

### Community 62 - "observability.py"
Cohesion: 0.15
Nodes (11): bind_call_context(), configure_logging(), ContextFilter, init_sentry(), JsonFormatter, PlainFormatter, _scrub_event(), setup_tracing() (+3 more)

### Community 63 - "Bulkhead"
Cohesion: 0.28
Nodes (6): VoiceRoomService, ResilientVoiceRoomService, get_voice_room_service(), Bulkhead, test_resilient_adapter_opens_the_breaker_and_stops_calling_the_provider(), test_resilient_adapter_times_out_and_records_a_failure()

### Community 64 - "gate_store.py"
Cohesion: 0.10
Nodes (7): InMemoryRateLimiter, RedisRateLimiter, RedisTokenBucket, TokenBucket, redis(), test_bucket_burst_refill_and_expiry(), test_token_bucket_burst_then_refill()

### Community 65 - "DemoStage.tsx"
Cohesion: 0.11
Nodes (20): AppLoading(), Caption, start(), ErrorKind, FALLBACK_LABEL, getDemoPhone(), newDemoPhone(), Phase (+12 more)

### Community 66 - "ADR 0006 — Auth cookies, rotation and SSE"
Cohesion: 0.40
Nodes (4): ADR 0006 — Auth cookies, rotation and SSE, Context, Decision, Rejected

### Community 67 - "test_gatekeeper.py"
Cohesion: 0.16
Nodes (14): ClinicPolicy, GateReason, DailyUsage, DenyingStore, FakeRepo, _gatekeeper(), test_blocklist_kill_switch_hidden_and_business_hours(), test_budget_exhaustion_trips_breaker_and_recovery_closes_it() (+6 more)

### Community 68 - "ScriptedAgent"
Cohesion: 0.14
Nodes (6): ScriptedAgent, ToolEvent, _moment(), SlotLedger, ToolResult, ToolRunner

### Community 69 - "hmac_auth.py"
Cohesion: 0.18
Nodes (7): replay_key(), sign(), verify(), verify_any(), bind_internal_log_context(), guard_internal_request(), verify_internal_signature()

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
Cohesion: 0.16
Nodes (9): _f(), WorkerConfig, estimate_cost_cents(), LatencyTracker, percentile(), TurnLatencyTracker, test_cost_estimate_uses_configured_prices_only(), test_percentiles_and_latency_summary() (+1 more)

### Community 78 - "seed_demo.py"
Cohesion: 0.06
Nodes (17): _dsn(), main(), _run(), _agent_config(), ClinicSeed, _dsn(), _id(), main() (+9 more)

### Community 79 - "voice.py"
Cohesion: 0.16
Nodes (13): GateAction, ClinicResolver, caller_identity_hash(), is_valid_caller_identity(), new_caller_identity(), VoiceSessionOut, create_voice_session(), _fallback_response() (+5 more)

### Community 80 - "internal_agent.py"
Cohesion: 0.10
Nodes (37): tenant_session(), IdempotencyStore, add_turns(), AppointmentIn, _aware(), book(), BookIn, BookOut (+29 more)

### Community 83 - "abuse/policy.py"
Cohesion: 0.14
Nodes (6): clinic_policy_from_context(), is_hidden_caller(), _with_emergency(), within_business_hours(), test_business_hours_weekday_window(), test_clinic_policy_applies_demo_caps()

### Community 84 - "calls.py"
Cohesion: 0.14
Nodes (12): CallSummaryGenerator, list_calls(), assign_request(), complete_request(), get_request(), list_requests(), mark_spam(), patch_request() (+4 more)

### Community 85 - "Checklist evidence"
Cohesion: 0.15
Nodes (12): 1. Tenant isolation, 2. AuthN / AuthZ, 3. Service-to-service, 6. DoS / cost, 7. Secrets and supply chain, 8. LGPD / data protection, 9. Headers / TLS, Checklist evidence (+4 more)

### Community 86 - "breaker.py"
Cohesion: 0.27
Nodes (7): breaker_key(), BreakerCheck, BreakerSnapshot, CostCircuitBreaker, parse_breaker_state(), probe_key(), test_cost_breaker_state_is_shared_and_half_open()

### Community 87 - "json"
Cohesion: 0.08
Nodes (19): test_worker_json_log_carries_call_ids_and_ignores_transcript_payload(), room_metadata_json(), dispose_engine(), health(), create_app(), lifespan(), configure_logging(), ContextFilter (+11 more)

### Community 88 - "agenda.py"
Cohesion: 0.20
Nodes (7): EventPublisher, cancel_appointment(), create_appointment(), list_agenda(), move_appointment(), AppointmentOut, get_events_dep()

### Community 89 - "entrypoint"
Cohesion: 0.22
Nodes (16): entrypoint(), add_turn(), close_after_handoff(), close_call(), on_item(), on_session_error(), on_tools(), persist_turn() (+8 more)

### Community 90 - "Gatekeeper"
Cohesion: 0.12
Nodes (13): Gatekeeper, gatekeeper_for(), rate_limits_from_settings(), _retry_seconds(), GateDecision, RateLimitBudget, AbuseRepository, StartVoiceSession (+5 more)

### Community 91 - "shared_kernel/errors.py"
Cohesion: 0.22
Nodes (11): _body(), register_exception_handlers(), domain_error(), http_error(), unhandled(), validation_error(), current_request_id(), DomainError (+3 more)

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

### Community 99 - "TriaVoz brand"
Cohesion: 0.25
Nodes (7): Color tokens (source: `apps/web/src/app/globals.css`), Iconography, Identity, Logo, Shape and motion, TriaVoz brand, Type

### Community 100 - "app/layout.tsx"
Cohesion: 0.38
Nodes (4): inter, metadata, RootLayout(), ThemeScript()

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

### Community 106 - "metrics.py"
Cohesion: 0.15
Nodes (9): get_limiter(), get_limiter_dep(), metrics_content_type(), metrics_payload(), observe_call_ended(), observe_handoff(), observe_tool_error(), metrics() (+1 more)

### Community 107 - "PgVoiceSessionRepository"
Cohesion: 0.07
Nodes (10): run_migrations_offline(), run_migrations_online(), _url(), RoutingClinicResolver, resolve_clinic_by_phone(), resolve_clinic_by_slug(), get_engine(), _session_factory() (+2 more)

### Community 108 - "helpers.ts"
Cohesion: 0.24
Nodes (13): API_URL, apiLogin(), CallItem, clinicOf(), createCall(), createQueueItem(), DEMO_PASSWORD, internalPost() (+5 more)

### Community 110 - "get_settings"
Cohesion: 0.10
Nodes (11): get_settings(), Settings, build_alert_service(), CompositeAlertNotifier, EmailAlertNotifier, LoggingAlertNotifier, get_idempotency_store(), get_gate_store() (+3 more)

### Community 112 - "unit/test_resilience.py"
Cohesion: 0.18
Nodes (7): BulkheadFullError, CircuitOpenError, _ok(), test_breaker_call_short_circuits_and_records_success(), test_breaker_closed_open_half_open_closed(), test_bulkhead_caps_concurrency(), test_timeout_and_composed_guard()

### Community 114 - "ADR 0010 — Observability, agent evals and the RAG decision"
Cohesion: 0.40
Nodes (4): ADR 0010 — Observability, agent evals and the RAG decision, Consequences, Context, Decision

### Community 115 - "passwords.py"
Cohesion: 0.20
Nodes (4): hash_password(), verify_password(), test_argon2_uses_explicit_strong_parameters(), test_password_hash_verifies_only_the_right_password()

### Community 116 - "dependencies"
Cohesion: 0.18
Nodes (11): dependencies, clsx, livekit-client, @livekit/components-react, lucide-react, next, next-intl, react (+3 more)

### Community 117 - "@sentry/nextjs"
Cohesion: 0.29
Nodes (3): onRequestError, register(), @sentry/nextjs

### Community 119 - "devDependencies"
Cohesion: 0.22
Nodes (9): devDependencies, @playwright/test, postcss, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom (+1 more)

### Community 120 - "TriaVozApi"
Cohesion: 0.11
Nodes (11): CallContext, ApiError, sign(), TriaVozApi, _client(), test_api_errors_expose_a_stable_code(), test_receptionist_counts_tool_errors_and_slot_taken(), test_requests_are_signed_and_carry_server_side_ids() (+3 more)

### Community 122 - "test_internal_agent_contract.py"
Cohesion: 0.43
Nodes (4): _contract(), _refs(), test_every_internal_operation_declares_a_json_response_schema(), test_internal_agent_contract_matches_snapshot()

### Community 124 - "scripts"
Cohesion: 0.29
Nodes (7): scripts, build, dev, start, test:e2e, test:e2e:report, typecheck

### Community 125 - "test_caller_identity.py"
Cohesion: 0.20
Nodes (8): _app(), FakeRooms, _internal(), _signed(), test_web_caller_cannot_manage_another_phones_appointments(), test_hmac_accepts_previous_secret_only_during_rotation(), test_hmac_rejects_replayed_old_timestamp(), test_hmac_roundtrip_and_tamper_detection()

### Community 128 - "ConfigVersionOut"
Cohesion: 0.15
Nodes (10): AgentConfigSchema, get_agent_config(), list_versions(), publish_version(), rollback_version(), save_draft(), AgentConfigIn, AgentConfigStateOut (+2 more)

### Community 132 - "test_sse_fanout.py"
Cohesion: 0.36
Nodes (4): _channel(), redis(), test_event_bus_fans_out_only_to_the_matching_tenant(), _wait_subscribed()

### Community 134 - "redact_tool_arguments"
Cohesion: 0.50
Nodes (3): _redact(), redact_tool_arguments(), test_redaction_removes_patient_identifiers()

### Community 138 - "_FakeRoomApi"
Cohesion: 0.20
Nodes (3): _FakeLiveKitApi, _FakeRoomApi, test_livekit_adapter_creates_the_room_and_signs_a_room_scoped_token()

## Knowledge Gaps
- **29 isolated node(s):** `triavoz-agent`, `triavoz-api`, `@livekit/components-react`, `react-dom`, `zustand` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 633 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `05 — Frontend UX (v2, nine lean routes)` connect `05 — Frontend UX (v2, nine lean routes)` to `next`?**
  _High betweenness centrality (0.220) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `StaffRepository` (e.g. with `StaffService` and `cancel_appointment()`) actually correct?**
  _`StaffRepository` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `triavoz-agent`, `triavoz-api`, `@livekit/components-react` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SchedulingRepository` be split into smaller, more focused modules?**
  _Cohesion score 0.09009009009009009 - nodes in this community are weakly interconnected._
- **Why does `ScopedMessages()` connect `next` to `agendamentos/page.tsx`, `0009 — Locale strategy: cookie + `?lang`, not path prefixes`, `types.ts`, `05 — Frontend UX (v2, nine lean routes)`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `Principal` (e.g. with `AccessTokenIssuer` and `AuthService`) actually correct?**
  _`Principal` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Should `package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._