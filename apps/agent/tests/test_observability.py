from __future__ import annotations

import json
import logging

from triavoz_agent.config import WorkerConfig
from triavoz_agent.observability import (
    ContextFilter,
    JsonFormatter,
    bind_call_context,
    init_sentry,
    setup_tracing,
)


def _config() -> WorkerConfig:
    return WorkerConfig(
        api_url="http://api",
        hmac_secret="secret",
        llm_model="model",
        stt_model="stt",
        stt_language="pt-BR",
        tts_voice_id="voice",
        tts_model="",
        tts_provider="cartesia",
        tts_language="pt-BR",
        max_call_seconds=300,
        max_turns=20,
        silence_timeout_seconds=15.0,
        emergency_grace_seconds=20.0,
        price_stt_per_minute_cents=0.0,
        price_llm_per_million_input_tokens_cents=0.0,
        price_llm_per_million_output_tokens_cents=0.0,
        price_tts_per_thousand_chars_cents=0.0,
    )


def test_worker_json_log_carries_call_ids_and_ignores_transcript_payload() -> None:
    bind_call_context(clinic_id="clinic-1", call_id="call-1")
    record = logging.LogRecord(
        "triavoz.agent", logging.INFO, __file__, 1, "agent session starting", (), None
    )
    record.transcript = "paciente disse algo"
    ContextFilter().filter(record)
    payload = json.loads(JsonFormatter(service="worker", environment="test").format(record))
    assert payload["clinic_id"] == "clinic-1"
    assert payload["call_id"] == "call-1"
    assert "transcript" not in payload
    assert "paciente disse algo" not in json.dumps(payload)


def test_worker_sentry_and_tracing_are_opt_in() -> None:
    cfg = _config()
    assert init_sentry(cfg) is False
    assert setup_tracing(cfg) is False
