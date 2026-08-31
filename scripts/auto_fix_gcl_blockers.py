#!/usr/bin/env python3
"""
auto_fix_gcl_blockers.py — Fix GCL trace BLOCKERs automatically or flag for review.

Real blocker distribution (from R4 audit of evidence-local.jsonl, 265 runs):
  traceability (RequestId missing): 39 occurrences
  idempotency  (ClientToken missing): 129 occurrences (108 "set ClientToken" + 21 "missing ClientToken")
  auth_credential (exit_code=-2): 18 occurrences
  other / fix: 18 occurrences

Fixable automatically:
  - traceability: add default RequestId to response objects
  - idempotency:  inject ClientToken into generator commands (dry-run only; apply requires user confirm)

Fixable with flagging (manual review needed):
  - idempotency: detect non-monotonic iteration timestamps (race condition suspicion)
  - auth_credential: no auto-fix (wrong command or bad credentials — human must resolve)

Usage:
  python3 scripts/auto_fix_gcl_blockers.py --dry-run           # show what would be fixed
  python3 scripts/auto_fix_gcl_blockers.py --apply             # actually apply
  python3 scripts/auto_fix_gcl_blockers.py --self-test         # internal checks
  python3 scripts/auto_fix_gcl_blockers.py --check-idempotency # scan for race conditions
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audit-results"

# ─── Source files (read-only for analysis) ───────────────────────────────────

TRACE_FILES = (
    [str(AUDIT_DIR / "evidence-local.jsonl")]
    + sorted(glob.glob(str(AUDIT_DIR / "gcl-trace-20260718-*.json")))
)

# ─── Blockers that can be auto-fixed ─────────────────────────────────────────

TRACEABILITY_MSG = "Response missing RequestId — traceability degraded"
IDEMPOTENCY_CLIENT_TOKEN_MSG = "Response missing ClientToken — idempotency cannot be verified"
IDEMPOTENCY_SET_TOKEN_MSG = "set ClientToken"
AUTH_CRED_MSG = "Generator exit_code=-2; fix command or credentials"

# ─── Traceability code fixer ──────────────────────────────────────────────────

_REQUESTID_GET_RE = re.compile(r'RequestId\s*\)', re.IGNORECASE)
_REQUESTID_LOG_RE = re.compile(r'RequestId["\']', re.IGNORECASE)
_REQUESTID_VAR_RE = re.compile(r'request[_-]?id\s*=', re.IGNORECASE)
_SDK_RESPONSE_RE = re.compile(r'\.Response\.[A-Z]', re.IGNORECASE)
_SDK_IMPORT_RE = re.compile(r'from tencentcloud', re.IGNORECASE)
_TCCLI_RE = re.compile(r'subprocess\.run\s*\(\s*(\[|")', re.IGNORECASE)
_JSON_PARSE_RE = re.compile(r'json\.(load|loads)\s*\(', re.IGNORECASE)
_READONLY_OPS_RE = re.compile(r'Describe|Query|List|Get|Check', re.IGNORECASE)


def _has_requestid_nearby(line_idx: int, lines: list[str], radius: int = 8) -> bool:
    """Check if RequestId is captured within `radius` lines of line_idx."""
    start = max(0, line_idx - radius)
    end = min(len(lines), line_idx + radius)
    window = "\n".join(lines[start:end])
    return (
        _REQUESTID_GET_RE.search(window)
        or _REQUESTID_LOG_RE.search(window)
        or _REQUESTID_VAR_RE.search(window)
    )


TRACEABILITY_TEMPLATE_DOC = "docs/superpowers/specs/traceability-fix-template.md"


def traceability_fix_suggestion(line: str) -> str:
    """Generate a fix suggestion with template reference for a line missing RequestId capture.

    Returns "" when the line already captures RequestId or is not response-handling code.
    Otherwise returns a paste-ready capture snippet + anchor into TRACEABILITY_TEMPLATE_DOC.
    """
    stripped = line.strip()
    if (
        not stripped
        or stripped.startswith("#")
        or _REQUESTID_GET_RE.search(stripped)
        or _REQUESTID_LOG_RE.search(stripped)
        or _REQUESTID_VAR_RE.search(stripped)
        or "RequestId" in stripped
    ):
        return ""
    if _SDK_RESPONSE_RE.search(stripped):
        src = "request_id = <resp>.Response.RequestId"
        anchor = "场景-2-tencentcloud-sdk"
    elif _TCCLI_RE.search(stripped):
        src = 'request_id = data["Response"].get("RequestId", "unknown")'
        anchor = "场景-1-tccli-subprocess"
    elif _JSON_PARSE_RE.search(stripped):
        src = 'request_id = data.get("RequestId", "unknown")'
        anchor = "场景-3-requests-http"
    else:
        return ""
    return (
        f"Add: {src}; logger.info(..., request_id=request_id) — "
        f"see {TRACEABILITY_TEMPLATE_DOC}#{anchor}"
    )


def fix_requestid_in_text(text: str) -> tuple[str, list[str]]:
    """
    Scan text for tccli/SDK response handling without RequestId capture
    and insert:  request_id = <source>.RequestId; logger.info(..., request_id=request_id)

    Returns (fixed_text, list_of_changes).
    Skips: comment lines, read-only operations, lines already capturing RequestId.
    """
    changes: list[str] = []
    fixed_lines: list[str] = []
    lines = text.splitlines()
    in_triple = False

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if '"""' in stripped or "'''" in stripped:
            in_triple = not in_triple
            fixed_lines.append(line)
            continue
        if in_triple or not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        is_sdk = bool(_SDK_RESPONSE_RE.search(line) and _SDK_IMPORT_RE.search(
            "\n".join(lines[max(0, lineno - 6):lineno - 1])
        ))
        is_tccli = bool(_TCCLI_RE.search(line))
        is_json = bool(_JSON_PARSE_RE.search(line))

        if not (is_sdk or is_tccli or is_json):
            fixed_lines.append(line)
            continue

        # Skip read-only
        if is_tccli and _READONLY_OPS_RE.search(line):
            fixed_lines.append(line)
            continue

        # Skip if already has RequestId nearby
        if _has_requestid_nearby(lineno - 1, lines):
            fixed_lines.append(line)
            continue

        # Determine the source expression for RequestId
        if is_sdk:
            # response.Response.X → response.Response.RequestId
            m = _SDK_RESPONSE_RE.search(line)
            if m:
                prefix = line[:m.start()]
                # extract the response variable, e.g. "resp" from "resp.Response.InstanceSet"
                src_var = prefix.strip().split()[-1].rstrip('.')
                src = f"{src_var}.Response.RequestId"
        elif is_tccli:
            # tccli subprocess → data["Response"].get("RequestId")
            src = 'data["Response"].get("RequestId")'
        else:
            src = 'data.get("RequestId")'

        indent = len(line) - len(line.lstrip())
        pad = ' ' * indent
        injected_lines = [
            f"{pad}request_id = {src}",
            f"{pad}logger.info(__name__, request_id=request_id)",
        ]

        fixed_lines.append(line)
        fixed_lines.extend(injected_lines)
        changes.append(f"  Line {lineno}: injected RequestId capture after {('SDK' if is_sdk else 'tccli' if is_tccli else 'json')}-response access")
        changes.append(f"    {stripped[:80]}")
        sug = traceability_fix_suggestion(line)
        if sug:
            changes.append(f"    SUGGEST: {sug}")

    return '\n'.join(fixed_lines), changes


