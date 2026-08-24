#!/usr/bin/env python3
"""Phase 3 — Autonomous destructive detection + human-issued token<->plan binding.
CRITICAL: the confirmation token is issued by a HUMAN at the plan-review gate
(non-weakening of AGENTS.md destructive-op confirmation rule). This module only
binds/verifies the human-issued token against the plan hash; it never generates one.
"""
from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

# Canonical destructive-verb list lives in assets/shared/destructive_verbs.json
# (single source — AGENTS.md TE-4/L13). Loaded at import time via an absolute
# path derived from __file__, so it is robust to the caller's cwd. If the asset
# is missing/corrupt, fall back to the previous inline set (never crash the
# importing tool) with a visible warning.
_SHARED_JSON = Path(__file__).resolve().parent.parent / "assets" / "shared" / "destructive_verbs.json"
_FALLBACK_VERBS = {"delete", "terminate", "destroy", "drop", "reset", "remove", "stop"}


def _load_verbs(path: Path | None = None) -> set[str]:
    """Load the destructive-verb set from a shared JSON asset (or the fallback)."""
    target = path or _SHARED_JSON
    try:
        with open(target, encoding="utf-8") as fh:
            return set(json.load(fh))
    except Exception:  # noqa: BLE001
        warnings.warn(f"cannot load {target}; falling back to built-in VERBS")
        return set(_FALLBACK_VERBS)


VERBS = _load_verbs()


# Inflections a destructive verb may legitimately carry. Matching these
# explicitly keeps "deleted"/"removes"/"stopping" destructive while refusing
# open-ended prefix matches, which previously flagged "resettable" (reset),
# "release notes" (release) and "formatting" (format) as destructive. Every
# false positive trains operators to rubber-stamp the confirmation gate, so
# over-matching is a safety regression rather than a conservative default.
_INFLECTIONS = ("", "s", "es", "d", "ed", "ing")


def is_destructive(plan_text: str) -> bool:
    tokens = {t.strip(".,;:!?()[]{}\"'`") for t in plan_text.lower().split()}
    return any(_matches(t, v) for t in tokens for v in VERBS)


def _matches(token: str, verb: str) -> bool:
    if len(verb) < 3:
        # A 2-char stem collides with too much benign vocabulary to inflect.
        return token == verb
    # "delete" + "d" -> "deleted"; also handle stems that drop a trailing "e"
    # ("terminate" -> "terminating") and consonant doubling ("stop" -> "stopping").
    stems = {verb, verb.rstrip("e"), verb + verb[-1]}
    return any(token == stem + suffix for stem in stems for suffix in _INFLECTIONS)


def plan_hash(plan_text: str) -> str:
    return hashlib.sha256(plan_text.encode()).hexdigest()[:16]


def bind_token(plan_text: str, human_token: str) -> str:
    """Verify the human-issued token equals the plan hash. Raise PermissionError if not.
    Returns the token on success (execution may proceed)."""
    expected = plan_hash(plan_text)
    if human_token != expected:
        raise PermissionError("confirmation token does not match plan_hash")
    return human_token


# ----------------------------------------------------------------------
# Phase 3.4.3 — AutonomyPolicy integration
# ----------------------------------------------------------------------
try:
    from autonomy_policy import LEVEL_0, LEVEL_1, LEVEL_2, LEVEL_3

    def evaluate_autonomy(
        operation: str,
        risk_level: str,
        is_destructive: bool,
        is_cross_system: bool,
        level: int = 0,
    ) -> str:
        """Evaluate which action to take for an operation given autonomy level.
        Returns action string: 'auto_confirm' | 'critic_review' | 'human_token' | 'human_approval'"""
        policies = {0: LEVEL_0, 1: LEVEL_1, 2: LEVEL_2, 3: LEVEL_3}
        policy = policies.get(level, LEVEL_0)
        return policy.evaluate(operation, risk_level, is_destructive, is_cross_system).action_taken

except ImportError:
    # autonomy_policy.py not yet available — provide a safe stub
    def evaluate_autonomy(
        operation: str,
        risk_level: str,
        is_destructive: bool,
        is_cross_system: bool,
        level: int = 0,
    ) -> str:
        """Fallback when AutonomyPolicy is not yet available."""
        return "human_token"
