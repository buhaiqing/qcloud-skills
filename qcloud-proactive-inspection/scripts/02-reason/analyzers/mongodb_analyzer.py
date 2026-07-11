"""
qcloud-proactive-inspection / scripts / 02-reason / analyzers / mongodb_analyzer.py
==================================================================================
MongoDB AIOps analyzer.

Discovery: MongoDB instances tagged with target customer.
Metrics: CPU, memory, disk, IOPS, connections, throughput, latency,
replication lag, and oplog window (best-effort via CloudMonitor).
Features: root-cause candidates with evidence for high CPU/latency,
connection storms, capacity pressure, replica lag, and slow-query/index risk.

This analyzer is read-only. It only generates findings and delegates any
mutation (scale, index creation, whitelist/security-group changes) to the
appropriate ops skill with human confirmation.
"""


from analyzers import register
from analyzers.base_analyzer import BaseAnalyzer
from lib.tags import get_tag, tag_dict


class MongoDBAnalyzer(BaseAnalyzer):
    service_name = "mongodb"
    icon = "[数据库]"

    METRICS = [
        "mongodb_cpu_utilization",
        "mongodb_memory_usage",
        "mongodb_disk_usage",
        "mongodb_iops",
        "mongodb_connections_current",
        "mongodb_connections_usage",
        "mongodb_opcounters",
        "mongodb_query_rate",
        "mongodb_insert_rate",
        "mongodb_update_rate",
        "mongodb_delete_rate",
        "mongodb_read_latency",
        "mongodb_write_latency",
        "mongodb_command_latency",
        "mongodb_repl_lag",
        "mongodb_oplog_window",
    ]

    def discover(self, topology: dict) -> list:
        self.topology = topology
        customer = topology.get("customer", "")
        raw = topology.get("raw", {})
        all_mongodb = raw.get("mongodb") or raw.get("mongo") or []
        if customer:
            self.resources = [r for r in all_mongodb if get_tag(r, "客户") == customer]
        else:
            self.resources = all_mongodb
        return self.resources

    def query_metrics(self, client, hours: int = 6) -> dict:
        for r in self.resources:
            rid = self._rid(r)
            if not rid:
                continue
            try:
                pts = client.get_metrics_batch(
                    rid,
                    self.METRICS,
                    hours=hours,
                    region=client.region,
                    service_code="mongodb",
                )
                if pts:
                    self.metrics[rid] = pts
            except Exception:
                continue
        return self.metrics

    def analyze(self) -> list:
        self.findings = []
        for r in self.resources:
            rid = self._rid(r)
            name = self._name(r, rid)
            instance_type = r.get("instanceClass") or r.get("class") or r.get("instanceType", "")
            metrics = self.metrics.get(rid, {})
            tags = tag_dict(r)

            status = r.get("status") or r.get("instanceStatus")
            if status and status != "running":
                self._add_finding(
                    "critical",
                    f"实例状态异常: {status}",
                    "检查最近备份/恢复/变更任务；若长时间非 running，提交工单并附 InstanceId/RequestId",
                    name,
                    rid,
                    instance_type=instance_type,
                    ops_skill="qcloud-mongodb-ops",
                )

            self._analyze_resource_pressure(name, rid, instance_type, metrics)
            self._analyze_latency_and_queries(name, rid, instance_type, metrics)
            self._analyze_connections(name, rid, instance_type, metrics)
            self._analyze_replication(name, rid, instance_type, metrics)
            self._analyze_capacity_trend(name, rid, instance_type, metrics)

            version = r.get("engineVersion") or r.get("mongodbVersion") or r.get("version")
            if version and str(version) < "4.0":
                self._add_finding(
                    "info",
                    f"MongoDB 版本 {version} 偏旧",
                    "建议评估升级窗口，升级前先验证驱动兼容性和备份可恢复性",
                    name,
                    rid,
                    instance_type=instance_type,
                    ops_skill="qcloud-mongodb-ops",
                )

            env = tags.get("环境", "")
            if env:
                self._add_finding(
                    "info", f"环境: {env}", "", name, rid, instance_type=instance_type
                )

        return self.findings

    def _analyze_resource_pressure(self, name, rid, instance_type, metrics):
        cpu = self._stats(metrics.get("mongodb_cpu_utilization"))
        mem = self._stats(metrics.get("mongodb_memory_usage"))
        disk = self._stats(metrics.get("mongodb_disk_usage"))
        iops = self._stats(metrics.get("mongodb_iops"))

        if cpu and cpu["max"] > 85:
            cause = self._root_cause_high_cpu(metrics)
            self._add_finding(
                "critical" if cpu["current"] > 85 else "warning",
                f"CPU 使用率峰值 {cpu['max']:.1f}% / 当前 {cpu['current']:.1f}%；根因候选: {cause}",
                "优先拉取慢查询并按 query shape 聚合；检查 explain 是否 COLLSCAN；若 QPS 同步激增，关联应用发布/流量；优化后仍持续高位再评估升配",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )
        elif cpu and cpu["avg"] > 70:
            self._add_finding(
                "warning",
                f"CPU 平均使用率 {cpu['avg']:.1f}% (>70%)",
                "建立同周期基线；检查慢查询、索引命中率和应用流量变化",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )

        if mem and mem["current"] > 90:
            self._add_finding(
                "critical",
                f"内存使用率 {mem['current']:.1f}% (>90%)",
                "分析 working set 是否超过内存；检查连接数和大聚合；必要时评估升配",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )
        elif mem and mem["current"] > 75:
            self._add_finding(
                "warning",
                f"内存使用率 {mem['current']:.1f}% (>75%)",
                "关注 working set 增长趋势；检查大集合和索引大小",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )

        if disk and disk["current"] > 90:
            self._add_finding(
                "critical",
                f"磁盘使用率 {disk['current']:.1f}% (>90%)",
                "立即评估扩容或清理历史集合；检查 TTL、备份/恢复任务和集合增长 TopN",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )
        elif disk and disk["current"] > 80:
            self._add_finding(
                "warning",
                f"磁盘使用率 {disk['current']:.1f}% (>80%)",
                "做 7 天容量趋势预测；识别增长最快集合和索引膨胀",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )

        if iops and iops["max"] > 0 and self._is_rising(metrics.get("mongodb_iops")):
            self._add_finding(
                "info",
                f"IOPS 呈上升趋势，当前 {iops['current']:.1f}",
                "与 read/write latency 联合判断磁盘瓶颈；检查是否有批量导入、无索引扫描或备份任务",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )

    def _analyze_latency_and_queries(self, name, rid, instance_type, metrics):
        read_lat = self._stats(metrics.get("mongodb_read_latency"))
        write_lat = self._stats(metrics.get("mongodb_write_latency"))
        cmd_lat = self._stats(metrics.get("mongodb_command_latency"))
        query = self._stats(metrics.get("mongodb_query_rate"))
        ops = self._stats(metrics.get("mongodb_opcounters"))

        high_latency = any(s and s["max"] > 200 for s in [read_lat, write_lat, cmd_lat])
        if high_latency:
            query_msg = ""
            if query and self._is_rising(metrics.get("mongodb_query_rate")):
                query_msg = f"；query_rate 当前 {query['current']:.1f} 且上升"
            elif ops and self._is_rising(metrics.get("mongodb_opcounters")):
                query_msg = f"；opcounters 当前 {ops['current']:.1f} 且上升"
            self._add_finding(
                "warning",
                f"MongoDB 延迟升高{query_msg}；读/写/命令延迟峰值分别为 {self._fmt(read_lat)}/{self._fmt(write_lat)}/{self._fmt(cmd_lat)} ms",
                "按时间窗口拉取 slow query；聚合 query shape；检查 COLLSCAN、docsExamined/nReturned、无索引 SORT；关联应用发布和流量突增",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )

    def _analyze_connections(self, name, rid, instance_type, metrics):
        conn = self._stats(metrics.get("mongodb_connections_current"))
        usage = self._stats(metrics.get("mongodb_connections_usage"))
        if usage and usage["current"] > 85:
            self._add_finding(
                "critical",
                f"连接使用率 {usage['current']:.1f}% (>85%)",
                "检查应用连接池是否泄漏；确认 maxPoolSize/minPoolSize；按客户端 IP 聚合连接；必要时限流或升配",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )
        elif usage and usage["current"] > 70:
            self._add_finding(
                "warning",
                f"连接使用率 {usage['current']:.1f}% (>70%)",
                "检查连接池复用和短连接风暴；设置连接数告警",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )
        elif conn and self._is_rising(metrics.get("mongodb_connections_current")):
            self._add_finding(
                "info",
                f"连接数持续上升，当前 {conn['current']:.0f}",
                "若 QPS 未同步上升，优先怀疑连接泄漏或连接池配置不当",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )

    def _analyze_replication(self, name, rid, instance_type, metrics):
        lag = self._stats(metrics.get("mongodb_repl_lag"))
        oplog = self._stats(metrics.get("mongodb_oplog_window"))
        if lag and lag["max"] > 60:
            self._add_finding(
                "critical",
                f"副本复制延迟峰值 {lag['max']:.1f}s (>60s)",
                "检查写入峰值、Secondary 读压力、网络抖动和磁盘 IOPS；必要时调整 readPreference 或扩容",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )
        elif lag and lag["max"] > 10:
            self._add_finding(
                "warning",
                f"副本复制延迟峰值 {lag['max']:.1f}s (>10s)",
                "关注持续性；关联 insert/update rate 与 Secondary 读流量",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )
        if oplog and oplog["current"] < 24:
            self._add_finding(
                "warning",
                f"Oplog window {oplog['current']:.1f}h (<24h)",
                "高写入场景下恢复窗口偏小；评估 oplog 容量和写入增长趋势",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )

    def _analyze_capacity_trend(self, name, rid, instance_type, metrics):
        disk_pts = metrics.get("mongodb_disk_usage")
        disk = self._stats(disk_pts)
        if not disk or len(disk_pts or []) < 4:
            return
        first = disk_pts[0][1]
        last = disk_pts[-1][1]
        growth = last - first
        if growth > 5 and last > 70:
            severity = "critical" if last > 85 and growth > 10 else "warning"
            self._add_finding(
                severity,
                f"磁盘使用率 {len(disk_pts)} 个采样点内上升 {growth:.1f}pp ({first:.1f}% → {last:.1f}%)",
                "按集合统计数据量/索引量增长；检查 TTL 是否生效；预测达到 90% 的剩余时间并提前扩容",
                name,
                rid,
                instance_type=instance_type,
                ops_skill="qcloud-mongodb-ops",
            )

    def _root_cause_high_cpu(self, metrics):
        query_rising = self._is_rising(metrics.get("mongodb_query_rate"))
        update_rising = self._is_rising(metrics.get("mongodb_update_rate"))
        latency_high = any(
            (self._stats(metrics.get(m)) or {}).get("max", 0) > 200
            for m in ["mongodb_read_latency", "mongodb_write_latency", "mongodb_command_latency"]
        )
        iops_rising = self._is_rising(metrics.get("mongodb_iops"))
        if latency_high and not query_rising:
            return "低效查询/缺索引导致单请求成本升高"
        if query_rising or update_rising:
            return "业务流量或应用发布引发读写放大"
        if iops_rising:
            return "磁盘 I/O 压力或批量扫描"
        return "需结合 slow query、currentOp 和发布变更进一步确认"

    def _rid(self, r):
        return r.get("instanceId") or r.get("mongodbInstanceId") or r.get("id")

    def _name(self, r, fallback):
        return r.get("instanceName") or r.get("name") or fallback

    def _stats(self, pts):
        if not pts:
            return None
        vals = [float(v) for _, v in pts if v is not None]
        if not vals:
            return None
        return {
            "current": vals[-1],
            "avg": sum(vals) / len(vals),
            "max": max(vals),
            "min": min(vals),
            "points": len(vals),
        }

    def _is_rising(self, pts, ratio=1.2, min_delta=1.0):
        if not pts or len(pts) < 4:
            return False
        vals = [float(v) for _, v in pts if v is not None]
        if len(vals) < 4:
            return False
        half = len(vals) // 2
        first = sum(vals[:half]) / half
        second = sum(vals[half:]) / (len(vals) - half)
        return second > first * ratio and (second - first) >= min_delta

    def _fmt(self, stats):
        return "-" if not stats else f"{stats['max']:.1f}"


register("mongodb", MongoDBAnalyzer)
