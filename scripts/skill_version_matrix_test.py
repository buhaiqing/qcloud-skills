from __future__ import annotations

import unittest

from skill_version_matrix import (
    SKILL_COMPAT,
    compatible_skills,
    is_compatible,
    parse_version,
    render_matrix,
)


class ParseVersionTest(unittest.TestCase):
    def test_full_semver(self) -> None:
        self.assertEqual(parse_version("1.2.3"), (1, 2, 3))

    def test_two_parts(self) -> None:
        self.assertEqual(parse_version("1.2"), (1, 2, 0))

    def test_one_part(self) -> None:
        self.assertEqual(parse_version("2"), (2, 0, 0))

    def test_with_v_prefix(self) -> None:
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))


class IsCompatibleTest(unittest.TestCase):
    def test_in_range(self) -> None:
        self.assertTrue(is_compatible("qcloud-cvm-ops", "1.2.0"))
        self.assertTrue(is_compatible("qcloud-cvm-ops", "2.0.0"))

    def test_out_of_range_below_min(self) -> None:
        self.assertFalse(is_compatible("qcloud-cvm-ops", "1.1.9"))

    def test_finops_requires_higher_min(self) -> None:
        self.assertFalse(is_compatible("qcloud-finops-ops", "1.2.0"))
        self.assertTrue(is_compatible("qcloud-finops-ops", "1.5.0"))

    def test_unknown_skill(self) -> None:
        self.assertFalse(is_compatible("qcloud-unknown-ops", "1.5.0"))

    def test_tccli_version_check(self) -> None:
        self.assertFalse(is_compatible("qcloud-cvm-ops", "1.5.0", tccli_version="2.9.9"))
        self.assertTrue(is_compatible("qcloud-cvm-ops", "1.5.0", tccli_version="3.0.0"))

    def test_tccli_none_skips_check(self) -> None:
        self.assertTrue(is_compatible("qcloud-cvm-ops", "1.5.0", tccli_version=None))


class CompatibleSkillsTest(unittest.TestCase):
    def test_returns_subset(self) -> None:
        skills = compatible_skills("1.2.0")
        self.assertIn("qcloud-cvm-ops", skills)
        self.assertNotIn("qcloud-finops-ops", skills)

    def test_all_compatible_at_high_version(self) -> None:
        skills = compatible_skills("9.0.0")
        for s in SKILL_COMPAT:
            self.assertIn(s, skills)


class RenderMatrixTest(unittest.TestCase):
    def test_returns_table_string(self) -> None:
        out = render_matrix()
        self.assertIn("| skill |", out)
        self.assertIn("qcloud-cvm-ops", out)
        self.assertIn("qcloud-finops-ops", out)
        # header + at least 4 rows
        lines = [line for line in out.splitlines() if line.startswith("|")]
        self.assertGreaterEqual(len(lines), 6)


if __name__ == "__main__":
    unittest.main()
