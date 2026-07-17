#!/usr/bin/env python3
"""Reflexion memory retrieval — load top-N relevant failure patterns for a skill.

Usage:
  python3 scripts/reflexion_retrieve.py retrieve --skill qcloud-cvm-ops
  python3 scripts/reflexion_retrieve.py retrieve --skill qcloud-cvm-ops --command TerminateInstances --top-n 5
  python3 scripts/reflexion_retrieve.py retrieve --skill qcloud-cvm-ops --json

Scoring formula (P0-C):
  score = base_score × severity_weight × recency_decay

  base_score:
    - 3 if pattern["skill"] == skill
    - 2 if command given and command in pattern["command"] or pattern["error"]
    - filtered out otherwise

  severity_weight:
    - 3.0  critical  — Safety=0 (credential leak, destructive without confirm)
    - 2.0  major    — Correctness=0 or Idempotency=0
    - 1.0  minor    — all other rubric failures

  recency_decay:
    - < 7 days:  1.0
    - 7–30 days: 0.7
    - 30–90 days: 0.3
    - > 90 days: 0.1
    - unknown (no last_seen): 1.0 (treat as recent for existing patterns)

Tie-break: composite_score desc, then count desc.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from _failure_pattern_store import (
    parse_existing, load_all_layers,
    HOT_PATH, WARM_PATH, COLD_PATH,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE_PATH = HOT_PATH  # hot layer === default

# P0-C: Severity weight constants
SEVERITY_WEIGHT = {
    "critical": 3.0,   # Safety=0
    "major": 2.0,     # Correctness=0 or Idempotency=0
    "minor": 1.0,     # all others
}


def _parse_severity(severity: str | None) -> float:
    """Return severity_weight, defaulting to minor (1.0) for unknown."""
    if severity:
        s = severity.lower()
        if s in SEVERITY_WEIGHT:
            return SEVERITY_WEIGHT[s]
    return 1.0


def recency_decay(last_seen: str | None) -> float:
    """Return recency decay multiplier.

    last_seen format: YYYY-MM or YYYY-MM-DD
    Unknown/missing -> 1.0 (no penalty for existing historical patterns).
    """
    if not last_seen:
        return 1.0
    try:
        # Accept both YYYY-MM and YYYY-MM-DD
        if len(last_seen) >= 10:
            last_dt = datetime.strptime(last_seen[:10], "%Y-%m-%d")
        else:
            last_dt = datetime.strptime(last_seen, "%Y-%m")
    except ValueError:
        return 1.0

    # Use naive datetime for comparison to avoid naive/aware mismatch
    now = datetime.now()
    delta_days = (now - last_dt).days
    if delta_days < 7:
        return 1.0
    elif delta_days < 30:
        return 0.7
    elif delta_days < 90:
        return 0.3
    else:
        return 0.1


def load_failure_patterns(
    skill: str,
    command: str | None = None,
    top_n: int = 3,
    path: Path | None = None,
    layer: str | None = None,
) -> list[dict[str, Any]]:
    """Load and rank failure patterns for a given skill (P0-B layered).

    Scoring (P0-C composite score):
      score = base_score × severity_weight × recency_decay

    Returns:
        List of the original dicts (no mutation of the store), sorted by
        composite_score desc then count desc.
        Only includes patterns with composite_score >= 2.0.
    """
    # P0-B: layered load when no path override
    if path is None and layer is None:
        hot, warm, cold = load_all_layers()
        # Cross-layer dedup: prefer hot > warm > cold
        seen_keys = set()
        scored: list[tuple[float, int, dict[str, Any]]] = []
        for patterns in [hot, warm, cold]:
            for key, p in patterns.items():
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                result = _score_pattern(p, skill, command)
                if result is not None:
                    scored.append((*result, p))
    elif path:
        # Legacy single-file path
        patterns = parse_existing(path)
        seen_keys = set()
        scored = []
        for key, p in patterns.items():
            if key in seen_keys:
                continue
            seen_keys.add(key)
            result = _score_pattern(p, skill, command)
            if result is not None:
                scored.append((*result, p))
    else:
        # Single layer requested
        layer_path = {"hot": HOT_PATH, "warm": WARM_PATH, "cold": COLD_PATH}.get(layer or "hot", HOT_PATH)
        patterns = parse_existing(layer_path) if layer_path.exists() else {}
        seen_keys = set()
        scored = []
        for key, p in patterns.items():
            if key in seen_keys:
                continue
            seen_keys.add(key)
            result = _score_pattern(p, skill, command)
            if result is not None:
                scored.append((*result, p))

    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [p for _, _, p in scored[:top_n]]


def _score_pattern(
    p: dict[str, Any],
    skill: str,
    command: str | None,
) -> tuple[float, int] | None:
    """Score one pattern. Returns (composite_score, count) or None if filtered out."""
    p_skill = p.get("skill", "")
    p_command = p.get("command", "")
    p_error = p.get("error", "")

    # Base score
    if p_skill == skill:
        base_score = 3.0
    elif command and (command in (p_command or "") or command in (p_error or "")):
        base_score = 2.0
    else:
        return None

    severity = p.get("severity")
    severity_weight = _parse_severity(severity)
    last_seen = p.get("last_seen") or p.get("first_seen")
    decay = recency_decay(last_seen)
    composite = base_score * severity_weight * decay

    if composite < 2.0:
        return None

    return (composite, p.get("count", 0))


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

    # Pattern 4: long base64-ish tokens
    text = re.sub(r"[A-Za-z0-9+/]{40,}={0,2}", "<masked>", text)

    return text


def _severity_label(severity: str | None) -> str:
    """Return a compact severity badge for injection output."""
    if not severity:
        return ""
    return f" [⚠️ {severity}]"


def format_for_injection(patterns: list[dict[str, Any]]) -> str:
    """Return a compact markdown block for Generator context injection.

    P0-C output format:
      - [<skill>] error=`error` -> fix=`fix` (count=N, sev=severity, age=last_seen)

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
        severity = p.get("severity") or ""
        last_seen = p.get("last_seen") or p.get("first_seen", "—")

        sev_tag = _severity_label(severity) if severity else ""
        lines.append(
            f"- [{skill}] error=`{error}` -> fix=`{fix}` "
            f"(count={count}, last_seen={last_seen}{sev_tag})"
        )

    return "\n".join(lines)


def cmd_retrieve(args: argparse.Namespace) -> int:
    """Handle the 'retrieve' subcommand."""
    patterns = load_failure_patterns(
        skill=args.skill,
        command=args.command,
        top_n=args.top_n,
        path=args.path,
        layer=getattr(args, "layer", None),
    )

    if args.json:
        # Output as JSON list (includes scoring metadata for debugging)
        enriched = []
        for p in patterns:
            sev = p.get("severity")
            last_seen = p.get("last_seen") or p.get("first_seen")
            sev_weight = _parse_severity(sev)
            decay = recency_decay(last_seen)
            base = 3.0 if p.get("skill") == args.skill else 2.0
            enriched.append({
                **p,
                "_score": round(base * sev_weight * decay, 3),
                "_severity_weight": sev_weight,
                "_recency_decay": decay,
            })
        output = json.dumps(enriched, indent=2, ensure_ascii=False)
        print(output)
    else:
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
    retrieve_parser.add_argument(
        "--layer",
        choices=["hot", "warm", "cold"],
        default=None,
        help="Query only this layer (default: all three, hot→warm→cold dedup)",
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
