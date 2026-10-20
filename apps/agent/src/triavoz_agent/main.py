"""Worker entrypoint: one job per room. clinic_id / caller number come from ROOM METADATA written
by the TriaVoz API when it created the session — never from the browser or the LLM."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from livekit import agents
from livekit.agents import (
    AgentSession,
    JobContext,
    TurnHandlingOptions,
    WorkerOptions,
    cli,
    inference,
    metrics,
)
from livekit.plugins import deepgram, elevenlabs, silero

from triavoz_agent.agent import CallContext, Receptionist
from triavoz_agent.api_client import ApiError, TriaVozApi
from triavoz_agent.config import WorkerConfig
from triavoz_agent.handoff import SipHandoff, find_caller_identity
from triavoz_agent.prompts import build_instructions, greeting_text
from triavoz_agent.telemetry import LatencyTracker, TurnLatencyTracker, estimate_cost_cents

log = logging.getLogger("triavoz.agent")

_URGENT = re.compile(
    r"dor no peito|falta de ar|sangramento|desmaio|infarto|avc|derrame|"
    r"emerg[eê]ncia|urgente|suic[ií]d|me matar|não consigo respirar",
    re.IGNORECASE,
)
_CLARIFY = re.compile(
    r"n[ãa]o entendi|pode repetir|n[ãa]o consegui entender|desculpe,? n[ãa]o",
    re.IGNORECASE,
)
_REDACT = {
    "customer_name",
    "patient_name",
    "caller_number",
    "caller_phone",
    "phone",
    "phone_number",
    "description",
    "reason",
}
_WEEKDAYS = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}


def prewarm(proc: agents.JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


def _today_label(now: datetime) -> str:
    return f"{now.strftime('%Y-%m-%d')} ({_WEEKDAYS[now.weekday()]})"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if key.lower() in _REDACT else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def redact_tool_arguments(raw: str) -> dict[str, Any]:
    """Pure helper (unit-tested): never persist patient names/phones/free-text descriptions."""
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {"arguments": "[unparseable]"}
    return _redact(parsed) if isinstance(parsed, dict) else {"arguments": "[unexpected]"}


def _livekit_http_url() -> str:
    configured = os.environ.get("TRIAVOZ_LIVEKIT_HTTP_URL")
    if configured:
        return configured.rstrip("/")
    url = os.environ.get("LIVEKIT_URL", "ws://localhost:7880")
    return url.replace("wss://", "https://").replace("ws://", "http://").rstrip("/")


async def entrypoint(ctx: JobContext) -> None:
    cfg = WorkerConfig.from_env()
    await ctx.connect()
    meta: dict[str, Any] = json.loads(ctx.room.metadata or "{}")
    clinic_id, channel = meta.get("clinic_id"), meta.get("channel", "web")
    if not clinic_id:
        log.error("room %s has no clinic_id in metadata; refusing to serve", ctx.room.name)
        return
    if not cfg.llm_model:
        log.error("TRIAVOZ_LLM_MODEL is empty; refusing to start a session")
        return

    api = TriaVozApi(cfg.api_url, cfg.hmac_secret)
    call_id = (
        str(meta["call_id"])
        if meta.get("call_id")
        else await api.start_call(clinic_id, channel, ctx.room.name, meta.get("caller_number"))
    )

    handoff_uri = os.environ.get("TRIAVOZ_HANDOFF_SIP_URI", "").strip()

    async def sip_transfer() -> None:
        identity = find_caller_identity(ctx.room)
        if not identity:
            raise RuntimeError("no SIP participant to transfer")
        await SipHandoff(
            http_url=_livekit_http_url(),
            api_key=os.environ["LIVEKIT_API_KEY"],
            api_secret=os.environ["LIVEKIT_API_SECRET"],
            room_name=ctx.room.name,
            participant_identity=identity,
            transfer_to=handoff_uri,
        )()

    call = CallContext(
        api,
        clinic_id,
        call_id,
        channel=channel,
        sip_transfer=sip_transfer if channel == "sip" and handoff_uri else None,
    )
    tz = meta.get("timezone", "America/Bahia")
    agent_cfg: dict[str, Any] = meta.get("agent_config") or {}

    if cfg.tts_provider == "elevenlabs":
        tts: Any = elevenlabs.TTS(
            voice_id=cfg.tts_voice_id,
            model=cfg.tts_model or "eleven_flash_v2_5",
            language="pt",
            streaming_latency=3,
        )
    else:
        # Fallback used by the demo because the supplied ElevenLabs key returns 401.
        # LiveKit Inference keeps the same LIVEKIT_API_KEY/SECRET and supports Portuguese.
        tts = inference.TTS(
            model=cfg.tts_model or "cartesia/sonic-3",
            voice=cfg.tts_voice_id,
            language=cfg.tts_language,
        )

    session: AgentSession[Any] = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(
            model=cfg.stt_model,
            language=cfg.stt_language,
            smart_format=True,
            interim_results=True,
        ),
        # LiveKit Cloud Inference: the provided LIVEKIT_API_KEY/SECRET are the only credentials.
        # Keeps the demo independent from a separate Anthropic key while preserving tool calling.
        llm=inference.LLM(cfg.llm_model),
        tts=tts,
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            endpointing={"mode": "fixed", "min_delay": 0.45, "max_delay": 2.5},
            interruption={
                "mode": "adaptive",
                "min_duration": 0.45,
                "min_words": 1,
                "false_interruption_timeout": 2.0,
                "resume_false_interruption": True,
            },
            preemptive_generation={
                "enabled": True,
                "preemptive_tts": True,
                "max_speech_duration": 10.0,
                "max_retries": 3,
            },
        ),
    )

    latency = LatencyTracker()
    turn_latency = TurnLatencyTracker(latency)
    usage = metrics.UsageCollector()
    turns: list[dict[str, Any]] = []
    persist_tasks: set[asyncio.Task[None]] = set()
    started = time.monotonic()
    done = asyncio.Event()
    state = {"seq": 0, "clarify_streak": 0, "interruptions": 0}

    async def persist_turn(turn: dict[str, Any]) -> None:
        try:
            await api.add_turns(clinic_id, call_id, [turn])
        except ApiError as exc:
            log.warning("incremental turn persist failed: %s", exc.code)
        except Exception:
            log.exception("incremental turn persist failed")

    def add_turn(turn: dict[str, Any]) -> None:
        turn["seq"] = state["seq"]
        state["seq"] += 1
        turns.append(turn)
        task = asyncio.create_task(persist_turn(turn))
        persist_tasks.add(task)
        task.add_done_callback(persist_tasks.discard)

    async def trigger_handoff(reason: str, instructions: str) -> None:
        if call.handoff_requested:
            return
        message = await call.request_handoff(reason)
        await session.generate_reply(instructions=f"{instructions} Diga também: {message}")

    def on_metrics(ev: agents.MetricsCollectedEvent) -> None:
        m = ev.metrics
        usage.collect(m)
        if isinstance(m, metrics.LLMMetrics):
            turn_latency.record("llm_ttft", m.ttft)
        elif isinstance(m, metrics.TTSMetrics):
            turn_latency.record("tts_ttfb", m.ttfb)
        elif isinstance(m, metrics.EOUMetrics):
            turn_latency.record("end_of_utterance", m.end_of_utterance_delay)
        elif isinstance(m, metrics.InterruptionMetrics):
            state["interruptions"] += m.num_interruptions
            latency.record("interruption_detection", m.detection_delay)

    def on_tools(ev: agents.FunctionToolsExecutedEvent) -> None:
        for call, output in ev.zipped():
            add_turn(
                {
                    "speaker": "tool",
                    "content": "",
                    "tool_name": call.name,
                    "tool_payload": {
                        "arguments": redact_tool_arguments(call.arguments),
                        "is_error": bool(output.is_error),
                        "output_chars": len(output.output or ""),
                    },
                }
            )

    def on_item(ev: agents.ConversationItemAddedEvent) -> None:
        item = ev.item
        item_type = getattr(item, "type", "")
        if item_type in ("function_call", "function_call_output"):
            return

        role = getattr(item, "role", None)
        text = getattr(item, "text_content", None)
        if role not in ("user", "assistant") or not text:
            return
        add_turn({"speaker": "patient" if role == "user" else "agent", "content": str(text)})
        if role == "user" and _URGENT.search(str(text)) and not call.handoff_requested:
            asyncio.create_task(
                trigger_handoff(
                    "urgency",
                    "Interrompa o fluxo. Diga para procurar o SAMU 192 imediatamente.",
                )
            )
        if role == "assistant":
            if _CLARIFY.search(str(text)):
                state["clarify_streak"] += 1
                if state["clarify_streak"] >= 2 and not call.handoff_requested:
                    asyncio.create_task(
                        trigger_handoff(
                            "misunderstanding",
                            "Diga que não conseguiu entender e que registrou um pedido de retorno.",
                        )
                    )
            else:
                state["clarify_streak"] = 0

    session.on("metrics_collected", on_metrics)
    session.on("conversation_item_added", on_item)
    session.on("function_tools_executed", on_tools)
    session.on("close", lambda _ev: done.set())

    now = datetime.now(ZoneInfo(tz))
    log.info("agent session starting clinic=%s call=%s", clinic_id, call_id)
    await session.start(
        room=ctx.room,
        agent=Receptionist(
            call,
            build_instructions(agent_cfg, today_iso=_today_label(now), timezone=tz),
        ),
    )
    log.info("agent session started; speaking greeting")
    # Direct TTS avoids an LLM cold start on the first audio; the LLM takes over on user turns.
    await session.say(greeting_text(agent_cfg), allow_interruptions=True, add_to_chat_ctx=True)
    log.info("greeting requested")

    try:
        await asyncio.wait_for(done.wait(), timeout=cfg.max_call_seconds)
        reason = "closed"
    except TimeoutError:
        reason = "max_duration"
        await session.aclose()
    finally:
        await asyncio.gather(*list(persist_tasks), return_exceptions=True)
        summary = usage.get_summary()
        usage_data = summary.__dict__.copy()
        usage_data["interruptions"] = state["interruptions"]
        usage_data["handoff_reason"] = call.handoff_reason
        cost = estimate_cost_cents(
            cfg,
            stt_seconds=float(usage_data.get("stt_audio_duration", 0.0) or 0.0),
            llm_input_tokens=int(usage_data.get("llm_prompt_tokens", 0) or 0),
            llm_output_tokens=int(usage_data.get("llm_completion_tokens", 0) or 0),
            tts_characters=int(usage_data.get("tts_characters_count", 0) or 0),
        )
        try:
            if turns:
                # Final idempotent flush covers turns whose incremental request was in flight.
                await api.add_turns(clinic_id, call_id, turns)
            await api.end_call(
                clinic_id,
                call_id,
                status="transferred" if call.handoff_completed else "completed",
                end_reason=reason,
                duration_seconds=int(time.monotonic() - started),
                usage=usage_data,
                latency_ms=latency.summary_ms(),
                cost_cents=cost,
                handoff_requested=call.handoff_requested,
                handoff_completed=call.handoff_completed,
            )
        finally:
            await api.aclose()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
