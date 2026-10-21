"""Worker entrypoint: one job per room. clinic_id / caller number come from ROOM METADATA written
by the TriaVoz API when it created the session — never from the browser or the LLM."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
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
from triavoz_agent.policy import HandoffPolicy
from triavoz_agent.prompts import build_instructions, greeting_text
from triavoz_agent.resilience import Bulkhead, CircuitBreaker, CircuitOpenError, guarded_call
from triavoz_agent.telemetry import LatencyTracker, TurnLatencyTracker, estimate_cost_cents

log = logging.getLogger("triavoz.agent")

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
    try:
        await asyncio.wait_for(ctx.connect(), timeout=10.0)
    except TimeoutError:
        log.error("LiveKit room connect timed out; closing job %s", ctx.room.name)
        return
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
    # The API writes the effective per-clinic cap; never exceed the worker's own hard ceiling.
    max_call_seconds = min(
        int(meta.get("max_call_seconds") or cfg.max_call_seconds), cfg.max_call_seconds
    )
    max_turns = int(meta.get("max_turns") or cfg.max_turns)
    silence_timeout = max(
        5.0, float(meta.get("silence_timeout_seconds") or cfg.silence_timeout_seconds)
    )
    emergency_message = str(
        meta.get("emergency_message")
        or agent_cfg.get("emergency_message")
        or "Se for uma emergência, ligue agora para o SAMU, no 192."
    )

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
    state: dict[str, Any] = {
        "seq": 0,
        "interruptions": 0,
        "last_user_at": time.monotonic(),
        "end_reason": None,
        "silence_warned": False,
        "emergency_grace_used": False,
        "provider_fallback_started": False,
    }
    policy = HandoffPolicy(max_turns=max_turns)
    provider_breaker = CircuitBreaker("voice-providers", failure_threshold=3, recovery_timeout=15)
    provider_bulkhead = Bulkhead("voice-providers", max_concurrency=4, wait_timeout=1.0)

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

    async def reply(instructions: str, *, deadline: float = 12.0) -> None:
        """Bulkhead + breaker + deadline around one LLM + TTS turn."""
        try:
            await guarded_call(
                lambda: session.generate_reply(instructions=instructions),
                breaker=provider_breaker,
                bulkhead=provider_bulkhead,
                deadline=deadline,
            )
        except CircuitOpenError:
            asyncio.create_task(provider_fallback())
        except Exception:
            log.warning("provider reply failed clinic=%s call=%s", clinic_id, call_id)

    async def trigger_handoff(reason: str, instructions: str) -> None:
        if call.handoff_requested:
            return
        message = await call.request_handoff(reason)
        await reply(f"{instructions} Diga também: {message}")

    async def trigger_emergency() -> None:
        """Emergency override: speaks SAMU guidance even if a handoff was already requested."""
        call.emergency_detected = True
        message = await call.request_handoff("urgency")
        await reply(
            "Interrompa o fluxo imediatamente. Avise que a ligação não substitui "
            f"atendimento de urgência e diga exatamente: {emergency_message} {message}",
            deadline=15.0,
        )

    async def warn_abuse() -> None:
        await reply(
            "Responda com calma, em uma frase, que a conversa precisa ser respeitosa "
            "e que você pode encerrar a ligação se isso continuar."
        )

    async def close_call(reason: str, *, delay: float = 0.0) -> None:
        if delay:
            await asyncio.sleep(delay)
        if done.is_set():
            return
        state["end_reason"] = reason
        with contextlib.suppress(Exception):
            await asyncio.wait_for(session.aclose(), timeout=5.0)
        done.set()

    async def close_after_handoff(reason: str) -> None:
        if policy.emergency:
            return
        await trigger_handoff(
            reason,
            "Explique em uma frase que a equipe vai retornar e que a ligação será encerrada.",
        )
        await close_call(reason, delay=4.0)

    async def provider_fallback() -> None:
        if done.is_set() or state["provider_fallback_started"]:
            return
        state["provider_fallback_started"] = True
        log.error("provider failure clinic=%s call=%s", clinic_id, call_id)
        with contextlib.suppress(Exception):
            await asyncio.wait_for(
                session.say(
                    "Estamos com uma instabilidade técnica. Vou registrar um retorno humano.",
                    allow_interruptions=False,
                ),
                timeout=6.0,
            )
        with contextlib.suppress(Exception):
            await call.request_handoff("provider_failure")
        await close_call("provider_failure")

    async def silence_watch() -> None:
        """One warning, then close when the caller goes silent after the greeting."""
        await asyncio.sleep(silence_timeout)
        while not done.is_set():
            if policy.emergency or call.handoff_requested:
                return
            idle = time.monotonic() - float(state["last_user_at"])
            if idle >= silence_timeout:
                if not state["silence_warned"]:
                    state["silence_warned"] = True
                    state["last_user_at"] = time.monotonic()
                    await reply("Pergunte em uma frase curta se a pessoa ainda está na linha.")
                else:
                    log.info("silence timeout clinic=%s call=%s", clinic_id, call_id)
                    await close_call("silence_timeout")
                    return
            await asyncio.sleep(1.0)

    def on_session_error(ev: Any) -> None:
        # TODO(verify-docs): the `error` event name/shape for livekit-agents 1.8.x.
        log.error("agent session error clinic=%s call=%s: %s", clinic_id, call_id, ev)
        asyncio.create_task(provider_fallback())

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
        turn: dict[str, Any] = {
            "speaker": "patient" if role == "user" else "agent",
            "content": str(text),
        }
        # TODO(verify-docs): attribute name for STT confidence in livekit-agents 1.8.x. The API
        # accepts `stt_confidence` on turns and the scorer penalizes consistently low values.
        confidence = getattr(item, "transcript_confidence", getattr(item, "confidence", None))
        if (
            role == "user"
            and isinstance(confidence, (int, float))
            and 0.0 <= float(confidence) <= 1.0
        ):
            turn["stt_confidence"] = float(confidence)
        add_turn(turn)
        if role == "user":
            state["last_user_at"] = time.monotonic()
            state["silence_warned"] = False
            event = policy.observe_user(str(text))
            if event == "urgency":
                asyncio.create_task(trigger_emergency())
            elif event == "abuse":
                asyncio.create_task(warn_abuse())
            elif event == "abuse_final":
                call.abusive_language_detected = True
                # Never log the caller's words or number; only the call ids and the event.
                log.warning("abusive language clinic=%s call=%s", clinic_id, call_id)
                asyncio.create_task(close_call("abusive_language"))
            elif event == "max_turns":
                asyncio.create_task(close_after_handoff("max_turns"))
        if role == "assistant":
            event = policy.observe_assistant(str(text))
            if event == "misunderstanding" and not policy.emergency:
                asyncio.create_task(
                    trigger_handoff(
                        "misunderstanding",
                        "Diga que não conseguiu entender e que registrou um pedido de retorno.",
                    )
                )

    session.on("metrics_collected", on_metrics)
    session.on("conversation_item_added", on_item)
    session.on("function_tools_executed", on_tools)
    session.on("error", on_session_error)
    session.on("close", lambda _ev: done.set())

    now = datetime.now(ZoneInfo(tz))
    log.info("agent session starting clinic=%s call=%s", clinic_id, call_id)
    start_failed = False
    try:
        # Bound provider startup: STT/LLM/TTS connections are established here.
        await guarded_call(
            lambda: session.start(
                room=ctx.room,
                agent=Receptionist(
                    call,
                    build_instructions(agent_cfg, today_iso=_today_label(now), timezone=tz),
                ),
            ),
            breaker=provider_breaker,
            bulkhead=provider_bulkhead,
            deadline=20.0,
        )
        log.info("agent session started; speaking greeting")
        # Direct TTS avoids an LLM cold start on the first audio; the LLM takes over on user turns.
        await guarded_call(
            lambda: session.say(
                greeting_text(agent_cfg), allow_interruptions=True, add_to_chat_ctx=True
            ),
            breaker=provider_breaker,
            bulkhead=provider_bulkhead,
            deadline=15.0,
        )
    except Exception:
        # Fallback: no agent session. Ask for a human callback; the API keeps the call record.
        log.exception("session start/greeting failed clinic=%s call=%s", clinic_id, call_id)
        start_failed = True
        state["end_reason"] = "provider_failure"
        with contextlib.suppress(Exception):
            await asyncio.wait_for(session.aclose(), timeout=5.0)
        with contextlib.suppress(Exception):
            await call.request_handoff("provider_failure")
    log.info("greeting requested")

    # The silence clock starts after the greeting, not when the job was created.
    state["last_user_at"] = time.monotonic()
    silence_task = asyncio.create_task(silence_watch()) if not start_failed else None
    reason = "provider_failure"
    if not start_failed:
        try:
            await asyncio.wait_for(done.wait(), timeout=max_call_seconds)
            reason = str(state["end_reason"] or "closed")
        except TimeoutError:
            reason = str(state["end_reason"] or "max_duration")
            if policy.emergency and not state["emergency_grace_used"]:
                # Give the SAMU guidance a brief window even when the hard cap was reached.
                state["emergency_grace_used"] = True
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(done.wait(), timeout=cfg.emergency_grace_seconds)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(session.aclose(), timeout=5.0)
    if silence_task is not None:
        silence_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await silence_task
    await asyncio.gather(*list(persist_tasks), return_exceptions=True)
    summary = usage.get_summary()
    usage_data = summary.__dict__.copy()
    usage_data["interruptions"] = state["interruptions"]
    usage_data["handoff_reason"] = call.handoff_reason
    usage_data["emergency_detected"] = call.emergency_detected
    cost = estimate_cost_cents(
        cfg,
        stt_seconds=float(usage_data.get("stt_audio_duration", 0.0) or 0.0),
        llm_input_tokens=int(usage_data.get("llm_prompt_tokens", 0) or 0),
        llm_output_tokens=int(usage_data.get("llm_completion_tokens", 0) or 0),
        tts_characters=int(usage_data.get("tts_characters_count", 0) or 0),
    )
    status = (
        "rejected"
        if reason in {"abusive_language", "max_turns", "silence_timeout"}
        else ("transferred" if call.handoff_completed else "completed")
    )
    try:
        if turns:
            # Final idempotent flush covers turns whose incremental request was in flight.
            await api.add_turns(clinic_id, call_id, turns)
        await api.end_call(
            clinic_id,
            call_id,
            status=status,
            end_reason=reason,
            duration_seconds=int(time.monotonic() - started),
            usage=usage_data,
            latency_ms=latency.summary_ms(),
            cost_cents=cost,
            handoff_requested=call.handoff_requested,
            handoff_completed=call.handoff_completed,
            abusive_language_detected=call.abusive_language_detected,
        )
    finally:
        await api.aclose()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
