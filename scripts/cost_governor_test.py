"""Unit tests for cost_governor."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import cost_governor as cg

CostCircuitBreaker = cg.CostCircuitBreaker
CostTracker = cg.CostTracker
load_budgets = cg.load_budgets
route = cg.route


class LoadBudgetsTest(unittest.TestCase):
    def test_load_budgets(self) -> None:
        data = {
            "qcloud-cvm-ops": {
                "daily_token_budget": 1000000,
                "daily_cost_budget_usd": 5.0,
                "model_options": ["gpt-4o-mini", "gpt-4o"],
                "default_model": "gpt-4o-mini",
            }
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            tmp = Path(f.name)
        try:
            loaded = load_budgets(tmp)
            self.assertIn("qcloud-cvm-ops", loaded)
            self.assertEqual(loaded["qcloud-cvm-ops"]["daily_token_budget"], 1000000)
        finally:
            tmp.unlink(missing_ok=True)

    def test_load_shared_budgets(self) -> None:
        path = Path(__file__).resolve().parents[1] / "assets" / "shared" / "skill_budgets.json"
        if not path.exists():
            self.skipTest("skill_budgets.json not found")
        budgets = load_budgets(path)
        for skill in ("qcloud-cvm-ops", "qcloud-cdb-ops", "qcloud-cos-ops"):
            self.assertIn(skill, budgets)
            self.assertIn("daily_token_budget", budgets[skill])
            self.assertIn("daily_cost_budget_usd", budgets[skill])
            self.assertIn("model_options", budgets[skill])
            self.assertIn("default_model", budgets[skill])


class CostTrackerTest(unittest.TestCase):
    def test_record_accumulates(self) -> None:
        budgets = {
            "qcloud-cvm-ops": {
                "daily_token_budget": 1000000,
                "daily_cost_budget_usd": 5.0,
                "model_options": ["gpt-4o-mini", "gpt-4o"],
                "default_model": "gpt-4o-mini",
            }
        }
        tracker = CostTracker(budgets)
        tracker.record("qcloud-cvm-ops", 100, 0.1)
        tracker.record("qcloud-cvm-ops", 200, 0.2)
        tokens_left, cost_left = tracker.remaining("qcloud-cvm-ops")
        self.assertEqual(tokens_left, 1000000 - 300)
        self.assertAlmostEqual(cost_left, 5.0 - 0.3)

    def test_is_breached(self) -> None:
        budgets = {
            "qcloud-cvm-ops": {
                "daily_token_budget": 100,
                "daily_cost_budget_usd": 1.0,
                "model_options": ["gpt-4o-mini"],
                "default_model": "gpt-4o-mini",
            }
        }
        tracker = CostTracker(budgets)
        self.assertFalse(tracker.is_breached("qcloud-cvm-ops"))
        tracker.record("qcloud-cvm-ops", 100, 0.0)
        self.assertTrue(tracker.is_breached("qcloud-cvm-ops"))


class CircuitBreakerTest(unittest.TestCase):
    def test_breach_trips_breaker(self) -> None:
        budgets = {
            "qcloud-cvm-ops": {
                "daily_token_budget": 100,
                "daily_cost_budget_usd": 1.0,
                "model_options": ["gpt-4o-mini"],
                "default_model": "gpt-4o-mini",
            }
        }
        tracker = CostTracker(budgets)
        breaker = CostCircuitBreaker()
        self.assertTrue(breaker.allow("qcloud-cvm-ops"))
        tracker.record("qcloud-cvm-ops", 100, 1.0)
        # Simulate breach handling via route or manual trip
        if tracker.is_breached("qcloud-cvm-ops"):
            breaker.trip("qcloud-cvm-ops")
        self.assertFalse(breaker.allow("qcloud-cvm-ops"))
        breaker.reset("qcloud-cvm-ops")
        self.assertTrue(breaker.allow("qcloud-cvm-ops"))


class RoutingTest(unittest.TestCase):
    def test_routing_picks_cheapest_within_budget(self) -> None:
        budgets = {
            "qcloud-cvm-ops": {
                "daily_token_budget": 1000000,
                "daily_cost_budget_usd": 5.0,
                "model_options": ["gpt-4o", "gpt-4o-mini", "claude-3-haiku"],
                "default_model": "gpt-4o-mini",
            }
        }
        tracker = CostTracker(budgets)
        breaker = CostCircuitBreaker()
        model = route("qcloud-cvm-ops", budgets, tracker, breaker)
        # Cheapest is gpt-4o-mini (0.15)
        self.assertEqual(model, "gpt-4o-mini")

    def test_breach_blocks_routing(self) -> None:
        budgets = {
            "qcloud-cvm-ops": {
                "daily_token_budget": 100,
                "daily_cost_budget_usd": 1.0,
                "model_options": ["gpt-4o-mini", "gpt-4o"],
                "default_model": "gpt-4o-mini",
            }
        }
        tracker = CostTracker(budgets)
        breaker = CostCircuitBreaker()
        tracker.record("qcloud-cvm-ops", 100, 1.0)
        model = route("qcloud-cvm-ops", budgets, tracker, breaker)
        self.assertIsNone(model)
        self.assertFalse(breaker.allow("qcloud-cvm-ops"))

    def test_open_breaker_blocks_routing(self) -> None:
        budgets = {
            "qcloud-cvm-ops": {
                "daily_token_budget": 1000000,
                "daily_cost_budget_usd": 5.0,
                "model_options": ["gpt-4o-mini"],
                "default_model": "gpt-4o-mini",
            }
        }
        tracker = CostTracker(budgets)
        breaker = CostCircuitBreaker()
        breaker.trip("qcloud-cvm-ops")
        model = route("qcloud-cvm-ops", budgets, tracker, breaker)
        self.assertIsNone(model)


if __name__ == "__main__":
    unittest.main()
