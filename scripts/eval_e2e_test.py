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

import eval_e2e


def _write_corpus(path: Path, entries: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


class TestLoadCorpus(unittest.TestCase):
    def test_loads_jsonl(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.jsonl"
            _write_corpus(p, [{"incident_id": "a"}, {"incident_id": "b"}])
            entries = eval_e2e._load_corpus(p)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["incident_id"], "a")

    def test_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.jsonl"
            p.write_text('\n{"incident_id": "a"}\n\n', encoding="utf-8")
            self.assertEqual(len(eval_e2e._load_corpus(p)), 1)


class TestRunE2EGrader(unittest.TestCase):
    def test_readonly_uses_entry_only(self):
        entry = {"command": "tccli cvm DescribeInstances"}
        # trace is ignored for readonly grader
        self.assertEqual(eval_e2e._run_e2e_grader(entry, {}, "readonly"), 1)

    def test_intent_uses_trace(self):
        entry = {"expected_intent": "reboot"}
        trace = {"intent": "reboot"}
        self.assertEqual(eval_e2e._run_e2e_grader(entry, trace, "intent"), 1)

    def test_unknown_grader_returns_none(self):
        self.assertIsNone(eval_e2e._run_e2e_grader({}, {}, "nope"))


class TestSummarizeResults(unittest.TestCase):
    def test_counts_pass_fail_skip(self):
        entries = [{"incident_id": "a"}, {"incident_id": "b"}]
        traces = {
            "a": {"intent": 1, "traceability": 0, "safety": 1, "readonly": 1},
            "b": {"intent": None, "traceability": 1, "safety": 0, "readonly": None},
        }
        summary = eval_e2e._summarize_results(entries, traces)
        g = summary["graders"]
        self.assertEqual(g["intent"]["pass"], 1)
        self.assertEqual(g["intent"]["skip"], 1)
        self.assertEqual(g["traceability"]["fail"], 1)
        self.assertEqual(g["traceability"]["pass"], 1)
        self.assertEqual(g["safety"]["pass"], 1)
        self.assertEqual(g["safety"]["fail"], 1)
        self.assertEqual(g["readonly"]["pass"], 1)
        self.assertEqual(g["readonly"]["skip"], 1)
        self.assertEqual(len(summary["per_entry"]), 2)


class TestRunE2EMode(unittest.TestCase):
    def test_e2e_writes_report(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            corpus = d / "corpus.jsonl"
            _write_corpus(corpus, [
                {"incident_id": "a", "expected_intent": "reboot", "command": "tccli cvm DescribeInstances"},
            ])
            trace_dir = d / "traces"
            trace_dir.mkdir()
            (trace_dir / "gcl-trace-a.json").write_text(json.dumps({
                "incident_id": "a", "intent": "reboot",
            }), encoding="utf-8")
            out = d / "report.json"

            eval_e2e._run_e2e_mode(corpus, trace_dir, out)
            self.assertTrue(out.exists())
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "e2e")
            self.assertEqual(report["corpus_total"], 1)
            self.assertEqual(report["traced_total"], 1)
            self.assertEqual(report["graders"]["intent"]["pass"], 1)


class TestRunABMode(unittest.TestCase):
    def test_ab_splits_reflexion(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            corpus = d / "corpus.jsonl"
            _write_corpus(corpus, [{"incident_id": "a"}])
            trace_dir = d / "traces"
            trace_dir.mkdir()
            (trace_dir / "gcl-trace-a.json").write_text(json.dumps({
                "incident_id": "a",
                "preflight_reflexion": {"injection": "some-injection"},
            }), encoding="utf-8")
            (trace_dir / "gcl-trace-a-ctrl.json").write_text(json.dumps({
                "incident_id": "a",
                "preflight_reflexion": {"injection": ""},
            }), encoding="utf-8")
            out = d / "ab.json"

            eval_e2e._run_ab_mode(corpus, trace_dir, out)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "ab")
            self.assertEqual(report["with_reflexion"]["total"], 1)
            self.assertEqual(report["without_reflexion"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
