# AIOps Diagnosis Troubleshooting

Cross-product read-only diagnosis error taxonomy. Per-operation details: see [`cli-usage.md`](cli-usage.md). All recovery paths emit partial bundles with `data_quality.degraded=true` unless marked **HALT**.

> **Use API for latest error codes:** `Response.Error.Code` from any failed `tccli` call. Table below covers common cross-product codes during evidence collection.

## Error Code Reference (Diagnosis-Specific)

| Code | Typical API | Recovery |
|------|-------------|----------|
| `RequestLimitExceeded` | Monitor, CLS, TKE | Retry 2× exp backoff (2s, 4s); then degrade layer |
| `RequestLimitExceeded.UinLimitExceeded` | Monitor | Retry 2× (60s); cap metrics at `max_metrics_per_run` |
| `ResourceNotFound` | TKE, CVM, CDB | **HALT** if primary `cluster_id`/`resource_id` invalid |
| `ResourceNotFound.InstanceNotFound` | CVM | Skip CVM layer; warn in `missing_sources` |
| `ResourceNotFound.ClusterNotFound` | TKE | **HALT** Event/RCA bundle for TKE scope |
| `AuthFailure` | All | **HALT** — credentials invalid; never print secret |
| `UnauthorizedOperation` | CloudAudit, CLS | Skip layer; set `evidence_by_layer.*.status=unavailable` |
| `UnauthorizedOperation.CamUnauthorized` | Any | Skip layer; delegate CAM fix to `qcloud-cam-ops` |
| `InvalidParameter` | Monitor, CLS | Fix param per API spec; retry once |
| `InvalidParameterValue` | GetMonitorData | Run `DescribeBaseMetrics`; fix Namespace/MetricName |
| `MissingParameter` | CLS SearchLog | **HALT** if required `TopicId` missing for log-scoped request |
| `InternalError` | Any | Retry 3× (2s, 4s, 8s); degrade layer if persists |
| `FailedOperation` | TKE, CLB | Retry 1×; record RequestId in trace |
| `UnsupportedOperation` | Product API | Skip method; use alternate read-only path |
| `NoData` | GetMonitorData empty `Values` | Baseline unavailable → `static_only` fallback |
| `ResourceUnavailable` | CLS topic | Skip CLS layer; lower confidence |
| `LimitExceeded` | DescribeAlarmHistories pagination | Paginate per [`cli-usage.md`](cli-usage.md#alarm-history-pagination) |

## Partial Data Recovery

| Condition | Action |
|-----------|--------|
| CLS topic unavailable | Skip `cls_events`; continue RCA with alarm + inventory |
| CloudAudit disabled | Skip `change_events`; note in `data_quality.warnings` |
| Pod evidence gap (no topic, no filters) | Use alarm dimensions only; confidence ≤ MEDIUM |
| Baseline window > 24h | **HALT** baseline mode; use `static_only` per [`anomaly-detection.md`](anomaly-detection.md) |
| Alarm count > `max_alarms_per_cluster` | Paginate then truncate with warning |
| All evidence layers unavailable | **HALT** — return error with required inputs list |

## Diagnostic Checklist (Pre-flight)

1. `{{env.TENCENTCLOUD_SECRET_ID}}` / `{{env.TENCENTCLOUD_SECRET_KEY}}` set (masked in output)
2. `{{env.TENCENTCLOUD_REGION}}` matches resource region
3. Time window: ISO → epoch for Monitor/CLS (`{{user.time_start_epoch}}`, `{{user.time_end_epoch}}`)
4. Primary ID present: `cluster_id` (TKE) or `resource_id` (single-product)
5. Read-only boundary: no `Create*` / `Modify*` / `Delete*` in trace

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-13 | Initial release — ≥15 cross-product error codes, partial-data recovery, pre-flight checklist |
