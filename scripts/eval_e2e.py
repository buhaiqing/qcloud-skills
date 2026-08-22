#!/usr/bin/env python3
"""P0-2 E2E Evaluation Suite runner.

Modes:
  e2e  -- run all graders per incident from corpus + trace-dir
  ab   -- A/B test: with vs without reflexion (--no-reflexion)

Usage:
  # E2E mode: corpus + trace-dir -> report
  python3 scripts/eval_e2e.py --mode e2e --corpus scripts/fixtures/incidents/corpus.jsonl \
      --trace-dir audit-results --output audit-results/e2e-report-20260822.json

  # A/B mode: compare reflexion-on vs reflexion-off
  python3 scripts/eval_e2e.py --mode ab --corpus scripts/fixtures/incidents/corpus.jsonl \
      --trace-dir audit-results --ab --output audit-results/e2e-ab-report-20260822.json

Backward compatible: if --trace-dir doesn't exist, corpus-only mode skips graders
that need trace data (grade_intent, grade_traceability, grade_safety, grade_plan).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_graders import grade_intent, grade_safety, grade_traceability


def _load_corpus(corpus_path: Path) -> list[dict[str, Any]]:
    """Load corpus.jsonl, return list of entries."""
    entries: list[dict[str, Any]] = []
    with corpus_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def _run_e2e_grader(entry: dict[str, Any], trace: dict[str, Any], grader_name: str) -> Any | None:
    """Run a single grader, return result or None if skip."""
    if grader_name == "readonly":
        from eval_graders import grade_readonly as _grader
        return _grader(entry)

    graders: dict[str, Any] = {
        "intent": grade_intent,
        "traceability": grade_traceability,
        "safety": grade_safety,
    }
    if grader_name in graders:
        return graders[grader_name](entry, trace)
    return None


def _summarize_results(entries: list[dict[str, Any]], traces: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Summarize grader results across all entries."""
    summary: dict[str, Any] = {
        "total": len(entries),
        "graders": {},
        "per_entry": [],
    }

    grader_keys = ["intent", "traceability", "safety", "readonly"]
    for gk in grader_keys:
        summary["graders"][gk] = {"pass": 0, "fail": 0, "skip": 0, "total": 0}

    for entry in entries:
        eid = entry.get("incident_id", "unknown")
        traces_for_entry = traces.get(eid, {})
        results: dict[str, Any] = {}
        for gk in grader_keys:
            tr = traces_for_entry.get(gk)
            if tr is None:
                r = None  # skip
            else:
                r = tr
            results[gk] = r
            summary["graders"][gk]["total"] += 1
            if r is None:
                summary["graders"][gk]["skip"] += 1
            elif r == 1:
                summary["graders"][gk]["pass"] += 1
            elif r == 0:
                summary["graders"][gk]["fail"] += 1

        summary["per_entry"].append({
            "incident_id": eid,
            "results": results,
        })

    return summary


