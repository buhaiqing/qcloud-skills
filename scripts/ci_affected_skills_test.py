#!/usr/bin/env python3
"""Tests for ci_affected_skills (KPI #4): deterministic stdin diff path."""
import subprocess
import sys
from pathlib import Path
from unittest import TestCase

SCRIPT = Path(__file__).resolve().parent / "ci_affected_skills.py"


class CiAffectedSkillsTest(TestCase):
    def test_detects_changed_skill(self) -> None:
        diff = "qcloud-cvm-ops/SKILL.md\nqcloud-cvm-ops/assets/golden/list_instances.json\n"
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=diff,
            capture_output=True,
            text=True,
        check=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn("qcloud-cvm-ops", result.stdout)

    def test_no_false_positive_on_unrelated_diff(self) -> None:
        # A diff touching only non-skill files must NOT emit any qcloud-*-ops name.
        diff = "README.md\nscripts/validate_local.py\ndocs/design.md\n"
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=diff,
            capture_output=True,
            text=True,
        check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    from unittest import main

    main()
