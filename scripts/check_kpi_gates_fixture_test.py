#!/usr/bin/env python3
"""H-50: every KPI#1/#2 safety rule must be individually visible to the gate.

Defect being closed: `scripts/fixtures/evidence/evidence-safety-violating.jsonl`
violates all three safety rules at once (one `leak_checked=false` record plus a
destructive record missing both token and plan_hash). The CI hook that grades it
therefore only proves "at least one rule is alive": delete any single rule from
`validate_evidence_schema.validate_record` and the other two keep turning the
step red, so the dead rule is invisible — the exact failure mode L25 describes
(a contract whose seam is never exercised drifts undetected).

Fix: one committed fixture per rule, each otherwise legal (11 fresh records,
exactly one violating record). This test grades each fixture *alone* — staged
into the repo's `audit-results/` under a per-run unique name and selected with
`GATE_EVIDENCE_GLOB`, which is the mechanism CI uses — so a rule that stops
firing turns its own fixture green and fails this test by name.

L6 both ways: the clean fixture must still pass (silent side), and each
single-violation fixture must turn the gate red with exactly one rule named
(fire side).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_kpi_gates  # noqa: E402

FIXTURES = ROOT / "scripts" / "fixtures" / "evidence"
FLOOR = json.loads(
    (ROOT / "assets" / "shared" / "thresholds.json").read_text(encoding="utf-8")
)["evidence_min_records"]

# The three rule signatures as validate_evidence_schema prints them. Each
# single-violation fixture must name exactly one of these and neither of the
# others; matching on the rule text is what makes "only one rule fired" a
# verdict rather than an assumption.
LEAK_RULE = "KPI#1 requires leak_checked=true"
TOKEN_RULE = "KPI#2 destructive op requires a non-null confirmation token"
PLAN_HASH_RULE = "KPI#2 destructive op requires a non-null plan_hash"
ALL_RULES = (LEAK_RULE, TOKEN_RULE, PLAN_HASH_RULE)

# fixture -> the one rule it is allowed to trip.
CASES = {
    "evidence-leak-unchecked-only.jsonl": LEAK_RULE,
    "evidence-destructive-no-token-only.jsonl": TOKEN_RULE,
    "evidence-destructive-no-plan-hash-only.jsonl": PLAN_HASH_RULE,
}
CLEAN_FIXTURE = "evidence-safety-clean.jsonl"
# The all-at-once fixture this change exists to stop relying on.
LEGACY_VIOLATING_FIXTURE = "evidence-safety-violating.jsonl"


def _violations(record: dict) -> list[str]:
    """Rule names a single record trips, in the validator's own terms."""
    safety = record.get("safety") or {}
    hit = []
    if safety.get("leak_checked") is not True:
        hit.append("leak_checked")
    if safety.get("destructive") is True and not safety.get("token"):
        hit.append("token")
    if safety.get("destructive") is True and not safety.get("plan_hash"):
        hit.append("plan_hash")
    return hit


