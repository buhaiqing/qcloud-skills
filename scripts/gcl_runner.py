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
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gcl_trajectory_quality import classify_op
from reflexion_retrieve import load_failure_patterns, format_for_injection
from success_pattern_mine import write_pending_with_lock

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


def run_command(
    command: str, timeout: int = 120, env: dict[str, str] | None = None
) -> dict[str, Any]:
    """Execute generator command; capture exit code and masked output."""
    try:
        proc_env = dict(os.environ)
        if env:
            proc_env.update(env)
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=proc_env,
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
            "op_type": classify_op(command),
        }
    except subprocess.TimeoutExpired:
        return {
            "command": mask_secrets(command),
            "exit_code": -1,
            "result_excerpt": f"TIMEOUT after {timeout}s",
            "stdout_len": 0,
            "stderr_len": 0,
            "op_type": classify_op(command),
        }


def structural_critic(generator: dict[str, Any]) -> dict[str, Any]:
    """Rule-based structural audit — for CI/dry-run only, not production Critic."""
    scores: dict[str, float] = {}
    suggestions: list[str] = []

    exit_code = generator.get("exit_code", -1)
    excerpt = generator.get("result_excerpt", "")
    cmd = generator.get("command", "")
    raw_output = generator.get("raw_output", "")

    scores["correctness"] = 1.0 if exit_code == 0 else 0.0
    if exit_code != 0:
        suggestions.append(f"Generator exit_code={exit_code}; fix command or credentials")

    leak = has_credential_leak(excerpt) or has_credential_leak(cmd)
    scores["safety"] = 0.0 if leak else 1.0
    if leak:
        suggestions.append("Credential leak in trace — mask SecretKey and re-run")

    # P1-B: Check Response has RequestId
    has_request_id = False
    if raw_output:
        try:
            out_dict = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
            has_request_id = "RequestId" in out_dict.get("Response", {})
        except Exception:
            pass
    scores["traceability"] = 1.0 if has_request_id else 0.5
    if not has_request_id and (exit_code == 0 or excerpt):
        suggestions.append("Response missing RequestId — traceability degraded")

    # P1-B: Check ClientToken (idempotency key)
    has_client_token = False
    if raw_output:
        try:
            out_dict = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
            has_client_token = "ClientToken" in out_dict.get("Response", {})
        except Exception:
            pass
    scores["idempotency"] = 1.0 if has_client_token else 0.5
    if not has_client_token and exit_code == 0:
        suggestions.append("Response missing ClientToken — idempotency cannot be verified")

    scores["spec_compliance"] = 1.0 if exit_code == 0 else 0.0
    if exit_code == 0 and "tccli" not in cmd and "python" not in cmd.lower():
        scores["spec_compliance"] = 0.5  # structural smoke: command succeeded

    # P1-B: Check required fields based on operation type
    cmd_lower = cmd.lower()
    is_delete = any(k in cmd_lower for k in ["delete", "destroy", "release", "terminate", "drop"])
    if is_delete and exit_code == 0:
        # For delete operations, absence of error in Response is the required field
        has_error_field = False
        if raw_output:
            try:
                out_dict = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
                has_error_field = "Error" in out_dict.get("Response", {})
            except Exception:
                pass
        # Delete success should have Error: null or absent
        if has_error_field:
            suggestions.append("Delete operation returned Error field — operation may have failed")
            scores["spec_compliance"] = 0.0

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


