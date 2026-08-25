#!/usr/bin/env python3
"""reflexion_efficacy.py — Measure whether Reflexion hint injection actually prevents failures.

Closes the memory-efficacy gap: gcl_runner.py records ``injection_id`` and
``matched_failure_keys[]`` in each trace's ``preflight_reflexion`` block; this
script correlates injections with outcomes across traces.

Metrics (JSON):
  runs_total             traces scanned
  runs_with_injection    traces that carried ≥1 failure-pattern hint
  hint_coverage          runs_with_injection / runs_total (None if no traces)
  patterns               per failure-pattern key:
                           injected_runs, failed_after_injection,
                           recurred_runs, prevention_rate (None when not injectable)
  non_vacuous            true iff ≥1 injected run was found (L8 guard)

Recurrence rule: after an injected run, a LATER trace of the same skill whose
final status != PASS and whose failure text contains the normalized pattern
error keyword counts as a recurrence for that pattern key.

CLI usage::

    python3 scripts/reflexion_efficacy.py                 # summary to stderr
    python3 scripts/reflexion_efficacy.py --json          # report to stdout
    python3 scripts/reflexion_efficacy.py --out PATH      # also write report file
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE_DIR = ROOT / "audit-results"

_KEYWORD_LEN = 40


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def load_traces(trace_dir: Path) -> list[dict[str, Any]]:
    """Load GCL traces oldest-first (by filename timestamp)."""
    traces: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(trace_dir.glob("gcl-trace-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"WARN: skip {path}: {exc}", file=sys.stderr)
            continue
        if isinstance(data, dict) and "skill" in data and "final" in data:
            traces.append((path.name, data))
    return [t for _, t in sorted(traces)]


def _failure_text(trace: dict[str, Any]) -> str:
    parts: list[str] = []
    for it in trace.get("iterations") or []:
        gen = it.get("generator") or {}
        excerpt = gen.get("result_excerpt")
        if excerpt:
            parts.append(str(excerpt))
        if gen.get("exit_code") not in (0, None):
            parts.append(json.dumps(gen.get("args") or {}, ensure_ascii=False))
    out = (trace.get("final") or {}).get("output")
    if out:
        parts.append(str(out))
    return _normalize(" ".join(parts))


def compute_report(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Pure computation over loaded traces (unit-testable)."""
    runs_with_injection = 0
    patterns: dict[str, dict[str, Any]] = {}

    # Index later failures per skill: list of failure texts in time order.
    events: list[tuple[int, str, str]] = []  # (index, skill, failure_text)
    for idx, trace in enumerate(traces):
        pre = trace.get("preflight_reflexion") or {}
        keys = pre.get("matched_failure_keys") or []
        if pre.get("injection_id") and keys:
            runs_with_injection += 1
        status = (trace.get("final") or {}).get("status", "")
        if status != "PASS":
            events.append((idx, trace.get("skill", ""), _failure_text(trace)))

    for idx, trace in enumerate(traces):
        pre = trace.get("preflight_reflexion") or {}
        keys = pre.get("matched_failure_keys") or []
        if not (pre.get("injection_id") and keys):
            continue
        skill = trace.get("skill", "")
        for key in keys:
            slot = patterns.setdefault(
                key,
                {
                    "injected_runs": 0,
                    "failed_after_injection": 0,
                    "recurred_runs": 0,
                    "prevention_rate": None,
                },
            )
            slot["injected_runs"] += 1
            keyword = _normalize(key.split("|")[-1])[:_KEYWORD_LEN]
            if not keyword:
                continue
            # immediate outcome of THIS run
            status = (trace.get("final") or {}).get("status", "")
            if status != "PASS":
                slot["failed_after_injection"] += 1
            # recurrence in any LATER failing run of the same skill
            if any(
                e_idx > idx and e_skill == skill and keyword in e_text
                for e_idx, e_skill, e_text in events
            ):
                slot["recurred_runs"] += 1
            if slot["injected_runs"] > 0:
                slot["prevention_rate"] = round(
                    1 - slot["recurred_runs"] / slot["injected_runs"], 3
                )

    total = len(traces)
    report = {
        "schema_version": "v1",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runs_total": total,
        "runs_with_injection": runs_with_injection,
        "hint_coverage": round(runs_with_injection / total, 3) if total else None,
        "patterns": patterns,
        "non_vacuous": runs_with_injection > 0,
    }
    # Self-check (L5/L8): an injected-run corpus MUST produce observable metrics;
    # empty corpora are valid but explicitly marked vacuous.
    if runs_with_injection:
        assert report["hint_coverage"] is not None and report["hint_coverage"] > 0
        assert all(p["injected_runs"] > 0 for p in patterns.values())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--trace-dir", type=str, default=str(DEFAULT_TRACE_DIR))
    parser.add_argument("--json", action="store_true", help="print JSON report to stdout")
    parser.add_argument("--out", type=str, default=None, help="also write report to PATH")
    args = parser.parse_args()

    traces = load_traces(Path(args.trace_dir))
    report = compute_report(traces)

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
        print(f"report written: {out_path}", file=sys.stderr)

    if args.json:
        print(payload)
    else:
        print(
            f"runs={report['runs_total']} injected={report['runs_with_injection']} "
            f"coverage={report['hint_coverage']} "
            f"patterns={len(report['patterns'])} non_vacuous={report['non_vacuous']}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
