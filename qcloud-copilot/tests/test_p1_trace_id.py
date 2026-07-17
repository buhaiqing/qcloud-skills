"""P1 regression tests: trace_id/eval_id unification across copilot + GCL chain.

Covers:
1. run_gcl threads session_id as --trace-id into gcl_runner (P1 core lineage).
2. dispatcher._emit_trace emits exec.step provenance with eval_id shape
   ``<session_id>:<step_id>:<rule>`` for the generic (non-L2) step path.
3. L2 provenance (safety.l2_confirm) is NOT overwritten by the generic change.
"""

from __future__ import annotations

from unittest.mock import patch

from copilot.dispatcher import PlanDispatcher
from copilot.integration.gcl import run_gcl
from copilot.models import PlanStep, StepResult


def _make_step(step_id: str = "s1", skill: str = "qcloud-cvm-ops", operation: str = "DescribeInstances", destructive: bool = False) -> PlanStep:
    return PlanStep(
        id=step_id,
        type="skill_call",
        skill=skill,
        operation=operation,
        reads_from_blackboard=[],
        writes_to_blackboard=[],
        destructive=destructive,
    )


def test_run_gcl_passes_trace_id():
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return type("R", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()

    with patch("copilot.integration.gcl.subprocess.run", fake_run):
        run_gcl("qcloud-cvm-ops", "DescribeInstances", {"x": 1}, session_id="ses-abc")

    cmd = captured["cmd"]
    assert "--trace-id" in cmd, f"--trace-id missing from cmd: {cmd}"
    idx = cmd.index("--trace-id")
    assert cmd[idx + 1] == "ses-abc", f"--trace-id value wrong: {cmd}"


def test_run_gcl_omits_trace_id_when_none():
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return type("R", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()

    with patch("copilot.integration.gcl.subprocess.run", fake_run):
        run_gcl("qcloud-cvm-ops", "DescribeInstances", {"x": 1})

    assert "--trace-id" not in captured["cmd"], f"--trace-id should be absent: {captured['cmd']}"


def test_emit_trace_emits_exec_step_provenance():
    captured = {}

    def fake_audit(**kwargs):
        captured.update(kwargs)

    disp = PlanDispatcher.__new__(PlanDispatcher)
    step = _make_step(step_id="s1")
    result = StepResult(step_id="s1", status="success", duration_ms=10)
    with patch("copilot.dispatcher.audit_trace", fake_audit):
        disp._emit_trace("ses-xyz", step, result, provenance=None)

    assert captured.get("provenance") is not None, "generic path must emit provenance"
    prov = captured["provenance"]
    assert prov["eval_id"] == "ses-xyz:s1:exec.step", f"eval_id shape wrong: {prov}"
    assert prov["rule"] == "exec.step"
    assert prov["decision"] == "success"


def test_emit_trace_keeps_caller_provenance():
    captured = {}
    caller_prov = {"eval_id": "ses-xyz:s1:custom.rule", "rule": "custom.rule", "input_ref": "x", "decision": "pass", "reason": "ok"}

    def fake_audit(**kwargs):
        captured.update(kwargs)

    disp = PlanDispatcher.__new__(PlanDispatcher)
    step = _make_step(step_id="s1")
    result = StepResult(step_id="s1", status="success", duration_ms=10)
    with patch("copilot.dispatcher.audit_trace", fake_audit):
        disp._emit_trace("ses-xyz", step, result, provenance=caller_prov)

    assert captured["provenance"] is caller_prov, "caller-provided provenance must not be overwritten"
