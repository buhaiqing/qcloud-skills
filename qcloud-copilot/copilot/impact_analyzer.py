# Phase 2.4 — Predictive Safety Gate: ImpactAssessment + ImpactAnalyzer.
# Evaluates blast radius before destructive operations by querying resource
# dependency graphs (CLB listeners, attached disks, EIPs, security groups).
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = ["AffectedResource", "ImpactAnalyzer", "ImpactAssessment", "RiskLevel"]
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AffectedResource:
    """A resource连带affected by the target destructive operation."""

    resource_type: str  # "CLB" | "CDB" | "SecurityGroup" | "Disk" | "EIP"
    resource_id: str
    relationship: str  # "listener" | "readonly_replica" | "member" | "mounted" | "bound"
    impact: str  # human-readable impact description


@dataclass
class ImpactAssessment:
    """Result of blast-radius analysis for a destructive operation."""

    operation: str  # e.g. "TerminateInstances", "DeleteVpc"
    resource_ids: list[str]
    affected_resources: list[AffectedResource] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    blast_radius: int = 0
    recommendation: str = ""


# Operations that are always CRITICAL regardless of blast radius
_ALWAYS_CRITICAL = frozenset({
    "deletevpc",
    "deletedatabase",
    "deletedb",
    "terminat iam",
    "deleteaccount",
    "deleteiam",
    "deletepolicy",
    "deleterole",
})

# Operations that imply HIGH risk when combined with blast_radius >= 3
_HIGH_RISK_OPS = frozenset({
    "terminateinstances",
    "deletedisk",
    "deleteloadbalancers",
    "deletelistener",
    "deletebackend",
    "deletetargetgroup",
})

# Operations that imply MEDIUM risk when combined with blast_radius >= 1
_MEDIUM_RISK_OPS = frozenset({
    "stopinstances",
    "modifysg",
    "modifysgrules",
    "stopservers",
    "restartinstances",
})


