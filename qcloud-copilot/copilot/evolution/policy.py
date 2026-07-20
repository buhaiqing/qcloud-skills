"""EVO-1 Decision layer (the Generator).

Turns stored patterns plus live OBS-1 metrics into three decision signals:

* :meth:`route_hint`  — warns when a skill carries many high-confidence failures.
* :meth:`op_allowlist` — surfaces operations proven by success patterns so the
  hallucination guard can whitelist them.
* :meth:`recommend_threshold` — nudges a rubric/quality threshold down when a
  skill is risky (low success rate or many failures).

The ``query`` argument is the OBS-1 ``observ_query`` module; it is optional and
every method degrades gracefully when it is ``None`` or raises.
"""

from __future__ import annotations

from copilot.evolution.store import EvolutionStore

FAIL_COUNT_THRESHOLD = 3
SUCCESS_RATE_FLOOR = 0.8
BASE_THRESHOLD = 0.7


def _as_skill(intent) -> str | None:
    if intent is None:
        return None
    if isinstance(intent, str):
        return intent
    primary = getattr(intent, "primary", None)
    if primary is None:
        return None
    return str(primary)


class EvolutionPolicy:
    def __init__(self, store: EvolutionStore, query):
        self._store = store
        self._query = query  # OBS-1 observ_query module/functions

    # -- high-frequency failure routing ----------------------------------

    def route_hint(self, intent) -> str | None:
        skill = _as_skill(intent)
        if not skill:
            return None
        failures = [
            p
            for p in self._store.load()
            if p.kind == "failure" and p.skill == skill and p.confidence >= 0.7
        ]
        if len(failures) >= FAIL_COUNT_THRESHOLD:
            return (
                f"WARNING: skill '{skill}' has {len(failures)} high-confidence failure "
                f"patterns recorded; require explicit --confirm and add extra "
                f"pre/post validation before execution."
            )
        return None

    # -- operation allowlist (anti-hallucination) -----------------------

    def op_allowlist(self, skill: str) -> set[str]:
        return {
            p.command
            for p in self._store.load()
            if p.kind == "success" and p.skill == skill and p.command
        }

    # -- threshold recommendation ---------------------------------------

    def recommend_threshold(self, skill: str, dim: str) -> float | None:
        rate = self._success_rate(skill)
        fail_n = sum(
            1
            for p in self._store.load()
            if p.kind == "failure" and p.skill == skill and p.confidence >= 0.7
        )
        if rate == 0.0 and fail_n == 0:
            return None
        adj = 0.0
        if rate and rate < SUCCESS_RATE_FLOOR:
            adj += (SUCCESS_RATE_FLOOR - rate) * 0.5
        adj += min(0.2, fail_n * 0.02)
        return round(min(1.0, BASE_THRESHOLD + adj), 3)

    # -- helpers ---------------------------------------------------------

    def _success_rate(self, skill: str) -> float:
        if self._query is None:
            return 0.0
        try:
            return float(self._query.skill_success_rate(skill))
        except Exception:
            return 0.0
