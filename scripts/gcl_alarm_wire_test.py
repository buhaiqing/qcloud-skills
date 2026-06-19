#!/usr/bin/env python3
"""Unit tests for scripts/gcl_alarm_wire.py."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import gcl_alarm_wire as gaw  # noqa: E402


def write_summary(root: Path, payload: dict) -> Path:
    audit = root / "audit-results"
    audit.mkdir(parents=True, exist_ok=True)
    path = audit / "gcl-quality-summary-test.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def healthy_summary() -> dict:
    return {
        "pass_rate": 0.95,
        "totals": {"PASS": 19, "MAX_ITER": 1, "SAFETY_FAIL": 0, "total_runs": 20},
    }


def quiet_call(func, args: argparse.Namespace) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(args)


class PlanTests(unittest.TestCase):
    def test_no_summary_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(root=Path(tmp), summary=None, config=Path(tmp) / "missing.yaml")
            self.assertEqual(quiet_call(gaw.cmd_plan, args), 2)

    def test_plan_does_not_call_subprocess_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = write_summary(root, healthy_summary())
            args = argparse.Namespace(root=root, summary=summary, config=root / "missing.yaml")
            with patch.object(gaw.subprocess, "run") as run:
                self.assertEqual(quiet_call(gaw.cmd_plan, args), 0)
                run.assert_not_called()

    def test_slo_breach_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = write_summary(root, {
                "pass_rate": 0.60,
                "totals": {"PASS": 6, "MAX_ITER": 0, "SAFETY_FAIL": 1, "total_runs": 10},
            })
            args = argparse.Namespace(root=root, summary=summary, config=root / "missing.yaml")
            self.assertEqual(quiet_call(gaw.cmd_plan, args), 1)

    def test_healthy_plan_returns_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = write_summary(root, healthy_summary())
            args = argparse.Namespace(root=root, summary=summary, config=root / "missing.yaml")
            self.assertEqual(quiet_call(gaw.cmd_plan, args), 0)


class ApplyTests(unittest.TestCase):
    def test_apply_dry_run_does_not_call_subprocess_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = write_summary(root, healthy_summary())
            args = argparse.Namespace(root=root, summary=summary, config=root / "missing.yaml", dry_run=True)
            with patch.object(gaw.subprocess, "run") as run:
                self.assertEqual(quiet_call(gaw.cmd_apply, args), 0)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
