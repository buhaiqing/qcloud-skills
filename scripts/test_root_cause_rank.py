"""Unit tests for RootCauseRanker (P0-5) — SLO-driven root cause ranking.

Covers SPEC §8 Self-check and §10 DoD:
  - default weight sum == 1.0
  - invalid weights (sum != 1) / window_boost <= 0 → ValueError
  - weighted rank formula ordering
  - topology distance ordering
  - impact_score derivation from BusinessContext
  - window adjust (core/release/maintenance)
  - business-impact acceptance: same resource, different context → different priority
  - immutability: rank() does not mutate input candidates
  - components dict present and correct
  - partial weight override (unspecified dims → 0, renormalized; unknown dim → error)
  - NaN/Inf guard on score inputs
  - business_impact clamp to [0, 1]
  - core-hours takes precedence over maintenance window
  - no credentials in JSONL

Run: python3 -m pytest scripts/test_root_cause_rank.py -q
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys_path = str(ROOT / "qcloud-copilot")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from copilot import root_cause_rank as rcr

BusinessContext = rcr.BusinessContext
CandidateRootCause = rcr.CandidateRootCause
RankResult = rcr.RankResult
RootCauseRanker = rcr.RootCauseRanker
default_weights = rcr.default_weights


def ctx(**kw) -> BusinessContext:
    base = {
        "service": "pay-api",
        "business_chain": "payment",
        "customer_tier": "platinum",
        "request_rate": 5000.0,
        "error_budget_consumed": 0.6,
    }
    base.update(kw)
    return BusinessContext(**base)


def cand(candidate_id: str, **kw) -> CandidateRootCause:
    base = {
        "candidate_id": candidate_id,
        "resource": f"res-{candidate_id}",
        "evidence_strength": 0.5,
        "topology_distance": 2,
        "time_correlation": 0.5,
        "historical_prior": 0.3,
    }
    base.update(kw)
    return CandidateRootCause(**base)


class WeightTests(unittest.TestCase):
    def test_default_weights_sum_to_one(self) -> None:
        w = default_weights()
        self.assertAlmostEqual(sum(w.values()), 1.0, places=9)

    def test_invalid_weights_zero_sum_raises(self) -> None:
        with self.assertRaises(ValueError):
            RootCauseRanker(weights={"evidence": 0.0, "topology": 0.0, "time_corr": 0.0, "impact": 0.0, "prior": 0.0})

    def test_window_boost_non_positive_raises(self) -> None:
        with self.assertRaises(ValueError):
            RootCauseRanker(window_boost=0.0)
        with self.assertRaises(ValueError):
            RootCauseRanker(window_boost=-1.0)


class RankOrderingTests(unittest.TestCase):
    def test_high_evidence_high_impact_ranks_above_low(self) -> None:
        ranker = RootCauseRanker()
        high = cand("h", evidence_strength=0.9, time_correlation=0.9, historical_prior=0.8,
                    business_impact=0.9, topology_distance=1)
        low = cand("l", evidence_strength=0.1, time_correlation=0.1, historical_prior=0.1,
                   business_impact=0.1, topology_distance=5)
        results = ranker.rank([low, high], ctx())
        self.assertEqual(results[0].candidate_id, "h")
        self.assertGreater(results[0].score, results[1].score)

    def test_topology_closer_ranks_above_farther(self) -> None:
        ranker = RootCauseRanker()
        near = cand("near", evidence_strength=0.5, time_correlation=0.5, historical_prior=0.3,
                    business_impact=0.5, topology_distance=1)
        far = cand("far", evidence_strength=0.5, time_correlation=0.5, historical_prior=0.3,
                   business_impact=0.5, topology_distance=5)
        results = ranker.rank([far, near], ctx())
        self.assertEqual(results[0].candidate_id, "near")
        self.assertGreater(results[0].score, results[1].score)


class ImpactScoreTests(unittest.TestCase):
    def test_platinum_core_vs_internal_maintenance_differ(self) -> None:
        ranker = RootCauseRanker()
        platinum = ctx(customer_tier="platinum", core_hours=True, maintenance_window=False,
                       request_rate=8000.0, error_budget_consumed=0.9)
        internal = ctx(customer_tier="internal", core_hours=False, maintenance_window=True,
                       request_rate=10.0, error_budget_consumed=0.1)
        c = cand("c", evidence_strength=0.5, topology_distance=2, time_correlation=0.5,
                 historical_prior=0.3, business_impact=None)
        s1 = ranker.impact_score(c, platinum)
        s2 = ranker.impact_score(c, internal)
        self.assertGreater(s1, s2)
        self.assertGreaterEqual(s1, 0.0)
        self.assertLessEqual(s1, 1.0)


class WindowAdjustTests(unittest.TestCase):
    def test_core_hours_boosts_priority(self) -> None:
        ranker = RootCauseRanker(window_boost=1.2)
        c = cand("c", evidence_strength=0.5, topology_distance=2, time_correlation=0.5,
                 historical_prior=0.3, business_impact=0.5)
        neutral = ctx(core_hours=False, release_window=False, maintenance_window=False)
        core = ctx(core_hours=True, release_window=False, maintenance_window=False)
        s_neutral = ranker.rank([c], neutral)[0].priority
        s_core = ranker.rank([c], core)[0].priority
        self.assertAlmostEqual(s_core, s_neutral * 1.2, places=9)
        self.assertGreater(s_core, s_neutral)

    def test_maintenance_window_reduces_priority(self) -> None:
        ranker = RootCauseRanker(window_boost=1.2)
        c = cand("c", evidence_strength=0.5, topology_distance=2, time_correlation=0.5,
                 historical_prior=0.3, business_impact=0.5)
        neutral = ctx(core_hours=False, release_window=False, maintenance_window=False)
        maint = ctx(core_hours=False, release_window=False, maintenance_window=True)
        s_neutral = ranker.rank([c], neutral)[0].priority
        s_maint = ranker.rank([c], maint)[0].priority
        self.assertAlmostEqual(s_maint, s_neutral / 1.2, places=9)
        self.assertLess(s_maint, s_neutral)


class BusinessImpactAcceptanceTests(unittest.TestCase):
    def test_same_resource_different_context_different_priority(self) -> None:
        ranker = RootCauseRanker()
        resource = "ins-pay-001"
        platinum = ctx(customer_tier="platinum", core_hours=True, request_rate=8000.0,
                       error_budget_consumed=0.9, maintenance_window=False)
        internal = ctx(customer_tier="internal", core_hours=False, request_rate=10.0,
                       error_budget_consumed=0.1, maintenance_window=True)
        c = cand("c", resource=resource, evidence_strength=0.5, topology_distance=2,
                 time_correlation=0.5, historical_prior=0.3, business_impact=None)
        p1 = ranker.rank([c], platinum)[0].priority
        p2 = ranker.rank([c], internal)[0].priority
        self.assertNotAlmostEqual(p1, p2, places=9)


class ImmutabilityTests(unittest.TestCase):
    def test_rank_does_not_mutate_candidates(self) -> None:
        ranker = RootCauseRanker()
        a = cand("a", evidence_strength=0.8, business_impact=0.8)
        b = cand("b", evidence_strength=0.2, business_impact=0.2)
        inputs = [a, b]
        before = [(c.candidate_id, c.priority) for c in inputs]
        ranker.rank(inputs, ctx())
        after = [(c.candidate_id, c.priority) for c in inputs]
        self.assertEqual(before, after)
        self.assertTrue(all(c.priority == 0.0 for c in inputs))


class ComponentsTests(unittest.TestCase):
    def test_components_present_and_correct(self) -> None:
        ranker = RootCauseRanker(weights={"evidence": 0.35, "topology": 0.2, "time_corr": 0.15,
                                          "impact": 0.2, "prior": 0.1})
        c = cand("c", evidence_strength=0.8, topology_distance=1, time_correlation=0.7,
                 historical_prior=0.4, business_impact=0.6)
        result = ranker.rank([c], ctx())[0]
        expected_impact = ranker.impact_score(c, ctx())
        expected_score = (0.35 * 0.8 + 0.2 * (1 / (1 + 1)) + 0.15 * 0.7
                          + 0.2 * expected_impact + 0.1 * 0.4)
        self.assertAlmostEqual(result.components["evidence"], 0.35 * 0.8, places=9)
        self.assertAlmostEqual(result.components["topology"], 0.2 * (1 / (1 + 1)), places=9)
        self.assertAlmostEqual(result.components["time_corr"], 0.15 * 0.7, places=9)
        self.assertAlmostEqual(result.components["impact"], 0.2 * expected_impact, places=9)
        self.assertAlmostEqual(result.components["prior"], 0.1 * 0.4, places=9)
        self.assertAlmostEqual(result.score, expected_score, places=9)


class WeightOverrideTests(unittest.TestCase):
    def test_partial_weights_zero_unspecified_dims(self) -> None:
        # Only "evidence" supplied: unspecified dims default to 0 (not the
        # default weight), so the caller must restate every dim they want.
        ranker = RootCauseRanker(weights={"evidence": 1.0})
        self.assertAlmostEqual(sum(ranker.weights.values()), 1.0, places=9)
        self.assertEqual(ranker.weights["evidence"], 1.0)
        self.assertEqual(ranker.weights["topology"], 0.0)
        self.assertEqual(ranker.weights["prior"], 0.0)

    def test_partial_weights_expresses_relative_importance(self) -> None:
        # Partial override expresses relative importance: unspecified dims are
        # 0 and the effective set is renormalized to sum 1.0.
        ranker = RootCauseRanker(weights={"evidence": 2.0, "impact": 1.0})
        self.assertAlmostEqual(sum(ranker.weights.values()), 1.0, places=9)
        self.assertAlmostEqual(ranker.weights["evidence"], 2.0 / 3.0, places=9)
        self.assertAlmostEqual(ranker.weights["impact"], 1.0 / 3.0, places=9)
        self.assertEqual(ranker.weights["topology"], 0.0)

    def test_unknown_weight_dim_raises(self) -> None:
        with self.assertRaises(ValueError):
            RootCauseRanker(weights={"evidence": 0.5, "bogus": 0.5})


class NaNGuardTests(unittest.TestCase):
    def _rank_one(self, **kw) -> list:
        ranker = RootCauseRanker()
        return ranker.rank([cand("c", **kw)], ctx())

    def test_nan_evidence_raises(self) -> None:
        with self.assertRaises(ValueError):
            self._rank_one(evidence_strength=float("nan"))

    def test_inf_time_correlation_raises(self) -> None:
        with self.assertRaises(ValueError):
            self._rank_one(time_correlation=float("inf"))

    def test_nan_prior_raises(self) -> None:
        with self.assertRaises(ValueError):
            self._rank_one(historical_prior=float("nan"))

    def test_nan_business_impact_raises(self) -> None:
        with self.assertRaises(ValueError):
            self._rank_one(business_impact=float("nan"))


class ImpactClampTests(unittest.TestCase):
    def test_business_impact_clamped_to_unit_interval(self) -> None:
        ranker = RootCauseRanker()
        c = cand("c", business_impact=1.5)
        self.assertAlmostEqual(ranker.impact_score(c, ctx()), 1.0, places=9)
        c_low = cand("c", business_impact=-0.5)
        self.assertAlmostEqual(ranker.impact_score(c_low, ctx()), 0.0, places=9)


class WindowPrecedenceTests(unittest.TestCase):
    def test_core_hours_takes_precedence_over_maintenance(self) -> None:
        # core/release boost wins even if maintenance is also set.
        ranker = RootCauseRanker(window_boost=1.2)
        c = cand("c", evidence_strength=0.5, topology_distance=2, time_correlation=0.5,
                 historical_prior=0.3, business_impact=0.5)
        neutral = ctx(core_hours=False, release_window=False, maintenance_window=False)
        both = ctx(core_hours=True, release_window=False, maintenance_window=True)
        s_neutral = ranker.rank([c], neutral)[0].priority
        s_both = ranker.rank([c], both)[0].priority
        self.assertAlmostEqual(s_both, s_neutral * 1.2, places=9)


class NoCredentialsTests(unittest.TestCase):
    def test_jsonl_contains_no_credentials(self) -> None:
        # context/candidate with secret-looking fields must not carry real credentials.
        rec = {
            "context": ctx(customer_tier="platinum").__dict__,
            "candidates": [
                cand("c", business_impact=0.5).__dict__,
            ],
        }
        blob = json.dumps(rec)
        self.assertNotIn("AKID", blob)
        self.assertNotIn("secret", blob)
        self.assertNotIn("SecretKey", blob)


if __name__ == "__main__":
    unittest.main()