def derive_rule_hits(
    critic: dict[str, Any], generator: dict[str, Any], structural: bool
) -> dict[str, list[str]]:
    """Explain each rubric dimension score via structured rule names (fixes L6/S-B).

    Returns ``{dim: [rule_hit, ...]}`` so a trace answers "safety=0 because
    which rule". Hits are structured rule identifiers, not free-text suggestions.

    - Structural mode: derived purely from score signals (credential leak,
      non-zero exit code, sub-threshold markers).
    - External-critic mode: map dimension-prefixed ``suggestions`` (e.g.
      ``"safety: ..."``) into their dim; sub-threshold dims without a hit get
      ``below_rubric_threshold``. Unprefixed free-text suggestions stay out of
      this field (they already live in ``critic.suggestions``).
    """
    scores = critic.get("scores", {})
    dims = list(RUBRIC_THRESHOLDS.keys())
    hits: dict[str, list[str]] = {dim: [] for dim in dims}

    leak = has_credential_leak(generator.get("result_excerpt", "")) or has_credential_leak(
        generator.get("command", "")
    )
    if scores.get("safety", 1.0) == 0.0:
        hits["safety"].append("credential_leak_detected" if leak else "critic_safety_zero")
    if scores.get("correctness", 1.0) == 0.0:
        hits["correctness"].append("generator_exit_code_nonzero")

    if not structural:
        for s in critic.get("suggestions", []):
            lowered = s.lower()
            for dim in dims:
                if lowered.startswith(dim) or f"{dim}:" in lowered:
                    hits[dim].append(s)
                    break

    for dim in dims:
        if scores.get(dim, 1.0) < RUBRIC_THRESHOLDS.get(dim, 1.0) and not hits[dim]:
            hits[dim].append("below_rubric_threshold")
    return hits


def decide(scores: dict[str, float]) -> str:
    if scores.get("safety", 1) == 0:
        return "SAFETY_FAIL"
    for dim, threshold in RUBRIC_THRESHOLDS.items():
        if scores.get(dim, 0) < threshold:
            return "RETRY"
    return "PASS"


# Reflexion: failure-pattern extraction (AGENTS.md §14.6).
# Maps Generator output + Critic suggestions to a structured failure_pattern
# block that callers (or Reflexion pre-flight) can persist to
# docs/failure-patterns.md. Categories match the schema in that file:
#   cli_parameter | skill_generation | cross_skill | runtime | token_efficiency
_FAILURE_SIGNATURES: list[tuple[str, re.Pattern[str]]] = [
    ("cli_parameter", re.compile(r"InvalidParameter|MissingParameter|AuthFailure\.", re.I)),
    ("runtime", re.compile(r"TIMEOUT|RequestLimitExceeded|InternalError|ConnectionError", re.I)),
    ("cross_skill", re.compile(r"delegate-to|not found in target skill|cross-skill", re.I)),
    ("token_efficiency", re.compile(r"token budget|exceeds.*token|too long|truncated", re.I)),
    ("skill_generation", re.compile(r"frontmatter missing|missing rubric|broken link", re.I)),
]


def _derive_severity(scores: dict[str, float]) -> str:
    """P0-C: Derive severity from critic scores.

    critical: Safety=0 (credential leak, destructive without confirm)
    major:   Correctness=0 or Idempotency=0
    minor:   all other rubric failures
    """
    s = scores or {}
    if s.get("safety", 1) == 0:
        return "critical"
    if s.get("correctness", 1) == 0 or s.get("idempotency", 1) == 0:
        return "major"
    return "minor"


def extract_failure_pattern(
    skill: str,
    command: str,
    generator: dict[str, Any],
    critic: dict[str, Any],
) -> dict[str, Any] | None:
    """Heuristic failure-pattern extraction. Returns None if no pattern matched.

    The schema mirrors ``docs/failure-patterns.md`` so that traces can feed
    Reflexion memory directly. Count starts at 1; downstream tooling is
    expected to dedup-and-increment before persisting.
    """
    corpus_parts = [
        command or "",
        generator.get("result_excerpt", "") or "",
        *(critic.get("suggestions") or []),
    ]
    corpus = "\n".join(corpus_parts)
    scores = critic.get("scores") or {}
    severity = _derive_severity(scores)
    for category, pattern in _FAILURE_SIGNATURES:
        match = pattern.search(corpus)
        if not match:
            continue
        fix = (critic.get("suggestions") or ["Investigate failure pattern and add fix"])[0]
        return {
            "category": category,
            "skill": skill,
            "command": command[:200] if command else None,
            "error": match.group(0),
            "fix": fix[:200],
            "count": 1,
            "reusable": category in {"cli_parameter", "runtime"},
            "severity": severity,  # P0-C
        }
    return None


