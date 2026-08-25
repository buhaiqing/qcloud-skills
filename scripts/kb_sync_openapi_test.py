#!/usr/bin/env python3
"""Tests for kb_sync_openapi.py — OpenAPI/tccli metadata → Layer-1/2 KB generation.

Covers: flag variant normalization, response data_field detection, product→skill
mapping with graceful skips, write/check round-trip, and validator merge wiring
(TCLOUD_KB_DIR consumed by cli_param_validator / schema_validator).
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cli_param_validator
import kb_sync_openapi as kbs
import schema_validator

FIXTURE_API_JSON = {
    "actions": {
        "DescribeFoos": {"input": "DescribeFoosRequest", "output": "DescribeFoosResponse"},
        "DeleteFoo": {"input": "DeleteFooRequest", "output": "DeleteFooResponse"},
    },
    "objects": {
        "DescribeFoosRequest": {
            "members": [
                {"name": "Limit", "type": "integer"},
                {"name": "FooIds", "type": "list"},
                {"name": "StoppedMode", "type": "string"},
            ]
        },
        "DescribeFoosResponse": {
            "members": [
                {"name": "TotalCount", "type": "integer"},
                {"name": "FooSet", "type": "list"},
                {"name": "RequestId", "type": "string"},
            ]
        },
        "DeleteFooRequest": {"members": [{"name": "FooId", "type": "string"}]},
        "DeleteFooResponse": {"members": [{"name": "RequestId", "type": "string"}]},
    },
}


def _make_services_dir(tmp: Path) -> Path:
    services = tmp / "services"
    prod = services / "cvm" / "v20200101"
    prod.mkdir(parents=True)
    (prod / "api.json").write_text(json.dumps(FIXTURE_API_JSON), encoding="utf-8")
    # unmapped product — must be skipped gracefully
    other = services / "notmapped" / "v20200101"
    other.mkdir(parents=True)
    (other / "api.json").write_text(json.dumps({"actions": {}}), encoding="utf-8")
    return services


class ParseApiJsonTest(unittest.TestCase):
    def setUp(self) -> None:
        self.flags, self.schemas, self.counts = kbs.parse_api_json(FIXTURE_API_JSON)

    def test_flag_variants_cover_both_conventions(self) -> None:
        flags = set(self.flags["DescribeFoos"])
        # StoppedMode → flat and kebab forms both present
        self.assertIn("stoppedmode", flags)
        self.assertIn("stopped-mode", flags)
        self.assertIn("fooids", flags)

    def test_response_data_field_from_list_member(self) -> None:
        schema = self.schemas["DescribeFoos"]
        self.assertEqual(schema["data_field"], "Response.FooSet")
        self.assertEqual(schema["request_id"], "Response.RequestId")

    def test_no_list_member_means_empty_data_field(self) -> None:
        self.assertEqual(self.schemas["DeleteFoo"]["data_field"], "")

    def test_counts_non_vacuous(self) -> None:
        self.assertEqual(self.counts["actions_total"], 2)
        self.assertEqual(self.counts["actions_covered"], 2)


class SyncTest(unittest.TestCase):
    def test_sync_maps_skill_and_skips_unmapped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            services = _make_services_dir(Path(tmp))
            payload = kbs.sync(services)
            self.assertIn("qcloud-cvm-ops", payload["flags"])
            self.assertNotIn("qcloud-notmapped-ops", payload["flags"])
            cov = payload["coverage"]["qcloud-cvm-ops"]
            self.assertEqual(cov["actions_covered"], 2)

    def test_write_and_check_roundtrip_and_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            services = _make_services_dir(Path(tmp))
            out = Path(tmp) / "shared"
            payload = kbs.sync(services)
            kbs.write_kbs(payload, out)
            self.assertTrue(kbs.kbs_match(payload, out))
            # mutate on-disk KB → drift detected
            stale = json.loads((out / kbs.FLAGS_FILE).read_text())
            stale["qcloud-cvm-ops"].pop("DeleteFoo")
            (out / kbs.FLAGS_FILE).write_text(json.dumps(stale))
            self.assertFalse(kbs.kbs_match(payload, out))


class ValidatorWiringTest(unittest.TestCase):
    """Validators must consume the generated KB via TCLOUD_KB_DIR."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        services = _make_services_dir(tmp)
        out = tmp / "shared"
        payload = kbs.sync(services)
        kbs.write_kbs(payload, out)
        self._old_env = dict(__import__("os").environ)
        __import__("os").environ["TCLOUD_KB_DIR"] = str(out)

    def tearDown(self) -> None:
        __import__("os").environ.clear()
        __import__("os").environ.update(self._old_env)
        self._tmp.cleanup()

    def test_cli_validator_uses_generated_flags(self) -> None:
        # DescribeFoos exists ONLY in the generated KB; a bogus flag must be caught.
        violations = cli_param_validator.validate_cli_params(
            "tccli cvm DescribeFoos --limit 20 --bogus-flag x"
        )
        flagged = [v["flag"] for v in violations]
        self.assertIn("bogus-flag", flagged)
        self.assertNotIn("limit", flagged)

    def test_schema_validator_uses_generated_schemas(self) -> None:
        # Missing RequestId on a generated-only action must be flagged.
        violations = schema_validator.validate_response_schema(
            "tccli cvm DeleteFoo", {"Response": {}}
        )
        self.assertTrue(violations, "generated schema must validate DeleteFoo response")


if __name__ == "__main__":
    unittest.main()
