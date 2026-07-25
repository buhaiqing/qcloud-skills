"""P5.4 — partial-failure recovery wrapper around an emissions sink.

emit_with_recovery(sink, observations) -> {
    success_count, failure_count, failures: [{index, error_type, message}, ...]
}

Each individual emit_observation call is wrapped in try/except. Successful
emits remain visible to the underlying sink; failures are reported but do
not block other emits.
"""
from __future__ import annotations

from typing import Iterable


def emit_with_recovery(sink, observations: Iterable) -> dict:
    """Best-effort emit each obs to `sink.emit_observation`. Never raises.

    Returns aggregate counts and per-failure detail.
    """
    success = 0
    failures: list[dict] = []
    for idx, obs in enumerate(observations):
        try:
            sink.emit_observation(obs)
            success += 1
        except BaseException as exc:
            failures.append({
                "index": idx,
                "obs_id": getattr(obs, "id", None),
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            })
    return {
        "success_count": success,
        "failure_count": len(failures),
        "failures": failures,
    }
