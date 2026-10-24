from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from triavoz.application.staff.ports import StaffRepository
from triavoz.infrastructure.security.tokens import Principal
from triavoz.interfaces.http.api_v1.schemas import (
    ClinicSettingsIn,
    ClinicSettingsOut,
    ProfessionalCreate,
    ProfessionalOut,
    ProfessionalPatch,
    ServiceCreate,
    ServiceOut,
    ServicePatch,
)
from triavoz.interfaces.http.deps import get_staff_repo, require_admin

router = APIRouter(prefix="/settings", tags=["settings"])
services_router = APIRouter(prefix="/services", tags=["services"])
professionals_router = APIRouter(prefix="/professionals", tags=["professionals"])


@router.get("/clinic", response_model=ClinicSettingsOut)
async def get_clinic_settings(
    repo: StaffRepository = Depends(get_staff_repo),
) -> ClinicSettingsOut:
    return ClinicSettingsOut.model_validate(await repo.get_clinic_settings())


@router.put("/clinic", response_model=ClinicSettingsOut)
async def update_clinic_settings(
    body: ClinicSettingsIn,
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(require_admin),
) -> ClinicSettingsOut:
    # WHY: keeping operational limits in the same transaction as the clinic name prevents a
    # half-saved settings screen; the gatekeeper reads this row on the next call.
    settings = await repo.update_clinic_settings(
        name=body.name,
        timezone=body.timezone,
        business_hours=body.business_hours.model_dump() if body.business_hours else None,
        max_call_seconds=body.max_call_seconds,
        max_concurrent_calls=body.max_concurrent_calls,
        daily_minute_budget=body.daily_minute_budget,
        daily_cost_budget_cents=body.daily_cost_budget_cents,
        kill_switch=body.kill_switch,
        hidden_caller_policy=body.hidden_caller_policy,
    )
    await repo.add_audit(
        action="settings.update",
        resource_type="clinic",
        resource_id=str(principal.clinic_id),
        user_id=principal.user_id,
        ip=None,
    )
    return ClinicSettingsOut.model_validate(settings)


@services_router.get("", response_model=list[ServiceOut])
async def list_services(repo: StaffRepository = Depends(get_staff_repo)) -> list[ServiceOut]:
    return [ServiceOut.model_validate(row) for row in await repo.list_services()]


@services_router.post("", response_model=ServiceOut)
async def create_service(
    body: ServiceCreate,
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(require_admin),
) -> ServiceOut:
    created = await repo.create_service(
        name=body.name, duration_min=body.duration_min, price_cents=body.price_cents
    )
    await repo.add_audit(
        action="service.create",
        resource_type="service",
        resource_id=str(created["id"]),
        user_id=principal.user_id,
        ip=None,
    )
    return ServiceOut.model_validate(created)


@services_router.patch("/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: UUID,
    body: ServicePatch,
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(require_admin),
) -> ServiceOut:
    if not body.model_fields_set:
        raise HTTPException(status_code=422, detail="empty_patch")
    updated = await repo.update_service(
        service_id,
        name=body.name,
        duration_min=body.duration_min,
        price_cents=body.price_cents,
        is_active=body.is_active,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="not_found")
    await repo.add_audit(
        action="service.update",
        resource_type="service",
        resource_id=str(service_id),
        user_id=principal.user_id,
        ip=None,
    )
    return ServiceOut.model_validate(updated)


@services_router.delete("/{service_id}", status_code=204)
async def deactivate_service(
    service_id: UUID,
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(require_admin),
) -> None:
    if not await repo.deactivate_service(service_id):
        raise HTTPException(status_code=404, detail="not_found")
    await repo.add_audit(
        action="service.deactivate",
        resource_type="service",
        resource_id=str(service_id),
        user_id=principal.user_id,
        ip=None,
    )


@professionals_router.get("", response_model=list[ProfessionalOut])
async def list_professionals(
    repo: StaffRepository = Depends(get_staff_repo),
) -> list[ProfessionalOut]:
    return [ProfessionalOut.model_validate(row) for row in await repo.list_professionals()]


@professionals_router.post("", response_model=ProfessionalOut)
async def create_professional(
    body: ProfessionalCreate,
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(require_admin),
) -> ProfessionalOut:
    created = await repo.create_professional(
        name=body.name, specialty=body.specialty, service_ids=body.service_ids
    )
    await repo.add_audit(
        action="professional.create",
        resource_type="professional",
        resource_id=str(created["id"]),
        user_id=principal.user_id,
        ip=None,
    )
    return ProfessionalOut.model_validate(created)


@professionals_router.patch("/{professional_id}", response_model=ProfessionalOut)
async def update_professional(
    professional_id: UUID,
    body: ProfessionalPatch,
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(require_admin),
) -> ProfessionalOut:
    if not body.model_fields_set:
        raise HTTPException(status_code=422, detail="empty_patch")
    updated = await repo.update_professional(
        professional_id,
        name=body.name,
        specialty=body.specialty,
        service_ids=body.service_ids,
        is_active=body.is_active,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="not_found")
    await repo.add_audit(
        action="professional.update",
        resource_type="professional",
        resource_id=str(professional_id),
        user_id=principal.user_id,
        ip=None,
    )
    return ProfessionalOut.model_validate(updated)


@professionals_router.delete("/{professional_id}", status_code=204)
async def deactivate_professional(
    professional_id: UUID,
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(require_admin),
) -> None:
    if not await repo.deactivate_professional(professional_id):
        raise HTTPException(status_code=404, detail="not_found")
    await repo.add_audit(
        action="professional.deactivate",
        resource_type="professional",
        resource_id=str(professional_id),
        user_id=principal.user_id,
        ip=None,
    )
