#!/usr/bin/env python3
"""Unit tests for scripts/check_gcl_conformance.py (GCL Tier-A conformance gate).

Pure stdlib — no external dependencies. Run with:
    python3 -m unittest gcl_conformance_test -v

Covers:
- GCL_SKILLS matches the 24-skill set declared in AGENTS.md §8.
- _count_numbered_sections returns 0 on any gap, target on full coverage.
- check_skill returns the expected keys.
- check_all iterates all 24 skills, sorted by name.
- Conformance: rubric, prompt, and Quality Gate are detected correctly.

Note: ``test_all_24_pass`` is intentionally failing on master as of 2026-06-18
(4 skills conform out of 24). It documents the audit baseline — subsequent
phases of the Tier-A Conformance Plan will close the gap.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure scripts/ is on sys.path when invoked as `python3 scripts/gcl_conformance_test.py`
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import check_gcl_conformance as gclc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class SkillListTests(unittest.TestCase):
    def test_24_skills_from_agents_md(self) -> None:
        """The conformance checker must enumerate the same 24 skills declared in AGENTS.md §8."""
        expected = {
            "qcloud-cvm-ops", "qcloud-cdb-ops", "qcloud-clb-ops", "qcloud-cos-ops",
            "qcloud-es-ops", "qcloud-redis-ops", "qcloud-tke-ops", "qcloud-vpc-ops",
            "qcloud-cam-ops", "qcloud-cdn-ops", "qcloud-cbs-ops", "qcloud-cls-ops",
            "qcloud-ckafka-ops", "qcloud-scf-ops", "qcloud-mongodb-ops",
            "qcloud-postgres-ops", "qcloud-ssl-ops", "qcloud-agsx-ops",
            "qcloud-finops-ops", "qcloud-monitor-ops", "qcloud-aiops-diagnosis",
            "qcloud-proactive-inspection", "qcloud-well-architected-review",
            "qcloud-skill-generator",
        }
        self.assertEqual(gclc.GCL_SKILLS, expected)
        self.assertEqual(len(gclc.GCL_SKILLS), 24)


class CounterTests(unittest.TestCase):
    def test_full_coverage_returns_target(self) -> None:
        text = "\n".join(f"## {n}. Title" for n in range(1, 9))
        self.assertEqual(gclc._count_numbered_sections(text, 8), 8)

    def test_missing_section_returns_zero(self) -> None:
        text = "\n".join(f"## {n}. Title" for n in range(1, 8))  # missing 8
        self.assertEqual(gclc._count_numbered_sections(text, 8), 0)

    def test_empty_text_returns_zero(self) -> None:
        self.assertEqual(gclc._count_numbered_sections("", 7), 0)

    def test_non_sequential_returns_zero(self) -> None:
        # Gaps (skipped number) also fail
        text = "## 1. X\n## 3. Y\n## 4. Z\n## 5. W\n## 6. V\n## 7. U\n## 8. T"
        self.assertEqual(gclc._count_numbered_sections(text, 8), 0)


class CheckSkillTests(unittest.TestCase):
    def test_check_skill_returns_expected_keys(self) -> None:
        report = gclc.check_skill(ROOT, "qcloud-cvm-ops")
        expected = {
            "skill", "rubric_sections", "prompt_sections",
            "has_quality_gate", "rubric_ok", "prompt_ok", "skill_ok", "ok",
        }
        self.assertEqual(set(report.keys()), expected)

    def test_check_skill_conformant(self) -> None:
        # qcloud-cdb-ops is one of the 4 fully conformant skills (verified 2026-06-18)
        report = gclc.check_skill(ROOT, "qcloud-cdb-ops")
        self.assertEqual(report["rubric_sections"], 8)
        self.assertEqual(report["prompt_sections"], 7)
        self.assertTrue(report["has_quality_gate"])
        self.assertTrue(report["ok"])

    def test_check_skill_missing_files(self) -> None:
        # qcloud-skill-generator is missing all three artifacts
        report = gclc.check_skill(ROOT, "qcloud-skill-generator")
        self.assertFalse(report["has_quality_gate"])
        self.assertFalse(report["ok"])


class CheckAllTests(unittest.TestCase):
    def test_check_all_24_sorted(self) -> None:
        result = gclc.check_all(ROOT)
        self.assertEqual(len(result), 24)
        skills = [r["skill"] for r in result]
        self.assertEqual(skills, sorted(skills))


class ConformanceTests(unittest.TestCase):
    def test_all_24_pass(self) -> None:
        """Once this plan completes, the conformance check passes on all 24 skills.

        As of 2026-06-18, only 4 skills (cvm, cdb, clb, cos) are fully conformant.
        This test is expected to fail; subsequent phases of the Tier-A Conformance
        Plan will close the gap. When this test passes, the gate is green.
        """
        result = gclc.check_all(ROOT)
        failing = [r["skill"] for r in result if not r["ok"]]
        self.assertEqual(
            failing, [],
            f"Expected all 24 skills to conform; failing: {failing}",
        )

    def test_rubric_section_count(self) -> None:
        """All 24 skills must have rubric.md with exactly 8 numbered sections (1..8, no gaps)."""
        result = gclc.check_all(ROOT)
        failing = [r["skill"] for r in result if not r["rubric_ok"]]
        self.assertEqual(
            failing, [],
            f"Skills with non-conformant rubric.md: {failing}",
        )

    def test_prompt_section_count(self) -> None:
        """All 24 skills must have prompt-templates.md with exactly 7 numbered sections (1..7, no gaps)."""
        result = gclc.check_all(ROOT)
        failing = [r["skill"] for r in result if not r["prompt_ok"]]
        self.assertEqual(
            failing, [],
            f"Skills with non-conformant prompt-templates.md: {failing}",
        )

    def test_quality_gate_present(self) -> None:
        """All 24 SKILL.md files must contain the `## Quality Gate (GCL)` heading."""
        result = gclc.check_all(ROOT)
        failing = [r["skill"] for r in result if not r["skill_ok"]]
        self.assertEqual(
            failing, [],
            f"Skills missing `## Quality Gate (GCL)` in SKILL.md: {failing}",
        )


if __name__ == "__main__":
    unittest.main()
