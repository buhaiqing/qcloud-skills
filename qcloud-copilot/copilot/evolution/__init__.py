"""EVO-1 self-evolution loop (Generator component)."""

from copilot.evolution.guard import DEFAULT_DRIFT_TOLERANCE, CEIL, FLOOR, SHADOW_RATIO, DriftGuard
from copilot.evolution.policy import EvolutionPolicy
from copilot.evolution.store import Pattern, EvolutionStore

__all__ = [
    "EvolutionStore",
    "Pattern",
    "EvolutionPolicy",
    "DriftGuard",
    "FLOOR",
    "CEIL",
    "SHADOW_RATIO",
    "DEFAULT_DRIFT_TOLERANCE",
]
