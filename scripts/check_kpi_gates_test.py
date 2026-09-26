#!/usr/bin/env python3
"""Unit tests for the aggregate KPI gate (check_kpi_gates).

L5: every assertion checks a populated value, not key presence.
L6: each gate proves BOTH that it fires and that it stays silent — the
threshold cases run the same fixture with different thresholds in
assets/shared/thresholds.json, so a hardcoded number cannot pass them.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_kpi_gates

FLOOR = json.loads(
    (ROOT / "assets" / "shared" / "thresholds.json").read_text(encoding="utf-8")
)["evidence_min_records"]

# The KPI#1/#2 CI hook grades these committed fixtures (see
# scripts/fixtures/evidence/ and the "KPI gates" step in validate-skills.yml).
# Their *fresh* records are dated 2099: a fixture cannot carry a true capture
# time, and a past date would rot into a freshness failure. The deliberately
# 2020-dated records in the clean fixture exercise the ageing path.
FIXTURES = ROOT / "scripts" / "fixtures" / "evidence"
CLEAN_FIXTURE = "evidence-safety-clean.jsonl"
VIOLATING_FIXTURE = "evidence-safety-violating.jsonl"
# Fleet size the router-threshold fixture pins `router_min_registry_skills` to.
FIXTURE_FLEET = 3

# Schema-valid EvidenceRecord with KPI#1 (leak_checked) / KPI#2 clean.
VALID_EVIDENCE = {
    "skill": "qcloud-cvm-ops", "run_id": "r1", "phase": "self-test",
    "intent": "list instances",
    "router_decision": {"top1_skill": "qcloud-cvm-ops", "candidates": ["qcloud-cvm-ops"],
                        "misdelegated": False, "fell_back": False},
    "trace": {}, "golden_ref": "assets/golden/list.json", "fixture_ref": None,
    "safety": {"destructive": False, "token": None, "plan_hash": None, "leak_checked": True},
    # Relative to now, not a frozen date: the gate ages evidence out
    # (evidence_max_age_days), so a hardcoded timestamp would rot into a
    # "cannot prove freshness" failure months from now.
    "provenance": {"source": "sandbox_e2e", "tool": "tccli",
                   "captured_at": datetime.now(UTC).isoformat()},
    "budgets": {"context_tokens": 100, "tool_calls": 2, "wall_clock_ms": 500},
    "cost": {"tokens": 100, "usd": None},
    "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1,
               "spec_compliance": 1},
}


def _captured_days_ago(days: float) -> dict:
    """VALID_EVIDENCE as captured `days` ago (negative = in the future)."""
    stamp = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    return {**VALID_EVIDENCE, "provenance": {**VALID_EVIDENCE["provenance"],
                                             "captured_at": stamp}}


@contextlib.contextmanager
def _quiet():
    """L20: print-capable gate functions must not leak stdout into test output."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


_POSITIVE = {"query": "run cvm instance", "should_trigger": True}
_CLEAN_NEGATIVE = {"query": "please write a poem", "should_trigger": False}
# c-ops HAS an eval file but no implicit keywords, i.e. it is unscoreable by
# construction: averaging it in moves both arms without measuring anything.
_C_QUERIES = [
    {"query": "cvm cluster please", "should_trigger": True},
    {"query": "another unmatched query", "should_trigger": False},
]


