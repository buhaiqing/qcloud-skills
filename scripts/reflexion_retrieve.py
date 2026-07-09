#!/usr/bin/env python3
"""Reflexion memory retrieval — load top-N relevant failure patterns for a skill.

Usage:
  python3 scripts/reflexion_retrieve.py retrieve --skill qcloud-cvm-ops
  python3 scripts/reflexion_retrieve.py retrieve --skill qcloud-cvm-ops --command TerminateInstances --top-n 5
  python3 scripts/reflexion_retrieve.py retrieve --skill qcloud-cvm-ops --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from failure_pattern_extract import parse_existing

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE_PATH = ROOT / "docs" / "failure-patterns.md"


def load_failure_patterns(
    skill: str,
    command: str | None = None,
    top_n: int = 3,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Load and rank failure patterns for a given skill.

    Scoring:
      - 3 points if pattern["skill"] == skill
      - 2 points if command given and (command in pattern.command or command in pattern.error)
      - 1 point otherwise (filtered out unless skill matches or command matches)
    Tie-break by count descending.

    Returns:
        List of the original dicts (no mutation of the store), sorted by score desc.
        Only includes patterns with score >= 2 (skill match or command substring match).
    """
    store_path = path or DEFAULT_STORE_PATH
    patterns = parse_existing(store_path)

    scored: list[tuple[int, int, dict[str, Any]]] = []  # (score, count, pattern)

    for key, p in patterns.items():
        score = 0
        p_skill = p.get("skill", "")
        p_command = p.get("command", "")
        p_error = p.get("error", "")
        p_count = p.get("count", 0)

        if p_skill == skill:
            score = 3
        elif command and (command in (p_command or "") or command in (p_error or "")):
            score = 2
        else:
            continue

        scored.append((score, p_count, p))

    # Sort by score desc, then by count desc (tie-break)
    scored.sort(key=lambda x: (-x[0], -x[1]))

    # Take top_n and return original dicts
    return [p for _, _, p in scored[:top_n]]


def _mask_credentials(text: str) -> str:
    """Replace credential-like tokens with <masked>.

    Conservative masking for obvious secret shapes:
      - SecretKey/secret_key followed by = and token
      - AKID... (Tencent Cloud SecretId)
      - password=... patterns
      - Long base64-ish secrets (40+ chars of [A-Za-z0-9+/=])
    """
    if not text:
        return text

    # Pattern 1: SecretKey=... or secret_key=...
    text = re.sub(r"(SecretKey|secret_key)\s*=\s*[^\s,)]+", r"\1=<masked>", text)

    # Pattern 2: password=... (common in error messages)
    text = re.sub(r"(password|Password|PASSWORD)\s*=\s*[^\s,)]+", r"\1=<masked>", text)

    # Pattern 3: AKID... (Tencent Cloud SecretId pattern)
    text = re.sub(r"\bAKID[A-Za-z0-9]{16,}\b", "<masked>", text)

    text = re.sub(r"[A-Za-z0-9+/]{40,}={0,2}", "<masked>", text)

    return text


def format_for_injection(patterns: list[dict[str, Any]]) -> str:
    """Return a compact markdown block for Generator context injection.

    Format:
      - [<skill>] error=`error` -> fix=`fix` (count=N)

    Credentials are masked. Returns empty string (not None) if patterns empty.
    """
    if not patterns:
        return ""

    lines = []
    for p in patterns:
        skill = p.get("skill", "—")
        error = _mask_credentials(p.get("error", "—"))
        fix = _mask_credentials(p.get("fix", "—"))
        count = p.get("count", 0)

        lines.append(f"- [{skill}] error=`{error}` -> fix=`{fix}` (count={count})")

    return "\n".join(lines)


def cmd_retrieve(args: argparse.Namespace) -> int:
    """Handle the 'retrieve' subcommand."""
    patterns = load_failure_patterns(
        skill=args.skill,
        command=args.command,
        top_n=args.top_n,
        path=args.path,
    )

    if args.json:
        # Output as JSON list
        output = json.dumps(patterns, indent=2, ensure_ascii=False)
        print(output)
    else:
        # Output as markdown block
        output = format_for_injection(patterns)
        print(output)

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="Reflexion memory retrieval for failure patterns",
        prog="reflexion_retrieve",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # retrieve subcommand
    retrieve_parser = subparsers.add_parser(
        "retrieve",
        help="Retrieve top-N relevant failure patterns for a skill",
    )
    retrieve_parser.add_argument(
        "--skill",
        required=True,
        help="Target skill name (e.g., qcloud-cvm-ops)",
    )
    retrieve_parser.add_argument(
        "--command",
        default=None,
        help="Optional command to improve ranking (substring match)",
    )
    retrieve_parser.add_argument(
        "--top-n",
        type=int,
        default=3,
        help="Number of patterns to return (default: 3)",
    )
    retrieve_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON list instead of markdown block",
    )
    retrieve_parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Override path to failure-patterns.md",
    )
    retrieve_parser.set_defaults(func=cmd_retrieve)

    return parser


def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