@contextlib.contextmanager
def _quiet():
    """L20: the gate prints a Markdown table; tests must not leak it."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


@contextlib.contextmanager
def _other_kpis_stubbed():
    """Judge main() on the evidence arm alone: KPI#3/#7/#8 shell out to the real
    repo, and a failure there would fake the exit-1 this test is asserting."""
    with mock.patch.object(check_kpi_gates, "kpi3_golden_coverage",
                           return_value=("pass", "stub", "")), \
            mock.patch.object(check_kpi_gates, "kpi7_router_confusion",
                              return_value=("pass", "stub", "")), \
            mock.patch.object(check_kpi_gates, "kpi8_spec_drift",
                              return_value=("skip", "stub", "stubbed")):
        yield


class PerRuleEvidenceFixtureTest(unittest.TestCase):
    """One fixture per rule, each graded on its own.

    Staging mirrors what CI does: the committed fixture is copied into the
    repo's `audit-results/` under a unique name, `GATE_EVIDENCE_GLOB` names that
    one file (so no other stream in the directory can supply the verdict), and
    both the staged copy and any `kpi-gate-report.json` overwritten by main() are
    restored/removed on the way out.
    """

    @contextlib.contextmanager
    def _graded(self, fixture_name: str):
        audit: Path = check_kpi_gates.AUDIT
        audit.mkdir(parents=True, exist_ok=True)
        staged = audit / f"evidence-h50-{Path(fixture_name).stem}-{uuid.uuid4().hex[:8]}.jsonl"
        staged.write_text((FIXTURES / fixture_name).read_text(encoding="utf-8"),
                          encoding="utf-8")
        report = audit / "kpi-gate-report.json"
        saved = report.read_bytes() if report.exists() else None
        try:
            with mock.patch.dict(os.environ, {"GATE_EVIDENCE_GLOB": staged.name}):
                yield staged
        finally:
            staged.unlink(missing_ok=True)
            if saved is None:
                report.unlink(missing_ok=True)
            else:
                report.write_bytes(saved)
            self.assertFalse(staged.exists(), f"staging leaked: {staged}")

    def test_each_fixture_trips_exactly_its_own_rule(self) -> None:
        """The core assertion: fire side, one rule named, other two silent."""
        for name, expected in CASES.items():
            with self.subTest(fixture=name), self._graded(name):
                status, detail, _ = check_kpi_gates.kpi1_2_safety()
            self.assertEqual(status, "fail", f"{name} did not turn the gate red: {detail}")
            self.assertIn(expected, detail, f"{name} did not report its own rule")
            for other in ALL_RULES:
                if other != expected:
                    self.assertNotIn(other, detail,
                                     f"{name} also tripped {other!r}: rule isolation lost")
            # one violating record, not a stream full of them: a fixture that
            # trips two rules on different records would hide a dead rule again.
            self.assertEqual(detail.count("record["), 1,
                             f"{name} reports {detail.count('record[')} violations: {detail}")

    def test_each_single_violation_fixture_fails_main(self) -> None:
        """What CI reads: the aggregate gate's exit code."""
        for name in CASES:
            with self.subTest(fixture=name), self._graded(name), \
                    _other_kpis_stubbed(), _quiet():
                self.assertEqual(check_kpi_gates.main(), 1)

    def test_clean_fixture_stays_green(self) -> None:
        """L6 silent side: with every rule exercised, none of them may fire here."""
        with self._graded(CLEAN_FIXTURE):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "pass", detail)
        self.assertIn("record(s) valid", detail)
        for rule in ALL_RULES:
            self.assertNotIn(rule, detail)
        with self._graded(CLEAN_FIXTURE), _other_kpis_stubbed(), _quiet():
            self.assertEqual(check_kpi_gates.main(), 0)

    def test_fixtures_carry_the_floor_and_a_single_violation(self) -> None:
        """The fixtures' own data contract, independent of the gate: >= the fresh
        record floor, and exactly one record per fixture that violates anything.
        If an edit makes a fixture trip a second rule, per-rule visibility is
        gone again even though every assertion above still passes."""
        for name in CASES:
            records = [
                json.loads(line)
                for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertGreaterEqual(len(records), FLOOR,
                                    f"{name} has {len(records)} record(s), floor is {FLOOR}")
            offenders = [(i, _violations(r)) for i, r in enumerate(records) if _violations(r)]
            self.assertEqual(len(offenders), 1, f"{name} has {offenders} violations")
            self.assertEqual(len(offenders[0][1]), 1,
                             f"{name} record {offenders[0][0]} violates {offenders[0][1]}")

    def test_fixtures_cover_each_rule_once(self) -> None:
        """A new rule added to the validator without a fixture reproducing it
        alone leaves this test asserting less than it claims. The rule set is
        read off the legacy all-at-once fixture, so the pairing is checked
        against the validator's behaviour rather than a hand-kept list."""
        legacy = [
            json.loads(line)
            for line in (FIXTURES / LEGACY_VIOLATING_FIXTURE).read_text(
                encoding="utf-8").splitlines()
            if line.strip()
        ]
        legacy_rules = {rule for r in legacy for rule in _violations(r)}
        covered = {_violations(r)[0]
                   for name in CASES
                   for r in [json.loads(line) for line in
                             (FIXTURES / name).read_text(encoding="utf-8").splitlines()
                             if line.strip()]
                   if _violations(r)}
        self.assertTrue(
            legacy_rules <= covered,
            f"rules exercised only by {LEGACY_VIOLATING_FIXTURE} lack a single-violation"
            f" fixture: {sorted(legacy_rules - covered)}",
        )


if __name__ == "__main__":
    unittest.main()
