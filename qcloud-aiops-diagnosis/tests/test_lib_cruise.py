"""Unit tests for lib/ modules — fingerprint, filters, cruise_logger, selective_workflow."""

import json
import os
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.finding_fingerprint import FindingFingerprint, FingerprintRegistry
from lib.finding_filters import FindingFilterSet, finops_cost_filter, reliability_filter
from lib.cruise_logger import CruiseLogger, Phase
from lib.selective_workflow import SelectiveWorkflow
from lib.topology_discovery import TopologyGraph, TopologyNode, NodeType


class TestFindingFingerprint(unittest.TestCase):

    def test_same_params_same_key(self):
        fp1 = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        fp2 = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        self.assertEqual(fp1.key, fp2.key)

    def test_different_resource_different_key(self):
        fp1 = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        fp2 = FindingFingerprint(metric="cpu_util", resource_id="ins-yyy", direction="upper")
        self.assertNotEqual(fp1.key, fp2.key)

    def test_different_metric_different_key(self):
        fp1 = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        fp2 = FindingFingerprint(metric="mem_util", resource_id="ins-xxx", direction="upper")
        self.assertNotEqual(fp1.key, fp2.key)

    def test_key_contains_metric_and_resource(self):
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        self.assertIn("cpu_util", fp.key)
        self.assertIn("ins-xxx", fp.key)

    def test_key_is_string(self):
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        self.assertIsInstance(fp.key, str)
        self.assertTrue(len(fp.key) > 0)


class TestFingerprintRegistry(unittest.TestCase):

    def test_register_new_returns_true(self):
        reg = FingerprintRegistry()
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        self.assertTrue(reg.register(fp, "CPU high"))

    def test_register_duplicate_returns_false(self):
        reg = FingerprintRegistry()
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        reg.register(fp, "CPU high")
        self.assertFalse(reg.register(fp, "CPU high again"))

    def test_register_increments_count(self):
        reg = FingerprintRegistry()
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        reg.register(fp, "CPU high")
        reg.register(fp, "CPU high again")
        self.assertEqual(reg.fingerprints[fp.key]["count"], 2)

    def test_summary_returns_total_and_unique(self):
        reg = FingerprintRegistry()
        fp = FindingFingerprint(metric="cpu_util", resource_id="ins-xxx", direction="upper")
        reg.register(fp, "CPU high", severity="warning")
        s = reg.summary()
        self.assertIn("total_findings", s)
        self.assertIn("unique_findings", s)
        self.assertEqual(s["unique_findings"], 1)


class TestFindingFilters(unittest.TestCase):

    def test_filter_set_passes_non_matching(self):
        fs = FindingFilterSet(name="test")
        kept, excluded = fs.apply([{"resource_id": "i-1", "message": "CPU 95%"}])
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(excluded), 0)

    def test_filter_set_excludes_matching(self):
        fs = FindingFilterSet(name="test")
        fs.add_rule(name="enc", field="message", op="contains", value="未加密")
        kept, excluded = fs.apply([{"resource_id": "i-1", "message": "数据盘 未加密"}])
        self.assertEqual(len(kept), 0)
        self.assertEqual(len(excluded), 1)

    def test_finops_cost_filter_returns_filter_set(self):
        fset = finops_cost_filter()
        self.assertIsInstance(fset, FindingFilterSet)
        kept, excluded = fset.apply([{"resource_id": "i-1", "severity": "warning"}])
        self.assertIsInstance(kept, list)
        self.assertIsInstance(excluded, list)

    def test_reliability_filter_returns_filter_set(self):
        fset = reliability_filter()
        self.assertIsInstance(fset, FindingFilterSet)

    def test_apply_and_annotate(self):
        fs = FindingFilterSet(name="test")
        annotated = fs.apply_and_annotate([{"resource_id": "i-1", "severity": "warning"}])
        self.assertIsInstance(annotated, list)


