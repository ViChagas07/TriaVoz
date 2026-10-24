from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from triavoz_agent.api_client import TriaVozApi

from evals.tools import SlotLedger, ToolResult, ToolRunner


@dataclass
class ScriptedAgent:
    """Deterministic policy that uses the same tools and confirmation rules as the worker.

    It never invents a time: every offer comes from `list_available_slots`, and an ISO time in
    speech or in a booking is checked against the offered set.
    """

    api: TriaVozApi
    clinic_id: str
    call_id: str
    ledger: SlotLedger = field(default_factory=SlotLedger)
    tool_events: list[Any] = field(default_factory=list)
    transcript: list[dict[str, str]] = field(default_factory=list)
    tools: ToolRunner = field(init=False)

    def __post_init__(self) -> None:
        self.tools = ToolRunner(
            self.api, self.clinic_id, self.call_id, ledger=self.ledger, events=self.tool_events
        )

    def say(self, text: str) -> None:
        self.ledger.record_speech(text)
        self.transcript.append({"speaker": "agent", "content": text})

    def patient(self, text: str) -> None:
        self.transcript.append({"speaker": "patient", "content": text})

    async def list_services(self) -> ToolResult:
        return await self.tools.call("list-services")

    async def list_slots(self, service_id: str, day: str) -> ToolResult:
        return await self.tools.call("list-slots", service_id=service_id, date=day)

    async def offer(self, slots: list[dict[str, Any]], limit: int = 3) -> None:
        chosen = slots[:limit]
        if chosen:
            self.say("Tenho estes horários: " + ", ".join(str(s["starts_at"]) for s in chosen))

    async def book(
        self,
        *,
        service_id: str,
        professional_id: str,
        starts_at: str,
        customer_name: str,
    ) -> ToolResult:
        self.say(f"Confirmo {customer_name}, {starts_at}. Posso confirmar o agendamento?")
        result = await self.tools.call(
            "book",
            service_id=service_id,
            professional_id=professional_id,
            starts_at=starts_at,
            customer_name=customer_name,
        )
        if result.ok:
            self.ledger.record_booking(starts_at)
            self.say("Agendamento confirmado.")
        else:
            self.say("Esse horário não está mais disponível. Vou consultar outros horários.")
        return result

    async def my_appointments(self) -> ToolResult:
        return await self.tools.call("my-appointments")

    async def cancel(self, appointment_id: str) -> ToolResult:
        result = await self.tools.call("cancel", appointment_id=appointment_id)
        if result.ok:
            self.say("Cancelamento confirmado.")
        return result

    async def reschedule(self, appointment_id: str, new_starts_at: str) -> ToolResult:
        self.say(f"Confirmo remarcar para {new_starts_at}. Posso confirmar?")
        result = await self.tools.call(
            "reschedule", appointment_id=appointment_id, new_starts_at=new_starts_at
        )
        if result.ok:
            self.ledger.record_booking(new_starts_at)
            self.say("Remarcação confirmada.")
        return result

    async def create_request(
        self, *, type_: str, title: str, description: str | None = None
    ) -> ToolResult:
        return await self.tools.call(
            "create-service-request", type=type_, title=title, description=description
        )

    async def handoff(self, reason: str) -> ToolResult:
        result = await self.create_request(
            type_="callback",
            title="Retorno humano solicitado",
            description=f"Motivo: {reason}",
        )
        if result.ok:
            self.say("Registrei seu pedido para a equipe retornar a ligação.")
        return result

    async def end(
        self,
        *,
        status: str,
        reason: str,
        handoff_requested: bool = False,
        abusive: bool = False,
        duration_seconds: int = 30,
    ) -> None:
        await self.api.end_call(
            self.clinic_id,
            self.call_id,
            status=status,
            end_reason=reason,
            duration_seconds=duration_seconds,
            usage={
                "tool_errors": self.tools.errors,
                "slot_taken_errors": sum(
                    1
                    for event in self.tool_events
                    if not event.ok and event.error in {"slot_taken", "slot_unavailable"}
                ),
            },
            latency_ms={
                "end_of_utterance": {"p50": 420.0, "p95": 610.0, "n": 3},
                "llm_ttft": {"p50": 700.0, "p95": 980.0, "n": 3},
                "tts_ttfb": {"p50": 180.0, "p95": 260.0, "n": 3},
                "time_to_first_audio": {"p50": 1300.0, "p95": 1800.0, "n": 3},
            },
            cost_cents=2.5,
            handoff_requested=handoff_requested,
            handoff_completed=False,
            abusive_language_detected=abusive,
        )
