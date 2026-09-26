#!/usr/bin/env python3
"""CR-3 + H-50: kpi-gates job must depend on a committed fixture, not a GATE_REQUIRE_EVIDENCE escape.

The CR-3 split (validate-skills.yml's `kpi-gates` job) is what makes the KPI gate
trustworthy on a CI runner: it grades a committed fixture staged under a name,
not whatever earlier steps in the same job happened to write into audit-results/.

Before CR-3, the gate ran as step 16 of 17 and was silently skipped whenever an
earlier non-`continue-on-error` step failed. The escape
`GATE_REQUIRE_EVIDENCE=0` would have masked that AND any future policy
regressions: it returns *before* any file is read, so with it set KPI#1/#2
cannot fail the build regardless of evidence. Setting it inside the `kpi-gates`
job is a quiet way to disarm the guard the job exists to enforce.

H-50 (no silent degradation) is the corollary in code: any non-pass status
including "skip" must turn CI red. A kpi-gates job that bails out via the
escape would be a green build that graded nothing — the defect in test form.

This test is the guardrail: assert the kpi-gates job block does not name the
escape. A future PR that adds it back fails CI before the change ships.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows" / "validate-skills.yml"


class KpiGatesJobGatingTest(unittest.TestCase):
    def test_kpi_gates_job_never_sets_GATE_REQUIRE_EVIDENCE(self) -> None:
        yaml_text = WORKFLOWS.read_text(encoding="utf-8")
        self.assertIn("kpi-gates:", yaml_text, "kpi-gates job missing from workflow")
        m = re.search(r"^  kpi-gates:\s*\n((?: {4,}.*\n?)+)", yaml_text, re.MULTILINE)
        self.assertIsNotNone(m, "could not locate kpi-gates job block")
        block = m.group(1)
        self.assertNotIn("GATE_REQUIRE_EVIDENCE", block,
            "kpi-gates job must not reference GATE_REQUIRE_EVIDENCE — CR-3 + H-50 require it depend on committed fixture")


if __name__ == "__main__":
    unittest.main()