#!/usr/bin/env python3
"""GCL Orchestrator (Phase 2) — Generator execution loop with external Critic injection.

Implements the **Orchestrator (O)** role from AGENTS.md GCL spec. Generator runs
`tccli`/shell commands; Critic scores MUST come from an **isolated** context via
``--critic-json`` or stdin — this script never self-scores as Critic in production mode.

Usage:
  python3 scripts/gcl_runner.py run \\
    --skill qcloud-cvm-ops \\
    --request "List CVM instances read-only" \\
    --command 'tccli cvm DescribeInstances --Region ap-guangzhou' \\
    [--max-iter 2] \\
    [--critic-json path/to/critic.json]

  # Rule-based structural audit only (CI / dry-run; NOT a substitute for isolated Critic):
  python3 scripts/gcl_runner.py run ... --structural-critic-only

Trace output: ``audit-results/gcl-trace-YYYYMMDD-HHMMSS.json``
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Per AGENTS.md §8 defaults (override via --max-iter)
SKILL_MAX_ITER: dict[str, int] = {
    "qcloud-cvm-ops": 2,
    "qcloud-cdb-ops": 2,
    "qcloud-clb-ops": 2,
    "qcloud-cos-ops": 2,
    "qcloud-es-ops": 2,
    "qcloud-redis-ops": 2,
    "qcloud-tke-ops": 2,
    "qcloud-vpc-ops": 2,
    "qcloud-cam-ops": 2,
    "qcloud-cbs-ops": 2,
    "qcloud-ckafka-ops": 2,
    "qcloud-mongodb-ops": 2,
    "qcloud-postgres-ops": 2,
    "qcloud-cdn-ops": 3,
    "qcloud-cls-ops": 3,
    "qcloud-scf-ops": 3,
    "qcloud-ssl-ops": 3,
    "qcloud-agsx-ops": 3,
    "qcloud-monitor-ops": 3,
    "qcloud-finops-ops": 3,
    "qcloud-proactive-inspection": 3,
    "qcloud-well-architected-review": 5,
    "qcloud-aiops-diagnosis": 5,
    "qcloud-skill-generator": 3,
}

RUBRIC_THRESHOLDS: dict[str, float] = {
    "correctness": 0.5,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5,
}

SECRET_PATTERNS = [
    re.compile(r"SecretKey\s*=\s*[^<\s][^\s\"']+", re.I),
    re.compile(r"TENCENTCLOUD_SECRET_KEY\s*=\s*[^\s\"']+", re.I),
    re.compile(r"AKID[A-Za-z0-9]{20,}"),
]


def mask_secrets(text: str) -> str:
    out = text
    out = re.sub(r"(SecretKey\s*=\s*)([^\s\"']+)", r"\1<masked>", out, flags=re.I)
    out = re.sub(r"(TENCENTCLOUD_SECRET_KEY\s*=\s*)([^\s\"']+)", r"\1<masked>", out, flags=re.I)
    return out


def has_credential_leak(text: str) -> bool:
    if "<masked>" in text:
        return False
    return any(p.search(text) for p in SECRET_PATTERNS)


def run_command(command: str, timeout: int = 120) -> dict[str, Any]:
    """Execute generator command; capture exit code and masked output."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        masked = mask_secrets(combined)
        excerpt = masked[:2000] + ("..." if len(masked) > 2000 else "")
        return {
            "command": mask_secrets(command),
            "exit_code": proc.returncode,
            "result_excerpt": excerpt,
            "stdout_len": len(proc.stdout or ""),
            "stderr_len": len(proc.stderr or ""),
        }
    except subprocess.TimeoutExpired:
        return {
            "command": mask_secrets(command),
            "exit_code": -1,
            "result_excerpt": f"TIMEOUT after {timeout}s",
            "stdout_len": 0,
            "stderr_len": 0,
        }


def structural_critic(generator: dict[str, Any]) -> dict[str, Any]:
    """Rule-based structural audit — for CI/dry-run only, not production Critic."""
    scores: dict[str, float] = {}
    suggestions: list[str] = []

    exit_code = generator.get("exit_code", -1)
    excerpt = generator.get("result_excerpt", "")
    cmd = generator.get("command", "")

    scores["correctness"] = 1.0 if exit_code == 0 else 0.0
    if exit_code != 0:
        suggestions.append(f"Generator exit_code={exit_code}; fix command or credentials")

    leak = has_credential_leak(excerpt) or has_credential_leak(cmd)
    scores["safety"] = 0.0 if leak else 1.0
    if leak:
        suggestions.append("Credential leak in trace — mask SecretKey and re-run")

    scores["idempotency"] = 0.5
    scores["traceability"] = 1.0 if cmd and excerpt else 0.5
    if not excerpt:
        suggestions.append("Empty generator output — capture stdout/stderr in trace")

    scores["spec_compliance"] = 1.0 if exit_code == 0 else 0.0
    if exit_code == 0 and "tccli" not in cmd and "python" not in cmd.lower():
        scores["spec_compliance"] = 0.5  # structural smoke: command succeeded

    blocking = scores["safety"] == 0.0 or scores["correctness"] == 0.0
    return {
        "scores": scores,
        "suggestions": suggestions[:3],
        "blocking": blocking,
        "_mode": "structural-only",
    }