def _write_repo(
    root: Path,
    min_top1: float,
    target_top1: float,
    max_misd: float = 0.30,
    *,
    a_negative: dict = _CLEAN_NEGATIVE,
    missing_eval: tuple[str, ...] = (),
    drop: tuple[str, ...] = (),
    min_registry_skills: int = FIXTURE_FLEET,
) -> Path:
    """Fixture: qcloud-a-ops gets its positive query wrong (routes to b),
    qcloud-b-ops gets its own right -> avg top1 = (0.0 + 1.0) / 2 = 0.50,
    avg misdelegation = 0.00 over the 2 scoreable skills (a, b).

    qcloud-c-ops is in the registry with empty `intent_keywords`: it has an
    eval_queries.json, so the *old* aggregation averaged it in as a 0.0/0.0 and
    reported 33.33% — it is the "unmeasured" skill the detail must name.
    `a_negative` swaps in a negative that routes back to a-ops (misdelegation);
    `missing_eval` deletes a skill's eval file to shrink the scoreable set;
    `drop` deletes the skill dir AND its registry entry, leaving
    `router_min_registry_skills` (pinned to the pre-drop fleet, as the real
    threshold is) as the only guard against a shrunken registry.
    """
    fleet = [
        {"name": "qcloud-a-ops", "intent_keywords": ["ZzzNeverUsedKeyword"]},
        {"name": "qcloud-b-ops", "intent_keywords": ["RunCvmInstance"]},
        {"name": "qcloud-c-ops", "intent_keywords": []},
    ]
    (root / "assets" / "shared").mkdir(parents=True)
    (root / "assets" / "shared" / "thresholds.json").write_text(
        json.dumps({"rubric_min_score": 0.5,
                    "safety_fail_threshold": 0,
                    "max_iterations": 5,
                    "gcl_structural_critic_only": True,
                    "reflexion_max_lines": 200,
                    "agents_md_max_lines": 500,
                    "router_min_top1_accuracy": min_top1,
                    # H-53: buffer-zone keys required by the strict validator
                    # even when the fixture only exercises the basic fail/pass
                    # arms. Same shape as _REQUIRED_THRESHOLD_KEYS in the gate;
                    # 0 here keeps the old tests' contract (no buffer;
                    # effective_floor = min_top1).
                    "router_min_top1_accuracy_noise_band": 0.0,
                    "router_min_top1_accuracy_meaningful_regression": 0.0,
                    "router_max_misdelegation": max_misd,
                    "router_target_top1_accuracy": target_top1,
                    "router_min_registry_skills": min_registry_skills,
                    # CR-2 fail-closed requires these keys even when the fixture
                    # only exercises kpi7 — partial files are a config error,
                    # not a "this test doesn't need them" case.
                    "evidence_min_records": 0,
                    "evidence_max_age_days": 90,
                    "tests_min_collected": 1,
                    "gcl_structural_fallback_max_ratio": 0.0,
                    "reflexion_min_injected_runs": 1}),
        encoding="utf-8",
    )
    audit = root / "audit-results"
    audit.mkdir()
    (audit / "skill-registry.json").write_text(
        json.dumps({"skills": [s for s in fleet if s["name"] not in drop]}),
        encoding="utf-8",
    )
    queries = {
        "qcloud-a-ops": [_POSITIVE, a_negative],
        "qcloud-b-ops": [_POSITIVE, _CLEAN_NEGATIVE],
        "qcloud-c-ops": _C_QUERIES,
    }
    for name, cases in queries.items():
        if name in missing_eval or name in drop:
            continue
        assets = root / name / "assets"
        assets.mkdir(parents=True)
        (assets / "eval_queries.json").write_text(
            json.dumps(cases), encoding="utf-8"
        )
    return root


@contextlib.contextmanager
def _router_fixture(min_top1: float, target_top1: float, max_misd: float = 0.30,
                    **kwargs):
    """Point the gate at a throwaway repo root (skill dirs + thresholds)."""
    with tempfile.TemporaryDirectory() as td:
        root = _write_repo(Path(td), min_top1, target_top1, max_misd, **kwargs)
        with mock.patch.object(check_kpi_gates, "ROOT", root), \
                mock.patch.object(check_kpi_gates, "REGISTRY",
                                  root / "audit-results" / "skill-registry.json"), \
                mock.patch.object(check_kpi_gates, "AUDIT", root / "audit-results"), \
                mock.patch.object(check_kpi_gates, "THRESHOLDS",
                                  root / "assets" / "shared" / "thresholds.json",
                                  create=True):
            yield root


def _stub_other_kpis() -> contextlib.ExitStack:
    """main() must be judged on the evidence gate alone; the other KPIs shell out
    to the real repo (registry build, spec-drift detector) and are stubbed.

    H-50 invariant: any non-pass status (incl. skip) escalates to exit 1.
    Stubbing kpi8_spec_drift to "skip" used to be benign — the old aggregator
    counted skip as harmless — but that escape hatch is exactly the silent-skip
    defect this slice exists to eliminate. The helper now reports "pass" for
    every stubbed KPI so the verdict reflects only the rule under test."""
    stack = contextlib.ExitStack()
    for name in ("kpi3_golden_coverage", "kpi7_router_confusion", "kpi8_spec_drift"):
        stack.enter_context(mock.patch.object(check_kpi_gates, name,
                                              return_value=("pass", "stub", "")))
    return stack


