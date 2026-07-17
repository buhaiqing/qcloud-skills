#!/usr/bin/env python3
"""Success Patterns Retrieval — query the layered success memory.

Usage:
  python3 scripts/success_pattern_retrieve.py retrieve --skill qcloud-cvm-ops
  python3 scripts/success_pattern_retrieve.py retrieve --skill qcloud-cvm-ops --operation RunInstances
  python3 scripts/success_pattern_retrieve.py retrieve --skill qcloud-cvm-ops --json
  python3 scripts/success_pattern_retrieve.py retrieve --skill qcloud-cvm-ops --top-n 5

Scoring formula (symmetric with failure-patterns retrieval):
  composite_score = base_score × severity_weight × recency_decay

  base_score:
    - 3.0 if skill matches AND operation matches
    - 2.0 if skill matches only
    - filtered out otherwise

  severity_weight (from iter, inverse of failure-patterns):
    - 3.0  iter=1   (single-shot success — highest quality)
    - 2.0  iter≤2   (near-optimal)
    - 1.0  iter>2   (required multiple retries)

  recency_decay (same as failure-patterns):
    - < 7 days:  1.0
    - 7–30 days: 0.7
    - 30–90 days: 0.3
    - > 90 days: 0.1
    - unknown: 1.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOT_PATH = ROOT / "docs" / "success-patterns.md"
WARM_PATH = ROOT / "docs" / "success-patterns-warm.md"
COLD_PATH = ROOT / "docs" / "success-patterns-cold.md"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# SuccessEntry (lightweight, mirrors success_pattern_mine.py)
# ---------------------------------------------------------------------------

class SuccessEntry:
    __slots__ = (
        "skill", "operation", "command_signature", "full_command",
        "iter", "count", "first_hit", "last_hit", "scores", "avg_iter",
    )

    def __init__(self, **kwargs: Any) -> None:
        for f in self.__slots__:
            setattr(self, f, kwargs.get(f))

    def to_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__slots__}


def _parse_table_row(line: str) -> list[str]:
    cells, current = [], ""
    in_backtick = False
    for ch in line:
        if ch == "`":
            in_backtick = not in_backtick
        elif ch == "|" and not in_backtick:
            cells.append(current.strip())
            current = ""
        else:
            current += ch
    cells.append(current.strip())
    return [c.strip() for c in cells[1:-1]]


def _parse_layer(path: Path) -> dict[tuple[str, str, str], SuccessEntry]:
    if not path.exists():
        return {}
    patterns: dict[tuple[str, str, str], SuccessEntry] = {}
    table_headers: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#") or not line:
            table_headers = []
            continue
        if line.startswith("|") and "---" not in line and "Skill" in line:
            table_headers = [h.lower().replace(" ", "").replace("-", "") for h in _parse_table_row(line)]
            continue
        if line.startswith("|") and "---" not in line and table_headers:
            cells = _parse_table_row(line)
            if len(cells) < 5:
                continue
            row = dict(zip(table_headers, cells))

            skill = row.get("skill", "").strip().strip("`")
            operation = row.get("operation", "").strip().strip("`")
            sig = row.get("commandsignature", "").strip().strip("`")
            if not skill:
                continue

            count_str = row.get("count", "0").strip()
            try:
                count = int(count_str)
            except ValueError:
                count = 0

            last_hit = row.get("lasthit", "").strip()
            first_hit = row.get("firsthit", "").strip()

            iter_str = row.get("iter", "1").strip()
            try:
                iter_val = int(iter_str)
            except ValueError:
                iter_val = 1

            avg_str = row.get("avgiter", "1.0").strip()
            try:
                avg_iter = float(avg_str)
            except ValueError:
                avg_iter = 1.0

            scores_raw = row.get("scores", "{}").strip()
            scores: dict[str, float] = {}
            if scores_raw and scores_raw not in ("{}", ""):
                try:
                    scores = json.loads(scores_raw)
                except json.JSONDecodeError:
                    scores = {}

            full_cmd = row.get("fullcommand", "").strip().strip("`")

            key = (skill, operation, sig)
            patterns[key] = SuccessEntry(
                skill=skill,
                operation=operation,
                command_signature=sig,
                full_command=full_cmd,
                iter=iter_val,
                count=count,
                first_hit=first_hit or last_hit,
                last_hit=last_hit,
                scores=scores,
                avg_iter=avg_iter,
            )
    return patterns


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _severity_weight(iter_val: Any) -> float:
    try:
        i = int(iter_val) if iter_val is not None else 1
    except (ValueError, TypeError):
        i = 1
    if i == 1:
        return 3.0
    elif i <= 2:
        return 2.0
    return 1.0


def recency_decay(last_hit: str | None) -> float:
    if not last_hit:
        return 1.0
    try:
        last_dt = datetime.strptime(last_hit[:10], "%Y-%m-%d")
    except ValueError:
        return 1.0
    now = datetime.now()
    delta_days = (now - last_dt).days
    if delta_days < 7:
        return 1.0
    elif delta_days < 30:
        return 0.7
    elif delta_days < 90:
        return 0.3
    return 0.1


def compute_composite(entry: SuccessEntry, skill: str, operation: str | None) -> float:
    base = 3.0 if (entry.skill == skill and
                   (operation is None or entry.operation == operation)) else 2.0 if entry.skill == skill else 0.0
    if base == 0.0:
        return 0.0
    sev = _severity_weight(entry.iter)
    decay = recency_decay(entry.last_hit)
    return base * sev * decay


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_success_patterns(
    skill: str,
    operation: str | None = None,
    top_n: int = 3,
) -> list[dict[str, Any]]:
    """Query hot → warm → cold layers, return top_n by composite_score desc.

    De-duplicates across layers: once a key is found in a higher-priority
    layer, it is not returned from lower layers.
    """
    hot = _parse_layer(HOT_PATH)
    warm = _parse_layer(WARM_PATH)
    cold = _parse_layer(COLD_PATH)

    seen_keys: set[tuple[str, str, str]] = set()
    results: list[tuple[float, dict[str, Any]]] = []

    for layer_name, layer in [("hot", hot), ("warm", warm), ("cold", cold)]:
        if len(results) >= top_n:
            break
        for key, entry in layer.items():
            if key in seen_keys:
                continue
            score = compute_composite(entry, skill, operation)
            if score < 2.0:
                continue
            seen_keys.add(key)
            d = entry.to_dict()
            d["_layer"] = layer_name
            d["_score"] = round(score, 3)
            d["_severity_weight"] = _severity_weight(entry.iter)
            d["_recency_decay"] = recency_decay(entry.last_hit)
            results.append((score, d))

    results.sort(key=lambda x: -x[0])
    return [item for _, item in results[:top_n]]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def format_for_injection(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return ""
    lines = []
    for e in entries:
        skill = e.get("skill", "—")
        op = e.get("operation", "—")
        sig = e.get("command_signature", "")[:60]
        count = e.get("count", 0)
        iter_v = e.get("iter", 1)
        last_hit = e.get("last_hit", "—")
        layer = e.get("_layer", "?")
        lines.append(
            f"- [{skill}] op=`{op}` sig=`{sig}...` "
            f"(count={count}, iter={iter_v}, last_hit={last_hit}, layer={layer})"
        )
    return "\n".join(lines)


def cmd_retrieve(args: argparse.Namespace) -> int:
    entries = retrieve_success_patterns(
        skill=args.skill,
        operation=args.operation,
        top_n=args.top_n,
    )
    if args.json:
        print(json.dumps(entries, indent=2, ensure_ascii=False))
    else:
        print(format_for_injection(entries))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Retrieve top-N success patterns for a skill",
        prog="success_pattern_retrieve",
    )
    parser.add_argument("--skill", required=True, help="Target skill name")
    parser.add_argument("--operation", default=None, help="Operation name (e.g., RunInstances)")
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return cmd_retrieve(args)


if __name__ == "__main__":
    sys.exit(main())
