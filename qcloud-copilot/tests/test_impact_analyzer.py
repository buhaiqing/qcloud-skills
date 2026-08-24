"""Tests for impact_analyzer.py (Phase 2.4)."""
from __future__ import annotations

import unittest

from copilot.impact_analyzer import (
    AffectedResource,
    ImpactAnalyzer,
    RiskLevel,
)


class TestImpactAnalyzer(unittest.TestCase):
    """Test suite for ImpactAnalyzer.assess()."""

    @staticmethod
    def _make_analyzer(
        clb_backends: dict[str, list[tuple[str, str]]] | None = None,
        attached_disks: dict[str, list[tuple[str, str]]] | None = None,
        bound_eips: dict[str, list[tuple[str, str]]] | None = None,
        member_sgs: dict[str, list[tuple[str, str]]] | None = None,
    ) -> ImpactAnalyzer:
        """Return an ImpactAnalyzer whose stub methods return the given data."""
        analyzer = ImpactAnalyzer()
        analyzer._query_clb_backends = lambda iid: (clb_backends or {}).get(iid, [])  # type: ignore[method-assign]
        analyzer._query_attached_disks = lambda iid: (attached_disks or {}).get(iid, [])  # type: ignore[method-assign]
        analyzer._query_bound_eips = lambda iid: (bound_eips or {}).get(iid, [])  # type: ignore[method-assign]
        analyzer._query_security_groups = lambda iid: (member_sgs or {}).get(iid, [])  # type: ignore[method-assign]
        return analyzer

    def test_cvm_terminate_with_affected_clb_and_disks(self) -> None:
        """CVM termination with CLB backends + mounted disks → HIGH risk."""
        analyzer = self._make_analyzer(
            clb_backends={"ins-xxx": [("lb-abc", "listener-http"), ("lb-def", "listener-https")]},
            attached_disks={"ins-xxx": [("disk-1", "data-disk-a"), ("disk-2", "data-disk-b")]},
            bound_eips={"ins-xxx": [("eip-xxx", "1.2.3.4")]},
            member_sgs={"ins-xxx": [("sg-abc", "web-sg")]},
        )
        result = analyzer.assess("TerminateInstances", ["ins-xxx"])

        # 6 affected: 2 CLB + 2 Disk + 1 EIP + 1 SG → CRITICAL (blast_radius >= 5)
        self.assertEqual(result.blast_radius, 6)
        self.assertEqual(result.risk_level, RiskLevel.CRITICAL)
        self.assertIn("CLB", {r.resource_type for r in result.affected_resources})
        self.assertIn("Disk", {r.resource_type for r in result.affected_resources})
        self.assertIn("EIP", {r.resource_type for r in result.affected_resources})
        self.assertIn("SecurityGroup", {r.resource_type for r in result.affected_resources})
        self.assertIn("先解绑", result.recommendation)

    def test_delete_vpc_is_critical(self) -> None:
        """DeleteVpc is always CRITICAL regardless of blast radius."""
        analyzer = self._make_analyzer()
        result = analyzer.assess("DeleteVpc", ["vpc-xxx"])
        self.assertEqual(result.risk_level, RiskLevel.CRITICAL)
        self.assertEqual(result.blast_radius, 0)
        self.assertIn("CRITICAL", result.recommendation)

    def test_delete_vpc_lowercase_is_critical(self) -> None:
        """DeleteVpc variants (lowercase / underscore) are also CRITICAL."""
        analyzer = self._make_analyzer()
        for op in ("deletevpc", "delete_vpc", "Delete_VPC", "DeleteVPC"):
            result = analyzer.assess(op, ["vpc-xxx"])
            self.assertEqual(result.risk_level, RiskLevel.CRITICAL, f"failed for {op}")

    def test_read_only_is_low_risk(self) -> None:
        """GetInstances / DescribeInstances are LOW risk regardless of resource."""
        analyzer = self._make_analyzer(
            clb_backends={"ins-xxx": [("lb-abc", "listener-http")]},
        )
        result = analyzer.assess("DescribeInstances", ["ins-xxx"])
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(result.blast_radius, 0)
        self.assertIn("Read-only", result.recommendation)

    def test_high_blast_radius_critical(self) -> None:
        """blast_radius >= 5 triggers CRITICAL even for non-always-critical ops."""
        analyzer = self._make_analyzer(
            clb_backends={
                "ins-1": [("lb-1", "l1")],
                "ins-2": [("lb-2", "l2")],
                "ins-3": [("lb-3", "l3")],
                "ins-4": [("lb-4", "l4")],
                "ins-5": [("lb-5", "l5")],
            },
            attached_disks={"ins-1": [("d1", "disk1")]},
            bound_eips={"ins-1": [("eip1", "1.1.1.1")]},
            member_sgs={"ins-1": [("sg1", "sg")]},
        )
        result = analyzer.assess("TerminateInstances", ["ins-1", "ins-2", "ins-3", "ins-4", "ins-5"])
        self.assertGreaterEqual(result.blast_radius, 5)
        self.assertEqual(result.risk_level, RiskLevel.CRITICAL)

    def test_medium_blast_radius_high(self) -> None:
        """blast_radius 3-4 triggers HIGH for TerminateInstances."""
        analyzer = self._make_analyzer(
            clb_backends={"ins-xxx": [("lb-1", "l1"), ("lb-2", "l2")]},
            attached_disks={"ins-xxx": [("disk-1", "data-disk")]},
        )
        result = analyzer.assess("TerminateInstances", ["ins-xxx"])
        self.assertEqual(result.blast_radius, 3)
        self.assertEqual(result.risk_level, RiskLevel.HIGH)

    def test_empty_resource_ids_low(self) -> None:
        """No resource_ids → LOW risk."""
        analyzer = self._make_analyzer()
        result = analyzer.assess("TerminateInstances", [])
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(result.blast_radius, 0)

    def test_stop_instances_medium(self) -> None:
        """StopInstances is MEDIUM risk even with no blast radius."""
        analyzer = self._make_analyzer()
        result = analyzer.assess("StopInstances", ["ins-xxx"])
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)

    def test_impact_assessment_contains_all_fields(self) -> None:
        """ImpactAssessment has all required fields."""
        analyzer = self._make_analyzer()
        result = analyzer.assess("DeleteDatabase", ["db-xxx"])
        self.assertIsInstance(result.operation, str)
        self.assertIsInstance(result.resource_ids, list)
        self.assertIsInstance(result.affected_resources, list)
        self.assertIsInstance(result.risk_level, RiskLevel)
        self.assertIsInstance(result.blast_radius, int)
        self.assertIsInstance(result.recommendation, str)

    def test_affected_resource_fields(self) -> None:
        """AffectedResource dataclass has expected fields."""
        ar = AffectedResource(
            resource_type="CLB",
            resource_id="lb-abc",
            relationship="listener_backend",
            impact="CLB listener will lose backend",
        )
        self.assertEqual(ar.resource_type, "CLB")
        self.assertEqual(ar.resource_id, "lb-abc")
        self.assertEqual(ar.relationship, "listener_backend")
        self.assertEqual(ar.impact, "CLB listener will lose backend")

    def test_risk_level_enum_values(self) -> None:
        """RiskLevel enum has expected string values."""
        self.assertEqual(RiskLevel.LOW.value, "low")
        self.assertEqual(RiskLevel.MEDIUM.value, "medium")
        self.assertEqual(RiskLevel.HIGH.value, "high")
        self.assertEqual(RiskLevel.CRITICAL.value, "critical")

    def test_multiple_resource_ids_aggregates_blast_radius(self) -> None:
        """Multiple resource_ids sum their affected resources."""
        analyzer = self._make_analyzer(
            clb_backends={
                "ins-1": [("lb-1", "l1")],
                "ins-2": [("lb-2", "l2")],
            },
            attached_disks={
                "ins-1": [("disk-1", "d1")],
                "ins-2": [("disk-2", "d2")],
            },
        )
        result = analyzer.assess("TerminateInstances", ["ins-1", "ins-2"])
        # 1 CLB + 1 disk for ins-1 + 1 CLB + 1 disk for ins-2 = 4
        self.assertEqual(result.blast_radius, 4)
        self.assertEqual(result.risk_level, RiskLevel.HIGH)


if __name__ == "__main__":
    unittest.main()