class Kpi7RouterThresholdTest(unittest.TestCase):
    def test_fails_below_router_min_top1_accuracy(self) -> None:
        """avg top1 = 50% against a 60% ratchet must FAIL."""
        with _router_fixture(0.60, 0.70) as root, _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
            self.assertEqual(status, "fail")
            self.assertIn("50.00%", detail)
            # H-53: the ratchet failure wording is now "below effective ratchet floor"
            # so the on-call can tell a real regression from a noise-band pass.
            # With noise_band=0 and meaningful_regression=0 in this fixture,
            # effective_floor == min_top1, so the message still names 60.00%.
            self.assertIn("below effective ratchet floor 60.00%", detail)
            # the artifact is still written for trend tracking, even on failure
            written = json.loads(
                (root / "audit-results" / "router-confusion.json").read_text(encoding="utf-8"))
        self.assertEqual(written["qcloud-a-ops"]["top1_accuracy"], 0.0)
        self.assertEqual(written["qcloud-b-ops"]["top1_accuracy"], 1.0)

    def test_passes_above_ratchet_and_names_the_target_gap(self) -> None:
        """Same 50% against a 10% ratchet passes — but 50% < 70% target, so the
        gap must be printed, not hidden behind a ✅."""
        with _router_fixture(0.10, 0.70), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "pass")
        self.assertIn("avg top1=50.00%", detail)
        self.assertIn("BELOW TARGET 70.00%", detail)
        self.assertIn(check_kpi_gates.ROUTER_GAP_ANCHOR, detail)

    def test_meeting_the_target_reports_no_gap(self) -> None:
        """L6 (silent side): above target, the detail carries no gap warning."""
        with _router_fixture(0.10, 0.40), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "pass")
        self.assertIn("avg top1=50.00% avg misdelegation=0.00%", detail)
        self.assertNotIn("BELOW TARGET", detail)

    def test_fails_above_max_misdelegation(self) -> None:
        """The misdelegation ceiling is its own ratchet, and it fires: a-ops'
        negative routes back to a-ops -> avg misdelegation = (1.0 + 0.0) / 2."""
        with _router_fixture(0.10, 0.70, max_misd=0.30,
                             a_negative={"query": "zzz never used keyword?!",
                                         "should_trigger": False}), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "fail")
        self.assertIn("avg misdelegation=50.00%", detail)
        self.assertIn("above misdelegation ceiling 30.00%", detail)

    def test_fails_when_fewer_than_half_the_registry_is_scoreable(self) -> None:
        """A measurement over a minority of the registry is not a measurement:
        1 of 3 skills has an eval file -> fail, and the detail names the gap."""
        with _router_fixture(0.10, 0.70, missing_eval=("qcloud-b-ops",)), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "fail")
        self.assertIn("only 1/3 skills are scoreable", detail)
        self.assertIn("qcloud-b-ops", detail)
        self.assertIn("qcloud-c-ops", detail)

    def test_fails_when_a_skill_was_deleted_from_the_registry(self) -> None:
        """A PR that deletes a skill it cannot make route legitimately used to
        raise *both* averages: dropping qcloud-a-ops leaves 2/2 scoreable, so the
        half-guard passes and the green row reports better numbers than the
        baseline. The registry floor is the guard that catches it."""
        with _router_fixture(0.10, 0.70, drop=("qcloud-a-ops",)), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "fail")
        self.assertIn("registry has 2 skill(s), below the recorded floor of 3", detail)
        # L6 (silent side): the same fixture with nothing dropped is inside the
        # floor, so the guard stays quiet on a healthy registry.
        with _router_fixture(0.10, 0.40), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "pass")
        self.assertNotIn("below the recorded floor", detail)

    def test_green_row_names_the_skills_it_did_not_measure(self) -> None:
        """A skill with empty intent_keywords has an eval file but scores a
        structural 0.0 on both arms (the router can never return it), so it is
        excluded — and named, so a ✅ still shows the coverage it skipped."""
        with _router_fixture(0.10, 0.40), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "pass")
        self.assertIn("2/3 skills scored", detail)
        self.assertIn("unmeasured: qcloud-c-ops", detail)
        # ...and it does not dilute the arms it was excluded from: averaging it
        # in would report 33.33% top1 instead of the keyworded skills' 50.00%.
        self.assertIn("avg top1=50.00%", detail)


