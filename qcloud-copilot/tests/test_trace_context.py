"""Tests for trace_context.py — P1.1."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "qcloud-copilot"))

from copilot.trace_context import (
    TraceContext,
    new_observation_id,
    new_trace_id,
)


def test_new_trace_id_format():
    tid = new_trace_id()
    assert tid.startswith("trc-")
    assert len(tid) == 16  # trc- + 12 hex


def test_new_observation_id_format():
    oid = new_observation_id()
    assert oid.startswith("obs-")
    assert len(oid) == 16  # obs- + 12 hex


def test_trace_id_stable_across_calls():
    ids = [new_trace_id() for _ in range(5)]
    assert len(set(ids)) == 5  # all unique


def test_session_id_defaults_to_trace_id():
    ctx = TraceContext(trace_id="trc-abc")
    assert ctx.session_id == "trc-abc"


def test_session_id_can_be_different():
    ctx = TraceContext(trace_id="trc-abc", session_id="ses-xyz")
    assert ctx.session_id == "ses-xyz"
    assert ctx.trace_id == "trc-abc"


def test_parent_stack_empty_initially():
    ctx = TraceContext(trace_id="trc-test")
    assert ctx.current_parent() is None


def test_push_pop_parent():
    ctx = TraceContext(trace_id="trc-test")
    parent = ctx.push_observation("obs-1")
    assert parent is None  # stack was empty
    assert ctx.current_parent() == "obs-1"

    parent2 = ctx.push_observation("obs-2")
    assert parent2 == "obs-1"  # previous top
    assert ctx.current_parent() == "obs-2"

    popped = ctx.pop_observation()
    assert popped == "obs-2"
    assert ctx.current_parent() == "obs-1"

    popped2 = ctx.pop_observation()
    assert popped2 == "obs-1"
    assert ctx.current_parent() is None


def test_pop_empty_stack_returns_none():
    ctx = TraceContext(trace_id="trc-test")
    assert ctx.pop_observation() is None


def test_observe_context_manager():
    ctx = TraceContext(trace_id="trc-test")
    with ctx.observe("span-1") as (obs_id, parent):
        assert obs_id.startswith("obs-")
        assert parent is None  # first observation, no parent
        assert ctx.current_parent() == obs_id
        with ctx.observe("span-2") as (child_id, child_parent):
            assert child_id.startswith("obs-")
            assert child_parent == obs_id
            assert ctx.current_parent() == child_id
        # after exiting span-2, parent is back to span-1
        assert ctx.current_parent() == obs_id
    # after exiting span-1, stack is empty
    assert ctx.current_parent() is None


def test_close_sets_ended_at_and_status():
    ctx = TraceContext(trace_id="trc-test")
    assert ctx.ended_at is None
    ctx.close(status="error")
    assert ctx.ended_at is not None
    assert ctx.status == "error"


def test_identity_defaults_to_null_tree():
    ctx = TraceContext(trace_id="trc-test")
    data = ctx.identity.to_dict()
    assert data["user_id"] is None
    assert data["tenant_id"] is None


def test_identity_can_be_passed():
    from copilot.trace_records import IdentityTree
    identity = IdentityTree(
        user_id="user-123",
        tenant_id="tenant-456",
        initiator_type="cli",
        identity_source="config",
        identity_confidence="declared",
    )
    ctx = TraceContext(trace_id="trc-test", identity=identity)
    data = ctx.identity.to_dict()
    assert data["user_id"] == "user-123"
    assert data["tenant_id"] == "tenant-456"


def test_to_dict():
    ctx = TraceContext(
        trace_id="trc-test",
        session_id="ses-test",
        incident_id="inc-001",
    )
    d = ctx.to_dict()
    assert d["trace_id"] == "trc-test"
    assert d["session_id"] == "ses-test"
    assert d["incident_id"] == "inc-001"
    assert "identity" in d
    assert "automation" in d
