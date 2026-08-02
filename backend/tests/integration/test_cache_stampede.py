"""Stampede-protection for the homepage cache rebuild (task brief §12, §17 "Stampede"
test list). Exercises CachedCatalogueQueryService._cached(stampede_protect=True)
directly with a fake loader — no PostgreSQL access needed, since the lock/rebuild
machinery itself doesn't touch self.query.
"""

from __future__ import annotations

import threading
import time

import pytest
from pydantic import TypeAdapter

from app.cache.catalogue_cache import ERROR_FALLBACK, HIT, MISS, CachedCatalogueQueryService
from app.cache.redis_cache import RedisCache
from app.core.config import get_settings

pytestmark = pytest.mark.usefixtures("flush_cache")

_ADAPTER: TypeAdapter[dict] = TypeAdapter(dict)


@pytest.fixture
def service() -> CachedCatalogueQueryService:
    cache = RedisCache(get_settings())
    # CatalogueQueryService's constructor only stores repository references against
    # the session, it never queries — safe to pass None here since these tests never
    # touch `service.query`.
    return CachedCatalogueQueryService(session=None, cache=cache, settings=get_settings())  # type: ignore[arg-type]


def test_concurrent_misses_cause_at_most_one_extra_rebuild(
    service: CachedCatalogueQueryService,
) -> None:
    """The production contract (task brief §12: "Other requests may briefly wait and
    retry cache, or fall back to PostgreSQL if waiting would hurt availability") does
    not guarantee exactly one rebuild under all scheduling conditions — a waiter whose
    retry budget (5 x 100ms) elapses before the lock holder finishes is explicitly
    allowed to fall back and rebuild itself rather than block indefinitely. On a
    quiet machine the common case is exactly one rebuild; this asserts the documented
    worst case (at most one duplicate) instead of a stricter guarantee the code never
    promised, so the test isn't a coin flip under host scheduling jitter."""
    call_count = 0
    count_lock = threading.Lock()

    def loader() -> dict:
        nonlocal call_count
        with count_lock:
            call_count += 1
        # Comfortably shorter than the waiters' total retry budget (5 x 0.1s = 0.5s
        # in _cached_with_lock) so this test isn't racing that budget on a slow/busy
        # machine.
        time.sleep(0.02)
        return {"built": True}

    statuses: list[str] = []
    statuses_lock = threading.Lock()

    def worker() -> None:
        _, status = service._cached(
            key="tb:v1:test:stampede",
            ttl_seconds=30,
            adapter=_ADAPTER,
            loader=loader,
            stampede_protect=True,
        )
        with statuses_lock:
            statuses.append(status)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # At most one thread loses the lock-wait race and rebuilds independently — never
    # every thread stampeding PostgreSQL, which is the actual property under test.
    assert call_count in (1, 2)
    non_hit_count = statuses.count(MISS) + statuses.count(ERROR_FALLBACK)
    assert non_hit_count == call_count
    assert statuses.count(HIT) == 5 - call_count


def test_lock_held_elsewhere_falls_back_to_loader_without_writing_cache(
    service: CachedCatalogueQueryService,
) -> None:
    key = "tb:v1:test:stampede-held"
    # Simulate another process/worker already rebuilding this key.
    token = service._cache.acquire_lock(f"{key}:lock", ttl_seconds=5)
    assert token is not None

    call_count = 0

    def loader() -> dict:
        nonlocal call_count
        call_count += 1
        return {"built": True}

    value, status = service._cached(
        key=key, ttl_seconds=30, adapter=_ADAPTER, loader=loader, stampede_protect=True
    )

    assert value == {"built": True}
    assert status == MISS
    assert call_count == 1
    # The waiting request must not have written the cache itself — that's the lock
    # holder's responsibility, and doing it twice would defeat the point of the lock.
    assert service._cache.get_json(key) is None


def test_lock_acquire_failure_still_returns_a_response(
    service: CachedCatalogueQueryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even if Redis itself is down (acquire_lock returns None from an error, not
    contention), the request must still complete via PostgreSQL rather than hang."""
    monkeypatch.setattr(service._cache, "acquire_lock", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service._cache, "get_json", lambda *_args, **_kwargs: None)

    value, status = service._cached(
        key="tb:v1:test:stampede-down",
        ttl_seconds=30,
        adapter=_ADAPTER,
        loader=lambda: {"built": True},
        stampede_protect=True,
    )

    assert value == {"built": True}
    assert status == MISS
