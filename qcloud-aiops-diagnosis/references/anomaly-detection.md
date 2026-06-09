# Dynamic Baseline Anomaly Detection

> **Read-only metric analysis.** Supplements static thresholds (`example-config.yaml` `thresholds`) with **multi-window baselines** (current vs yesterday vs last week), percentile deviation, and slope change. No ML service required — Agent computes scores from `GetMonitorData` responses.

## 1. Anomaly Evidence Model

Extend the Multi-Source RCA evidence fragment ([`multi-source-rca.md`](multi-source-rca.md) §1) with baseline fields:

```json
{
  "source": "monitor",
  "signal": "metric_anomaly",
  "metric_or_pattern": "CpuUsage",
  "namespace": "QCE/CVM",
  "entity_id": "ins-xxx",
  "entity_type": "cvm_instance",
  "current": {"p50": 45, "p95": 78, "max": 82, "unit": "%"},
  "baselines": {
    "yesterday_same_window": {"p50": 42, "p95": 48, "max": 52},
    "last_week_same_window": {"p50": 40, "p95": 46, "max": 50}
  },
  "deviation": {
    "vs_yesterday_p95_ratio": 1.63,
    "vs_week_p95_ratio": 1.70,
    "vs_yesterday_max_delta": 30,
    "slope_spike": true
  },
  "anomaly_score": 68,
  "anomaly_severity": "HIGH",
  "detection_method": "baseline_ratio|percentile|slope|static_fallback",
  "confidence": "HIGH|MEDIUM|LOW",
  "timestamp": "2026-06-09T10:00:00+08:00",
  "window_start": "2026-06-09T10:00:00+08:00",
  "window_end": "2026-06-09T11:00:00+08:00",
  "static_threshold_breach": false,
  "linkage": {"instance_id": "ins-xxx"}
}
```

### JSON Paths (centralized)

| Field | Path in `GetMonitorData` response |
|---|---|
| Datapoint values | `DataPoints[0].Values[]` |
| Timestamps | `DataPoints[0].Timestamps[]` |
| Metric name | request `MetricName` |
| Namespace | request `Namespace` |

> **TE-1:** Metric names and namespaces change. Run `tccli monitor DescribeBaseMetrics --Namespace <ns>` before relying on defaults below.

## 2. Detection Pipeline

```
Resolve target metrics (product catalog §5)
  → Fetch current window (GetMonitorData)
  → Fetch yesterday same window (-24h shift)
  → Fetch last week same window (-7d shift)
  → Compute p50/p95/max per window
  → Score anomaly (§4)
  → Emit Anomaly Finding or Anomaly Bundle (§6)
```

**API budget:** Max **3 queries per metric** (current + yesterday + week). For multi-metric scans, cap at `anomaly_detection.max_metrics_per_run` (default 6). On rate limit, retry once; then degrade to static thresholds only.

### Window shift rules

| User window | `time_start` / `time_end` | Yesterday baseline | Week baseline |
|---|---|---|---|
| Current | `{{user.time_start}}` → `{{user.time_end}}` | start − 24h, end − 24h | start − 7d, end − 7d |

Convert ISO windows to the format `GetMonitorData` accepts (same as existing [`cli-usage.md`](cli-usage.md)). Store epoch variants in `{{user.baseline_yesterday_start}}` etc. when pre-computed.

### Period selection

| Diagnosis window length | `Period` (seconds) |
|---|---|
| ≤ 1h | 60 |
| 1h – 6h | 300 |
| 6h – 24h | 600 |

## 3. Detection Methods

### 3.1 Baseline ratio (primary)

Flag when **current p95** exceeds baseline p95 by configurable ratio **and** absolute value is meaningful:

```
ratio_y = current.p95 / max(yesterday.p95, 1)
ratio_w = current.p95 / max(week.p95, 1)

anomaly if (ratio_y >= deviation_ratio_warning OR ratio_w >= deviation_ratio_warning)
         AND current.p95 >= min_absolute_floor
```

Default `deviation_ratio_warning`: 1.5 (see `example-config.yaml`).

**Suppress false positives:** If static threshold NOT breached AND `current.p95 < static.warning`, downgrade severity one level unless `ratio >= deviation_ratio_critical` (default 2.0).

### 3.2 Percentile deviation

When baseline data is sparse (< 5 datapoints), use max instead of p95:

```
delta = current.max - max(yesterday.max, week.max)
anomaly if delta >= absolute_delta_warning (default 15 for % metrics)
```

### 3.3 Slope spike (change-point lite)

On current window datapoints sorted by time:

```
slope_recent = mean(diff(last 3 values))
slope_baseline = median(diff(all values))

slope_spike = slope_recent >= 2 * max(slope_baseline, epsilon)
```

Adds +10 to anomaly score when true (§4).

### 3.4 Static fallback

When yesterday AND week baselines unavailable (`NoData`, empty `Values`, or API error):

