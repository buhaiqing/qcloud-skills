#!/usr/bin/env python3
"""Tests for self_evolution_loop.py — upgrade_signal → gate → PR orchestration."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import self_evolution_loop as sel

SKILL = "qcloud-cvm-ops"
PATTERN = {
    "_key": f"{SKILL}|TerminateInstances|InvalidInstanceIds malformed",
    "error": "InvalidInstanceIds malformed",
    "fix": 'Pass --InstanceIds \'["ins-x"]\' as JSON array',
    "count": 7,
    "category": "cli_parameter",
}


def _fixture_root(tmp: Path) -> Path:
    ref = tmp / SKILL / "references"
    ref.mkdir(parents=True)
    (ref / "troubleshooting.md").write_text("# Troubleshooting\n\nexisting notes\n")
    return tmp


def _loop(tmp: Path, **kw) -> sel.SelfEvolutionLoop:
    defaults: dict = {
        "root": _fixture_root(Path(tmp)),
        "gate_fn": lambda root: (True, "golden gate ok"),
        "max_skills": 5,
    }
    defaults.update(kw)
    return sel.SelfEvolutionLoop(**defaults)


REPORT = {"upgrade_signal": [SKILL]}


class SelfEvolutionLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_pick = sel.pick_root_cause
        sel.pick_root_cause = lambda skill: dict(PATTERN)

    def tearDown(self) -> None:
        sel.pick_root_cause = self._orig_pick

    def test_dry_run_builds_proposal_without_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            loop = _loop(tmp, dry_run=True)
            summary = loop.run(report_override=dict(REPORT))
            outcome = summary["outcomes"][0]
            self.assertEqual(outcome["status"], "dry_run")
            self.assertTrue(summary["ok"])
            # file untouched
            ts = Path(loop.root / SKILL / "references" / "troubleshooting.md")
            self.assertEqual(ts.read_text().count("Self-evolution remediation"), 0)

    def test_pr_path_invokes_workflow_with_valid_proposal(self) -> None:
        captured: list[sel.FixProposal] = []

        def fake_workflow(proposal: sel.FixProposal):
            captured.append(proposal)
            return type("R", (), {"status": "created", "message": "PR opened"})()

        with tempfile.TemporaryDirectory() as tmp:
            loop = _loop(tmp, workflow_fn=fake_workflow)
            summary = loop.run(report_override=dict(REPORT))
            self.assertEqual(summary["outcomes"][0]["status"], "pr_created")
            self.assertEqual(len(captured), 1)
            p = captured[0]
            # L5/L8: populated values asserted, not just key presence
            self.assertIn("InvalidInstanceIds", p.new_content)
            self.assertIn("JSON array", p.new_content)
            self.assertGreater(p.occurrence_count, 0)
            self.assertFalse(p.auto_merge)

    def test_no_pattern_skips(self) -> None:
        sel.pick_root_cause = lambda skill: None
        with tempfile.TemporaryDirectory() as tmp:
            summary = _loop(tmp).run(report_override=dict(REPORT))
            self.assertEqual(summary["outcomes"][0]["status"], "skipped_no_pattern")

    def test_duplicate_remediation_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            loop = _loop(tmp)
            ts = Path(loop.root / SKILL / "references" / "troubleshooting.md")
            ts.write_text(ts.read_text() + "\n### Self-evolution remediation 2099-01-01\n"
                          "\n- **Error**: InvalidInstanceIds malformed\n")
            summary = loop.run(report_override=dict(REPORT))
            self.assertEqual(summary["outcomes"][0]["status"], "skipped_duplicate")

    def test_gate_failure_blocks_workflow(self) -> None:
        called = {"wf": False}

        def fake_workflow(proposal):
            called["wf"] = True
            raise AssertionError("workflow must not run when gate fails")

        with tempfile.TemporaryDirectory() as tmp:
            loop = _loop(
                tmp,
                gate_fn=lambda root: (False, "frontmatter gate failed"),
                workflow_fn=fake_workflow,
            )
            summary = loop.run(report_override=dict(REPORT))
            self.assertEqual(summary["outcomes"][0]["status"], "gate_failed")
            self.assertFalse(summary["ok"])
            self.assertFalse(called["wf"])

    def test_missing_troubleshooting_target_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            loop = sel.SelfEvolutionLoop(
                root=Path(tmp),  # no skill dir at all
                gate_fn=lambda root: (True, "ok"),
            )
            summary = loop.run(report_override=dict(REPORT))
            self.assertEqual(summary["outcomes"][0]["status"], "skipped_no_target")

    def test_empty_signals_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = _loop(tmp).run(report_override={"upgrade_signal": []})
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["outcomes"], [])


if __name__ == "__main__":
    unittest.main()
