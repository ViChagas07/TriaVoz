"""Staff-facing application service: mutations + audit/events, no HTTP and no SQL."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any
from uuid import UUID

from triavoz.application.abuse.alerts import AlertService
from triavoz.application.auth.ports import PasswordHasher
from triavoz.application.events import EventPublisher
from triavoz.application.staff.ports import CallSummaryGenerator, StaffRepository
from triavoz.shared_kernel.errors import Conflict, NotFound, ServiceUnavailable


class StaffService:
    def __init__(
        self,
        repo: StaffRepository,
        events: EventPublisher,
        hasher: PasswordHasher,
        summary_generator: CallSummaryGenerator,
        alerts: AlertService | None = None,
    ) -> None:
        self._repo = repo
        self._events = events
        self._hasher = hasher
        self._summary = summary_generator
        self._alerts = alerts

    async def update_request(
        self,
        request_id: UUID,
        *,
        title: str | None,
        description: str | None,
        priority: str | None,
        due_date: date | None,
        actor_id: UUID,
    ) -> dict[str, Any]:
        updated = await self._repo.update_request(
            request_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
        )
        if updated is None:
            raise NotFound("request")
        await self._repo.add_request_event(
            request_id, "updated", user_id=actor_id, note="request updated"
        )
        await self._events.publish(
            updated["clinic_id"], "request.updated", {"request_id": str(request_id)}
        )
        return updated

    async def assign_request(
        self, request_id: UUID, *, user_id: UUID, actor_id: UUID
    ) -> dict[str, Any]:
        updated = await self._repo.assign_request(request_id, user_id)
        if updated is None:
            raise NotFound("request")
        await self._repo.add_request_event(
            request_id, "assigned", user_id=actor_id, note=str(user_id)
        )
        await self._events.publish(
            updated["clinic_id"],
            "request.assigned",
            {"request_id": str(request_id), "assigned_to": str(user_id)},
        )
        return updated

    async def complete_request(self, request_id: UUID, *, actor_id: UUID) -> dict[str, Any]:
        updated = await self._repo.complete_request(request_id)
        if updated is None:
            raise NotFound("request")
        await self._repo.add_request_event(request_id, "completed", user_id=actor_id)
        await self._events.publish(
            updated["clinic_id"], "request.completed", {"request_id": str(request_id)}
        )
        return updated

    async def mark_spam(
        self, request_id: UUID, *, actor_id: UUID, expires_in_days: int | None = None
    ) -> dict[str, Any]:
        updated = await self._repo.mark_request_spam(request_id, expires_in_days=expires_in_days)
        if updated is None:
            raise NotFound("request")
        await self._repo.add_request_event(
            request_id, "marked_spam", user_id=actor_id, note="blocklist updated"
        )
        await self._events.publish(
            updated["clinic_id"], "request.spam", {"request_id": str(request_id)}
        )
        if self._alerts is not None:
            await self._alerts.record_prank_flag(updated["clinic_id"])
        return updated

    async def create_user(
        self,
        *,
        email: str,
        full_name: str,
        role: str,
        password: str,
        actor_id: UUID,
    ) -> dict[str, Any]:
        if role not in {"admin", "attendant"}:
            raise Conflict("role")
        password_hash = await asyncio.to_thread(self._hasher.hash, password)
        try:
            user = await self._repo.create_user(
                email=email, full_name=full_name, role=role, password_hash=password_hash
            )
        except Exception as exc:
            # Unique (clinic_id, email) is the only expected integrity failure here.
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise Conflict("email_exists") from exc
            raise
        await self._repo.add_audit(
            action="team.create",
            resource_type="clinic_user",
            resource_id=str(user["id"]),
            user_id=actor_id,
            ip=None,
        )
        return user

    async def deactivate_user(self, user_id: UUID, *, actor_id: UUID) -> dict[str, Any]:
        if user_id == actor_id:
            raise Conflict("cannot_deactivate_self")
        user = await self._repo.deactivate_user(user_id)
        if user is None:
            raise NotFound("user")
        await self._repo.add_audit(
            action="team.deactivate",
            resource_type="clinic_user",
            resource_id=str(user_id),
            user_id=actor_id,
            ip=None,
        )
        return user

    async def add_blocked(
        self,
        *,
        e164: str,
        reason: str | None,
        actor_id: UUID,
        expires_in_days: int | None = None,
    ) -> dict[str, Any]:
        blocked = await self._repo.add_blocked(
            e164=e164,
            reason=reason,
            source="manual",
            expires_in_days=expires_in_days,
        )
        await self._repo.add_audit(
            action="blocked.add",
            resource_type="blocked_number",
            resource_id=str(blocked["id"]),
            user_id=actor_id,
            ip=None,
        )
        return blocked

    async def delete_blocked(self, blocked_id: UUID, *, actor_id: UUID) -> None:
        await self._remove_block(blocked_id, actor_id=actor_id, action="blocked.delete")

    async def unblock(self, blocked_id: UUID, *, actor_id: UUID) -> None:
        """Explicit human override: the "unblock" action in the feedback loop."""
        await self._remove_block(blocked_id, actor_id=actor_id, action="blocked.unblock")

    async def _remove_block(self, blocked_id: UUID, *, actor_id: UUID, action: str) -> None:
        deleted = await self._repo.delete_blocked(blocked_id)
        if not deleted:
            raise NotFound("blocked_number")
        await self._repo.add_audit(
            action=action,
            resource_type="blocked_number",
            resource_id=str(blocked_id),
            user_id=actor_id,
            ip=None,
        )

    async def save_config(self, *, config: dict[str, Any], actor_id: UUID) -> dict[str, Any]:
        version = await self._repo.next_config_version()
        created = await self._repo.create_config(
            version=version, config=config, created_by=actor_id, status="draft"
        )
        await self._repo.add_audit(
            action="agent_config.draft",
            resource_type="agent_config",
            resource_id=str(version),
            user_id=actor_id,
            ip=None,
        )
        return created

    async def publish_config(self, version: int, *, actor_id: UUID) -> dict[str, Any]:
        published = await self._repo.publish_config(version)
        if published is None:
            raise NotFound("agent_config")
        await self._repo.add_audit(
            action="agent_config.publish",
            resource_type="agent_config",
            resource_id=str(version),
            user_id=actor_id,
            ip=None,
        )
        await self._events.publish(
            published["clinic_id"], "agent_config.published", {"version": version}
        )
        return published

    async def rollback_config(self, version: int, *, actor_id: UUID) -> dict[str, Any]:
        target = await self._repo.get_config_version(version)
        if target is None:
            raise NotFound("agent_config")
        new_version = await self._repo.next_config_version()
        await self._repo.create_config(
            version=new_version,
            config=target["config"],
            created_by=actor_id,
            status="draft",
        )
        published = await self._repo.publish_config(new_version)
        assert published is not None
        await self._repo.add_audit(
            action="agent_config.rollback",
            resource_type="agent_config",
            resource_id=str(new_version),
            user_id=actor_id,
            ip=None,
        )
        return published

    async def summarize_call(self, call_id: UUID, *, actor_id: UUID) -> str:
        call = await self._repo.get_call(call_id)
        if call is None:
            raise NotFound("call")
        turns = await self._repo.get_call_turns(call_id)
        summary = await self._summary.summarize(call, turns)
        if not summary:
            raise ServiceUnavailable("summary_generator_not_configured")
        await self._repo.set_call_summary(call_id, summary)
        await self._repo.add_audit(
            action="call.summary.generate",
            resource_type="call",
            resource_id=str(call_id),
            user_id=actor_id,
            ip=None,
        )
        return summary
