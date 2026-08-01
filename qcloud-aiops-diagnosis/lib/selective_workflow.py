"""Selective workflow execution — skips analyzers for absent topology resources.

The cruise-sniff phase discovers which resource types are present in the
topology. This module uses that information to construct the minimal set of
analyzers that should run, skipping those whose prerequisites are absent.

Example:
    sw = SelectiveWorkflow(topology=graph)
    plan = sw.build_plan(metrics=["cpu_util", "mem_util"])
    # plan is a list of WorkflowStep: (name, enabled, reason, metadata)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lib.topology_discovery import NodeType, TopologyGraph

# Map: analyzer name → required resource types (ANY of these must be present)
ANALYZER_REQUIREMENTS: dict[str, list[NodeType]] = {
    "cvm_analyzer":    [NodeType.CVM],
    "clb_analyzer":    [NodeType.CLB],
    "vpc_analyzer":    [NodeType.VPC],
    "eni_analyzer":    [NodeType.ENI],
    "nat_analyzer":    [NodeType.NAT],
    "vpn_analyzer":    [NodeType.VPN],
    "cdn_analyzer":    [NodeType.CDN],
    "eip_analyzer":    [NodeType.EIP],
}

# Map: metric name → required resource types (ALL must be present)
METRIC_REQUIREMENTS: dict[str, list[NodeType]] = {
    "cpu_util":       [NodeType.CVM],
    "mem_util":       [NodeType.CVM],
    "disk_util":      [NodeType.CVM],
    "network_in":     [NodeType.CVM, NodeType.ENI],
    "network_out":    [NodeType.CVM, NodeType.ENI],
    "lb_qps":         [NodeType.CLB],
    "lb_latency":     [NodeType.CLB],
    "lb_cps":         [NodeType.CLB],
    "vpc_flow":       [NodeType.VPC],
    "nat_conn":       [NodeType.NAT],
    "cdn_bps":        [NodeType.CDN],
}


@dataclass
class WorkflowStep:
    """A single step in the selective diagnostic workflow.

    Fields:
        name: analyzer/step identifier
        enabled: whether this step should run
        reason: human-readable justification for enabled/disabled decision
        priority: lower values run earlier in the diagnostic chain
        metadata: additional context (e.g. which metrics triggered this step)
    """
    name: str
    enabled: bool
    reason: str
    priority: int = 10  # lower = runs first
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SelectiveWorkflow:
    """Selectively enable/disable diagnostic workflow steps based on topology."""

    topology: TopologyGraph
    _steps: list[WorkflowStep] = field(default_factory=list)

    def build_plan(
        self,
        metrics: list[str] | None = None,
        analyzers: list[str] | None = None,
    ) -> list[WorkflowStep]:
        """Build the selective execution plan.

        Args:
            metrics: List of metric names to check. None = use all defined.
            analyzers: List of analyzer names to consider. None = use all.

        Returns:
            List of WorkflowSteps with enabled/disabled decisions.
        """
        self._steps = []

        # Step 1: Always check if topology is empty
        if self.topology.is_empty():
            self._steps.append(WorkflowStep(
                name="topology_discovery",
                enabled=True,
                reason="topology discovery required before analysis",
                priority=0,
            ))
            return self._steps

        # Step 2: Add analyzer steps based on topology presence
        all_analyzers = set(ANALYZER_REQUIREMENTS.keys())
        target_analyzers = set(analyzers) if analyzers else all_analyzers

        for analyzer in sorted(target_analyzers):
            req_types = ANALYZER_REQUIREMENTS.get(analyzer, [])
            if not req_types:
                self._steps.append(WorkflowStep(
                    name=analyzer,
                    enabled=True,
                    reason="no topology requirements defined",
                    priority=10,
                ))
                continue

            present = [t for t in req_types if not self.topology.is_empty([t])]
            if present:
                self._steps.append(WorkflowStep(
                    name=analyzer,
                    enabled=True,
                    reason=f"required resources present: {[t.value for t in present]}",
                    priority=self._tier_priority(req_types),
                ))
            else:
                self._steps.append(WorkflowStep(
                    name=analyzer,
                    enabled=False,
                    reason=f"required resources absent: {[t.value for t in req_types]}",
                    priority=99,
                ))

        # Step 3: Add metric-level steps
        if metrics:
            for metric in metrics:
                req_types = METRIC_REQUIREMENTS.get(metric, [])
                if not req_types:
                    continue
                present = [t for t in req_types if not self.topology.is_empty([t])]
                if not present:
                    self._steps.append(WorkflowStep(
                        name=f"metric_{metric}",
                        enabled=False,
                        reason=f"no {metric} data: {[t.value for t in req_types]} resources absent",
                        priority=20,
                    ))

        # Sort by priority
        self._steps.sort(key=lambda s: s.priority)
        return self._steps

    def execute_plan(
        self,
        metrics: list[str] | None = None,
        analyzers: list[str] | None = None,
    ) -> list[WorkflowStep]:
        """Build and return the execution plan."""
        return self.build_plan(metrics=metrics, analyzers=analyzers)

    def get_enabled_analyzers(self) -> list[str]:
        """Return names of enabled analyzers."""
        return [s.name for s in self._steps if s.enabled]

    def get_disabled_analyzers(self) -> list[str]:
        """Return names of disabled analyzers."""
        return [s.name for s in self._steps if not s.enabled]

    def summary(self) -> dict[str, Any]:
        """Return a summary dict for reporting."""
        return {
            "total_steps": len(self._steps),
            "enabled": len(self.get_enabled_analyzers()),
            "disabled": len(self.get_disabled_analyzers()),
            "enabled_analyzers": self.get_enabled_analyzers(),
            "disabled_analyzers": self.get_disabled_analyzers(),
            "resource_counts": self.topology.node_count(),
        }

    @staticmethod
    def _tier_priority(types: list[NodeType]) -> int:
        """Map NodeTypes to workflow priority (tier order)."""
        tier_map = {NodeType.VPC: 1, NodeType.CVM: 2, NodeType.CLB: 3}
        return min((tier_map.get(t, 5) for t in types), default=10)
