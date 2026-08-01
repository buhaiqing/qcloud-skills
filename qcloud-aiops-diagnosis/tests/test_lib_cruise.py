# Copyright (c) 2026. All rights reserved.
"""Unit tests for lib/ modules — fingerprint, filters, cruise_logger, selective_workflow."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import contextlib

from lib.cruise_logger import CruiseLogger, Phase
from lib.finding_filters import FindingFilterSet, finops_cost_filter, reliability_filter
from lib.finding_fingerprint import FindingFingerprint, FingerprintRegistry
from lib.selective_workflow import SelectiveWorkflow
from lib.topology_discovery import NodeType, TopologyGraph, TopologyNode


class TestFindingFingerprint(unittest.TestCase):
    """Tests for FindingFingerprint deduplication key generation."""

    def test_same_params_same_key(self) -> None:
        """Verify identical fingerprints produce the same key."""
        fp1 = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        fp2 = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        assert fp1.key == fp2.key

    def test_different_resource_different_key(self) -> None:
        """Verify different resource IDs produce different keys."""
        fp1 = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        fp2 = FindingFingerprint(metric="cpu_util", resource_id="ins-yyy", direction="upper")
        assert fp1.key != fp2.key

    def test_different_metric_different_key(self) -> None:
        """Verify different metrics produce different keys."""
        fp1 = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        fp2 = FindingFingerprint(metric="mem_util", resource_id="ins-xxx", direction="upper")
        assert fp1.key != fp2.key

    def test_key_contains_metric_and_resource(self) -> None:
        """Verify the key string contains metric and resource ID."""
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        assert "cpu_util" in fp.key
        assert "ins-xxx" in fp.key

    def test_key_is_string(self) -> None:
        """Verify the key is a non-empty string."""
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        assert isinstance(fp.key, str)
        assert len(fp.key) > 0


class TestFingerprintRegistry(unittest.TestCase):
    """Tests for FingerprintRegistry deduplication tracking."""

    def test_register_new_returns_true(self) -> None:
        """Verify registering a new fingerprint returns True."""
        reg = FingerprintRegistry()
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        assert reg.register(fp, "CPU high")

    def test_register_duplicate_returns_false(self) -> None:
        """Verify registering a duplicate fingerprint returns False."""
        reg = FingerprintRegistry()
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        reg.register(fp, "CPU high")
        assert not reg.register(fp, "CPU high again")

    def test_register_increments_count(self) -> None:
        """Verify duplicate registration increments the count."""
        reg = FingerprintRegistry()
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        reg.register(fp, "CPU high")
        reg.register(fp, "CPU high again")
        assert reg.fingerprints[fp.key]["count"] == 2

    def test_summary_returns_total_and_unique(self) -> None:
        """Verify summary returns total_findings and unique_findings."""
        reg = FingerprintRegistry()
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        reg.register(fp, "CPU high", severity="warning")
        s = reg.summary()
        assert "total_findings" in s
        assert "unique_findings" in s
        assert s["unique_findings"] == 1


class TestFindingFilters(unittest.TestCase):
    """Tests for FindingFilterSet suppression and annotation."""

    def test_filter_set_passes_non_matching(self) -> None:
        """Verify non-matching findings are kept."""
        fs = FindingFilterSet(name="test")
        kept, excluded = fs.apply([{"resource_id": "i-1", "message": "CPU 95%"}])
        assert len(kept) == 1
        assert len(excluded) == 0

    def test_filter_set_excludes_matching(self) -> None:
        """Verify matching findings are excluded."""
        fs = FindingFilterSet(name="test")
        fs.add_rule(name="enc", field="message", op="contains", value="未加密")
        kept, excluded = fs.apply([{"resource_id": "i-1", "message": "数据盘 未加密"}])
        assert len(kept) == 0
        assert len(excluded) == 1

    def test_finops_cost_filter_returns_filter_set(self) -> None:
        """Verify finops_cost_filter returns a FindingFilterSet."""
        fset = finops_cost_filter()
        assert isinstance(fset, FindingFilterSet)
        kept, excluded = fset.apply([{"resource_id": "i-1", "severity": "warning"}])
        assert isinstance(kept, list)
        assert isinstance(excluded, list)

    def test_reliability_filter_returns_filter_set(self) -> None:
        """Verify reliability_filter returns a FindingFilterSet."""
        fset = reliability_filter()
        assert isinstance(fset, FindingFilterSet)

    def test_apply_and_annotate(self) -> None:
        """Verify apply_and_annotate returns a list."""
        fs = FindingFilterSet(name="test")
        annotated = fs.apply_and_annotate([{"resource_id": "i-1", "severity": "warning"}])
        assert isinstance(annotated, list)


class TestCruiseLogger(unittest.TestCase):
    """Tests for CruiseLogger structured event logging."""

    def setUp(self) -> None:
        """Create a temporary JSONL file for testing."""
        self._tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self._tmp.close()
        self.path = self._tmp.name

    def tearDown(self) -> None:
        """Remove the temporary JSONL file."""
        with contextlib.suppress(OSError):
            Path(self.path).unlink()

    def test_start_end_phase(self) -> None:
        """Verify phase start and end events are logged."""
        logger = CruiseLogger(cruise_id="test-001", region="ap-guangzhou")
        logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.end_phase(Phase.TOPOLOGY_DISCOVERY, data={"nodes": 12})
        logger.save(path=self.path)
        with Path(self.path).open() as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        events = [e for e in lines if e.get("phase") not in ("__root__", None)]
        assert len([e for e in events if e["event_type"] == "start"]) >= 1
        assert len([e for e in events if e["event_type"] == "complete"]) >= 1

    def test_skip_step(self) -> None:
        """Verify skip_step logs a skip event with reason."""
        logger = CruiseLogger(cruise_id="test-skip-001", region="ap-guangzhou")
        logger.start_phase(Phase.SELECTIVE_WORKFLOW)
        logger.skip_step("clb_analyzer", reason="no CLB in topology")
        logger.end_phase(Phase.SELECTIVE_WORKFLOW)
        logger.save(path=self.path)
        with Path(self.path).open() as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        skips = [e for e in lines if e.get("event_type") == "skip"]
        assert len(skips) == 1
        assert skips[0]["data"]["reason"] == "no CLB in topology"

    def test_log_decision(self) -> None:
        """Verify log_decision logs a decision event."""
        logger = CruiseLogger(cruise_id="test-decision-001", region="ap-guangzhou")
        logger.start_phase(Phase.SELECTIVE_WORKFLOW)
        logger.log_decision("run_cvm_analyzer", "CVM nodes found",
                            options=["run", "skip"], chosen="run")
        logger.end_phase(Phase.SELECTIVE_WORKFLOW)
        logger.save(path=self.path)
        with Path(self.path).open() as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        decisions = [e for e in lines if e.get("event_type") == "decision"]
        assert len(decisions) == 1
        assert decisions[0]["data"]["chosen"] == "run"

    def test_emit_finding(self) -> None:
        """Verify emit_finding logs a finding event."""
        logger = CruiseLogger(cruise_id="test-finding-001", region="ap-guangzhou")
        logger.start_phase(Phase.ML_DETECTION)
        logger.emit_finding({"resource_id": "ins-123", "anomaly": True})
        logger.end_phase(Phase.ML_DETECTION)
        logger.save(path=self.path)
        with Path(self.path).open() as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        findings = [e for e in lines if e.get("event_type") == "finding"]
        assert len(findings) == 1
        assert "ins-123" in str(findings[0])

    def test_to_training_pairs(self) -> None:
        """Verify to_training_pairs generates (context, decision) pairs."""
        logger = CruiseLogger(cruise_id="test-tpairs-001", region="ap-guangzhou")
        logger.start_phase(Phase.SELECTIVE_WORKFLOW)
        logger.log_decision("run_cvm_analyzer", "CVM nodes found",
                            options=["run", "skip"], chosen="run")
        logger.end_phase(Phase.SELECTIVE_WORKFLOW)
        pairs = logger.to_training_pairs()
        assert len(pairs) >= 1
        assert pairs[0]["output"]["chosen"] == "run"

    def test_phase_summary(self) -> None:
        """Verify phase_summary aggregates events by phase."""
        logger = CruiseLogger(cruise_id="test-summary-001", region="ap-guangzhou")
        logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.end_phase(Phase.TOPOLOGY_DISCOVERY, data={"nodes": 5})
        summary = logger.phase_summary()
        assert "topology_discovery" in summary
        assert summary["topology_discovery"]["count"] > 0

    def test_context_manager_saves_file(self) -> None:
        """Verify context manager saves the JSONL file on exit."""
        from pathlib import Path
        with CruiseLogger(cruise_id="test-cm-001", region="ap-guangzhou") as lg:
            lg.start_phase(Phase.CAPACITY_FORECAST)
            lg.end_phase(Phase.CAPACITY_FORECAST)
        matches = list(Path(".runtime/cruise").glob("test-cm-001-*.jsonl"))
        assert len(matches) > 0
        for m in matches:
            Path(m).unlink()
    def test_log_error(self) -> None:
        """Verify log_error logs an error event."""
        logger = CruiseLogger(cruise_id="test-error-001", region="ap-guangzhou")
        logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.log_error("tccli_cvm", "SecretIdNotFound", recoverable=True)
        logger.end_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.save(path=self.path)
        with Path(self.path).open() as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        errors = [e for e in lines if e.get("event_type") == "error"]
        assert len(errors) == 1
        assert "SecretIdNotFound" in errors[0].get("error", "")

    def test_jsonl_header_footer(self) -> None:
        """Verify the JSONL output has header and footer lines."""
        logger = CruiseLogger(cruise_id="test-hf-001", region="ap-guangzhou")
        logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.end_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.save(path=self.path)
        with Path(self.path).open() as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        assert lines[0]["type"] == "cruise_audit_header"
        assert lines[-1]["type"] == "cruise_audit_footer"


class TestSelectiveWorkflow(unittest.TestCase):
    """Tests for SelectiveWorkflow topology-driven plan building."""

    def test_empty_topology_builds_plan(self) -> None:
        """Verify empty topology still builds a plan."""
        tg = TopologyGraph()
        sw = SelectiveWorkflow(topology=tg)
        plan = sw.build_plan(metrics=["cpu_util"])
        assert isinstance(plan, list)

    def test_topology_with_cvm_builds_plan(self) -> None:
        """Verify topology with CVM nodes builds a plan."""
        tg = TopologyGraph()
        tg.add_node(TopologyNode(
            id="vm-xxx", type=NodeType.CVM,
            region="ap-guangzhou", name="vm-xxx", status="running",
            metadata={},
        ))
        sw = SelectiveWorkflow(topology=tg)
        plan = sw.build_plan(metrics=["cpu_util"])
        assert isinstance(plan, list)
        assert len(plan) > 0

    def test_workflow_steps_have_required_fields(self) -> None:
        """Verify each workflow step has enabled, name, and reason attributes."""
        tg = TopologyGraph()
        sw = SelectiveWorkflow(topology=tg)
        plan = sw.build_plan(metrics=["cpu_util"])
        for step in plan:
            assert hasattr(step, "enabled")
            assert hasattr(step, "name")
            assert hasattr(step, "reason")


if __name__ == "__main__":
    unittest.main()
