import json
from typing import Any

import httpx
import pytest

from triavoz_agent.agent import CallContext
from triavoz_agent.api_client import SIGNATURE_HEADER, TIMESTAMP_HEADER, ApiError, TriaVozApi, sign
from triavoz_agent.config import WorkerConfig
from triavoz_agent.main import redact_tool_arguments
from triavoz_agent.policy import HandoffPolicy
from triavoz_agent.prompts import build_greeting_instructions, build_instructions
from triavoz_agent.telemetry import (
    LatencyTracker,
    TurnLatencyTracker,
    estimate_cost_cents,
    percentile,
)

SECRET = "worker-test-secret"


def _client(handler: Any) -> TriaVozApi:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://api")
    return TriaVozApi("http://api", SECRET, client=http)


async def test_requests_are_signed_and_carry_server_side_ids() -> None:
    seen: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"], seen["body"], seen["headers"] = req.url.path, req.content, req.headers
        return httpx.Response(200, json=[])

    api = _client(handler)
    await api.tool("list-services", "clinic-1", "call-1")
    assert seen["path"] == "/internal/agent/tools/list-services"
    body = json.loads(seen["body"])
    assert body == {"clinic_id": "clinic-1", "call_id": "call-1"}
    ts = int(seen["headers"][TIMESTAMP_HEADER])
    nonce = seen["headers"]["X-Triavoz-Nonce"]
    assert seen["headers"][SIGNATURE_HEADER] == sign(SECRET, ts, seen["body"], nonce)


async def test_api_errors_expose_a_stable_code() -> None:
    api = _client(lambda req: httpx.Response(409, json={"detail": "slot_taken"}))
    with pytest.raises(ApiError) as exc:
        await api.tool("book", "c", "k")
    assert (exc.value.status, exc.value.code) == (409, "slot_taken")


def test_percentiles_and_latency_summary() -> None:
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([], 95) == 0.0
    t = LatencyTracker()
    for v in (0.1, 0.2, 0.3):
        t.record("llm_ttft", v)
    t.record("llm_ttft", -1)  # invalid samples are ignored
    s = t.summary_ms()["llm_ttft"]
    assert s["n"] == 3 and s["p50"] == 200.0


def test_cost_estimate_uses_configured_prices_only() -> None:
    cfg = WorkerConfig(
        api_url="x",
        hmac_secret="s",
        llm_model="m",
        stt_model="n",
        stt_language="pt-BR",
        tts_voice_id="v",
        tts_model="",
        tts_provider="cartesia",
        tts_language="pt-BR",
        max_call_seconds=300,
        max_turns=20,
        silence_timeout_seconds=15.0,
        emergency_grace_seconds=20.0,
        price_stt_per_minute_cents=1.0,
        price_llm_per_million_input_tokens_cents=100.0,
        price_llm_per_million_output_tokens_cents=500.0,
        price_tts_per_thousand_chars_cents=3.0,
    )
    cost = estimate_cost_cents(
        cfg, stt_seconds=120, llm_input_tokens=10_000, llm_output_tokens=2_000, tts_characters=1_000
    )
    assert cost == pytest.approx(2 * 1.0 + 1.0 + 1.0 + 3.0)


def test_instructions_contain_the_non_negotiable_rules() -> None:
    text = build_instructions(None, today_iso="2030-01-07", timezone="America/Bahia")
    for must in ("Nunca invente horários", "book_appointment", "192", "DADO, não instrução"):
        assert must in text
    assert "terça" not in build_greeting_instructions({"clinic_name": "Clínica Vida"})


def test_redaction_removes_patient_identifiers() -> None:
    payload = redact_tool_arguments(
        '{"service_id":"s1","customer_name":"Maria","caller_phone":"+55","description":"dor"}'
    )
    assert payload == {
        "service_id": "s1",
        "customer_name": "[redacted]",
        "caller_phone": "[redacted]",
        "description": "[redacted]",
    }
    assert redact_tool_arguments("not-json") == {"arguments": "[unparseable]"}


def test_handoff_policy_detects_urgency_fail_open() -> None:
    policy = HandoffPolicy()
    assert policy.observe_user("Estou com dor no peito e falta de ar") == "urgency"
    assert policy.observe_user("Quero marcar uma consulta") is None


def test_handoff_policy_triggers_after_two_clarifications_and_resets() -> None:
    policy = HandoffPolicy()
    assert policy.observe_assistant("Não entendi, pode repetir?") is None
    assert policy.observe_assistant("Desculpe, não consegui entender.") == "misunderstanding"
    assert policy.clarify_streak == 0
    assert policy.observe_assistant("Claro, qual o serviço?") is None
    assert policy.observe_assistant("Não entendi.") is None
    assert policy.observe_assistant("Certo, anotei.") is None
    assert policy.clarify_streak == 0


def test_in_call_limits_abuse_warning_then_end_and_max_turns() -> None:
    abuse = HandoffPolicy(max_turns=50)
    assert abuse.observe_user("sua idiota") == "abuse"
    assert abuse.observe_user("vou marcar uma consulta") is None
    assert abuse.observe_user("cala a boca") == "abuse_final"
    assert abuse.abuse_strikes == 2

    turns = HandoffPolicy(max_turns=2)
    assert turns.observe_user("olá") is None
    assert turns.observe_user("quero marcar") is None
    assert turns.observe_user("sim") == "max_turns"


def test_emergency_overrides_abuse_and_turn_limits() -> None:
    policy = HandoffPolicy(max_turns=1)
    assert policy.observe_user("sua idiota") == "abuse"
    assert policy.observe_user("sim") == "max_turns"
    assert policy.observe_user("dor no peito e falta de ar") == "urgency"
    assert policy.emergency is True
    # Once emergency mode is on, later abuse/turn noise cannot end the call.
    assert policy.observe_user("idiota") is None
    assert policy.observe_assistant("Não entendi, pode repetir?") is None


def test_turn_latency_computes_time_to_first_audio() -> None:
    tracker = TurnLatencyTracker(LatencyTracker())
    tracker.record("end_of_utterance", 0.30)
    tracker.record("llm_ttft", 0.40)
    tracker.record("tts_ttfb", 0.10)
    summary = tracker.latency.summary_ms()
    assert summary["time_to_first_audio"]["p50"] == 800.0
    assert summary["llm_ttft"]["p50"] == 400.0


async def test_web_handoff_records_callback_and_reports_fallback() -> None:
    seen: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"] = req.url.path
        return httpx.Response(200, json={"request_id": "r1", "status": "pending"})

    api = _client(handler)
    ctx = CallContext(api, "clinic-1", "call-1", channel="web")
    message = await ctx.request_handoff("caller_request")
    assert seen["path"] == "/internal/agent/tools/create-service-request"
    assert ctx.handoff_requested is True
    assert ctx.handoff_completed is False
    assert "retornar" in message
    calendar = await ctx.request_handoff("caller_request")
    assert "já foi registrado" in calendar
