# Copyright (c) 2026. All rights reserved.
"""Thin tccli wrapper for proactive-inspection metric queries (best-effort)."""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _run_tccli(product: str, operation: str, region: str, extra: list[str] | None = None) -> dict:
    """Run a tccli query. Failures return ``{"_error": ...}`` instead of ``{}``.

    An empty dict is indistinguishable from "no resources", so auth failures and
    throttling used to look like healthy empty inventories.
    """
    cmd = ["tccli", product, operation, "--region", region, "--output", "json"]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
    if proc.returncode != 0:
        logger.warning(
            "tccli %s %s failed (rc=%s): %s", product, operation, proc.returncode,
            (proc.stderr or "").strip()[:200],
        )
        return {"_error": f"rc={proc.returncode}", "_stderr": (proc.stderr or "")[:200]}
    if not proc.stdout.strip():
        return {}
    try:
        resp = json.loads(proc.stdout).get("Response", {})
    except json.JSONDecodeError:
        logger.warning("tccli %s %s returned non-JSON output", product, operation)
        return {"_error": "InvalidJSON"}
    if "Error" in resp:
        code = resp["Error"].get("Code", "Unknown")
        logger.warning("tccli %s %s API error: %s", product, operation, code)
        return {"_error": code, "_stderr": (proc.stderr or "")[:200]}
    return resp


def _raise_on_error(resp: dict) -> None:
    """Turn the ``_error`` sentinel into an exception.

    Callers must not silently treat a failed query as "no resources"; each
    consumer decides whether to propagate or degrade explicitly.
    """
    if "_error" in resp:
        raise RuntimeError(f"tccli failed: {resp['_error']}")


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
            # Metric queries degrade per-metric on purpose (see class docstring),
            # but the failure is now logged instead of masquerading as no data.
            try:
                points = self._parse_data_points(resp)
            except RuntimeError as exc:
                logger.warning("metric %s unavailable for %s: %s", metric, resource_id, exc)
                continue
            if points:
                result[metric] = points
        return result

    def list_clusters(self) -> list[dict[str, Any]]:
        resp = _run_tccli("tke", "DescribeClusters", self.region)
        _raise_on_error(resp)
        clusters = resp.get("Clusters")
        return clusters if isinstance(clusters, list) else []

    @staticmethod
    def _parse_data_points(resp: dict) -> list[tuple[int, float]]:
        _raise_on_error(resp)
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
