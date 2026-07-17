"""P6 — L2 confirmation result into audit_trace (rule safety.l2_confirm)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from copilot.dispatcher import PlanDispatcher
from copilot.engine import CopilotEngine
from copilot.integration.skills import SkillDispatcher
from copilot.models import PlanStep, StepResult


def _load_l2_traces(session_id: str) -> list[dict]:
    # audit_trace spreads trace_data keys to the top level of the record.
    audit_dir = Path.cwd() / ".runtime" / "gcl" / "copilot" / "audit" / session_id
    records: list[dict] = []
    if not audit_dir.exists():
        return records
    for f in audit_dir.glob("*.json"):
        rec = json.loads(f.read_text(encoding="utf-8"))
        prov = rec.get("provenance") or {}
        if prov.get("rule") == "safety.l2_confirm":
            records.append(rec)
    return records


def _fake_plan(destructive: bool) -> MagicMock:
    step = PlanStep(
        id="s1",
        type="skill_call",
        skill="qcloud-cvm-ops",
        operation="describe-instances",
        destructive=destructive,
    )
    plan = MagicMock()
    plan.plan_id = "plan-l2"
    plan.steps = [step]
    return plan


def test_engine_emits_l2_trace_on_pass(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = CopilotEngine()
    engine._emit_l2_trace("ses-engine-pass", _fake_plan(True), passed=True, issues=[])

    traces = _load_l2_traces("ses-engine-pass")
    assert len(traces) == 1
    assert traces[0]["provenance"]["decision"] == "pass"
    assert traces[0]["status"] == "pass"
    assert traces[0]["destructive_steps"] == ["s1"]


def test_engine_emits_l2_trace_on_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = CopilotEngine()
    engine._emit_l2_trace(
        "ses-engine-fail",
        _fake_plan(True),
        passed=False,
        issues=["destructive op requires confirmation"],
    )

    traces = _load_l2_traces("ses-engine-fail")
    assert len(traces) == 1
    assert traces[0]["provenance"]["decision"] == "fail"
    assert traces[0]["status"] == "fail"
    assert "requires confirmation" in traces[0]["provenance"]["reason"]


def test_dispatcher_emits_step_l2_trace_when_destructive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    step = PlanStep(
        id="del-1",
        type="skill_call",
        skill="qcloud-cvm-ops",
        operation="delete-instances",
        destructive=True,
    )
    plan = MagicMock()
    plan.steps = [step]
    plan.context = {}

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(step_id="del-1", status="success")

    disp = PlanDispatcher(skill_dispatcher=skill)
    disp._execute_step(step, plan, MagicMock(), "ses-l2-step", l2_confirmed=True)

    traces = _load_l2_traces("ses-l2-step")
    assert len(traces) == 1
    assert traces[0]["provenance"]["decision"] == "pass"
    assert traces[0]["status"] == "pass"
    assert traces[0]["destructive"] is True


def test_dispatcher_l2_trace_unconfirmed_without_confirm(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    step = PlanStep(
        id="del-2",
        type="skill_call",
        skill="qcloud-cvm-ops",
        operation="delete-instances",
        destructive=True,
    )
    plan = MagicMock()
    plan.steps = [step]
    plan.context = {}

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(step_id="del-2", status="success")

    disp = PlanDispatcher(skill_dispatcher=skill)
    disp._execute_step(step, plan, MagicMock(), "ses-l2-unconf", l2_confirmed=False)

    traces = _load_l2_traces("ses-l2-unconf")
    assert len(traces) == 1
    assert traces[0]["provenance"]["decision"] == "fail"
    assert traces[0]["status"] == "unconfirmed"


def test_dispatcher_skips_l2_trace_for_non_destructive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    step = PlanStep(
        id="read-1",
        type="skill_call",
        skill="qcloud-cvm-ops",
        operation="describe-instances",
        destructive=False,
    )
    plan = MagicMock()
    plan.steps = [step]
    plan.context = {}

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(step_id="read-1", status="success")

    disp = PlanDispatcher(skill_dispatcher=skill)
    disp._execute_step(step, plan, MagicMock(), "ses-l2-read", l2_confirmed=True)

    assert _load_l2_traces("ses-l2-read") == []
