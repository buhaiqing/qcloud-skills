from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any

from copilot.blackboard import BlackboardClient

SKILL_NAME = "qcloud-monitor-ops"
SKILL_VERSION = "1.3.0"

_SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "INFO": 4}


class AlertIntelRunner:
    """Analyze alarm history via tccli and write structured contribution to blackboard."""

    def analyze(
        self,
        params: dict[str, Any],
        blackboard: BlackboardClient,
        session_id: str,
    ) -> dict[str, Any]:
        alarms = params.get("alarm_history")
        if alarms is None:
            alarms = self._fetch_alarm_history(params)

        contribution = self._build_contribution(alarms, params)
        blackboard.write_contribution(session_id, SKILL_NAME, contribution)

        if contribution["verdict"] in ("WARNING", "CRITICAL"):
            blackboard.add_pending_action(
                session_id,
                {
                    "action": "invoke_skill",
                    "skill": "qcloud-proactive-inspection",
                    "reason": f"{contribution['verdict']} findings require targeted inspection",
                },
            )

        return contribution

    def _fetch_alarm_history(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        region = params.get("region_id", params.get("region", "ap-guangzhou"))
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=24)
        cmd = [
            "tccli",
            "monitor",
            "DescribeAlarmHistories",
            "--region",
            region,
            "--output",
            "json",
            "--StartTime",
            str(int(start.timestamp())),
            "--EndTime",
            str(int(end.timestamp())),
            "--Limit",
            str(params.get("page_size", 100)),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        if proc.returncode != 0 or not proc.stdout.strip():
            return []

        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return []

        histories = parsed.get("Response", {}).get("Histories") or []
        return list(histories)

    def _build_contribution(
        self,
        alarms: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        hints: set[str] = set()
        worst_rank = 99

        for idx, alarm in enumerate(alarms):
            resource_id = (
                alarm.get("Dimensions")
                and alarm["Dimensions"][0].get("Value")
                or alarm.get("InstanceId")
                or alarm.get("resourceId")
                or ""
            )
            if resource_id:
                hints.add(str(resource_id))

            severity = self._infer_severity(alarm, params)
            rank = _SEVERITY_RANK.get(severity, 4)
            worst_rank = min(worst_rank, rank)

            findings.append(
                {
                    "id": f"finding-{resource_id or idx}-{alarm.get('MetricName', 'alarm')}",
                    "severity": severity,
                    "summary": self._summarize(alarm),
                    "resource_id": resource_id,
                    "service_code": alarm.get("Namespace", ""),
                    "metric_name": alarm.get("MetricName", ""),
                }
            )

        verdict = self._verdict_from_rank(worst_rank if findings else 99)

        return {
            "version": SKILL_VERSION,
            "verdict": verdict,
            "findings": findings,
            "topology_hints": sorted(hints),
            "metadata": {
                "alarm_count": len(alarms),
                "time_window": params.get("time_window", "最近24h"),
                "severity_filter": params.get("severity_filter", ""),
            },
        }

    def _infer_severity(self, alarm: dict[str, Any], params: dict[str, Any]) -> str:
        explicit = alarm.get("severity") or alarm.get("level")
        if explicit in _SEVERITY_RANK:
            return explicit

        metric = (
            alarm.get("MetricName")
            or alarm.get("metricName")
            or alarm.get("Metric")
            or ""
        ).lower()
        if "cpu" in metric or "memory" in metric or "disk" in metric:
            return "P0"
        return "P1"

    def _summarize(self, alarm: dict[str, Any]) -> str:
        namespace = alarm.get("Namespace", "unknown")
        metric = alarm.get("MetricName", "metric")
        content = alarm.get("Content") or alarm.get("AlarmDescription") or ""
        return f"{namespace} {metric} 告警 {content}".strip()

    def _verdict_from_rank(self, rank: int) -> str:
        if rank <= _SEVERITY_RANK["P0"]:
            return "CRITICAL"
        if rank <= _SEVERITY_RANK["P1"]:
            return "WARNING"
        return "PASS"