class ImpactAnalyzer:
    """Queries resource dependency graphs to assess blast radius.

    Currently hardcoded for CVM TerminateInstances analysis.
    Extensible: add per-product query methods as skill coverage expands.
    """

    def assess(self, operation: str, resource_ids: list[str]) -> ImpactAssessment:
        """Analyze blast radius for operation on resource_ids.

        Returns ImpactAssessment with affected_resources, risk_level, blast_radius,
        and action-specific recommendation.
        """
        op_lower = operation.lower().replace("_", "").replace("-", "").replace(" ", "")
        assessment = ImpactAssessment(operation=operation, resource_ids=resource_ids)

        if not resource_ids:
            assessment.risk_level = RiskLevel.LOW
            assessment.recommendation = "No resources specified — no impact."
            return assessment

        # Always-critical operations bypass blast-radius checks
        if op_lower in _ALWAYS_CRITICAL:
            assessment.risk_level = RiskLevel.CRITICAL
            assessment.recommendation = "CRITICAL operation — human approval mandatory with full impact report."
            return assessment

        # Read-only operations are always LOW
        if self._is_read_only(operation):
            assessment.risk_level = RiskLevel.LOW
            assessment.recommendation = "Read-only operation — no impact anticipated."
            return assessment

        # CVM-specific dependency analysis
        if self._is_cvm_destructive(operation):
            self._analyze_cvm_dependencies(assessment)

        # Determine risk level from blast radius + operation class
        self._assign_risk_level(assessment, op_lower)

        # Generate recommendation if not already set
        if not assessment.recommendation:
            assessment.recommendation = self._build_recommendation(assessment)

        return assessment

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_read_only(operation: str) -> bool:
        """Heuristic: operations starting with Get/Describe/Inspect/Query are read-only."""
        read_prefixes = ("get", "describe", "inspect", "query", "list", "search", "lookup")
        return operation.lower().startswith(read_prefixes)

    @staticmethod
    def _is_cvm_destructive(operation: str) -> bool:
        """Returns True for CVM destructive operations that have dependency side-effects."""
        cvm_destructive = (
            "terminate",
            "stop",
            "restart",
            "reboot",
            "reset",
            "modify",
            "delete",
            "release",
            "deregister",
            "unbind",
            "detach",
        )
        op_lower = operation.lower()
        return any(kw in op_lower for kw in cvm_destructive)

    def _analyze_cvm_dependencies(self, assessment: ImpactAssessment) -> None:
        """Query mock dependency graph for CVM resources.

        In production this would call tccli cvm DescribeInstances /
        clb DescribeClassicalLBTargets / cbs DescribeDisks / vpc DescribeAddresses.
        Here we stub the query interface so the logic path is testable.
        """
        for resource_id in assessment.resource_ids:
            # --- CLB listeners where this instance is a backend ---
            clb_backends = self._query_clb_backends(resource_id)
            for listener_id, listener_name in clb_backends:
                assessment.affected_resources.append(
                    AffectedResource(
                        resource_type="CLB",
                        resource_id=listener_id,
                        relationship="listener_backend",
                        impact=f"CLB listener {listener_name} ({listener_id}) will lose backend {resource_id}",
                    )
                )

            # --- Data disks that are mounted to this instance ---
            attached_disks = self._query_attached_disks(resource_id)
            for disk_id, disk_name in attached_disks:
                assessment.affected_resources.append(
                    AffectedResource(
                        resource_type="Disk",
                        resource_id=disk_id,
                        relationship="mounted",
                        impact=f"Data disk {disk_name} ({disk_id}) will be released — data loss risk",
                    )
                )

            # --- Elastic IPs bound to this instance ---
            bound_eips = self._query_bound_eips(resource_id)
            for eip_id, eip_addr in bound_eips:
                assessment.affected_resources.append(
                    AffectedResource(
                        resource_type="EIP",
                        resource_id=eip_id,
                        relationship="bound",
                        impact=f"EIP {eip_addr} ({eip_id}) will be disassociated",
                    )
                )

            # --- Security groups that contain this instance as a member ---
            member_sgs = self._query_security_groups(resource_id)
            for sg_id, sg_name in member_sgs:
                assessment.affected_resources.append(
                    AffectedResource(
                        resource_type="SecurityGroup",
                        resource_id=sg_id,
                        relationship="member",
                        impact=f"Security group {sg_name} ({sg_id}) will lose member {resource_id}",
                    )
                )

        assessment.blast_radius = len(assessment.affected_resources)

    # ------------------------------------------------------------------
    # Query stubs — replace with real tccli calls in production
    # ------------------------------------------------------------------

    def _query_clb_backends(self, instance_id: str) -> list[tuple[str, str]]:
        """Return (listener_id, listener_name) pairs where instance_id is a CLB backend."""
        return []

    def _query_attached_disks(self, instance_id: str) -> list[tuple[str, str]]:
        """Return (disk_id, disk_name) pairs for disks mounted to instance_id."""
        return []

    def _query_bound_eips(self, instance_id: str) -> list[tuple[str, str]]:
        """Return (eip_id, eip_address) pairs bound to instance_id."""
        return []

    def _query_security_groups(self, instance_id: str) -> list[tuple[str, str]]:
        """Return (sg_id, sg_name) pairs where instance_id is a member."""
        return []

    # ------------------------------------------------------------------
    # Risk-level assignment
    # ------------------------------------------------------------------

    @staticmethod
    def _assign_risk_level(assessment: ImpactAssessment, op_lower: str) -> None:
        """Derive risk_level from blast_radius and operation class."""
        blast = assessment.blast_radius

        if op_lower in _ALWAYS_CRITICAL or blast >= 5:
            assessment.risk_level = RiskLevel.CRITICAL
        elif blast >= 3 or op_lower in _HIGH_RISK_OPS:
            assessment.risk_level = RiskLevel.HIGH
        elif blast >= 1 or op_lower in _MEDIUM_RISK_OPS:
            assessment.risk_level = RiskLevel.MEDIUM
        else:
            assessment.risk_level = RiskLevel.LOW

    @staticmethod
    def _build_recommendation(assessment: ImpactAssessment) -> str:
        """Generate Chinese-language recommendation based on affected resource types."""
        types = {r.resource_type for r in assessment.affected_resources}
        ops_lower = assessment.operation.lower()

        if not types:
            return "No affected resources detected — proceed with caution."

        parts: list[str] = []

        if "CLB" in types:
            parts.append("先解绑 CLB 后端")
        if "EIP" in types:
            parts.append("再解绑 EIP")
        if "Disk" in types:
            parts.append("再卸载磁盘（数据备份确认）")
        if "SecurityGroup" in types:
            parts.append("从安全组移除该实例")
        if "CDB" in types:
            parts.append("断开数据库只读副本")

        if parts:
            base = " → ".join(parts)
            if "terminate" in ops_lower or "delete" in ops_lower:
                return f"{base}，最后执行删除操作"
            return base

        return "操作前请确认所有关联资源已妥善处理"
