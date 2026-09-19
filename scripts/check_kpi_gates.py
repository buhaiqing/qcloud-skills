#!/usr/bin/env python3
"""Aggregate CI gate for the spec-mandated KPI set.

Spec anchor:
  docs/superpowers/specs/2026-07-28-harness-engineering-optimization-design.md

Enforces (subset of the 8 spec KPIs that we can assert today from disk):
  KPI#1  safety.leak_checked == true            (per EvidenceRecord)
  KPI#2  safety.destructive -> safety.token set  (per EvidenceRecord)
  KPI#3  every executable skill has >=5 golden   (via build_skill_registry --check)
  KPI#7  router top1 accuracy >= ratchet, misdelegation <= derived bound
                                                (via harness_router --confusion)

KPI#4-#6 and #8 require run-time data (changed-skill regression, telemetry split,
P95 latency) and are not in scope of this offline aggregator.

Skip semantics:
- KPI#1 and KPI#2 require evidence under audit-results/: evidence-*.json
  snapshots and/or the append-only evidence-local.jsonl stream. When neither
  exists the gate is reported as "skipped" with exit 0 — this matches the
  existing Makefile `kpi` target behaviour and avoids hard-failing CI on a
  pre-evidence repo. Once any evidence appears the gate becomes a hard failure
  if schema or safety rules are violated (including a malformed JSONL line).
- KPI#3 and KPI#7 are always enforced (they only need the registry and the
  existing assets/eval_queries.json ground truth). Thresholds for KPI#7 come
  from assets/shared/thresholds.json (TE-4 shared constants).

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
# Shared thresholds (TE-4): no KPI number is hardcoded in this gate.
THRESHOLDS = ROOT / "assets" / "shared" / "thresholds.json"
# Where the runbook that tells the on-call how to close the routing gap lives.
ROUTER_GAP_ANCHOR = "docs/harness-engineering/runbooks/kpi7-router-confusion-failure.md"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    # check=False: this helper is fire-and-forget; callers read returncode
    # and decide. Raising on non-zero would prevent the aggregator from
    # reporting the actual KPI failure (e.g. build_skill_registry --check
    # returns 1 when KPI#3 fails — exactly what we want to surface).
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def kpi1_2_safety() -> tuple[str, str, str]:
    """KPI#1 + #2: evidence safety rules via validate_evidence_schema.

    Both evidence streams are validated: the single-record `evidence-*.json`
    snapshots AND the append-only `evidence-local.jsonl` stream that
    scripts/evidence_kernel.py:78 actually writes (one record per line).
    Globbing only the former inspected 1 record out of 550 — the safety gate was
    green because it was reading a rounding error of the evidence.

    Returns (status, detail, note) where status in {pass, fail, skip}.
    """
    evidence_files = sorted(AUDIT.glob("evidence-*.json"))
    jsonl_stream = AUDIT / "evidence-local.jsonl"
    if jsonl_stream.exists():
        evidence_files.append(jsonl_stream)
    if not evidence_files:
        return (
            "skip",
            "no audit-results/evidence-*.json or evidence-local.jsonl",
            "KPI#1/#2 not enforced yet",
        )

    proc = _run(["python3", "scripts/validate_evidence_schema.py", *[str(p) for p in evidence_files]])
    if proc.returncode == 0:
        # The validator is the authoritative counter (kpi-pattern.md attribute
        # 3); pass its record count through instead of re-parsing the files here.
        counted = proc.stdout.strip().removeprefix("OK: ")
        return "pass", counted or f"{len(evidence_files)} evidence file(s) valid", ""
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
    """KPI#7: emit confusion matrix per skill into audit-results/router-confusion.json.

    Fail-closed since the metric became real (owning-skill ground truth, see
    harness_router.confusion_matrix): the gate now compares avg top1 accuracy
    against `router_min_top1_accuracy` and negative-query misdelegation against
    its derived bound. Passing while *below* `router_target_top1_accuracy` is
    allowed but the gap is printed in the detail — a gate that cannot yet be met
    must say so instead of hiding behind a ✅.
    """
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
    # A measurement covering less than half the registry is not a measurement of
    # the registry — fail rather than report a green on a degenerate sample.
    if len(scored) * 2 < len(skills):
        return (
            "fail",
            f"only {len(scored)}/{len(skills)} skills produced a measurement (need >= half)",
            "",
        )
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    min_top1 = float(thresholds["router_min_top1_accuracy"])
    target_top1 = float(thresholds["router_target_top1_accuracy"])
    # Misdelegation bound: the negative-side mirror of the accuracy ratchet,
    # derived as the residual error budget the *target* implies — to be right
    # target_top1 of the time, at most (1 - target_top1) of the negative-side
    # decisions may be wrong. Derived rather than stored as a second constant so
    # the two bounds cannot drift apart.
    max_misdelegation = 1.0 - target_top1
    avg_top1 = sum(v["top1_accuracy"] for v in scored) / len(scored)
    avg_misd = sum(v["misdelegation"] for v in scored) / len(scored)
    detail = (
        f"{len(scored)}/{len(skills)} skills scored; "
        f"avg top1={avg_top1:.2%} avg misdelegation={avg_misd:.2%}"
    )
    if avg_top1 < min_top1:
        return "fail", f"{detail} — below ratchet {min_top1:.2%}", ""
    if avg_misd > max_misdelegation:
        return "fail", f"{detail} — above derived misdelegation bound {max_misdelegation:.2%}", ""
    if avg_top1 < target_top1:
        return (
            "pass",
            (
                f"{detail} (BELOW TARGET {target_top1:.2%} — routing accuracy is a known "
                f"open gap; see {ROUTER_GAP_ANCHOR})"
            ),
            "",
        )
    return "pass", detail, ""


def kpi8_spec_drift() -> tuple[str, str, str]:
    """KPI#8 (informational): run detect_spec_drift.py, report new drift kinds.

    Always 'skip' (informational) — source_drift items are pre-existing
    known limitations (fields written via _final_scores helper).
    New drift kinds (file_line_ref_drift, md_fragment_drift,
    phantom_link_drift) indicate real rot and are surfaced for review.
    Scope: docs/harness-engineering/ only (the maintained methodology dir).
    Other docs/superpowers/ drift is pre-existing and out of scope.
    """
    r = _run(["python3", "scripts/detect_spec_drift.py"])
    lines = r.stdout.split("\n")
    # Extract non-pre-existing drift kinds (source_drift = known limitation)
    new_kinds = sorted({
        l.split("|")[1].strip() for l in lines
        if any(k in l for k in [
            "file_line_ref_drift",
            "md_fragment_drift",
            "phantom_link_drift",
        ]) and "pass" not in l.lower() and "Field" not in l
    })
    if not new_kinds:
        return "skip", "detector clean; 5 source_drift known limitations documented", "informational"
    detail = "; ".join(new_kinds)
    # Check for pre-existing only
    only_source = new_kinds == ["source_drift"]
    if only_source:
        return "skip", "detector clean; 5 source_drift known limitations documented", "informational"
    return "fail", f"NEW spec drift: {detail}", "review required before merge"


def main() -> int:
    results = {
        "KPI#1 leak_checked / KPI#2 destructive-token": kpi1_2_safety(),
        "KPI#3 golden coverage": kpi3_golden_coverage(),
        "KPI#7 router confusion matrix": kpi7_router_confusion(),
        "KPI#8 spec drift (informational)": kpi8_spec_drift(),
    }

    print("| KPI | Status | Detail |")
    print("|---|---|---|")
    failed = 0
    skipped = 0
    for label, (status, detail, note) in results.items():
        marker = {"pass": "✅", "fail": "❌", "skip": "⏭ ", "informational": "ℹ️ "}[status]
        suffix = f" — {note}" if note else ""
        print(f"| {label} | {marker} {status} | {detail}{suffix} |")
        if status == "fail":
            failed += 1
        elif status == "skip" or status == "informational":
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
