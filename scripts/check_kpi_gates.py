#!/usr/bin/env python3
"""Aggregate CI gate for the spec-mandated KPI set.

Spec anchor:
  docs/superpowers/specs/2026-07-28-harness-engineering-optimization-design.md

Enforces (subset of the 8 spec KPIs that we can assert today from disk):
  KPI#1  safety.leak_checked == true            (per EvidenceRecord)
  KPI#2  safety.destructive -> safety.token set  (per EvidenceRecord)
  KPI#3  every executable skill has >=5 golden   (via build_skill_registry --check)
  KPI#7  router top1 accuracy / misdelegation / fallback observable
                                                (via harness_router --confusion)

KPI#4-#6 and #8 require run-time data (changed-skill regression, telemetry split,
P95 latency) and are not in scope of this offline aggregator.

Skip semantics:
- KPI#1 and KPI#2 require evidence-*.json files under audit-results/. When no
  such files exist the gate is reported as "skipped" with exit 0 — this matches
  the existing Makefile `kpi` target behaviour and avoids hard-failing CI on a
  pre-evidence repo. Once any evidence file appears the gate becomes a hard
  failure if schema or safety rules are violated.
- KPI#3 and KPI#7 are always enforced (they only need the registry and the
  existing assets/eval_queries.json ground truth).

Exit codes:
  0 = all enforceable KPIs pass (or are skipped with informational note)
  1 = one or more enforced KPIs failed
  2 = internal error (missing files the gate itself depends on)

Output: a Markdown table on stdout so the Makefile target can pipe to console
without JSON parsing; audit-results/kpi-gate-report.json is also emitted for
trend tracking.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit-results"

# Spec-required ground-truth file already produced by build_skill_registry --emit
REGISTRY = AUDIT / "skill-registry.json"
EVAL_QUERIES_GLOB = "assets/eval_queries.json"  # relative to each skill dir


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    # check=False: this helper is fire-and-forget; callers read returncode
    # and decide. Raising on non-zero would prevent the aggregator from
    # reporting the actual KPI failure (e.g. build_skill_registry --check
    # returns 1 when KPI#3 fails — exactly what we want to surface).
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def kpi1_2_safety() -> tuple[str, str, str]:
    """KPI#1 + #2: evidence safety rules via validate_evidence_schema.

    Returns (status, detail, note) where status in {pass, fail, skip}.
    """
    evidence_files = sorted(AUDIT.glob("evidence-*.json"))
    if not evidence_files:
        return "skip", "no audit-results/evidence-*.json", "KPI#1/#2 not enforced yet"

    proc = _run(["python3", "scripts/validate_evidence_schema.py", *[str(p) for p in evidence_files]])
    if proc.returncode == 0:
        return "pass", f"{len(evidence_files)} evidence file(s) valid", ""
    if proc.returncode == 1:
        return "fail", proc.stdout.strip()[:500], ""
    return "fail", f"validate_evidence_schema exit={proc.returncode}: {proc.stderr.strip()[:200]}", ""


def kpi3_golden_coverage() -> tuple[str, str, str]:
    """KPI#3: >=5 parseable golden per executable skill."""
    proc = _run(["python3", "scripts/build_skill_registry.py", "--check"])
    if proc.returncode == 0:
        return "pass", "all executable skills have >=5 golden scenarios", ""
    return "fail", proc.stdout.strip()[:600] or proc.stderr.strip()[:200], ""


def kpi7_router_confusion() -> tuple[str, str, str]:
    """KPI#7: emit confusion matrix per skill into audit-results/router-confusion.json."""
    if not REGISTRY.exists():
        # Auto-build the registry rather than requiring a prior step in the pipeline.
        emit = _run(["python3", "scripts/build_skill_registry.py", "--emit"])
        if emit.returncode != 0:
            return "fail", f"build_skill_registry --emit failed: {emit.stderr.strip()[:200]}", ""
    if not REGISTRY.exists():
        return "fail", f"missing {REGISTRY.name} after --emit", ""
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    skills = [s["name"] for s in registry.get("skills", [])]

    # Import the router module directly to avoid spawning 31 subprocesses.
    sys.path.insert(0, str(ROOT / "scripts"))
    import harness_router  # type: ignore[import-not-found]

    aggregate: dict[str, dict] = {}
    for skill in skills:
        eval_path = ROOT / skill / "eval_queries.json"
        if not eval_path.exists():
            eval_path = ROOT / skill / "assets" / "eval_queries.json"
        if not eval_path.exists():
            aggregate[skill] = {"skipped": "no eval_queries.json"}
            continue
        eval_queries = json.loads(eval_path.read_text(encoding="utf-8"))
        aggregate[skill] = harness_router.confusion_matrix(registry, eval_queries, skill)

    AUDIT.mkdir(exist_ok=True)
    (AUDIT / "router-confusion.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    scored = [v for v in aggregate.values() if isinstance(v, dict) and "top1_accuracy" in v]
    if not scored:
        return "fail", "no skill produced a confusion matrix (missing eval_queries.json everywhere)", ""
    avg_top1 = sum(v["top1_accuracy"] for v in scored) / len(scored)
    avg_misd = sum(v["misdelegation"] for v in scored) / len(scored)
    return (
        "pass",
        f"{len(scored)}/{len(skills)} skills scored; avg top1={avg_top1:.2%} avg misdelegation={avg_misd:.2%}",
        "",
    )


def main() -> int:
    results = {
        "KPI#1 leak_checked / KPI#2 destructive-token": kpi1_2_safety(),
        "KPI#3 golden coverage": kpi3_golden_coverage(),
        "KPI#7 router confusion matrix": kpi7_router_confusion(),
    }

    print("| KPI | Status | Detail |")
    print("|---|---|---|")
    failed = 0
    skipped = 0
    for label, (status, detail, note) in results.items():
        marker = {"pass": "✅", "fail": "❌", "skip": "⏭ "}[status]
        suffix = f" — {note}" if note else ""
        print(f"| {label} | {marker} {status} | {detail}{suffix} |")
        if status == "fail":
            failed += 1
        elif status == "skip":
            skipped += 1

    AUDIT.mkdir(exist_ok=True)
    (AUDIT / "kpi-gate-report.json").write_text(
        json.dumps(
            {label: {"status": s, "detail": d, "note": n} for label, (s, d, n) in results.items()},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    if failed:
        print(f"\nKPI GATES FAIL: {failed} enforced KPI(s) failed")
        return 1
    print(f"\nKPI GATES PASS: enforced KPIs green; {skipped} skipped (informational)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
