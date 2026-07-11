"""Evidence chain builder + Blackboard integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from copilot.blackboard import BlackboardClient
from copilot.evidence import build_evidence_chain
from copilot.models import ClassifiedIntent, ExecutionPlan, IntentType, PlanStep, StepResult
from copilot.report_gen import synthesize_from_blackboard

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / ".runtime" / "blackboard" / "schema.json"
FIXTURE_PATH = REPO_ROOT / ".runtime" / "blackboard" / "fixtures" / "evidence-chain.json"


@pytest.fixture
def validator() -> jsonschema.Draft7Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return jsonschema.Draft7Validator(
        schema,
        format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER,
    )


def test_evidence_fixture_validates(validator: jsonschema.Draft7Validator) -> None:
    instance = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    validator.validate(instance)


def test_build_evidence_chain_topology_strategy() -> None:
    plan = ExecutionPlan(
        intent=ClassifiedIntent(primary=IntentType.REPORT, secondary=[], targets=[]),
        context={"customer": "朔州天源", "region": "ap-guangzhou"},
        steps=[
            PlanStep(
                id="vpc-0",
                type="skill_call",
                skill="qcloud-vpc-ops",
                operation="describe-vpcs",
                description="VPC 拓扑上下文",
            )
        ],
    )
    contributions = {
        "qcloud-proactive-inspection": {
            "verdict": "WARNING",
            "findings": [{"id": "f1", "severity": "P1", "summary": "磁盘未加密"}],
            "topology_hints": ["i-1"],
            "metadata": {
                "resource_coverage": {"total_analyzed_resources": 9},
            },
        }
    }
    sniff = {
        "raw": {"vms": [{"instanceId": "i-1"}], "lbs": [{"loadBalancerId": "lb-1"}]},
        "topology": {"vpcs": [{"vpcId": "vpc-1"}]},
    }
    chain = build_evidence_chain(
        user_request="朔州天源 VPC 风险巡检",
        plan=plan,
        step_results=[
            StepResult(step_id="vpc-0", status="success", duration_ms=100),
        ],
        contributions=contributions,
        sniff_data=sniff,
    )
    assert chain["schema_version"] == "1.1"
    assert chain["strategy"]["decision_maker"] == "topology_reasoner_v1"
    assert chain["strategy"]["llm_native_target"] is True
    assert chain["results"]["overall_verdict"] == "WARNING"
    assert len(chain["strategy"]["priority_chain"]) >= 1


def test_blackboard_write_evidence_chain(tmp_path: Path) -> None:
    repo_schema = REPO_ROOT / ".runtime" / "blackboard" / "schema.json"
    board_dir = tmp_path / "blackboard"
    board_dir.mkdir()
    board_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"), encoding="utf-8"
    )
    client = BlackboardClient(board_dir=board_dir)
    client.get_or_create("ses-ev", "test request")
    chain = {
        "schema_version": "1.1",
        "built_at": "2026-07-10T00:00:00+00:00",
        "strategy": {"mode": "topology_first"},
        "plan": {},
        "process": [],
        "results": {"overall_verdict": "PASS", "contributions": {}, "artifact_index": []},
    }
    client.write_evidence_chain("ses-ev", chain)
    loaded = client.read_evidence_chain("ses-ev")
    assert loaded is not None
    assert loaded["strategy"]["mode"] == "topology_first"


def test_report_includes_evidence_section() -> None:
    evidence = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["shared_context"][
        "evidence_chain"
    ]
    contributions = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["shared_context"][
        "contributions"
    ]
    report = synthesize_from_blackboard(
        contributions,
        audience="detailed",
        customer="朔州天源",
        evidence_chain=evidence,
    )
    titles = [s.title for s in report.sections]
    assert "巡检证据链" in titles
    evidence_sec = next(s for s in report.sections if s.title == "巡检证据链")
    blob = "\n".join(evidence_sec.findings)
    assert "topology_reasoner_v1" in blob
    assert "巡检策略" in blob
