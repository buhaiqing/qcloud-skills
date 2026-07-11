"""
qcloud-proactive-inspection / scripts / 02-reason / analyzers / rds_postgresql_analyzer.py
============================================================================================
RDS PostgreSQL Analyzer.

Performs health checks, slow query analysis, VACUUM status monitoring,
and replication lag detection for PostgreSQL instances.

Delegates to qcloud-postgres-ops skill for actual DB operations.
"""

from . import register
from .base_analyzer import BaseAnalyzer


# ── Thresholds (from references/threshold-definitions.md) ──

HEALTH_THRESHOLDS = {
    "cpu_util": {"warning": 70.0, "critical": 85.0},
    "memory_usage": {"warning": 80.0, "critical": 90.0},
    "storage_usage": {"warning": 75.0, "critical": 90.0},
    "connections_usage": {"warning": 70.0, "critical": 85.0},  # % of max_connections
    "active_connections": {"warning": 50, "critical": 80},
}

SLOW_QUERY_THRESHOLDS = {
    "critical": {"execution_time_ms": 5000, "rows_examined": 1000000},
    "major": {"execution_time_ms": 1000, "rows_examined": 100000},
    "minor": {"execution_time_ms": 200, "rows_examined": 10000},
}

REPLICATION_LAG_THRESHOLDS = {
    "critical": 60,  # seconds
    "major": 10,
    "minor": 1,
}

VACUUM_THRESHOLDS = {
    "dead_tuple_ratio": 10.0,  # %
    "max_vacuum_age_days": 7,
}

# Root cause patterns for PostgreSQL
ROOT_CAUSE_PATTERNS = {
    "missing_index": {
        "icon": "[分类]",
        "label": "Missing Index",
        "description": "Sequential scan detected, high rows examined vs returned",
    },
    "seq_scan_heavy": {
        "icon": "[指标]",
        "label": "Heavy Sequential Scan",
        "description": "Frequent sequential scans on large tables",
    },
    "lock_contention": {
        "icon": "[安全]",
        "label": "Lock Contention",
        "description": "High lock wait time detected",
    },
    "idle_in_transaction": {
        "icon": "[暂停]",
        "label": "Idle in Transaction",
        "description": "Connections idle in transaction for long time",
    },
    "vacuum_lag": {
        "icon": "[清理]",
        "label": "VACUUM Lag",
        "description": "Dead tuples accumulation exceeds threshold",
    },
    "connection_leak": {
        "icon": "[连接]",
        "label": "Connection Leak",
        "description": "Idle connections growing continuously",
    },
    "replication_lag": {
        "icon": "[延迟]",
        "label": "Replication Lag",
        "description": "Read replica lag exceeds threshold",
    },
}


class RdsPostgresqlAnalyzer(BaseAnalyzer):
    """RDS PostgreSQL Health and Performance Analyzer."""

    service_name = "rds_postgresql"
    icon = "[数据库]"

    def discover(self, topology: dict) -> list:
        """Extract PostgreSQL instances from topology."""
        self.topology = topology
        all_instances = topology.get("raw", {}).get("rds", [])

        # Filter PostgreSQL instances
        self.resources = [inst for inst in all_instances if inst.get("engine") == "PostgreSQL"]

        return self.resources

    def query_metrics(self, client, hours: int = 6) -> dict:
        """Query CloudMonitor metrics for PostgreSQL instances.

        Note: Detailed PostgreSQL metrics (pg_stat_statements, pg_stat_activity)
        require direct database access via qcloud-postgres-ops skill.
        """
        self.metrics = {}
        for instance in self.resources:
            instance_id = instance.get("instanceId")
            # Placeholder for CloudMonitor metrics
            # Real implementation would query:
            # - CPU, Memory, Storage, Connections
            self.metrics[instance_id] = {
                "cpu_util": [],
                "memory_usage": [],
                "storage_usage": [],
                "connections": [],
            }
        return self.metrics

    def _check_health_thresholds(self, instance: dict) -> list:
        """Check instance health against thresholds."""
        findings = []
        instance_id = instance.get("instanceId", "unknown")
        instance_name = instance.get("instanceName", "")

        # Get instance specs
        cpu = instance.get("instanceCPU", 0)
        memory_mb = instance.get("instanceMemoryMB", 0)
        storage_gb = instance.get("instanceStorageGB", 0)

        # Check storage (from instance spec vs usage would need CloudMonitor)
        # For now, generate info-level findings about basic info
        findings.append(
            {
                "resource": instance_name,
                "resource_id": instance_id,
                "resource_type": "rds_postgresql",
                "severity": "info",
                "message": f"PostgreSQL {instance.get('engineVersion', '')}, {cpu}vCPU, {memory_mb}MB, {storage_gb}GB",
                "action": "Health monitoring requires CloudMonitor metrics or DB direct access",
                "ops_skill": "qcloud-postgres-ops",
                "requires_confirmation": True,
            }
        )

        return findings

    def _check_slow_query_risk(self, instance: dict) -> list:
        """Check slow query risk indicators."""
        findings = []
        # Without direct DB access, we flag for delegation
        # Real implementation would check pg_stat_statements
        return findings

    def _check_vacuum_status(self, instance: dict) -> list:
        """Check VACUUM/ANALYZE status."""
        findings = []
        # Without direct DB access, we flag for delegation
        # Real implementation would check pg_stat_user_tables
        return findings

    def analyze(self) -> list:
        """Execute PostgreSQL health analysis."""
        findings = []

        for instance in self.resources:
            # Health check
            findings.extend(self._check_health_thresholds(instance))

            # Slow query check (placeholder)
            findings.extend(self._check_slow_query_risk(instance))

            # VACUUM status check (placeholder)
            findings.extend(self._check_vacuum_status(instance))

            # Add delegation reminder for deep analysis
            instance_id = instance.get("instanceId")
            instance_name = instance.get("instanceName", "")

            findings.append(
                {
                    "resource": instance_name,
                    "resource_id": instance_id,
                    "resource_type": "rds_postgresql",
                    "severity": "info",
                    "message": "Deep analysis (slow queries, VACUUM, locks) requires qcloud-postgres-ops",
                    "action": "Delegate to qcloud-postgres-ops for pg_stat_statements analysis",
                    "ops_skill": "qcloud-postgres-ops",
                    "requires_confirmation": True,
                }
            )

        self.findings = findings
        return findings


# Register the analyzer
register("rds_postgresql", RdsPostgresqlAnalyzer)
