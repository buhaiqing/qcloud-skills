"""Lightweight multi-agent negotiation + conflict detection.

In-memory, side-effect free except recorded proposal/decision state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Action = Literal["READ", "WRITE", "DELETE", "SCALE"]

MUTATING: frozenset[str] = frozenset({"WRITE", "DELETE", "SCALE"})


@dataclass(frozen=True)
class ResourceOp:
    """Intended operation by an agent on a cloud resource."""

    agent_id: str
    resource_id: str
    action: Action
    priority: int = 0

    def conflicts_with(self, other: ResourceOp) -> bool:
        """Return True if two ops on the same resource would conflict."""
        if self.resource_id != other.resource_id:
            return False
        if self.action == "READ" and other.action == "READ":
            return False
        return self.action in MUTATING or other.action in MUTATING


class NegotiationHub:
    """In-memory hub that collects proposals and resolves conflicts."""

    def __init__(self) -> None:
        self._ops: dict[str, ResourceOp] = {}
        self._decisions: dict[str, str] = {}
        self._counter: int = 0

    def propose(self, op: ResourceOp) -> str:
        """Record an intended op and return its proposal id."""
        self._counter += 1
        pid = f"p{self._counter}"
        self._ops[pid] = op
        return pid

    def detect_conflicts(self) -> list[tuple[str, str]]:
        """Return pairs of proposal ids whose ops conflict."""
        ids = list(self._ops.keys())
        conflicts: list[tuple[str, str]] = []
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if self._ops[a].conflicts_with(self._ops[b]):
                    conflicts.append((a, b))
        return conflicts

    def resolve(self) -> dict[str, str]:
        """Resolve all proposals; higher priority wins, ties by proposal id.

        Non-conflicting proposals are GRANTED. For each conflicting pair,
        the higher-priority proposal wins; ties broken deterministically by
        proposal id (lexicographically smaller wins).
        """
        # Build conflict graph: for each pid, set of conflicting pids
        conflicts = self.detect_conflicts()
        conflicting_ids: set[str] = set()
        for a, b in conflicts:
            conflicting_ids.add(a)
            conflicting_ids.add(b)

        # Non-conflicting -> GRANTED
        decisions: dict[str, str] = {}
        for pid in self._ops:
            if pid not in conflicting_ids:
                decisions[pid] = "GRANTED"

        # For conflicting proposals, sort by (-priority, pid) so winner is first
        # within each connected conflict group. Simplest deterministic rule:
        # globally sort conflicting proposals and greedily grant; deny anyone
        # who conflicts with an already-granted proposal with >= priority.
        # Equivalent to: for each pair (a,b), higher priority wins, tie -> smaller pid.
        # To satisfy all pairs simultaneously, we rank all conflicting pids.
        ranked = sorted(
            conflicting_ids,
            key=lambda pid: (-self._ops[pid].priority, pid),
        )

        # Track which resources have been claimed by a granted proposal
        # But conflicts are only within same resource, so per-resource tracking.
        granted_by_resource: dict[str, str] = {}  # resource_id -> winning pid
        denied: set[str] = set()

        for pid in ranked:
            if pid in denied:
                continue
            res = self._ops[pid].resource_id
            if res in granted_by_resource:
                # Already a winner for this resource; check if current should
                # actually win over the recorded winner (should not happen due
                # to sorted order, but handle groups correctly)
                # Since ranked is priority-desc, first one per resource wins.
                decisions[pid] = "DENIED"
                denied.add(pid)
            else:
                # This is the winner for this resource among conflicting ops.
                # Grant it; deny all other conflicting ops on same resource.
                decisions[pid] = "GRANTED"
                granted_by_resource[res] = pid
                # Deny remaining conflicting ops on same resource
                for other in conflicting_ids:
                    if other == pid or other in decisions:
                        continue
                    if self._ops[other].resource_id == res and self._ops[pid].conflicts_with(
                        self._ops[other]
                    ):
                        # Only deny those that actually conflict with winner
                        # (which they do by being in conflicting_ids for that resource,
                        # but verify)
                        decisions[other] = "DENIED"

        # Any conflicting id not yet decided (should not happen) -> DENIED
        for pid in conflicting_ids:
            if pid not in decisions:
                decisions[pid] = "DENIED"

        self._decisions = decisions
        return dict(decisions)

    def decisions(self) -> dict[str, str]:
        """Return last resolve decisions (proposal id -> GRANTED/DENIED)."""
        return dict(self._decisions)
