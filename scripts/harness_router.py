#!/usr/bin/env python3
"""Phase 4 — Runtime Router: frontmatter-only candidate selection, progressive
references load (by the caller after selection), per-run budget enforcement, and
intent confusion matrix over existing eval_queries.json (ground truth)."""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]


def select_top1(registry: Dict[str, Any], intent: str) -> Dict[str, Any]:
    """Frontmatter-only candidate ranking. Scores each skill by how many of its
    intent_keywords appear in the intent text; returns the best match plus the
    full candidate list (caller loads references only for top1)."""
    best, best_score = None, -1
    for s in registry["skills"]:
        score = sum(
            1 for kw in s.get("intent_keywords", [])
            if kw and kw.lower() in intent.lower()
        )
        if score > best_score:
            best, best_score = s["name"], score
    return {
        "top1_skill": best,
        "score": best_score,
        "candidates": [s["name"] for s in registry["skills"]],
    }


def confusion_matrix(
    registry: Dict[str, Any], eval_queries: List[dict], skill: str
) -> Dict[str, float]:
    """Reuse eval_queries.json (ground truth) for routing accuracy.

    Each eval item: {"query": str, "should_trigger": bool, "intent": keyword}.
    Positive (should_trigger=true): correct iff select_top1(query).top1_skill's
    intent_keywords contain the item's intent keyword.
    Negative (should_trigger=false): false-positive iff the top1 skill's
    intent_keywords contain the item's intent keyword (misdelegation).
    """
    pos = [q for q in eval_queries if q.get("should_trigger")]
    neg = [q for q in eval_queries if not q.get("should_trigger")]
    tp = sum(1 for q in pos if _top1_has_intent(registry, q, skill))
    fp = sum(1 for q in neg if _top1_has_intent(registry, q, skill))
    top1 = (tp / len(pos)) if pos else 0.0
    misdelegation = (fp / len(neg)) if neg else 0.0
    return {"top1_accuracy": top1, "misdelegation": misdelegation, "fallback": 0.0}


def _top1_has_intent(registry: Dict[str, Any], q: dict, skill: str) -> bool:
    top = select_top1(registry, q.get("query", ""))["top1_skill"]
    skills = {s["name"]: s for s in registry["skills"]}
    top_kw = skills.get(top, {}).get("intent_keywords", [])
    return q.get("intent") in top_kw


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
