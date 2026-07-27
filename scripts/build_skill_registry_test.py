import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve().parent / "build_skill_registry.py"


class BuildSkillRegistryTest(unittest.TestCase):
    def test_registry_has_all_skills(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--emit"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads((ROOT / "audit-results" / "skill-registry.json").read_text())
        self.assertGreaterEqual(data["count"], 30)
        for s in data["skills"]:
            self.assertIn("name", s)
            self.assertIn("cli_applicability", s)
            self.assertIn("intent_keywords", s)


if __name__ == "__main__":
    unittest.main()
