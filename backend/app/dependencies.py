"""Dependency-injection foundation shared across route handlers."""

from __future__ import annotations

from collections.abc import Generator

import redis
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db as _get_db
from app.core.redis import get_redis_client


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


def get_redis() -> redis.Redis:
    return get_redis_client()


def get_app_settings() -> Settings:
    return get_settings()