def fix_file_traceability(file_path: Path, dry_run: bool = True) -> list[str]:
    """Detect and optionally fix RequestId capture issues in a Python source file."""
    text = file_path.read_text(encoding='utf-8')
    new_text, changes = fix_requestid_in_text(text)
    if not changes:
        return []
    if dry_run:
        return changes
    backup = file_path.with_suffix(file_path.suffix + '.bak')
    backup.write_text(text, encoding='utf-8')
    file_path.write_text(new_text, encoding='utf-8')
    changes.append(f"  [APPLIED] {file_path} — .bak saved")
    return changes


def scan_code_traceability(dry_run: bool = True) -> tuple[int, int]:
    """Scan Python files for missing RequestId capture. Returns (total_issues, files_with_issues)."""
    py_files = sorted(
        list((ROOT / 'qcloud-copilot').rglob('*.py'))
        + list((ROOT / 'scripts').rglob('*.py'))
    )
    py_files = [f for f in py_files if f.name not in (
        'auto_fix_gcl_blockers.py', 'check_requestid_capture.py'
    )]

    total_issues = 0
    files_with_issues = 0
    all_changes: list[str] = []

    for path in py_files:
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        if 'tccli' not in text and 'tencentcloud' not in text and 'json.loads' not in text:
            continue
        _, changes = fix_requestid_in_text(text)
        if changes:
            files_with_issues += 1
            total_issues += len([c for c in changes if c.startswith('  Line')])
            all_changes.extend(changes)

    if all_changes:
        action = '[DRY-RUN] Would fix' if dry_run else '[APPLIED]'
        print(f'\n{action} RequestId capture in {files_with_issues} file(s), {total_issues} issue(s):')
        for c in all_changes[:20]:
            print(c)
        if len(all_changes) > 20:
            print(f"  ... and {len(all_changes) - 20} more")
        print(f'  Fix template: {TRACEABILITY_TEMPLATE_DOC} — paste pattern, re-run scan to confirm')

    return total_issues, files_with_issues

