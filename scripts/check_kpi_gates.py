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

Evidence semantics (changed in round 2 — round 1 skipped when the stream was
empty, which made truncating the stream *improve* the verdict):
- KPI#1 and KPI#2 read every `audit-results/evidence-*.json*` file: the
  single-record snapshots, the append-only `evidence-local.jsonl` stream and the
  per-run `evidence-<run_id>.jsonl` files scripts/evidence_kernel.py writes.
- The gate FAILS when no evidence file exists, and when fewer than
  `evidence_min_records` *fresh* records were read (`evidence_max_age_days`
  window; see validate_evidence_schema.py). Zero evidence is not evidence.
- Only `GATE_REQUIRE_EVIDENCE=0` restores the old "skip" behaviour, for a repo
  that is deliberately evidence-free (CI: the evidence stream is machine-local
  and gitignored, so `validate-skills.yml` runs the gate with that escape and
  says so in its step name).
- KPI#3 and KPI#7 are always enforced (they only need the registry and the
  existing assets/eval_queries.json ground truth). Thresholds come from
  assets/shared/thresholds.json (TE-4 shared constants).

Exit codes:
  0 = all enforceable KPIs pass (or are skipped with informational note)
  1 = one or more enforced KPIs failed
  2 = internal error: the gate's own configuration (assets/shared/thresholds.json)
      is missing or malformed. Reported separately from 1 so CI does not announce
      a KPI regression when the real fault is a broken threshold file.

Output: a Markdown table on stdout so the Makefile target can pipe to console
without JSON parsing; audit-results/kpi-gate-report.json is also emitted for
trend tracking.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit-results"

# Spec-required ground-truth file already produced by build_skill_registry --emit
REGISTRY = AUDIT / "skill-registry.json"
EVAL_QUERIES_GLOB = "assets/eval_queries.json"  # relative to each skill dir
# Shared thresholds (TE-4). The ratchet values live here rather than in this
# module — but note the file ships in the same tree the gate grades, so a PR can
# move its own floor: see kpi-pattern.md § "The ratchet is self-referential".
THRESHOLDS = ROOT / "assets" / "shared" / "thresholds.json"
# Where the runbook that tells the on-call how to close the routing gap lives.
ROUTER_GAP_ANCHOR = "docs/harness-engineering/runbooks/kpi7-router-confusion-failure.md"


class GateConfigError(Exception):
    """The gate's own configuration is unusable (missing/malformed thresholds).

    Distinct from a KPI failure on purpose: main() maps this to exit 2, so a
    broken thresholds.json cannot masquerade as "one or more enforced KPIs
    failed", which is what an uncaught exception (exit 1) told the on-call.
    """


