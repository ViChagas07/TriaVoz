from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from triavoz.application.staff.ports import StaffRepository
from triavoz.application.staff.service import StaffService
from triavoz.infrastructure.security.tokens import Principal
from triavoz.interfaces.http.api_v1.schemas import (
    CallDetailOut,
    CallEventOut,
    CallListOut,
    CallOut,
    CallTurnOut,
)
from triavoz.interfaces.http.deps import (
    current_principal,
    get_staff_repo,
    get_staff_service,
)
from triavoz.interfaces.http.pagination import decode_cursor, encode_cursor

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=CallListOut)
async def list_calls(
    repo: StaffRepository = Depends(get_staff_repo),
    status: Literal["in_progress", "completed", "failed", "rejected", "transferred"] | None = None,
    day: date | None = None,
    cursor: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
) -> CallListOut:
    try:
        cursor_ts, cursor_id = decode_cursor(cursor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_cursor") from exc
    rows = await repo.list_calls(
        status=status,
        day=day,
        cursor_ts=cursor_ts,
        cursor_id=cursor_id,
        limit=limit + 1,
    )
    page, has_more = rows[:limit], len(rows) > limit
    next_cursor = (
        encode_cursor(page[-1]["started_at"], page[-1]["id"]) if has_more and page else None
    )
    return CallListOut(items=[CallOut.model_validate(r) for r in page], next_cursor=next_cursor)


@router.get("/{call_id}", response_model=CallDetailOut)
async def get_call(call_id: UUID, repo: StaffRepository = Depends(get_staff_repo)) -> CallDetailOut:
    call = await repo.get_call(call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="not_found")
    return CallDetailOut.model_validate(call)


@router.get("/{call_id}/turns", response_model=list[CallTurnOut])
async def get_turns(
    call_id: UUID,
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(current_principal),
) -> list[CallTurnOut]:
    call = await repo.get_call(call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="not_found")
    turns = await repo.get_call_turns(call_id)
    # Transcript access is sensitive: append-only audit trail, never log the content itself.
    await repo.add_audit(
        action="call.transcript.read",
        resource_type="call",
        resource_id=str(call_id),
        user_id=principal.user_id,
        ip=None,
    )
    return [CallTurnOut.model_validate(t) for t in turns]


@router.get("/{call_id}/events", response_model=list[CallEventOut])
async def get_events(
    call_id: UUID, repo: StaffRepository = Depends(get_staff_repo)
) -> list[CallEventOut]:
    call = await repo.get_call(call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="not_found")
    return [CallEventOut.model_validate(e) for e in await repo.get_call_events(call_id)]


@router.post("/{call_id}/summary", response_model=dict[str, str])
async def generate_summary(
    call_id: UUID,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(current_principal),
) -> dict[str, str]:
    summary = await service.summarize_call(call_id, actor_id=principal.user_id)
    return {"summary": summary}
