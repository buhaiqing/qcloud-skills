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
