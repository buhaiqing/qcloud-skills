"""EVO-1 self-evolution loop (Generator component)."""

from __future__ import annotations

import threading
from contextlib import suppress

from copilot.evolution.guard import CEIL, DEFAULT_DRIFT_TOLERANCE, FLOOR, SHADOW_RATIO, DriftGuard
from copilot.evolution.policy import EvolutionPolicy
from copilot.evolution.store import EvolutionStore, Pattern

__all__ = [
    "CEIL",
    "DEFAULT_DRIFT_TOLERANCE",
    "FLOOR",
    "SHADOW_RATIO",
    "DriftGuard",
    "EvolutionPolicy",
    "EvolutionRegistry",
    "EvolutionStore",
    "Pattern",
    "get_calibration_for_skill",
    "set_calibration_for_skill",
]

# ---------------------------------------------------------------------------
# EvolutionRegistry — runtime threshold injection from EVO-1 policy
# Consumed by gcl_runner._rubric_calibration() to override RUBRIC_THRESHOLDS.
# ---------------------------------------------------------------------------

_calibration_lock = threading.RLock()
_calibrations: dict[str, dict[str, float]] = {}  # skill → {dim: threshold}


class EvolutionRegistry:
    """Thread-safe global registry for per-skill calibrated thresholds.

    Written by CopilotEngine after running EVO-1 subagent fan-out;
    read by gcl_runner._rubric_calibration() before scoring.
    """

    def set(self, skill: str, thresholds: dict[str, float]) -> None:
        with _calibration_lock:
            _calibrations[skill] = dict(thresholds)

    def get(self, skill: str) -> dict[str, float] | None:
        with _calibration_lock:
            return _calibrations.get(skill)

    def clear(self) -> None:
        with _calibration_lock:
            _calibrations.clear()

    def all(self) -> dict[str, dict[str, float]]:
        with _calibration_lock:
            return dict(_calibrations)


# Singleton
_registry = EvolutionRegistry()
set_calibration_for_skill = _registry.set
get_calibration_for_skill = _registry.get


# ---------------------------------------------------------------------------
# Subagent helpers — used by CopilotEngine._query_evolution()
# ---------------------------------------------------------------------------

def query_route_hint(policy: EvolutionPolicy | None, intent) -> str | None:
    """Subagent 1: route_hint from EvolutionPolicy."""
    if policy is None:
        return None
    try:
        return policy.route_hint(intent)
    except Exception:  # noqa: BLE001
        return None


def query_calibrated_thresholds(
    policy: EvolutionPolicy | None, skill: str, dims: list[str]
) -> dict[str, float] | None:
    """Subagent 2: recommend_threshold for each rubric dimension."""
    if policy is None:
        return None
    result: dict[str, float] = {}
    for dim in dims:
        with suppress(Exception):
            val = policy.recommend_threshold(skill, dim)
            if val is not None:
                result[dim] = val
    return result if result else None


def query_op_allowlist(policy: EvolutionPolicy | None, skill: str) -> set[str] | None:
    """Subagent 3: op_allowlist from EvolutionPolicy."""
    if policy is None:
        return None
    try:
        return policy.op_allowlist(skill)
    except Exception:  # noqa: BLE001
        return None
