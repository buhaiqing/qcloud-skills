#!/usr/bin/env python3
"""tccli_shadow.py — Shadow rehearsal shim for tccli (maturity gap #5).

Record real tccli responses ONCE, then replay them deterministically so the
full GCL Generator→Critic loop rehearses destructive operations with ZERO
cloud side-effects.

Modes
-----
exec    Replay-only. Looks up a recorded fixture for the normalized command.
        HIT  → stdout = stored response, exit = stored exit_code.
        MISS → stderr ``SHADOW_MISS:<key>``, exit 2. NEVER calls real tccli.
record  Wraps a REAL tccli call (explicit opt-in), sanitizes and stores the
        response as a fixture. Requires ``--yes-real-api``; destructive
        commands additionally require ``--allow-destructive-record``.
key     Print the normalized lookup key for a command (debugging).

Fixture layout: ``audit-results/shadow-fixtures/<key>.json`` (see spec:
docs/superpowers/specs/shadow-rehearsal-design.md).

CLI usage::

    python3 scripts/tccli_shadow.py key -- 'tccli cvm DescribeInstances --region ap-guangzhou'
    python3 scripts/tccli_shadow.py exec -- 'tccli cvm TerminateInstances --instanceIds ...'
    python3 scripts/tccli_shadow.py record --yes-real-api -- 'tccli cvm DescribeInstances ...'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "audit-results" / "shadow-fixtures"

SCHEMA_VERSION = "v1"

# Resource-id prefixes replaced by stable placeholders so rehearsals match on
# shape, not specific ids. Region is kept (responses vary by region).
_ID_PLACEHOLDERS = (
    ("ins-", "ins-*"),
    ("sg-", "sg-*"),
    ("lb-", "lb-*"),
    ("vpc-", "vpc-*"),
    ("subnet-", "subnet-*"),
    ("disk-", "disk-*"),
    ("cbs-", "cbs-*"),
    ("snap-", "snap-*"),
    ("lh-", "lh-*"),
    ("tdsqlsqlserver-", "tdsqlsqlserver-*"),
)

# Destructive verbs (aligned with harness_safety / shared destructive_verbs).
DESTRUCTIVE_ACTIONS = frozenset({
    "terminate", "delete", "drop", "destroy", "release", "stop",
    "reset", "detach", "disassociate", "clear", "flush", "purge",
    "isolate", "unbind", "disable", "revoke", "offline",
})


def is_destructive_command(command: str) -> bool:
    """Match the parsed action's CamelCase words against the verb set.

    StopInstances → {stop, instances} → destructive; DescribeInstances is not.
    """
    action = _parse_action(command)[1]
    if not action:
        return False
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", action)
    return any(w.lower() in DESTRUCTIVE_ACTIONS for w in words)


def mask_secrets_text(text: str) -> str:
    """Credential masking aligned with gcl_runner.mask_secrets (L3)."""
    try:
        from gcl_runner import mask_secrets  # local import to avoid cycle
        return mask_secrets(text)
    except Exception:  # noqa: BLE001 — fallback keeps masking working standalone
        text = re.sub(r"(AKID[A-Za-z0-9]+)", "<masked-secret-id>", text)
        text = re.sub(r'(?i)(secret["\']?\s*[:=,]\s*"?)[A-Za-z0-9+/=]+', r"\1<masked>", text)
        return text


def parse_tccli_command(command: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Parse 'tccli <product> <Action> [--flag value ...]' → (product, action, flags).

    Deliberately a local copy of flag-walking (cf. cli_param_validator):
    the shim must stay importable and correct WITHOUT pulling in the GCL
    runner's KB machinery. Raises ValueError when the command is not a
    well-formed tccli invocation.
    """
    tokens = shlex.split(command)
    if not tokens or tokens[0] != "tccli":
        raise ValueError(f"not a tccli command: {command!r}")
    if len(tokens) < 3:
        raise ValueError(f"incomplete tccli command: {command!r}")
    product, action = tokens[1], tokens[2]
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", product) or not re.fullmatch(r"[A-Za-z0-9]+", action):
        raise ValueError(f"suspicious product/action token: {product!r} {action!r}")
    flags: list[tuple[str, str]] = []
    i = 3
    while i < len(tokens):
        tok = tokens[i]
        if not tok.startswith("-"):
            raise ValueError(f"unexpected positional token: {tok!r}")
        if not tok.startswith("--"):
            raise ValueError(f"unsupported short option: {tok!r}")
        flag = tok[2:].lower()
        # tccli allows multi-value flags: values run until the next --flag.
        values: list[str] = []
        j = i + 1
        while j < len(tokens) and not tokens[j].startswith("--"):
            values.append(tokens[j])
            j += 1
        flags.append((flag, " ".join(values)))
        i = j
    return product, action, flags


def _placeholder(value: str) -> str:
    low = value.lower()
    for prefix, ph in _ID_PLACEHOLDERS:
        if low.startswith(prefix):
            return ph
    return value