class TestCruiseLogger(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self._tmp.close()
        self.path = self._tmp.name

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_start_end_phase(self):
        logger = CruiseLogger(cruise_id="test-001", region="ap-guangzhou")
        logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.end_phase(Phase.TOPOLOGY_DISCOVERY, data={"nodes": 12})
        logger.save(path=self.path)
        with open(self.path) as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        events = [e for e in lines if e.get("phase") not in ("__root__", None)]
        self.assertGreaterEqual(len([e for e in events if e["event_type"] == "start"]), 1)
        self.assertGreaterEqual(len([e for e in events if e["event_type"] == "complete"]), 1)

    def test_skip_step(self):
        logger = CruiseLogger(cruise_id="test-skip-001", region="ap-guangzhou")
        logger.start_phase(Phase.SELECTIVE_WORKFLOW)
        logger.skip_step("clb_analyzer", reason="no CLB in topology")
        logger.end_phase(Phase.SELECTIVE_WORKFLOW)
        logger.save(path=self.path)
        with open(self.path) as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        skips = [e for e in lines if e.get("event_type") == "skip"]
        self.assertEqual(len(skips), 1)
        self.assertEqual(skips[0]["data"]["reason"], "no CLB in topology")

    def test_log_decision(self):
        logger = CruiseLogger(cruise_id="test-decision-001", region="ap-guangzhou")
        logger.start_phase(Phase.SELECTIVE_WORKFLOW)
        logger.log_decision("run_cvm_analyzer", "CVM nodes found",
                            options=["run", "skip"], chosen="run")
        logger.end_phase(Phase.SELECTIVE_WORKFLOW)
        logger.save(path=self.path)
        with open(self.path) as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        decisions = [e for e in lines if e.get("event_type") == "decision"]
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["data"]["chosen"], "run")

    def test_emit_finding(self):
        logger = CruiseLogger(cruise_id="test-finding-001", region="ap-guangzhou")
        logger.start_phase(Phase.ML_DETECTION)
        logger.emit_finding({"resource_id": "ins-123", "anomaly": True})
        logger.end_phase(Phase.ML_DETECTION)
        logger.save(path=self.path)
        with open(self.path) as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        findings = [e for e in lines if e.get("event_type") == "finding"]
        self.assertEqual(len(findings), 1)
        self.assertIn("ins-123", str(findings[0]))

    def test_to_training_pairs(self):
        logger = CruiseLogger(cruise_id="test-tpairs-001", region="ap-guangzhou")
        logger.start_phase(Phase.SELECTIVE_WORKFLOW)
        logger.log_decision("run_cvm_analyzer", "CVM nodes found",
                            options=["run", "skip"], chosen="run")
        logger.end_phase(Phase.SELECTIVE_WORKFLOW)
        pairs = logger.to_training_pairs()
        self.assertGreaterEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["output"]["chosen"], "run")

    def test_phase_summary(self):
        logger = CruiseLogger(cruise_id="test-summary-001", region="ap-guangzhou")
        logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.end_phase(Phase.TOPOLOGY_DISCOVERY, data={"nodes": 5})
        summary = logger.phase_summary()
        self.assertIn("topology_discovery", summary)
        self.assertGreater(summary["topology_discovery"]["count"], 0)

    def test_context_manager_saves_file(self):
        import glob
        with CruiseLogger(cruise_id="test-cm-001", region="ap-guangzhou") as lg:
            lg.start_phase(Phase.CAPACITY_FORECAST)
            lg.end_phase(Phase.CAPACITY_FORECAST)
        matches = glob.glob(".runtime/cruise/test-cm-001-*.jsonl")
        self.assertGreater(len(matches), 0)
        for m in matches:
            os.unlink(m)
    def test_log_error(self):
        logger = CruiseLogger(cruise_id="test-error-001", region="ap-guangzhou")
        logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.log_error("tccli_cvm", "SecretIdNotFound", recoverable=True)
        logger.end_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.save(path=self.path)
        with open(self.path) as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        errors = [e for e in lines if e.get("event_type") == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("SecretIdNotFound", errors[0].get("error", ""))

    def test_jsonl_header_footer(self):
        logger = CruiseLogger(cruise_id="test-hf-001", region="ap-guangzhou")
        logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.end_phase(Phase.TOPOLOGY_DISCOVERY)
        logger.save(path=self.path)
        with open(self.path) as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        self.assertEqual(lines[0]["type"], "cruise_audit_header")
        self.assertEqual(lines[-1]["type"], "cruise_audit_footer")


class TestSelectiveWorkflow(unittest.TestCase):

    def test_empty_topology_builds_plan(self):
        tg = TopologyGraph()
        sw = SelectiveWorkflow(topology=tg)
        plan = sw.build_plan(metrics=["cpu_util"])
        self.assertIsInstance(plan, list)

    def test_topology_with_cvm_builds_plan(self):
        tg = TopologyGraph()
        tg.add_node(TopologyNode(
            id="vm-xxx", type=NodeType.CVM,
            region="ap-guangzhou", name="vm-xxx", status="running",
            metadata={},
        ))
        sw = SelectiveWorkflow(topology=tg)
        plan = sw.build_plan(metrics=["cpu_util"])
        self.assertIsInstance(plan, list)
        self.assertGreater(len(plan), 0)

    def test_workflow_steps_have_required_fields(self):
        tg = TopologyGraph()
        sw = SelectiveWorkflow(topology=tg)
        plan = sw.build_plan(metrics=["cpu_util"])
        for step in plan:
            self.assertTrue(hasattr(step, "enabled"))
            self.assertTrue(hasattr(step, "name"))
            self.assertTrue(hasattr(step, "reason"))


if __name__ == "__main__":
    unittest.main()