def _write_repo_with_thresholds(
    root, *,
    min_top1, noise_band, meaningful_regression,
    target_top1=0.40, max_misd=0.30, min_registry_skills=FIXTURE_FLEET,
    a_query=None, omit_keys=(),
):
    """H-53 fixture: pin the buffer-zone keys to specific values. The fleet
    returns top1 = 0.0 for qcloud-a-ops and 1.0 for qcloud-b-ops by default
    (avg = 0.50), so the test sweeps min_top1 across the boundaries to land
    the measurement in each branch.
    """
    fleet = [
        {"name": "qcloud-a-ops", "intent_keywords": ["ZzzNeverUsedKeyword"]},
        {"name": "qcloud-b-ops", "intent_keywords": ["RunCvmInstance"]},
        {"name": "qcloud-c-ops", "intent_keywords": []},
    ]
    base = {
        "rubric_min_score": 0.5,
        "safety_fail_threshold": 0,
        "max_iterations": 5,
        "gcl_structural_critic_only": True,
        "reflexion_max_lines": 200,
        "agents_md_max_lines": 500,
        "router_min_top1_accuracy": min_top1,
        "router_min_top1_accuracy_noise_band": noise_band,
        "router_min_top1_accuracy_meaningful_regression": meaningful_regression,
        "router_max_misdelegation": max_misd,
        "router_target_top1_accuracy": target_top1,
        "router_min_registry_skills": min_registry_skills,
        "evidence_min_records": 0,
        "evidence_max_age_days": 90,
        "tests_min_collected": 1,
        "gcl_structural_fallback_max_ratio": 0.0,
        "reflexion_min_injected_runs": 1,
    }
    for k in omit_keys:
        base.pop(k, None)
    (root / "assets" / "shared").mkdir(parents=True)
    (root / "assets" / "shared" / "thresholds.json").write_text(
        json.dumps(base), encoding="utf-8",
    )
    audit = root / "audit-results"
    audit.mkdir()
    (audit / "skill-registry.json").write_text(
        json.dumps({"skills": fleet}), encoding="utf-8",
    )
    queries = {
        "qcloud-a-ops": [a_query or _POSITIVE, _CLEAN_NEGATIVE],
        "qcloud-b-ops": [_POSITIVE, _CLEAN_NEGATIVE],
        "qcloud-c-ops": _C_QUERIES,
    }
    for name, cases in queries.items():
        assets = root / name / "assets"
        assets.mkdir(parents=True)
        (assets / "eval_queries.json").write_text(
            json.dumps(cases), encoding="utf-8",
        )
    return root


@contextlib.contextmanager
def _buffer_zone_fixture(
    *,
    min_top1, noise_band, meaningful_regression,
    target_top1=0.40, max_misd=0.30, a_query=None, omit_keys=(),
):
    """H-53: throwaway repo whose thresholds include the buffer-zone keys.
    effective_floor = min_top1 - noise_band - meaningful_regression."""
    with tempfile.TemporaryDirectory() as td:
        root = _write_repo_with_thresholds(
            Path(td),
            min_top1=min_top1, noise_band=noise_band,
            meaningful_regression=meaningful_regression,
            target_top1=target_top1, max_misd=max_misd,
            a_query=a_query, omit_keys=omit_keys,
        )
        with mock.patch.object(check_kpi_gates, "ROOT", root), \
                mock.patch.object(check_kpi_gates, "REGISTRY",
                                  root / "audit-results" / "skill-registry.json"), \
                mock.patch.object(check_kpi_gates, "AUDIT", root / "audit-results"), \
                mock.patch.object(check_kpi_gates, "THRESHOLDS",
                                  root / "assets" / "shared" / "thresholds.json",
                                  create=True):
            yield root


