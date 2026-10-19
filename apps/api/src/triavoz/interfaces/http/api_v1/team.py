from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from triavoz.application.staff.ports import StaffRepository
from triavoz.application.staff.service import StaffService
from triavoz.infrastructure.security.tokens import Principal
from triavoz.interfaces.http.api_v1.schemas import TeamUserCreate, UserOut
from triavoz.interfaces.http.deps import get_staff_repo, get_staff_service, require_admin

router = APIRouter(prefix="/team", tags=["team"])


@router.get("", response_model=list[UserOut])
async def list_team(
    repo: StaffRepository = Depends(get_staff_repo),
    _: Principal = Depends(require_admin),
) -> list[UserOut]:
    return [UserOut.model_validate(u) for u in await repo.list_users()]


@router.post("", response_model=UserOut)
async def create_user(
    body: TeamUserCreate,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(require_admin),
) -> UserOut:
    user = await service.create_user(
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        password=body.password,
        actor_id=principal.user_id,
    )
    return UserOut.model_validate(user)


@router.delete("/{user_id}", response_model=UserOut)
async def deactivate_user(
    user_id: UUID,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(require_admin),
) -> UserOut:
    return UserOut.model_validate(
        await service.deactivate_user(user_id, actor_id=principal.user_id)
    )
