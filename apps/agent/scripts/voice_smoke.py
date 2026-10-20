"""Scripted audio caller for the live demo (dev tool, no secrets).

Uses LiveKit Inference TTS for the caller's voice, publishes real audio into the room created by
POST /api/v1/voice/session, then reads the persisted transcript through the staff API. This is
evidence tooling, not a test that runs in CI.

Run (API on :58001, worker registered with the same LiveKit project):
    poetry run python scripts/voice_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx
from livekit import rtc
from livekit.agents import inference, tts
from livekit.agents.utils import http_context

API = os.environ.get("SMOKE_API_URL", "http://127.0.0.1:58001")
CLINIC = os.environ.get("SMOKE_CLINIC", "clinica-horizonte")
EMAIL = os.environ.get("SMOKE_EMAIL", "admin@horizonte.demo")
PASSWORD = os.environ.get("SMOKE_PASSWORD", "Demo!TriaVoz2026")
CALLER = os.environ.get("SMOKE_CALLER", "+5571999900010")
CALLER_VOICE = os.environ.get("SMOKE_VOICE", "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc")

SCENARIOS = {
    "booking": [
        "Olá, quero marcar uma consulta, por favor.",
        "Consulta clínica. Meu nome é Maria Silva.",
        "Pode ser o primeiro horário que você ofereceu.",
        "Sim, pode confirmar.",
        "Obrigada, tchau.",
    ],
    "cancel": [
        "Olá, quero cancelar minha consulta, por favor.",
        "A consulta de amanhã às oito da manhã.",
        "Sim, pode cancelar.",
        "Obrigada, tchau.",
    ],
    "reschedule": [
        "Olá, quero remarcar minha consulta, por favor.",
        "A consulta de amanhã às nove e meia da manhã.",
        "Pode ser às dez da manhã?",
        "Sim, pode remarcar.",
        "Obrigada, tchau.",
    ],
    "urgency": [
        "Estou com dor no peito e falta de ar.",
        "Sim, por favor, registre o retorno.",
    ],
}
SCENARIO = os.environ.get("SMOKE_SCENARIO", "booking")
LINES = SCENARIOS[SCENARIO]


async def _synthesize(text: str) -> list[rtc.AudioFrame]:
    frames: list[rtc.AudioFrame] = []
    async with http_context.open():
        engine = inference.TTS("cartesia/sonic-3", voice=CALLER_VOICE, language="pt")
        try:
            async for event in engine.synthesize(text):
                if isinstance(event, tts.SynthesizedAudio):
                    frames.append(event.frame)
        finally:
            await engine.aclose()
    return frames


async def _turns(client: httpx.AsyncClient, token: str, call_id: str) -> list[dict[str, Any]]:
    response = await client.get(
        f"/api/v1/calls/{call_id}/turns",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return list(response.json())


async def _wait_agent_turn(
    client: httpx.AsyncClient, token: str, call_id: str, after: int, timeout: float = 30
) -> list[dict[str, Any]]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        turns = await _turns(client, token, call_id)
        agent = [t for t in turns if t["seq"] > after and t["speaker"] == "agent"]
        if agent:
            return turns
        await asyncio.sleep(0.5)
    return await _turns(client, token, call_id)


async def main() -> int:
    async with httpx.AsyncClient(base_url=API, timeout=60) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"clinic_code": CLINIC, "email": EMAIL, "password": PASSWORD},
        )
        login.raise_for_status()
        token = str(login.json()["access_token"])
        session = await client.post(
            "/api/v1/voice/session",
            json={"caller_number": CALLER, "clinic_code": CLINIC},
        )
        session.raise_for_status()
        room_info = session.json()
        call_id = str(room_info["call_id"])
        print(f"room={room_info['room_name']} call={call_id}")

        audio = [await _synthesize(line) for line in LINES]
        first = next(frame for group in audio for frame in group)
        room = rtc.Room()
        await room.connect(room_info["url"], room_info["token"])
        source = rtc.AudioSource(first.sample_rate, first.num_channels)
        track = rtc.LocalAudioTrack.create_audio_track("caller", source)
        await room.local_participant.publish_track(
            track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        )
        print(f"caller_joined sample_rate={first.sample_rate}")

        turns = await _wait_agent_turn(client, token, call_id, -1, timeout=60)
        print("greeting:", next((t["content"] for t in turns if t["speaker"] == "agent"), None))
        # The greeting ChatMessage can be persisted before RoomIO links the caller track. Let the
        # agent finish subscribing before sending speech.
        await asyncio.sleep(6.0)

        last_seq = max((int(t["seq"]) for t in turns), default=-1)
        for index, line in enumerate(LINES):
            print(f"caller[{index}]:", line)
            for frame in audio[index]:
                await source.capture_frame(frame)
                await asyncio.sleep(frame.samples_per_channel / frame.sample_rate)
            if index < len(LINES) - 1:
                turns = await _wait_agent_turn(client, token, call_id, last_seq, timeout=35)
                last_seq = max((int(t["seq"]) for t in turns), default=last_seq)
                agent_text = [t["content"] for t in turns if t["speaker"] == "agent"][-1:]
                print("agent:", agent_text)
                await asyncio.sleep(2.0)

        await asyncio.sleep(4)
        await room.disconnect()
        await asyncio.sleep(2)
        detail = await client.get(
            f"/api/v1/calls/{call_id}", headers={"Authorization": f"Bearer {token}"}
        )
        turns = await _turns(client, token, call_id)
        print("\nTRANSCRIPT")
        for turn in turns:
            print(f"{turn['seq']:>2} {turn['speaker']:<7} {turn.get('tool_name') or '':<20} {turn['content']}")
        print("\nCALL")
        print(json.dumps(detail.json(), indent=2, ensure_ascii=False))
        out = Path(os.environ.get("TEMP", ".")) / f"triavoz_voice_smoke_{uuid.uuid4().hex[:8]}.json"
        out.write_text(
            json.dumps({"turns": turns, "call": detail.json()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nartifact={out}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
