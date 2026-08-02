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

  # Built-in LLM Critic (Phase 1 module 1.1). Uses OpenAI-compatible chat API.
  python3 scripts/gcl_runner.py run ... --llm-critic \\
    [--llm-model MODEL] [--llm-base-url URL]
  # Falls back to structural_critic on timeout / malformed response.

Trace output: ``audit-results/gcl-trace-YYYYMMDD-HHMMSS.json``
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from distribution_drift import compute_drift
from distribution_drift import load_traces as _load_traces_dd
from evidence_kernel import SENSITIVE_KEY_RE, mask_trace, post_record, preflight
from gcl_trajectory_quality import classify_op
from hallucination_detection import detect_hallucinations
from reflexion_retrieve import format_for_injection as ff_fail
from reflexion_retrieve import load_failure_patterns
from success_pattern_mine import write_pending_with_lock
from success_pattern_retrieve import retrieve_success_patterns


def load_tcloud_error_hints() -> str:
    """Load Tencent Cloud API error code hints for Critic prompt injection."""
    try:
        from tcloud_error_codes import TCLOUD_ERROR_CODES

        lines = ["## Tencent Cloud Error Code Reference"]
        for code, info in TCLOUD_ERROR_CODES.items():
            lines.append(f"- `{code}`: {info['category']} — {info['fix']}")
        return "\n".join(lines)
    except Exception:  # noqa: BLE001
        return ""


def load_error_code_map() -> dict[str, dict[str, str]]:
    """Load the raw Tencent Cloud error-code→info mapping for structural_critic use."""
    try:
        from tcloud_error_codes import TCLOUD_ERROR_CODES

        return TCLOUD_ERROR_CODES
    except Exception:  # noqa: BLE001
        return {}

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


@contextlib.contextmanager
def _rubric_calibration(root: Path, skill: str):
    """Apply calibrated rubric thresholds for skill; restore on exit.

    Looks for ``audit-results/rubric-calibration-*.json`` and, if a matching
    skill entry exists, overrides ``RUBRIC_THRESHOLDS`` for the duration of the
    block.  The module-global is always restored, even on exception.
    """
    _saved = dict(RUBRIC_THRESHOLDS)
    try:
        CAL_DIR = root / "audit-results"
        files = sorted(CAL_DIR.glob("rubric-calibration-*.json"))
        if files:
            latest = files[-1]
            with open(latest) as fh:
                data = json.load(fh)
            skill_calib = data.get("skills", {}).get(skill, {})
            if skill_calib:
                for dim, val in skill_calib.items():
                    if dim in RUBRIC_THRESHOLDS:
                        RUBRIC_THRESHOLDS[dim] = val
                print(
                    f"[rubric_calibrate] Using calibrated thresholds for {skill}",
                    file=sys.stderr,
                )
    except Exception:  # noqa: BLE001, S110
        pass  # non-blocking
    try:
        yield
    finally:
        RUBRIC_THRESHOLDS.clear()
        RUBRIC_THRESHOLDS.update(_saved)


# Shared thresholds — assets/shared/thresholds.json is the single source
# (AGENTS.md TE-4). Loaded at import time; a missing/corrupt asset degrades to
# built-in defaults with a warning (never crashes importing tools).
_SHARED_DIR = Path(__file__).resolve().parent.parent / "assets" / "shared"


