#!/usr/bin/env python3
"""Tests for migrate_skill_frontmatter.py — Phase 1 Step 1.2.3.

TDD: written before implementation.

Run: cd scripts && python3 -m unittest migrate_skill_frontmatter_test -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from migrate_skill_frontmatter import diff_text, migrate_file

HARDCODED = {
    "SKILL_TO_PRODUCT": {"qcloud-cvm-ops": "cvm", "qcloud-redis-ops": "redis"},
    "OPERATION_ALIAS": {
        ("qcloud-cvm-ops", "describe"): "describe-instances",
    },
    "SKILL_PARAM_MAPPING": {
        ("qcloud-cvm-ops", "describe-instance"): "InstanceIds.0",
    },
}


def _write(tmp: Path, name: str, body: str) -> Path:
    skill_dir = tmp / f"qcloud-{name}-ops"
    skill_dir.mkdir(parents=True, exist_ok=True)
    p = skill_dir / "SKILL.md"
    p.write_text(body)
    return p


class MigrateSkillFrontmatterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="migrate_frontmatter_"))

    def test_dry_run_does_not_modify_file(self):
        body = (
            "---\n"
            "name: qcloud-cvm-ops\n"
            "description: Test\n"
            "metadata:\n"
            "  cli_applicability: dual-path\n"
            "---\n"
            "# Body\n"
        )
        p = _write(self.tmp, "cvm", body)
        migrate_file(p, dry_run=True, hardcoded=HARDCODED)
        self.assertEqual(p.read_text(), body)

    def test_apply_adds_product_name_under_metadata(self):
        body = (
            "---\n"
            "name: qcloud-cvm-ops\n"
            "description: Test\n"
            "metadata:\n"
            "  cli_applicability: dual-path\n"
            "---\n"
            "# Body\n"
        )
        p = _write(self.tmp, "cvm", body)
        original, new = migrate_file(p, dry_run=False, hardcoded=HARDCODED)
        self.assertNotEqual(original, new, "expected a change")
        new_text = p.read_text()
        self.assertIn("product_name: cvm", new_text)
        # product_name should be under metadata.* (real structure): indented
        self.assertIn("\n  product_name: cvm\n", new_text,
                      "product_name must be indented under metadata:")
        # Ensure NOT at top-level (un-indented)
        self.assertNotIn("\nproduct_name: cvm\n", new_text,
                         "product_name must not appear at top level")
        # Exactly one occurrence total
        self.assertEqual(new_text.count("product_name: cvm"), 1)

    def test_apply_adds_operation_aliases_and_param_mapping(self):
        body = (
            "---\n"
            "name: qcloud-cvm-ops\n"
            "description: Test\n"
            "metadata:\n"
            "  cli_applicability: dual-path\n"
            "---\n"
            "# Body\n"
        )
        p = _write(self.tmp, "cvm", body)
        migrate_file(p, dry_run=False, hardcoded=HARDCODED)
        text = p.read_text()
        self.assertIn("operation_aliases:", text)
        self.assertIn("describe: describe-instances", text)
        self.assertIn("param_mapping:", text)
        self.assertIn("describe-instance: InstanceIds.0", text)

    def test_apply_idempotent(self):
        body = (
            "---\n"
            "name: qcloud-cvm-ops\n"
            "description: Test\n"
            "metadata:\n"
            "  cli_applicability: dual-path\n"
            "---\n"
            "# Body\n"
        )
        p = _write(self.tmp, "cvm", body)
        migrate_file(p, dry_run=False, hardcoded=HARDCODED)
        first = p.read_text()
        migrate_file(p, dry_run=False, hardcoded=HARDCODED)
        second = p.read_text()
        self.assertEqual(first, second,
                         "second migration should be a no-op")

    def test_apply_skips_unknown_skill(self):
        body = (
            "---\n"
            "name: qcloud-agsx-ops\n"
            "description: Test\n"
            "metadata:\n"
            "  cli_applicability: sdk-only\n"
            "---\n"
            "# Body\n"
        )
        p = _write(self.tmp, "agsx", body)
        original, new = migrate_file(p, dry_run=False, hardcoded=HARDCODED)
        # agsx not in HARDCODED → no change
        self.assertEqual(original, new)

    def test_apply_creates_metadata_block_if_missing(self):
        body = (
            "---\n"
            "name: qcloud-cvm-ops\n"
            "description: Test\n"
            "---\n"
            "# Body\n"
        )
        p = _write(self.tmp, "cvm", body)
        migrate_file(p, dry_run=False, hardcoded=HARDCODED)
        text = p.read_text()
        self.assertIn("product_name: cvm", text)
        self.assertIn("metadata:", text)

    def test_diff_text_returns_unified_diff(self):
        a = "---\nname: x\n---\n"
        b = "---\nname: x\nmetadata:\n  product_name: y\n---\n"
        diff = diff_text(a, b)
        self.assertIn("+", diff)
        self.assertIn("product_name", diff)

    def test_apply_preserves_body_after_frontmatter(self):
        body = (
            "---\n"
            "name: qcloud-cvm-ops\n"
            "description: Test\n"
            "metadata:\n"
            "  cli_applicability: dual-path\n"
            "---\n"
            "# Important Body Section\n\nDo not lose this.\n"
        )
        p = _write(self.tmp, "cvm", body)
        migrate_file(p, dry_run=False, hardcoded=HARDCODED)
        text = p.read_text()
        self.assertIn("# Important Body Section", text)
        self.assertIn("Do not lose this.", text)


if __name__ == "__main__":
    unittest.main()