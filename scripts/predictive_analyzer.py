#!/usr/bin/env python3
"""predictive_analyzer.py — Capacity forecasting for cloud resources.

Implements linear regression and moving-average forecasting for proactive
capacity alerts (disk exhaustion, memory saturation, etc.) based on
GetMonitorData historical series.

Usage:
  python3 scripts/predictive_analyzer.py forecast \\
      --namespace QCE/CVM --metric DiskUsage \\
      --instance-id ins-xxx --region ap-guangzhou \\
      --history-days 7 --threshold 90

  python3 scripts/predictive_analyzer.py batch --input metrics.json
  python3 scripts/predictive_analyzer.py self-verify
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Prediction methods
# ---------------------------------------------------------------------------

def linear_regression_predict(historical_data: list[float]) -> dict[str, Any]:
    """Fit OLS linear regression and return model + 1-step-ahead prediction."""
    if len(historical_data) < 3:
        raise ValueError("Linear regression requires >= 3 points")
    n = len(historical_data)
    x = list(range(n))
    y = historical_data
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    num = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    den = sum((x[i] - x_mean) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0.0
    intercept = y_mean - slope * x_mean
    y_pred = [slope * x[i] + intercept for i in range(n)]
    ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
    r_sq = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
    # Predict 1 horizon step ahead
    predicted = slope * n + intercept
    return {
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r_squared": round(r_sq, 4),
        "predicted_value": round(predicted, 4),
        "method": "linear_regression",
    }


def moving_average_predict(historical_data: list[float], window: int = 7) -> float:
    """Weighted moving average — recent values weighted more heavily."""
    if not historical_data:
        raise ValueError("No data provided")
    w = min(window, len(historical_data))
    vals = historical_data[-w:]
    weights = list(range(1, w + 1))
    weighted_sum = sum(vals[i] * weights[i] for i in range(w))
    return weighted_sum / sum(weights)


def exponential_smoothing_predict(
    data: list[float], alpha: float = 0.3, beta: float = 0.1
) -> dict[str, float]:
    """Holt's linear exponential smoothing — captures trend without explicit seasonality."""
    if len(data) < 2:
        return {"level": float(data[0]) if data else 0.0, "trend": 0.0}
    level = float(data[0])
    trend = float(data[1]) - float(data[0])
    for val in data[1:]:
        val_f = float(val)
        last_level = level
        level = alpha * val_f + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend
    return {
        "level": round(level, 4),
        "trend": round(trend, 4),
        "predicted_value": round(level + trend, 4),
        "method": "exponential_smoothing",
    }


# ---------------------------------------------------------------------------
# Data preprocessing
# ---------------------------------------------------------------------------

def _rolling_avg(data: list[float], w: int) -> list[float]:
    return [sum(data[max(0, i - w + 1):i + 1]) / min(i + 1, w) for i in range(len(data))]


def _rolling_std(data: list[float], w: int) -> list[float]:
    avgs = _rolling_avg(data, w)
    return [
        math.sqrt(sum((data[j] - avgs[i]) ** 2 for j in range(max(0, i - w + 1), i + 1))
                  / min(i + 1, w))
        for i in range(len(data))
    ]


def preprocess_data(data: list[float]) -> list[float]:
    """Clean: remove outliers (3σ), then 3-point moving-average smooth."""
    if len(data) < 3:
        return [x for x in data if x is not None and not math.isnan(x)]
    # Drop NaN
    cleaned = [x for x in data if x is not None and not math.isnan(x)]
    if len(cleaned) < 3:
        return cleaned
    w = min(5, len(cleaned))
    avg = _rolling_avg(cleaned, w)
    std = _rolling_std(cleaned, w)
    filtered = []
    for i, val in enumerate(cleaned):
        center, s = avg[i], std[i]
        if abs(val - center) <= 3 * max(s, 0.001):
            filtered.append(val)
        else:
            filtered.append(center)  # replace outlier with rolling avg
    # 3-point smoothing
    if len(filtered) < 3:
        return filtered
    smoothed = []
    for i in range(len(filtered)):
        if i == 0:
            smoothed.append((filtered[0] + filtered[1]) / 2)
        elif i == len(filtered) - 1:
            smoothed.append((filtered[-2] + filtered[-1]) / 2)
        else:
            smoothed.append((filtered[i - 1] + filtered[i] + filtered[i + 1]) / 3)
    return smoothed


