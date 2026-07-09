#!/usr/bin/env python3
"""Tests for GCL Tier-A conformance checker."""
from __future__ import annotations

import unittest
from pathlib import Path

import check_gcl_conformance as gclc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class SkillListTests(unittest.TestCase):
    def test_32_skills_from_agents_md(self) -> None:
        """The conformance checker must enumerate the same 32 skills declared in AGENTS.md."""
        expected = {
            # Product-scoped (28)
            "qcloud-cvm-ops", "qcloud-cdb-ops", "qcloud-clb-ops", "qcloud-cos-ops",
            "qcloud-es-ops", "qcloud-redis-ops", "qcloud-tke-ops", "qcloud-vpc-ops",
            "qcloud-cam-ops", "qcloud-cdn-ops", "qcloud-cbs-ops", "qcloud-cls-ops",
            "qcloud-ckafka-ops", "qcloud-scf-ops", "qcloud-mongodb-ops",
            "qcloud-postgres-ops", "qcloud-ssl-ops", "qcloud-agsx-ops",
            "qcloud-finops-ops", "qcloud-monitor-ops", "qcloud-ccn-ops",
            "qcloud-vpn-ops", "qcloud-dc-ops", "qcloud-cicd-ops",
            "qcloud-service-mesh-ops", "qcloud-migration-ops", "qcloud-tcop-ops",
            "qcloud-tdmq-ops",
            # Cross-product (3)
            "qcloud-aiops-diagnosis", "qcloud-proactive-inspection",
            "qcloud-well-architected-review",
            # Meta-skill (1)
            "qcloud-skill-generator",
        }
        self.assertEqual(gclc.GCL_SKILLS, expected)


class ConformanceTests(unittest.TestCase):
    def test_all_32_pass(self) -> None:
        """All 32 skills must pass GCL Tier-A conformance."""
        result = gclc.check_all(ROOT)
        failing = [r for r in result if not r["ok"]]
        self.assertEqual(
            failing, [],
            f"{len(failing)} skills fail conformance: {[r['skill'] for r in failing]}",
        )

    def test_rubric_section_count(self) -> None:
        result = gclc.check_all(ROOT)
        for r in result:
            with self.subTest(skill=r["skill"]):
                self.assertEqual(
                    r["rubric_sections"], 8,
                    f"{r['skill']} rubric has {r['rubric_sections']} sections, expected 8",
                )

    def test_prompt_section_count(self) -> None:
        result = gclc.check_all(ROOT)
        for r in result:
            with self.subTest(skill=r["skill"]):
                self.assertEqual(
                    r["prompt_sections"], 7,
                    f"{r['skill']} prompt-templates has {r['prompt_sections']} sections, expected 7",
                )

    def test_quality_gate_present(self) -> None:
        result = gclc.check_all(ROOT)
        for r in result:
            with self.subTest(skill=r["skill"]):
                self.assertTrue(
                    r["has_quality_gate"],
                    f"{r['skill']} SKILL.md missing '## Quality Gate (GCL)' section",
                )


if __name__ == "__main__":
    unittest.main()