class TestRouterBufferZone(unittest.TestCase):
    """H-53: ratchet has a buffer zone. effective_floor = min_top1 - noise_band
    - meaningful_regression. Three branches:
      - avg < effective_floor  -> "fail" with detail naming "effective"
      - effective_floor <= avg < min_top1 -> "pass" with note naming noise/buffer
      - avg >= min_top1 -> "pass" with NO noise/buffer mention

    Plus a CR-2 invariant: missing `noise_band` raises GateConfigError so a
    partial thresholds file cannot silently revert the buffer zone."""

    def test_router_below_effective_floor_fails(self) -> None:
        """avg = 0.50 < effective_floor (0.70 - 0.015 - 0.025 = 0.660) -> fail
        and the detail names the effective floor so the on-call can see why."""
        with _buffer_zone_fixture(
            min_top1=0.70, noise_band=0.015, meaningful_regression=0.025,
        ), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "fail")
        self.assertIn("effective", detail.lower())
        self.assertIn("66.00%", detail)
        self.assertIn("avg top1=50.00%", detail)
        self.assertIn("below effective ratchet floor", detail)
        self.assertIn("noise_band=1.50%", detail)
        self.assertIn("meaningful_regression=2.50%", detail)

    def test_router_in_noise_zone_passes_with_note(self) -> None:
        """avg = 0.50 sits inside the buffer zone (effective_floor, min_top1) =
        (0.50, 0.70) when noise_band=0.10 + meaningful_regression=0.10 ->
        effective_floor = 0.50. So measurement lands >= effective_floor and
        < min_top1: canonical buffer-zone position."""
        with _buffer_zone_fixture(
            min_top1=0.70, noise_band=0.10, meaningful_regression=0.10,
        ), _quiet():
            status, detail, note = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "pass")
        self.assertTrue(
            "noise" in note.lower() or "buffer" in note.lower(),
            f"note should mention noise/buffer; got {note!r}",
        )
        self.assertIn("avg top1=50.00%", detail)
        self.assertIn("gap to fail floor", note)
        self.assertIn("gap to target", note)
        self.assertIn("+10.00%", note)
        self.assertIn("+0.00%", note)

    def test_router_above_min_top1_passes_cleanly(self) -> None:
        """avg = 0.50 >= min_top1 (0.10) -> "pass" with NO noise/buffer mention.
        Above-min_top1 reads like a normal score, not a noisy one (L6 silent side)."""
        with _buffer_zone_fixture(
            min_top1=0.10, noise_band=0.015, meaningful_regression=0.025,
            target_top1=0.40,
        ), _quiet():
            status, detail, note = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "pass")
        self.assertIn("avg top1=50.00%", detail)
        self.assertNotIn("noise", note.lower())
        self.assertNotIn("buffer", note.lower())

    def test_missing_noise_band_key_raises_GateConfigError(self) -> None:
        """CR-2 / H-53: a partial thresholds.json cannot silently revert the
        buffer zone. Strict validator fires before kpi7 reads anything."""
        with _buffer_zone_fixture(
            min_top1=0.70, noise_band=0.015, meaningful_regression=0.025,
            omit_keys=("router_min_top1_accuracy_noise_band",),
        ), _quiet():
            with self.assertRaises(check_kpi_gates.GateConfigError) as ctx:
                check_kpi_gates.kpi7_router_confusion()
        self.assertIn("router_min_top1_accuracy_noise_band", str(ctx.exception))
        self.assertIn("kpi7_router_confusion", str(ctx.exception))


