#!/usr/bin/env python3
"""ErrorEscalator — runtime error escalation chain for skill execution.

Phase 1.3 of the L3 Adaptive Orchestration plan. Given a Tencent Cloud API
error code (e.g. ``InvalidVpc.NotFound``), resolves an ``ErrorRule`` that
tells the dispatcher whether to HALT, RETRY with backoff, FIX the call
once, or DELEGATE to another skill.

Design notes:

* **Safe default**: unknown codes → ``Action.HALT``. Never silently retry
  an unknown error; never silently succeed.
* **Prefix fallback**: ``InvalidVpc.NotFound`` → exact match → if missing,
  falls back to ``InvalidVpc`` → falls back to wildcard → finally HALT.
* **Specific-product rule wins**: a rule with ``product="cvm"`` is preferred
  over one with ``product=""`` when both match.
* **Pure stdlib**: no PyYAML, no regex gymnastics beyond the parser module.

Public API:

    Action            StrEnum: HALT / RETRY / FIX / DELEGATE
    ErrorRule         dataclass
    ErrorEscalator    main resolver
        add_rule(rule)
        load_from_skill(skill_dir) -> int
        load_all_skills(repo_root) -> int
        resolve(error_code, product="") -> ErrorRule
        compute_backoff(strategy, attempt) -> float
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Action(str, Enum):
    HALT = "HALT"
    RETRY = "RETRY"
    FIX = "FIX"
    DELEGATE = "DELEGATE"


@dataclass
class ErrorRule:
    code: str
    product: str = ""  # "" = wildcard; otherwise exact product name (e.g. "cvm")
    action: Action = Action.HALT
    max_retries: int = 0
    backoff_seconds: list[int] = field(default_factory=list)
    backoff_strategy: str = "fixed"  # "fixed" | "exponential"
    delegate_to: str | None = None
    recovery_hint: str = ""


def _safe_halt_rule(error_code: str, product: str = "") -> ErrorRule:
    """Construct the HALT fallback rule returned for unknown error codes."""
    return ErrorRule(
        code=error_code,
        product=product,
        action=Action.HALT,
        max_retries=0,
        recovery_hint=(
            "Unknown error code; treating as critical (HALT). "
            "Add an explicit rule to escalate this code."
        ),
    )


class ErrorEscalator:
    """Resolve an API error code into an ``ErrorRule`` and backoff schedule."""

    def __init__(self, rules: Iterable[ErrorRule] | None = None) -> None:
        self._rules: list[ErrorRule] = list(rules) if rules else []

    # ---- mutation ---------------------------------------------------------

    def add_rule(self, rule: ErrorRule) -> None:
        self._rules.append(rule)

    def add_rules(self, rules: Iterable[ErrorRule]) -> None:
        self._rules.extend(rules)

    # ---- resolution -------------------------------------------------------

    def resolve(self, error_code: str, product: str = "") -> ErrorRule:
        """Return the best matching ``ErrorRule`` for ``error_code``.

        Resolution order (highest priority first):

        1. Exact ``(code, product)`` — returns immediately.
        2. Exact ``(code, "")`` — wildcard-product rule.
        3. Prefix ``(code-prefix, product)`` — most specific prefix wins.
        4. Prefix ``(code-prefix, "")`` — wildcard product.
        5. ``HALT`` fallback.
        """
        if not error_code:
            return _safe_halt_rule(error_code or "<empty>", product)

        best_rule: ErrorRule | None = None
        best_score: int = -1

        for rule in self._rules:
            score = _match_score(rule, error_code, product)
            if score > best_score:
                best_score = score
                best_rule = rule

        if best_rule is not None:
            return best_rule
        return _safe_halt_rule(error_code, product)

    # ---- backoff ----------------------------------------------------------

    def compute_backoff(self, strategy: str, attempt: int) -> float:
        """Return backoff in seconds for the given strategy + 0-indexed attempt.

        Supported strategies:

        * ``"exponential"`` → ``2 ** attempt`` seconds (1, 2, 4, 8, ...)
        * ``"fixed"``       → 1.0 seconds (caller may consult rule.backoff_seconds)
        * anything else     → 1.0 (safe default; never crashes the caller)
        """
        if strategy == "exponential":
            try:
                return float(2 ** max(0, int(attempt)))
            except (TypeError, ValueError):
                return 1.0
        return 1.0

    # ---- skill loading ----------------------------------------------------

    def load_from_skill(self, skill_dir: Path) -> int:
        """Parse ``skill_dir/SKILL.md`` and register every ErrorRule found.

        Returns the number of rules added. Returns 0 when the file does
        not exist (skill_dir may be a stub or scaffold).
        """
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            return 0
        # Local import keeps parser module optional at import time.
        from error_table_parser import parse_error_table

        rules = parse_error_table(skill_md.read_text(encoding="utf-8"))
        self._rules.extend(rules)
        return len(rules)

    def load_all_skills(self, repo_root: Path) -> int:
        """Scan every ``qcloud-*-ops/SKILL.md`` under ``repo_root`` and load rules."""
        total = 0
        for sk in sorted(repo_root.glob("qcloud-*-ops")):
            if not sk.is_dir():
                continue
            total += self.load_from_skill(sk)
        return total


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _match_score(rule: ErrorRule, error_code: str, product: str) -> int:
    """Score a rule against the query. Higher = better. -1 = no match.

    Scoring (lower-priority first):

    * Prefix match (rule.code is a dotted prefix of error_code):
      score = ``len(rule.code)`` (longer prefix = better fallback)
    * Exact match (rule.code == error_code):
      score = ``1000 + (10 if specific product else 0)`` to break ties.
    """
    if not rule.code:
        return -1
    if rule.product and rule.product != product:
        return -1

    if rule.code == error_code:
        return 1000 + (10 if rule.product else 0)
    if error_code.startswith(rule.code + "."):
        return len(rule.code)
    return -1


# Module-level convenience shim so callers can use either
# ``escalator.compute_backoff(...)`` or the bare ``compute_backoff(...)``.

def compute_backoff(strategy: str, attempt: int) -> float:
    return ErrorEscalator().compute_backoff(strategy, attempt)