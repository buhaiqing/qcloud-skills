"""EVO-1 Guard layer.

Two responsibilities:

* *Bound*: :meth:`clamp` keeps any evolution-derived numeric value inside a safe
  ``[FLOOR, CEIL]`` interval (e.g. a recommended threshold).
* *Shadow*: :meth:`should_use_evolution` deterministically routes a small,
  stable fraction of runs (``SHADOW_RATIO``) through evolution logic so new
  policies are validated on live traffic before a full rollout, and
  :meth:`evaluate` gates the rollout on whether quality held or improved.
"""

from __future__ import annotations

import hashlib

FLOOR = 0.0
CEIL = 1.0
SHADOW_RATIO = 0.05
DEFAULT_DRIFT_TOLERANCE = 0.1


class DriftGuard:
    def clamp(self, value: float, floor: float = FLOOR, ceil: float = CEIL) -> float:
        return max(floor, min(value, ceil))

    def should_use_evolution(self, run_id: str) -> bool:
        if not run_id:
            return False
        digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
        frac = int(digest[:8], 16) / 0xFFFFFFFF
        return frac < SHADOW_RATIO

    def evaluate(
        self,
        before_rate: float,
        after_rate: float,
        tolerance: float = DEFAULT_DRIFT_TOLERANCE,
    ) -> bool:
        if before_rate <= 0:
            return after_rate >= 0.0
        return after_rate >= max(0.0, before_rate - tolerance)
