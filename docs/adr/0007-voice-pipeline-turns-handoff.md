# ADR 0007 — Live voice pipeline, turn tuning, turn persistence and handoff

**Status:** accepted (P04)

## Providers actually used
- **STT:** Deepgram Nova-3, `pt-BR`, streaming with interim results (provided key verified).
- **LLM:** **LiveKit Cloud Inference** `openai/gpt-4.1-mini` using the provided LiveKit key. The
  supplied credential set did not include an Anthropic key, so the provider is behind the same
  LiveKit project instead of hardcoding a missing key.
- **TTS:** default **LiveKit Inference / Cartesia Sonic 3 `pt-BR`**. The supplied ElevenLabs key
  returns **401** (verified against `/v1/voices`, `/v1/models`, `/v1/user`); the ElevenLabs adapter
  remains selectable with `TRIAVOZ_TTS_PROVIDER=elevenlabs` once a valid key is provided.
- No keys are committed. Provider settings live in the ignored `.env`; the example file documents
  names and public prices only.

## Turn handling (measured profile)
`TurnHandlingOptions` with semantic turn detection, fixed endpointing 0.45–2.5s, adaptive
interruption (0.45s / 1 word, false-interruption resume after 2s) and preemptive generation/TTS.
Live calls showed **1–2 detected interruptions per call** and adaptive detection delays around
250–1,850ms. No formal baseline run was captured before tuning; this is a documented gap.

## Latency target and measurements
Target for the demo: **p50 time-to-first-audio ≤ 1.8s, p95 ≤ 2.8s** in the Brazil region.

| call | duration | TTFA p50/p95 | LLM TTFT p50/p95 | TTS TTFB p50/p95 | EOU p50 | interruptions | cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| booking | 88s | 1,629 / 2,697ms | 762 / 1,111ms | 296 / 1,010ms | 577ms | 1 | 3.36¢ |
| cancel | 50s | 1,424 / 2,342ms | 551 / 1,461ms | 296 / 1,018ms | 577ms | 2 | 2.73¢ |
| reschedule | 57s | 2,008 / 2,093ms | 678 / 1,144ms | 322 / 1,010ms | 577ms | 2 | 3.55¢ |
| urgency | 41s | 1,576ms (n=1) | 688 / 961ms | 1,000 / 1,010ms | 576ms | 1 | 1.75¢ |

`time_to_first_audio` is computed as EOU + LLM TTFT + TTS TTFB and stored per call in
`calls.latency_ms`; individual stages are stored too. The greeting is direct TTS and is not counted
as a user-turn TTFA.

## Persistence
Turns are POSTed incrementally as they arrive; the final flush is idempotent. Tool calls are
persisted from `function_tools_executed` with `tool_name` and a redacted payload (patient name,
phone, description/reason removed; output content never stored, only length/error).

## Handoff
- Web demo: `request_human_handoff` creates a `callback` service request tied to the caller's phone
  and returns a polite fallback message; the call records `handoff_requested=true`.
- Urgency keywords are detected server-side (fail-open): the agent speaks the SAMU 192 message and
  requests handoff; the normal booking flow is not blocked.
- SIP/phone: `SipHandoff` uses `LiveKitAPI.sip.transfer_sip_participant` with
  `TransferSIPParticipantRequest` (python `livekit-api` 1.2.x). It is implemented behind
  `TRIAVOZ_HANDOFF_SIP_URI` but **not exercised live** because no SIP trunk/number is configured.

## Known limitations
- The reschedule voice run moved the appointment to 09:30 instead of the requested 10:00; the
  prompt was tightened afterwards (explicit exact-time confirmation) but not re-run live.
- First-call greetings after a worker restart can be delayed by provider cold start; a warm worker
  path was used for the successful calls.
- The deployed Render `/voice/session` returned 500 during this session, so evidence was collected
  against the local API + LiveKit Cloud, not Render.
