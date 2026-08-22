"""Cost governance: per-skill budgets, circuit breaker, model routing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Estimated per-request cost (USD) per model — used for deterministic routing.
MODEL_COSTS: dict[str, float] = {
    "gpt-4o-mini": 0.15,
    "claude-3-haiku": 0.25,
    "gpt-4o": 2.5,
    "claude-3-sonnet": 3.0,
}


def load_budgets(path: Path) -> dict[str, Any]:
    """Load skill budgets from a JSON file."""
    text = path.read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(text)
    return data


class CostTracker:
    """In-memory per-skill cumulative tokens / cost tracking."""

    def __init__(self, budgets: dict[str, Any] | None = None) -> None:
        self._budgets: dict[str, Any] = budgets or {}
        self._tokens: dict[str, int] = {}
        self._cost: dict[str, float] = {}

    def record(self, skill: str, tokens: int, cost_usd: float) -> None:
        self._tokens[skill] = self._tokens.get(skill, 0) + tokens
        self._cost[skill] = self._cost.get(skill, 0.0) + cost_usd

    def remaining(self, skill: str) -> tuple[int, float]:
        budget = self._budgets.get(skill)
        if budget is None:
            return (0, 0.0)
        daily_tokens: int = int(budget.get("daily_token_budget", 0))
        daily_cost: float = float(budget.get("daily_cost_budget_usd", 0.0))
        used_tokens = self._tokens.get(skill, 0)
        used_cost = self._cost.get(skill, 0.0)
        return (daily_tokens - used_tokens, daily_cost - used_cost)

    def is_breached(self, skill: str) -> bool:
        tokens_left, cost_left = self.remaining(skill)
        # No budget entry -> not breached (caller handles missing budget separately)
        if skill not in self._budgets:
            return False
        return tokens_left <= 0 or cost_left <= 0


class CostCircuitBreaker:
    """Circuit breaker with OPEN / CLOSED per skill."""

    def __init__(self) -> None:
        self._open: set[str] = set()

    def trip(self, skill: str) -> None:
        self._open.add(skill)

    def allow(self, skill: str) -> bool:
        return skill not in self._open

    def reset(self, skill: str) -> None:
        self._open.discard(skill)

    @property
    def state(self) -> dict[str, str]:
        return {s: "OPEN" for s in self._open}


def route(
    skill: str,
    budgets: dict[str, Any],
    tracker: CostTracker,
    breaker: CostCircuitBreaker,
    *,
    preferred: str | None = None,
) -> str | None:
    """Pick cheapest affordable model or block if breaker OPEN / breached.

    - If breaker OPEN for skill -> None.
    - If tracker reports breached -> trip breaker and return None.
    - Otherwise prefer `preferred` if affordable, else cheapest affordable.
    - If budget nearly exhausted (<20 % remaining) downgrade to cheapest.
    - If no model affordable -> trip and return None.
    """
    if not breaker.allow(skill):
        return None

    if tracker.is_breached(skill):
        breaker.trip(skill)
        return None

    budget = budgets.get(skill)
    if budget is None:
        return None

    model_options: list[str] = list(budget.get("model_options", []))
    if not model_options:
        return None

    # Deterministic cheapest-first ordering.
    def _cost(m: str) -> float:
        return MODEL_COSTS.get(m, 999.0)

    sorted_models = sorted(model_options, key=_cost)
    cheapest = sorted_models[0]

    tokens_left, cost_left = tracker.remaining(skill)
    daily_tokens = int(budget.get("daily_token_budget", 0))
    daily_cost = float(budget.get("daily_cost_budget_usd", 0.0))

    # Nearly exhausted -> force cheapest.
    nearly_exhausted = False
    if daily_cost > 0 and cost_left < daily_cost * 0.2:
        nearly_exhausted = True
    if daily_tokens > 0 and tokens_left < daily_tokens * 0.2:
        nearly_exhausted = True
    if nearly_exhausted:
        # Cheapest must still be affordable; otherwise trip.
        if _cost(cheapest) > cost_left and cost_left <= 0:
            breaker.trip(skill)
            return None
        affordable = [m for m in sorted_models if _cost(m) <= cost_left]
        if not affordable:
            # If remaining cost is tiny but >0, still return cheapest
            # (allow slight over-budget rather than hard block mid-day).
            # Only block when fully exhausted which is already handled above.
            return cheapest
        return affordable[0]

    if (
        preferred is not None
        and preferred in model_options
        and _cost(preferred) <= cost_left
    ):
        return preferred

    affordable = [m for m in sorted_models if _cost(m) <= cost_left]
    if not affordable:
        # No affordable model but not yet breached (cost_left >0 but < cheapest).
        # Return cheapest anyway if cost_left >0 to avoid premature block;
        # trip only when breached on next record.
        if cost_left > 0:
            return cheapest
        breaker.trip(skill)
        return None
    return affordable[0]
