#!/usr/bin/env python3
"""Aggregate incident-state.jsonl into a per-incident lifecycle table.

Reads ``audit-results/incident-state.jsonl`` (or a positional path argument),
replays each incident's action log through the IncidentStateMachine and prints a
table of incident_id | state | mttd | mtta | mttr | dwell ...

Usage:
  python3 scripts/incident_state_aggregate.py
  python3 scripts/incident_state_aggregate.py path/to/incident-state.jsonl

Exit codes: 0 on success, 1 on missing/unreadable file or parse error.
Stdlib-only.
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

from copilot.incident_state import (
    IncidentRecord,
    IncidentState,
    dwell_stats,
    replay,
)

DEFAULT_PATH = ROOT / "audit-results" / "incident-state.jsonl"
_DWELL_STATES = ("detected", "correlated", "diagnosed", "mitigating", "verifying", "resolved")


def load_records(path: Path) -> list[dict]:
    """读取 JSONL，逐行解析；任一解析失败即抛异常（调用方转 exit 1）。"""
    if not path.exists():
        raise FileNotFoundError(f"incident state file not found: {path}")
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


def _final_record(record: dict) -> IncidentRecord:
    """从一条 incident 记录回放其 action_log 得到最终状态。

    若记录顶层携带 ``detected_at``/``severity``，则种子化到回放记录，使
    dwell/mttd 统计精确（动作日志本身无 DETECT 事件）。
    """
    incident_id = record.get("incident_id", "unknown")
    action_log = record.get("action_log") or []
    if not action_log:
        return IncidentRecord(
            incident_id=incident_id,
            state=IncidentState.DETECTED,
            severity=str(record.get("severity", "P1")),
            detected_at=record.get("detected_at"),
        )
    rec = replay(
        action_log,
        incident_id=incident_id,
        severity=str(record.get("severity", "P1")),
        detected_at=record.get("detected_at"),
    )
    return rec


def print_table(rows: list[tuple[str, str, dict[str, float]]]) -> None:
    header = (
        f"{'incident_id':16} {'state':12} {'mttd(m)':>9} {'mtta(m)':>9} "
        f"{'mttr(m)':>9}" + "".join(f" {s:>9}" for s in _DWELL_STATES)
    )
    print(header)
    print("-" * len(header))
    for incident_id, state, stats in rows:
        dwell_cells = "".join(f" {stats.get(s, 0.0):9.2f}" for s in _DWELL_STATES)
        print(
            f"{incident_id:16} {state:12} {stats['mttd_min']:9.2f} "
            f"{stats['mtta_min']:9.2f} {stats['mttr_min']:9.2f}{dwell_cells}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", type=Path, default=DEFAULT_PATH,
        help="Path to incident-state.jsonl (default: audit-results/incident-state.jsonl)",
    )
    args = parser.parse_args()

    try:
        records = load_records(args.path)
    except (FileNotFoundError, OSError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    rows: list[tuple[str, str, dict[str, float]]] = []
    for record in records:
        rec = _final_record(record)
        stats = dwell_stats(rec)
        rows.append((rec.incident_id, rec.state.value, stats))

    print(f"# incident lifecycle — {len(records)} records")
    print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
