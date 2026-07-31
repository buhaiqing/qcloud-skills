"""TRACE-1 v3 trace context: trace_id generation, span stack, identity propagation.

Responsibilities:
  - Generate stable v3 trace IDs (trc- prefix) distinct from session_id
  - Maintain observation parent chain (push/pop)
  - Carry identity tree and automation tree through execution
  - Provide current parent_observation_id for nested observations

Usage:
  ctx = TraceContext(session_id="ses-abc")
  with ctx.observe("root-span") as parent_id:
      with ctx.observe("child-span") as child_id:
          pass  # parent_id is "obs-xxx", child_id is "obs-yyy"
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from copilot.trace_records import AutomationTree, IdentityTree


def new_trace_id() -> str:
    """Generate a stable v3 trace ID (trc- prefix, 12 hex chars)."""
    return f"trc-{uuid.uuid4().hex[:12]}"


def new_observation_id() -> str:
    """Generate an observation ID."""
    return f"obs-{uuid.uuid4().hex[:12]}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class TraceContext:
    """TRACE-1 v3 execution context.

    trace_id is the v3 aggregate root ID; session_id is the Copilot session
    (they may be equal for simplicity but have distinct semantics per SPEC §4.1).
    """

    trace_id: str
    session_id: str | None = None
    incident_id: str | None = None
    started_at: str = field(default_factory=_utc_now)
    ended_at: str | None = None
    status: str = "success"
    # Identity (SPEC §16)
    identity: IdentityTree = field(default_factory=IdentityTree)
    automation: AutomationTree = field(default_factory=AutomationTree)
    # Internal
    _parent_stack: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.session_id is None:
            self.session_id = self.trace_id

    def push_observation(self, obs_id: str) -> str | None:
        """Push obs_id onto the parent stack; returns previous parent or None."""
        parent = self._parent_stack[-1] if self._parent_stack else None
        self._parent_stack.append(obs_id)
        return parent

    def pop_observation(self) -> str | None:
        """Pop current observation ID from stack; returns it."""
        if not self._parent_stack:
            return None
        return self._parent_stack.pop()

    def current_parent(self) -> str | None:
        """Top of parent stack, or None if no active observation."""
        return self._parent_stack[-1] if self._parent_stack else None

    def close(self, status: str = "success") -> None:
        self.ended_at = _utc_now()
        self.status = status

    @contextmanager
    def observe(self, name: str = ""):
        """Context manager: generate obs ID, push parent, yield, pop on exit."""
        obs_id = new_observation_id()
        parent = self.push_observation(obs_id)
        try:
            yield obs_id, parent
        finally:
            self.pop_observation()

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "incident_id": self.incident_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "identity": self.identity.to_dict(),
            "automation": self.automation.to_dict(),
        }
