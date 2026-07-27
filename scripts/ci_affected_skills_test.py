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
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("qcloud-cvm-ops", result.stdout)


if __name__ == "__main__":
    from unittest import main

    main()
