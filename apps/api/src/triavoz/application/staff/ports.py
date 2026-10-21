from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID


class StaffRepository(Protocol):
    """Tenant-bound repository for staff operations. RLS is the isolation mechanism."""

    async def clinic_timezone(self) -> str: ...
    async def get_clinic_settings(self) -> dict[str, Any]: ...
    async def update_clinic_settings(
        self,
        *,
        name: str,
        timezone: str,
        business_hours: dict[str, Any] | None,
        max_call_seconds: int,
        max_concurrent_calls: int,
        daily_minute_budget: int,
        daily_cost_budget_cents: int,
        kill_switch: bool,
        hidden_caller_policy: str,
    ) -> dict[str, Any]: ...

    # Catalog (settings screen)
    async def list_services(self) -> list[dict[str, Any]]: ...
    async def create_service(
        self, *, name: str, duration_min: int, price_cents: int
    ) -> dict[str, Any]: ...
    async def update_service(
        self,
        service_id: UUID,
        *,
        name: str | None,
        duration_min: int | None,
        price_cents: int | None,
        is_active: bool | None,
    ) -> dict[str, Any] | None: ...
    async def deactivate_service(self, service_id: UUID) -> bool: ...
    async def list_professionals(self) -> list[dict[str, Any]]: ...
    async def create_professional(
        self, *, name: str, specialty: str | None, service_ids: list[UUID]
    ) -> dict[str, Any]: ...
    async def update_professional(
        self,
        professional_id: UUID,
        *,
        name: str | None,
        specialty: str | None,
        service_ids: list[UUID] | None,
        is_active: bool | None,
    ) -> dict[str, Any] | None: ...
    async def deactivate_professional(self, professional_id: UUID) -> bool: ...

    # Requests
    async def list_requests(
        self,
        *,
        status: str | None,
        type_: str | None,
        priority: str | None,
        day: date | None,
        search: str | None,
        cursor_ts: datetime | None,
        cursor_id: UUID | None,
        limit: int,
    ) -> list[dict[str, Any]]: ...
    async def get_request(self, request_id: UUID) -> dict[str, Any] | None: ...
    async def get_request_events(self, request_id: UUID) -> list[dict[str, Any]]: ...
    async def update_request(
        self,
        request_id: UUID,
        *,
        title: str | None,
        description: str | None,
        priority: str | None,
        due_date: date | None,
    ) -> dict[str, Any] | None: ...
    async def assign_request(self, request_id: UUID, user_id: UUID) -> dict[str, Any] | None: ...
    async def complete_request(self, request_id: UUID) -> dict[str, Any] | None: ...
    async def mark_request_spam(
        self, request_id: UUID, *, expires_in_days: int | None = None
    ) -> dict[str, Any] | None: ...
    async def add_request_event(
        self,
        request_id: UUID,
        event_type: str,
        *,
        user_id: UUID | None = None,
        note: str | None = None,
    ) -> None: ...
    async def add_audit(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: UUID | None,
        ip: str | None,
    ) -> None: ...

    # Calls
    async def list_calls(
        self,
        *,
        status: str | None,
        day: date | None,
        cursor_ts: datetime | None,
        cursor_id: UUID | None,
        limit: int,
    ) -> list[dict[str, Any]]: ...
    async def get_call(self, call_id: UUID) -> dict[str, Any] | None: ...
    async def get_call_turns(self, call_id: UUID) -> list[dict[str, Any]]: ...
    async def get_call_events(self, call_id: UUID) -> list[dict[str, Any]]: ...
    async def set_call_summary(self, call_id: UUID, summary: str) -> None: ...

    # Agenda
    async def list_appointments(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        professional_id: UUID | None,
    ) -> list[dict[str, Any]]: ...
    async def get_appointment(self, appointment_id: UUID) -> dict[str, Any] | None: ...

    # Agent config
    async def get_published_config(self) -> dict[str, Any] | None: ...
    async def get_config_version(self, version: int) -> dict[str, Any] | None: ...
    async def list_config_versions(self) -> list[dict[str, Any]]: ...
    async def next_config_version(self) -> int: ...
    async def create_config(
        self, *, version: int, config: dict[str, Any], created_by: UUID | None, status: str
    ) -> dict[str, Any]: ...
    async def publish_config(self, version: int) -> dict[str, Any] | None: ...

    # Team
    async def list_users(self) -> list[dict[str, Any]]: ...
    async def create_user(
        self, *, email: str, full_name: str, role: str, password_hash: str
    ) -> dict[str, Any]: ...
    async def deactivate_user(self, user_id: UUID) -> dict[str, Any] | None: ...

    # Blocked numbers
    async def list_blocked(self) -> list[dict[str, Any]]: ...
    async def add_blocked(
        self,
        *,
        e164: str,
        reason: str | None,
        source: str,
        expires_in_days: int | None = None,
    ) -> dict[str, Any]: ...
    async def delete_blocked(self, blocked_id: UUID) -> bool: ...

    # Dashboard
    async def dashboard(self, *, start: datetime, end: datetime) -> dict[str, Any]: ...

    # Internal voice tool: non-schedulable request
    async def create_service_request(
        self,
        *,
        clinic_id: UUID,
        call_id: UUID,
        type_: str,
        title: str,
        description: str | None,
        patient_name: str | None,
        requested_date: date | None,
        due_date: date | None,
    ) -> UUID: ...


class CallSummaryGenerator(Protocol):
    async def summarize(self, call: dict[str, Any], turns: list[dict[str, Any]]) -> str | None: ...
