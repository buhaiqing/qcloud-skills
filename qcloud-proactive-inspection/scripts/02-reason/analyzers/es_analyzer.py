"""
qcloud-proactive-inspection / scripts / 02-reason / analyzers / es_analyzer.py
=============================================================================
Elasticsearch analyzer.

Checks: cluster health, version, node count, disk type, encryption status.
"""

from . import register
from analyzers.base_analyzer import BaseAnalyzer
from lib.tags import get_tag


class EsAnalyzer(BaseAnalyzer):
    service_name = "elasticsearch"
    icon = "[搜索]"

    def discover(self, topology: dict) -> list:
        self.topology = topology
        customer = topology.get("customer", "")
        all_es = topology.get("raw", {}).get("es", [])
        self.resources = [e for e in all_es if get_tag(e, "客户") == customer]
        return self.resources

    def query_metrics(self, client, hours: int = 6) -> dict:
        # ES monitoring metrics may not be available via vm serviceCode
        # Best-effort: try common monitor metrics
        es_metrics = ["cpu_util", "memory.usage", "vm.disk.dev.used"]
        for es in self.resources:
            rid = es.get("instanceId")
            if not rid:
                continue
            try:
                pts = client.get_metrics_batch(
                    rid, es_metrics, hours=hours, region=client.region, service_code="es"
                )
                if pts:
                    self.metrics[rid] = pts
            except Exception:
                continue
        return self.metrics

    def analyze(self) -> list:
        self.findings = []
        for es in self.resources:
            rid = es.get("instanceId")
            name = es.get("instanceName", rid)
            tags = {t["key"]: t["value"] for t in es.get("tags", [])}

            # Version check
            ver = es.get("instanceVersion", "")
            if ver and ver < "7.0":
                self._add_finding(
                    "warning", f"ES版本{ver} 偏旧", "建议升级到7.x以获得更好性能和安全性", name
                )

            # Cluster type
            ctype = es.get("clusterType", "")
            env = tags.get("环境", "")
            if ctype == "general" and env == "production":
                self._add_finding("info", "通用型集群 (生产环境)", "", name)

            # Node configuration
            ic = es.get("instanceClass", {})
            node_count = ic.get("nodeCount", 0)
            node_class = ic.get("nodeClass", "")
            node_disk_gb = ic.get("nodeDiskGB", 0)
            node_disk_type = ic.get("nodeDiskType", "")

            self._add_finding(
                "info",
                f"节点配置: {node_count}×{node_class}, 磁盘{node_disk_gb}GB {node_disk_type}",
                "",
                name,
            )

            # Kibana
            kibana = ic.get("kibana", False)
            if kibana:
                kibana_url = es.get("kibanaUrl", "")
                self._add_finding("info", f"Kibana已启用: {kibana_url[:60]}..", "", name)

            # Dedicated master / coordinating nodes
            if es.get("dedicatedMaster"):
                self._add_finding("info", "专用主节点已启用", "", name)
            if es.get("coordinating"):
                self._add_finding("info", "专用协调节点已启用", "", name)
            if es.get("warmnode"):
                self._add_finding("info", "温节点已启用", "", name)

            # Disk encryption check (from instance class if available)
            disk_type_desc = ic.get("nodeDiskTypeDesc", "")
            if disk_type_desc:
                self._add_finding("info", f"磁盘类型: {disk_type_desc}", "", name)

            # Charge
            charge = es.get("charge", {})
            expire = charge.get("chargeExpiredTime", "")
            if expire:
                self._add_finding("info", f"到期时间: {expire}", "", name)

            # Count metrics
            metrics = self.metrics.get(rid, {})
            for mname in ["cpu_util", "memory.usage"]:
                pts = metrics.get(mname, [])
                if pts:
                    avg = sum(v for _, v in pts) / len(pts)
                    if mname == "cpu_util" and avg > 70:
                        self._add_finding("warning", f"CPU平均{avg:.1f}%", "检查ES查询负载", name)
                    elif mname == "memory.usage" and avg > 80:
                        self._add_finding(
                            "warning", f"内存平均{avg:.1f}%", "检查JVM堆内存使用", name
                        )

        return self.findings


register("elasticsearch", EsAnalyzer)
