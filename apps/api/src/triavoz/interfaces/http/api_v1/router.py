from __future__ import annotations

from fastapi import APIRouter

from triavoz.interfaces.http.api_v1 import (
    agenda,
    agent_config,
    auth,
    blocked,
    calls,
    dashboard,
    events,
    requests,
    settings,
    team,
    voice,
)

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(requests.router)
router.include_router(calls.router)
router.include_router(agenda.router)
router.include_router(agent_config.router)
router.include_router(dashboard.router)
router.include_router(events.router)
router.include_router(team.router)
router.include_router(blocked.router)
router.include_router(settings.router)
router.include_router(settings.services_router)
router.include_router(settings.professionals_router)
router.include_router(voice.router)
