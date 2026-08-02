#!/usr/bin/env python3
"""Aggregate quality-feedback.jsonl into a per-dimension quality table.

Reads ``audit-results/quality-feedback.jsonl`` (or a positional path argument),
calls ``compute_metrics`` and prints a dimension table.

Usage:
  python3 scripts/quality_feedback_aggregate.py
  python3 scripts/quality_feedback_aggregate.py path/to/quality-feedback.jsonl
  python3 scripts/quality_feedback_aggregate.py path/to/quality-feedback.jsonl --by model

Exit codes: 0 on success, 1 on missing/unreadable file or parse error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys_path = str(ROOT / "qcloud-copilot")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from copilot.quality.feedback import compute_metrics

DEFAULT_PATH = ROOT / "audit-results" / "quality-feedback.jsonl"
VALID_DIMS = ("rule", "model", "product", "tenant_id")


def load_records(path: Path) -> list[dict]:
    """读取 JSONL，逐行解析；任一解析失败即抛异常（调用方转 exit 1）。"""
    if not path.exists():
        raise FileNotFoundError(f"quality feedback file not found: {path}")
    records: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"parse error at line {lineno}: {e}") from e
    return records


def print_table(metrics_by_dim: dict[str, object], by: str) -> None:
    header = (
        f"{by:24} {'precision':>9} {'recall':>9} {'noise':>9} {'late':>9} "
        f"{'mttd(h)':>9} {'confirm(m)':>10} {'calib':>9} {'n':>5}"
    )
    print(header)
    print("-" * len(header))
    for dim, m in metrics_by_dim.items():
        print(
            f"{dim:24} {m.precision:9.3f} {m.recall:9.3f} {m.noise_rate:9.3f} "
            f"{m.late_rate:9.3f} {m.avg_mttd_hours:9.2f} {m.avg_confirm_mins:10.1f} "
            f"{m.calibration_error:9.3f} {m.n:5}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", type=Path, default=DEFAULT_PATH,
        help="Path to quality-feedback.jsonl (default: audit-results/quality-feedback.jsonl)",
    )
    parser.add_argument(
        "--by", default="rule", choices=VALID_DIMS,
        help="Grouping dimension (default: rule)",
    )
    args = parser.parse_args()

    try:
        records = load_records(args.path)
    except (FileNotFoundError, OSError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    metrics_by_dim = compute_metrics(records, by=args.by)
    print(f"# quality feedback ({args.by}) — {len(records)} records")
    print_table(metrics_by_dim, args.by)
    return 0


if __name__ == "__main__":
    sys.exit(main())
