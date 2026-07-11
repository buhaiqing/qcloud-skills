"""
qcloud-proactive-inspection / scripts / 02-reason / analyzers / redis_analyzer.py
================================================================================
Redis cache analyzer.

Discovery: Redis instances tagged with target customer.
Metrics:  memory usage, hit rate, connections, CPU (if available).
Features: detects high-memory (OOM risk), low hit rate (cache miss / penetration).
"""

from . import register
from analyzers.base_analyzer import BaseAnalyzer
from lib.tags import tag_dict


class RedisAnalyzer(BaseAnalyzer):
    service_name = "redis"
    icon = "[缓存]"

    REDIS_METRICS = ["redis.memory.usage", "redis.hit_rate", "redis.connections", "redis.cpu.util"]

    def discover(self, topology: dict) -> list:
        return self.discover_by_tag(topology, "redis")

    def query_metrics(self, client, hours: int = 6) -> dict:
        return self.query_metrics_batch(
            client,
            id_field="cacheInstanceId",
            metrics=self.REDIS_METRICS,
            hours=hours,
            service_code="redis",
        )

    def analyze(self) -> list:
        self.findings = []
        for r in self.resources:
            rid = r.get("cacheInstanceId")
            name = r.get("cacheInstanceName") or rid or ""
            mem_mb = r.get("cacheInstanceMemoryMB", 0)
            tags = tag_dict(r)

            metrics = self.metrics.get(rid, {})

            # Memory usage
            mem = metrics.get("redis.memory.usage", [])
            if mem:
                last = mem[-1][1]
                if last > 85:
                    self._add_finding(
                        "critical",
                        f"内存使用率{last:.1f}% (规格{mem_mb}MB)",
                        "立即扩容或清理key",
                        resource=name,
                    )
                elif last > 75:
                    self._add_finding(
                        "warning",
                        f"内存使用率{last:.1f}%",
                        f"计划扩容或清理key (当前规格{mem_mb}MB, 已用{last * mem_mb / 100:.0f}MB)",
                        resource=name,
                    )

            # Memory trend (rising = OOM risk)
            if mem and len(mem) >= 6:
                first_half = sum(v for _, v in mem[: len(mem) // 2]) / (len(mem) // 2)
                second_half = sum(v for _, v in mem[len(mem) // 2 :]) / (len(mem) - len(mem) // 2)
                if second_half > first_half * 1.2 and second_half > 60:
                    self._add_finding(
                        "warning",
                        f"内存使用率持续上升 ({first_half:.1f}% → {second_half:.1f}%)",
                        "检查是否有大key或内存泄漏",
                        resource=name,
                    )

            # Hit rate
            hr = metrics.get("redis.hit_rate", [])
            if hr:
                avg_hr = sum(v for _, v in hr) / len(hr)
                if avg_hr < 80:
                    self._add_finding(
                        "warning",
                        f"缓存命中率{avg_hr:.1f}% (<80%)",
                        "检查是否存在缓存穿透、热key过期",
                        resource=name,
                    )
                elif avg_hr < 90:
                    self._add_finding("info", f"缓存命中率{avg_hr:.1f}%", "建议关注", resource=name)

            # Connections
            conn = metrics.get("redis.connections", [])
            if conn:
                avg_conn = sum(v for _, v in conn) / len(conn)
                if avg_conn > 9000:
                    self._add_finding(
                        "warning",
                        f"连接数{avg_conn:.0f}",
                        "检查是否有连接泄漏，考虑限制maxclients",
                        resource=name,
                    )

            # Eviction policy
            policy = r.get("maxmemoryPolicy", "unknown")
            if policy == "noeviction":
                self._add_finding(
                    "info",
                    "淘汰策略: noeviction (内存满时写入会失败)",
                    "建议改用volatile-lru或allkeys-lru",
                    resource=name,
                )

            # Version check
            ver = r.get("redisVersion", "")
            if ver and ver < "5.0":
                self._add_finding(
                    "info", f"Redis版本{ver}偏旧", "建议升级到5.0+以获得更好性能和安全性", resource=name
                )

            # Environment tag
            env = tags.get("环境", "")
            if env:
                self._add_finding("info", f"环境: {env}", "", resource=name)

        return self.findings


register("redis", RedisAnalyzer)
