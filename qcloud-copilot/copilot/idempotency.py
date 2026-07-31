"""P5.4 — idempotent emission helper.

with_idempotency_key(producer, idempotency_key) -> (record, was_duplicate)

Caller passes a `producer` callable that builds an ObservationRecord. The
first invocation emits and returns `(record, False)`. Subsequent calls with
the same `idempotency_key` return the cached record and `(record, True)`.

Thread-safe: locks guard the registry of completed keys.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

_LOCK = threading.Lock()
_KEYS: dict[str, Any] = {}


def with_idempotency_key(
    *,
    producer: Callable[[], Any],
    idempotency_key: str,
) -> tuple[Any, bool]:
    """Return (record, was_duplicate)."""
    with _LOCK:
        cached = _KEYS.get(idempotency_key)
        if cached is not None:
            return cached, True
        record = producer()
        _KEYS[idempotency_key] = record
        return record, False


def reset_idempotency_registry() -> None:
    """Drop all cached keys (test helper)."""
    with _LOCK:
        _KEYS.clear()
