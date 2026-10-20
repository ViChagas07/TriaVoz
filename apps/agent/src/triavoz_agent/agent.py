"""The receptionist agent and its tools. Tools only call the TriaVoz API (RLS lives there)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from livekit.agents import Agent, RunContext, ToolError, function_tool

from triavoz_agent.api_client import ApiError, TriaVozApi

log = logging.getLogger("triavoz.agent.tools")

_FRIENDLY = {
    "slot_taken": "Esse horário acabou de ser ocupado. Consulte os horários de novo e ofereça outros.",
    "slot_unavailable": "Esse horário não está disponível. Consulte os horários livres e ofereça outros.",
    "not_found": "Não encontrei isso. Confirme as informações com a pessoa.",
    "invalid_request": "Alguma informação está inválida. Confirme os dados com a pessoa.",
}


class CallContext:
    """Server-provided identifiers for this call. The LLM can neither see nor change them."""

    def __init__(
        self,
        api: TriaVozApi,
        clinic_id: str,
        call_id: str,
        *,
        channel: str = "web",
        sip_transfer: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self.api, self.clinic_id, self.call_id = api, clinic_id, call_id
        self.channel = channel
        self._sip_transfer = sip_transfer
        self.handoff_requested = False
        self.handoff_completed = False
        self.handoff_reason: str | None = None

    async def request_handoff(self, reason: str) -> str:
        if self.handoff_requested:
            return "O pedido de atendimento humano já foi registrado."
        self.handoff_requested = True
        self.handoff_reason = reason
        # Web demo fallback: persist a callback request tied to the caller's own phone.
        try:
            await self.api.tool(
                "create-service-request",
                self.clinic_id,
                self.call_id,
                type="callback",
                title="Retorno humano solicitado",
                description=f"Motivo: {reason}"[:500],
            )
        except ApiError as exc:
            log.warning("handoff callback could not be persisted: %s", exc.code)

        if self.channel == "sip" and self._sip_transfer is not None:
            try:
                await self._sip_transfer()
                self.handoff_completed = True
                return "Transferindo sua ligação para um atendente agora."
            except Exception:
                log.exception("SIP handoff failed; falling back to callback")
        return (
            "Registrei seu pedido para a equipe retornar a ligação. "
            "Se for uma urgência, procure atendimento imediatamente."
        )


class Receptionist(Agent):  # type: ignore[misc]
    def __init__(self, ctx: CallContext, instructions: str) -> None:
        super().__init__(instructions=instructions)
        self._c = ctx

    async def _call(self, name: str, **kwargs: Any) -> Any:
        try:
            return await self._c.api.tool(name, self._c.clinic_id, self._c.call_id, **kwargs)
        except ApiError as exc:
            raise ToolError(_FRIENDLY.get(exc.code, "Não consegui concluir agora.")) from exc

    @function_tool
    async def list_services(self, context: RunContext) -> list[dict[str, Any]]:
        """List the services this clinic offers (id, name, duration, price)."""
        return list(await self._call("list-services"))

    @function_tool
    async def list_available_slots(
        self,
        context: RunContext,
        service_id: str,
        date: str,
        professional_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the FREE appointment times for a service on a date.

        Args:
            service_id: id from list_services.
            date: the day, as YYYY-MM-DD.
            professional_id: optional professional id to filter by.
        """
        return list(
            await self._call(
                "list-slots", service_id=service_id, date=date, professional_id=professional_id
            )
        )

    @function_tool
    async def book_appointment(
        self,
        context: RunContext,
        service_id: str,
        professional_id: str,
        starts_at: str,
        customer_name: str,
    ) -> dict[str, Any]:
        """Book an appointment. Call ONLY after the caller explicitly confirmed it out loud.

        Args:
            service_id: id from list_services.
            professional_id: professional_id of the chosen slot.
            starts_at: the exact `starts_at` value (ISO 8601 with offset) of the chosen slot.
            customer_name: caller's name as confirmed.
        """
        return dict(
            await self._call(
                "book",
                service_id=service_id,
                professional_id=professional_id,
                starts_at=starts_at,
                customer_name=customer_name,
            )
        )

    @function_tool
    async def list_my_appointments(self, context: RunContext) -> list[dict[str, Any]]:
        """List the caller's own upcoming appointments (only those tied to the caller's phone)."""
        return list(await self._call("my-appointments"))

    @function_tool
    async def cancel_appointment(self, context: RunContext, appointment_id: str) -> dict[str, Any]:
        """Cancel one of the caller's appointments, after they confirmed it.

        Args:
            appointment_id: id from list_my_appointments.
        """
        return dict(await self._call("cancel", appointment_id=appointment_id))

    @function_tool
    async def reschedule_appointment(
        self, context: RunContext, appointment_id: str, new_starts_at: str
    ) -> dict[str, Any]:
        """Move one of the caller's appointments to another FREE slot, after they confirmed it.

        Args:
            appointment_id: id from list_my_appointments.
            new_starts_at: exact `starts_at` (ISO 8601 with offset) of a slot from list_available_slots.
        """
        return dict(
            await self._call(
                "reschedule", appointment_id=appointment_id, new_starts_at=new_starts_at
            )
        )

    @function_tool
    async def create_service_request(
        self,
        context: RunContext,
        type: Literal["appointment", "exam_pickup", "message", "callback", "other"],
        title: str,
        description: str | None = None,
        patient_name: str | None = None,
        requested_date: str | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Record a non-schedulable request (exam pickup, message, callback) for the staff.

        Use only when the caller needs something the scheduling tools cannot do. The caller's phone
        is attached server-side from the call; never ask for it or for a clinic id.

        Args:
            type: appointment, exam_pickup, message, callback or other.
            title: short summary for the staff.
            description: optional details, without clinical advice.
            patient_name: optional name the caller gave.
            requested_date: optional YYYY-MM-DD.
            due_date: optional YYYY-MM-DD.
        """
        return dict(
            await self._call(
                "create-service-request",
                type=type,
                title=title,
                description=description,
                patient_name=patient_name,
                requested_date=requested_date,
                due_date=due_date,
            )
        )

    @function_tool
    async def request_human_handoff(self, context: RunContext, reason: str) -> str:
        """Ask for a human attendant (caller asked, repeated misunderstandings, or an emergency).

        Args:
            reason: short reason, e.g. "caller_request", "misunderstanding", "urgency".
        """
        return await self._c.request_handoff(reason)
