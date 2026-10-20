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
| reschedule (exact/confirmed, P04.1) | 99s | 1,498 / 1,773ms | 737 / 2,083ms | 291 / 1,018ms | 577ms | 0 | 4.00¢ |
| misunderstanding → handoff (P04.1) | 71s | 3,310 / 3,803ms | 536 / 1,016ms | 295 / 1,011ms | 2,493ms | 0 | 2.63¢ |
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

## P04.1 quality pass
- Exact-time reschedule verified: appointment moved **10:00 → 10:30 local**; the agent restated the
  new time and asked “Posso confirmar?”; the caller confirmed; only then did
  `reschedule_appointment` run and succeed (`86faa52b`, 4.00¢, TTFA p50 1,498 / p95 1,773ms).
- Two consecutive misunderstandings verified live (`8084229b`): the agent called
  `request_human_handoff`, persisted `handoff_requested=true`, and created a callback request;
  2.63¢. The trigger is also a pure `HandoffPolicy` with unit tests (urgency, two-clarification
  streak, reset).
- The earlier 09:30 slot-selection gap is closed for this flow; note the TTFA target fails on the
  misunderstanding call because long end-of-utterance pauses (2.49s) dominate.

## Known limitations
- First-call greetings after a worker restart can be delayed by provider cold start; a warm worker
  was used for the successful calls. Pre-warming TTS/LLM connections is still TODO.
- SIP transfer is code-complete but untested live (no trunk/number).
- The deployed Render `/voice/session` returned 500 during this session, so evidence was collected
  against the local API + LiveKit Cloud, not Render.
