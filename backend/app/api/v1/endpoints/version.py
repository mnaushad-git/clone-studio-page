"""Version endpoint — app version, environment, and API version. No secrets."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/version", summary="Version information")
def version(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return {
        "app_version": settings.app_version,
        "app_env": settings.app_env,
        "api_version": "v1",
    }
