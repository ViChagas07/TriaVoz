from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from triavoz_agent.api_client import TriaVozApi

from evals.agent import ScriptedAgent
from evals.fixtures import ClinicFixture


@dataclass
class EvalSession:
    api: TriaVozApi
    fixture: ClinicFixture
    phone: str
    call_id: str
    agent: ScriptedAgent
    ended: bool = False

    @classmethod
    async def open(
        cls, api: TriaVozApi, fixture: ClinicFixture, *, phone: str, channel: str = "phone"
    ) -> EvalSession:
        call_id = await api.start_call(str(fixture.clinic_id), channel, None, phone)
        return cls(
            api=api,
            fixture=fixture,
            phone=phone,
            call_id=call_id,
            agent=ScriptedAgent(api, str(fixture.clinic_id), call_id),
        )

    async def finish(self, *, status: str, reason: str, **kwargs: Any) -> None:
        if self.ended:
            return
        await self.agent.end(status=status, reason=reason, **kwargs)
        self.ended = True


async def book_for_phone(
    api: TriaVozApi,
    fixture: ClinicFixture,
    *,
    phone: str,
    slot: dict[str, Any],
    customer_name: str = "Paciente Avaliação",
) -> UUID:
    """Create an appointment through the real tool, from a different call/phone."""
    call_id = await api.start_call(str(fixture.clinic_id), "phone", None, phone)
    try:
        result = await api.tool(
            "book",
            str(fixture.clinic_id),
            call_id,
            service_id=str(fixture.service_id),
            professional_id=str(slot["professional_id"]),
            starts_at=str(slot["starts_at"]),
            customer_name=customer_name,
        )
        return UUID(str(result["appointment_id"]))
    finally:
        await api.end_call(
            str(fixture.clinic_id),
            call_id,
            status="completed",
            end_reason="setup",
            duration_seconds=1,
            usage={},
            latency_ms={},
            cost_cents=0,
        )
