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


if __name__ == "__main__":
    from unittest import main

    main()
