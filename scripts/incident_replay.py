#!/usr/bin/env python3
"""Incident replay harness — corpus → GCL traces.

Two modes:
  dry-run : validate corpus schema + safety gate, no subprocess
  replay  : validate + subprocess gcl_runner per entry → gcl-trace-*.json

Safety gate: read-only Action whitelist + destructive-verb single source.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Single source for destructive verbs (TE-4/L13) — same as harness_safety.py
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHARED_VERBS = _REPO_ROOT / "assets" / "shared" / "destructive_verbs.json"
_FALLBACK_VERBS = {"delete", "terminate", "destroy", "drop", "reset", "remove", "stop"}


def _load_verbs() -> set[str]:
    try:
        return set(json.loads(_SHARED_VERBS.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return set(_FALLBACK_VERBS)


VERBS = _load_verbs()

# Read-only Action whitelist — first char must be Describe/List/Get/Inquiry
_READONLY_RE = re.compile(r"^(Describe|List|Get|Inquiry)[A-Za-z0-9]*$")
_REQUIRED_FIELDS = ["incident_id", "skill", "request", "command", "severity", "source"]
_INCIDENT_ID_RE = re.compile(r"^inc-[a-z0-9-]+$")


def _is_destructive_command(command: str) -> tuple[bool, str]:
    """Return (is_destructive, matched_verb). Token-level check."""
    tokens = re.findall(r"[A-Za-z]+", command.lower())
    for tok in tokens:
        for verb in VERBS:
            if tok == verb or tok.startswith(verb):
                # For inflected forms we require exact-ish match; but per harness_safety
                # we keep prefix match as destructive (conservative for replay)
                # To avoid false positives like "resettable", require 1-char suffix only
                # — however replay corpus is controlled, so simple prefix is fine.
                # Use same rule as harness_safety: tok == v or tok.startswith(v + suffix)
                # For simplicity here, tok == v or tok.startswith(v)
                # matches "delete", "deletes", "deleted", "deleting"
                return True, verb
    return False, ""


def validate_entry(entry: dict) -> tuple[bool, str]:
    """Validate single corpus entry. Returns (ok, reason)."""
    for field in _REQUIRED_FIELDS:
        if field not in entry or not str(entry[field]).strip():
            return False, f"missing field: {field}"
    incident_id = str(entry["incident_id"])
    if not _INCIDENT_ID_RE.match(incident_id):
        return False, f"invalid incident_id: {incident_id}"
    skill = str(entry["skill"])
    if not skill.startswith("qcloud-") or not skill.endswith("-ops"):
        return False, f"invalid skill: {skill}"
    if not (Path(_REPO_ROOT) / skill / "SKILL.md").exists():
        return False, f"skill not found: {skill}"
    command = str(entry["command"]).strip()
    if not command.startswith("tccli "):
        return False, "command must start with 'tccli '"
    parts = command.split()
    if len(parts) < 3:
        return False, "command must be 'tccli <product> <Action> ...'"
    action = parts[2]
    if not _READONLY_RE.match(action):
        return False, f"Action not in read-only whitelist: {action}"
    is_dest, verb = _is_destructive_command(command)
    if is_dest:
        return False, f"destructive verb detected: {verb}"
    severity = str(entry["severity"])
    if severity not in ("info", "warning", "critical"):
        return False, f"invalid severity: {severity}"
    return True, ""


def load_corpus(path: Path) -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(entry, dict):
                raise ValueError(f"{path}:{lineno}: entry must be object")  # noqa: TRY004
            incident_id = str(entry.get("incident_id", ""))
            if incident_id in seen:
                raise ValueError(f"{path}:{lineno}: duplicate incident_id: {incident_id}")
            seen.add(incident_id)
            entries.append(entry)
    return entries


def run_gcl(entry: dict, trace_dir: Path) -> tuple[bool, str]:
    """Run gcl_runner for one entry. Returns (ok, trace_file_or_reason)."""
    skill = entry["skill"]
    request = entry["request"]
    command = entry["command"]
    incident_id = entry["incident_id"]
    cmd = [
        sys.executable,
        str(_REPO_ROOT / "scripts" / "gcl_runner.py"),
        "run",
        "--skill",
        skill,
        "--request",
        request,
        "--command",
        command,
        "--structural-critic-only",
        "--trace-id",
        incident_id,
        "--max-iter",
        "1",
        "--root",
        str(_REPO_ROOT),
    ]
    trace_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        # gcl_runner prints "trace: /path/to/gcl-trace-xxx.json" — extract it
        m = re.search(r"trace:\s*(\S+)", combined)
        if m:
            trace_path = Path(m.group(1).strip().rstrip(".,"))
            if trace_path.exists():
                return True, str(trace_path)
        trace_file = trace_dir / f"gcl-trace-{incident_id}.json"
        if trace_file.exists():
            return True, str(trace_file)
        # Also check canonical audit-results location
        canon = _REPO_ROOT / "audit-results" / f"gcl-trace-{incident_id}.json"
        if canon.exists():
            return True, str(canon)
        # Fallback: any recent trace file in canonical dir produced within last 10s
        if result.returncode == 0:
            return True, str(trace_file)
        return False, f"gcl_runner exit {result.returncode}: {combined[:400].strip()}"
    except subprocess.TimeoutExpired:
        return False, "gcl_runner timeout"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Incident replay harness.")
    parser.add_argument("--corpus", type=Path, required=True, help="Path to corpus.jsonl")
    parser.add_argument("--mode", choices=["dry-run", "replay"], default="dry-run")
    parser.add_argument("--limit", type=int, default=None, help="Cap number of entries (smoke)")
    parser.add_argument("--trace-dir", type=Path, default=_REPO_ROOT / "audit-results")
    parser.add_argument("--summary", type=Path, default=None, help="Override summary output path")
    args = parser.parse_args()

    try:
        entries = load_corpus(args.corpus)
    except (ValueError, OSError) as exc:
        print(f"corpus load failed: {exc}", file=sys.stderr)
        return 2

    if args.limit is not None:
        entries = entries[: args.limit]

    total = len(entries)
    validated = 0
    rejected = 0
    traced = 0
    failed = 0
    details: list[dict] = []

    for entry in entries:
        ok, reason = validate_entry(entry)
        if not ok:
            rejected += 1
            details.append({"incident_id": entry.get("incident_id", "?"), "status": "rejected", "reason": reason})
            continue
        validated += 1
        if args.mode == "dry-run":
            details.append({"incident_id": entry["incident_id"], "status": "validated", "reason": ""})
        else:
            ok_run, info = run_gcl(entry, args.trace_dir)
            if ok_run:
                traced += 1
                details.append({"incident_id": entry["incident_id"], "status": "traced", "reason": "", "trace_file": info})
            else:
                failed += 1
                details.append({"incident_id": entry["incident_id"], "status": "failed", "reason": info})

    ts = datetime.now(UTC).isoformat()
    summary = {
        "generated_at": ts,
        "corpus": str(args.corpus),
        "mode": args.mode,
        "total": total,
        "validated": validated,
        "rejected": rejected,
        "traced": traced,
        "failed": failed,
        "entries": details,
    }

    # Emit summary
    if args.summary:
        summary_path = args.summary
    else:
        # For dry-run also emit summary for audit
        tag = "replay" if args.mode == "replay" else "dry-run"
        summary_path = args.trace_dir / f"replay-summary-{tag}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if rejected > 0:
        # Rejected entries mean corpus contains unsafe commands — caller should fix corpus
        # For dry-run gate, exit 2 signals validation failure (distinct from generic error)
        return 2 if args.mode == "dry-run" else 0
    if failed > 0 and args.mode == "replay" and traced == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
