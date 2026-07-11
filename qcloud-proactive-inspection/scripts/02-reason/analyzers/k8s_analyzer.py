"""
qcloud-proactive-inspection / scripts / 02-reason / analyzers / k8s_analyzer.py
==============================================================================
Kubernetes cluster analyzer (Tencent TKE).

Discovery via Tencent Cloud tags:
- Cluster status and version (tccli tke DescribeCluster)
- Node group info (VM count per group)
- Recognized via the tke.cloud.tencent.com/cluster_id tag on VMs / CLBs

Pod-level analysis is NOT covered by this analyzer; delegate to qcloud-tke-ops
when deeper pod/Deployment diagnostics are required.
"""

from . import register
from analyzers.base_analyzer import BaseAnalyzer
from lib.normalize import normalize_resource
from lib.tags import get_tag

K8S_CLUSTER_TAG = "tke.cloud.tencent.com/cluster_id"


class K8sAnalyzer(BaseAnalyzer):
    service_name = "k8s"
    icon = "[集群]"

    def discover(self, topology: dict) -> list:
        """Discover K8s clusters from tagged VMs + CLBs."""
        self.topology = topology
        customer = topology.get("customer", "")
        all_vms = topology.get("raw", {}).get("vms", [])
        all_lbs = topology.get("raw", {}).get("lbs", [])

        # Extract unique cluster IDs from VM tags and CLB tags
        cluster_ids = set()
        for vm in all_vms:
            if get_tag(vm, "客户") == customer:
                cid = get_tag(vm, K8S_CLUSTER_TAG)
                if cid:
                    cluster_ids.add(cid)
        for lb in all_lbs:
            if get_tag(lb, "客户") == customer:
                cid = get_tag(lb, K8S_CLUSTER_TAG)
                if cid:
                    cluster_ids.add(cid)

        # Build cluster info
        self.resources = []
        for cid in cluster_ids:
            nodes = [vm for vm in all_vms if get_tag(vm, K8S_CLUSTER_TAG) == cid]
            ingress = [
                lb
                for lb in all_lbs
                if get_tag(lb, K8S_CLUSTER_TAG) == cid
                and get_tag(lb, "tke.cloud.tencent.com/created_by")
            ]
            cluster_info = {
                "cluster_id": cid,
                "node_count": len(nodes),
                "node_vms": [v.get("instanceName") for v in nodes],
                "ingress_count": len(ingress),
                "ingress_lbs": [lb.get("loadBalancerName") for lb in ingress],
                "node_groups": self._extract_node_groups(nodes),
            }
            self.resources.append(cluster_info)

        return self.resources

    def query_metrics(self, client, hours: int = 6) -> dict:
        """Collect cluster info via kubernetes API (best-effort)."""
        try:
            clusters = client.list_clusters()
            for cl in self.resources:
                cid = cl["cluster_id"]
                match = [
                    c
                    for c in clusters
                    if c.get("ClusterId") == cid
                    or c.get("clusterId") == cid
                    or str(c.get("ClusterName", "")).find(cid[:8]) >= 0
                ]
                if match:
                    info = normalize_resource(match[0])
                    cl["cluster_info_api"] = info
                    cl["version"] = info.get("clusterVersion") or info.get("version", "N/A")
                    cl["state"] = info.get("clusterStatus") or info.get("clusterState", "N/A")
        except Exception:
            pass
        for cl in self.resources:
            cl.setdefault("version", "N/A")
            cl.setdefault("state", "N/A")
        return {}

    def analyze(self) -> list:
        self.findings = []
        for cl in self.resources:
            cid = cl["cluster_id"]
            node_count = cl["node_count"]
            version = cl.get("version", "N/A")
            state = cl.get("state", "N/A")

            if state and str(state).lower() not in ("running", "active", "n/a", "normal"):
                self._add_finding(
                    "critical", f"集群状态异常: {state}", "检查控制平面和控制节点健康", cid
                )
            else:
                self._add_finding("info", f"集群健康 (状态={state}, 版本={version})", "", cid)

            if node_count == 0:
                self._add_finding("warning", "集群无节点", "检查节点组配置", cid)
            else:
                self._add_finding(
                    "info", f"节点数: {node_count}, Ingress数: {cl['ingress_count']}", "", cid
                )

            # Check node group info
            ng = cl.get("node_groups", {})
            for ng_id, ng_vms in ng.items():
                self._add_finding("info", f"节点组 {ng_id}: {len(ng_vms)} 台VM", "", cid)

        return self.findings

    @staticmethod
    def _extract_node_groups(nodes: list) -> dict:
        groups = {}
        for vm in nodes:
            ng = get_tag(vm, "tke.cloud.tencent.com/node_group_id")
            if ng:
                groups.setdefault(ng, []).append(vm.get("instanceName"))
        return groups


register("k8s", K8sAnalyzer)
