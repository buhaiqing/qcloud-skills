# Cruise Report Format

> Output schema for the active inspection (cruise) mode of `qcloud-aiops-diagnosis`.

## Top-Level Structure

```json
{
  "metadata": { ... },
  "topology": { ... },
  "findings": [ ... ],
  "fingerprints": { ... },
  "capacity_forecast": { ... },
  "cruise_diff": { ... }
}
```

## `metadata`

```json
{
  "metadata": {
    "cruise_id": "cruise-20260727-001",
    "region": "ap-guangzhou",
    "timestamp": "2026-07-27T10:00:00+08:00",
    "duration_seconds": 42,
    "mode": "active_inspection",
    "version": "2.6.0"
  }
}
```

## `topology`

Same schema as `topology-discovery-workflow.md` output.

## `findings`

```json
{
  "findings": [
    {
      "finding_id": "f-001",
      "fingerprint_hash": "a3f5c2b7",
      "resource_id": "ins-123456",
      "resource_type": "cvm",
      "metric": "cpu_util",
      "anomaly": true,
      "level": "critical",
      "score": 0.87,
      "threshold": 0.72,
      "model": "IsolationForestDetector",
      "direction": "upper",
      "window_minutes": 60,
      "summary": "CPU utilization spike: current 94.2%, baseline 45±8%",
      "suppressed_by": [],
      "timestamp": "2026-07-27T10:00:00+08:00"
    }
  ]
}
```

## `fingerprints`

FingerprintRegistry export — see `finding-fingerprint.md`.

## `capacity_forecast`

```json
{
  "capacity_forecast": [
    {
      "resource_id": "ins-123456",
      "metric": "cpu_util",
      "horizon_days": 7,
      "forecast": {
        "predictions": [78.2, 79.1, 81.4, 83.7, 85.9, 87.2, 89.1],
        "lower": [72.1, 73.0, 75.3, 77.6, 79.8, 81.1, 83.0],
        "upper": [84.3, 85.2, 87.5, 89.8, 92.0, 93.3, 95.2],
        "confidence": 0.95,
        "model": "XGBoostCapacityPredictor"
      },
      "alerts": [
        {
          "resource_id": "ins-123456",
          "metric": "cpu_util",
          "threshold": 90.0,
          "forecast_value": 95.2,
          "horizon_steps": 7,
          "severity": "critical"
        }
      ]
    }
  ]
}
```

## `cruise_diff`

```json
{
  "cruise_diff": {
    "baseline_cruise_id": "cruise-20260720-001",
    "current_cruise_id": "cruise-20260727-001",
    "baseline_total_findings": 14,
    "current_total_findings": 9,
    "unique_findings": 6,
    "resolved_findings": 8,
    "new_findings": 3,
    "delta_by_type": {
      "cvm": { "baseline": 10, "current": 6, "delta": -4 },
      "clb": { "baseline": 4, "current": 3, "delta": -1 }
    }
  }
}
```
