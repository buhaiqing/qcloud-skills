# P1-5 Cost Governance — Design Spec

## Background

Skills invoke LLMs per operation. Without per-skill budgets a single noisy skill can burn the daily quota and block others. This spec adds token/cost budgets, a circuit breaker, and cost-aware routing.

## Budget Model

`assets/shared/skill_budgets.json` maps skill → budget:

```json
{
  "qcloud-cvm-ops": {
    "daily_token_budget": 1000000,
    "daily_cost_budget_usd": 5.0,
    "model_options": ["gpt-4o-mini", "gpt-4o", "claude-3-haiku"],
    "default_model": "gpt-4o-mini"
  }
}
```

- `daily_token_budget` / `daily_cost_budget_usd`: hard daily caps.
- `model_options`: allowed models ordered arbitrarily; routing picks cheapest affordable.
- `default_model`: preferred when budget is healthy.

Pricing reference (`scripts/cost_governor.py:MODEL_COSTS`) provides deterministic cost per model for routing decisions (e.g. `gpt-4o-mini: 0.15`, `gpt-4o: 2.5`).

## Breaker State Machine

```
CLOSED --trip()--> OPEN --reset()--> CLOSED
```

- `CostCircuitBreaker.allow(skill)`: `False` when OPEN.
- `trip(skill)` on `CostTracker.is_breached(skill)` (tokens_left ≤ 0 or cost_left ≤ 0).
- `reset(skill)` clears OPEN (e.g. next day cron).

## Routing Logic

`route(skill, budgets, tracker, breaker, *, preferred=None) -> str | None`

1. If `breaker` OPEN → `None` (blocked).
2. If `tracker.is_breached` → `trip` + `None`.
3. If skill missing from budgets or `model_options` empty → `None`.
4. Sort `model_options` by `MODEL_COSTS` ascending (deterministic).
5. If remaining < 20 % of daily budget (tokens or cost) → force cheapest affordable.
6. If `preferred` given and affordable → return it.
7. Else return cheapest affordable model within `cost_left`.
8. If no model affordable → `trip` + `None`.

## Verification

```python
assert load_budgets(path)["qcloud-cvm-ops"]["daily_token_budget"] > 0
tracker = CostTracker(budgets)
tracker.record(skill, 100, 0.1)
assert tracker.remaining(skill)[0] == budgets[skill]["daily_token_budget"] - 100
assert not tracker.is_breached(skill)
tracker.record(skill, 10**9, 10**9)
assert tracker.is_breached(skill)
breaker = CostCircuitBreaker()
breaker.trip(skill)
assert not breaker.allow(skill)
assert route(skill, budgets, tracker, breaker) is None
```

## Files

| File | Purpose |
|------|---------|
| `assets/shared/skill_budgets.json` | Per-skill budgets |
| `scripts/cost_governor.py` | `load_budgets`, `CostTracker`, `CostCircuitBreaker`, `route` |
| `scripts/cost_governor_test.py` | Unit tests |
