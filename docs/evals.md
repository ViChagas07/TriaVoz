# Agent evals (EDD)

The suite runs a **scripted patient + scripted agent policy in text mode** against the real
HMAC-signed `/internal/agent/tools/*` endpoints and a real PostgreSQL test database. It needs no
provider key, audio stack or LiveKit room, so the same deterministic subset runs in CI.

## Run

```bash
# Needs a migrated test DB (same variables as the API tests)
export TRIAVOZ_TEST_OWNER_DSN=postgresql://triavoz_owner:...@localhost:5432/triavoz
export TRIAVOZ_TEST_APP_DSN=postgresql://triavoz_app:...@localhost:5432/triavoz
export TRIAVOZ_TEST_REDIS_URL=redis://localhost:6379/15   # optional
cd apps/api && poetry run python -m evals

# single scenario / custom artifacts
poetry run python -m evals --scenario urgency_handoff
poetry run python -m evals --json-out evals/results/ci.json --markdown-out evals/results/ci.md
```

There is also `make evals`. The command exits non-zero if any scenario fails, any slot was
hallucinated, or handoff accuracy is below 100%.

## What is exercised

The harness seeds an isolated clinic with services, one professional and weekday availability, then
opens a real call through `POST /internal/agent/calls/start`. The scripted agent mirrors the worker’s
tool list and confirmation policy; the patient utterances are fixed so the suite is deterministic.
Every booking, cancellation, reschedule, handoff callback and ownership check goes through the real
API and PostgreSQL (RLS, exclusion constraint, idempotency, HMAC, replay guard).

| Scenario | What it proves |
|---|---|
| `happy_path_booking` | Lists services/slots, speaks only offered times, books and persists the appointment |
| `slot_taken_alternative` | A lost slot is refused; the agent re-lists and books a real alternative |
| `cancel_appointment` | Lists the caller’s own appointment and cancels it |
| `reschedule_appointment` | Moves the caller’s appointment to another free slot |
| `wrong_owner_cancel_refused` | Another phone’s appointment is never listed and cancel returns `not_found` |
| `prompt_injection` | Caller text cannot reveal other patients or book a non-offered time (API refuses) |
| `out_of_scope` | Clinical advice is refused and registered as a service request, with no booking |
| `urgency_handoff` | SAMU 192 guidance plus a persisted callback/handoff |
| `silence` | One warning, then close (pure `SilencePolicy`) |
| `abuse` | One warning, then close on the second abusive turn (pure `HandoffPolicy`) |

## Metrics

- **Task success** — every scenario check passed.
- **No-hallucinated-slot rate** — every ISO time spoken or booked must be in the set returned by
  `list_available_slots`; the suite requires **zero** hallucinated slots.
- **Tool-error recovery** — the slot-taken scenario must fail once, then recover and book.
- **Handoff correctness** — expected handoff (urgency) equals the actual persisted handoff.
- **Turns to completion** — patient + agent messages recorded by the harness.

## Latest local result

| Scenario | Success | Hallucinated slots | Tool errors | Recovery | Handoff | Turns |
|---|---:|---:|---:|---:|---:|---:|
| `happy_path_booking` | PASS | 0 | 0 | n/a | yes | 5 |
| `slot_taken_alternative` | PASS | 0 | 1 | yes | yes | 8 |
| `cancel_appointment` | PASS | 0 | 0 | n/a | yes | 2 |
| `reschedule_appointment` | PASS | 0 | 0 | n/a | yes | 4 |
| `wrong_owner_cancel_refused` | PASS | 0 | 1 | n/a | yes | 1 |
| `prompt_injection` | PASS | 0 | 1 | n/a | yes | 2 |
| `out_of_scope` | PASS | 0 | 0 | n/a | yes | 2 |
| `urgency_handoff` | PASS | 0 | 0 | n/a | yes | 3 |
| `silence` | PASS | 0 | 0 | n/a | yes | 0 |
| `abuse` | PASS | 0 | 0 | n/a | yes | 2 |

**10/10 scenarios · task success 100% · no-hallucinated-slot 100% · tool-error recovery 100% ·
handoff accuracy 100% · 2.9 average turns.**

Artifacts are written to `apps/api/evals/results/latest.json` (full transcript and tool events) and
`latest.md` (table). CI uploads `apps/api/evals/results/` as the `triavoz-evals` artifact.

## Scope / limitations

- The CI path uses a **scripted** agent policy, not the production LLM. It validates tool contracts,
  server-side guardrails, ownership, urgency and recovery, but not model phrasing or prompt
  adherence. A live-LLM variant can reuse the same `ToolRunner` when a provider key is available.
- Text only: STT/TTS/barge-in quality is covered by the manual voice checks in `PROGRESS.md`.
- The database is synthetic and isolated; the fixture deletes its clinic at the end.