def _load_shared_json(name: str) -> dict[str, Any]:
    try:
        with open(_SHARED_DIR / name, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        warnings.warn(f"cannot load shared asset {_SHARED_DIR / name}; using built-in defaults")
        return {}


_THRESHOLDS: dict[str, Any] = _load_shared_json("thresholds.json")
# Default minimum score for the generic rubric dimensions (correctness,
# idempotency, traceability, spec_compliance). "safety" keeps its own
# perfect-score gate (1.0); its abort semantics are driven by
# SAFETY_FAIL_THRESHOLD.
_RUBRIC_MIN_SCORE: float = float(_THRESHOLDS.get("rubric_min_score", 0.5))
SAFETY_FAIL_THRESHOLD: float = float(_THRESHOLDS.get("safety_fail_threshold", 0.0))


RUBRIC_THRESHOLDS: dict[str, float] = {
    "correctness": _RUBRIC_MIN_SCORE,
    "safety": 1.0,
    "idempotency": _RUBRIC_MIN_SCORE,
    "traceability": _RUBRIC_MIN_SCORE,
    "spec_compliance": _RUBRIC_MIN_SCORE,
}

# Single source for credential shapes (TE-4): evidence_kernel.SENSITIVE_KEY_RE
# already tolerates `--secretKey x`, `"secretKey":"x"` and `SecretKey=x`. Two
# divergent maskers meant a payload masked here still leaked past the Evidence
# gate (and vice-versa), so both paths now share one pattern.
# The `(?!<masked>)` guard keeps the detector from re-flagging its own
# placeholder: without it, masking a leak produced `...=<masked>`, which still
# matched and pinned the run at SAFETY_FAIL with no retry able to clear it.
# (`SENSITIVE_KEY_RE`'s value class excludes `<`/`>`, so it needs no guard.)
SECRET_PATTERNS = [
    SENSITIVE_KEY_RE,
    re.compile(
        r"TENCENTCLOUD_SECRET_KEY\s*[:=\s]\s*(?!<masked>)[^\s\"']+", re.IGNORECASE
    ),
]


def mask_secrets(text: str) -> str:
    out = SENSITIVE_KEY_RE.sub(r"\1<masked>", text)
    return re.sub(
        r"(TENCENTCLOUD_SECRET_KEY\s*[:=\s]\s*)([^\s\"']+)",
        r"\1<masked>",
        out,
        flags=re.IGNORECASE,
    )


def has_credential_leak(text: str) -> bool:
    # No `<masked>` early-return: a partially masked blob can still carry an
    # unmasked secret, and the kill-switch made that leak invisible.
    return any(p.search(text) for p in SECRET_PATTERNS)


ALLOWED_EXECUTABLES = frozenset({"tccli"})


def parse_generator_command(command: str) -> list[str]:
    """Split a Generator command into argv, rejecting anything but ``tccli``.

    The Generator command reaches us as an operator/LLM-supplied string. Running
    it through a shell would make `;`, backticks and `$(...)` executable, so we
    tokenize with shlex and run with ``shell=False``; metacharacters then survive
    only as inert argv text.
    """
    try:
        argv = shlex.split(command)
    except ValueError as e:
        raise ValueError(f"unparsable command: {e}") from e
    if not argv:
        raise ValueError("empty command")
    if argv[0] not in ALLOWED_EXECUTABLES:
        raise ValueError(
            f"only tccli invocations permitted (got {argv[0]!r})"
        )
    return argv


def run_command(
    command: str, timeout: int = 120, env: dict[str, str] | None = None
) -> dict[str, Any]:
    """Execute generator command; capture exit code and masked output."""
    try:
        argv = parse_generator_command(command)
    except ValueError as e:
        return {
            "command": mask_secrets(command),
            "exit_code": -2,
            "result_excerpt": f"COMMAND REJECTED: {e}",
            "stdout_len": 0,
            "stderr_len": 0,
            "op_type": classify_op(command),
        }
    try:
        proc_env = dict(os.environ)
        if env:
            proc_env.update(env)
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=proc_env,
            check=False,
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
        # Use _error_code_map for specific guidance; fall back to generic message
        error_map = generator.get("_error_code_map", {})
        specific = ""
        for code, info in error_map.items():
            if code in excerpt or code in cmd:
                specific = f"`{code}`: {info['category']} — {info['fix']}"
                break
        if specific:
            suggestions.append(f"Generator exit_code={exit_code}; {specific}")
        else:
            suggestions.append(f"Generator exit_code={exit_code}; fix command or credentials")

    leak = has_credential_leak(excerpt) or has_credential_leak(cmd)
    scores["safety"] = 0.0 if leak else 1.0
    if leak:
        suggestions.append("Credential leak in trace — mask SecretKey and re-run")

    # Parse the generator output once; every structural check below reads it.
    # `unparseable` is distinct from `absent`: if output was produced but cannot
    # be read, the structural checks prove nothing and must not score as 0.5.
    response: dict[str, Any] = {}
    unparseable = False
    if raw_output:
        try:
            out_dict = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
            response = out_dict.get("Response", {})
            if not isinstance(response, dict):
                raise TypeError("Response is not an object")
        except (json.JSONDecodeError, TypeError, AttributeError):
            unparseable = True
            response = {}
            suggestions.append("raw_output unparseable — scores unverifiable")

    # P1-B: Check Response has RequestId
    has_request_id = "RequestId" in response
    scores["traceability"] = 0.0 if unparseable else (1.0 if has_request_id else 0.5)
    if not has_request_id and not unparseable and (exit_code == 0 or excerpt):
        suggestions.append("Response missing RequestId — traceability degraded")

    # P1-B: Check ClientToken (idempotency key)
    has_client_token = "ClientToken" in response
    scores["idempotency"] = 0.0 if unparseable else (1.0 if has_client_token else 0.5)
    if not has_client_token and not unparseable and exit_code == 0:
        suggestions.append("Response missing ClientToken — idempotency cannot be verified")

    scores["spec_compliance"] = 1.0 if exit_code == 0 else 0.0
    if exit_code == 0 and "tccli" not in cmd and "python" not in cmd.lower():
        scores["spec_compliance"] = 0.5  # structural smoke: command succeeded

    # P1-B: Check required fields based on operation type
    cmd_lower = cmd.lower()
    is_delete = any(k in cmd_lower for k in ["delete", "destroy", "release", "terminate", "drop"])
    # A successful delete must not carry an Error field in its Response.
    if is_delete and exit_code == 0 and "Error" in response:
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


# ---------------------------------------------------------------------------
# Phase 1 module 1.1: built-in LLM Critic
# ---------------------------------------------------------------------------

DEFAULT_LLM_TIMEOUT = 120
DEFAULT_LLM_MODEL = "gpt-4o-mini"

_LLM_PROMPT_TEMPLATE = """You are the Critic in a Generator-Critic Loop for Tencent Cloud ops skills.

Score the Generator's tccli command execution against the rubric. Return JSON:
{
  "scores": {
    "correctness": 0 | 0.5 | 1,
    "safety":      0 | 1,
    "idempotency": 0 | 0.5 | 1,
    "traceability":0 | 0.5 | 1,
    "spec_compliance": 0 | 0.5 | 1
  },
  "suggestions": ["..."],
  "blocking": true | false
}

Rules:
- safety=0 if credentials appear in command/output, or destructive op without confirmation
- correctness=0 if exit_code != 0 or result is malformed
- idempotency=0 if side-effects confirmed (read-only is fine)
- traceability=0 if no RequestId / no structured output
- spec_compliance=0 if operation doesn't match skill intent
- blocking=true only when safety=0 or correctness=0
- Wrap your JSON in a ```json``` code fence for clarity."""


def _load_skill_rubric(root: Path, skill: str) -> str:
    """Load skill-specific rubric. Falls back to generic if absent."""
    rubric = root / skill / "references" / "rubric.md"
    if rubric.exists():
        return rubric.read_text(encoding="utf-8")
    return "(no skill-specific rubric; use generic GCL rubric from docs/gcl-spec.md)"


def _build_llm_config() -> dict[str, Any] | None:
    """Build LLM config from GCL_LLM_* env vars. Returns None when incomplete."""
    api_key = os.environ.get("GCL_LLM_API_KEY", "").strip()
    base_url = os.environ.get("GCL_LLM_BASE_URL", "").strip()
    model = os.environ.get("GCL_LLM_MODEL", "").strip() or DEFAULT_LLM_MODEL
    raw_timeout = os.environ.get("GCL_LLM_TIMEOUT", "").strip()
    try:
        timeout = int(raw_timeout) if raw_timeout else DEFAULT_LLM_TIMEOUT
    except ValueError:
        timeout = DEFAULT_LLM_TIMEOUT
    if not api_key or not base_url:
        return None
    return {
        "api_key": api_key,
        "base_url": base_url.rstrip("/"),
        "model": model,
        "timeout": timeout,
    }


def _call_llm_chat(
    llm_config: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Call OpenAI-compatible chat completion API; return raw response body string.

    Raises urllib.error.URLError / TimeoutError on network failures.
    """
    url = f"{llm_config['base_url']}/chat/completions"
    payload = {
        "model": llm_config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llm_config['api_key']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=llm_config["timeout"]) as resp:
        body = resp.read().decode("utf-8")
    # OpenAI format: response.choices[0].message.content
    try:
        parsed = json.loads(body)
        return parsed["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError):
        # Some providers return raw JSON; fall through
        return body


def _parse_llm_response(body: str) -> dict[str, Any]:
    """Extract a Critic JSON payload from an LLM response string.

    Tolerates:
      - raw JSON
      - JSON wrapped in ```json ... ``` fences
      - prose prefix before the JSON block
    Raises ValueError when no JSON object can be found.
    """
    text = body.strip()
    # Strip code fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        # Find the first { ... } block
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            text = text[brace_start:brace_end + 1]
    parsed = json.loads(text)
    parsed["_mode"] = "llm-builtin"
    return parsed


def llm_critic(
    generator: dict[str, Any],
    skill: str,
    rubric_text: str,
    prompt_template: str,
    llm_config: dict[str, Any],
) -> dict[str, Any]:
    """Built-in LLM Critic (Phase 1 module 1.1).

    - Sends generator output + skill-specific rubric to OpenAI-compatible API
    - On timeout / malformed response: retries once, then falls back to
      ``structural_critic()`` with ``_mode = "structural-only-fallback"``.
    - Never raises: returns a Critic payload that satisfies
      ``validate_critic_payload()`` (or its fallback).
    """
    system_prompt = (
        f"{prompt_template}\n\n"
        f"--- RUBRIC ({skill}) ---\n{rubric_text}"
    )
    user_prompt = (
        f"Skill: {skill}\n"
        f"Command: {generator.get('command', '')}\n"
        f"Exit code: {generator.get('exit_code', '?')}\n"
        f"Result excerpt: {generator.get('result_excerpt', '')}\n"
    )

    last_exc: Exception | None = None
    for attempt in range(2):  # initial + 1 retry
        try:
            body = _call_llm_chat(llm_config, system_prompt, user_prompt)
            parsed = _parse_llm_response(body)
            # Validate shape; on invalid shape, fall through to fallback
            errs = validate_critic_payload(parsed)
            if errs:
                last_exc = ValueError("; ".join(errs))
                continue
            return parsed
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError, ValueError) as e:
            last_exc = e
            continue
    # Fallback to structural critic
    structural = structural_critic(generator)
    structural["_mode"] = "structural-only-fallback"
    structural["_fallback_reason"] = (
        f"LLM critic failed after 2 attempts: {type(last_exc).__name__ if last_exc else 'unknown'}"
    )
    return structural


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
    if scores.get("safety", 1) <= SAFETY_FAIL_THRESHOLD:
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
    ("cli_parameter", re.compile(r"InvalidParameter|MissingParameter|AuthFailure\.", re.IGNORECASE)),
    ("runtime", re.compile(r"TIMEOUT|RequestLimitExceeded|InternalError|ConnectionError", re.IGNORECASE)),
    ("cross_skill", re.compile(r"delegate-to|not found in target skill|cross-skill", re.IGNORECASE)),
    ("token_efficiency", re.compile(r"token budget|exceeds.*token|too long|truncated", re.IGNORECASE)),
    ("skill_generation", re.compile(r"frontmatter missing|missing rubric|broken link", re.IGNORECASE)),
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


def _emit_trace_span(
    root: Path,
    run_id: str,
    skill: str,
    command: str,
    status: str,
    scores: dict[str, float] | None = None,
    error_code: str | None = None,
    duration_ms: int = 0,
    trace_id: str | None = None,
) -> None:
    """Phase 1.4 — side-emit a unified TraceSpan alongside persist_trace().

    Best-effort: failures here never break GCL. Imports the observability
    facade lazily so gcl_runner can run on stdlib-only environments that
    don't ship copilot/.
    """
    try:
        # Local import keeps the scripts/ tree decoupled from qcloud-copilot/.
        import sys as _sys
        copilot_root = str((root / "qcloud-copilot").resolve())
        if copilot_root not in _sys.path:
            _sys.path.insert(0, copilot_root)
        from copilot.observ import ObservableSink, TraceSpan
    except Exception:  # noqa: BLE001 - observability must never break GCL
        return
    op_match = re.search(r"tccli\s+\w+\s+(\w+)", command or "")
    operation = op_match.group(1) if op_match else "gcl_run"
    span = TraceSpan(
        span_id=f"{run_id}:{skill}",
        trace_id=trace_id or run_id,
        parent_span_id=None,
        run_id=run_id,
        skill=skill,
        operation=operation,
        step_id="gcl.run",
        status=status,
        duration_ms=duration_ms,
        error_code=error_code,
        gcl_scores=scores,
        metadata={"command": (command or "")[:200]},
    )
    try:
        ObservableSink(runtime_root=root / ".runtime").emit_trace_span(span)
    except Exception:  # noqa: BLE001, S110 - observability must never break GCL
        pass


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
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        path = out_dir / f"gcl-trace-{ts}.json"
    path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def emit_evidence_record(root: Path, trace: dict[str, Any], args: argparse.Namespace, run_id: str,
                         pf: dict[str, Any] | None = None) -> None:
    """Additive EvidenceRecord side-emit (KPI pipeline). Does NOT replace persist_trace.

    `pf` is the PreFlight result already computed in cmd_run — carries the REAL
    destructive decision + token binding outcome so KPI #2 (destructive_coverage)
    is non-vacuous instead of hardcoded-false.
    """
    try:
        masked = mask_trace(trace)
        destructive = bool(pf.get("destructive")) if pf else False
        token_bound = bool(pf.get("token_bound")) if pf else False
        record = {
            "skill": args.skill,
            "run_id": run_id,
            "phase": "production",
            "intent": args.request,
            "router_decision": {"top1_skill": args.skill, "candidates": [args.skill],
                                 "misdelegated": False, "fell_back": False},
            "trace": masked,
            "golden_ref": None, "fixture_ref": None,
            "safety": {"destructive": destructive,
                       "token": os.environ.get("HARNESS_CONFIRM_TOKEN") if destructive else None,
                       "token_bound": token_bound, "plan_hash": None, "leak_checked": True},
            "provenance": {"source": "gcl_runner", "tool": "tccli",
                           "captured_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
            "budgets": {"context_tokens": 0, "tool_calls": len(trace.get("iterations", [])),
                        "wall_clock_ms": 0},
            "cost": {"tokens": 0, "usd": None},
            "scores": _final_scores(trace),
        }
        post_record(record)
    except Exception as exc:  # noqa: BLE001 - Evidence side-emit must never break GCL
        # Still non-fatal, but no longer silent: a permanently broken KPI
        # pipeline used to look identical to a healthy one.
        print(f"WARN: evidence side-emit failed: {exc}", file=sys.stderr)


def _final_scores(trace: dict[str, Any]) -> dict[str, float]:
    """Real Critic scores from the last iteration.

    Previously hardcoded to all-1, which made the KPI feed vacuous: every run
    reported a perfect score regardless of what the Critic actually returned.
    """
    for iteration in reversed(trace.get("iterations") or []):
        scores = (iteration.get("critic") or {}).get("scores")
        if isinstance(scores, dict) and scores:
            return {k: float(v) for k, v in scores.items()}
    return dict.fromkeys(RUBRIC_THRESHOLDS, 0.0)

def _format_success_injection(entries: list[dict[str, Any]]) -> str:
    """Format success patterns for Generator context injection.

    Mirrors success_pattern_retrieve.format_for_injection but emits
    REUSE guidance instead of failure warnings — guiding Generator toward
    proven single-shot paths.

    Returns empty string when entries is empty.
    """
    if not entries:
        return ""
    lines = []
    for e in entries:
        skill = e.get("skill", "—")
        op = e.get("operation", "—")
        sig = (e.get("command_signature", "") or "")[:60]
        count = e.get("count", 0)
        iter_v = e.get("iter", 1)
        last_hit = e.get("last_hit", "—")
        layer = e.get("_layer", "?")
        layer_tag = f"[{layer.upper()}]" if layer != "hot" else ""
        lines.append(
            f"- {layer_tag}[{skill}] op=`{op}` sig=`{sig}...` "
            f"(count={count}, iter={iter_v}, last_hit={last_hit})"
        )
    return "Known success paths (consider reusing):\n" + "\n".join(lines)

def post_process(trace_path: Path, root: Path) -> None:
    """Run hallucination detection and distribution drift on the new trace.

    Called after PASS and MAX_ITER paths. Alerts go to stderr so they don't
    interfere with structured JSON output.
    """
    try:
        trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    # Hallucination detection
    suspects = detect_hallucinations([trace_data])
    if suspects:
        print(
            f"HALLUCINATION_ALERT: {len(suspects)} suspect(s) in {trace_path.name}",
            file=sys.stderr,
        )
        for s in suspects:
            print(
                f"  [{s['skill']}] iter={s['iter']} types={s['types']} "
                f"cmd={s['command'][:60]}",
                file=sys.stderr,
            )
    # Distribution drift
    try:
        all_traces = _load_traces_dd(root / "audit-results", since_days=30)
        if len(all_traces) >= 6:
            mid = len(all_traces) // 2
            w2 = all_traces[mid:]   # newer half
            w1 = all_traces[:mid]   # older half
            result = compute_drift(w1, w2)
            if "error" in result:
                print(f"DISTRIBUTION_DRIFT: {result['error']}", file=sys.stderr)
            else:
                alerts = result.get("alerts", [])
                print(
                    f"DISTRIBUTION_DRIFT: {len(alerts)} alert(s)",
                    file=sys.stderr,
                )
                for a in alerts:
                    print(
                        f"  [{a['metric']}] drift={a['drift']:.3f} "
                        f"sigma={a['drift_sigma']:.3f} [{a['direction']}] "
                        f"severity={a['severity']}",
                        file=sys.stderr,
                    )
    except Exception:  # noqa: BLE001, S110
        pass  # non-blocking



def cmd_run(args: argparse.Namespace) -> int:
    root = args.root
    # Precedence: CLI flag > per-skill SKILL_MAX_ITER > shared thresholds.json > built-in fallback.
    max_iter = (
        args.max_iter
        or SKILL_MAX_ITER.get(args.skill)
        or _THRESHOLDS.get("max_iterations")
        or 3
    )
    with _rubric_calibration(root, args.skill):

        # Load failure patterns (prevention hints)
        try:
            prior_fail = load_failure_patterns(args.skill, args.command)
        except Exception:  # noqa: BLE001
            prior_fail = []
        fail_block = ff_fail(prior_fail)
    
        # Load success patterns (convergence guidance — single-shot wins first)
        op_match = re.search(r"tccli\s+\w+\s+(\w+)", args.command or "")
        operation = op_match.group(1) if op_match else None
        try:
            prior_success = retrieve_success_patterns(args.skill, operation=operation, top_n=3)
        except Exception:  # noqa: BLE001
            prior_success = []
        succ_block = _format_success_injection(prior_success)
    
        # Combine: success hints guide Generator toward fast convergence;
        # failure hints prevent known mistakes
        reflexion_block = "\n".join(filter(None, [succ_block, fail_block]))
        trace: dict[str, Any] = {
            "skill": args.skill,
            "request": args.request,
            "rubric_version": "v1",
            "iterations": [],
            "preflight_reflexion": {
                "skill": args.skill,
                "command": args.command,
                "matched_failures": len(prior_fail),
                "matched_successes": len(prior_success),
                "injection": reflexion_block,
            },
        }
        gen_env = {"REFLEXION_PATTERNS": reflexion_block} if reflexion_block else None
    
        critic_feedback = ""
        command = args.command
        run_id = os.environ.get("HARNESS_RUN_ID", args.trace_id or "local")

        # Evidence Kernel PreFlight + Phase 3 human-token binding (additive gates)
        from harness_safety import bind_token, is_destructive  # local import to keep top clean
        token = os.environ.get("HARNESS_CONFIRM_TOKEN")
        pf = preflight(args.command, token)
        pf["token_bound"] = False
        if not pf["allowed"]:
            print(f"PREFLIGHT BLOCKED: {pf['reason']}", file=sys.stderr)
            return 2
        if is_destructive(args.command):
            try:
                bind_token(args.command, token or "")
                pf["token_bound"] = True
            except PermissionError as e:
                print(f"PLAN-TOKEN MISMATCH: {e} (human must set HARNESS_CONFIRM_TOKEN=plan_hash)", file=sys.stderr)
                return 2

        for iteration in range(1, max_iter + 1):
            generator = run_command(command, timeout=args.timeout, env=gen_env)
            generator["args"] = {"iter": iteration, "critic_feedback": critic_feedback or None}
            generator["error_code_hints"] = load_tcloud_error_hints()
            generator["_error_code_map"] = load_error_code_map()
    
            if args.structural_critic_only:
                critic = structural_critic(generator)
            elif args.llm_critic:
                # Phase 1 module 1.1: built-in LLM Critic
                cfg = _build_llm_config()
                # CLI flags override env vars
                if args.llm_model:
                    cfg = cfg or {}
                    cfg["model"] = args.llm_model
                if args.llm_base_url:
                    cfg = cfg or {}
                    cfg["base_url"] = args.llm_base_url.rstrip("/")
                if cfg is None:
                    print(
                        "ERROR: --llm-critic requires GCL_LLM_API_KEY and GCL_LLM_BASE_URL "
                        "(or --llm-base-url + --llm-model).",
                        file=sys.stderr,
                    )
                    return 2
                rubric_text = _load_skill_rubric(root, args.skill)
                critic = llm_critic(
                    generator, args.skill,
                    rubric_text= rubric_text,
                    prompt_template=_LLM_PROMPT_TEMPLATE,
                    llm_config=cfg,
                )
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
                emit_evidence_record(root, trace, args, run_id, pf)
                _emit_trace_span(
                    root, run_id, args.skill, command,
                    status="halted",
                    scores=critic.get("scores"),
                    error_code="SAFETY_FAIL",
                    trace_id=args.trace_id,
                )
                print(f"SAFETY_FAIL — trace: {path}", file=sys.stderr)
                return 3
    
            if decision == "PASS":
                trace["final"] = {
                    "status": "PASS",
                    "iter": iteration,
                    "output": generator.get("result_excerpt", ""),
                }
                path = persist_trace(root, trace, trace_id=args.trace_id)
                emit_evidence_record(root, trace, args, run_id, pf)
                _emit_trace_span(
                    root, run_id, args.skill, command,
                    status="success",
                    scores=critic.get("scores"),
                    trace_id=args.trace_id,
                )
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
                        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
                    })
                except Exception:  # noqa: BLE001, S110
                    pass  # non-blocking: success logging must not break the main return path
                print(f"PASS (iter {iteration}) — trace: {path}")
                if args.enable_post_process:
                    post_process(path, root)
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
        emit_evidence_record(root, trace, args, run_id, pf)
        _emit_trace_span(
            root, run_id, args.skill, command,
            status="failure",
            scores=trace["iterations"][-1]["critic"].get("scores") if trace["iterations"] else None,
            error_code="MAX_ITER",
            trace_id=args.trace_id,
        )
        print(f"MAX_ITER — trace: {path}", file=sys.stderr)
        if args.enable_post_process:
            post_process(path, root)
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
        "--llm-critic",
        action="store_true",
        help="Use built-in LLM Critic (Phase 1 module 1.1). Requires GCL_LLM_* env vars. "
             "Falls back to structural critic on timeout/malformed response.",
    )
    run.add_argument(
        "--llm-model",
        default=None,
        help="LLM model name (overrides GCL_LLM_MODEL env var)",
    )
    run.add_argument(
        "--llm-base-url",
        default=None,
        help="LLM API base URL (overrides GCL_LLM_BASE_URL env var)",
    )
    run.add_argument(
        "--trace-id",
        default=None,
        help="Cross-system join key (e.g. copilot session_id). Names the trace file "
        "gcl-trace-<trace_id>.json so copilot and GCL traces share one identifier namespace.",
    )
    run.add_argument(
        "--enable-post-process",
        action="store_true",
        default=False,
        help="Enable post-processing: hallucination detection + distribution drift",
    )
    run.set_defaults(func=cmd_run)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())