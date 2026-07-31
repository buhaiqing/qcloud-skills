#!/usr/bin/env python3
"""Tests for scripts/migrate_error_tables.py — Phase 1 Step 1.3.3.

TDD: written before implementation.

L1: TestCase subclasses (unittest discover finds them).
L5: assert populated values, not just key presence.
L7: integration re-reads live target; tested against a sandbox copy.

Run: cd scripts && python3 -m unittest test_migrate_error_tables -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from error_table_parser import parse_error_table
from migrate_error_tables import (
    _find_legacy_table_ranges,
    _parse_frontmatter,
    _render_standard_table,
    _split_frontmatter_body,
    migrate_skill,
)

# ============================================================================
# Fixtures
# ============================================================================

LEGACY_3COL = """\
| Error Code | Max Retries | Recovery |
|------------|-------------|----------|
| `InvalidVpc.NotFound` | 0 | HALT. Delegate to qcloud-vpc-ops |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT if persists |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
"""

LEGACY_5COL = """\
| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|---------------|-------------|---------|--------------|-------------|
| `InternalError` | 3 | 2s/4s/8s | Retry; escalate with RequestId | `[ERROR]` |
| `InvalidParameter` | 0 | -- | Fix period/region parameter | `[ERROR]` |
"""

LEGACY_2COL = """\
| Error pattern | Recovery |
|--------------|----------|
| `ResourceNotFound` | HALT; no resources found |
"""

STANDARD_6COL = """\
| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |
|------------|--------|-------------|---------|-------------|---------------|
| `InvalidVpc.NotFound` | HALT | 0 | — | qcloud-vpc-ops | Verify VPC exists |
"""

STUB_TABLE = """\
| Error Code | Max Retries | Recovery |
|------------|-------------|----------|
See `references/error-reference.md` for full taxonomy. Common: ...
"""


# ============================================================================
# Tests
# ============================================================================

class RenderStandardTableTests(unittest.TestCase):
    """Render an ErrorRule list back into 6-col markdown."""

    def test_render_with_explicit_backoff(self):
        # 3-col legacy with backoff list
        rules = parse_error_table(LEGACY_3COL)
        text = _render_standard_table(rules)
        self.assertIn("| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |", text)
        self.assertIn("| `InvalidVpc.NotFound` | HALT | 0 | — | qcloud-vpc-ops | HALT. Delegate to qcloud-vpc-ops |", text)
        self.assertIn("| `InternalError` | RETRY | 3 | 2s,4s,8s | — | Retry; HALT if persists |", text)
        self.assertIn("| `RequestLimitExceeded` | RETRY | 3 | exponential | — | Back off and retry |", text)

    def test_render_5col_legacy(self):
        rules = parse_error_table(LEGACY_5COL)
        # 5-col shape: code | retries | backoff | action_text | hint
        text = _render_standard_table(rules)
        self.assertIn("| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |", text)
        codes = {r.code for r in rules}
        self.assertEqual(codes, {"InternalError", "InvalidParameter"})
        # Max retries comes from col 1, not the action text
        rule_int = next(r for r in rules if r.code == "InternalError")
        rule_param = next(r for r in rules if r.code == "InvalidParameter")
        self.assertEqual(rule_int.max_retries, 3)
        self.assertEqual(rule_param.max_retries, 0)

    def test_render_skips_when_no_rules(self):
        text = _render_standard_table([])
        self.assertIn("| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |", text)
        non_empty = [ln for ln in text.splitlines() if ln.strip()]
        self.assertEqual(len(non_empty), 2,
                         "empty rules list should give header+separator only")

    def test_backoff_renders_empty_dash_when_no_seconds_or_strategy(self):
        rules = parse_error_table(LEGACY_3COL)
        rule = next(r for r in rules if r.code == "InvalidVpc.NotFound")
        rendered = _render_standard_table([rule])
        self.assertIn("| — |", rendered,
                      "empty backoff should render as em-dash column")


class FindLegacyTableRangesTests(unittest.TestCase):
    """Locate legacy tables in raw markdown text (line ranges)."""

    def test_finds_single_legacy_3col(self):
        body = "Some prose\n" + LEGACY_3COL + "\nMore prose\n"
        ranges = _find_legacy_table_ranges(body)
        self.assertEqual(len(ranges), 1, f"expected 1 legacy table, got {len(ranges)}")
        _start, _end, header, _rows = ranges[0]
        self.assertEqual(header, ["Error Code", "Max Retries", "Recovery"])

    def test_skips_already_standard_6col(self):
        body = STANDARD_6COL + "\n"
        ranges = _find_legacy_table_ranges(body)
        self.assertEqual(ranges, [], "standard 6-col tables should be skipped")

    def test_finds_multiple_legacy_tables(self):
        body = "Intro\n\n" + LEGACY_3COL + "\n\nMiddle\n\n" + LEGACY_2COL + "\n"
        ranges = _find_legacy_table_ranges(body)
        self.assertEqual(len(ranges), 2)

    def test_skips_stub_tables_with_no_data_rows(self):
        # Stub: header + separator + description prose below.
        # Only 2 pipe-rows → not a real table.
        body = "Intro\n\n" + STUB_TABLE + "\n"
        ranges = _find_legacy_table_ranges(body)
        self.assertEqual(ranges, [], "stub tables with no data rows must not be migrated")

    def test_skips_non_error_tables(self):
        # Pre-flight check table; first column is something other than error.
        body = (
            "| Check | Action |\n"
            "|---|---|\n"
            "| Region | Valid |\n"
            "| Zone | Valid |\n"
        )
        ranges = _find_legacy_table_ranges(body)
        self.assertEqual(ranges, [], "non-error tables must not be flagged")


class FrontmatterSplitTests(unittest.TestCase):
    """Frontmatter is preserved exactly when split from body."""

    def test_split_with_frontmatter(self):
        text = (
            "---\n"
            "name: qcloud-cvm-ops\n"
            "description: Test\n"
            "---\n"
            "\n# Body\n"
            + LEGACY_3COL
        )
        fm, body = _split_frontmatter_body(text)
        self.assertIsNotNone(fm)
        self.assertIn("name: qcloud-cvm-ops", fm.text)
        self.assertTrue(fm.text.rstrip().endswith("---"),
                        f"frontmatter must end with closing dashes; got {fm.text!r}")
        self.assertIn("# Body", body)
        self.assertIn(LEGACY_3COL.strip(), body)

    def test_split_no_frontmatter(self):
        text = "# Just a body\n" + LEGACY_3COL
        fm, body = _split_frontmatter_body(text)
        self.assertIsNone(fm)
        self.assertEqual(body, text)

    def test_parse_frontmatter_keys(self):
        text = (
            "---\n"
            "name: qcloud-cvm-ops\n"
            "description: Test\n"
            "metadata:\n"
            "  version: '1.0.0'\n"
            "---\n"
        )
        fm = _parse_frontmatter(text)
        self.assertIsNotNone(fm)
        self.assertEqual(fm.name, "qcloud-cvm-ops")
        self.assertEqual(fm.version, "1.0.0")


class MigrateSkillTests(unittest.TestCase):
    """Whole-file migration: dry-run vs apply, idempotency, body preservation."""

    def _write_skill(self, tmp: Path, body: str, *, with_fm: bool = True) -> Path:
        skill_dir = tmp / "qcloud-test-ops"
        skill_dir.mkdir(parents=True, exist_ok=True)
        prefix = (
            "---\n"
            "name: qcloud-test-ops\n"
            "description: Test skill\n"
            "metadata:\n"
            "  cli_applicability: dual-path\n"
            "  version: '1.0.0'\n"
            "---\n"
            "\n# Body\n\n" if with_fm else "# Body\n\n"
        )
        p = skill_dir / "SKILL.md"
        p.write_text(prefix + body)
        return p

    def test_dry_run_does_not_modify_file(self):
        tmp = Path(tempfile.mkdtemp(prefix="mig_dry_"))
        body_text = "# Body\n\n" + LEGACY_3COL + "\nMore prose\n"
        p = self._write_skill(tmp, body_text)
        original = p.read_text()
        before_text, after_text = migrate_skill(p, dry_run=True)
        self.assertNotEqual(before_text, after_text, "dry-run should report a diff")
        self.assertEqual(p.read_text(), original, "dry-run must not modify file")

    def test_apply_writes_standard_format(self):
        tmp = Path(tempfile.mkdtemp(prefix="mig_apply_"))
        body_text = "# Body\n\n" + LEGACY_3COL + "\n"
        p = self._write_skill(tmp, body_text)
        _before_text, after_text = migrate_skill(p, dry_run=False)
        self.assertIn("| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |",
                      after_text)
        self.assertIn("| `InternalError` | RETRY | 3 | 2s,4s,8s | — | Retry; HALT if persists |",
                      after_text)
        # File actually written
        self.assertEqual(p.read_text(), after_text)

    def test_idempotent(self):
        tmp = Path(tempfile.mkdtemp(prefix="mig_idem_"))
        body_text = "# Body\n\n" + LEGACY_3COL + "\n"
        p = self._write_skill(tmp, body_text)
        _, first_pass = migrate_skill(p, dry_run=False)
        p.write_text(first_pass)
        _, second_pass = migrate_skill(p, dry_run=False)
        self.assertEqual(first_pass, second_pass,
                         "second apply must be a no-op (idempotency)")

    def test_preserves_body_text_around_tables(self):
        tmp = Path(tempfile.mkdtemp(prefix="mig_body_"))
        body_text = (
            "# Heading\n\n"
            "Prose paragraph above.\n\n"
            + LEGACY_3COL +
            "\nTrailing prose.\n\n## Subheading\n\n- bullet\n- item\n"
        )
        p = self._write_skill(tmp, body_text)
        _, after = migrate_skill(p, dry_run=False)
        # Surrounding prose untouched
        self.assertIn("# Heading", after)
        self.assertIn("Prose paragraph above.", after)
        self.assertIn("Trailing prose.", after)
        self.assertIn("## Subheading", after)
        self.assertIn("- bullet\n- item", after)
        # Frontmatter preserved
        self.assertIn("cli_applicability: dual-path", after)
        self.assertIn("name: qcloud-test-ops", after)

    def test_preserves_code_fences(self):
        tmp = Path(tempfile.mkdtemp(prefix="mig_fence_"))
        body_text = (
            "# Body\n\n"
            "```bash\n"
            "tccli cvm DescribeInstances --InstanceIds '[\"i-xxx\"]'\n"
            "```\n\n"
            + LEGACY_3COL +
            "\n```python\n"
            "print('hello')\n"
            "```\n"
        )
        p = self._write_skill(tmp, body_text)
        _, after = migrate_skill(p, dry_run=False)
        self.assertIn("tccli cvm DescribeInstances --InstanceIds '[\"i-xxx\"]'", after)
        self.assertIn("print('hello')", after)

    def test_preserves_unsupported_tables_intact(self):
        tmp = Path(tempfile.mkdtemp(prefix="mig_untouched_"))
        # A Pre-flight check table that LOOKS like a table but isn't an error table.
        pref_table = (
            "| Check | Action |\n"
            "|---|---|\n"
            "| Region | Valid |\n"
        )
        body_text = "# Body\n\n" + pref_table + "\n" + LEGACY_3COL
        p = self._write_skill(tmp, body_text)
        _, after = migrate_skill(p, dry_run=False)
        # Pre-flight table is preserved verbatim
        self.assertIn("| Check | Action |", after)
        self.assertIn("| Region | Valid |", after)
        # Error table is migrated
        self.assertIn("| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |",
                      after)

    def test_no_changes_to_already_standard_file(self):
        tmp = Path(tempfile.mkdtemp(prefix="mig_std_"))
        body_text = "# Body\n\n" + STANDARD_6COL + "\n"
        p = self._write_skill(tmp, body_text)
        _before_text, after_text = migrate_skill(p, dry_run=False)
        self.assertEqual(_before_text, after_text,
                         "files with only 6-col tables must report no change")

    def test_legacy_table_with_preceding_section_header_preserves_header(self):
        tmp = Path(tempfile.mkdtemp(prefix="mig_hdr_"))
        body_text = (
            "## Error Code Reference\n\n"
            + LEGACY_3COL +
            "\n\nSee `references/foo.md` for more.\n"
        )
        p = self._write_skill(tmp, body_text)
        _, after = migrate_skill(p, dry_run=False)
        self.assertIn("## Error Code Reference", after)
        self.assertIn("See `references/foo.md` for more.", after)


class RealWorldMigrationTests(unittest.TestCase):
    """End-to-end against a real SKILL.md (sandbox copy, not source)."""

    def test_migrate_real_skill_produces_standard_format(self):
        # Find a real SKILL.md with legacy tables in this repo.
        repo_root = Path(__file__).resolve().parents[1]
        cvm = repo_root / "qcloud-cvm-ops" / "SKILL.md"
        if not cvm.exists():
            self.skipTest("repo qcloud-cvm-ops/SKILL.md missing")
        with tempfile.TemporaryDirectory(prefix="real_mig_") as td:
            tmp_skill = Path(td) / "qcloud-cvm-ops" / "SKILL.md"
            tmp_skill.parent.mkdir(parents=True)
            original_text = cvm.read_text(encoding="utf-8")
            tmp_skill.write_text(original_text, encoding="utf-8")
            _, migrated = migrate_skill(tmp_skill, dry_run=False)
            # Re-parse migrated: it should produce SAME rules as original.
            rules_before = parse_error_table(original_text)
            rules_after = parse_error_table(migrated)
            self.assertGreater(len(rules_before), 0)
            # Same count of rows (the parser handles both formats).
            self.assertEqual(len(rules_before), len(rules_after),
                             "migration must preserve row count")
            # Same set of error codes.
            self.assertEqual(
                {r.code for r in rules_before},
                {r.code for r in rules_after},
            )
            # Same actions.
            actions_before = {r.code: r.action for r in rules_before}
            actions_after = {r.code: r.action for r in rules_after}
            self.assertEqual(actions_before, actions_after)
            # Same backoff_seconds.
            bk_before = {r.code: r.backoff_seconds for r in rules_before}
            bk_after = {r.code: r.backoff_seconds for r in rules_after}
            self.assertEqual(bk_before, bk_after)
            # Migrated must contain the new header.
            self.assertIn("| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |",
                          migrated)


if __name__ == "__main__":
    unittest.main()
