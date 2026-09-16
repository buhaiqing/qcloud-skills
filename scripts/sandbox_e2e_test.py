"""TDD tests for scripts/sandbox_e2e.py.

Validates golden-scenario matching against fixtures via the subprocess CLI,
per lesson L1 (unittest.TestCase discovery) and L5 (assert populated values).
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]


class SandboxE2ETest(TestCase):
    def _write_skill_dir(self, fixture: dict, golden: dict) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="sandbox_e2e_"))
        fixture_dir = tmp / "fixtures"
        golden_dir = tmp / "golden"
        fixture_dir.mkdir()
        golden_dir.mkdir()
        (fixture_dir / "describe_instances.json").write_text(json.dumps(fixture))
        (golden_dir / "list.json").write_text(json.dumps(golden))
        return tmp

    def test_golden_match_passes(self) -> None:
        fixture = {
            "Response": {"TotalCount": 1, "InstanceSet": [{"InstanceId": "ins-abc123"}]}
        }
        golden = {
            "intent": "list CVM instances",
            "expected": {
                "fixture": "fixtures/describe_instances.json",
                "assertions": [
                    {"path": "$.Response.InstanceSet[0].InstanceId", "op": "exists"}
                ],
            },
        }
        skill_dir = self._write_skill_dir(fixture, golden)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sandbox_e2e.py"), "--skill-dir", str(skill_dir)],
            capture_output=True,
            text=True,
        check=False)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_golden_mismatch_fails(self) -> None:
        fixture = {"Response": {"InstanceSet": []}}
        golden = {
            "intent": "list CVM instances",
            "expected": {
                "fixture": "fixtures/describe_instances.json",
                "assertions": [
                    {"path": "$.Response.InstanceSet[0].InstanceId", "op": "exists"}
                ],
            },
        }
        skill_dir = self._write_skill_dir(fixture, golden)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sandbox_e2e.py"), "--skill-dir", str(skill_dir)],
            capture_output=True,
            text=True,
        check=False)
        self.assertNotEqual(result.returncode, 0, msg=result.stderr)

    def test_seed_fixture_null_skips(self) -> None:
        """P1-1: seed files with _seed:true and fixture:null exit 0 (SKIP, not MISMATCH)."""
        golden = {
            "_seed": True,
            "_seed_generator": "generate_golden_seeds.py",
            "_seed_skill": "qcloud-test-ops",
            "_seed_action_verb": "describe",
            "intent": "Describe one resource by id",
            "input": {
                "action": "<REPLACE_WITH_REAL_TCCLI_ACTION_FOR_DESCRIBE>",
                "region": "{{env.TENCENTCLOUD_REGION}}",
            },
            "expected": {
                "fixture": None,
                "assertions": [{"path": "$.Response", "op": "exists"}],
            },
        }
        tmp = Path(tempfile.mkdtemp(prefix="sandbox_seed_"))
        golden_dir = tmp / "golden"
        golden_dir.mkdir()
        (golden_dir / "seed_describe_one.json").write_text(json.dumps(golden))
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sandbox_e2e.py"), "--skill-dir", str(tmp)],
            capture_output=True,
            text=True,
        check=False)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("GOLDEN OK", result.stdout)
        self.assertNotIn("GOLDEN MISMATCH", result.stdout)


if __name__ == "__main__":
    from unittest import main

    main()
