"""
qcloud-proactive-inspection / scripts / 02-reason / analyzers / vm_analyzer.py
=============================================================================
VM / ECS analyzer.

Handles both:
- K8s node VMs → focus on Pod allocation, node pressure
- Traditional VMs → focus on application resource usage, OS tuning

Discovery: extracts VMs from topology tagged with the target customer.
Metrics:  CPU, memory, disk IOPS/usage, network bandwidth, system load, TCP conn.
Spec limits: checks against instance type and disk type upper limits.
"""

from . import register
from .base_analyzer import BaseAnalyzer
from lib.tags import tag_dict, get_tag


# ── Thresholds (from references/threshold-definitions.md) ──

THRESHOLDS = {
    "cpu_util": {"warning": 70.0, "critical": 85.0},
    "memory.usage": {"warning": 80.0, "critical": 90.0},
    "vm.disk.dev.used": {"warning": 75.0, "critical": 90.0},
    "vm.disk.dev.io.read": {"warning": None, "critical": None},  # check spec limits
    "vm.disk.dev.io.write": {"warning": None, "critical": None},
}

# Spec limits (partial — full table in references/)
INSTANCE_LIMITS = {
    "c.n3.large": {"network_gbps": 1.5, "max_pps": 300000, "max_conn": 200000},
    "c.n3.xlarge": {"network_gbps": 3.0, "max_pps": 500000, "max_conn": 400000},
    "c.n3.2xlarge": {"network_gbps": 4.0, "max_pps": 800000, "max_conn": 500000},
    "g.n3.large": {"network_gbps": 1.5, "max_pps": 300000, "max_conn": 200000},
    "g.n3.2xlarge": {"network_gbps": 4.0, "max_pps": 800000, "max_conn": 500000},
    "g.n3.4xlarge": {"network_gbps": 8.0, "max_pps": 1200000, "max_conn": 800000},
    "m.n2.xlarge": {"network_gbps": 3.0, "max_pps": 500000, "max_conn": 400000},
}

DISK_LIMITS = {
    "ssd.gp1": {"max_iops_per_gb": 20, "max_iops": 10000, "throughput_mbps": 150},
    "ssd.io1": {"max_iops_per_gb": 50, "max_iops": 50200, "throughput_mbps": 350},
}

K8S_TAG_KEYS = [
    "tke.cloud.tencent.com/cluster_id",
    "tke.cloud.tencent.com/node_group_id",
]


