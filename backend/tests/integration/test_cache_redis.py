"""Integration tests against a real Redis (REDIS_URL=.../15) for RedisCache — task
brief §17 "Cache abstraction" + §14 "Redis failure behavior" test lists.
"""

from __future__ import annotations

import time

import pytest

from app.cache.redis_cache import RedisCache
from app.core.config import get_settings

pytestmark = pytest.mark.usefixtures("flush_cache")


@pytest.fixture
def cache() -> RedisCache:
    return RedisCache(get_settings())


def test_ping_succeeds_against_real_redis(cache: RedisCache) -> None:
    assert cache.ping() is True


def test_set_then_get_json_round_trips(cache: RedisCache) -> None:
    cache.set_json("tb:v1:test:key", {"a": 1, "name_ar": "كعكة"}, ttl_seconds=30)

    assert cache.get_json("tb:v1:test:key") == {"a": 1, "name_ar": "كعكة"}


def test_get_json_missing_key_returns_none(cache: RedisCache) -> None:
    assert cache.get_json("tb:v1:test:does-not-exist") is None


def test_ttl_is_applied_and_expires(cache: RedisCache) -> None:
    cache.set_json("tb:v1:test:ttl", {"v": 1}, ttl_seconds=1)

    assert cache.get_json("tb:v1:test:ttl") == {"v": 1}
    time.sleep(1.2)
    assert cache.get_json("tb:v1:test:ttl") is None


def test_delete_removes_key(cache: RedisCache) -> None:
    cache.set_json("tb:v1:test:del", {"v": 1}, ttl_seconds=30)

    assert cache.delete("tb:v1:test:del") is True
    assert cache.get_json("tb:v1:test:del") is None


def test_delete_many_removes_all_given_keys(cache: RedisCache) -> None:
    cache.set_json("tb:v1:test:a", 1, ttl_seconds=30)
    cache.set_json("tb:v1:test:b", 2, ttl_seconds=30)

    deleted = cache.delete_many(["tb:v1:test:a", "tb:v1:test:b", "tb:v1:test:missing"])

    assert deleted == 2
    assert cache.get_json("tb:v1:test:a") is None
    assert cache.get_json("tb:v1:test:b") is None


def test_delete_by_prefix_uses_scan_and_deletes_matching_keys(cache: RedisCache) -> None:
    for i in range(5):
        cache.set_json(f"tb:v1:test:prefix:{i}", i, ttl_seconds=30)
    cache.set_json("tb:v1:test:other:key", "unrelated", ttl_seconds=30)

    deleted = cache.delete_by_prefix("tb:v1:test:prefix:")

    assert deleted == 5
    assert cache.get_json("tb:v1:test:other:key") == "unrelated"


def test_exists(cache: RedisCache) -> None:
    assert cache.exists("tb:v1:test:exists") is False
    cache.set_json("tb:v1:test:exists", 1, ttl_seconds=30)
    assert cache.exists("tb:v1:test:exists") is True


def test_corrupt_cached_value_is_deleted_and_returns_none(cache: RedisCache) -> None:
    # Bypass set_json to write a value the JSON codec can't parse.
    cache._client.set("tb:v1:test:corrupt", b"{not valid json")

    result = cache.get_json("tb:v1:test:corrupt")

    assert result is None
    assert cache.exists("tb:v1:test:corrupt") is False


def test_acquire_lock_then_release_allows_reacquire(cache: RedisCache) -> None:
    token = cache.acquire_lock("tb:v1:test:lock", ttl_seconds=5)
    assert token is not None
    assert cache.acquire_lock("tb:v1:test:lock", ttl_seconds=5) is None

    cache.release_lock("tb:v1:test:lock", token)

    assert cache.acquire_lock("tb:v1:test:lock", ttl_seconds=5) is not None


def test_release_lock_does_not_delete_a_lock_held_by_a_different_token(cache: RedisCache) -> None:
    token = cache.acquire_lock("tb:v1:test:lock", ttl_seconds=5)
    assert token is not None

    cache.release_lock("tb:v1:test:lock", "some-other-token")

    # Still held by the real token — a second acquire must fail.
    assert cache.acquire_lock("tb:v1:test:lock", ttl_seconds=5) is None


def test_lock_expires_safely_without_manual_release(cache: RedisCache) -> None:
    token = cache.acquire_lock("tb:v1:test:short-lock", ttl_seconds=1)
    assert token is not None

    time.sleep(1.2)

    assert cache.acquire_lock("tb:v1:test:short-lock", ttl_seconds=5) is not None


def test_sadd_bounded_allows_up_to_the_cap_then_rejects(cache: RedisCache) -> None:
    assert cache.sadd_bounded("tb:v1:test:tracked", "a", max_members=2) is True
    assert cache.sadd_bounded("tb:v1:test:tracked", "b", max_members=2) is True
    assert cache.sadd_bounded("tb:v1:test:tracked", "c", max_members=2) is False
    # Already-tracked members are always allowed, even once the cap is reached.
    assert cache.sadd_bounded("tb:v1:test:tracked", "a", max_members=2) is True


def test_get_json_unavailable_redis_falls_back_to_none() -> None:
    settings = get_settings()
    # Point at a port nothing is listening on — simulates Redis being down without
    # actually stopping the shared test Redis instance other tests depend on.
    broken_settings = settings.model_copy(
        update={"redis_url": "redis://localhost:1/15", "cache_redis_operation_timeout_seconds": 0.2}
    )
    broken_cache = RedisCache(broken_settings)

    assert broken_cache.get_json("tb:v1:test:whatever") is None
    assert broken_cache.set_json("tb:v1:test:whatever", {"v": 1}, ttl_seconds=30) is False
    assert broken_cache.ping() is False
    assert broken_cache.delete_by_prefix("tb:v1:test:") == 0
