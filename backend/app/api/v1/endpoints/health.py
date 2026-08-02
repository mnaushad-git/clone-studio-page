"""Liveness and readiness endpoints.

health: confirms the process is up. Must not touch PostgreSQL or Redis.
readiness: confirms PostgreSQL and Redis are actually reachable.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from app.core.config import Settings, get_settings
from app.core.database import check_database_connection
from app.core.redis import check_redis_connection

router = APIRouter()


@router.get("/health", summary="Liveness check")
def health(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
    }


@router.get("/readiness", summary="Readiness check")
def readiness(response: Response) -> dict[str, Any]:
    database_ok = check_database_connection()
    redis_ok = check_redis_connection()
    overall_ok = database_ok and redis_ok

    response.status_code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if overall_ok else "unavailable",
        "dependencies": {
            "database": "ok" if database_ok else "unavailable",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }
