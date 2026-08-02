"""Approximate, process-local cache hit/miss counters for the Admin system-status
screen (task brief §19: "Approximate hit/miss counters if metrics exist").

Deliberately not Redis-backed: a shared counter would need its own invalidation/reset
story and is not worth the complexity for an approximate, best-effort figure. Counts
reset on process restart and are not aggregated across multiple API worker processes —
"approximate" is the documented contract, not a bug.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

_lock = threading.Lock()
_hits = 0
_misses = 0
_errors = 0


def record_hit() -> None:
    global _hits
    with _lock:
        _hits += 1


def record_miss() -> None:
    global _misses
    with _lock:
        _misses += 1


def record_error() -> None:
    global _errors
    with _lock:
        _errors += 1


@dataclass(frozen=True)
class CacheMetricsSnapshot:
    hits: int
    misses: int
    errors: int


def snapshot() -> CacheMetricsSnapshot:
    with _lock:
        return CacheMetricsSnapshot(hits=_hits, misses=_misses, errors=_errors)
