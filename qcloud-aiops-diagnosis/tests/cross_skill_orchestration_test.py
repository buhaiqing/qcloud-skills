#!/usr/bin/env python3
"""Tests for cross-skill orchestration payloads and mode selection.

Validates the contracts in
`qcloud-aiops-diagnosis/references/cross-skill-orchestration.md` without requiring
live cloud credentials.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parents[1]  # qcloud-aiops-diagnosis/
ASSETS = SKILL_DIR / "assets"

# Optional JSON Schema validation; if jsonschema is unavailable we do structural checks.
try:
    import jsonschema  # type: ignore

    HAS_JSONSCHEMA = True
except Exception:  # pragma: no cover
    HAS_JSONSCHEMA = False


def load_schema(name: str) -> dict[str, Any]:
    path = ASSETS / name
    if not path.exists():
        raise FileNotFoundError(f"Missing schema: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_json(name: str) -> dict[str, Any]:
    path = ASSETS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _assert_has_keys(obj: dict[str, Any], keys: set[str], label: str) -> None:
    missing = keys - obj.keys()
    if missing:
        raise AssertionError(f"{label} missing required keys: {sorted(missing)}")


class FinOpsHandoffTests(unittest.TestCase):
    """FinOps → AIOps handoff (cross-skill-orchestration.md §2.1)."""

    def setUp(self) -> None:
        self.schema = load_schema("finops-handoff.schema.json")
        self.sample = {
            "handoff_id": "finops-ho-20260609-001",
            "source_skill": "qcloud-finops-ops",
            "anomaly": {
                "month": "2026-05",
                "confidence": "HIGH",
                "ii_ratio": 0.35,
                "iii_ratio": 0.92,
                "ii_violated": True,
                "iii_violated": True,
                "total_delta_cny": 12500.0,
            },
            "top_products": [
                {
                    "product": "cvm",
                    "delta_cny": 8000,
                    "delta_pct": 0.42,
                    "top_resource_ids": ["ins-aaa", "ins-bbb"],
                },
                {"product": "cdb", "delta_cny": 3000, "delta_pct": 0.28},
            ],
            "dispatch_inspection": True,
            "time_window": {"start": "2026-05-01", "end": "2026-05-31"},
            "owner": "finops-team",
        }

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed")
    def test_sample_against_schema(self) -> None:
        jsonschema.validate(self.sample, self.schema)

    def test_required_fields(self) -> None:
        _assert_has_keys(self.sample, {"handoff_id", "source_skill", "anomaly", "top_products"}, "finops_handoff")
        _assert_has_keys(self.sample["anomaly"], {"confidence"}, "anomaly")
        for item in self.sample["top_products"]:
            _assert_has_keys(item, {"product", "delta_cny"}, "top_products item")

    def test_source_skill_const(self) -> None:
        self.assertEqual(self.sample["source_skill"], "qcloud-finops-ops")

    def test_invalid_source_skill_rejected(self) -> None:
        if not HAS_JSONSCHEMA:
            self.fail("jsonschema not installed: cannot validate schema const constraint")
        bad = {**self.sample, "source_skill": "qcloud-cvm-ops"}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(bad, self.schema)


class ProactiveInspectionHandoffTests(unittest.TestCase):
    """Proactive Inspection → AIOps handoff (cross-skill-orchestration.md §2.2)."""

    def setUp(self) -> None:
        self.schema = load_schema("inspection-handoff.schema.json")
        self.sample = {
            "handoff_id": "insp-ho-20260609-002",
            "source_skill": "qcloud-proactive-inspection",
            "inspection_id": "insp-20260609-weekly",
            "findings": [
                {
                    "resource_type": "cvm",
                    "resource_id": "ins-aaa",
                    "severity": "CRITICAL",
                    "rule": "cpu_sustained_high",
                    "metric": "CpuUsage",
                    "value": "96%",
                    "detected_at": "2026-06-09T08:00:00+08:00",
                }
            ],
            "report_path": "./audit-results/inspection-report-20260609.md",
        }

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed")
    def test_sample_against_schema(self) -> None:
        jsonschema.validate(self.sample, self.schema)

    def test_required_fields(self) -> None:
        _assert_has_keys(
            self.sample,
            {"handoff_id", "source_skill", "inspection_id", "findings"},
            "inspection_handoff",
        )
        finding = self.sample["findings"][0]
        _assert_has_keys(
            finding,
            {"resource_type", "resource_id", "severity", "rule"},
            "finding",
        )

    def test_findings_non_empty(self) -> None:
        self.assertGreaterEqual(len(self.sample["findings"]), 1)


class ModeSelectionTests(unittest.TestCase):
    """Orchestration mode selection (cross-skill-orchestration.md §1)."""

    def select_mode(self, handoff_source: str, confidence: str, top_product_delta: bool, dispatch_inspection: bool, resolved: bool, prevention: bool, capacity_pressure: bool) -> str:
        """Reference implementation of the mode-selection pseudocode."""
        if handoff_source == "finops" and confidence == "HIGH" and dispatch_inspection:
            return "F1"
        if handoff_source == "finops" and top_product_delta:
            return "F2"
        if handoff_source == "proactive_inspection" and confidence == "CRITICAL":
            # spec: finding_severity >= CRITICAL (CRITICAL is highest severity)
            return "P1"
        if resolved and prevention:
            return "A1"
        if capacity_pressure:
            return "A2"
        return "standard"

    def test_f1_finops_high_with_inspection(self) -> None:
        self.assertEqual(self.select_mode("finops", "HIGH", True, True, False, False, False), "F1")

    def test_f2_finops_with_top_product_delta(self) -> None:
        self.assertEqual(self.select_mode("finops", "MEDIUM", True, False, False, False, False), "F2")

    def test_p1_proactive_inspection_critical(self) -> None:
        self.assertEqual(self.select_mode("proactive_inspection", "CRITICAL", False, False, False, False, False), "P1")

    def test_a1_prevention_after_resolution(self) -> None:
        self.assertEqual(self.select_mode("none", "", False, False, True, True, False), "A1")

    def test_a2_capacity_pressure(self) -> None:
        self.assertEqual(self.select_mode("none", "", False, False, False, False, True), "A2")

    def test_standard_fallback(self) -> None:
        self.assertEqual(self.select_mode("none", "", False, False, False, False, False), "standard")


class CrossSkillBundleTests(unittest.TestCase):
    """Cross-Skill Orchestration Bundle structure (cross-skill-orchestration.md §5)."""

    def test_bundle_required_fields(self) -> None:
        bundle: dict[str, Any] = {
            "orchestration_id": "xskill-20260609-001",
            "mode": "F2",
            "participating_skills": [
                "qcloud-finops-ops",
                "qcloud-proactive-inspection",
                "qcloud-aiops-diagnosis",
            ],
            "handoffs": {"finops": {}, "inspection": {}, "aiops": {}},
            "joint_hypothesis": {
                "summary": "CVM traffic burst caused May bill +42% and CLB 5xx",
                "confidence": "HIGH",
                "score": 7,
            },
            "artifacts": {
                "rca_id": "rca-20260609-001",
                "inspection_report": "./audit-results/inspection-report-20260609.md",
                "finops_anomaly_ref": "finops-ho-20260609-001",
                "incident_kb_id": "ikb-20260609-001",
            },
            "prevention_items": [],
            "finops_advisory": None,
            "recommendations": [
                {
                    "action": "RECOMMENDATION (not execution): right-size CVM ins-aaa after traffic review",
                    "delegate_to": "qcloud-finops-ops",
                    "priority": "P1",
                }
            ],
            "data_quality": {"status": "complete", "warnings": []},
        }
        _assert_has_keys(
            bundle,
            {
                "orchestration_id",
                "mode",
                "participating_skills",
                "handoffs",
                "joint_hypothesis",
                "artifacts",
                "prevention_items",
                "finops_advisory",
                "recommendations",
                "data_quality",
            },
            "cross_skill_bundle",
        )
        _assert_has_keys(bundle["joint_hypothesis"], {"summary", "confidence", "score"}, "joint_hypothesis")
        _assert_has_keys(bundle["artifacts"], {"rca_id"}, "artifacts")


class PreventionAndFinOpsAdvisoryTests(unittest.TestCase):
    """AIOps outbound handoff structures (cross-skill-orchestration.md §2.3/2.4)."""

    def test_prevention_handoff_structure(self) -> None:
        item = {
            "item_id": "prev-001",
            "source_rca_id": "rca-20260609-001",
            "check_type": "disk_usage_trend",
            "resource_type": "cvm",
            "resource_id": "ins-xxx",
            "rationale": "Root cause was disk pressure; add weekly disk rotation check",
            "delegate_to": "qcloud-proactive-inspection",
            "priority": "P1",
        }
        _assert_has_keys(
            item,
            {"item_id", "source_rca_id", "check_type", "resource_type", "resource_id", "delegate_to", "priority"},
            "prevention_item",
        )

    def test_finops_advisory_structure(self) -> None:
        advisory = {
            "trigger": "capacity_saturation",
            "confidence": "MEDIUM",
            "affected_products": ["cvm", "cdb"],
            "resource_ids": ["ins-xxx", "cdb-yyy"],
            "signals": [
                {"type": "baseline_anomaly", "metric": "CpuUsage", "anomaly_score": 68}
            ],
            "recommended_finops_actions": [
                "RECOMMENDATION (not execution): run right-sizing analysis via qcloud-finops-ops"
            ],
            "delegate_to": "qcloud-finops-ops",
        }
        _assert_has_keys(
            advisory,
            {"trigger", "confidence", "affected_products", "resource_ids", "signals", "recommended_finops_actions", "delegate_to"},
            "finops_advisory",
        )


if __name__ == "__main__":
    unittest.main()