- Set `detection_method=static_fallback`
- Apply `thresholds.*` from config
- Set `confidence=LOW`; add warning `baseline_unavailable`

## 4. Anomaly Score (0–100)

| Component | Max points | Formula |
|---|---|---|
| vs yesterday p95 ratio | 40 | `min(40, (ratio_y - 1) * 40)` when `ratio_y > 1` |
| vs week p95 ratio | 30 | `min(30, (ratio_w - 1) * 30)` when `ratio_w > 1` |
| Static critical breach | 20 | +20 if `current.max >= thresholds.*.critical` |
| Slope spike | 10 | +10 if `slope_spike` |

| anomaly_severity | Score range | Action |
|---|---|---|
| CRITICAL | ≥ 70 | Immediate correlation with logs/alarms; RCA if user reports incident |
| HIGH | 50–69 | Correlate 2+ metrics; surface in proactive scan |
| MEDIUM | 30–49 | Monitor; include in Anomaly Bundle digest |
| LOW | < 30 | Informational only |

Integrate into RCA hypothesis scoring: **+1** per HIGH+ anomaly on root entity; **+2** if anomaly precedes alarm by ≤ 10 min.

## 5. Product Metric Catalog (defaults)

> Use API for latest. Query: `tccli monitor DescribeBaseMetrics --Namespace <ns>`.

| resource_type | Namespace | Metrics to scan (priority order) |
|---|---|---|
| `cvm` | `QCE/CVM` | `CpuUsage`, `MemUsage`, `DiskUsage`, `NetworkIn`, `NetworkOut` |
| `redis` | `QCE/REDIS` | `CpuUs`, `Storage`, `Connections`, `InFlow`, `OutFlow` |
| `cdb` | `QCE/CDB` | `CpuUseRate`, `VolumeRate`, `Qps`, `SlowQueries` |
| `clb` | `QCE/LB` | `ClientConnum`, `UnhealthNum`, `DropTotal`, `Intraffic`, `Outtraffic` |
| `tke` | `QCE/TKE` | `cluster_cpu_usage`, `cluster_mem_usage`, `cluster_running_nodes` |
| `es` | `QCE/CES` | `indexing_latency`, `jvm_mem_usage`, `cpu_usage` |

Dimensions: CVM `InstanceId`; Redis `instanceid`; CDB `instanceId`; CLB `loadBalancerId`; TKE `clusterid`.

## 6. Anomaly Bundle Output Schema

For proactive scans and standalone anomaly requests:

```json
{
  "anomaly_bundle_id": "anom-20260609-001",
  "resource_type": "cvm",
  "resource_id": "ins-xxx",
  "diagnosis_window": "1h",
  "detection_mode": "baseline_primary",
  "findings": [],
  "summary": {
    "total_metrics_scanned": 5,
    "anomalies_detected": 2,
    "highest_severity": "HIGH",
    "highest_score": 68
  },
  "data_quality": {
    "status": "complete|partial",
    "baseline_coverage": {"yesterday": true, "last_week": true},
    "degraded_metrics": [],
    "warnings": []
  },
  "recommendations": [
    {
      "action": "RECOMMENDATION (not execution): correlate CpuUsage anomaly with NetworkIn and CLS error logs",
      "delegate_to": "qcloud-cvm-ops",
      "priority": "P1"
    }
  ],
  "incident_timeline_ref": null
}
```

Embed condensed findings in RCA Bundle:

```json
"anomaly_findings": [
  {"metric": "CpuUsage", "anomaly_score": 68, "anomaly_severity": "HIGH", "vs_yesterday_p95_ratio": 1.63}
]
```

## 7. CLI Collection (multi-window)

See [`cli-usage.md`](cli-usage.md#dynamic-baseline-metric-windows). Pattern for CVM `CpuUsage`:

```bash
# Current window
tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName CpuUsage \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" \
  --EndTime "{{user.time_end}}" \
  --Period 300

# Yesterday same window (shift -24h; use derived ISO timestamps)
tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName CpuUsage \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.baseline_yesterday_start}}" \
  --EndTime "{{user.baseline_yesterday_end}}" \
  --Period 300
```

Repeat for `{{user.baseline_week_start}}` / `{{user.baseline_week_end}}` (−7d shift).

## 8. Degraded Behavior

| Condition | Behavior |
|---|---|
| Yesterday missing, week OK | Score using week only; `confidence=MEDIUM` |
| Both baselines missing | `static_fallback`; warn in bundle |
| `InvalidParameterValue` namespace/metric | Skip metric; list in `degraded_metrics` |
| Window > 24h | HALT baseline mode; static thresholds only |
| Rate limit | Retry once; then scan fewer metrics |

## 9. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-09 | Initial release — Anomaly Evidence Model, multi-window baselines, ratio/percentile/slope detection, anomaly score, product metric catalog, Anomaly Bundle schema |