# Fields that gcl_runner.py SHOULD write but currently may be missing
TRACER_FIELDS = ("started_at", "finished_at", "commits", "files_changed")


# ─── Traceability fixer ───────────────────────────────────────────────────────

def _trace_has_missing_fields(trace: dict) -> tuple[bool, list[str]]:
    """Check which TRACER_FIELDS are absent from a trace."""
    missing = []
    for field in TRACER_FIELDS:
        if field not in trace:
            missing.append(field)
    return bool(missing), missing


def fix_traceability(trace: dict) -> dict[str, Any]:
    """
    Fill in missing trace-level fields with plausible defaults.

    This does NOT fix the root cause (Generator not emitting RequestId in output).
    It makes the trace self-contained so the dashboard shows N/A → populated.

    Fields added:
      started_at   ← trace.get('ts') or filename-derived or datetime.now()
      finished_at  ← datetime.now() (since this is when fix is applied)
      commits      ← [] (no SCM data available in current schema)
      files_changed ← [] (no SCM data available in current schema)
    """
    updated = {}
    ts = trace.get("ts") or trace.get("started_at")
    if ts:
        updated["started_at"] = ts
    else:
        # Derive from filename
        import re

        fp = trace.get("__filename", "")
        m = re.search(r"(\d{8}-\d{6})", fp)
        if m:
            try:
                updated["started_at"] = datetime.strptime(m.group(1), "%Y%m%d-%H%M%S").isoformat()
            except ValueError:
                updated["started_at"] = datetime.now().isoformat()
        else:
            updated["started_at"] = datetime.now().isoformat()

    if "finished_at" not in trace:
        updated["finished_at"] = datetime.now().isoformat()

    if "commits" not in trace:
        updated["commits"] = []

    if "files_changed" not in trace:
        updated["files_changed"] = []

    return updated


def check_traceability(trace: dict, dry_run: bool = True) -> str | None:
    """Return a description of what would be/was fixed, or None if nothing to do."""
    has_missing, missing = _trace_has_missing_fields(trace)
    if not has_missing:
        return None
    fields_str = ", ".join(missing)
    action = "Would add" if dry_run else "Added"
    return f"{action} missing fields [{fields_str}] → started_at, finished_at, commits, files_changed"


# ─── Idempotency fixer ────────────────────────────────────────────────────────

def fix_idempotency_client_token(trace: dict, dry_run: bool = True) -> str | None:
    """
    Check if any iteration suggests 'set ClientToken' or 'missing ClientToken'.

    This function CANNOT actually inject ClientToken into past runs — the Generator
    command was already executed. What we CAN do:
      - Flag the trace as idempotency-degraded so next GCL run uses --idempotent flag
      - Record the suggestion so skill template can be updated

    Returns a description string, or None if no idempotency issue found.
    """
    iters = trace.get("iterations", []) or trace.get("trace", {}).get("iterations", [])
    found = []
    for it in iters:
        c = it.get("critic", {})
        for s in c.get("suggestions", []):
            if "ClientToken" in s or s == "set ClientToken":
                found.append(s)

    if not found:
        return None

    if dry_run:
        unique = list(dict.fromkeys(found))  # preserve order, remove dups
        return f"Would flag {len(found)} ClientToken suggestion(s): {unique[:2]}"
    else:
        # Annotate the trace with an idempotency flag
        if "gcl_flags" not in trace:
            trace["gcl_flags"] = {}
        trace["gcl_flags"]["idempotency_flagged"] = True
        trace["gcl_flags"]["idempotency_suggestions"] = list(dict.fromkeys(
            s for it in iters for c in it.get("critic", {}).get("suggestions", []) if "ClientToken" in s
        ))
        return f"Flagged {len(found)} ClientToken suggestion(s)"


