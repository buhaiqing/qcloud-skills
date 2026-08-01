# Copyright (c) 2026. All rights reserved.
"""Thin tccli wrapper for proactive-inspection metric queries (best-effort)."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from typing import Any


def _run_tccli(product: str, operation: str, region: str, extra: list[str] | None = None) -> dict:
    cmd = ["tccli", product, operation, "--region", region, "--output", "json"]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}
    try:
        return json.loads(proc.stdout).get("Response", {})
    except json.JSONDecodeError:
        return {}


class TccliClient:
    """Minimal tccli-backed client used by analyzers.

    Metric queries are best-effort: any failure yields an empty result so
    analyzers degrade gracefully instead of aborting the run.
    """

    def __init__(self, region: str) -> None:
        self.region = region

    def get_metrics_batch(
        self,
        resource_id: str,
        metrics: list[str],
        *,
        hours: int = 6,
        region: str | None = None,
        service_code: str = "vm",
    ) -> dict[str, list[tuple[int, float]]]:
        region = region or self.region
        end = datetime.now(UTC)
        start = end - timedelta(hours=hours)
        fmt = "%Y-%m-%dT%H:%M:%S%z"
        instances = json.dumps(
            [{"Dimensions": [{"Name": "InstanceId", "Value": resource_id}]}],
            ensure_ascii=False,
        )
        result: dict[str, list[tuple[int, float]]] = {}
        for metric in metrics:
            resp = _run_tccli(
                "monitor",
                "GetMonitorData",
                region,
                [
                    "--Namespace",
                    f"QCE/{service_code}",
                    "--MetricName",
                    metric,
                    "--Instances",
                    instances,
                    "--Period",
                    "300",
                    "--StartTime",
                    start.strftime(fmt),
                    "--EndTime",
                    end.strftime(fmt),
                ],
            )
            points = self._parse_data_points(resp)
            if points:
                result[metric] = points
        return result

    def list_clusters(self) -> list[dict[str, Any]]:
        resp = _run_tccli("tke", "DescribeClusters", self.region)
        clusters = resp.get("Clusters")
        return clusters if isinstance(clusters, list) else []

    @staticmethod
    def _parse_data_points(resp: dict) -> list[tuple[int, float]]:
        points: list[tuple[int, float]] = []
        for dp in resp.get("DataPoints") or []:
            timestamps = dp.get("Timestamps") or []
            values = dp.get("Values") or []
            for ts, value in zip(timestamps, values):
                try:
                    points.append((int(ts), float(value)))
                except (TypeError, ValueError):
                    continue
        return points
