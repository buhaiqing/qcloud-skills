"""
refs/uncertainty/feedback_loop.py
=================================
UncertaintyFeedbackLoop — state machine + Bayesian posterior update +
human-in-the-loop reconciliation.

MAJOR M-B1 fix: Added RECONCILE state — human corrections now route
back to CALCULATING (not directly to GENERATING), ensuring full
confidence recalculation after the user corrects the model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class UncertaintyState(Enum):
    INITIAL = "initial"
    CALCULATING = "calculating"
    # M-B1 fix: reconcile → recalculate → generate
    RECONCILE = "reconcile"     # human correction received; back to CALCULATING
    HIGH_CONFIDENCE = "high_confidence"
    MEDIUM_CONFIDENCE = "medium_confidence"
    LOW_CONFIDENCE = "low_confidence"
    REFUSAL = "refusal"
    GENERATING = "generating"


@dataclass
class UncertaintyContext:
    state: UncertaintyState
    confidence: float
    prior_confidence: float
    external_signals: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# UncertaintyFeedbackLoop
# ---------------------------------------------------------------------------

@dataclass
class UncertaintyFeedbackLoop:
    """
    Uncertainty feedback loop:
    - External signals update internal confidence
    - Human-in-the-loop corrections trigger RECONCILE → CALCULATING
    - Tool results update via Bayesian posterior

    State transitions (M-B1 fix):
      human_correction → RECONCILE → CALCULATING → (H|M|L) → GENERATING → INITIAL
    """

    state: UncertaintyState = UncertaintyState.INITIAL
    confidence: float = 1.0
    prior_confidence_history: list[tuple[float, float]] = field(default_factory=list)
    retrain_buffer: list[dict[str, str]] = field(default_factory=list)

    # Default tool reliability weights (经验值; 生产环境通过历史调用统计)
    TOOL_RELIABILITY: dict[str, float] = field(default_factory=lambda: {
        "search": 0.80,
        "calculator": 0.95,
        "code_executor": 0.90,
        "knowledge_base": 0.85,
    })

    def update_from_tool_result(
        self,
        tool_name: str,
        tool_result: dict[str, Any],
        prior_confidence: float,
    ) -> float:
        """
        Bayesian posterior update from tool execution result.

        P(H|E) = P(E|H) * P(H) / [P(E|H)*P(H) + P(E|¬H)*P(¬H)]
        """
        reliability = self.TOOL_RELIABILITY.get(tool_name, 0.70)
        success_signal = tool_result.get("success", True)
        # Likelihood of evidence given hypothesis
        evidence_likelihood = reliability if success_signal else (1 - reliability)

        numerator = evidence_likelihood * prior_confidence
        denominator = (
            evidence_likelihood * prior_confidence +
            (1 - evidence_likelihood) * (1 - prior_confidence)
        )
        if denominator == 0:
            posterior = 0.0
        else:
            posterior = numerator / denominator

        # Smooth update (prevent oscillation)
        alpha = 0.30
        self.confidence = alpha * posterior + (1 - alpha) * prior_confidence
        return self.confidence

    def update_from_human_correction(
        self,
        original_response: str,
        human_correction: str,
        current_confidence: float,
    ) -> float:
        """
        M-B1 fix: Human correction triggers RECONCILE state — model
        must return to CALCULATING and recompute confidence from scratch.

        Correction signal determines confidence penalty:
          major  → 0.5x (large rewrite detected)
          minor  → 0.8x (minor adjustment)
          none   → unchanged
        """
        correction_signal = self._detect_correction_type(original_response, human_correction)

        if correction_signal == "major":
            new_confidence = current_confidence * 0.5
            self._flag_for_retraining(original_response, human_correction)
        elif correction_signal == "minor":
            new_confidence = current_confidence * 0.8
        else:
            new_confidence = current_confidence

        self.prior_confidence_history.append((current_confidence, new_confidence))
        self.confidence = new_confidence

        # M-B1 fix: route back to RECONCILE → CALCULATING
        self.state = UncertaintyState.RECONCILE

        return new_confidence

    def _detect_correction_type(self, original: str, corrected: str) -> str:
        """Detect correction magnitude (simplified heuristic)."""
        if not corrected:
            return "none"
        if len(corrected) < len(original) * 0.5:
            return "major"
        return "minor"

    def _flag_for_retraining(
        self, original: str, corrected: str, timestamp: str | None = None
    ):
        """Mark (original, corrected) pair for retraining buffer."""
        if timestamp is None:
            import datetime
            timestamp = datetime.datetime.now().isoformat()
        self.retrain_buffer.append({
            "original": original,
            "corrected": corrected,
            "timestamp": timestamp,
        })

    def step(self, context: UncertaintyContext) -> UncertaintyContext:
        """
        State machine one-step transition.

        Human-correction path (M-B1 fix):
          RECONCILE → CALCULATING (confidence recomputed externally)
        """
        self.state = context.state
        self.confidence = context.confidence

        if self.state == UncertaintyState.INITIAL:
            self.state = UncertaintyState.CALCULATING

        elif self.state == UncertaintyState.CALCULATING:
            if self.confidence >= 0.85:
                self.state = UncertaintyState.HIGH_CONFIDENCE
            elif self.confidence >= 0.60:
                self.state = UncertaintyState.MEDIUM_CONFIDENCE
            elif self.confidence >= 0.30:
                self.state = UncertaintyState.LOW_CONFIDENCE
            else:
                self.state = UncertaintyState.REFUSAL

        # M-B1 fix: RECONCILE routes back to CALCULATING
        elif self.state == UncertaintyState.RECONCILE:
            self.state = UncertaintyState.CALCULATING

        elif self.state in (
            UncertaintyState.HIGH_CONFIDENCE,
            UncertaintyState.MEDIUM_CONFIDENCE,
            UncertaintyState.LOW_CONFIDENCE,
        ):
            self.state = UncertaintyState.GENERATING

        elif self.state == UncertaintyState.GENERATING:
            self.state = UncertaintyState.INITIAL  # cycle back

        return UncertaintyContext(
            state=self.state,
            confidence=self.confidence,
            prior_confidence=context.confidence,
        )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loop = UncertaintyFeedbackLoop()

    # Step through normal flow
    print("=== Normal flow ===")
    ctx = UncertaintyContext(UncertaintyState.INITIAL, 1.0, 1.0)
    for i in range(5):
        ctx = loop.step(ctx)
        print(f"  step {i+1}: state={ctx.state.value:20}  confidence={ctx.confidence:.4f}")

    # Tool result update
    print("\n=== Tool result update ===")
    new_conf = loop.update_from_tool_result(
        "search", {"success": True}, loop.confidence
    )
    print(f"  after successful search: confidence={new_conf:.4f}")

    # M-B1 fix: human correction → RECONCILE
    print("\n=== Human correction (M-B1 fix) ===")
    new_conf2 = loop.update_from_human_correction(
        "The capital of France is Paris.",
        "No — the capital of France is Paris.  (minor phrasing fix)",
        loop.confidence,
    )
    print(f"  after human correction: confidence={new_conf2:.4f}  state={loop.state.value}")
    # Next step should go CALCULATING
    ctx2 = UncertaintyContext(loop.state, new_conf2, new_conf2)
    ctx2 = loop.step(ctx2)
    print(f"  next step:              state={ctx2.state.value}")
    print(f"  ✓ RECONCILE → CALCULATING path verified: {ctx2.state == UncertaintyState.CALCULATING}")