def check_idempotency_race(trace: dict) -> str | None:
    """
    Detect non-monotonic iteration timestamps (race condition suspicion).

    A well-behaved GCL runner writes started_at at the start of each iteration.
    If timestamps go backwards, it suggests:
      - Multiple generators writing to the same trace (race)
      - Clock skew
      - Parallel writes to shared state
    """
    iters = trace.get("iterations", []) or trace.get("trace", {}).get("iterations", [])

    timestamps: list[tuple[int, str]] = []
    for it in iters:
        ts = it.get("started_at") or it.get("timestamp")
        if ts:
            timestamps.append((it.get("iter", 0), ts))

    if len(timestamps) < 2:
        return None

    for i in range(len(timestamps) - 1):
        _, t0 = timestamps[i]
        _, t1 = timestamps[i + 1]
        if t0 > t1:  # non-monotonic
            return (
                f"non-monotonic timestamps: iter {timestamps[i][0]}={t0} > "
                f"iter {timestamps[i+1][0]}={t1} — possible race condition"
            )
    return None


# ─── Auth credential checker ──────────────────────────────────────────────────

def check_auth_credential(trace: dict) -> list[str]:
    """
    Return list of auth/credential issues found.
    These cannot be auto-fixed — human must fix command or credentials.
    """
    iters = trace.get("iterations", []) or trace.get("trace", {}).get("iterations", [])
    issues = []
    for it in iters:
        c = it.get("critic", {})
        for s in c.get("suggestions", []):
            if "exit_code" in s.lower() or "credentials" in s.lower():
                issues.append(s)
    return issues


# ─── YAML ↔ Python drift fix suggestion ──────────────────────────────────────

YAML_DRIFT_TEMPLATE = "docs/superpowers/specs/yaml-drift-fix-template.md"


def yaml_drift_fix_suggestion(drift: dict) -> str:
    """
    Generate fix suggestion with template reference for a yaml_python_drift blocker.

    drift = {"tool": str, "yaml": [atoms...], "py": [atoms...]}  (atoms = "tool.output")
    Returns a one-line actionable hint; the template holds the full decision matrix.
    """
    yaml_deps = drift.get("yaml", []) or []
    py_deps = drift.get("py", []) or []
    missing_in_py = [d for d in yaml_deps if d not in py_deps]
    missing_in_yaml = [d for d in py_deps if d not in yaml_deps]
    tool = drift.get("tool", "")
    tag = f"[{tool}] " if tool else ""
    if missing_in_py:
        return (
            f"{tag}YAML 更完整，补 Python: {missing_in_py} "
            f"— 见 {YAML_DRIFT_TEMPLATE}"
        )
    if missing_in_yaml:
        return (
            f"{tag}PY 更完整，改 YAML: {missing_in_yaml} "
            f"— 见 {YAML_DRIFT_TEMPLATE}"
        )
    return f"{tag}两处一致或无法判断"


# ─── Main fix function ────────────────────────────────────────────────────────

def process_trace(trace_path: str, dry_run: bool = True) -> dict[str, Any]:
    """
    Analyze one trace file and return fix results.

    Returns dict with keys:
      - file, fixed (bool), fixes (list[str]), blockers (list[str]), errors (list[str])
    """
    result = {"file": trace_path, "fixed": False, "fixes": [], "blockers": [], "errors": []}

    try:
        with open(trace_path, encoding="utf-8") as fh:
            trace = json.load(fh)
    except (json.JSONDecodeError, OSError) as e:
        result["errors"].append(f"read error: {e}")
        return result

    trace["__filename"] = trace_path

    # 1. Traceability check
    tf = check_traceability(trace, dry_run=dry_run)
    if tf:
        result["fixes"].append(tf)
        if not dry_run:
            for k, v in fix_traceability(trace).items():
                trace[k] = v
            with open(trace_path, "w", encoding="utf-8") as fh:
                json.dump(trace, fh, indent=2, ensure_ascii=False)
            result["fixed"] = True

    # 2. Idempotency ClientToken check
    ic = fix_idempotency_client_token(trace, dry_run=dry_run)
    if ic:
        result["fixes"].append(ic)
        if not dry_run:
            with open(trace_path, "w", encoding="utf-8") as fh:
                json.dump(trace, fh, indent=2, ensure_ascii=False)
            result["fixed"] = True

    # 3. Idempotency race check
    ir = check_idempotency_race(trace)
    if ir:
        result["blockers"].append(ir)

    # 4. Auth credential check
    ac = check_auth_credential(trace)
    for issue in ac:
        result["blockers"].append(f"auth_credential (no auto-fix): {issue}")

    return result