class Kpi1SafetyEvidenceTest(unittest.TestCase):
    """KPI#1/#2 must read the real evidence stream (evidence-local.jsonl)."""

    @contextlib.contextmanager
    def _audit_dir(self, lines: list[str], name: str = "evidence-local.jsonl"):
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit-results"
            audit.mkdir()
            (audit / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
            with mock.patch.object(check_kpi_gates, "AUDIT", audit):
                yield audit

    @staticmethod
    def _records(n: int, days_ago: float = 0) -> list[str]:
        return [json.dumps(_captured_days_ago(days_ago)) for _ in range(n)]

    def test_jsonl_stream_is_validated_and_counted(self) -> None:
        with self._audit_dir(self._records(FLOOR)):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "pass")
        self.assertIn(f"{FLOOR} record(s) valid", detail)

    def test_per_run_jsonl_is_read_not_just_dot_json(self) -> None:
        """The round-1 glob was `evidence-*.json`, which cannot match the
        `evidence-<run_id>.jsonl` files the fleet actually writes."""
        with self._audit_dir(self._records(FLOOR), name="evidence-run42.jsonl"):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "pass")
        self.assertIn(f"{FLOOR} record(s) valid", detail)

    def test_empty_stream_fails_instead_of_passing_as_zero_evidence(self) -> None:
        """BLOCKER-2: an empty/whitespace-only stream parsed to 0 records and the
        old gate mapped rc 0 to 'pass' — truncating evidence improved the verdict."""
        for lines in ([], ["", "  ", ""]):
            with self._audit_dir(lines):
                status, detail, _ = check_kpi_gates.kpi1_2_safety()
            self.assertEqual(status, "fail", lines)
            self.assertIn("0 fresh record(s)", detail)

    def test_below_the_floor_fails(self) -> None:
        """One self-minted record is not fleet evidence: the floor is the gate."""
        with self._audit_dir(self._records(FLOOR - 1)):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "fail")
        self.assertIn(f"--min-records floor is {FLOOR}", detail)

    def test_absent_stream_fails_by_default_and_skips_only_with_the_escape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit-results"
            audit.mkdir()
            with mock.patch.object(check_kpi_gates, "AUDIT", audit):
                status, detail, _ = check_kpi_gates.kpi1_2_safety()
                self.assertEqual(status, "fail")
                self.assertIn("no evidence stream", detail)
                with mock.patch.dict(os.environ, {"GATE_REQUIRE_EVIDENCE": "0"}):
                    status, detail, _ = check_kpi_gates.kpi1_2_safety()
            self.assertEqual(status, "skip")
            self.assertIn("GATE_REQUIRE_EVIDENCE=0", detail)

    def test_aged_out_records_are_reported_but_not_counted_as_evidence(self) -> None:
        """A 2019 stream must not keep the safety gate green forever."""
        with self._audit_dir(self._records(FLOOR, days_ago=3650)):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "fail")
        self.assertIn("0 fresh record(s)", detail)
        # "0 fresh" alone cannot be told apart from an empty stream; the aged-out
        # count is what sends the on-call to runbook V5 instead of V4.
        self.assertIn(f"{FLOOR} record(s) were read but aged out beyond", detail)
        with self._audit_dir(self._records(FLOOR) + self._records(FLOOR, days_ago=3650)):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "pass")
        self.assertIn(f"{FLOOR} record(s) valid, {FLOOR} aged-out", detail)

    def test_malformed_jsonl_line_fails(self) -> None:
        lines = [*self._records(FLOOR), '{"skill": "broken", ']
        with self._audit_dir(lines):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "fail")
        self.assertIn("JSONL line", detail)

    def test_main_fails_on_absent_evidence_and_on_bad_jsonl(self) -> None:
        """L6 both ways: exit 1 when there is no evidence stream at all, exit 0
        on a healthy one, exit 1 again on a broken line."""
        with tempfile.TemporaryDirectory() as td, _stub_other_kpis(), _quiet():
            audit = Path(td) / "audit-results"
            audit.mkdir()
            with mock.patch.object(check_kpi_gates, "AUDIT", audit):
                self.assertEqual(check_kpi_gates.main(), 1)  # fires: no evidence
                (audit / "evidence-local.jsonl").write_text(
                    "\n".join(self._records(FLOOR)) + "\n", encoding="utf-8")
                self.assertEqual(check_kpi_gates.main(), 0)  # silent: clean stream
                (audit / "evidence-local.jsonl").write_text("{not json}\n", encoding="utf-8")
                self.assertEqual(check_kpi_gates.main(), 1)  # fires