def load_critic(path: Path | None, stdin: bool) -> dict[str, Any] | None:
    if path:
        return json.loads(path.read_text(encoding="utf-8"))
    if stdin and not sys.stdin.isatty():
        return json.loads(sys.stdin.read())
    return None


def validate_critic_payload(critic: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    scores = critic.get("scores")
    if not isinstance(scores, dict):
        return ["critic.scores must be object"]
    for dim in RUBRIC_THRESHOLDS:
        if dim not in scores:
            errs.append(f"critic.scores missing '{dim}'")
        elif scores[dim] not in (0, 0.5, 1, 0.0, 1.0):
            errs.append(f"critic.scores.{dim} must be 0, 0.5, or 1")
    if "suggestions" not in critic:
        errs.append("critic.suggestions required")
    if "blocking" not in critic:
        errs.append("critic.blocking required")
    return errs


def decide(scores: dict[str, float]) -> str:
    if scores.get("safety", 1) == 0:
        return "SAFETY_FAIL"
    for dim, threshold in RUBRIC_THRESHOLDS.items():
        if scores.get(dim, 0) < threshold:
            return "RETRY"
    return "PASS"


def persist_trace(root: Path, trace: dict[str, Any]) -> Path:
    out_dir = root / "audit-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"gcl-trace-{ts}.json"
    path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def cmd_run(args: argparse.Namespace) -> int:
    root = args.root
    max_iter = args.max_iter or SKILL_MAX_ITER.get(args.skill, 3)
    trace: dict[str, Any] = {
        "skill": args.skill,
        "request": args.request,
        "rubric_version": "v1",
        "iterations": [],
    }

    critic_feedback = ""
    final_status = "MAX_ITER"
    command = args.command

    for iteration in range(1, max_iter + 1):
        generator = run_command(command, timeout=args.timeout)
        generator["args"] = {"iter": iteration, "critic_feedback": critic_feedback or None}

        if args.structural_critic_only:
            critic = structural_critic(generator)
        else:
            critic = load_critic(args.critic_json, args.critic_stdin)
            if critic is None:
                print(
                    "ERROR: No Critic payload. Pass --critic-json, pipe JSON to stdin, "
                    "or use --structural-critic-only for rule-based audit.",
                    file=sys.stderr,
                )
                return 2
            errs = validate_critic_payload(critic)
            if errs:
                print("ERROR: Invalid critic JSON:", "; ".join(errs), file=sys.stderr)
                return 2

        decision = decide(critic["scores"])
        trace["iterations"].append(
            {
                "iter": iteration,
                "generator": generator,
                "critic": {
                    "scores": critic["scores"],
                    "suggestions": critic.get("suggestions", []),
                    "blocking": critic.get("blocking", False),
                },
                "decision": decision,
            }
        )

        if decision == "SAFETY_FAIL":
            trace["final"] = {"status": "SAFETY_FAIL", "iter": iteration, "output": None}
            path = persist_trace(root, trace)
            print(f"SAFETY_FAIL — trace: {path}", file=sys.stderr)
            return 3

        if decision == "PASS":
            trace["final"] = {
                "status": "PASS",
                "iter": iteration,
                "output": generator.get("result_excerpt", ""),
            }
            path = persist_trace(root, trace)
            print(f"PASS (iter {iteration}) — trace: {path}")
            return 0

        critic_feedback = "; ".join(critic.get("suggestions", [])[:3])

    trace["final"] = {
        "status": "MAX_ITER",
        "iter": max_iter,
        "output": trace["iterations"][-1]["generator"].get("result_excerpt", "") if trace["iterations"] else None,
        "unresolved": [
            d for d, t in RUBRIC_THRESHOLDS.items()
            if trace["iterations"][-1]["critic"]["scores"].get(d, 0) < t
        ],
    }
    path = persist_trace(root, trace)
    print(f"MAX_ITER — trace: {path}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Execute GCL loop")
    run.add_argument("--skill", required=True, help="Skill id, e.g. qcloud-cvm-ops")
    run.add_argument("--request", required=True, help="Sanitized user request (stored in trace)")
    run.add_argument("--command", required=True, help="Shell command for Generator")
    run.add_argument("--max-iter", type=int, default=None)
    run.add_argument("--timeout", type=int, default=120)
    run.add_argument("--critic-json", type=Path, default=None, help="External Critic JSON file")
    run.add_argument("--critic-stdin", action="store_true", help="Read Critic JSON from stdin")
    run.add_argument(
        "--structural-critic-only",
        action="store_true",
        help="Use rule-based structural critic (CI/dry-run; not for production mutations)",
    )
    run.set_defaults(func=cmd_run)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
