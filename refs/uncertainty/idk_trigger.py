"""
refs/uncertainty/idk_trigger.py
================================
UncertaintyTrigger — knowledge boundary detection, time-sensitivity detection,
and Structured Refusal response generation.
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# UncertaintyTrigger
# ---------------------------------------------------------------------------

@dataclass
class UncertaintyTrigger:
    """
    I Don't Know trigger conditions.

    Attributes
    ----------
    knowledge_boundary_flag : bool
        True when query falls outside knowledge-base coverage.
    time_sensitivity_flag : bool
        True when query asks for time-sensitive information.
    self_eval_confidence : float
        Self-assessed confidence (0~1).
    refusal_threshold : float
        Confidence below which refusal is mandatory.
    """
    knowledge_boundary_flag: bool = False
    time_sensitivity_flag: bool = False
    self_eval_confidence: float = 1.0
    refusal_threshold: float = 0.30

    def should_refuse(self) -> bool:
        """Refuse if any condition is met."""
        return (
            self.knowledge_boundary_flag
            or (self.time_sensitivity_flag and self.self_eval_confidence < 0.60)
            or self.self_eval_confidence < self.refusal_threshold
        )


# ---------------------------------------------------------------------------
# Detection helpers (simplified — real impl would call embedding model)
# ---------------------------------------------------------------------------

# ponytail: no embedding model in stdlib; stub with keyword heuristic.
# Upgrade path: swap `_detect_kb_stub` for a real encoder in production.
_TIME_INDICATORS: list[str] = [
    "最新", "最近", "现在", "今天", "当前",
    "latest", "recent", "current", "now", "today",
    "2024", "2025", "2026",
]
_KB_SIMILARITY_STUB_THRESHOLD = 0.5


def detect_knowledge_boundary(
    query: str,
    retrieval_scores: list[float],
    threshold: float = _KB_SIMILARITY_STUB_THRESHOLD,
) -> bool:
    """
    Detect whether query is outside knowledge coverage.

    Parameters
    ----------
    query : str
        User query (unused in stub — kept for API compatibility).
    retrieval_scores : List[float]
        Similarity scores from knowledge-base retrieval (empty = no match).
    threshold : float
        Minimum acceptable similarity score.

    Returns
    -------
    bool
        True if query is out-of-knowledge (empty retrieval or low similarity).
    """
    del query  # unused in stub; retained for future embedding model path
    if not retrieval_scores:
        return True
    return max(retrieval_scores) < threshold


def detect_time_sensitivity(
    query: str,
    knowledge_cutoff: str,  # ISO date string "YYYY-MM-DD"
    current_time: str | None = None,
) -> bool:
    """
    Detect whether query requires up-to-date information.

    Parameters
    ----------
    query : str
        User query text.
    knowledge_cutoff : str
        ISO date of knowledge cutoff (e.g. "2025-09-01").
    current_time : str, optional
        ISO date of now. If None, assumes knowledge is stale.

    Returns
    -------
    bool
        True if query contains time indicators and knowledge may be outdated.
    """
    has_time_indicator = any(
        indicator.lower() in query.lower() for indicator in _TIME_INDICATORS
    )
    if not has_time_indicator:
        return False
    # If we don't know current time, assume it might be after cutoff
    if current_time is None:
        return True
    return current_time > knowledge_cutoff


# ---------------------------------------------------------------------------
# Structured Refusal
# ---------------------------------------------------------------------------

@dataclass
class RefusalResponse:
    # non-default fields first
    reason: str      # high_level | out_of_knowledge | time_sensitive | low_confidence
    confidence: float
    # optional fields with defaults
    status: str = "refused"
    suggestion: str | None = None

    def to_markdown(self) -> str:
        return (
            f"**抱歉，我无法回答这个问题。**\n\n"
            f"- **原因**: {self.reason}\n"
            f"- **置信度**: {self.confidence:.2%}\n"
            f"- **建议**: {self.suggestion or '请尝试换一种问法，或提供更多上下文。'}\n"
        )


_REFUSAL_TEMPLATES = {
    "high_level":       "这个问题涉及{{domain}}领域，需要更专业的知识。",
    "out_of_knowledge":  "我的知识库中没有与「{query}」相关的信息。",
    "time_sensitive":    "该问题需要最新的信息（截止到{cutoff}），我可能无法提供准确答案。",
    "low_confidence":    "我对这个问题的置信度仅为{conf:.0%}，无法确保回答准确。",
}


def build_refusal(
    reason: str,
    confidence: float,
    query: str | None = None,
    domain: str | None = None,
    cutoff: str | None = None,
    suggestion: str | None = None,
) -> RefusalResponse:
    """Build a structured refusal response."""
    return RefusalResponse(
        status="refused",
        reason=reason,
        confidence=confidence,
        suggestion=suggestion,
    )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== UncertaintyTrigger ===")
    t1 = UncertaintyTrigger(knowledge_boundary_flag=True)
    print(f"  kb only:              should_refuse={t1.should_refuse()}")

    t2 = UncertaintyTrigger(time_sensitivity_flag=True, self_eval_confidence=0.50)
    print(f"  time+conf=0.50:       should_refuse={t2.should_refuse()}")

    t3 = UncertaintyTrigger(self_eval_confidence=0.25)
    print(f"  conf=0.25:            should_refuse={t3.should_refuse()}")

    t4 = UncertaintyTrigger(self_eval_confidence=0.50)
    print(f"  conf=0.50 (pass):     should_refuse={t4.should_refuse()}")

    print("\n=== detect_knowledge_boundary ===")
    print(f"  empty retrieval:      {detect_knowledge_boundary('what?', [])}")
    print(f"  high similarity:      {detect_knowledge_boundary('what?', [0.9, 0.8])}")
    print(f"  low similarity:       {detect_knowledge_boundary('what?', [0.3, 0.2])}")

    print("\n=== detect_time_sensitivity ===")
    print(f"  'latest news' cut=2025: {detect_time_sensitivity('latest news', '2025-01-01', '2026-01-01')}")
    print(f"  'latest news' no time:  {detect_time_sensitivity('latest news', '2025-01-01')}")
    print(f"  'static fact':          {detect_time_sensitivity('what is gravity', '2025-01-01')}")

    print("\n=== build_refusal ===")
    r = build_refusal("out_of_knowledge", 0.20, query="quantum consciousness")
    print(r.to_markdown())