class CommittedEvidenceFixtureTest(unittest.TestCase):
    """The KPI#1/#2 CI hook grades the committed fixtures in
    scripts/fixtures/evidence/, staged by the workflow step under one name and
    selected by GATE_EVIDENCE_GLOB. L6: the clean fixture must stay silent and
    the violating one must fire in the same environment CI uses."""

    @staticmethod
    def _text(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    @contextlib.contextmanager
    def _graded(self, name: str):
        """Stage a fixture the way the workflow does, under the graded name."""
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit-results"
            audit.mkdir()
            staged = audit / "evidence-fixture.jsonl"
            staged.write_text(self._text(name), encoding="utf-8")
            with mock.patch.object(check_kpi_gates, "AUDIT", audit), \
                    mock.patch.dict(os.environ,
                                    {"GATE_EVIDENCE_GLOB": staged.name}):
                yield staged

    def test_clean_fixture_stays_silent_and_exercises_the_age_path(self) -> None:
        with self._graded(CLEAN_FIXTURE):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "pass")
        self.assertIn("record(s) valid", detail)
        # the aged-out branch ran: the 2020-dated records are reported, not counted
        self.assertIn("aged-out", detail)

    def test_violating_fixture_fires_both_safety_rules(self) -> None:
        with self._graded(VIOLATING_FIXTURE):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "fail")
        self.assertIn("KPI#1 requires leak_checked=true", detail)
        self.assertIn("KPI#2 destructive op requires a non-null confirmation token", detail)

    def test_main_exits_0_on_the_clean_fixture_and_1_on_the_violating_one(self) -> None:
        """What the workflow asserts, end to end: the very command CI runs goes
        red if the safety rules stop firing."""
        with self._graded(CLEAN_FIXTURE) as staged, _stub_other_kpis(), _quiet():
            self.assertEqual(check_kpi_gates.main(), 0)
            staged.write_text(self._text(VIOLATING_FIXTURE), encoding="utf-8")
            self.assertEqual(check_kpi_gates.main(), 1)

    def test_graded_set_is_the_named_file_not_the_local_stream(self) -> None:
        """Steps in the same CI job write into this directory (the smoke test
        writes one record; the unit tests minted 17 more until they were
        isolated), so a default glob can grade records the job wrote seconds
        earlier — the defect. Naming the fixture excludes them."""
        forged = [{**VALID_EVIDENCE,
                   "safety": {**VALID_EVIDENCE["safety"], "leak_checked": False}}]
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit-results"
            audit.mkdir()
            (audit / "evidence-local.jsonl").write_text(
                "\n".join(json.dumps(r) for r in forged * (FLOOR + 1)) + "\n",
                encoding="utf-8",
            )
            (audit / "evidence-fixture.jsonl").write_text(
                self._text(CLEAN_FIXTURE), encoding="utf-8")
            with mock.patch.object(check_kpi_gates, "AUDIT", audit):
                status, detail, _ = check_kpi_gates.kpi1_2_safety()
                self.assertEqual(status, "fail")          # the minted stream is read
                self.assertIn("leak_checked", detail)
                with mock.patch.dict(os.environ,
                                     {"GATE_EVIDENCE_GLOB": "evidence-fixture.jsonl"}):
                    status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "pass")                  # the fixture is read instead

    def test_clean_fixture_supplies_the_configured_floor(self) -> None:
        """The fixture exists to exercise the floor and the ageing window: raising
        evidence_min_records past what it supplies must break this test loudly
        instead of silently reddening CI."""
        rows = [json.loads(line) for line in self._text(CLEAN_FIXTURE).splitlines()
                if line.strip()]
        fresh = [r for r in rows if not r["provenance"]["captured_at"].startswith("2020")]
        self.assertGreaterEqual(len(fresh), FLOOR)
        self.assertTrue(len(rows) > len(fresh), "no aged-out record: ageing unexercised")


class TestAggregate(unittest.TestCase):
    """H-50: aggregate() must downgrade any non-pass status (incl. skip) to
    exit 1, so a silently-skipped rule cannot masquerade as a green build.
    The frozen KpiResult / AggregateVerdict dataclasses live in
    check_kpi_gates.py; the function uses raw strings."""

    def test_aggregate_all_pass_returns_exit_0(self) -> None:
        results = [
            check_kpi_gates.KpiResult(rule="kpi1", status="pass", detail="ok"),
            check_kpi_gates.KpiResult(rule="kpi2", status="pass", detail="ok"),
            check_kpi_gates.KpiResult(rule="kpi7", status="pass", detail="ok"),
        ]
        verdict = check_kpi_gates.aggregate(results)
        self.assertEqual(verdict.status, "pass")
        self.assertEqual(verdict.exit_code, 0)

    def test_aggregate_any_fail_returns_exit_1(self) -> None:
        results = [
            check_kpi_gates.KpiResult(rule="kpi1", status="pass", detail="ok"),
            check_kpi_gates.KpiResult(rule="kpi2", status="fail", detail="leak"),
            check_kpi_gates.KpiResult(rule="kpi7", status="pass", detail="ok"),
        ]
        verdict = check_kpi_gates.aggregate(results)
        self.assertEqual(verdict.status, "fail")
        self.assertEqual(verdict.exit_code, 1)

    def test_aggregate_any_skip_returns_exit_1_and_warns(self) -> None:
        """H-50 KEY: a skip in any rule -> AggregateVerdict("warn", 1, ...)."""
        results = [
            check_kpi_gates.KpiResult(rule="kpi1", status="pass", detail="ok"),
            check_kpi_gates.KpiResult(rule="kpi2", status="skip", detail="GATE_REQUIRE_EVIDENCE=0"),
            check_kpi_gates.KpiResult(rule="kpi7", status="pass", detail="ok"),
        ]
        verdict = check_kpi_gates.aggregate(results)
        self.assertEqual(verdict.status, "warn")
        self.assertEqual(verdict.exit_code, 1)
        self.assertIn("skipped", verdict.note)

    def test_aggregate_all_skip_returns_exit_1(self) -> None:
        results = [
            check_kpi_gates.KpiResult(rule="kpi1", status="skip", detail="d1"),
            check_kpi_gates.KpiResult(rule="kpi2", status="skip", detail="d2"),
            check_kpi_gates.KpiResult(rule="kpi7", status="skip", detail="d3"),
        ]
        verdict = check_kpi_gates.aggregate(results)
        self.assertEqual(verdict.status, "warn")
        self.assertEqual(verdict.exit_code, 1)