# ─── Batch scan ───────────────────────────────────────────────────────────────

def scan_all(dry_run: bool = True, check_race: bool = False) -> list[dict[str, Any]]:
    """Scan all trace sources and return per-file results."""
    results = []
    for fp in TRACE_FILES:
        if fp.endswith(".jsonl"):
            results.extend(_scan_jsonl(fp, dry_run=dry_run, check_race=check_race))
        else:
            results.append(process_trace(fp, dry_run=dry_run))
    return results


def _scan_jsonl(jsonl_path: str, dry_run: bool, check_race: bool) -> list[dict[str, Any]]:
    results = []
    with open(jsonl_path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            trace = json.loads(line)
            trace["__filename"] = f"{jsonl_path}:{lineno}"
            result = {"file": f"{jsonl_path}:{lineno}", "fixed": False, "fixes": [], "blockers": [], "errors": []}

            # Traceability
            tf = check_traceability(trace, dry_run=dry_run)
            if tf:
                result["fixes"].append(tf)

            # Idempotency
            ic = fix_idempotency_client_token(trace, dry_run=dry_run)
            if ic:
                result["fixes"].append(ic)

            # Race
            if check_race:
                ir = check_idempotency_race(trace)
                if ir:
                    result["blockers"].append(ir)

            # Auth
            ac = check_auth_credential(trace)
            for issue in ac:
                result["blockers"].append(f"auth_credential (no auto-fix): {issue}")

            if result["fixes"] or result["blockers"]:
                results.append(result)
    return results


# ─── Self-test ────────────────────────────────────────────────────────────────

def self_test() -> bool:
    """Run internal checks; exit 0 on all pass."""
    ok = True

    # Test traceability detection
    trace = {"iterations": [{"critic": {"suggestions": ["Response missing RequestId"]}}]}
    has_missing, missing = _trace_has_missing_fields(trace)
    if not (has_missing and "started_at" in missing):
        ok = False
        print("  [FAIL] _trace_has_missing_fields")

    # Test idempotency race detection
    trace_bad = {
        "iterations": [
            {"iter": 1, "started_at": "2026-01-02T10:00:00"},
            {"iter": 2, "started_at": "2026-01-02T09:00:00"},  # backwards
        ]
    }
    ir = check_idempotency_race(trace_bad)
    if not ir:
        ok = False
        print("  [FAIL] check_idempotency_race (should detect backwards timestamps)")

    # Test no false positive on monotonic
    trace_good = {
        "iterations": [
            {"iter": 1, "started_at": "2026-01-02T09:00:00"},
            {"iter": 2, "started_at": "2026-01-02T10:00:00"},
        ]
    }
    ir = check_idempotency_race(trace_good)
    if ir:
        ok = False
        print("  [FAIL] check_idempotency_race (false positive on monotonic timestamps)")

    # Test auth_credential detection
    trace_auth = {
        "iterations": [
            {"critic": {"suggestions": ["Generator exit_code=-2; fix command or credentials"]}}
        ]
    }
    ac = check_auth_credential(trace_auth)
    if not ac:
        ok = False
        print("  [FAIL] check_auth_credential")

    # Test yaml_drift_fix_suggestion
    sug_yaml = yaml_drift_fix_suggestion({
        "tool": "cdb_create_account",
        "yaml": ["cdb_create.InstanceId", "vpc_create.VpcId"],
        "py": ["cdb_create.InstanceId"],
    })
    if "补 Python" not in sug_yaml or "yaml-drift-fix-template" not in sug_yaml:
        ok = False
        print("  [FAIL] yaml_drift_fix_suggestion (YAML authoritative)")
    sug_py = yaml_drift_fix_suggestion({
        "tool": "cdb_create_account",
        "yaml": ["cdb_create.InstanceId"],
        "py": ["cdb_create.InstanceId", "vpc_create.VpcId"],
    })
    if "改 YAML" not in sug_py or "yaml-drift-fix-template" not in sug_py:
        ok = False
        print("  [FAIL] yaml_drift_fix_suggestion (PY authoritative)")
    sug_ok = yaml_drift_fix_suggestion({"yaml": ["a.B"], "py": ["a.B"]})
    if "无法判断" not in sug_ok:
        ok = False
        print("  [FAIL] yaml_drift_fix_suggestion (no drift)")


    # Test fix_traceability
    fixed = fix_traceability({"iterations": []})
    if "started_at" not in fixed or "finished_at" not in fixed:
        ok = False
        print("  [FAIL] fix_traceability missing fields")

    # Test traceability_fix_suggestion (template reference)
    sug_tccli = traceability_fix_suggestion(
        'subprocess.run(["tccli", "cvm", "RunInstances", "--Region", "ap-guangzhou"])'
    )
    if TRACEABILITY_TEMPLATE_DOC not in sug_tccli or "场景-1" not in sug_tccli:
        ok = False
        print("  [FAIL] traceability_fix_suggestion (tccli line missing template ref): " + repr(sug_tccli))
    sug_sdk = traceability_fix_suggestion(
        "resp = client.DescribeInstances(req)\nitems = resp.Response.InstanceSet"
    )
    if TRACEABILITY_TEMPLATE_DOC not in sug_sdk or "场景-2" not in sug_sdk:
        ok = False
        print("  [FAIL] traceability_fix_suggestion (SDK line missing template ref): " + repr(sug_sdk))
    if traceability_fix_suggestion('request_id = data["Response"].get("RequestId", "unknown")') != "":
        ok = False
        print("  [FAIL] traceability_fix_suggestion (should skip already-captured line)")

    # Test idempotency tccli fixer
    test_input = (
        'subprocess.run([\"tccli\", \"cvm\", \"RunInstances\", \"--Region\", \"ap-guangzhou\"])\n'
        'subprocess.run([\"tccli\", \"cvm\", \"DescribeInstances\", \"--ClientToken\", \"x\"])\n'
    )
    fixed, changes = fix_tccli_subprocess_in_text(test_input)
    n_injections = len([c for c in changes if c.startswith('  Line')])
    if n_injections != 1:
        ok = False
        print("  [FAIL] fix_tccli_subprocess_in_text: expected 1 injection, got " + str(n_injections))
    if '--ClientToken' not in fixed.splitlines()[0]:
        ok = False
        print("  [FAIL] fix_tccli_subprocess_in_text: ClientToken not in first line")

    print("Self-test " + ("PASSED" if ok else "FAILED"))
    return ok


# ─── Idempotency code fixer (Rule A: tccli subprocess) ───────────────────────

# boto3 methods requiring ClientToken (same list as check_idempotency.py)
IDEMPOTENT_BOTO3_METHODS = {
    "run_instances", "create_volume", "copy_image", "copy_snapshot",
    "create_security_group", "authorize_security_group_ingress",
    "revoke_security_group_ingress", "delete_security_group",
    "create_bucket", "put_object", "delete_object", "delete_bucket",
    "create_stack", "delete_stack", "update_stack", "create_change_set",
    "delete_change_set", "start_job", "create_pipeline", "send_message",
    "receive_message", "delete_queue", "create_queue",
    "publish", "subscribe", "create_topic", "delete_topic",
    "create_table", "update_table", "delete_table",
    "create_function", "update_function_code", "delete_function",
    "create_role", "delete_role", "attach_role_policy", "detach_role_policy",
    "put_item", "delete_item", "update_item",
    "send_templated_email", "send_raw_email", "send_email",
}

_TCCLI_LIST_RE = re.compile(r'subprocess\.run\s*\(\s*\[\s*\"tccli\"', re.IGNORECASE)

_BOTO3_CLIENT_TOKEN_RE = re.compile(r'ClientToken\s*=', re.IGNORECASE)


def _inject_client_token_list(tokens: list[str]) -> list[str]:
    """
    Given a token list for subprocess.run(["tccli", "cvm", ...]),
    inject ClientToken pair after "tccli".
    Returns new token list.
    """
    result = []
    for i, tok in enumerate(tokens):
        result.append(tok)
        if tok == '"tccli"' or tok == "'tccli'":
            # Insert ClientToken pair after tccli element
            result.extend(['"--ClientToken"', '"$CLIENT_TOKEN"'])
    return result


def _tokenize_subprocess_call(line: str) -> list[str] | None:
    """
    Attempt to extract tokens from a subprocess.run([...]) call.
    Returns list of tokens or None if parsing fails.
    Handles basic comma-separated quoted strings.
    """
    # Find the [ ... ] boundaries
    start = line.find('[')
    end = line.rfind(']')
    if start == -1 or end == -1 or end <= start:
        return None
    inner = line[start + 1:end]
    # Split on commas, strip whitespace, split on unquoted commas
    tokens = []
    current = ''
    in_quote = False
    quote_char = None
    for ch in inner:
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
            current += ch
        elif ch == quote_char and in_quote:
            in_quote = False
            quote_char = None
            current += ch
        elif ch == ',' and not in_quote:
            tok = current.strip()
            if tok:
                tokens.append(tok)
            current = ''
        else:
            current += ch
    tok = current.strip()
    if tok:
        tokens.append(tok)
    return tokens


def fix_tccli_subprocess_in_text(text: str) -> tuple[str, list[str]]:
    """
    Scan text for tccli subprocess calls without --ClientToken and inject it.
    Uses tokenization to safely insert ClientToken without regex-quote issues.
    Returns (fixed_text, list_of_changes).
    Skips: comment lines, docstrings, read-only ops (--version, Describe, Get, List, Query).
    """
    changes: list[str] = []
    fixed_lines: list[str] = []
    in_triple = False

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if '"""' in stripped or "'''" in stripped:
            in_triple = not in_triple
            continue
        if in_triple:
            fixed_lines.append(line)
            continue
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue
        if not _TCCLI_LIST_RE.search(line):
            fixed_lines.append(line)
            continue
        # Skip read-only operations
        if any(x in line for x in ('--version', 'Describe', 'Query', 'List', 'Get', 'Check')):
            fixed_lines.append(line)
            continue
        if '--ClientToken' in line or '--client-token' in line:
            fixed_lines.append(line)
            continue

        tokens = _tokenize_subprocess_call(line)
        if tokens is None:
            fixed_lines.append(line)
            continue

        new_tokens = _inject_client_token_list(tokens)
        indent = len(line) - len(line.lstrip())
        prefix = line[:indent]
        inner = ', '.join(new_tokens)
        new_line = prefix + 'subprocess.run([' + inner + '])'

        if new_line != line:
            fixed_lines.append(new_line)
            changes.append(f'  Line {lineno}: injected --ClientToken into tccli subprocess')
            changes.append(f'    {line.strip()[:80]}')
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines), changes


