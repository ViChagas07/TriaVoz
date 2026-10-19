from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from fastapi import APIRouter, Depends

from triavoz.application.staff.ports import StaffRepository
from triavoz.interfaces.http.api_v1.schemas import DashboardOut
from triavoz.interfaces.http.deps import get_staff_repo

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
async def dashboard(repo: StaffRepository = Depends(get_staff_repo)) -> DashboardOut:
    now = datetime.now(UTC)
    start = datetime.combine(now.date(), time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    return DashboardOut.model_validate(await repo.dashboard(start=start, end=end))
