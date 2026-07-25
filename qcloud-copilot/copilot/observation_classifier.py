"""P2.7 — ObservationType classification aligned with Langfuse semantics.

Rules (per SPEC §14.5):
  - Generator / Critic / Summarizer       → GENERATION (produces output content)
  - Skill / API call / Verification / SafetyGate → SPAN (executes a unit of work)
  - Plain "Event" markers / unclassified  → EVENT

Use:
    from copilot.observation_classifier import classify_observation_type
    kind = classify_observation_type(name="gcl-generator")  # -> GENERATION
"""
from __future__ import annotations

import re
from typing import Optional

from copilot.trace_records import ObservationType


_GENERATION_TOKENS = ("generator", "critic", "summarizer")
_SPAN_TOKENS = (
    "skill", "skill_call", "api", "verification", "safety.", "rubric",
    "tccli", "sdk-call", "tool", "retrieve", "exec", "execute",
)
_EVENT_TOKENS = ("init", "start", "end", "session.", "trace.", "blackboard-init")

# Tencent Cloud API action signature: starts with a verb and CamelCases (e.g. DescribeInstances)
_API_ACTION_RE = re.compile(
    r"\b(describe|list|get|create|delete|modify|terminate|reboot|"
    r"start|stop|bind|unbind|attach|detach|associate)[a-z]+\b"
)


def classify_observation_type(
    name: str,
    kind: Optional[str] = None,
) -> ObservationType:
    """Classify an observation by `name` (heuristic) or explicit `kind`.

    `kind` (if provided) is one of "SPAN" / "GENERATION" / "EVENT" and wins.
    """
    if kind:
        normalized = kind.strip().upper()
        if normalized in {"SPAN", "GENERATION", "EVENT"}:
            return ObservationType(normalized)

    lname = (name or "").lower()
    if not lname:
        return ObservationType.EVENT

    # GENERATION first (most specific)
    if any(tok in lname for tok in _GENERATION_TOKENS):
        return ObservationType.GENERATION

    # SPAN — Skill / API / Verification / Safety / Tencent Cloud API action signature
    if any(tok in lname for tok in _SPAN_TOKENS) or _API_ACTION_RE.search(lname):
        return ObservationType.SPAN

    # EVENT — explicit lifecycle markers
    if any(tok in lname for tok in _EVENT_TOKENS):
        return ObservationType.EVENT

    return ObservationType.EVENT
