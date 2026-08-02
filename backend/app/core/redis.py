"""Redis client factory and connectivity check."""

from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)


def check_redis_connection() -> bool:
    """Readiness check: True if PING succeeds, False otherwise."""
    try:
        return bool(get_redis_client().ping())
    except Exception:
        return False
