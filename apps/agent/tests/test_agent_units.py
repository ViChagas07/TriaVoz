import json
from typing import Any

import httpx
import pytest

from triavoz_agent.api_client import SIGNATURE_HEADER, TIMESTAMP_HEADER, ApiError, TriaVozApi, sign
from triavoz_agent.config import WorkerConfig
from triavoz_agent.prompts import build_greeting_instructions, build_instructions
from triavoz_agent.telemetry import LatencyTracker, estimate_cost_cents, percentile

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
    assert seen["headers"][SIGNATURE_HEADER] == sign(SECRET, ts, seen["body"])


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
        max_call_seconds=300,
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
