#!/usr/bin/env python3
"""Blueprint-driven routing decision: implements agent-routing-blueprint.md.

Run with a natural-language task description:
    python3 scripts/routing_decision.py "fix the ruff check error in detect_spec_drift.py"
    python3 scripts/routing_decision.py "write a runbook for k8s cluster inspection"

Exit codes: 0=main-direct, 1=subagent(single), 2=subagent(fan-out), 3=no decision (ambiguous)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_BLUEPRINT = ROOT / "docs" / "harness-engineering" / "agent-routing-blueprint.md"
_VERSION = "2026-09-12"


def _prose_trigger(task: str) -> bool:
    t = task.lower()
    prose_verbs = {
        "write", "draft", "create", "generate",  # create
        "document", "describe", "explain",        # describe
        "spec", "design", "plan", "outline",      # plan
        "review", "check", "audit",               # review
    }
    prose_nouns = {
        "spec", "runbook", "readme", "skILL.md",
        "design doc", "documentation", "guide",
        "blueprint", "decision tree", "markdown",
        "section", "chapter", "paragraph",
    }
    t_words = set(re.split(r"\W+", t))
    has_prose_verb = bool(prose_verbs & t_words)
    has_prose_noun = bool(prose_nouns & t_words)
    return has_prose_verb and has_prose_noun


def _exploration_trigger(task: str) -> bool:
    t = task.lower()
    exploration_phrases = [
        "investigate", "explore", "research", "find the best",
        "figure out", "understand", "diagnose the root cause",
        "which approach", "compare", "evaluate options",
    ]
    return any(p in t for p in exploration_phrases)


def _size_gate(task: str) -> bool:
    """True if ≤30-line single-file, no new public surface."""
    t = task.lower()
    small_patterns = [
        "fix typo", "fix comment", "add comment", "rename variable",
        "small fix", "one line", "single line", "line fix",
        "typo", "bump version", "update comment", "ruff fix",
    ]
    has_small = any(p in t for p in small_patterns)
    has_file = (
        "file" in t or
        ".py" in t or ".md" in t or ".json" in t or
        ".yaml" in t or ".yml" in t or ".sh" in t
    )
    return has_small and has_file


def decide(task: str) -> dict:
    """Route task: returns routing decision per agent-routing-blueprint.md."""
    result = {
        "task": task,
        "version": _VERSION,
        "routing": None,
        "mode": None,
        "confidence": None,
        "reasoning": [],
    }

    # Q1: single file / single step / deterministic?
    if _size_gate(task):
        result["routing"] = "main-direct"
        result["mode"] = "main-direct"
        result["confidence"] = "high"
        result["reasoning"].append("Q1: single-file deterministic → main-direct")
        return result

    # Q2: user opt-out
    opt_out = {"skip orchestrator", "skip", "main direct", "你自己处理", "不派"}
    if any(p in task.lower() for p in opt_out):
        result["routing"] = "main-direct"
        result["mode"] = "main-direct"
        result["confidence"] = "high"
        result["reasoning"].append("Q2: user opt-out → main-direct")
        return result

    # Q3: prose-writer filter (before code gate)
    if _prose_trigger(task):
        result["routing"] = "main-direct"
        result["mode"] = "main-direct"
        result["confidence"] = "high"
        result["reasoning"].append(
            "Q3: structured prose task (write/draft/spec + noun) → main-direct"
        )
        return result

    # Q4: code complexity
    large = any(k in task.lower() for k in [
        "new file", "new module", "cross-module",
        "multi-file", "add feature", "implement",
        ">=30 lines", "over 30 lines",
    ])
    if not large and ("single" in task.lower() or "one" in task.lower()):
        result["routing"] = "main-direct"
        result["mode"] = "main-direct"
        result["confidence"] = "medium"
        result["reasoning"].append(
            "Q4: ≤30-line single-file → main-direct"
        )
        return result

    # Q5: independent slices?
    slice_words = {"parallel", "independent", "both", "all of them",
                   "fan-out", "separate", "multiple tasks"}
    has_slices = any(w in task.lower() for w in slice_words)
    if has_slices:
        result["routing"] = "fan-out"
        result["mode"] = "subagent-fan-out"
        result["confidence"] = "medium"
        result["reasoning"].append("Q5: independent slices → fan-out")
        return result

    # Default: single subagent
    result["routing"] = "single-subagent"
    result["mode"] = "subagent-single"
    result["confidence"] = "low"
    if _exploration_trigger(task):
        result["reasoning"].append("Exploration detected — single subagent preferred")
    else:
        result["reasoning"].append("Default: single subagent with self-verifiable exit")
    return result


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} '<task description>' [--json]")
        print(f"Version: {_VERSION} (agent-routing-blueprint.md)")
        print("\nExamples:")
        examples = [
            ("fix the ruff error in detect_spec_drift.py", "main-direct"),
            ("write a runbook for k8s inspection", "main-direct"),
            ("add KPI#9 to check_kpi_gates.py and validate it", "subagent-single"),
            ("parallel: fix ruff + update Makefile + bump version", "subagent-fan-out"),
        ]
        for task, route in examples:
            print(f"  {sys.argv[0]} '{task}'")
            print(f"    → {route}")
        return 0

    args = sys.argv[1:]
    if "--json" in args:
        args.remove("--json")
    task = " ".join(args).strip()
    json_mode = "--json" in sys.argv

    result = decide(task)

    if json_mode:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Task: {task[:80]}{'...' if len(task) > 80 else ''}")
        print(f"Routing: {result['routing']} ({result['confidence']} confidence)")
        print("Reasoning:")
        for r in result["reasoning"]:
            print(f"  • {r}")
        print(f"\nVersion: {result['version']}")

    # exit code = routing mode
    mode_map = {"main-direct": 0, "subagent-single": 1, "single-subagent": 1, "fan-out": 2}
    return mode_map.get(result["routing"], 3)


if __name__ == "__main__":
    sys.exit(main())
