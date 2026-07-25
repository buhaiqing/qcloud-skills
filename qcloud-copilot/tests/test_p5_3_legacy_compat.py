"""P5.3 — legacy compatibility: read old GCL trace JSON + old Copilot audit JSON
into the new ObservationRecord / UsageEvent schema and round-trip without
corrupting `_from_legacy` provenance metadata.
"""
from __future__ import annotations


def test_legacy_gcl_v1_record_parses_to_observation_with_provenance():
    from copilot.trace_records import legacy_gcl_to_observation

    gcl = {
        "run_id": "gcl-run-001",
        "iteration": 2,
        "generator": "Generator",
        "critic": "Critic",
        "passed": True,
        "timestamp": "2026-07-25T00:00:00Z",
        "latency_ms": 1234,
        "rubric_version": "rca-v1",
        "model_version": "gpt-4o",
        "prompt": {"role": "system", "content": "Diagnose ..."},
        "output": {"rca": "network-congestion", "impact": "10% delay"},
        "evidence": ["vm-1", "vm-2"],
    }
    obs = legacy_gcl_to_observation(gcl, "trc-p5-3")
    assert obs.trace_id == "trc-p5-3"
    assert obs.metadata["_from_legacy"] is True
    assert obs.metadata["gcl_run_id"] == "gcl-run-001"
    assert obs.metadata["gcl_generator"] == "Generator"
    assert obs.metadata["gcl_critic"] == "Critic"
    assert obs.metadata["gcl_iteration"] == 2
    assert obs.metadata["gcl_passed"] is True
    assert obs.metadata["gcl_rubric_version"] == "rca-v1"
    assert obs.metadata["gcl_model_version"] == "gpt-4o"
    assert obs.metadata["gcl_latency_ms"] == 1234


def test_legacy_audit_step_parses_to_span_observation():
    from copilot.trace_records import legacy_audit_to_observation

    audit = {
        "step_id": "cvm-1",
        "skill": "qcloud-cvm-ops",
        "operation": "DescribeInstances",
        "region": "ap-guangzhou",
        "status": "success",
        "duration_ms": 432,
        "timestamp": "2026-07-25T00:00:00Z",
    }
    obs = legacy_audit_to_observation(audit, "trc-p5-3")
    assert obs.trace_id == "trc-p5-3"
    assert obs.type.value == "SPAN"
    assert obs.metadata["_from_legacy"] is True
    assert obs.metadata["skill_name"] == "qcloud-cvm-ops"
    assert obs.metadata["operation_name"] == "DescribeInstances"
    assert obs.metadata["region"] == "ap-guangzhou"
    assert obs.metadata["step_id"] == "cvm-1"


def test_legacy_gcl_v0_record_legacy_missing_fields_defaults_safely():
    """A minimal legacy v0 GCL trace (no iteration / no rubric_version) must parse without error."""
    from copilot.trace_records import legacy_gcl_to_observation

    gcl = {
        "generator": "G",
        "timestamp": "2026-07-25T00:00:00Z",
        "passed": False,
    }
    obs = legacy_gcl_to_observation(gcl, "trc-x")
    assert obs.metadata["gcl_passed"] is False
    assert obs.metadata["gcl_iteration"] is None  # missing -> None, NOT ''/'unknown'


def test_legacy_audit_missing_optional_fields_yields_None_not_unknown():
    from copilot.trace_records import legacy_audit_to_observation

    audit = {"step_id": "s1", "status": "success"}
    obs = legacy_audit_to_observation(audit, "trc-x")
    assert obs.metadata["skill_name"] is None
    assert obs.metadata["operation_name"] is None
    assert obs.metadata["region"] is None


def test_legacy_records_set_observation_type_for_gcl_and_audit_distinctly():
    """GCL -> GENERATION (LLM-like output); Audit -> SPAN (skill execution)."""
    from copilot.trace_records import (
        legacy_gcl_to_observation,
        legacy_audit_to_observation,
    )
    gcl_obs = legacy_gcl_to_observation({"generator": "G", "timestamp": "2026-07-25T00:00:00Z", "passed": True}, "t")
    audit_obs = legacy_audit_to_observation({"step_id": "s", "status": "success"}, "t")
    assert gcl_obs.type.value == "GENERATION"
    assert audit_obs.type.value == "SPAN"


def test_legacy_round_trip_via_observ_query_returns_observation():
    """Old Copilot audit JSONL should be readable by observ_query for cross-version queries."""
    from copilot.observ_query import read_audit_records
    import json
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        run_dir = td_path / ".runtime" / "gcl" / "copilot" / "audit" / "ses-legacy"
        run_dir.mkdir(parents=True, exist_ok=True)
        audit_record = {
            "trace_id": "ses-legacy",
            "session_id": "ses-legacy",
            "step_id": "cvm-1",
            "skill": "qcloud-cvm-ops",
            "duration_ms": 200,
            "status": "success",
        }
        (run_dir / "step-cvm-1-20260725T000000.json").write_text(
            json.dumps(audit_record, ensure_ascii=False, indent=2)
        )
        with __import__("contextlib").redirect_stdout(__import__("io").StringIO()):
            recs = read_audit_records(run_id="ses-legacy", runtime_root=td_path)
        assert len(recs) == 1
        assert recs[0]["skill"] == "qcloud-cvm-ops"
        assert recs[0]["status"] == "success"
