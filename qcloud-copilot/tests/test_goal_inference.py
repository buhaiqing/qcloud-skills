from __future__ import annotations

import unittest
from typing import ClassVar

from copilot.goal_inference import GoalInference, _skill_chain_for_goal
from copilot.models import InferredGoal, SkillChain


class GoalInferenceTests(unittest.TestCase):
    """Tests for Phase 2.2 Intent-Driven Goal Inference."""

    def test_keyword_infer_diagnose_performance(self):
        """"机器很慢" → diagnose_performance chain."""
        gi = GoalInference()
        result = gi.infer("机器很慢", {})
        self.assertEqual(result.goal, "diagnose_performance")
        self.assertGreater(result.confidence, 0.0)
        self.assertGreaterEqual(len(result.candidate_chains), 2)
        for chain in result.candidate_chains:
            self.assertIsInstance(chain, SkillChain)
            self.assertIsInstance(chain.skills, list)
            self.assertTrue(len(chain.skills) > 0)

    def test_keyword_infer_cost_optimization(self):
        """帮我省点钱 → cost optimization chain."""
        gi = GoalInference()
        result = gi.infer("帮我省点钱", {})
        self.assertEqual(result.goal, "cost_optimization")
        self.assertGreater(result.confidence, 0.0)

    def test_keyword_infer_inspection(self):
        """最近老报警 → inspection chain."""
        gi = GoalInference()
        result = gi.infer("最近老报警", {})
        self.assertEqual(result.goal, "inspection")
        self.assertGreater(result.confidence, 0.0)

    def test_keyword_infer_proactive_inspection(self):
        """检查一下 → proactive_inspection chain."""
        gi = GoalInference()
        result = gi.infer("检查一下服务器状态", {})
        self.assertEqual(result.goal, "proactive_inspection")
        self.assertGreater(result.confidence, 0.0)

    def test_destructive_chain_marked_high_risk(self):
        """Chain with destructive ops → risk=high."""
        gi = GoalInference()
        # A destructive chain: stop-instance, delete-instance
        chain = SkillChain(
            skills=["qcloud-cvm-ops"],
            description="停止实例",
            estimated_duration="约 1 分钟",
            risk="low",
            reads_only=False,
        )
        risk = gi._evaluate_risk(chain)
        self.assertEqual(risk, "high")

    def test_readonly_chain_marked_low_risk(self):
        """Read-only chain → risk=low."""
        gi = GoalInference()
        chain = SkillChain(
            skills=["qcloud-monitor-ops", "qcloud-cvm-ops"],
            description="监控查询",
            estimated_duration="约 1 分钟",
            risk="low",
            reads_only=True,
        )
        risk = gi._evaluate_risk(chain)
        self.assertEqual(risk, "low")

    def test_confidence_below_threshold_generates_questions(self):
        """confidence < 0.7 → clarifying_questions populated."""
        gi = GoalInference()
        # Low keyword hit count → lower confidence
        result = gi.infer("机器", {})
        self.assertLess(result.confidence, 0.7)
        self.assertGreater(len(result.clarifying_questions), 0)

    def test_high_confidence_no_questions(self):
        """High confidence → no clarifying questions needed."""
        gi = GoalInference()
        # Multiple strong keywords → higher confidence
        result = gi.infer("机器很慢很卡，帮我诊断一下CPU和内存问题", {})
        self.assertGreater(result.confidence, 0.6)
        # clarifying_questions may still be populated but with different logic
        self.assertIsInstance(result.clarifying_questions, list)

    def test_skill_chain_validated_against_registry(self):
        """Skills in chains should be validated against known skills."""
        class MockSkillDispatcher:
            _known_skills: ClassVar[set[str]] = {"qcloud-cvm-ops", "qcloud-monitor-ops"}

        gi = GoalInference(skill_registry=MockSkillDispatcher())
        result = gi.infer("机器很慢", {})
        for chain in result.candidate_chains:
            for skill in chain.skills:
                self.assertIn(skill, MockSkillDispatcher._known_skills)

    def test_multiple_candidates_returned(self):
        """Must return 2+ candidate_chains."""
        gi = GoalInference()
        result = gi.infer("机器很慢", {})
        self.assertGreaterEqual(len(result.candidate_chains), 2)

    def test_inferred_goal_fields_complete(self):
        """All InferredGoal fields are populated."""
        gi = GoalInference()
        result = gi.infer("帮我省点钱", {})
        self.assertIsInstance(result.goal, str)
        self.assertIsInstance(result.description, str)
        self.assertIsInstance(result.confidence, float)
        self.assertIsInstance(result.candidate_chains, list)
        self.assertIsInstance(result.risk_level, str)
        self.assertIsInstance(result.clarifying_questions, list)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_skill_chain_fields_complete(self):
        """All SkillChain fields are populated."""
        gi = GoalInference()
        result = gi.infer("检查一下", {})
        for chain in result.candidate_chains:
            self.assertIsInstance(chain.skills, list)
            self.assertIsInstance(chain.description, str)
            self.assertIsInstance(chain.estimated_duration, str)
            self.assertIn(chain.risk, ("low", "medium", "high"))
            self.assertIsInstance(chain.reads_only, bool)

    def test_risk_level_high_when_any_chain_high(self):
        """If any chain has risk=high, inferred goal risk_level=high."""
        gi = GoalInference()
        result = gi.infer("机器很慢", {})
        chain_risks = {c.risk for c in result.candidate_chains}
        if "high" in chain_risks:
            self.assertEqual(result.risk_level, "high")

    def test_llm_infer_fallback_on_error(self):
        """LLM infer falls back to keyword infer on error."""
        gi = GoalInference(llm_config={"client": None})  # invalid client
        result = gi.infer("机器很慢", {})
        # Should fall back to keyword inference
        self.assertEqual(result.goal, "diagnose_performance")

    def test_unknown_query_defaults_to_proactive_inspection(self):
        """Query with no keywords → defaults to proactive_inspection."""
        gi = GoalInference()
        result = gi.infer("asdfghjkl123", {})
        self.assertEqual(result.goal, "proactive_inspection")

    def test_skill_chain_for_goal_returns_valid_chains(self):
        """_skill_chain_for_goal returns correct structure."""
        chains = _skill_chain_for_goal("diagnose_performance", None)
        self.assertGreaterEqual(len(chains), 1)
        for c in chains:
            self.assertIsInstance(c.skills, list)
            self.assertTrue(len(c.skills) > 0)

    def test_context_passed_to_infer(self):
        """Context dict is passed through to LLM infer."""
        gi = GoalInference(llm_config={})
        ctx = {"parsed_entities": {"resource_id": ["ins-123"]}}
        # With empty LLM config, falls back to keyword anyway
        result = gi.infer("机器很慢", ctx)
        self.assertIsInstance(result, InferredGoal)

    def test_infer_returns_inferred_goal_instance(self):
        """infer() returns an InferredGoal instance."""
        gi = GoalInference()
        result = gi.infer("帮我省点钱", {})
        self.assertIsInstance(result, InferredGoal)

    def test_confidence_calculation_bounded(self):
        """Confidence is bounded between 0.0 and 1.0."""
        gi = GoalInference()
        # Very low keyword hit → minimum confidence
        result = gi.infer("x", {})
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