class GateFooterTest(unittest.TestCase):
    """H-19: the escape skip and KPI#8's informational skip must not be
    summarised by one word — a CI reader takes the last line as the verdict."""

    def test_footer_separates_not_enforced_from_informational(self) -> None:
        """H-19 + H-50: KPI#1's escape skip and KPI#8's informational skip
        must not be summarised by one word. After H-50 the escape skip also
        makes main() exit 1 (visible degradation) -- the test asserts that
        contract."""
        with tempfile.TemporaryDirectory() as td, _stub_other_kpis():
            audit = Path(td) / "audit-results"
            audit.mkdir()
            with mock.patch.object(check_kpi_gates, "AUDIT", audit), \
                    mock.patch.dict(os.environ, {"GATE_REQUIRE_EVIDENCE": "0"}), \
                    contextlib.redirect_stdout(buf := io.StringIO()):
                self.assertEqual(check_kpi_gates.main(), 1)
        out = buf.getvalue()
        self.assertIn("1 NOT ENFORCED (KPI#1/#2)", out)
        self.assertIn("skipped", out.lower())


class GateConfigErrorTest(unittest.TestCase):
    """MAJOR: a broken thresholds.json is a gate error (exit 2), not a KPI
    regression (exit 1) — the module docstring reserves those exits."""

    @contextlib.contextmanager
    def _thresholds(self, text: str | None):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "thresholds.json"
            if text is not None:
                path.write_text(text, encoding="utf-8")
            with mock.patch.object(check_kpi_gates, "THRESHOLDS", path):
                yield path

    def test_broken_thresholds_raise_a_config_error(self) -> None:
        """Each breakage names the file it tried to read (and a missing key, when
        the file parsed but a key did not) instead of dying with a traceback.

        CR-2: the *aggregate* gate fails-closed on any missing key from the
        full required set, not just the one the calling KPI reads. The error
        message names the FIRST missing key (alphabetical) and the owner
        module; the test asserts one of the legitimately-missing keys is
        named, not a specific one — the strict validation is the contract.
        """
        bad = {
            "absent": (None, None),
            "unparseable": ("{oops", None),
            # the file is missing most keys; whichever one the strict
            # validator surfaces first is acceptable — it's still a config
            # error pointing at the file.
            "missing key": ('{"router_min_top1_accuracy": 0.1}',
                            "rubric_min_score"),
            "null value": (json.dumps({"rubric_min_score": None,
                                       "router_min_top1_accuracy": 0.1,
                                       "router_max_misdelegation": 0.3,
                                       "router_target_top1_accuracy": 0.7}),
                           "rubric_min_score"),
        }
        with _router_fixture(0.10, 0.70):
            for label, (text, key) in bad.items():
                with self.subTest(label), self._thresholds(text) as path, _quiet():
                    with self.assertRaises(check_kpi_gates.GateConfigError) as ctx:
                        check_kpi_gates.kpi7_router_confusion()
                    self.assertIn(str(path), str(ctx.exception))
                    if key:
                        self.assertIn(key, str(ctx.exception))

    def test_main_exits_2_not_1_on_broken_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit-results"
            audit.mkdir()
            (audit / "evidence-local.jsonl").write_text(
                "\n".join(self._records()) + "\n", encoding="utf-8")
            with self._thresholds("{oops"), \
                    mock.patch.object(check_kpi_gates, "AUDIT", audit), \
                    _stub_other_kpis(), contextlib.redirect_stdout(buf := io.StringIO()):
                self.assertEqual(check_kpi_gates.main(), 2)
        self.assertIn("GATE CONFIG ERROR", buf.getvalue())
        self.assertIn("thresholds.json", buf.getvalue())

    @staticmethod
    def _records() -> list[str]:
        return [json.dumps(VALID_EVIDENCE)]


if __name__ == "__main__":
    unittest.main()