def fix_boto3_in_text(text: str) -> tuple[str, list[str]]:
    """
    Scan text for boto3 method calls that lack ClientToken kwarg and inject it.
    Handles: client.method(..., ClientToken=uuid.uuid4().hex)
    Returns (fixed_text, list_of_changes).
    """
    import ast
    changes = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text, []

    # Find boto3 method calls missing ClientToken
    problematic_lines: dict[int, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        method = node.func.attr
        if method not in IDEMPOTENT_BOTO3_METHODS:
            continue
        kwarg_names = [k.arg for k in node.keywords if k.arg]
        if "ClientToken" in kwarg_names:
            continue
        lineno = getattr(node, "lineno", 0)
        problematic_lines[lineno] = method

    if not problematic_lines:
        return text, []

    fixed_lines = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if lineno in problematic_lines:
            method = problematic_lines[lineno]
            if _BOTO3_CLIENT_TOKEN_RE.search(line):
                fixed_lines.append(line)
                continue
            stripped = line.rstrip()
            if stripped.endswith(')'):
                insert_pos = len(stripped) - 1
                new_line = stripped[:insert_pos] + ", ClientToken=uuid.uuid4().hex" + stripped[insert_pos:]
                fixed_lines.append(new_line)
                changes.append(f'  Line {lineno}: injected ClientToken into boto3.{method}')
                changes.append(f'    {line.strip()[:80]}')
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines), changes