# ---------------------------------------------------------------------------
# Core forecasting
# ---------------------------------------------------------------------------

def time_to_exhaustion(
    current: float, slope: float, threshold: float
) -> tuple[float | None, str | None]:
    """Hours/days until metric reaches threshold. Returns (value, unit) or (None, None)."""
    if slope <= 0:
        return None, None
    remaining = threshold - current
    if remaining <= 0:
        return 0.0, "hours"
    hours = remaining / slope
    return (round(hours, 1), "hours") if hours < 24 else (round(hours / 24, 1), "days")


ALERT_RECS = {
    "disk_exhaustion": "Expand disk or clean up data",
    "memory_exhaustion": "Optimize memory usage or scale up",
    "cpu_saturation": "Review workload and consider scaling",
    "network_saturation": "Optimize network usage or increase bandwidth",
}


def _classify_trend(slope: float) -> str:
    a = abs(slope)
    if a <= 0.01:
        return "stable"
    return "increasing" if slope > 0 else "decreasing"


def predict_capacity(
    historical_data: list[float],
    metric_name: str,
    threshold_pct: float,
    entity_id: str,
) -> dict[str, Any]:
    """Predict when a metric will hit threshold.

    Selection: linear regression (R² >= 0.7) → exponential smoothing (|trend| > 0.01)
             → moving average fallback.
    """
    current = historical_data[-1] if historical_data else 0.0

    if len(historical_data) < 3:
        predicted = moving_average_predict(historical_data)
        method, r_sq, slope = "moving_average", None, 0.0
        trend = "unknown"
    else:
        cleaned = preprocess_data(historical_data)
        try:
            lr = linear_regression_predict(cleaned)
            r_sq = lr["r_squared"]
            if r_sq >= 0.7:
                slope = lr["slope"]
                predicted = lr["predicted_value"]
                method = "linear_regression"
                trend = _classify_trend(slope)
            else:
                es = exponential_smoothing_predict(cleaned)
                if abs(es["trend"]) > 0.01:
                    slope = es["trend"]
                    predicted = es["predicted_value"]
                    method = "exponential_smoothing"
                    trend = _classify_trend(slope)
                else:
                    predicted = moving_average_predict(cleaned)
                    method, r_sq, slope = "moving_average", None, 0.0
                    trend = "stable"
        except Exception:
            predicted = moving_average_predict(cleaned)
            method, r_sq, slope = "moving_average", None, 0.0
            trend = "unknown"

    predicted = max(0.0, min(100.0, predicted))

    # Confidence interval
    if r_sq is not None and r_sq > 0 and len(historical_data) >= 5:
        ci_width = (1.0 - r_sq) * 20
        conf_int = {
            "lower": round(max(0, predicted - ci_width), 2),
            "upper": round(min(100, predicted + ci_width), 2),
        }
        conf_level = round(r_sq, 3)
    else:
        conf_int = {
            "lower": round(predicted * 0.9, 2),
            "upper": round(min(100, predicted * 1.1), 2),
        }
        conf_level = 0.5

    # Severity + time to exhaustion
    tte_val, tte_unit = time_to_exhaustion(current, slope, threshold_pct)
    exhaustion_str = f"{tte_val}{tte_unit}" if tte_val is not None else "unknown"

    if predicted >= threshold_pct:
        if tte_val is not None and tte_val <= 3:
            severity = "CRITICAL"
        elif tte_val is not None and tte_val <= 7:
            severity = "HIGH"
        else:
            severity = "MEDIUM"
        exhaustion_date = (
            (datetime.now(timezone.utc)
             + timedelta(hours=tte_val * 24 if tte_unit == "days" else tte_val))
            .strftime("%Y-%m-%dT%H:%M:%S+08:00")
        )
    else:
        severity = "LOW" if tte_val is None or tte_val > 7 else "MEDIUM"
        exhaustion_date = None

    # Alert type
    ml = metric_name.lower()
    if "disk" in ml or "storage" in ml:
        alert_type = "disk_exhaustion"
    elif "mem" in ml:
        alert_type = "memory_exhaustion"
    elif "cpu" in ml:
        alert_type = "cpu_saturation"
    elif "network" in ml or "bandwidth" in ml:
        alert_type = "network_saturation"
    else:
        alert_type = "resource_threshold"

    rec = ALERT_RECS.get(alert_type, "Review resource usage")
    priority = 1 if severity == "CRITICAL" else 2 if severity == "HIGH" else 3

    return {
        "source": "prediction",
        "signal": "capacity_forecast",
        "metric_or_pattern": metric_name,
        "entity_id": entity_id,
        "current": {"value": round(current, 2), "unit": "%"},
        "prediction": {
            "method": method,
            "predicted_value": round(predicted, 2),
            "predicted_unit": "%",
            "confidence_interval": conf_int,
            "confidence_level": conf_level,
            "trend": trend,
            "slope": round(slope, 4),
            "r_squared": r_sq,
        },
        "capacity_alert": {
            "alert_type": alert_type,
            "severity": severity,
            "time_to_exhaustion": exhaustion_str,
            "exhaustion_date": exhaustion_date,
            "recommended_action": f"RECOMMENDATION (not execution): {rec}",
            "priority": priority,
        },
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

_DIM_MAP = {
    "QCE/CVM": "InstanceId",
    "QCE/REDIS": "instanceid",
    "QCE/CDB": "instanceId",
    "QCE/LB": "loadBalancerId",
    "QCE/TKE": "clusterid",
    "QCE/COS": "bucket",
    "QCE/CKAFKA": "InstanceId",
    "QCE/CMONGO": "target",
    "QCE/POSTGRES": "DBInstanceId",
    "QCE/SCF": "FunctionName",
    "QCE/CDN": "Domain",
}


def _dim_name(ns: str) -> str:
    return _DIM_MAP.get(ns, "InstanceId")


def _iso_range(days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")


def _period(days: int) -> int:
    return 60 if days <= 1 else 300 if days <= 7 else 3600 if days <= 30 else 86400


def _fetch(namespace: str, metric: str, inst_id: str, region: str,
           start: str, end: str, period: int) -> list[float]:
    inst_json = json.dumps([{"Dimensions": [{"Name": _dim_name(namespace), "Value": inst_id}]}])
    cmd = ["tccli", "monitor", "GetMonitorData",
           "--Namespace", namespace, "--MetricName", metric,
           "--Instances", inst_json,
           "--StartTime", start, "--EndTime", end, "--Period", str(period)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                          env={**subprocess.os.environ, "TCLOUD_OUTPUT_FORMAT": "json"})
        if r.returncode != 0:
            return []
        dps = json.loads(r.stdout).get("Response", {}).get("DataPoints", [])
        if dps and dps[0].get("Values"):
            return [float(v) for v in dps[0]["Values"]]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# CLI subcommands
# ---------------------------------------------------------------------------

def cmd_forecast(args: argparse.Namespace) -> int:
    start, end = _iso_range(args.history_days)
    data = _fetch(args.namespace, args.metric, args.instance_id,
                  args.region, start, end, _period(args.history_days))
    if not data:
        print("ERROR: No metric data. Check credentials and resource ID.", file=sys.stderr)
        return 1
    result = predict_capacity(data, args.metric, args.threshold, args.instance_id)
    if args.output:
        with open(args.output, "w") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        a = result["capacity_alert"]
        p = result["prediction"]
        print(f"[{a['severity']}] {args.metric} for {args.instance_id}")
        print(f"  Current: {result['current']['value']}%  →  Predicted: {p['predicted_value']}%")
        print(f"  Method: {p['method']}  R²={p.get('r_squared','N/A')}  Trend={p['trend']}")
        print(f"  TTE: {a['time_to_exhaustion']}  Action: {a['recommended_action']}")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    specs = json.loads(Path(args.input).read_text())
    results = []
    for s in specs:
        data = _fetch(s["namespace"], s["metric"], s["instance_id"],
                      s.get("region", "ap-guangzhou"),
                      *_iso_range(s.get("history_days", 7)),
                      _period(s.get("history_days", 7)))
        if not data:
            results.append({"instance_id": s["instance_id"], "metric": s["metric"], "error": "no_data"})
        else:
            results.append(predict_capacity(data, s["metric"],
                               s.get("threshold", 90.0), s["instance_id"]))
    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2, ensure_ascii=False))
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            if "error" in r:
                print(f"[ERROR] {r['instance_id']}/{r['metric']}: {r['error']}")
            else:
                a, p = r["capacity_alert"], r["prediction"]
                print(f"[{a['severity']}] {r['entity_id']}/{r['metric_or_pattern']}: "
                      f"now={r['current']['value']}% → pred={p['predicted_value']}% "
                      f"(@ {p['method']}, TTE={a['time_to_exhaustion']})")
    return 0


