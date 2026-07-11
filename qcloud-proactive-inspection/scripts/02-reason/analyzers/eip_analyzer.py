"""
qcloud-proactive-inspection / scripts / 02-reason / analyzers / eip_analyzer.py
=================================================
Elastic IP analyzer.

Checks: bandwidth utilization, association/binding status, public exposure risk.
Read-only output: audit findings and recommendations only; no EIP mutation.
"""

from typing import Any

from . import register
from analyzers.base_analyzer import BaseAnalyzer

EIP_THRESHOLDS = {
    "bandwidth_warning_ratio": 0.80,
    "bandwidth_info_ratio": 0.50,
}


def _first_present(data: dict, keys: tuple, default: object = None) -> Any:
    for key in keys:
        if key in data and data.get(key) not in (None, ""):
            return data.get(key)
    return default


class EipAnalyzer(BaseAnalyzer):
    service_name = "eip"
    icon = "[拓扑]"

    def discover(self, topology: dict) -> list:
        return self.discover_by_tag(topology, "eips")

    def query_metrics(self, client, hours: int = 6) -> dict:
        for eip in self.resources:
            rid = self._resource_id(eip)
            if not rid:
                continue
            try:
                pts = client.get_metrics_batch(
                    rid,
                    ["eip.bandwidth.in", "eip.bandwidth.out"],
                    hours=hours,
                    region=getattr(client, "region", None),
                    service_code="eip",
                )
                if pts:
                    self.metrics[rid] = pts
            except Exception:
                continue
        return self.metrics

    def analyze(self) -> list:
        self.findings = []
        for eip in self.resources:
            rid = self._resource_id(eip)
            ip = self._ip_address(eip)
            bandwidth_mbps = self._bandwidth_mbps(eip)
            bound_resource = self._bound_resource(eip)
            metrics = self.metrics.get(rid, {})

            ctx = {
                "resource": ip,
                "resource_id": rid,
                "resource_ip": ip,
                "instance_type": f"{bandwidth_mbps}Mbps",
            }

            for direction, label in [
                ("eip.bandwidth.in", "入带宽"),
                ("eip.bandwidth.out", "出带宽"),
            ]:
                pts = metrics.get(direction, [])
                if not pts:
                    continue
                peak = max(v for _, v in pts) / 1_000_000  # bps → Mbps
                ratio = peak / bandwidth_mbps if bandwidth_mbps > 0 else 0
                if ratio >= EIP_THRESHOLDS["bandwidth_warning_ratio"]:
                    self._add_finding(
                        "warning",
                        f"{label}峰值{peak:.1f}Mbps，达到EIP带宽{bandwidth_mbps}Mbps的{ratio * 100:.0f}%",
                        "只读建议：确认业务流量峰值；如需调整带宽，由人工通过 qcloud-vpc-ops 执行",
                        ops_skill="qcloud-vpc-ops",
                        **ctx,
                    )
                elif ratio >= EIP_THRESHOLDS["bandwidth_info_ratio"]:
                    self._add_finding(
                        "info",
                        f"{label}峰值{peak:.1f}Mbps，达到EIP带宽的{ratio * 100:.0f}%",
                        "建议关注带宽趋势",
                        **ctx,
                    )

            if bound_resource:
                self._add_finding(
                    "info",
                    f"EIP已绑定：{bound_resource}，带宽{bandwidth_mbps}Mbps",
                    "审计记录：公网入口需确保安全组/ACL最小开放",
                    **ctx,
                )
            else:
                self._add_finding(
                    "warning",
                    f"EIP未绑定任何资源，带宽{bandwidth_mbps}Mbps",
                    "只读建议：确认是否闲置；如需释放或绑定，必须由人工通过 qcloud-vpc-ops 执行",
                    ops_skill="qcloud-vpc-ops",
                    **ctx,
                )

            if not metrics:
                self._add_finding(
                    "info",
                    "未获取到EIP流量指标",
                    "建议检查云监控指标是否开通；本次仅基于资源属性完成审计",
                    **ctx,
                )

        return self.findings

    def _resource_summary(self) -> list:
        return [
            {
                "elasticIpId": self._resource_id(e),
                "ip": self._ip_address(e),
                "bandwidthMbps": self._bandwidth_mbps(e),
                "binding": self._bound_resource(e),
            }
            for e in self.resources
        ]

    def _resource_id(self, eip: dict) -> str:
        return _first_present(eip, ("elasticIpId", "id", "eipId"), "")

    def _ip_address(self, eip: dict) -> str:
        return _first_present(
            eip, ("elasticIpAddress", "ipAddress", "publicIp", "address"), self._resource_id(eip)
        )

    def _bandwidth_mbps(self, eip: dict) -> float:
        value = _first_present(
            eip, ("bandwidthMbps", "bandwidth", "bandwidthMb", "bandwidthM"), 1000
        )
        try:
            return float(value)
        except (TypeError, ValueError):
            return 1000.0

    def _bound_resource(self, eip: dict) -> str:
        resource_id = _first_present(
            eip,
            ("instanceId", "resourceId", "bindResourceId", "targetId", "associatedResourceId"),
            "",
        )
        resource_type = _first_present(
            eip,
            (
                "instanceType",
                "resourceType",
                "bindResourceType",
                "targetType",
                "associatedResourceType",
            ),
            "",
        )
        if resource_id and resource_type:
            return f"{resource_type}:{resource_id}"
        return resource_id or ""


register("eip", EipAnalyzer)