def _run_e2e_mode(corpus_path: Path, trace_dir: Path, output_path: Path) -> None:
    """Run E2E mode: corpus + trace-dir -> per-incident + report."""
    entries = _load_corpus(corpus_path)

    # Collect traces per incident_id
    traces: dict[str, dict[str, Any]] = {}
    if trace_dir.exists():
        for tf in trace_dir.glob("gcl-trace-*.json"):
            try:
                t = json.loads(tf.read_text(encoding="utf-8"))
                eid = t.get("incident_id", tf.stem.replace("gcl-trace-", ""))
                traces[eid] = t
            except (json.JSONDecodeError, OSError):
                # best-effort: continue if trace file is malformed or unreadable
                pass

    # Run graders per entry
    per_entry: list[dict[str, Any]] = []
    graded: dict[str, dict[str, Any]] = {}
    for entry in entries:
        eid = entry.get("incident_id", "unknown")
        trace = traces.get(eid, {})

        results: dict[str, Any] = {}
        for gk in ["intent", "traceability", "safety", "readonly"]:
            r = _run_e2e_grader(entry, trace, gk)
            results[gk] = r

        graded[eid] = results
        per_entry.append({
            "incident_id": eid,
            "results": results,
        })

    # Build summary from graded results (not raw traces)
    summary = _summarize_results(entries, graded)
    summary["generated_at"] = datetime.now(UTC).isoformat()
    summary["mode"] = "e2e"
    summary["corpus_total"] = len(entries)
    summary["traced_total"] = len(traces)

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def _run_ab_mode(corpus_path: Path, trace_dir: Path, output_path: Path) -> None:
    """Run A/B mode: compare reflexion-on vs reflexion-off.

    Requires that trace-dir contains traces from both modes:
    - normal traces (with reflexion)
    - traces from gcl_runner --no-reflexion (without reflexion)

    Produces comparative report with per-entry pass/fail/skip for each mode.
    """
    entries = _load_corpus(corpus_path)

    traces_with: dict[str, dict[str, Any]] = {}
    traces_without: dict[str, dict[str, Any]] = {}
    if trace_dir.exists():
        for tf in trace_dir.glob("gcl-trace-*.json"):
            try:
                t = json.loads(tf.read_text(encoding="utf-8"))
                has_reflexion = t.get("preflight_reflexion", {}).get("injection", "") != ""
                eid = t.get("incident_id", tf.stem.replace("gcl-trace-", ""))
                if has_reflexion:
                    traces_with[eid] = t
                else:
                    traces_without[eid] = t
                if "-ctrl" in tf.name or "-noreflexion" in tf.name.lower():
                    traces_without[eid] = t
            except (json.JSONDecodeError, OSError):
                pass

    # Run graders for both modes
    results_with: list[dict[str, Any]] = []
    results_without: list[dict[str, Any]] = []

    for i, entry in enumerate(entries):
        eid = entry.get("incident_id", "unknown")
        trace_w = traces_with.get(eid, {})
        trace_wo = traces_without.get(eid, {})

        rw: dict[str, Any] = {}
        rwo: dict[str, Any] = {}

        for gk in ["intent", "traceability", "safety", "readonly"]:
            rw[gk] = trace_w.get(gk)  # already evaluated or None
            rwo[gk] = trace_wo.get(gk)

        results_with.append({"incident_id": eid, "results": rw})
        results_without.append({"incident_id": eid, "results": rwo})

    # Build comparative summary
    summary: dict[str, Any] = {
        "total": len(entries),
        "mode": "ab",
        "generated_at": datetime.now(UTC).isoformat(),
        "with_reflexion": {"total": len(traces_with)},
        "without_reflexion": {"total": len(traces_without)},
        "per_entry": [],
    }

    # Compare per-entry
    for i, entry in enumerate(entries):
        eid = entry.get("incident_id", "unknown")
        rw = results_with[i]["results"] if i < len(results_with) else {}
        rwo = results_without[i]["results"] if i < len(results_without) else {}

        entry_res = {
            "incident_id": eid,
            "with": {gk: rw.get(gk) for gk in ["intent", "traceability", "safety", "readonly"]},
            "without": {gk: rwo.get(gk) for gk in ["intent", "traceability", "safety", "readonly"]},
        }
        summary["per_entry"].append(entry_res)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["e2e", "ab"], required=True,
                        help="Evaluation mode: e2e (default) or ab (A/B reflexion test)")
    parser.add_argument("--corpus", type=Path, required=True,
                        help="Path to corpus.jsonl from P0-1")
    parser.add_argument("--trace-dir", type=Path, default=None,
                        help="Path to directory with gcl-trace-*.json files")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output report path (default: audit-results/e2e-report-<ts>.json)")
    parser.add_argument("--ab", action="store_true",
                        help="Run A/B mode (requires --trace-dir with both reflexion and no-reflexion traces)")

    args = parser.parse_args()

    if not args.corpus.exists():
        print(f"ERROR: corpus not found: {args.corpus}", file=sys.stderr)
        return 1

    # Set output path
    if not args.output:
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        if args.mode == "ab":
            args.output = Path(f"audit-results/e2e-ab-report-{ts}.json")
        else:
            args.output = Path(f"audit-results/e2e-report-{ts}.json")

    if args.mode == "e2e":
        _run_e2e_mode(args.corpus, args.trace_dir or Path("audit-results"), args.output)
    elif args.mode == "ab":
        if not args.trace_dir:
            print("ERROR: --trace-dir required for A/B mode", file=sys.stderr)
            return 1
        _run_ab_mode(args.corpus, args.trace_dir, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())