"""The receptionist agent and its tools. Tools only call the TriaVoz API (RLS lives there)."""

from __future__ import annotations

from typing import Any

from livekit.agents import Agent, RunContext, ToolError, function_tool

from triavoz_agent.api_client import ApiError, TriaVozApi

_FRIENDLY = {
    "slot_taken": "Esse horário acabou de ser ocupado. Consulte os horários de novo e ofereça outros.",
    "slot_unavailable": "Esse horário não está disponível. Consulte os horários livres e ofereça outros.",
    "not_found": "Não encontrei isso. Confirme as informações com a pessoa.",
    "invalid_request": "Alguma informação está inválida. Confirme os dados com a pessoa.",
}


class CallContext:
    """Server-provided identifiers for this call. The LLM can neither see nor change them."""

    def __init__(self, api: TriaVozApi, clinic_id: str, call_id: str) -> None:
        self.api, self.clinic_id, self.call_id = api, clinic_id, call_id
        self.handoff_requested = False


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
    async def request_human_handoff(self, context: RunContext, reason: str) -> str:
        """Ask for a human attendant (caller asked, repeated misunderstandings, or an emergency).

        Args:
            reason: short reason, e.g. "caller_request", "misunderstanding", "urgency".
        """
        # TODO(P04, verify-docs): perform the real transfer (LiveKit SIP transfer / warm handoff).
        self._c.handoff_requested = True
        return (
            "Transferência ainda indisponível nesta demonstração. Diga que vai registrar o pedido "
            "para a equipe retornar a ligação e encerre com educação."
        )
