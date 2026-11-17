"""Per-IP rate limits for the public, unauthenticated endpoints.

Fixed windows in Redis, same approach as the admin login throttle. If Redis is unreachable
the request is allowed: this is a guard against abuse, and it must never take checkout down.
Behind Caddy, request.client.host is the visitor's address because uvicorn runs with
--proxy-headers.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError
from app.core.redis import get_redis_client

logger = logging.getLogger("app.core.rate_limit")


def rate_limit(scope: str, *, limit_setting: str, window_seconds: int) -> Callable[[Request], None]:
    """A FastAPI dependency allowing `settings.<limit_setting>` requests per IP per window."""

    def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        limit = int(getattr(settings, limit_setting))
        ip = request.client.host if request.client else "unknown"
        window = int(time.time() // window_seconds)
        key = f"{settings.cache_key_prefix}:ratelimit:{scope}:{ip}:{window}"
        try:
            client = get_redis_client()
            count = int(client.incr(key))
            if count == 1:
                client.expire(key, window_seconds + 5)
        except Exception:  # noqa: BLE001 - Redis being down must never block customers
            logger.warning("rate_limit_unavailable", extra={"scope": scope})
            return
        if count > limit:
            logger.warning("rate_limited", extra={"scope": scope})
            raise RateLimitedError("Too many requests. Please wait a few minutes and try again.")

    return dependency
