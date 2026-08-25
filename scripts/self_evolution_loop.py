#!/usr/bin/env python3
"""self_evolution_loop.py — Close the self-evolution loop end-to-end.

Wires the last mile of the maturity roadmap:

    skill_quality_score.upgrade_signal
        → root-cause selection (docs/failure-patterns* layers)
        → golden regression gate (frontmatter bump/required checks + Layer-1/2 KB load)
        → FixProposal (conservative documentation-level remediation)
        → SelfHealPRWorkflow.run_workflow (branch → commit → PR → CI → merge)

The generated change is deliberately conservative: append a remediation entry to
the owning skill's ``references/troubleshooting.md``. Automatic code generation
is out of scope for this phase; the PR carries the diagnosis for human review.

CLI usage::

    python3 scripts/self_evolution_loop.py --dry-run          # no network/git side effects
    python3 scripts/self_evolution_loop.py --max-skills 3     # default 5

Exit codes: 0 nothing-to-do / all proposals succeeded; 1 any failure or gate block.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import skill_quality_score
from _failure_pattern_store import load_all_layers
from self_heal_pr_workflow import FixProposal, SelfHealPRWorkflow


@dataclass
class LoopOutcome:
    """Per-skill result of one loop iteration."""

    skill: str
    status: str  # "pr_created" | "pr_merged" | "dry_run" | "skipped_no_pattern" | "skipped_no_target" | "skipped_duplicate" | "gate_failed" | "failed"
    detail: str


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def pick_root_cause(skill: str) -> dict[str, Any] | None:
    """Highest-count failure pattern for a skill across hot/warm/cold layers."""
    best: dict[str, Any] | None = None
    for layer in load_all_layers():
        for key, pattern in (layer or {}).items():
            if not key.startswith(f"{skill}|"):
                continue
            if best is None or int(pattern.get("count", 0)) > int(best.get("count", 0)):
                best = {**pattern, "_key": key}
    return best


def _remediation_block(skill: str, pattern: dict[str, Any]) -> str:
    error = str(pattern.get("error", "")).replace("\n", " ")
    fix = str(pattern.get("fix", "")).replace("\n", " ")
    return (
        f"\n### Self-evolution remediation {_today()}\n\n"
        f"- **Signal**: skill_quality_score upgrade_signal (quality below threshold)\n"
        f"- **Root cause pattern**: `{pattern.get('_key', '')}` "
        f"(count={pattern.get('count', 0)})\n"
        f"- **Error**: {error}\n"
        f"- **Prevention**: {fix}\n"
        f"- **Source**: scripts/self_evolution_loop.py — review before relying on this entry\n"
    )


def default_golden_gate(root: Path) -> tuple[bool, str]:
    """Regression gate that must pass BEFORE any PR is created.

    1. Whole-repo SKILL.md frontmatter validation (bump/required fields).
    2. Layer-1 flag KB loads (generated or hand-maintained fallback).
    """
    import cli_param_validator
    import validate_skills_frontmatter

    if validate_skills_frontmatter.main([]) != 0:
        return False, "frontmatter gate failed"
    if not cli_param_validator._load_extended():
        return False, "Layer-1 flag KB empty (neither generated nor built-in)"
    return True, "golden gate passed"


class SelfEvolutionLoop:
    def __init__(
        self,
        root: Path = ROOT,
        dry_run: bool = False,
        max_skills: int = 5,
        gate_fn: Callable[[Path], tuple[bool, str]] | None = None,
        workflow_fn: Callable[[FixProposal], Any] | None = None,
    ):
        self.root = root
        self.dry_run = dry_run
        self.max_skills = max_skills
        self.gate_fn = gate_fn or default_golden_gate
        self.workflow_fn = workflow_fn

    def run(self, report_override: dict[str, Any] | None = None) -> dict[str, Any]:
        report = report_override or skill_quality_score.build_report(self.root)
        signals = list((report or {}).get("upgrade_signal") or [])[: self.max_skills]
        outcomes = [self._process_skill(skill) for skill in signals]
        failed = [o for o in outcomes if o.status in ("failed", "gate_failed")]
        return {
            "schema_version": "v1",
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dry_run": self.dry_run,
            "signals": signals,
            "outcomes": [
                {"skill": o.skill, "status": o.status, "detail": o.detail} for o in outcomes
            ],
            "ok": not failed,
        }

    def _troubleshooting_path(self, skill: str) -> Path | None:
        candidate = self.root / skill / "references" / "troubleshooting.md"
        return candidate if candidate.is_file() else None

    def _build_proposal(
        self, skill: str, pattern: dict[str, Any]
    ) -> tuple[FixProposal | None, str]:
        target = self._troubleshooting_path(skill)
        if target is None:
            return None, f"{skill}/references/troubleshooting.md missing"
        old = target.read_text(encoding="utf-8")
        error_kw = str(pattern.get("error", ""))[:40].strip()
        if error_kw and error_kw in old:
            return None, "duplicate remediation already present"
        new = old.rstrip("\n") + "\n" + _remediation_block(skill, pattern)
        proposal = FixProposal(
            level="L2",
            skill=skill,
            error_code=error_kw or "unknown",
            occurrence_count=int(pattern.get("count", 0)),
            target_file=str(target),
            old_content=old,
            new_content=new,
            rationale=(
                f"quality score below threshold; top recurring failure pattern "
                f"`{pattern.get('_key', '')}` (count={pattern.get('count', 0)})"
            ),
            risk_assessment="documentation-only change to references/troubleshooting.md",
            auto_merge=False,
        )
        return proposal, "proposal built"

    def _process_skill(self, skill: str) -> LoopOutcome:
        pattern = pick_root_cause(skill)
        if pattern is None:
            return LoopOutcome(skill, "skipped_no_pattern", "no recurring failure pattern found")

        proposal, detail = self._build_proposal(skill, pattern)
        if proposal is None:
            return LoopOutcome(skill, "skipped_no_target" if "missing" in detail else "skipped_duplicate", detail)

        ok, gate_detail = self.gate_fn(self.root)
        if not ok:
            return LoopOutcome(skill, "gate_failed", gate_detail)

        if self.dry_run:
            return LoopOutcome(skill, "dry_run", f"{gate_detail}; proposal ready (no side effects)")

        try:
            workflow = self.workflow_fn or (
                lambda p: SelfHealPRWorkflow(repo_path=str(self.root)).run_workflow(p)
            )
            result = workflow(proposal)
            status = "pr_merged" if getattr(result, "status", "") == "merged" else (
                "pr_created" if getattr(result, "status", "") == "created" else "failed"
            )
            return LoopOutcome(skill, status, str(getattr(result, "message", "")))
        except Exception as exc:  # noqa: BLE001 — loop must isolate per-skill failures
            return LoopOutcome(skill, "failed", f"{type(exc).__name__}: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true",
                        help="build proposals and run gates without git/network side effects")
    parser.add_argument("--max-skills", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    loop = SelfEvolutionLoop(root=args.root.resolve(), dry_run=args.dry_run,
                             max_skills=args.max_skills)
    summary = loop.run()
    print(json_dumps(summary) if args.json else _human(summary))
    return 0 if summary["ok"] else 1


def json_dumps(summary: dict[str, Any]) -> str:
    import json
    return json.dumps(summary, ensure_ascii=False, indent=2)


def _human(summary: dict[str, Any]) -> str:
    lines = [f"self-evolution loop: dry_run={summary['dry_run']} ok={summary['ok']}"]
    for o in summary["outcomes"]:
        lines.append(f"  [{o['status']}] {o['skill']}: {o['detail'][:90]}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
