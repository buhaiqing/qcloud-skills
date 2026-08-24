#!/usr/bin/env python3
"""Phase 3.4 — Governance framework: configurable autonomy levels and rule evaluation."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Literal

# ----------------------------------------------------------------------
# Dataclasses
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class AutonomyRule:
    """A single rule mapping a condition expression to an action."""

    condition: str  # e.g. "risk_level == 'LOW'", "is_destructive"
    action: Literal["auto_confirm", "critic_review", "human_token", "human_approval"]
    scope: list[str]  # ["*"] or skill names
    max_decisions_per_hour: int = 0  # 0 = no limit
    require_audit: bool = True


@dataclass(frozen=True)
class AutonomyDecision:
    """Result of evaluating an operation against a policy."""

    action_taken: Literal["auto_confirm", "critic_review", "human_token", "human_approval"]
    matched_rule: AutonomyRule | None
    rationale: str


@dataclass
class AutonomyPolicy:
    """A named set of rules evaluated in order; first match wins."""

    level: int
    description: str
    rules: list[AutonomyRule]

    # Internal: decision history for rate limiting — keyed by (skill, action)
    # Values are lists of Unix timestamps when decisions were made.
    _decision_clock: dict[tuple[str, str], list[float]] = field(default_factory=dict, repr=False)

    def evaluate(
        self,
        operation: str,
        risk_level: str,
        is_destructive: bool,
        is_cross_system: bool,
    ) -> AutonomyDecision:
        """Evaluate which action to take for an operation.

        Rules are evaluated in order; the first rule whose condition
        evaluates to True wins.  If no rule matches, a catch-all
        ``auto_confirm`` decision is returned.

        Condition expressions support a safe subset of Python syntax:
          - attribute comparisons: ``risk_level == 'LOW'``
          - membership tests:    ``risk_level in ('LOW', 'MEDIUM')``
          - bare booleans:       ``is_destructive``
          - bare attribute:      ``is_cross_system``
          - catch-all:           ``else``

        Raises
        ------
        ValueError
            If a rule condition cannot be parsed.
        TypeError
            If a rule condition does not evaluate to a bool.
        """
        locals_dict: dict[str, object] = {
            "risk_level": risk_level,
            "is_destructive": is_destructive,
            "is_cross_system": is_cross_system,
        }

        for rule in self.rules:
            # Catch-all for when no specific rule matched
            if rule.condition == "else":
                rationale = (
                    f"no prior rule matched for operation={operation!r}, "
                    f"risk_level={risk_level!r}, is_destructive={is_destructive}, "
                    f"is_cross_system={is_cross_system}"
                )
                return AutonomyDecision(
                    action_taken=rule.action,
                    matched_rule=rule,
                    rationale=rationale,
                )

            # Build the eval-safe expression
            cond = rule.condition

            # Substitute single-quoted string literals with double-quoted equivalents
            # so we can safely evaluate them (avoids injection via quote tricks).
            # This is safe because the RHS of == / `in` must be a string literal
            # in the condition grammar defined by the spec.
            cond_safe = _substitute_quotes(cond)

            try:
                result = eval(cond_safe, {}, locals_dict)
            except Exception as exc:
                raise ValueError(
                    f"cannot evaluate condition {cond!r}: {exc}"
                ) from exc

            if not isinstance(result, bool):
                raise TypeError(
                    f"condition {cond!r} did not evaluate to bool (got {type(result).__name__})"
                )

            if result:
                # Rate-limit check
                if rule.max_decisions_per_hour > 0:
                    key = ("|".join(rule.scope), rule.action)
                    now = time.time()
                    self._decision_clock.setdefault(key, [])
                    self._decision_clock[key] = [
                        ts for ts in self._decision_clock[key]
                        if now - ts < 3600
                    ]
                    if len(self._decision_clock[key]) >= rule.max_decisions_per_hour:
                        rationale = (
                            f"rate limit ({rule.max_decisions_per_hour}/hour) reached "
                            f"for scope={rule.scope}, action={rule.action}"
                        )
                        return AutonomyDecision(
                            action_taken="human_token",
                            matched_rule=rule,
                            rationale=rationale,
                        )
                    self._decision_clock[key].append(now)

                rationale = (
                    f"rule[{rule.condition}] matched: "
                    f"operation={operation!r}, risk_level={risk_level!r}, "
                    f"is_destructive={is_destructive}, is_cross_system={is_cross_system}"
                )
                return AutonomyDecision(
                    action_taken=rule.action,
                    matched_rule=rule,
                    rationale=rationale,
                )

        # No rule matched — safe default
        rationale = (
            f"no rule matched for operation={operation!r}, "
            f"risk_level={risk_level!r}; defaulting to auto_confirm"
        )
        return AutonomyDecision(
            action_taken="auto_confirm",
            matched_rule=None,
            rationale=rationale,
        )


def _substitute_quotes(expr: str) -> str:
    """Convert single-quoted string literals in a condition to double quotes.

    This prevents a user from closing the quote early and injecting
    arbitrary expressions into the ``eval()`` call.
    """
    # Replace single-quoted strings:  'LOW'  →  "LOW"
    return re.sub(r"'([^']+)'", lambda m: f'"{m.group(1)}"', expr)


# ----------------------------------------------------------------------
# Pre-defined policies
# ----------------------------------------------------------------------

# Level 0 (Phase 1): All destructive ops need human token; everything else auto-confirms
LEVEL_0 = AutonomyPolicy(
    level=0,
    description="All destructive ops need human token",
    rules=[
        AutonomyRule(
            condition="is_destructive",
            action="human_token",
            scope=["*"],
            require_audit=True,
        ),
        # Catch-all so non-destructive operations auto-confirm
        AutonomyRule(
            condition="else",
            action="auto_confirm",
            scope=["*"],
            require_audit=False,
        ),
    ],
)

# Level 1 (Phase 2): LOW auto, MEDIUM critic, HIGH/CRITICAL human
LEVEL_1 = AutonomyPolicy(
    level=1,
    description="LOW auto, MEDIUM critic, HIGH/CRITICAL human",
    rules=[
        AutonomyRule(
            condition="risk_level == 'LOW'",
            action="auto_confirm",
            scope=["*"],
            require_audit=False,
        ),
        AutonomyRule(
            condition="risk_level == 'MEDIUM'",
            action="critic_review",
            scope=["*"],
            require_audit=True,
        ),
        AutonomyRule(
            condition="risk_level in ('HIGH', 'CRITICAL')",
            action="human_token",
            scope=["*"],
            require_audit=True,
        ),
    ],
)

# Level 2 (Phase 3 early): LOW/MEDIUM auto, HIGH critic, CRITICAL approval
# NOTE: is_cross_system rule MUST come before risk_level rules (first match wins)
LEVEL_2 = AutonomyPolicy(
    level=2,
    description="LOW/MEDIUM auto, HIGH critic, CRITICAL approval",
    rules=[
        # Cross-system operations always need a human token — evaluated first
        AutonomyRule(
            condition="is_cross_system",
            action="human_token",
            scope=["*"],
            require_audit=True,
        ),
        AutonomyRule(
            condition="risk_level in ('LOW', 'MEDIUM')",
            action="auto_confirm",
            scope=["*"],
            require_audit=False,
        ),
        AutonomyRule(
            condition="risk_level == 'HIGH'",
            action="critic_review",
            scope=["*"],
            require_audit=True,
        ),
        AutonomyRule(
            condition="risk_level == 'CRITICAL'",
            action="human_approval",
            scope=["*"],
            require_audit=True,
        ),
    ],
)

# Level 3 (Phase 3 late): Only CRITICAL needs approval; cross-system needs token
# NOTE: is_cross_system rule MUST come before risk_level rules (first match wins)
LEVEL_3 = AutonomyPolicy(
    level=3,
    description="Only CRITICAL needs approval; cross-system always needs token",
    rules=[
        # Cross-system operations always need a human token — evaluated first
        AutonomyRule(
            condition="is_cross_system",
            action="human_token",
            scope=["*"],
            require_audit=True,
        ),
        AutonomyRule(
            condition="risk_level in ('LOW', 'MEDIUM', 'HIGH')",
            action="auto_confirm",
            scope=["*"],
            require_audit=False,
        ),
        AutonomyRule(
            condition="risk_level == 'CRITICAL'",
            action="human_approval",
            scope=["*"],
            require_audit=True,
        ),
    ],
)


# ----------------------------------------------------------------------
# Convenience evaluator used by harness_safety.py
# ----------------------------------------------------------------------

def evaluate_autonomy(
    operation: str,
    risk_level: str,
    is_destructive: bool,
    is_cross_system: bool,
    level: int = 0,
) -> str:
    """Evaluate which action to take for an operation at the given autonomy level.

    Returns
    -------
    str
        One of: ``auto_confirm``, ``critic_review``, ``human_token``, ``human_approval``.
    """
    policies: dict[int, AutonomyPolicy] = {
        0: LEVEL_0,
        1: LEVEL_1,
        2: LEVEL_2,
        3: LEVEL_3,
    }
    policy = policies.get(level, LEVEL_0)
    return policy.evaluate(
        operation=operation,
        risk_level=risk_level,
        is_destructive=is_destructive,
        is_cross_system=is_cross_system,
    ).action_taken
