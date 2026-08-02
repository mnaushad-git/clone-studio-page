"""Redis-backed CacheClient implementation (task brief §3, §4, §12).

Every public method catches Redis/serialization failures itself and degrades to a
safe default (None / False / 0) rather than raising — callers (the cache-aside wrapper
in app/cache/catalogue_cache.py, and the invalidation service) never need their own
try/except around a cache call; PostgreSQL stays reachable regardless of Redis state
(task brief §3.5, §14).

Uses a dedicated Redis client (separate from app.core.redis.get_redis_client, which
Celery/admin-login-throttle share with a fixed 2s timeout) so
CACHE_REDIS_OPERATION_TIMEOUT_SECONDS only affects catalogue caching.
"""

from __future__ import annotations

import logging
import secrets
import time
from functools import lru_cache

import redis

from app.cache import serializer
from app.core.config import Settings
from app.core.logging import correlation_id_ctx

logger = logging.getLogger("app.cache.redis")

# Bounded batch size for SCAN-based prefix deletes (task brief §11: "Delete in bounded
# batches, avoid blocking Redis") — never a single unbounded DEL of every matched key.
_SCAN_BATCH_SIZE = 500
_SCAN_COUNT_HINT = 200


@lru_cache
def _build_client(redis_url: str, connect_timeout: float, operation_timeout: float) -> redis.Redis:
    return redis.Redis.from_url(
        redis_url, socket_connect_timeout=connect_timeout, socket_timeout=operation_timeout
    )


def _key_namespace(key: str) -> str:
    parts = key.split(":")
    return ":".join(parts[:4]) if len(parts) >= 4 else key


class RedisCache:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = _build_client(
            settings.redis_url,
            connect_timeout=min(2.0, settings.cache_redis_operation_timeout_seconds),
            operation_timeout=settings.cache_redis_operation_timeout_seconds,
        )

    def _log(self, operation: str, *, latency_ms: float, **fields: object) -> None:
        if not self._settings.cache_log_hits and operation in ("get_hit", "get_miss"):
            return
        logger.info(
            "cache_operation",
            extra={
                "cache_operation": operation,
                "cache_latency_ms": round(latency_ms, 2),
                "correlation_id": correlation_id_ctx.get(),
                **fields,
            },
        )

    def _log_error(self, operation: str, key: str, exc: Exception) -> None:
        logger.warning(
            "cache_error",
            extra={
                "cache_operation": operation,
                "cache_key_namespace": _key_namespace(key),
                "cache_error": str(exc),
            },
        )

    # -- CacheClient interface ------------------------------------------------------

    def get_json(self, key: str) -> object | None:
        start = time.perf_counter()
        try:
            raw = self._client.get(key)
        except redis.RedisError as exc:
            self._log_error("get", key, exc)
            return None
        latency_ms = (time.perf_counter() - start) * 1000
        if raw is None:
            self._log("get_miss", latency_ms=latency_ms, cache_key_namespace=_key_namespace(key))
            return None
        try:
            value = serializer.loads(raw)
        except (ValueError, TypeError) as exc:
            # Corrupt/unexpected-type cached value — delete it so the next request
            # rebuilds cleanly rather than repeatedly failing to decode it.
            self._log_error("get_corrupt", key, exc)
            self.delete(key)
            return None
        self._log("get_hit", latency_ms=latency_ms, cache_key_namespace=_key_namespace(key))
        return value

    def set_json(self, key: str, value: object, ttl_seconds: int) -> bool:
        start = time.perf_counter()
        try:
            payload = serializer.dumps(value)
        except TypeError as exc:
            self._log_error("set_serialize", key, exc)
            return False
        try:
            # SET ... EX, not the deprecated SETEX convenience method (redis-py
            # deprecated .setex() itself in 2.6.12; the SETEX command is unaffected).
            self._client.set(key, payload, ex=ttl_seconds)
        except redis.RedisError as exc:
            self._log_error("set", key, exc)
            return False
        latency_ms = (time.perf_counter() - start) * 1000
        self._log(
            "set",
            latency_ms=latency_ms,
            cache_key_namespace=_key_namespace(key),
            ttl_seconds=ttl_seconds,
        )
        return True

    def delete(self, key: str) -> bool:
        try:
            return bool(self._client.delete(key))
        except redis.RedisError as exc:
            self._log_error("delete", key, exc)
            return False

    def delete_many(self, keys: list[str]) -> int:
        if not keys:
            return 0
        try:
            return int(self._client.delete(*keys))
        except redis.RedisError as exc:
            self._log_error("delete_many", keys[0], exc)
            return 0

    def delete_by_prefix(self, prefix: str) -> int:
        pattern = f"{prefix}*"
        deleted = 0
        try:
            batch: list[bytes] = []
            for found_key in self._client.scan_iter(match=pattern, count=_SCAN_COUNT_HINT):
                batch.append(found_key)
                if len(batch) >= _SCAN_BATCH_SIZE:
                    deleted += int(self._client.delete(*batch))
                    batch = []
            if batch:
                deleted += int(self._client.delete(*batch))
        except redis.RedisError as exc:
            self._log_error("delete_by_prefix", prefix, exc)
            return deleted
        logger.info(
            "cache_prefix_invalidated",
            extra={
                "cache_operation": "delete_by_prefix",
                "cache_key_namespace": _key_namespace(prefix),
                "cache_deleted_keys": deleted,
                "correlation_id": correlation_id_ctx.get(),
            },
        )
        return deleted

    def exists(self, key: str) -> bool:
        try:
            return bool(self._client.exists(key))
        except redis.RedisError as exc:
            self._log_error("exists", key, exc)
            return False

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except redis.RedisError:
            return False

    # -- stampede-protection lock (task brief §12) -----------------------------------

    def acquire_lock(self, key: str, ttl_seconds: int) -> str | None:
        token = secrets.token_hex(8)
        try:
            got = self._client.set(key, token, nx=True, px=int(ttl_seconds * 1000))
        except redis.RedisError as exc:
            self._log_error("lock_acquire", key, exc)
            return None
        return token if got else None

    _RELEASE_SCRIPT = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    end
    return 0
    """

    def release_lock(self, key: str, token: str) -> None:
        try:
            self._client.eval(self._RELEASE_SCRIPT, 1, key, token)
        except redis.RedisError as exc:
            # A lock left in place until its TTL expires is safe by design (task
            # brief §12: "Ensure a crashed request cannot leave a permanent lock") —
            # failing to release early just delays the next rebuild by at most the
            # lock TTL, never blocks it forever.
            self._log_error("lock_release", key, exc)

    # -- bounded product-list key-space guard (task brief §15) ----------------------

    _BOUNDED_SADD_SCRIPT = """
    if redis.call("SISMEMBER", KEYS[1], ARGV[1]) == 1 then
        return 1
    end
    if redis.call("SCARD", KEYS[1]) >= tonumber(ARGV[2]) then
        return 0
    end
    redis.call("SADD", KEYS[1], ARGV[1])
    return 1
    """

    def sadd_bounded(self, set_key: str, member: str, max_members: int) -> bool:
        try:
            result = self._client.eval(self._BOUNDED_SADD_SCRIPT, 1, set_key, member, max_members)
        except redis.RedisError as exc:
            self._log_error("sadd_bounded", set_key, exc)
            return True
        return bool(result)
