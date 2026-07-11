"""
qcloud-proactive-inspection / scripts / 02-reason / analyzers / sg_analyzer.py
=============================================================================
Security Group analyzer.

Checks: dangerous open ports (0.0.0.0/0 to DB/management ports),
rule count explosion, overly permissive CIDRs.
"""

from . import register
from analyzers.base_analyzer import BaseAnalyzer
from lib.tags import get_tag

# Ports that should NEVER be open to 0.0.0.0/0
DANGER_PORTS = {
    22: "SSH",
    3389: "RDP",
    5432: "PostgreSQL",
    3306: "MySQL",
    6379: "Redis",
    27017: "MongoDB",
    9200: "Elasticsearch",
    8080: "Tomcat",
    8443: "Tomcat-SSL",
}


class SgAnalyzer(BaseAnalyzer):
    service_name = "security_group"
    icon = "[安全]"

    def discover(self, topology: dict) -> list:
        self.topology = topology
        customer = topology.get("customer", "")
        all_sgs = topology.get("raw", {}).get("security_groups", [])
        all_vms = topology.get("raw", {}).get("vms", [])
        customer_vm_ids = {
            vm.get("instanceId") for vm in all_vms if get_tag(vm, "客户") == customer
        }

        linked_sg_ids: set[str] = set()
        for vm in all_vms:
            if vm.get("instanceId") not in customer_vm_ids:
                continue
            for sg_id in vm.get("securityGroupIds") or []:
                linked_sg_ids.add(str(sg_id))

        self.resources = [
            sg
            for sg in all_sgs
            if sg.get("groupId") in linked_sg_ids or get_tag(sg, "客户") == customer
        ]
        return self.resources

    def query_metrics(self, client, hours: int = 6) -> dict:
        return {}  # No metrics for SGs

    def analyze(self) -> list:
        self.findings = []
        for sg in self.resources:
            name = sg.get("groupName", sg.get("groupId", ""))
            # Rules might be in permissionInbound / permissionOutbound
            for direction in [
                "permissionInbound",
                "permissionOutbound",
                "SecurityGroupPolicySet",
                "securityGroupPolicySet",
                "rules",
            ]:
                rules = sg.get(direction) or []
                if direction in ("SecurityGroupPolicySet", "securityGroupPolicySet") and isinstance(rules, dict):
                    rules = (rules.get("Ingress") or []) + (rules.get("Egress") or [])
                for rule in rules:
                    if not isinstance(rule, dict):
                        continue
                    cidr = (
                        rule.get("cidr")
                        or rule.get("addressPrefix")
                        or rule.get("CidrBlock")
                        or rule.get("Ipv6CidrBlock")
                        or ""
                    )
                    port_from = rule.get("port") or rule.get("fromPort") or rule.get("Port")
                    port_to = rule.get("portTo") or rule.get("toPort") or port_from
                    protocol = rule.get("protocol", "any")

                    if cidr == "0.0.0.0/0":
                        # Check if this is a danger port
                        for p in range(int(port_from or 0), int(port_to or port_from or 0) + 1):
                            if p in DANGER_PORTS:
                                self._add_finding(
                                    "critical",
                                    f"安全组规则: {DANGER_PORTS[p]}(端口{p}) 对公网开放 (0.0.0.0/0)",
                                    "建议限制来源IP或使用VPN/堡垒机",
                                    resource=name,
                                )
                                break
                        else:
                            if port_from and int(port_from) > 1024:
                                self._add_finding(
                                    "warning",
                                    f"安全组规则: 端口{port_from}-{port_to}({protocol}) 对公网开放 (0.0.0.0/0)",
                                    "建议按需限制CIDR范围",
                                    resource=name,
                                )

            # Rule count
            policy = sg.get("SecurityGroupPolicySet") or sg.get("securityGroupPolicySet") or {}
            rule_count = (
                len(sg.get("rules", []))
                + len(sg.get("permissionInbound", []))
                + len(sg.get("permissionOutbound", []))
                + len(policy.get("Ingress") or [])
                + len(policy.get("Egress") or [])
            )
            if rule_count > 50:
                self._add_finding(
                    "warning",
                    f"安全组规则数量: {rule_count}",
                    "建议合并冗余规则，减少规则数量",
                    resource=name,
                )

        return self.findings


register("security_group", SgAnalyzer)
