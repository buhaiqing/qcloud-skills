"""
refs/uncertainty/hedging_injector.py
=====================================
HedgingInjector — four-level confidence expression + automatic
hedging-phrase injection / over-confidence weakening.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass

from token_confidence import ConfidenceLevel

# ---------------------------------------------------------------------------
# Four-level hedging phrases (anchored to ConfidenceLevel)
# ---------------------------------------------------------------------------

HEDGING_PHRASES: dict[ConfidenceLevel, list[str]] = {
    ConfidenceLevel.HIGH: [
        "这是正确的。",
        "根据我的知识，这是确定的。",
    ],
    ConfidenceLevel.MEDIUM: [
        "根据现有信息，这可能是正确的，但存在不确定性。",
        "我的置信度约为 {conf:.0%}，建议进一步核实。",
        "这个答案有一定把握，但不完全确定。",
    ],
    ConfidenceLevel.LOW: [
        "我对这个答案不太确定（置信度约 {conf:.0%}），仅供参考。",
        "这可能不是完全准确的，建议查阅权威来源。",
        "我的把握有限，建议寻求专业意见。",
    ],
    ConfidenceLevel.UNKNOWN: [
        "我无法确定这个问题的答案。",
        "这个问题超出了我的知识范围。",
    ],
}


def generate_hedged_response(
    content: str,
    confidence: float,
    level: ConfidenceLevel,
) -> str:
    """Append a contextually appropriate hedging phrase."""
    phrases = HEDGING_PHRASES.get(level, HEDGING_PHRASES[ConfidenceLevel.UNKNOWN])
    phrase = random.choice(phrases)
    if "{conf}" in phrase:
        phrase = phrase.format(conf=confidence)
    return f"{content}\n\n{phrase}"


# ---------------------------------------------------------------------------
# HedgingInjector — in-text injection
# ---------------------------------------------------------------------------

@dataclass
class HedgingInjector:
    """
    Automatically inject / weaken hedging phrases in generated text
    based on the target confidence level.

    Strategy
    --------
    HIGH   : remove over-confident adverbs (definitely → likely)
    MEDIUM : leave as-is
    LOW    : strengthen hedged adverbs (may → likely)
    UNKNOWN: no injection (response already a refusal)
    """

    STRENGTHEN_MAP: dict[str, str] | None = None   # lazy init
    WEAKEN_MAP: dict[str, str] | None = None       # lazy init

    def __post_init__(self):
        if self.STRENGTHEN_MAP is None:
            self.STRENGTHEN_MAP = {
                "may": "likely",
                "might": "probably",
                "could": "can",
                "possibly": "probably",
            }
        if self.WEAKEN_MAP is None:
            self.WEAKEN_MAP = {
                "definitely": "likely",
                "certainly": "probably",
                "will": "may",
            }

    # Compiled regex patterns (class-level, not per-instance — ponytail).
    # Deliberately mutable so subclasses or tests can extend it; the
    # ponytail comment above records the trade-off.
    _PATTERNS = [  # noqa: RUF012
        re.compile(r"\b(may|might|could|possibly)\b", re.IGNORECASE),
        re.compile(r"\b(will|definitely|certainly)\b", re.IGNORECASE),
    ]

    def inject(self, text: str, target_level: ConfidenceLevel) -> str:
        """Apply hedging transformation for target confidence level."""
        if target_level == ConfidenceLevel.HIGH:
            return self._weaken_overconfident(text)
        if target_level == ConfidenceLevel.LOW:
            return self._strengthen_hedging(text)
        # MEDIUM / UNKNOWN — leave unchanged
        return text

    def _weaken_overconfident(self, text: str) -> str:
        for pattern in self._PATTERNS[1:]:  # only over-confident patterns
            if pattern.search(text):
                for p, replacement in (self.WEAKEN_MAP or {}).items():
                    text = re.sub(r"\b" + p + r"\b", replacement, text, flags=re.IGNORECASE)
        return text

    def _strengthen_hedging(self, text: str) -> str:
        for pattern in self._PATTERNS[:1]:   # only hedging patterns
            if pattern.search(text):
                for weak, strong in (self.STRENGTHEN_MAP or {}).items():
                    text = re.sub(r"\b" + weak + r"\b", strong, text, flags=re.IGNORECASE)
        return text


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    injector = HedgingInjector()

    tests = [
        ("This will definitely work.", ConfidenceLevel.HIGH),
        ("This may be correct.", ConfidenceLevel.LOW),
        ("The answer is 42.", ConfidenceLevel.MEDIUM),
    ]

    for text, level in tests:
        transformed = injector.inject(text, level)
        print(f"  [{level.value}] {text!r:40} → {transformed!r}")

    print("\n=== generate_hedged_response ===")
    for level in ConfidenceLevel:
        out = generate_hedged_response("The sky is blue.", 0.75, level)
        print(f"  [{level.value}] {out!r}")
