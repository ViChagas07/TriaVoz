"""Start a voice session only after the gatekeeper admits it.

The gatekeeper is the ONLY place that decides whether credits may be spent. Emergency hints are
answered with SAMU guidance even when every protection is active. A rejected call creates no
`calls` row and no room.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass

from triavoz.application.abuse.alerts import AlertService
from triavoz.application.abuse.gatekeeper import gatekeeper_for, rate_limits_from_settings
from triavoz.application.abuse.policy import (
    ClinicPolicy,
    GateDecision,
    clinic_policy_from_context,
)
from triavoz.application.abuse.ports import AbuseRepository, GateStore
from triavoz.application.voice.ports import VoiceRoomService, VoiceSessionRepository
from triavoz.config import Settings
from triavoz.observability.metrics import observe_gatekeeper_block
from triavoz.shared_kernel.emergency import EMERGENCY_MESSAGE
from triavoz.shared_kernel.errors import ServiceUnavailable

__all__ = ["StartVoiceSession", "VoiceSessionOutcome", "VoiceSessionResult", "room_metadata_json"]

log = logging.getLogger("triavoz.voice")


@dataclass(frozen=True)
class VoiceSessionResult:
    call_id: str
    room_name: str
    token: str
    url: str


@dataclass(frozen=True)
class VoiceSessionOutcome:
    decision: GateDecision
    session: VoiceSessionResult | None
    policy: ClinicPolicy
    timezone: str
    # Set when the call row was created but the provider failed. Returning normally lets the
    # route commit `status='failed'` before it answers 503; raising here would roll it back.
    provider_error: bool = False


class StartVoiceSession:
    """Creates the call (server-side tenant context) and the room, then returns a short token."""

    def __init__(
        self,
        repo: VoiceSessionRepository,
        rooms: VoiceRoomService,
        abuse: AbuseRepository,
        store: GateStore,
        settings: Settings,
        *,
        alert_service: AlertService | None = None,
    ) -> None:
        self._repo = repo
        self._rooms = rooms
        self._abuse = abuse
        self._store = store
        self._settings = settings
        self._alerts = alert_service

    async def execute(
        self,
        *,
        caller_number: str | None,
        client_ip: str,
        ttl_seconds: int,
        channel: str = "web",
        emergency: bool = False,
        demo_caps: bool = True,
        caller_verified: bool = False,
        caller_identity_hash: bytes | None = None,
    ) -> VoiceSessionOutcome:
        ctx = await self._repo.voice_context()
        if ctx is None:
            raise ServiceUnavailable("voice_clinic_unavailable")
        agent_config = ctx.get("agent_config") or {}
        ctx["emergency_message"] = agent_config.get("emergency_message") or EMERGENCY_MESSAGE

        policy = clinic_policy_from_context(
            ctx,
            demo_hard_max_call_seconds=(
                self._settings.demo_hard_max_call_seconds if demo_caps else None
            ),
            demo_daily_minute_budget=(
                self._settings.demo_daily_minute_budget if demo_caps else None
            ),
            demo_daily_cost_budget_cents=(
                self._settings.demo_daily_cost_budget_cents if demo_caps else None
            ),
        )
        clinic_id = ctx["clinic_id"]
        call_id = uuid.uuid4()
        gate = gatekeeper_for(
            clinic_id=clinic_id,
            policy=policy,
            repo=self._abuse,
            store=self._store,
            rate_limits=rate_limits_from_settings(self._settings),
            cooldown_seconds=self._settings.cost_breaker_cooldown_seconds,
            failure_threshold=self._settings.cost_breaker_failure_threshold,
            alerts=self._alerts,
        )
        decision = await gate.admit(
            caller_number=caller_number,
            client_ip=client_ip,
            slot_id=str(call_id),
            emergency=emergency,
            enforce_ip_limit=channel == "web",
        )
        if not decision.allowed:
            await self._repo.record_gatekeeper_block(decision.reason.value)
            observe_gatekeeper_block(decision.reason.value)
            return VoiceSessionOutcome(
                decision=decision, session=None, policy=policy, timezone=ctx["timezone"]
            )

        room_name = f"triavoz-{uuid.uuid4().hex[:16]}"
        try:
            await self._repo.create_call(
                call_id=call_id,
                room_name=room_name,
                caller_number=caller_number,
                channel=channel,
                caller_verified=caller_verified,
                caller_identity_hash=caller_identity_hash,
            )
            metadata = {
                "clinic_id": str(clinic_id),
                "call_id": str(call_id),
                "channel": channel,
                "caller_number": caller_number,
                "timezone": ctx["timezone"],
                "agent_config": agent_config,
                "max_call_seconds": policy.max_call_seconds,
                "max_turns": self._settings.demo_max_turns,
                "silence_timeout_seconds": self._settings.demo_silence_timeout_seconds,
                "emergency_message": policy.emergency_text(),
                "gatekeeper_probe": decision.breaker_probe,
            }
            room = await self._rooms.create_room(
                room_name=room_name,
                identity=f"{channel}-{uuid.uuid4().hex[:12]}",
                metadata=metadata,
                ttl_seconds=ttl_seconds,
            )
        except Exception as exc:
            await self._repo.fail_call(call_id)
            await gate.release(str(call_id))
            log.warning(
                "voice session failed clinic=%s call=%s error=%s",
                clinic_id,
                call_id,
                type(exc).__name__,
            )
            return VoiceSessionOutcome(
                decision=decision,
                session=None,
                policy=policy,
                timezone=ctx["timezone"],
                provider_error=True,
            )

        if self._alerts is not None:
            await self._alerts.record_call(clinic_id)
        log.info("voice session started clinic=%s call=%s channel=%s", clinic_id, call_id, channel)
        return VoiceSessionOutcome(
            decision=decision,
            session=VoiceSessionResult(str(call_id), room.room_name, room.token, room.url),
            policy=policy,
            timezone=ctx["timezone"],
        )


def room_metadata_json(metadata: dict[str, object]) -> str:
    return json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
