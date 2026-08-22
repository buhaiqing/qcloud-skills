#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import synthesize_incident_corpus as syn


class TestSynthesize(unittest.TestCase):
    def test_output_meets_coverage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "corpus.jsonl"
            result = syn.synthesize(_HERE.parent, out, per_skill=1)
            self.assertGreaterEqual(result["total"], 20)
            self.assertGreaterEqual(result["skills"], 5)
            self.assertEqual(set(result["severities"]), {"info", "warning", "critical"})
            lines = [l for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
            self.assertEqual(len(lines), result["total"])
            for line in lines:
                entry = json.loads(line)
                for field in ["incident_id", "skill", "request", "command", "severity", "source"]:
                    self.assertIn(field, entry)
                self.assertTrue(entry["command"].startswith("tccli "))
                self.assertRegex(entry["command"].split()[2], r"^(Describe|List|Get|Inquiry)")

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out1 = Path(tmpdir) / "c1.jsonl"
            out2 = Path(tmpdir) / "c2.jsonl"
            syn.synthesize(_HERE.parent, out1, per_skill=1)
            syn.synthesize(_HERE.parent, out2, per_skill=1)
            self.assertEqual(out1.read_text(encoding="utf-8"), out2.read_text(encoding="utf-8"))

    def test_existing_corpus_valid(self):
        corpus = _HERE / "fixtures" / "incidents" / "corpus.jsonl"
        if not corpus.exists():
            self.skipTest("corpus not generated")
        entries = [json.loads(l) for l in corpus.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertGreaterEqual(len(entries), 20)
        self.assertGreaterEqual(len({e["skill"] for e in entries}), 5)
        for e in entries:
            self.assertTrue(e["command"].startswith("tccli "))
            self.assertRegex(e["command"].split()[2], r"^(Describe|List|Get|Inquiry)")


if __name__ == "__main__":
    unittest.main()
