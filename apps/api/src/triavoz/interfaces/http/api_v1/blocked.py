from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from triavoz.application.staff.ports import StaffRepository
from triavoz.application.staff.service import StaffService
from triavoz.infrastructure.security.tokens import Principal
from triavoz.interfaces.http.api_v1.schemas import BlockedCreate, BlockedOut
from triavoz.interfaces.http.deps import get_staff_repo, get_staff_service, require_admin

router = APIRouter(prefix="/blocked-numbers", tags=["blocked-numbers"])


@router.get("", response_model=list[BlockedOut])
async def list_blocked(
    repo: StaffRepository = Depends(get_staff_repo),
    _: Principal = Depends(require_admin),
) -> list[BlockedOut]:
    return [BlockedOut.model_validate(b) for b in await repo.list_blocked()]


@router.post("", response_model=BlockedOut)
async def add_blocked(
    body: BlockedCreate,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(require_admin),
) -> BlockedOut:
    blocked = await service.add_blocked(
        e164=body.e164,
        reason=body.reason,
        actor_id=principal.user_id,
        expires_in_days=body.expires_in_days,
    )
    return BlockedOut.model_validate(blocked)


@router.delete("/{blocked_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blocked(
    blocked_id: UUID,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(require_admin),
) -> Response:
    await service.delete_blocked(blocked_id, actor_id=principal.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{blocked_id}/unblock", status_code=status.HTTP_204_NO_CONTENT)
async def unblock(
    blocked_id: UUID,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(require_admin),
) -> Response:
    """Human override for the feedback loop: remove a block (manual or auto spam)."""
    await service.unblock(blocked_id, actor_id=principal.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
