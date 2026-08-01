"""Topology discovery for Tencent Cloud using tccli.

Discovers CVM, CLB, VPC, and peering relationships and builds a
topology graph for selective_analyzer execution.

Usage:
    discover = TopologyDiscovery(region="ap-guangzhou")
    graph = discover.discover_all()          # full topology
    graph = discover.discover_services(["cvm", "clb"])  # selected services
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


class NodeType(str, Enum):
    CVM = "cvm"
    CLB = "clb"
    VPC = "vpc"
    VPC_PEERING = "vpc_peering"
    ENI = "eni"  # Elastic Network Interface
    CDN = "cdn"
    EIP = "eip"
    NAT = "nat"
    VPN = "vpn"
    UNKNOWN = "unknown"


@dataclass
class TopologyNode:
    id: str
    type: NodeType
    region: str
    name: str = ""
    status: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "region": self.region,
            "name": self.name,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class TopologyEdge:
    source: str
    target: str
    rel: str  # e.g. "binds_to", "peers_with", "routes_to"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "rel": self.rel,
            "metadata": self.metadata,
        }


@dataclass
class TopologyGraph:
    nodes: list[TopologyNode] = field(default_factory=list)
    edges: list[TopologyEdge] = field(default_factory=list)

    def add_node(self, node: TopologyNode) -> None:
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: TopologyEdge) -> None:
        self.add_node(self._node_by_id(edge.source))
        self.add_node(self._node_by_id(edge.target))
        if not any(
            e.source == edge.source and e.target == edge.target for e in self.edges
        ):
            self.edges.append(edge)

    def _node_by_id(self, node_id: str) -> TopologyNode:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return TopologyNode(id=node_id, type=NodeType.UNKNOWN, region="unknown")

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    def node_count(self) -> dict[NodeType, int]:
        counts: dict[NodeType, int] = {t: 0 for t in NodeType}
        for n in self.nodes:
            counts[n.type] = counts.get(n.type, 0) + 1
        return counts

    def is_empty(self, node_types: list[NodeType] | None = None) -> bool:
        """Return True if no nodes of requested types exist."""
        if node_types is None:
            return len(self.nodes) == 0
        return all(n.type not in node_types for n in self.nodes)


class TopologyDiscovery:
    """Discover Tencent Cloud resource topology via tccli."""

    # Tier determines execution priority: lower = earlier in diagnostic chain.
    TIER_MAP: ClassVar[dict[NodeType, int]] = {
        NodeType.VPC: 0,
        NodeType.CVM: 1,
        NodeType.CLB: 1,
        NodeType.ENI: 2,
        NodeType.EIP: 2,
        NodeType.NAT: 2,
        NodeType.VPN: 2,
        NodeType.VPC_PEERING: 3,
        NodeType.CDN: 4,
    }

    def __init__(
        self,
        region: str = "ap-guangzhou",
        vpc_id: str | None = None,
        dry_run: bool = False,
    ):
        self.region = region
        self.vpc_id = vpc_id
        self.dry_run = dry_run
        self._graph = TopologyGraph()

    def _tccli(self, product: str, action: str, **kwargs: Any) -> dict[str, Any]:
        """Execute tccli and return parsed JSON response."""
        if self.dry_run:
            return {"Response": {}}

        args = [
            "tccli",
            product,
            action,
            "--region", self.region,
            "--output", "json",
        ]
        for k, v in kwargs.items():
            # Quote values to prevent tccli argument misparsing on special chars.
            # subprocess.run with a list (no shell=True) is safe; tccli receives
            # each arg as a separate argv element so no shell injection risk here.
            args.extend([f"--{k}", str(v)])

        result = subprocess.run(args, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            err = result.stderr.strip()
            # Log to stderr so operators can see tccli failures in real time.
            import sys
            print(f"[topology_discovery] tccli error: {err}", file=sys.stderr)
            return {"Response": {}, "Error": err}
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            err = f"invalid JSON from tccli: {result.stdout[:200]}"
            import sys
            print(f"[topology_discovery] {err}", file=sys.stderr)
            return {"Response": {}, "Error": err}

    def discover_all(self) -> TopologyGraph:
        """Discover full topology: VPC → CVM → CLB → ENI/EIP."""
        self._graph = TopologyGraph()
        self.discover_vpcs()
        self.discover_cvm_instances()
        self.discover_clb_loadbalancers()
        self.discover_vpc_peering()
        self.discover_eni()
        return self._graph

    def discover_services(self, services: list[str]) -> TopologyGraph:
        """Discover only specified services.

        Supported: cvm, clb, vpc, vpc_peering, eni
        """
        self._graph = TopologyGraph()
        for svc in services:
            method = getattr(self, f"discover_{svc}", None)
            if callable(method):
                method()
            else:
                raise ValueError(f"Unsupported service: {svc}")  # noqa: TRY004  # value not in supported set, not a type error
        return self._graph

    def discover_vpcs(self) -> None:
        """Discover VPCs in the region."""
        resp = self._tccli("vpc", "DescribeVpcs")
        vpcs = resp.get("Response", {}).get("VpcSet", [])
        for vpc in vpcs:
            node = TopologyNode(
                id=vpc.get("VpcId", ""),
                type=NodeType.VPC,
                region=self.region,
                name=vpc.get("VpcName", ""),
                status=vpc.get("State", "unknown"),
                metadata={
                    "cidr": vpc.get("CidrBlock", ""),
                    "is_default": vpc.get("IsDefault", False),
                },
            )
            self._graph.add_node(node)

    def discover_cvm_instances(self) -> None:
        """Discover CVM instances and bind to VPC via ENIs."""
        resp = self._tccli("cvm", "DescribeInstances", **({"Filters.0.Name": "vpc-id", "Filters.0.Values.0": self.vpc_id} if self.vpc_id else {}))
        instances = resp.get("Response", {}).get("InstanceSet", [])
        for inst in instances:
            inst_id = inst.get("InstanceId", "")
            vpc_id = inst.get("VirtualPrivateCloud", {}).get("VpcId", "")
            node = TopologyNode(
                id=inst_id,
                type=NodeType.CVM,
                region=inst.get("Placement", {}).get("Zone", self.region),
                name=inst.get("InstanceName", ""),
                status=inst.get("InstanceState", "unknown"),
                metadata={
                    "instance_type": inst.get("InstanceType", ""),
                    "cpu": inst.get("CPU", ""),
                    "memory": inst.get("Memory", ""),
                    "os": inst.get("Os", ""),
                    "vpc_id": vpc_id,
                },
            )
            self._graph.add_node(node)

            # CVM → VPC edge
            if vpc_id:
                self._graph.add_edge(TopologyEdge(
                    source=vpc_id,
                    target=inst_id,
                    rel="contains",
                    metadata={"via": "vpc_id"},
                ))

    def discover_clb_loadbalancers(self) -> None:
        """Discover CLB instances and backend servers."""
        resp = self._tccli("clb", "DescribeLoadBalancers")
        lbs = resp.get("Response", {}).get("LoadBalancerSet", [])
        for lb in lbs:
            lb_id = lb.get("LoadBalancerId", "")
            vpc_id = lb.get("VpcId", "")
            node = TopologyNode(
                id=lb_id,
                type=NodeType.CLB,
                region=lb.get("LoadBalancerRegion", self.region),
                name=lb.get("LoadBalancerName", ""),
                status=lb.get("LoadBalancerStatus", "unknown"),
                metadata={
                    "address_type": lb.get("AddressType", ""),
                    "network_type": lb.get("NetworkAttributes", {}).get("InternetChargeType", ""),
                    "vpc_id": vpc_id,
                },
            )
            self._graph.add_node(node)

            if vpc_id:
                self._graph.add_edge(TopologyEdge(
                    source=vpc_id,
                    target=lb_id,
                    rel="contains",
                    metadata={"via": "vpc_id"},
                ))

            # Bind CLB → CVM via DescribeTargets
            self._discover_clb_targets(lb_id)

    def _discover_clb_targets(self, lb_id: str) -> None:
        """Discover backend CVM targets of a CLB."""
        try:
            target_resp = self._tccli("clb", "DescribeTargets", LoadBalancerId=lb_id)
            targets = target_resp.get("Response", {}).get("Listeners", [])
            for listener in targets:
                for rule in listener.get("Rules", []):
                    for target in rule.get("Targets", []):
                        self._graph.add_edge(TopologyEdge(
                            source=lb_id,
                            target=target.get("InstanceId", ""),
                            rel="loadbalances",
                            metadata={
                                "listener_id": listener.get("ListenerId", ""),
                                "weight": target.get("Weight", ""),
                            },
                        ))
        except Exception:  # noqa: BLE001, S110  # best-effort: one failing LB must not abort the whole discovery
            pass

    def discover_vpc_peering(self) -> None:
        """Discover VPC peering connections."""
        resp = self._tccli("vpc", "DescribeVpcPeeringConnections")
        connections = resp.get("Response", {}).get("VpcPeeringConnectionSet", [])
        for conn in connections:
            conn_id = conn.get("VpcPeeringConnectionId", "")
            node = TopologyNode(
                id=conn_id,
                type=NodeType.VPC_PEERING,
                region=self.region,
                name=conn.get("VpcPeeringConnectionName", ""),
                status=conn.get("State", "unknown"),
                metadata={
                    " accepter_vpc": conn.get("AccepterVpcInfo", {}).get("VpcId", ""),
                    "requester_vpc": conn.get("RequesterVpcInfo", {}).get("VpcId", ""),
                },
            )
            self._graph.add_node(node)

            accepter = conn.get("AccepterVpcInfo", {}).get("VpcId", "")
            requester = conn.get("RequesterVpcInfo", {}).get("VpcId", "")
            if accepter and requester:
                self._graph.add_edge(TopologyEdge(
                    source=accepter,
                    target=requester,
                    rel="peers_with",
                    metadata={"peering_id": conn_id},
                ))

    def discover_eni(self) -> None:
        """Discover ENIs and bind to CVM."""
        filters = {}
        if self.vpc_id:
            filters = {"Filters.0.Name": "vpc-id", "Filters.0.Values.0": self.vpc_id}
        resp = self._tccli("vpc", "DescribeNetworkInterfaces", **filters)
        nis = resp.get("Response", {}).get("NetworkInterfaceSet", [])
        for ni in nis:
            ni_id = ni.get("NetworkInterfaceId", "")
            inst_id = ni.get("InstanceId", "")
            node = TopologyNode(
                id=ni_id,
                type=NodeType.ENI,
                region=ni.get("Zone", self.region),
                name=ni.get("NetworkInterfaceName", ""),
                status=ni.get("State", "unknown"),
                metadata={
                    "vpc_id": ni.get("VpcId", ""),
                    "subnet_id": ni.get("SubnetId", ""),
                    "private_ip": ni.get("PrivateIpAddressSet", [{}])[0].get("PrivateIpAddress", ""),
                },
            )
            self._graph.add_node(node)

            if inst_id:
                self._graph.add_edge(TopologyEdge(
                    source=inst_id,
                    target=ni_id,
                    rel="binds_to",
                    metadata={"eni": ni_id},
                ))

    def get_tier_order(self) -> list[NodeType]:
        """Return NodeTypes sorted by diagnostic priority (tier)."""
        return sorted(NodeType, key=lambda t: self.TIER_MAP.get(t, 99))

    def resource_summary(self) -> dict[str, int]:
        """Return node counts by type."""
        return {t.value: count for t, count in self._graph.node_count().items()}
