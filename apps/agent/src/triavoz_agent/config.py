"""Worker settings from the environment. API keys for the providers are read by the LiveKit plugins
themselves (DEEPGRAM_API_KEY, ELEVEN_API_KEY, ANTHROPIC_API_KEY, LIVEKIT_*)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _f(name: str, default: float = 0.0) -> float:
    return float(os.environ.get(name, default))


@dataclass(frozen=True)
class WorkerConfig:
    api_url: str
    hmac_secret: str
    llm_model: str
    stt_model: str
    stt_language: str
    tts_voice_id: str
    tts_model: str
    tts_provider: str
    tts_language: str
    max_call_seconds: int
    max_turns: int
    silence_timeout_seconds: float
    emergency_grace_seconds: float
    # Unit prices are NOT hardcoded (vendors change them). Set them in the environment to get
    # a cost estimate per call; leave at 0 to record usage only.
    price_stt_per_minute_cents: float
    price_llm_per_million_input_tokens_cents: float
    price_llm_per_million_output_tokens_cents: float
    price_tts_per_thousand_chars_cents: float
    # Observability is opt-in; structured logs are the default.
    log_format: str = "json"
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.0
    sentry_release: str | None = None
    otel_exporter_endpoint: str | None = None
    otel_service_name: str = "triavoz-voice-worker"
    otel_sample_ratio: float = 1.0

    @classmethod
    def from_env(cls) -> WorkerConfig:
        return cls(
            api_url=os.environ.get("TRIAVOZ_API_URL", "http://localhost:8000").rstrip("/"),
            hmac_secret=os.environ["TRIAVOZ_INTERNAL_HMAC_SECRET"],
            llm_model=os.environ["TRIAVOZ_LLM_MODEL"],
            stt_model=os.environ.get("TRIAVOZ_STT_MODEL", "nova-3"),
            stt_language=os.environ.get("TRIAVOZ_STT_LANGUAGE", "pt-BR"),
            tts_voice_id=os.environ["TRIAVOZ_TTS_VOICE_ID"],
            tts_model=os.environ.get("TRIAVOZ_TTS_MODEL", ""),
            tts_provider=os.environ.get("TRIAVOZ_TTS_PROVIDER", "cartesia"),
            tts_language=os.environ.get("TRIAVOZ_TTS_LANGUAGE", "pt-BR"),
            max_call_seconds=int(os.environ.get("TRIAVOZ_MAX_CALL_SECONDS", "300")),
            max_turns=int(os.environ.get("TRIAVOZ_MAX_TURNS", "20")),
            silence_timeout_seconds=_f("TRIAVOZ_SILENCE_TIMEOUT_SECONDS", 15.0),
            emergency_grace_seconds=_f("TRIAVOZ_EMERGENCY_GRACE_SECONDS", 20.0),
            log_format=os.environ.get("TRIAVOZ_LOG_FORMAT", "json"),
            sentry_dsn=os.environ.get("TRIAVOZ_SENTRY_DSN") or None,
            sentry_traces_sample_rate=_f("TRIAVOZ_SENTRY_TRACES_SAMPLE_RATE"),
            sentry_release=os.environ.get("TRIAVOZ_SENTRY_RELEASE") or None,
            otel_exporter_endpoint=os.environ.get("TRIAVOZ_OTEL_EXPORTER_ENDPOINT") or None,
            otel_service_name=os.environ.get("TRIAVOZ_OTEL_SERVICE_NAME", "triavoz-voice-worker"),
            otel_sample_ratio=_f("TRIAVOZ_OTEL_SAMPLE_RATIO", 1.0),
            price_stt_per_minute_cents=_f("TRIAVOZ_PRICE_STT_PER_MIN_CENTS"),
            price_llm_per_million_input_tokens_cents=_f("TRIAVOZ_PRICE_LLM_IN_PER_M_CENTS"),
            price_llm_per_million_output_tokens_cents=_f("TRIAVOZ_PRICE_LLM_OUT_PER_M_CENTS"),
            price_tts_per_thousand_chars_cents=_f("TRIAVOZ_PRICE_TTS_PER_K_CHARS_CENTS"),
        )
