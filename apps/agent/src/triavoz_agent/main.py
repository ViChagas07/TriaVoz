"""Worker entrypoint: one job per room. clinic_id / caller number come from ROOM METADATA written
by the TriaVoz API when it created the session — never from the browser or the LLM."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from livekit import agents
from livekit.agents import AgentSession, JobContext, WorkerOptions, cli, metrics
from livekit.plugins import anthropic, deepgram, elevenlabs, silero

from triavoz_agent.agent import CallContext, Receptionist
from triavoz_agent.api_client import TriaVozApi
from triavoz_agent.config import WorkerConfig
from triavoz_agent.prompts import build_greeting_instructions, build_instructions
from triavoz_agent.telemetry import LatencyTracker, estimate_cost_cents

log = logging.getLogger("triavoz.agent")


def prewarm(proc: agents.JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext) -> None:
    cfg = WorkerConfig.from_env()
    await ctx.connect()
    meta: dict[str, Any] = json.loads(ctx.room.metadata or "{}")
    clinic_id, channel = meta.get("clinic_id"), meta.get("channel", "web")
    if not clinic_id:
        log.error("room %s has no clinic_id in metadata; refusing to serve", ctx.room.name)
        return

    api = TriaVozApi(cfg.api_url, cfg.hmac_secret)
    call_id = await api.start_call(clinic_id, channel, ctx.room.name, meta.get("caller_number"))
    call = CallContext(api, clinic_id, call_id)
    tz = meta.get("timezone", "America/Bahia")
    agent_cfg: dict[str, Any] = meta.get("agent_config") or {}

    tts_kwargs: dict[str, Any] = {"voice_id": cfg.tts_voice_id}
    if cfg.tts_model:
        tts_kwargs["model"] = cfg.tts_model
    session: AgentSession[Any] = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model=cfg.stt_model, language=cfg.stt_language),
        llm=anthropic.LLM(model=cfg.llm_model),
        tts=elevenlabs.TTS(**tts_kwargs),
        allow_interruptions=True,  # barge-in: the caller can cut the agent off mid-sentence
        # TODO(P04, verify-docs): tune endpointing delays and try the semantic turn detector.
    )

    latency, usage = LatencyTracker(), metrics.UsageCollector()
    turns: list[dict[str, Any]] = []
    started = time.monotonic()
    done = asyncio.Event()

    def on_metrics(ev: agents.MetricsCollectedEvent) -> None:
        m = ev.metrics
        usage.collect(m)
        if isinstance(m, metrics.LLMMetrics):
            latency.record("llm_ttft", m.ttft)
        elif isinstance(m, metrics.TTSMetrics):
            latency.record("tts_ttfb", m.ttfb)
        elif isinstance(m, metrics.EOUMetrics):
            latency.record("end_of_utterance", m.end_of_utterance_delay)

    def on_item(ev: agents.ConversationItemAddedEvent) -> None:
        item = ev.item
        role = getattr(item, "role", None)
        text = getattr(item, "text_content", None)
        if role in ("user", "assistant") and text:
            turns.append(
                {
                    "seq": len(turns),
                    "speaker": "patient" if role == "user" else "agent",
                    "content": text,
                }
            )

    session.on("metrics_collected", on_metrics)
    session.on("conversation_item_added", on_item)
    session.on("close", lambda _ev: done.set())

    now = datetime.now(ZoneInfo(tz))
    await session.start(
        room=ctx.room,
        agent=Receptionist(
            call,
            build_instructions(agent_cfg, today_iso=now.strftime("%Y-%m-%d (%A)"), timezone=tz),
        ),
    )
    await session.generate_reply(instructions=build_greeting_instructions(agent_cfg))

    try:
        await asyncio.wait_for(done.wait(), timeout=cfg.max_call_seconds)  # hard cap on duration
        reason = "closed"
    except TimeoutError:
        reason = "max_duration"
        await session.aclose()
    finally:
        summary = usage.get_summary()
        cost = estimate_cost_cents(
            cfg,
            stt_seconds=float(getattr(summary, "stt_audio_duration", 0.0) or 0.0),
            llm_input_tokens=int(getattr(summary, "llm_prompt_tokens", 0) or 0),
            llm_output_tokens=int(getattr(summary, "llm_completion_tokens", 0) or 0),
            tts_characters=int(getattr(summary, "tts_characters_count", 0) or 0),
        )
        try:
            if turns:
                await api.add_turns(clinic_id, call_id, turns)
            await api.end_call(
                clinic_id,
                call_id,
                status="transferred" if call.handoff_requested else "completed",
                end_reason=reason,
                duration_seconds=int(time.monotonic() - started),
                usage=summary.__dict__ if hasattr(summary, "__dict__") else {},
                latency_ms=latency.summary_ms(),
                cost_cents=cost,
            )
        finally:
            await api.aclose()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
