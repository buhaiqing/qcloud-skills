"""Unit tests for AIOpsEnvelope (P0-1) — wrap / validate / causation / breaking.

Covers SPEC §8 Self-check:
  - wrap() output passes validate() for all event_types
  - causation chain linking
  - payload compatibility (unchanged)
  - desensitization (no credentials in envelope)
  - breaking-change detection

Run: python3 -m pytest scripts/test_aiops_envelope.py -q
     (or) python3 -m unittest scripts.test_aiops_envelope
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "qcloud-aiops-diagnosis" / "assets" / "aiops-envelope.schema.json"
FIXTURES_PATH = ROOT / "qcloud-aiops-diagnosis" / "assets" / "aiops-envelope.fixtures.json"

sys_path = str(ROOT / "qcloud-copilot")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from copilot import aiops_envelope as env
from validate_aiops_envelope import _breaking_changes


class WrapTests(unittest.TestCase):
    def test_all_event_types_wrap_valid(self) -> None:
        for et in env.EVENT_TYPES:
            envelope = env.wrap(et, {"k": "v"}, trace_id=f"trace-{et}")
            errors = env.validate(envelope)
            self.assertEqual(errors, [], f"event_type={et} produced invalid envelope: {errors}")

    def test_trace_id_required(self) -> None:
        with self.assertRaises(ValueError):
            env.wrap("alarm", {}, trace_id="")
        with self.assertRaises(ValueError):
            env.wrap("alarm", {}, trace_id=None)  # type: ignore[arg-type]

    def test_unknown_event_type_rejected(self) -> None:
        with self.assertRaises(ValueError):
            env.wrap("bogus", {}, trace_id="trace-x")

    def test_payload_unchanged(self) -> None:
        payload = {"metric": "cpu", "value": 95, "nested": {"a": [1, 2]}}
        envelope = env.wrap("alarm", payload, trace_id="trace-1")
        self.assertEqual(envelope["payload"], payload)
        self.assertIs(envelope["payload"], payload)  # 同一对象，未改写

    def test_nullable_fields_omitted_not_rejected(self) -> None:
        # 本地/自动化运行无值用 null 语义（不写入 None 键），schema 允许缺失。
        envelope = env.wrap("incident", {}, trace_id="trace-2")
        self.assertNotIn("tenant_id", envelope)
        self.assertNotIn("causation_id", envelope)
        self.assertEqual(env.validate(envelope), [])

    def test_optional_fields_attached(self) -> None:
        envelope = env.wrap(
            "rca",
            {},
            trace_id="trace-3",
            tenant_id="t-1",
            region="ap-guangzhou",
            incident_id="INC-1",
            causation_id="caus-abc",
            resource={"product": "cvm", "resource_id": "ins-x"},
            decision={"maker": "aiops", "severity": "P1"},
            action_state="executing",
        )
        self.assertEqual(envelope["tenant_id"], "t-1")
        self.assertEqual(envelope["causation_id"], "caus-abc")
        self.assertEqual(envelope["resource"]["resource_id"], "ins-x")
        self.assertEqual(env.validate(envelope), [])


class CausationTests(unittest.TestCase):
    def test_causation_chain_linking(self) -> None:
        # 根因 alarm 生成 causation_id，下游事件引用它 → 串联
        root_alarm_id = "alarm-cpu-001"
        caus = env.new_causation_id(root_alarm_id)
        self.assertTrue(caus.startswith("caus-"))
        self.assertEqual(len(caus), 5 + 12)
        self.assertEqual(env.new_causation_id(root_alarm_id), caus, "deterministic per seed")

        rca = env.wrap("rca", {}, trace_id="trace-rca", incident_id="INC-1", causation_id=caus)
        action = env.wrap("action", {}, trace_id="trace-act", incident_id="INC-1", causation_id=caus)
        self.assertEqual(rca["causation_id"], action["causation_id"])
        self.assertEqual(rca["incident_id"], action["incident_id"])

    def test_causation_distinct_seeds(self) -> None:
        self.assertNotEqual(env.new_causation_id("alarm-a"), env.new_causation_id("alarm-b"))


class DesensitizationTests(unittest.TestCase):
    def test_no_credentials_in_envelope_structure(self) -> None:
        # envelope 结构字段（schema_version/event_id/trace_id/...）绝不携带凭据。
        # payload 保留原始内容（脱敏由上层 trace 层负责），不在此层改写。
        env_with_creds = env.wrap(
            "action",
            {"detail": "safe"},
            trace_id="trace-sec",
            incident_id="INC-1",
            tenant_id="tenant-01",
        )
        blob = json.dumps(env_with_creds)
        self.assertNotIn("AKID", blob)
        self.assertNotIn("secret", blob)
        # payload 原样保留（含敏感键名），不在此层断言脱敏 payload
        payload = {"secret": "AKIDexampleSecretId0123456789"}
        wrapped = env.wrap("action", payload, trace_id="trace-sec")
        self.assertIs(wrapped["payload"], payload)


class BreakingChangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.new_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def _copy(self) -> dict:
        return json.loads(json.dumps(self.schema))

    def test_removing_required_field_is_not_breaking(self) -> None:
        # 从 required 移除字段是向后兼容的（生产者仍会 emit 它，只是变为可选）。
        new = self._copy()
        new["required"] = [f for f in new["required"] if f != "trace_id"]
        changes = _breaking_changes(self.schema, new)
        self.assertEqual(changes, [])

    def test_adding_required_field_is_breaking(self) -> None:
        new = self._copy()
        new["required"].append("tenant_id")
        changes = _breaking_changes(self.schema, new)
        self.assertTrue(any("+tenant_id" in c for c in changes))

    def test_enum_narrowing_is_breaking(self) -> None:
        new = self._copy()
        new["properties"]["event_type"]["enum"] = new["properties"]["event_type"]["enum"][:4]
        changes = _breaking_changes(self.schema, new)
        self.assertTrue(any("enum narrowed" in c for c in changes))

    def test_const_change_is_breaking(self) -> None:
        new = self._copy()
        new["properties"]["schema_version"]["const"] = "0.2"
        changes = _breaking_changes(self.schema, new)
        self.assertTrue(any("schema_version: const changed" in c for c in changes))

    def test_additive_minor_is_not_breaking(self) -> None:
        new = self._copy()
        new["properties"]["new_optional_field"] = {"type": "string"}
        changes = _breaking_changes(self.schema, new)
        self.assertEqual(changes, [])


class FixtureTests(unittest.TestCase):
    def test_all_fixtures_valid(self) -> None:
        data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
        for name, scenario in data["scenarios"].items():
            env_wrapped = env.wrap(
                scenario["event_type"],
                scenario.get("payload", {}),
                trace_id=scenario["trace_id"],
                tenant_id=scenario.get("tenant_id"),
                region=scenario.get("region"),
                incident_id=scenario.get("incident_id"),
                causation_id=scenario.get("causation_id"),
                resource=scenario.get("resource"),
                time_window=scenario.get("time_window"),
                evidence=scenario.get("evidence"),
                data_quality=scenario.get("data_quality"),
                confidence=scenario.get("confidence"),
                decision=scenario.get("decision"),
                action_state=scenario.get("action_state"),
            )
            errors = env.validate(env_wrapped)
            self.assertEqual(errors, [], f"fixture {name} invalid: {errors}")


if __name__ == "__main__":
    unittest.main()
