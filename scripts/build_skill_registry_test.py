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
                           capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads((ROOT / "audit-results" / "skill-registry.json").read_text())
        self.assertGreaterEqual(data["count"], 30)
        for s in data["skills"]:
            self.assertIn("name", s)
            self.assertIn("cli_applicability", s)
            self.assertIn("intent_keywords", s)

    def test_intent_keywords_populated(self):
        data = json.loads((ROOT / "audit-results" / "skill-registry.json").read_text())
        with_keywords = [s["name"] for s in data["skills"] if s.get("intent_keywords")]
        self.assertTrue(with_keywords, "expected at least one skill with populated intent_keywords")
        # a skill whose description uses backticks must yield intent_keywords
        kw_skill = next(s for s in data["skills"] if s.get("intent_keywords"))
        self.assertTrue(kw_skill["intent_keywords"],
                        f"{kw_skill['name']} should have intent_keywords")


if __name__ == "__main__":
    unittest.main()
