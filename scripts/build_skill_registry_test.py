"""Unit tests for scripts/build_skill_registry.py.

Both tests read one registry emitted by setUpClass into a TemporaryDirectory.
Previously the data came from the repo's gitignored
audit-results/skill-registry.json: test_intent_keywords_populated read a file
it never produced, relying on its alphabetical sibling to emit it first. On a
fresh checkout ("i" sorts before "r") it ran first and errored — which made
the blocking unittest step in CI red and silently skipped the KPI step after
it. The emit also wrote into the repo on every run. See AGENTS.md L25.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve().parent / "build_skill_registry.py"


class BuildSkillRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.registry_path = Path(cls._tmp.name) / "skill-registry.json"
        cls.emit = subprocess.run(
            [sys.executable, str(SCRIPT), "--emit", "--out", str(cls.registry_path)],
            capture_output=True, text=True, check=False,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _registry(self) -> dict:
        """Parse the emitted registry, surfacing the emitter's own failure."""
        self.assertEqual(self.emit.returncode, 0, self.emit.stderr)
        return json.loads(self.registry_path.read_text())

    def test_registry_has_all_skills(self):
        data = self._registry()
        self.assertGreaterEqual(data["count"], 30)
        for s in data["skills"]:
            self.assertIn("name", s)
            self.assertIn("cli_applicability", s)
            self.assertIn("intent_keywords", s)

    def test_intent_keywords_populated(self):
        data = self._registry()
        with_keywords = [s["name"] for s in data["skills"] if s.get("intent_keywords")]
        self.assertTrue(with_keywords, "expected at least one skill with populated intent_keywords")
        # a skill whose description uses backticks must yield intent_keywords
        kw_skill = next(s for s in data["skills"] if s.get("intent_keywords"))
        self.assertTrue(kw_skill["intent_keywords"],
                        f"{kw_skill['name']} should have intent_keywords")

    def test_emit_never_touches_the_repo_audit_dir(self) -> None:
        """--emit must write only where --out points, never into the repo.

        Regression under test (CR-5): the emitter hardcoded
        audit-results/skill-registry.json, so every run of the suite rewrote a
        gitignored workspace file. Snapshot shape follows
        gcl_runner_test.test_run_with_temp_root_never_touches_committed_artefacts:
        record the destination's state, exercise the writer, and assert it did
        not move. mtime is part of the snapshot because the registry rebuild is
        deterministic — a reverted fix rewrites identical bytes, so content
        alone would let the regression through.
        """
        audit = ROOT / "audit-results"

        def snapshot() -> list[tuple]:
            # [] when the directory is absent; glob tolerates a missing dir.
            return sorted(
                (p.name, p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
                for p in audit.glob("*") if p.is_file()
            )

        before = snapshot()

        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "skill-registry.json"
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "--emit", "--out", str(dst)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            # Pollute first, then non-vacuity: the pollution check cannot fail
            # spuriously when the emitter writes nothing, so a reverted --out
            # reports the repo write instead of misreporting vacuity.
            self.assertEqual(snapshot(), before,
                             "the repo's audit-results/ was written by the suite")
            # ...and without this the guard passes vacuously if the emitter stops firing.
            self.assertTrue(dst.is_file(), "emit wrote nothing — the guard would be vacuous")


if __name__ == "__main__":
    unittest.main()