def persist_trace(root: Path, trace: dict[str, Any], trace_id: str | None = None) -> Path:
    """Persist a GCL trace.

    `trace_id` is the cross-system join key: when provided it names the file
    (gcl-trace-<trace_id>.json) so copilot session traces and GCL traces share
    one identifier namespace (fixes data-lineage break L3). Falls back to a
    UTC timestamp to stay backward-compatible with existing timestamp-based
    queries and the structural smoke tests.
    """
    out_dir = root / "audit-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    if trace_id:
        trace = {**trace, "trace_id": trace_id}
        path = out_dir / f"gcl-trace-{trace_id}.json"
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = out_dir / f"gcl-trace-{ts}.json"
    path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def cmd_run(args: argparse.Namespace) -> int:
    root = args.root
    max_iter = args.max_iter or SKILL_MAX_ITER.get(args.skill, 3)
    try:
        prior_patterns = load_failure_patterns(args.skill, args.command)
    except Exception:
        prior_patterns = []
    prior_block = format_for_injection(prior_patterns)

    trace: dict[str, Any] = {
        "skill": args.skill,
        "request": args.request,
        "rubric_version": "v1",
        "iterations": [],
        "preflight_reflexion": {
            "skill": args.skill,
            "command": args.command,
            "matched": len(prior_patterns),
            "injection": prior_block,
        },
    }
    gen_env = {"REFLEXION_PATTERNS": prior_block} if prior_block else None

    critic_feedback = ""
    command = args.command

    for iteration in range(1, max_iter + 1):
        generator = run_command(command, timeout=args.timeout, env=gen_env)
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
                    "rubric_rule_hits": derive_rule_hits(
                        critic, generator, args.structural_critic_only
                    ),
                },
                "decision": decision,
            }
        )

        if decision == "SAFETY_FAIL":
            trace["final"] = {
                "status": "SAFETY_FAIL",
                "iter": iteration,
                "output": None,
                "failure_pattern": extract_failure_pattern(
                    args.skill, command, generator, critic
                ),
            }
            path = persist_trace(root, trace, trace_id=args.trace_id)
            print(f"SAFETY_FAIL — trace: {path}", file=sys.stderr)
            return 3

        if decision == "PASS":
            trace["final"] = {
                "status": "PASS",
                "iter": iteration,
                "output": generator.get("result_excerpt", ""),
            }
            path = persist_trace(root, trace, trace_id=args.trace_id)
            # P0-A: write success pattern to pending log
            try:
                scores = critic.get("scores") or {}
                op_match = re.search(r"tccli\s+\w+\s+(\w+)", command or "")
                operation = op_match.group(1) if op_match else ""
                write_pending_with_lock({
                    "skill": args.skill,
                    "operation": operation,
                    "command": command or "",
                    "iter": iteration,
                    "scores": scores,
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                })
            except Exception:
                pass  # non-blocking: success logging must not break the main return path
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
        "failure_pattern": extract_failure_pattern(
            args.skill, command, trace["iterations"][-1]["generator"], trace["iterations"][-1]["critic"]
        ),
    }
    path = persist_trace(root, trace)
    print(f"MAX_ITER — trace: {path}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Execute GCL loop")
    run.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: parent of scripts/)",
    )
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
    run.add_argument(
        "--trace-id",
        default=None,
        help="Cross-system join key (e.g. copilot session_id). Names the trace file "
        "gcl-trace-<trace_id>.json so copilot and GCL traces share one identifier namespace.",
    )
    run.set_defaults(func=cmd_run)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
