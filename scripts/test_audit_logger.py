#!/usr/bin/env python3
"""Tests for audit_logger — Phase 3.4 immutable audit log."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from audit_logger import AuditLogger, AutonomousDecision


def _make_decision(
    decision_id: str = "abc123",
    autonomy_level: int = 1,
    operation: str = "DescribeInstances",
    risk_level: str = "LOW",
    action_taken: str = "auto_confirm",
    result: str = "success",
    minutes_from_now: int = 10,
    skill: str | None = "test-skill",
) -> AutonomousDecision:
    now = datetime.now(UTC)
    return AutonomousDecision(
        decision_id=decision_id,
        timestamp=now.isoformat(),
        autonomy_level=autonomy_level,
        operation=operation,
        resource_ids=["i-12345678"],
        risk_level=risk_level,
        action_taken=action_taken,
        rationale="test",
        result=result,
        revocable_until=(now + timedelta(minutes=minutes_from_now)).isoformat(),
        skill=skill,
    )


class AuditLoggerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._logger = AuditLogger(runtime_root=Path(self._tmpdir))

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # log_decision
    # ------------------------------------------------------------------

    def test_log_decision_writes_jsonl(self) -> None:
        decision = _make_decision(decision_id="aaa111")
        self._logger.log_decision(decision)

        log_path = self._logger._log_path
        self.assertTrue(log_path.exists(), f"log file not created at {log_path}")

        with open(log_path, encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
        self.assertEqual(len(lines), 1)

        parsed = json.loads(lines[0])
        self.assertEqual(parsed["decision_id"], "aaa111")
        self.assertEqual(parsed["result"], "success")

    def test_log_decision_append_mode(self) -> None:
        self._logger.log_decision(_make_decision("first"))
        self._logger.log_decision(_make_decision("second"))

        with open(self._logger._log_path, encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
        self.assertEqual(len(lines), 2)

        ids = {json.loads(ln)["decision_id"] for ln in lines}
        self.assertEqual(ids, {"first", "second"})

    def test_log_decision_creates_parent_dirs(self) -> None:
        decision = _make_decision()
        self._logger.log_decision(decision)
        self.assertTrue(self._logger._log_path.exists())

    # ------------------------------------------------------------------
    # generate_report
    # ------------------------------------------------------------------

    def test_generate_report_empty(self) -> None:
        report = self._logger.generate_report(since="2020-01-01T00:00:00Z")
        self.assertIn("No autonomous decisions found", report)

    def test_generate_report_includes_all_decisions(self) -> None:
        self._logger.log_decision(_make_decision(decision_id="id1", operation="Op1"))
        self._logger.log_decision(_make_decision(decision_id="id2", operation="Op2"))

        since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        report = self._logger.generate_report(since=since)
        self.assertIn("Op1", report)
        self.assertIn("Op2", report)
        self.assertIn("**Total decisions:** 2", report)

    def test_generate_report_filters_by_level(self) -> None:
        self._logger.log_decision(
            _make_decision(decision_id="id0", autonomy_level=0, operation="Lvl0Op")
        )
        self._logger.log_decision(
            _make_decision(decision_id="id2", autonomy_level=2, operation="Lvl2Op")
        )

        since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        report_l2 = self._logger.generate_report(since=since, level=2)
        self.assertIn("id2", report_l2)
        self.assertIn("Lvl2Op", report_l2)
        self.assertNotIn("Lvl0Op", report_l2)

    def test_generate_report_groups_by_action(self) -> None:
        self._logger.log_decision(
            _make_decision("a1", action_taken="auto_confirm")
        )
        self._logger.log_decision(
            _make_decision("a2", action_taken="auto_confirm")
        )
        self._logger.log_decision(
            _make_decision("h1", action_taken="human_token")
        )

        since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        report = self._logger.generate_report(since=since)
        self.assertIn("auto_confirm", report)
        self.assertIn("human_token", report)
        self.assertIn("2", report)
        self.assertIn("1", report)

    def test_generate_report_includes_by_skill_section(self) -> None:
        self._logger.log_decision(
            _make_decision("s1", skill="cvm-ops", operation="CVmOp")
        )
        self._logger.log_decision(
            _make_decision("s2", skill="cvm-ops", operation="CVmOp2")
        )
        self._logger.log_decision(
            _make_decision("s3", skill="cdb-ops", operation="CDbOp")
        )

        since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        report = self._logger.generate_report(since=since)
        self.assertIn("cvm-ops", report)
        self.assertIn("cdb-ops", report)

    def test_generate_report_filters_old_decisions(self) -> None:
        old_ts = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        log_path = self._logger._log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        old_data = {
            "decision_id": "old-decision",
            "timestamp": old_ts,
            "autonomy_level": 1,
            "operation": "OldOp",
            "resource_ids": [],
            "risk_level": "LOW",
            "action_taken": "auto_confirm",
            "rationale": "test",
            "result": "success",
            "revocable_until": (
                datetime.fromisoformat(old_ts) + timedelta(minutes=10)
            ).isoformat(),
            "skill": "test",
        }
        log_path.write_text(json.dumps(old_data) + "\n", encoding="utf-8")
        # Add a new decision
        self._logger.log_decision(
            _make_decision("new-decision", operation="NewOp")
        )
        since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        report = self._logger.generate_report(since=since)
        self.assertIn("NewOp", report)
        self.assertNotIn("OldOp", report)

    # ------------------------------------------------------------------
    # revoke
    # ------------------------------------------------------------------

    def test_revoke_within_window_succeeds(self) -> None:
        decision = _make_decision("to-revoke", result="success")
        self._logger.log_decision(decision)

        success = self._logger.revoke("to-revoke")
        self.assertTrue(success)

        with open(self._logger._log_path, encoding="utf-8") as fh:
            records = [json.loads(ln) for ln in fh if ln.strip()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["result"], "rolled_back")

    def test_revoke_outside_window_fails(self) -> None:
        # Create a decision record that is already outside the 5-minute window
        old_ts = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        record = {
            "decision_id": "expired-decision",
            "timestamp": old_ts,
            "autonomy_level": 1,
            "operation": "ExpiredOp",
            "resource_ids": [],
            "risk_level": "LOW",
            "action_taken": "auto_confirm",
            "rationale": "test",
            "result": "success",
            "revocable_until": (
                datetime.fromisoformat(old_ts) + timedelta(minutes=5)
            ).isoformat(),
            "skill": "test",
        }
        self._logger._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._logger._log_path.write_text(
            json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        success = self._logger.revoke("expired-decision")
        self.assertFalse(success)
    def test_revoke_nonexistent_id_returns_false(self) -> None:
        success = self._logger.revoke("does-not-exist")
        self.assertFalse(success)

    def test_revoke_already_revoked_returns_false(self) -> None:
        decision = _make_decision("already-revoked", result="rolled_back")
        self._logger.log_decision(decision)

        success = self._logger.revoke("already-revoked")
        self.assertFalse(success)

    def test_revoke_preserves_other_records(self) -> None:
        self._logger.log_decision(_make_decision("keep-me"))
        self._logger.log_decision(_make_decision("revoke-me"))
        self._logger.log_decision(_make_decision("keep-me-too"))

        self._logger.revoke("revoke-me")

        with open(self._logger._log_path, encoding="utf-8") as fh:
            records = [json.loads(ln) for ln in fh if ln.strip()]

        # All 3 records still present (revoke marks result, doesn't delete)
        ids = {r["decision_id"] for r in records}
        self.assertEqual(ids, {"keep-me", "revoke-me", "keep-me-too"})
        # Verify results: 2 success + 1 rolled_back
        results = {r["result"] for r in records}
        self.assertEqual(results, {"success", "rolled_back"})
        # Verify specific record states
        by_id = {r["decision_id"]: r for r in records}
        self.assertEqual(by_id["revoke-me"]["result"], "rolled_back")
        self.assertEqual(by_id["keep-me"]["result"], "success")
        self.assertEqual(by_id["keep-me-too"]["result"], "success")


class AutonomousDecisionTests(unittest.TestCase):
    def test_to_dict_contains_all_fields(self) -> None:
        d = AutonomousDecision(
            decision_id="abc123",
            timestamp="2025-01-01T00:00:00+00:00",
            autonomy_level=2,
            operation="DeleteVpc",
            resource_ids=["vpc-123"],
            risk_level="CRITICAL",
            action_taken="human_approval",
            rationale="very risky",
            result="success",
            revocable_until="2025-01-01T00:05:00+00:00",
            skill="vpc-ops",
        )
        as_dict = d.to_dict()
        self.assertEqual(as_dict["decision_id"], "abc123")
        self.assertEqual(as_dict["action_taken"], "human_approval")
        self.assertEqual(as_dict["resource_ids"], ["vpc-123"])

    def test_from_dict_roundtrip(self) -> None:
        original = AutonomousDecision(
            decision_id="xyz789",
            timestamp="2025-06-15T12:00:00+00:00",
            autonomy_level=3,
            operation="TerminateInstances",
            resource_ids=["i-1", "i-2"],
            risk_level="HIGH",
            action_taken="critic_review",
            rationale="moderate risk",
            result="success",
            revocable_until="2025-06-15T12:05:00+00:00",
            skill=None,
        )
        roundtripped = AutonomousDecision.from_dict(original.to_dict())
        self.assertEqual(roundtripped.decision_id, original.decision_id)
        self.assertEqual(roundtripped.operation, original.operation)
        self.assertEqual(roundtripped.resource_ids, original.resource_ids)
        self.assertEqual(roundtripped.skill, original.skill)
        self.assertEqual(roundtripped.action_taken, original.action_taken)


if __name__ == "__main__":
    unittest.main()
