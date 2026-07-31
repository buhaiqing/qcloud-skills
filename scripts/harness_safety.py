#!/usr/bin/env python3
"""Phase 3 — Autonomous destructive detection + human-issued token<->plan binding.
CRITICAL: the confirmation token is issued by a HUMAN at the plan-review gate
(non-weakening of AGENTS.md destructive-op confirmation rule). This module only
binds/verifies the human-issued token against the plan hash; it never generates one.
"""
from __future__ import annotations

import hashlib

VERBS = {"delete", "terminate", "destroy", "drop", "reset", "remove", "stop"}


def is_destructive(plan_text: str) -> bool:
    # Prefix-match so inflected forms ("deleted", "removes", "removing") are
    # caught — a bare substring/split match would let "the instance will be
    # deleted" bypass the mandatory human-confirmation token.
    tokens = plan_text.lower().split()
    return any(t == v or t.startswith(v) for t in tokens for v in VERBS)


def plan_hash(plan_text: str) -> str:
    return hashlib.sha256(plan_text.encode()).hexdigest()[:16]


def bind_token(plan_text: str, human_token: str) -> str:
    """Verify the human-issued token equals the plan hash. Raise PermissionError if not.
    Returns the token on success (execution may proceed)."""
    expected = plan_hash(plan_text)
    if human_token != expected:
        raise PermissionError("confirmation token does not match plan_hash")
    return human_token