class VmAnalyzer(BaseAnalyzer):
    service_name = "vm"
    icon = "[主机]"

    METRICS = [
        "cpu_util",
        "memory.usage",
        "vm.disk.dev.io.read",
        "vm.disk.dev.io.write",
        "vm.disk.dev.used",
        "vm.avg.load5",
        "vm.network.dev.bytes.in",
        "vm.network.dev.bytes.out",
        "vm.netstat.tcp.established",
    ]

    def discover(self, topology: dict) -> list:
        """Extract VMs tagged with the target customer."""
        return self.discover_by_tag(topology, "vms")

    def query_metrics(self, client, hours: int = 6) -> dict:
        """Collect metrics for all discovered VMs (last 6 hours)."""
        return self.query_metrics_batch(
            client, id_field="instanceId", metrics=self.METRICS, hours=hours, service_code="vm"
        )

    def analyze(self) -> list:
        """Run all VM analysis rules."""
        self.findings = []

        for vm in self.resources:
            rid = vm.get("instanceId")
            name = vm.get("instanceName", rid)
            ip = vm.get("privateIpAddress", "")
            instance_type = vm.get("instanceType", "")
            tags = tag_dict(vm)
            is_k8s = any(k in tags for k in K8S_TAG_KEYS)
            limits = INSTANCE_LIMITS.get(instance_type, {})
            metrics = self.metrics.get(rid, {})

            # Helper to auto-fill VM context into findings
            ctx = {
                "resource": name,
                "resource_id": rid,
                "resource_ip": ip,
                "instance_type": instance_type,
            }

            # ── CPU threshold ──
            cpu = metrics.get("cpu_util", [])
            if cpu:
                avg = sum(v for _, v in cpu) / len(cpu)
                max_cpu = max(v for _, v in cpu)
                if avg > THRESHOLDS["cpu_util"]["critical"]:
                    act = (
                        "1. 登录服务器执行 `top -bn1` 查看高CPU进程; "
                        "2. 确认异常进程后联系应用负责人; "
                        "3. 如需升配，通过 qcloud-cvm-ops 执行"
                    )
                    self._add_finding(
                        "critical",
                        f"CPU平均使用率{avg:.1f}%（阈值>{THRESHOLDS['cpu_util']['critical']}%），峰值{max_cpu:.1f}%",
                        act,
                        ops_skill="qcloud-cvm-ops",
                        **ctx,
                    )
                elif avg > THRESHOLDS["cpu_util"]["warning"]:
                    act = "检查进程资源占用；如持续偏高建议升配（通过 qcloud-cvm-ops）"
                    self._add_finding(
                        "warning",
                        f"CPU平均使用率{avg:.1f}%（阈值>{THRESHOLDS['cpu_util']['warning']}%）",
                        act,
                        **ctx,
                    )

            # ── Memory threshold ──
            mem = metrics.get("memory.usage", [])
            if mem:
                avg = sum(v for _, v in mem) / len(mem)
                max_mem = max(v for _, v in mem)
                if avg > THRESHOLDS["memory.usage"]["critical"]:
                    act = (
                        "1. 登录服务器执行 `free -m` 确认内存使用; "
                        "2. 检查应用日志查找 OOM 相关错误; "
                        "3. 如需升配，通过 qcloud-cvm-ops 执行升配操作"
                    )
                    self._add_finding(
                        "critical",
                        f"内存平均使用率{avg:.1f}%（阈值>{THRESHOLDS['memory.usage']['critical']}%），峰值{max_mem:.1f}%",
                        act,
                        ops_skill="qcloud-cvm-ops",
                        **ctx,
                    )
                elif avg > THRESHOLDS["memory.usage"]["warning"]:
                    self._add_finding(
                        "warning",
                        f"内存平均使用率{avg:.1f}%（阈值>{THRESHOLDS['memory.usage']['warning']}%）",
                        "检查进程内存占用，关注是否有内存泄漏",
                        **ctx,
                    )

            # ── Disk usage ──
            du = metrics.get("vm.disk.dev.used", [])
            if du:
                last = du[-1][1]
                if last > THRESHOLDS["vm.disk.dev.used"]["critical"]:
                    self._add_finding(
                        "critical",
                        f"磁盘使用率{last:.1f}%（阈值>{THRESHOLDS['vm.disk.dev.used']['critical']}%）",
                        "1. 登录服务器执行 `df -h` 确认具体分区; 2. 清理日志或临时文件; 3. 通过 qcloud-cvm-ops 扩容云盘",
                        ops_skill="qcloud-cvm-ops",
                        **ctx,
                    )
                elif last > THRESHOLDS["vm.disk.dev.used"]["warning"]:
                    self._add_finding(
                        "warning",
                        f"磁盘使用率{last:.1f}%（阈值>{THRESHOLDS['vm.disk.dev.used']['warning']}%）",
                        "计划扩容或清理数据",
                        **ctx,
                    )

            # ── IOPS spec limit ──
            disk_type = self._infer_disk_type(vm)
            disk_limits = DISK_LIMITS.get(disk_type, {})
            max_iops = disk_limits.get("max_iops", 999999)

            for iop_metric, label in [
                ("vm.disk.dev.io.read", "读IOPS"),
                ("vm.disk.dev.io.write", "写IOPS"),
            ]:
                pts = metrics.get(iop_metric, [])
                if pts:
                    peak = max(v for _, v in pts)
                    avg_iops = sum(v for _, v in pts) / len(pts)
                    ratio = peak / max_iops if max_iops > 0 else 0
                    if ratio > 0.8:
                        self._add_finding(
                            "warning",
                            f"{label}峰值{peak:.0f}，平均{avg_iops:.0f}，已达{disk_type}上限{max_iops}的{ratio * 100:.0f}%",
                            f"1. 检查磁盘 {disk_type} 是否达到IOPS瓶颈; 2. 优化查询减少IO; 3. 如需升配通过 qcloud-cvm-ops 执行",
                            ops_skill="qcloud-cvm-ops",
                            **ctx,
                        )

            # ── Network bandwidth spec limit ──
            net_gbps = limits.get("network_gbps", 99)
            net_max_bps = net_gbps * 1_000_000_000
            for _direction, label, mkey in [
                ("入", "入带宽", "vm.network.dev.bytes.in"),
                ("出", "出带宽", "vm.network.dev.bytes.out"),
            ]:
                pts = metrics.get(mkey, [])
                if pts:
                    peak_bps = max(v for _, v in pts)
                    peak_mbps = peak_bps / 1_000_000
                    ratio = peak_bps / net_max_bps if net_max_bps > 0 else 0
                    if ratio > 0.8:
                        self._add_finding(
                            "warning",
                            f"网络{label}带宽峰值{peak_mbps:.1f}Mbps，已达{instance_type}上限{net_gbps}Gbps的{ratio * 100:.0f}%",
                            "1. 检查流量来源; 2. 如需升配实例规格通过 qcloud-cvm-ops 执行",
                            ops_skill="qcloud-cvm-ops",
                            **ctx,
                        )

            # 云盘加密
            for dd in vm.get("dataDisks", []):
                cd = dd.get("cloudDisk", {})
                if not cd.get("encrypted", True) and not cd.get("encrypt", True):
                    self._add_finding(
                        "warning",
                        f"数据盘 {cd.get('name', '')} ({cd.get('diskSizeGB', 0)}GB {cd.get('diskType', '')}) 未加密",
                        "控制台操作：云硬盘 → 更多 → 创建加密快照 → 用快照创建加密盘",
                        ops_skill="qcloud-cvm-ops",
                        **ctx,
                    )
            sd = vm.get("systemDisk", {}).get("cloudDisk", {})
            if not sd.get("encrypted", True) and not sd.get("encrypt", True):
                self._add_finding(
                    "info",
                    f"系统盘 {sd.get('diskSizeGB', 0)}GB {sd.get('diskType', '')} 未加密",
                    "敏感环境建议通过加密快照迁移",
                    ops_skill="qcloud-cvm-ops",
                    **ctx,
                )

            # K8s 识别
            if is_k8s:
                cluster_id = get_tag(vm, "tke.cloud.tencent.com/cluster_id")
                self._add_finding(
                    "info", f"K8s节点（集群 {cluster_id}）", "Pod级分析请使用 k8s_analyzer", **ctx
                )

            # 系统负载
            ld = metrics.get("vm.avg.load5", [])
            if ld:
                avg_load = sum(v for _, v in ld) / len(ld)
                vcpu = self._estimate_vcpu(instance_type)
                ratio = avg_load / vcpu if vcpu > 0 else 0
                if ratio > 6.0:
                    self._add_finding(
                        "warning",
                        f"系统负载(5min)平均{avg_load:.2f}（vCPU={vcpu}，负载/vCPU={ratio:.2f}，阈值>6.0）",
                        "检查是否有异常进程或流量突增",
                        ops_skill="qcloud-cvm-ops",
                        **ctx,
                    )

            # TCP 连接
            tcp = metrics.get("vm.netstat.tcp.established", [])
            if tcp:
                avg_tcp = sum(v for _, v in tcp) / len(tcp)
                max_conn = limits.get("max_conn", 9999999)
                if max_conn < 9999999 and avg_tcp > max_conn * 0.8:
                    self._add_finding(
                        "warning",
                        f"TCP连接数平均{avg_tcp:.0f}，已达{instance_type}上限{max_conn}的{avg_tcp / max_conn * 100:.0f}%",
                        "检查连接泄漏，考虑升配实例规格",
                        ops_skill="qcloud-cvm-ops",
                        **ctx,
                    )

            # 到期提醒
            charge = vm.get("charge", {})
            expire = charge.get("chargeExpiredTime", "")
            if expire:
                self._add_finding(
                    "info",
                    f"到期时间: {expire}",
                    "通过 qcloud-cvm-ops 续费",
                    ops_skill="qcloud-cvm-ops",
                    **ctx,
                )

        return self.findings

    def _compute_water_level(self) -> dict:
        """Compute spec resource water level for display."""
        levels = {}
        for vm in self.resources:
            rid = vm.get("instanceId")
            instance_type = vm.get("instanceType", "")
            limits = INSTANCE_LIMITS.get(instance_type, {})
            metrics = self.metrics.get(rid, {})
            wl = {}

            net_gbps = limits.get("network_gbps", 99)
            net_max = net_gbps * 1_000_000_000
            for direction in ["vm.network.dev.bytes.in", "vm.network.dev.bytes.out"]:
                pts = metrics.get(direction, [])
                if pts and net_max > 0:
                    peak = max(v for _, v in pts)
                    wl[direction] = min(peak / net_max, 1.0)

            disk_type = self._infer_disk_type(vm)
            dl = DISK_LIMITS.get(disk_type, {})
            for iop in ["vm.disk.dev.io.read", "vm.disk.dev.io.write"]:
                pts = metrics.get(iop, [])
                if pts and dl.get("max_iops", 0) > 0:
                    peak = max(v for _, v in pts)
                    wl[iop] = min(peak / dl["max_iops"], 1.0)

            cpu = metrics.get("cpu_util", [])
            if cpu:
                avg = sum(v for _, v in cpu) / len(cpu)
                wl["cpu_util"] = avg / 100.0

            mem = metrics.get("memory.usage", [])
            if mem:
                avg = sum(v for _, v in mem) / len(mem)
                wl["memory.usage"] = avg / 100.0

            if wl:
                levels[rid] = wl
        return levels

    @staticmethod
    def _infer_disk_type(vm: dict) -> str:
        """Try to infer the primary data disk type from VM info."""
        for dd in vm.get("dataDisks", []):
            cd = dd.get("cloudDisk", {})
            dt = cd.get("diskType", "")
            if dt:
                return dt
        sd = vm.get("systemDisk", {})
        cd = sd.get("cloudDisk", {})
        return cd.get("diskType", "ssd.gp1")

    @staticmethod
    def _estimate_vcpu(instance_type: str) -> int:
        """Estimate vCPU count from instance type string."""
        mapping = {
            "c.n3.large": 2,
            "c.n3.xlarge": 4,
            "c.n3.2xlarge": 8,
            "g.n3.large": 2,
            "g.n3.2xlarge": 8,
            "g.n3.4xlarge": 16,
            "m.n2.xlarge": 4,
        }
        return mapping.get(instance_type, 8)


register("vm", VmAnalyzer)
