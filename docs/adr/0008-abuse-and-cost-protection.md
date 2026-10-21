# 0008 — Abuse, cost protection and emergency override

Status: accepted · 2026-10-21 · P05

## Context

The public voice demo spends real STT/LLM/TTS credits and creates rooms before a caller says a word.
Prank callers, repeat dialers and a shared public link can drain the budget. At the same time, a
patient with an emergency must never be filtered out by an anti-abuse rule.

Spec 04 asks for progressive friction: cheap checks before the agent starts, in-call friction,
post-call scoring, and a feedback loop. This ADR records how those pieces fit together.

## Decision

### 1. Gatekeeper before any spend

`StartVoiceSession` builds a `Gatekeeper` inside the tenant transaction and asks it for a
`GateDecision` before creating a `calls` row or a LiveKit room. Order:

1. **Emergency hint** — always returns the clinic's emergency message + SAMU 192 guidance.
2. Kill switch, hidden-number policy, business hours.
3. Blocklist: clinic rows + global rows (`blocked_numbers.clinic_id IS NULL`), expired rows ignored.
4. Token buckets per caller (`clinic:{id}:rl:caller:{e164}`), per IP
   (`clinic:{id}:rl:ip:{ip}`) and clinic-wide (`clinic:{id}:rl:global`).
5. Daily minute and cost budgets from `clinic_settings` (demo caps may only lower them).
6. Cost circuit breaker (Redis JSON state, shared) — closed → open → half-open probe.
7. Concurrent-call slot (`clinic:{id}:rl:concurrent`, Redis sorted set, TTL-expired so a crashed
   process cannot leak capacity).
8. Allow.

Every refusal is a `GateDecision` with a fixed message that still tells the caller how to reach
SAMU. A blocked caller is not silently dropped. The API returns HTTP 200 with `mode=fallback` (or
`mode=emergency`); only an admitted call gets a room token.

The same gatekeeper runs for the optional HMAC-signed telephony webhook
(`POST /internal/agent/telephony/incoming`). Hidden/unknown callers are allowed by default; a clinic
must explicitly set `hidden_caller_policy='reject'` because hidden numbers are unverifiable data.

### 2. Emergency override

* Gatekeeper: `emergency_hint=true` short-circuits before every limit, including kill switch,
  blocklist, budgets and an open breaker. It creates no room and spends no provider credit; it
  returns the SAMU message/handoff payload.
* Worker: urgency keywords set `HandoffPolicy.emergency`. From then on abuse strikes, turn limits
  and misunderstanding handoffs are ignored. The hard-duration timer grants one extra
  `TRIAVOZ_EMERGENCY_GRACE_SECONDS` window so the SAMU instruction can be spoken.
* Tests cover emergency in every protection state and in-call emergency precedence.

### 3. In-call limits (worker)

* Silence after the greeting: one “are you still there?” prompt, then `silence_timeout`.
* Hard duration: API metadata `max_call_seconds`, capped by the worker's own ceiling.
* Max turns from metadata (`demo_max_turns`).
* Abusive language: one calm warning, second strike ends the call and sets
  `abusive_language_detected` on the end payload (the words are never logged).
* Two consecutive clarifications → handoff (existing policy, kept).
* The call still ends with a persisted record in every path; call ends are idempotent.

### 4. Post-call scoring

`score_call` is pure: very short (<15s), no patient speech, no valid outcome, repeat caller (2+/5+
calls in 24h), average STT confidence <0.55, abusive language. Score is clamped 0–100 and stored in
`calls.abuse_score`; flags go to `calls.suspicion_flags`. Linked `service_requests.suspicion_flags`
are updated so the dashboard can show a **review** badge (`needs_review` in the API). A score never
automatically blocks a number: a human marks spam or unblocks it.

### 5. Feedback loop

* `mark-spam` sets the request to `spam`, blocklists the number (`source=auto_spam_flag`) with an
  optional `expires_in_days`.
* `POST /api/v1/blocked-numbers/{id}/unblock` (and `DELETE`) is the explicit human override.
* Identical requests from the same number/type/title within 10 minutes are deduplicated.
* Spike alerts (calls/hour, cost/hour, prank flags/hour) are logged; e-mail is sent when SMTP
  settings and `TRIAVOZ_ALERTS_EMAIL` are configured. Phone numbers are never included.

### 6. Resilience and fallbacks

| Call | Guard | Fallback |
|---|---|---|
| LiveKit room/token (API) | 5s timeout + bulkhead 10 + breaker 3/15s | 503 `voice_provider_unavailable`; slot released |
| LiveKit connect (worker) | 10s timeout | job closes; no half-open session |
| Session start / greeting (STT/LLM/TTS init) | 20s / 15s timeouts | callback request + `provider_failure` end |
| LLM + TTS turn (`generate_reply`/`say`) | 12–15s timeout | fixed spoken message, then close |
| Internal API tools (worker) | 8s timeout + bulkhead + breaker | tool error → calm message; handoff path remains |
| Provider error event | LiveKit Agents error handler | fixed “instabilidade” message + callback + close |

STT is a stream, so it is bounded by silence/max-duration rather than a per-utterance deadline.
LiveKit Agents owns the provider connections; the worker bounds the operations that wait on them.
An open breaker for LiveKit fails fast instead of making callers wait for a dead provider.

### 7. Demo hardening

Per-IP, per-caller and clinic-wide buckets, `demo_hard_max_call_seconds`, demo daily minute/cost
caps, concurrency cap, kill switch. Cloudflare Turnstile is optional: set
`TRIAVOZ_TURNSTILE_SECRET` and send `turnstile_token` with the session request; it is verified
server-side (fail-closed when enabled and unavailable). `TRIAVOZ_TEST_REDIS_URL` makes CI run the
Lua integration tests against a real Redis.

## Consequences / risks

* If Redis is unavailable, limits and the HMAC replay cache fall back to process-local state;
  multi-replica protection (and cross-replica replay rejection) is weaker until Redis returns.
  Database budgets and provider breakers still apply.
* The abuse score is a triage aid, not proof. Only manual actions (spam/unblock) change access.
* `stt_confidence` depends on the LiveKit event attribute; `TODO(verify-docs)` marks it. The scorer
  already handles `None`.
* The telephony endpoint validates the internal HMAC; a real Twilio adapter still needs provider
  signature validation + TwiML behind it.
* Business-hours configuration is optional and fails open; a malformed value must never take voice
  down.