# ---------------------------------------------------------------------------
# Self-verification
# ---------------------------------------------------------------------------

def self_verify() -> bool:
    cases = [
        ("Linear up", [60, 62, 64, 66, 68, 70, 72], "DiskUsage", 90, "increasing"),
        ("Linear stable", [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0], "CpuUsage", 80, "stable"),
        ("Short data", [70, 75], "MemUsage", 90, "unknown"),
        ("Exponential", [10, 15, 22, 30, 40], "NetworkOut", 80, "increasing"),
    ]
    ok = True
    for name, data, metric, threshold, expected in cases:
        try:
            r = predict_capacity(data, metric, threshold, "test-ins")
            t = r["prediction"]["trend"]
            passed = t == expected
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}: "
                  f"trend={t} (expected {expected})")
            if not passed:
                ok = False
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            ok = False
    # Unit tests
    lr = linear_regression_predict([1.0, 2.0, 3.0, 4.0, 5.0])
    lr_ok = abs(lr["slope"] - 1.0) < 0.001 and abs(lr["intercept"] - 1.0) < 0.001
    print(f"  [{'PASS' if lr_ok else 'FAIL'}] linear_regression: slope={lr['slope']} intercept={lr['intercept']}")
    if not lr_ok:
        ok = False
    ma = moving_average_predict([10, 20, 30, 40, 50])
    ma_ok = 30 < ma < 40
    print(f"  [{'PASS' if ma_ok else 'FAIL'}] moving_average: result={ma:.2f} (expected ~35)")
    if not ma_ok:
        ok = False
    es = exponential_smoothing_predict([10, 12, 14, 16, 18])
    es_ok = es["level"] > 10
    print(f"  [{'PASS' if es_ok else 'FAIL'}] exponential_smoothing: level={es['level']:.2f}")
    if not es_ok:
        ok = False
    return ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    fc = sub.add_parser("forecast", help="Forecast one resource")
    fc.add_argument("--namespace", required=True)
    fc.add_argument("--metric", required=True)
    fc.add_argument("--instance-id", required=True)
    fc.add_argument("--region", default="ap-guangzhou")
    fc.add_argument("--history-days", type=int, default=7)
    fc.add_argument("--threshold", type=float, default=90.0)
    fc.add_argument("--output")
    fc.add_argument("--json", action="store_true")
    fc.set_defaults(func=cmd_forecast)
    bc = sub.add_parser("batch", help="Batch forecast from JSON file")
    bc.add_argument("--input", required=True, type=Path)
    bc.add_argument("--output")
    bc.add_argument("--json", action="store_true")
    bc.set_defaults(func=cmd_batch)
    sv = sub.add_parser("self-verify")
    sv.set_defaults(func=lambda _: 0 if self_verify() else 1)
    return p


def main() -> int:
    return build_parser().parse_args().func(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
