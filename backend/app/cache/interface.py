"""Cache abstraction — route handlers and services depend on this, never on raw Redis
commands (task brief §4: "Route handlers must not construct Redis commands
directly."). `RedisCache` (redis_cache.py) is the only production implementation;
the Protocol exists so tests/other call sites can type against it without importing
redis-py.
"""

from __future__ import annotations

from typing import Any, Protocol


class CacheClient(Protocol):
    def get_json(self, key: str) -> Any | None:
        """Returns the deserialized value, or None on a miss, corrupt value, or any
        Redis failure. Never raises — callers always have a PostgreSQL fallback."""
        ...

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Best-effort write. Returns False (never raises) if Redis is unavailable."""
        ...

    def delete(self, key: str) -> bool: ...

    def delete_many(self, keys: list[str]) -> int:
        """Returns the number of keys actually deleted (0 on failure)."""
        ...

    def delete_by_prefix(self, prefix: str) -> int:
        """SCAN-based (never KEYS) bounded-batch prefix delete. Returns the number of
        keys deleted."""
        ...

    def exists(self, key: str) -> bool: ...

    def ping(self) -> bool: ...

    def acquire_lock(self, key: str, ttl_seconds: int) -> str | None:
        """Stampede-protection lock (SET NX PX). Returns an opaque token to pass to
        release_lock on success, or None if the lock is already held or Redis is
        unavailable."""
        ...

    def release_lock(self, key: str, token: str) -> None:
        """No-ops safely if the lock already expired or was never held by `token` —
        never deletes a lock acquired by someone else."""
        ...

    def sadd_bounded(self, set_key: str, member: str, max_members: int) -> bool:
        """Atomically adds `member` to the set at `set_key` unless it's already
        present or the set has reached `max_members`. Returns True if `member` is (or
        already was) a member, False if the cap was hit. Used to bound product-list
        cache key-space growth (CACHE_MAX_PRODUCT_LIST_KEYS). Fails open (returns
        True) on a Redis error — a transient guard failure must not silently disable
        caching."""
        ...
