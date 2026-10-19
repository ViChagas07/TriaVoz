from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from triavoz.application.staff.ports import StaffRepository
from triavoz.application.staff.service import StaffService
from triavoz.infrastructure.security.tokens import Principal
from triavoz.interfaces.http.api_v1.schemas import (
    AssignIn,
    RequestDetailOut,
    RequestListOut,
    RequestOut,
    RequestPatch,
)
from triavoz.interfaces.http.deps import current_principal, get_staff_repo, get_staff_service
from triavoz.interfaces.http.pagination import decode_cursor, encode_cursor

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=RequestListOut)
async def list_requests(
    repo: StaffRepository = Depends(get_staff_repo),
    status: Literal["pending", "in_progress", "done", "cancelled", "spam"] | None = None,
    type: Literal["appointment", "exam_pickup", "message", "callback", "other"] | None = None,
    priority: Literal["urgent", "normal", "low"] | None = None,
    day: date | None = None,
    search: str | None = Query(default=None, max_length=100),
    cursor: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
) -> RequestListOut:
    try:
        cursor_ts, cursor_id = decode_cursor(cursor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_cursor") from exc
    rows = await repo.list_requests(
        status=status,
        type_=type,
        priority=priority,
        day=day,
        search=search,
        cursor_ts=cursor_ts,
        cursor_id=cursor_id,
        limit=limit + 1,
    )
    page, has_more = rows[:limit], len(rows) > limit
    next_cursor = (
        encode_cursor(page[-1]["created_at"], page[-1]["id"]) if has_more and page else None
    )
    return RequestListOut(
        items=[RequestOut.model_validate(r) for r in page], next_cursor=next_cursor
    )


@router.get("/{request_id}", response_model=RequestDetailOut)
async def get_request(
    request_id: UUID, repo: StaffRepository = Depends(get_staff_repo)
) -> RequestDetailOut:
    request = await repo.get_request(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="not_found")
    events = await repo.get_request_events(request_id)
    return RequestDetailOut.model_validate({**request, "timeline": events})


@router.patch("/{request_id}", response_model=RequestOut)
async def patch_request(
    request_id: UUID,
    body: RequestPatch,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(current_principal),
) -> RequestOut:
    if not body.model_fields_set:
        raise HTTPException(status_code=422, detail="empty_patch")
    updated = await service.update_request(
        request_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        due_date=body.due_date,
        actor_id=principal.user_id,
    )
    return RequestOut.model_validate(updated)


@router.post("/{request_id}/assign", response_model=RequestOut)
async def assign_request(
    request_id: UUID,
    body: AssignIn,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(current_principal),
) -> RequestOut:
    updated = await service.assign_request(
        request_id, user_id=body.user_id, actor_id=principal.user_id
    )
    return RequestOut.model_validate(updated)


@router.post("/{request_id}/complete", response_model=RequestOut)
async def complete_request(
    request_id: UUID,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(current_principal),
) -> RequestOut:
    updated = await service.complete_request(request_id, actor_id=principal.user_id)
    return RequestOut.model_validate(updated)


@router.post("/{request_id}/mark-spam", response_model=RequestOut)
async def mark_spam(
    request_id: UUID,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(current_principal),
) -> RequestOut:
    updated = await service.mark_spam(request_id, actor_id=principal.user_id)
    return RequestOut.model_validate(updated)
