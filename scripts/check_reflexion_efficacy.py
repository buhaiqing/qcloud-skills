#!/usr/bin/env python3
"""check_reflexion_efficacy.py — Fail-closed CI gate for the Reflexion memory loop.

Exit codes
  0  non_vacuous AND runs_with_injection >= reflexion_min_injected_runs
  1  vacuous corpus (no traces with injection) — the reflexion loop is not being exercised
  2  configuration error (missing threshold key or manifest)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_DIR = ROOT / "audit-results"
THRESHOLDS = ROOT / "assets" / "shared" / "thresholds.json"
MANIFEST = ROOT / "assets" / "shared" / "validation_commands.yaml"


def load_thresholds() -> dict:
    try:
        return json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"CONFIG ERROR: cannot read thresholds: {exc}", file=sys.stderr)
        sys.exit(2)


def load_efficacy_report() -> dict:
    import subprocess

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "reflexion_efficacy.py"), "--json"],
        capture_output=True, text=True, timeout=60,
    )
    # The script always exits 0; JSON is on stdout.
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # Empty corpus → no JSON output; treat as vacuous
        return {}


def main() -> int:
    thresholds = load_thresholds()
    min_injected = thresholds.get("reflexion_min_injected_runs")

    if min_injected is None:
        print(
            "CONFIG ERROR: reflexion_min_injected_runs not found in thresholds.json",
            file=sys.stderr,
        )
        return 2

    report = load_efficacy_report()
    runs_total = report.get("runs_total", 0)
    runs_with_injection = report.get("runs_with_injection", 0)
    non_vacuous = report.get("non_vacuous", False)
    hint_coverage = report.get("hint_coverage")

    print(
        f"reflexion_efficacy  runs_total={runs_total}  "
        f"runs_with_injection={runs_with_injection}  "
        f"hint_coverage={hint_coverage}  non_vacuous={non_vacuous}  "
        f"threshold_min_injected={min_injected}",
        file=sys.stderr,
    )

    if not non_vacuous:
        print(
            "GATE FAIL: reflexion loop is vacuous (0 traces with injection). "
            "Ensure GCL traces carry failure-pattern hints — "
            "the memory loop is not being exercised.",
            file=sys.stderr,
        )
        return 1

    if runs_with_injection < min_injected:
        print(
            f"GATE FAIL: runs_with_injection={runs_with_injection} "
            f"< reflexion_min_injected_runs={min_injected}. "
            "The reflexion memory loop is exercised below the minimum threshold.",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: reflexion_efficacy  hint_coverage={hint_coverage}  "
        f"injected_runs={runs_with_injection}/{min_injected}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