def _thresholds() -> dict:
    try:
        return json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GateConfigError(f"{THRESHOLDS}: cannot read ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise GateConfigError(f"{THRESHOLDS}: invalid JSON ({exc})") from exc


def _threshold(cfg: dict, key: str) -> float:
    try:
        return float(cfg[key])
    except KeyError as exc:
        raise GateConfigError(f"{THRESHOLDS}: missing key {key!r}") from exc
    except (TypeError, ValueError) as exc:
        raise GateConfigError(
            f"{THRESHOLDS}: key {key!r} must be a number, got {cfg[key]!r}"
        ) from exc


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    # check=False: this helper is fire-and-forget; callers read returncode
    # and decide. Raising on non-zero would prevent the aggregator from
    # reporting the actual KPI failure (e.g. build_skill_registry --check
    # returns 1 when KPI#3 fails — exactly what we want to surface).
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def kpi1_2_safety() -> tuple[str, str, str]:
    """KPI#1 + #2: evidence safety rules via validate_evidence_schema.

    Every `audit-results/evidence-*.json*` file is validated: the single-record
    `.json` snapshots AND the per-run `.jsonl` streams that
    scripts/evidence_kernel.py writes (one record per line, named
    `evidence-<run_id>.jsonl` — the round-1 glob `evidence-*.json` could not
    match those at all, so the fleet's real evidence was never read).

    Fail-closed on emptiness: a missing stream, or fewer than
    `evidence_min_records` records inside the `evidence_max_age_days` window, is
    a FAIL. Round 1 returned "skip" (and the validator returned rc 0) for an
    empty stream, so truncating the evidence improved the verdict.
    `GATE_REQUIRE_EVIDENCE=0` is the documented escape for an evidence-free repo
    (used by CI, whose evidence stream is machine-local and gitignored).

    Returns (status, detail, note) where status in {pass, fail, skip}.
    """
    if os.environ.get("GATE_REQUIRE_EVIDENCE") == "0":
        return (
            "skip",
            "GATE_REQUIRE_EVIDENCE=0 — evidence stream is machine-local/untracked here",
            "KPI#1/#2 not enforced in this environment",
        )
    cfg = _thresholds()  # GateConfigError -> exit 2, not a KPI failure
    min_records = int(_threshold(cfg, "evidence_min_records"))
    max_age_days = _threshold(cfg, "evidence_max_age_days")
    evidence_files = sorted(AUDIT.glob("evidence-*.json*"))
    if not evidence_files:
        return (
            "fail",
            (
                f"no evidence stream under {AUDIT.name}/ (need >= {min_records} fresh"
                f" record(s)); set GATE_REQUIRE_EVIDENCE=0 only if this repo is"
                f" deliberately evidence-free"
            ),
            "",
        )

    proc = _run([
        "python3", "scripts/validate_evidence_schema.py",
        "--min-records", str(min_records),
        "--max-age-days", f"{max_age_days:g}",
        *[str(p) for p in evidence_files],
    ])
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
    harness_router.confusion_matrix): the gate compares avg top1 accuracy against
    the `router_min_top1_accuracy` ratchet and negative-query misdelegation
    against the `router_max_misdelegation` ceiling. Both bounds are set from the
    *measured* baseline (the same reference), while `router_target_top1_accuracy`
    is the aspirational goal whose gap is printed on every run — a gate that
    cannot yet be met must say so instead of hiding behind a ✅.

    Both arms are averaged over *scoreable* skills only: a skill whose registry
    frontmatter has empty `intent_keywords` can never be returned by
    select_top1, so it scores a structural 0.0 on top1 and 0.0 on misdelegation
    no matter what the router does. 15 of 31 skills are in that state; averaging
    them in reported misdelegation 7.85% over a fleet whose movable skills sit at
    15.21%, and set a bound the movable skills could never trip. Every skill left
    out of the average is named in the detail, so a green row still shows what it
    did not measure.
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
    # A skill the router can never return (empty intent_keywords) contributes a
    # structural zero to both arms; it is a registry-frontmatter gap, not a
    # routing measurement, so it is excluded and named instead of averaged in.
    keyworded = {s["name"]: bool(s.get("intent_keywords")) for s in registry.get("skills", [])}
    scoreable = [
        (skill, v) for skill, v in aggregate.items()
        if isinstance(v, dict) and "top1_accuracy" in v and keyworded.get(skill)
    ]
    unmeasured = sorted(set(skills) - {skill for skill, _ in scoreable})
    # A measurement covering less than half the registry is not a measurement of
    # the registry — fail rather than report a green on a degenerate sample.
    if len(scoreable) * 2 < len(skills):
        return (
            "fail",
            (
                f"only {len(scoreable)}/{len(skills)} skills are scoreable (need >= half);"
                f" unmeasured: {', '.join(unmeasured) or 'none'}"
            ),
            "",
        )
    # Reference per arm, stated because they are not mirrors: the top1 arm
    # ratchets at the measured baseline (`router_min_top1_accuracy`, a floor) and
    # the misdelegation arm at its own measured baseline
    # (`router_max_misdelegation`, a ceiling). Both come from the same
    # measurement, so the two arms cannot drift apart; the aspirational
    # `router_target_top1_accuracy` is only used to print the gap.
    cfg = _thresholds()
    min_top1 = _threshold(cfg, "router_min_top1_accuracy")
    max_misdelegation = _threshold(cfg, "router_max_misdelegation")
    target_top1 = _threshold(cfg, "router_target_top1_accuracy")
    top1_arm = [v["top1_accuracy"] for _, v in scoreable if v["top1_accuracy"] is not None]
    misd_arm = [v["misdelegation"] for _, v in scoreable if v["misdelegation"] is not None]
    if not top1_arm or not misd_arm:
        return (
            "fail",
            (
                f"unmeasurable arms: {len(top1_arm)} skill(s) with positives,"
                f" {len(misd_arm)} with negatives (need >= 1 of each)"
            ),
            "",
        )
    avg_top1 = sum(top1_arm) / len(top1_arm)
    avg_misd = sum(misd_arm) / len(misd_arm)
    detail = (
        f"{len(scoreable)}/{len(skills)} skills scored; "
        f"avg top1={avg_top1:.2%} avg misdelegation={avg_misd:.2%}; "
        f"unmeasured: {', '.join(unmeasured) or 'none'}"
    )
    if avg_top1 < min_top1:
        return "fail", f"{detail} — below ratchet {min_top1:.2%}", ""
    if avg_misd > max_misdelegation:
        return "fail", f"{detail} — above misdelegation ceiling {max_misdelegation:.2%}", ""
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
    try:
        results = {
            "KPI#1 leak_checked / KPI#2 destructive-token": kpi1_2_safety(),
            "KPI#3 golden coverage": kpi3_golden_coverage(),
            "KPI#7 router confusion matrix": kpi7_router_confusion(),
            "KPI#8 spec drift (informational)": kpi8_spec_drift(),
        }
    except GateConfigError as exc:
        # Exit 2, not 1: a broken gate configuration is not a KPI regression, and
        # the on-call must not be paged for a threshold file that will not parse.
        print(f"GATE CONFIG ERROR: {exc}")
        return 2

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