def normalize_command(
    command: str,
) -> dict[str, Any]:
    """Normalize to the canonical rehearsal shape.

    Flag names lowercased; values get resource-id placeholders. Output is the
    dict stored under fixture ``normalized`` and hashed into the lookup key.
    """
    product, action, flags = parse_tccli_command(command)
    flag_map: dict[str, str] = {}
    for name, value in sorted(flags):
        # Placeholder each value token so arity survives: "ins-a ins-b" and
        # "ins-c" must NOT collapse onto the same fixture key.
        flag_map[name] = " ".join(_placeholder(v) for v in value.split())
    return {"product": product.lower(), "action": action, "flags": flag_map}


def fixture_key(normalized: dict[str, Any]) -> str:
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode()).hexdigest()[:16]


def command_key(command: str) -> str:
    return fixture_key(normalize_command(command))


# ---------------------------------------------------------------------------
# Fixture store
# ---------------------------------------------------------------------------

def save_fixture(
    command: str,
    *,
    stdout: str,
    stderr: str,
    exit_code: int,
    fixture_dir: Path | None = None,
) -> Path:
    normalized = normalize_command(command)
    key = fixture_key(normalized)
    out_dir = fixture_dir or FIXTURE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "key": key,
        "normalized": normalized,
        "raw_command_masked": mask_secrets_text(command),
        "stdout": mask_secrets_text(stdout),
        "stderr": mask_secrets_text(stderr),
        "exit_code": int(exit_code),
        "destructive": is_destructive_command(command),
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    path = out_dir / f"{key}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_fixture(key: str, fixture_dir: Path | None = None) -> dict[str, Any] | None:
    path = (fixture_dir or FIXTURE_DIR) / f"{key}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def _parse_action(command: str) -> tuple[str, str]:
    try:
        product, action, _ = parse_tccli_command(command)
        return product, action
    except ValueError:
        return "", ""


def cmd_exec(args: argparse.Namespace) -> int:
    command = args.command
    try:
        normalized = normalize_command(command)
    except ValueError as exc:
        print(f"SHADOW_REJECT: {exc}", file=sys.stderr)
        return 3
    key = fixture_key(normalized)

    fixture_dir = (
        Path(args.fixture_dir) if args.fixture_dir
        else (Path(os.environ["SHADOW_FIXTURE_DIR"]) if os.environ.get("SHADOW_FIXTURE_DIR") else None)
    )
    fixture = load_fixture(key, fixture_dir)
    if fixture is None:
        print(f"SHADOW_MISS:{key}", file=sys.stderr)
        return 2
    sys.stdout.write(fixture.get("stdout", ""))
    if fixture.get("stderr"):
        sys.stderr.write(fixture["stderr"])
    return int(fixture.get("exit_code", 0))


def cmd_record(args: argparse.Namespace) -> int:
    command = args.command
    try:
        parse_tccli_command(command)
    except ValueError as exc:
        print(f"RECORD_REJECT: {exc}", file=sys.stderr)
        return 3
    if not args.yes_real_api:
        # L21 deny-by-default: recording hits the REAL cloud API.
        print("RECORD_REJECT: record mode hits the real API; pass --yes-real-api", file=sys.stderr)
        return 4
    if is_destructive_command(command) and not args.allow_destructive_record:
        print(
            "RECORD_REJECT: destructive commands require --allow-destructive-record "
            "(and MUST already be guarded upstream)",
            file=sys.stderr,
        )
        return 4

    argv = shlex.split(command)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=args.timeout, check=False)
    except subprocess.TimeoutExpired:
        print(f"RECORD_TIMEOUT: no fixture written (limit {args.timeout}s)", file=sys.stderr)
        return 5
    path = save_fixture(
        command,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        exit_code=proc.returncode,
        fixture_dir=Path(args.fixture_dir) if args.fixture_dir else None,
    )
    print(f"recorded: {path} (exit={proc.returncode})", file=sys.stderr)
    return 0


def cmd_key(args: argparse.Namespace) -> int:
    try:
        normalized = normalize_command(args.command)
    except ValueError as exc:
        print(f"KEY_REJECT: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"key": fixture_key(normalized), "normalized": normalized},
                     ensure_ascii=False, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)

    p_exec = sub.add_parser("exec", help="replay a recorded response (never touches network)")
    p_exec.add_argument("--fixture-dir", default=None)
    p_exec.add_argument("command")
    p_exec.set_defaults(fn=cmd_exec)

    p_rec = sub.add_parser("record", help="run REAL tccli once and store the response")
    p_rec.add_argument("--fixture-dir", default=None)
    p_rec.add_argument("--yes-real-api", action="store_true",
                       help="confirm this wraps a REAL cloud API call")
    p_rec.add_argument("--allow-destructive-record", action="store_true",
                       help="permit recording DESTRUCTIVE commands (use with extreme care)")
    p_rec.add_argument("--timeout", type=int, default=120)
    p_rec.add_argument("command")
    p_rec.set_defaults(fn=cmd_record)

    p_key = sub.add_parser("key", help="print normalized lookup key")
    p_key.add_argument("command")
    p_key.set_defaults(fn=cmd_key)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
