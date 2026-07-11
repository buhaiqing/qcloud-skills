"""
qcloud-proactive-inspection / scripts / 02-reason / analyzers / nat_analyzer.py
=================================================
NAT Gateway analyzer.

Checks: SNAT connection count, bandwidth utilization.
"""

from . import register
from analyzers.base_analyzer import BaseAnalyzer
from lib.tags import get_tag


class NatAnalyzer(BaseAnalyzer):
    service_name = "nat"
    icon = "[网关]"

    def discover(self, topology: dict) -> list:
        self.topology = topology
        customer = topology.get("customer", "")
        all_nats = topology.get("raw", {}).get("nats", [])
        self.resources = [n for n in all_nats if get_tag(n, "客户") == customer]
        return self.resources

    def query_metrics(self, client, hours: int = 6) -> dict:
        for nat in self.resources:
            rid = nat.get("natGatewayId") or nat.get("id")
            if not rid:
                continue
            try:
                pts = client.get_metrics_batch(
                    rid,
                    ["nat.connections", "nat.bandwidth.in", "nat.bandwidth.out"],
                    hours=hours,
                    region=client.region,
                    service_code="nat",
                )
                if pts:
                    self.metrics[rid] = pts
            except Exception:
                continue
        return self.metrics

    def analyze(self) -> list:
        self.findings = []
        for nat in self.resources:
            rid = nat.get("natGatewayId") or nat.get("id")
            name = nat.get("natGatewayName", rid)
            metrics = self.metrics.get(rid, {})

            conn = metrics.get("nat.connections", [])
            if conn:
                avg_c = sum(v for _, v in conn) / len(conn)
                max_c = max(v for _, v in conn)
                if max_c > 50000:
                    self._add_finding(
                        "warning",
                        f"SNAT连接峰值{max_c:.0f}",
                        "接近端口耗尽风险，考虑增加NAT网关规格或拆分",
                        name,
                    )
                elif avg_c > 30000:
                    self._add_finding("info", f"SNAT连接平均{avg_c:.0f}", "建议关注", name)

            for direction, label in [
                ("nat.bandwidth.in", "入带宽"),
                ("nat.bandwidth.out", "出带宽"),
            ]:
                pts = metrics.get(direction, [])
                if pts:
                    peak = max(v for _, v in pts) / 1_000_000
                    if peak > 500:
                        self._add_finding("info", f"NAT {label}峰值{peak:.1f}Mbps", "", name)

        return self.findings


register("nat", NatAnalyzer)
