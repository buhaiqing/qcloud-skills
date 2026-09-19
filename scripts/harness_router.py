#!/usr/bin/env python3
"""Phase 4 — Runtime Router: frontmatter-only candidate selection, progressive
references load (by the caller after selection), per-run budget enforcement, and
a top-1 confusion matrix over the existing eval_queries.json, using the owning
skill directory as ground truth."""
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_TOKEN_RE = re.compile(r"[\s_\-]+|(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _tokens(text: str) -> set:
    """Lowercase word tokens, splitting CamelCase / underscore boundaries so
    'DescribeInstances' -> {'describe', 'instances'} and 'Run_Health_Check'
    -> {'run', 'health', 'check'}."""
    parts = _TOKEN_RE.split(text)
    return {p.lower() for p in parts if p}

def _keyword_overlap(keyword: str, query_tokens: set) -> int:
    """Count how many word-tokens of a keyword (e.g. 'DescribeInstances') are
    present in the query token set. Whole-word overlap, not raw substring, so
    'describe my cvm instances' matches 'DescribeInstances' (describe+instances)."""
    kt = _tokens(keyword)
    if not kt:
        return 0
    return sum(1 for t in kt if t in query_tokens)

def select_top1(registry: dict[str, Any], intent: str) -> dict[str, Any]:
    """Frontmatter-only candidate ranking. Scores each skill by word-token
    overlap between its intent_keywords (CamelCase API names) and the intent
    text; returns the best match plus the full candidate list (caller loads
    references only for top1).

    Deterministic tie-break: on equal score, the alphabetically-first skill name
    wins (avoids dict-order non-determinism). Returns top1_skill="" when no
    skill scores >0 (e.g. empty intent_keywords, or a query whose tokens miss
    every keyword), never None — a no-match must not be silently delegated to
    whichever skill happens to sort first.
    """
    q_tokens = _tokens(intent)
    best, best_score = "", 0
    for s in sorted(registry["skills"], key=lambda x: x["name"]):
        score = sum(
            _keyword_overlap(kw, q_tokens)
            for kw in s.get("intent_keywords", [])
        )
        if score > best_score:
            best, best_score = s["name"], score
    return {
        "top1_skill": best,
        "score": best_score,
        "candidates": [s["name"] for s in registry["skills"]],
    }


def confusion_matrix(
    registry: dict[str, Any], eval_queries: list[dict], skill: str
) -> dict[str, float]:
    """Routing accuracy for one skill, against owning-skill ground truth.

    `skill` is the directory whose eval_queries.json this is, so it IS the label
    for every item in the file — the router either lands on the owning skill or
    it does not. No per-item `intent` key is required (29 of 31 eval_queries.json
    files carry none; the previous intent-keyword lookup therefore compared
    None against a keyword list and pinned top1_accuracy/misdelegation to the
    constant 0.0 — a vacuous metric that the gate still reported as PASS).

    Positive (should_trigger=true): correct iff select_top1(query).top1_skill == skill.
    Negative (should_trigger=false): misdelegation iff top1_skill == skill.
    """
    pos = [q for q in eval_queries if q.get("should_trigger")]
    neg = [q for q in eval_queries if not q.get("should_trigger")]
    tp = sum(1 for q in pos if select_top1(registry, q.get("query", ""))["top1_skill"] == skill)
    fp = sum(1 for q in neg if select_top1(registry, q.get("query", ""))["top1_skill"] == skill)
    top1 = (tp / len(pos)) if pos else 0.0
    misdelegation = (fp / len(neg)) if neg else 0.0
    return {"top1_accuracy": top1, "misdelegation": misdelegation, "fallback": 0.0}



def main() -> int:
    args = sys.argv
    if "--registry" in args and "--intent" in args:
        reg = json.loads(Path(args[args.index("--registry") + 1]).read_text())
        intent = args[args.index("--intent") + 1]
        print(json.dumps(select_top1(reg, intent)))
        return 0
    if "--confusion" in args:
        reg = json.loads(Path(args[args.index("--registry") + 1]).read_text())
        eq = json.loads(Path(args[args.index("--eval") + 1]).read_text())
        skill = args[args.index("--skill") + 1]
        print(json.dumps(confusion_matrix(reg, eq, skill)))
        return 0
    print(
        "usage: --registry R --intent I | --confusion --registry R --eval E --skill S",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