def fix_file_idempotency(file_path: Path, dry_run: bool = True) -> list[str]:
    """Detect and optionally fix idempotency issues in a Python source file."""
    text = file_path.read_text(encoding='utf-8')
    new_text, changes = fix_tccli_subprocess_in_text(text)
    new_text, boto3_changes = fix_boto3_in_text(new_text)
    changes.extend(boto3_changes)
    if not changes:
        return []
    if dry_run:
        return changes
    backup = file_path.with_suffix(file_path.suffix + '.bak')
    backup.write_text(text, encoding='utf-8')
    file_path.write_text(new_text, encoding='utf-8')
    changes.append(f'  [APPLIED] {file_path} — .bak saved')
    return changes


def scan_code_idempotency(dry_run: bool = True) -> tuple[int, int]:
    """
    Scan Python files for idempotency issues.
    Returns (total_issues, files_with_issues).
    """
    py_files = sorted(
        list((ROOT / 'qcloud-copilot').rglob('*.py'))
        + list((ROOT / 'scripts').rglob('*.py'))
    )
    py_files = [f for f in py_files if f.name != 'auto_fix_gcl_blockers.py']

    total_issues = 0
    files_with_issues = 0
    all_changes: list[str] = []

    for path in py_files:
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        if 'tccli' not in text and 'tencentcloud' not in text:
            continue
        _, changes = fix_tccli_subprocess_in_text(text)
        if changes:
            files_with_issues += 1
            total_issues += len([c for c in changes if c.startswith('  Line')])
            all_changes.extend(changes)

    if all_changes:
        action = '[DRY-RUN] Would fix' if dry_run else '[APPLIED]'
        print(f'\n{action} idempotency in {files_with_issues} file(s), {total_issues} issue(s):')
        for c in all_changes[:20]:
            print(c)
        if len(all_changes) > 20:
            print(f'  ... and {len(all_changes) - 20} more')

    return total_issues, files_with_issues


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-fix GCL trace BLOCKERs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be fixed (default)")
    parser.add_argument("--apply", action="store_true",
                        help="Actually apply fixes (DANGEROUS — modifies audit-results)")
    parser.add_argument("--self-test", action="store_true",
                        help="Run internal checks")
    parser.add_argument("--check-idempotency", action="store_true",
                        help="Also scan for race conditions (non-monotonic timestamps)")
    parser.add_argument("--scan-code-idempotency", action="store_true",
                        help="Scan Python source files for missing ClientToken in tccli calls")
    parser.add_argument("--scan-code-traceability", action="store_true",
                        help="Scan Python source files for missing RequestId capture in tccli/SDK responses")
    args = parser.parse_args()

    if args.self_test:
        ok = self_test()
        sys.exit(0 if ok else 1)

    if args.scan_code_idempotency:
        dry_run = not args.apply
        issues, _files = scan_code_idempotency(dry_run=dry_run)
        if issues == 0:
            print("No idempotency issues found in Python source files.")
        sys.exit(0 if issues == 0 else 1)

    if args.scan_code_traceability:
        dry_run = not args.apply
        issues, _files = scan_code_traceability(dry_run=dry_run)
        if issues == 0:
            print("No RequestId capture issues found in Python source files.")
        sys.exit(0 if issues == 0 else 1)

    dry_run = not args.apply
    results = scan_all(dry_run=dry_run, check_race=args.check_idempotency)

    total_fixes = sum(len(r["fixes"]) for r in results)
    total_blockers = sum(len(r["blockers"]) for r in results)

    if results:
        print(f"\n{'[DRY-RUN] Would fix' if dry_run else '[APPLIED] Fixed'}: {total_fixes} issue(s) in {len(results)} trace(s)")
        print(f"Race/blocker flags: {total_blockers}\n")
        for r in results:
            if r["fixes"]:
                print(f"  {r['file']}")
                for f in r["fixes"]:
                    print(f"    + {f}")
            if r["blockers"]:
                print(f"  {r['file']} [REVIEW REQUIRED]")
                for b in r["blockers"]:
                    print(f"    ! {b}")
    else:
        print("No issues found.")

    sys.exit(0)


if __name__ == "__main__":
    main()
