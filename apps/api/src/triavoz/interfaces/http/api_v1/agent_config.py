from __future__ import annotations

from fastapi import APIRouter, Depends

from triavoz.application.staff.ports import StaffRepository
from triavoz.application.staff.service import StaffService
from triavoz.infrastructure.security.tokens import Principal
from triavoz.interfaces.http.api_v1.schemas import (
    AgentConfigIn,
    AgentConfigStateOut,
    ConfigVersionOut,
)
from triavoz.interfaces.http.deps import (
    get_staff_repo,
    get_staff_service,
    require_admin,
)

router = APIRouter(prefix="/agent-config", tags=["agent-config"])


@router.get("", response_model=AgentConfigStateOut)
async def get_agent_config(
    repo: StaffRepository = Depends(get_staff_repo),
    _: Principal = Depends(require_admin),
) -> AgentConfigStateOut:
    published = await repo.get_published_config()
    versions = await repo.list_config_versions()
    draft = next((v for v in versions if v["status"] == "draft"), None)
    return AgentConfigStateOut(
        published=ConfigVersionOut.model_validate(published) if published else None,
        latest_draft=ConfigVersionOut.model_validate(draft) if draft else None,
    )


@router.get("/versions", response_model=list[ConfigVersionOut])
async def list_versions(
    repo: StaffRepository = Depends(get_staff_repo),
    _: Principal = Depends(require_admin),
) -> list[ConfigVersionOut]:
    return [ConfigVersionOut.model_validate(v) for v in await repo.list_config_versions()]


@router.put("/draft", response_model=ConfigVersionOut)
async def save_draft(
    body: AgentConfigIn,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(require_admin),
) -> ConfigVersionOut:
    created = await service.save_config(config=body.model_dump(), actor_id=principal.user_id)
    return ConfigVersionOut.model_validate(created)


@router.post("/{version}/publish", response_model=ConfigVersionOut)
async def publish_version(
    version: int,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(require_admin),
) -> ConfigVersionOut:
    published = await service.publish_config(version, actor_id=principal.user_id)
    return ConfigVersionOut.model_validate(published)


@router.post("/{version}/rollback", response_model=ConfigVersionOut)
async def rollback_version(
    version: int,
    service: StaffService = Depends(get_staff_service),
    principal: Principal = Depends(require_admin),
) -> ConfigVersionOut:
    published = await service.rollback_config(version, actor_id=principal.user_id)
    return ConfigVersionOut.model_validate(published)
