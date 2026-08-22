#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import incident_replay


def _valid_entry(incident_id="inc-cvm-001", skill="qcloud-cvm-ops", command="tccli cvm DescribeInstances --limit 5 --output json"):
    return {
        "incident_id": incident_id,
        "skill": skill,
        "request": "List CVM instances",
        "command": command,
        "severity": "info",
        "source": "eval_queries",
    }


class TestValidateEntry(unittest.TestCase):
    def test_valid_passes(self):
        ok, reason = incident_replay.validate_entry(_valid_entry())
        self.assertTrue(ok, reason)

    def test_missing_field(self):
        e = _valid_entry()
        del e["skill"]
        ok, reason = incident_replay.validate_entry(e)
        self.assertFalse(ok)
        self.assertIn("missing field", reason)

    def test_invalid_incident_id(self):
        ok, _ = incident_replay.validate_entry(_valid_entry(incident_id="bad id"))
        self.assertFalse(ok)

    def test_non_tccli_command(self):
        ok, reason = incident_replay.validate_entry(_valid_entry(command="echo hello"))
        self.assertFalse(ok)
        self.assertIn("tccli", reason)

    def test_non_readonly_action_rejected(self):
        ok, reason = incident_replay.validate_entry(_valid_entry(command="tccli cvm DeleteInstances --ids ins-xxx"))
        self.assertFalse(ok)
        self.assertIn("read-only", reason)

    def test_destructive_verb_rejected(self):
        ok, reason = incident_replay.validate_entry(_valid_entry(command="tccli cvm DescribeInstances --filter delete"))
        self.assertFalse(ok)
        self.assertIn("destructive", reason)

    def test_invalid_skill(self):
        ok, _ = incident_replay.validate_entry(_valid_entry(skill="not-a-skill"))
        self.assertFalse(ok)

    def test_all_fixture_corpus_passes_whitelist(self):
        corpus = _HERE / "fixtures" / "incidents" / "corpus.jsonl"
        if not corpus.exists():
            self.skipTest("corpus not generated yet")
        for line in corpus.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            ok, reason = incident_replay.validate_entry(entry)
            self.assertTrue(ok, f"{entry['incident_id']}: {reason}")


class TestLoadCorpus(unittest.TestCase):
    def test_load_valid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
            fh.write(json.dumps(_valid_entry("inc-cvm-001")) + "\n")
            fh.write(json.dumps(_valid_entry("inc-cvm-002")) + "\n")
            path = Path(fh.name)
        try:
            entries = incident_replay.load_corpus(path)
            self.assertEqual(len(entries), 2)
        finally:
            path.unlink(missing_ok=True)

    def test_duplicate_incident_id_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
            fh.write(json.dumps(_valid_entry("inc-dup-001")) + "\n")
            fh.write(json.dumps(_valid_entry("inc-dup-001")) + "\n")
            path = Path(fh.name)
        try:
            with self.assertRaises(ValueError):
                incident_replay.load_corpus(path)
        finally:
            path.unlink(missing_ok=True)

    def test_invalid_json_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
            fh.write("not json\n")
            path = Path(fh.name)
        try:
            with self.assertRaises(ValueError):
                incident_replay.load_corpus(path)
        finally:
            path.unlink(missing_ok=True)


class TestDryRun(unittest.TestCase):
    def test_clean_corpus_dry_run_exit_0(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
            fh.write(json.dumps(_valid_entry("inc-cvm-001")) + "\n")
            fh.write(json.dumps(_valid_entry("inc-cbs-002", skill="qcloud-cbs-ops", command="tccli cbs DescribeDisks --limit 5 --output json")) + "\n")
            corpus = Path(fh.name)
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.json"
            orig = sys.argv
            sys.argv = ["incident_replay.py", "--corpus", str(corpus), "--mode", "dry-run", "--summary", str(summary)]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = incident_replay.main()
            finally:
                sys.argv = orig
            self.assertEqual(rc, 0)
            data = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(data["total"], 2)
            self.assertEqual(data["rejected"], 0)
            self.assertEqual(data["validated"], 2)
        corpus.unlink(missing_ok=True)

    def test_destructive_entry_dry_run_exit_2(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
            fh.write(json.dumps(_valid_entry(command="tccli cvm DeleteInstances --ids ins-xxx")) + "\n")
            corpus = Path(fh.name)
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.json"
            orig = sys.argv
            sys.argv = ["incident_replay.py", "--corpus", str(corpus), "--mode", "dry-run", "--summary", str(summary)]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = incident_replay.main()
            finally:
                sys.argv = orig
            self.assertEqual(rc, 2)
            data = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(data["rejected"], 1)
        corpus.unlink(missing_ok=True)

    def test_summary_traced_equals_len_minus_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
            fh.write(json.dumps(_valid_entry("inc-cvm-001")) + "\n")
            fh.write(json.dumps(_valid_entry(command="tccli cvm DeleteInstances --ids ins-xxx", incident_id="inc-cvm-002")) + "\n")
            fh.write(json.dumps(_valid_entry("inc-cvm-003")) + "\n")
            corpus = Path(fh.name)
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.json"
            orig = sys.argv
            sys.argv = ["incident_replay.py", "--corpus", str(corpus), "--mode", "dry-run", "--summary", str(summary)]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    incident_replay.main()
            finally:
                sys.argv = orig
            data = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(data["total"], 3)
            self.assertEqual(data["rejected"], 1)
            self.assertEqual(data["validated"], 2)
        corpus.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
