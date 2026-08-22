#!/usr/bin/env python3
"""Tiered HITL approval gate for risky ops actions."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from harness_safety import bind_token, is_destructive, plan_hash


class ApprovalTier(Enum):
    AUTO = "auto"
    TOKEN_BOUND = "token_bound"
    HUMAN_REVIEW = "human_review"


class Decision(Enum):
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT_DEGRADED = "timeout_degraded"


@dataclass
class ApprovalDecision:
    incident_id: str
    plan_text: str
    tier: ApprovalTier
    decision: Decision
    approver: str
    token_hash: str
    timestamp: float
    reason: str


def classify_action(plan_text: str, severity: str) -> ApprovalTier:
    """Classify a plan into an approval tier."""
    if not is_destructive(plan_text):
        return ApprovalTier.AUTO
    sev = severity.strip().lower()
    if sev in ("critical", "high"):
        return ApprovalTier.HUMAN_REVIEW
    if sev in ("info", "warning"):
        return ApprovalTier.TOKEN_BOUND
    # Unknown severity defaults to stricter review when destructive
    return ApprovalTier.HUMAN_REVIEW


def _resolve_now(now: float | Callable[[], float] | None) -> float:
    if now is None:
        return time.monotonic()
    if callable(now):
        return float(now())
    return float(now)


def request_approval(
    plan_text: str,
    severity: str,
    trace: dict[str, Any],
    *,
    timeout_s: float = 30.0,
    now: float | Callable[[], float] | None = None,
    human_token: str | None = None,
    human_approver: str | None = None,
    incident_id: str | None = None,
) -> ApprovalDecision:
    """Request approval for a plan and append an auditable record to trace."""
    tier = classify_action(plan_text, severity)
    ts = _resolve_now(now)
    iid = incident_id if incident_id is not None else plan_hash(plan_text)
    # Simulate deadline: start is 0, elapsed is ts; timeout when ts >= timeout_s.
    timed_out = ts >= timeout_s

    decision: Decision
    approver: str
    token_hash: str
    reason: str

    if tier == ApprovalTier.AUTO:
        decision = Decision.APPROVED
        approver = "system"
        token_hash = ""
        reason = "non-destructive plan auto-approved"
    elif tier == ApprovalTier.TOKEN_BOUND:
        if human_token is not None:
            try:
                bind_token(plan_text, human_token)
                decision = Decision.APPROVED
                approver = "human-token"
                token_hash = plan_hash(plan_text)
                reason = "token bound successfully"
            except PermissionError:
                if timed_out:
                    decision = Decision.TIMEOUT_DEGRADED
                    approver = ""
                    token_hash = ""
                    reason = "invalid token and deadline elapsed — degraded"
                else:
                    decision = Decision.DENIED
                    approver = ""
                    token_hash = ""
                    reason = "invalid token"
        else:
            if timed_out:
                decision = Decision.TIMEOUT_DEGRADED
                approver = ""
                token_hash = ""
                reason = "no valid token before deadline — degraded"
            else:
                decision = Decision.DENIED
                approver = ""
                token_hash = ""
                reason = "missing token"
    else:  # HUMAN_REVIEW
        if human_approver is not None and human_approver.strip() != "":
            decision = Decision.APPROVED
            approver = human_approver.strip()
            token_hash = ""
            reason = "human approver signed"
        else:
            if timed_out:
                decision = Decision.TIMEOUT_DEGRADED
                approver = ""
                token_hash = ""
                reason = "no human sign-off before deadline — degraded"
            else:
                decision = Decision.DENIED
                approver = ""
                token_hash = ""
                reason = "awaiting human sign-off"

    result = ApprovalDecision(
        incident_id=iid,
        plan_text=plan_text,
        tier=tier,
        decision=decision,
        approver=approver,
        token_hash=token_hash,
        timestamp=ts,
        reason=reason,
    )

    chain = trace.get("approval_chain")
    if not isinstance(chain, list):
        trace["approval_chain"] = []
        chain = trace["approval_chain"]
    chain.append(
        {
            "tier": tier.value,
            "decision": decision.value,
            "timestamp": ts,
            "approver": approver,
            "token_hash": token_hash,
            "reason": reason,
        }
    )
    return result
