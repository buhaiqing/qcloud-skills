# AIOps Diagnosis CLI Usage

This cross-cutting diagnosis skill is **CLI-first with SDK fallback**. All commands here are read-only. **SDK paths:** [`api-sdk-usage.md`](api-sdk-usage.md).

## Preconditions

- Credentials are read from environment only; never print secret values.
- Convert ISO windows to Unix epoch seconds for Monitor alarm history and CLS search:
  - `{{user.time_start}}` / `{{user.time_end}}` → `{{user.time_start_epoch}}` / `{{user.time_end_epoch}}`.
- If optional IDs are unavailable, skip that source and set `data_quality.degraded=true` in the Event Bundle.

## CLI Collection Commands

### Monitor alarm history

```bash
tccli monitor DescribeAlarmHistories \
  --Module monitor \
  --Namespaces '[{"MonitorType":"MT_QCE","Namespace":"QCE/TKE"}]' \
  --StartTime {{user.time_start_epoch}} \
  --EndTime {{user.time_end_epoch}} \
  --PageNumber 1 \
  --PageSize 100
```

### Alarm history pagination

Storm windows may exceed one page. Loop until `TotalCount` satisfied or cap reached:

1. Start `PageNumber=1`, `PageSize=100`.
2. Append `Histories[]` to in-memory collection.
3. If `len(collected) >= TotalCount` OR `len(collected) >= max_alarms_per_cluster` (default 100 from `example-config.yaml`) → stop.
4. Else `PageNumber++`, retry; on `LimitExceeded` → wait 2s, retry once per [`troubleshooting.md`](troubleshooting.md).
5. If truncated at cap, set `data_quality.warnings[]`: `"alarm history truncated at max_alarms_per_cluster"`.

SDK fallback: same loop — see [`api-sdk-usage.md`](api-sdk-usage.md#sdk-example-monitor-alarm-history-with-pagination).

### Metric metadata and metric data

Use API for latest metric names/dimensions before relying on defaults:

```bash
tccli monitor DescribeAllNamespaces --Region {{env.TENCENTCLOUD_REGION}} --Module monitor --SceneType ST_ALARM
tccli monitor DescribeBaseMetrics --Namespace QCE/TKE

tccli monitor GetMonitorData \
  --Namespace QCE/TKE \
  --MetricName cluster_running_nodes \
  --Instances '[{"Dimensions":[{"Name":"clusterid","Value":"{{user.cluster_id}}"}]}]' \
  --StartTime "{{user.time_start}}" \
  --EndTime "{{user.time_end}}" \
  --Period 300
```

### TKE inventory and context

```bash
tccli tke DescribeClusters --Region {{env.TENCENTCLOUD_REGION}} --ClusterIds '["{{user.cluster_id}}"]'
tccli tke DescribeClusterInstances --Region {{env.TENCENTCLOUD_REGION}} --ClusterId "{{user.cluster_id}}"
tccli tke DescribeClusterNodePools --Region {{env.TENCENTCLOUD_REGION}} --ClusterId "{{user.cluster_id}}"
tccli tke DescribeClusterNodePoolDetail --Region {{env.TENCENTCLOUD_REGION}} --ClusterId "{{user.cluster_id}}" --NodePoolId "{{user.node_pool_id}}"
tccli tke DescribeAddon --Region {{env.TENCENTCLOUD_REGION}} --ClusterId "{{user.cluster_id}}" --AddonName "{{user.addon_name}}"
tccli tke DescribeResourceUsage --Region {{env.TENCENTCLOUD_REGION}} --ClusterId "{{user.cluster_id}}"

# Best-effort/degraded pod evidence only: DescribePodsBySpec requires CPU/Memory filters.
tccli tke DescribePodsBySpec --Region {{env.TENCENTCLOUD_REGION}} --ClusterId "{{user.cluster_id}}" --Cpu {{user.pod_cpu_filter}} --Memory {{user.pod_memory_filter}}
```

`DescribeClusterNodePoolDetail` and `DescribeAddon` require optional IDs/names. `DescribePodsBySpec` is not a generic pod-status command; use alarm dimensions and CLS events as the normal pod evidence path. Call `DescribePodsBySpec` only as best-effort/degraded evidence when the user supplies CPU/Memory filters; otherwise skip it, set `data_quality.degraded=true`, and lower confidence.

### CLB backend correlation

```bash
tccli clb DescribeTargetHealth --Region {{env.TENCENTCLOUD_REGION}} --LoadBalancerIds '["{{user.load_balancer_id}}"]'
tccli clb DescribeTargets --Region {{env.TENCENTCLOUD_REGION}} --LoadBalancerId "{{user.load_balancer_id}}"
```

### CloudAudit change events (change correlation)

```bash
tccli cloudaudit LookUpEvents \
  --StartTime {{user.time_start_epoch}} \
  --EndTime {{user.time_end_epoch}} \
  --MaxResults 100
```

Filter `Events[]` for mutation actions relevant to the incident scope. See [`change-correlation.md`](change-correlation.md) §2 for event-name patterns. If CloudAudit is disabled or returns `AccessDenied`, skip, set `evidence_by_layer.change_events.status=unavailable`, and lower change-as-root confidence.

### CLS event/log search

```bash
tccli cls SearchLog \
  --TopicId "{{user.tke_event_topic_id}}" \
  --From {{user.time_start_epoch}} \
  --To {{user.time_end_epoch}} \
  --QueryString "(level:Warning OR level:Error) AND cluster_id:{{user.cluster_id}}" \
  --Limit 100
```

> **SDK fallback:** [`api-sdk-usage.md`](api-sdk-usage.md) — client setup, allowed methods, pagination, CLS/TKE examples.

## Multi-Source RCA Collection

All commands above also feed into multi-source RCA. Additional read-only commands for CVM evidence:

### CVM instance info

```bash
tccli cvm DescribeInstances --InstanceIds '["{{user.instance_id}}"]'
```

For correlated CVM metrics (CPU/memory/disk/network):

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName {{metric_name}} \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.instance_id}}"}]}]' \
  --StartTime "{{user.time_start}}" \
  --EndTime "{{user.time_end}}" \
  --Period 300
```

Valid CVM metric names for RCA correlation: `CpuUsage`, `MemUsage`, `DiskUsage`, `DiskWriteTraffic`, `DiskReadTraffic`, `NetworkIn`, `NetworkOut`. Use API for latest: `tccli monitor DescribeBaseMetrics --Namespace QCE/CVM`.

### Dynamic baseline metric windows

For each metric in [`anomaly-detection.md`](anomaly-detection.md) §5, query **three** windows: current, yesterday (−24h), last week (−7d). Derive shifted ISO timestamps from `{{user.time_start}}` / `{{user.time_end}}`:

| Window | Start | End |
|---|---|---|
| Current | `{{user.time_start}}` | `{{user.time_end}}` |
| Yesterday | `{{user.baseline_yesterday_start}}` | `{{user.baseline_yesterday_end}}` |
| Last week | `{{user.baseline_week_start}}` | `{{user.baseline_week_end}}` |

```bash
# Example: CVM CpuUsage — current + yesterday + week (same Period)
tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName CpuUsage \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" \
  --EndTime "{{user.time_end}}" \
  --Period 300

tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName CpuUsage \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.baseline_yesterday_start}}" \
  --EndTime "{{user.baseline_yesterday_end}}" \
  --Period 300

tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName CpuUsage \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.baseline_week_start}}" \
  --EndTime "{{user.baseline_week_end}}" \
  --Period 300
```

Cap metrics per run at `anomaly_detection.max_metrics_per_run` (default 6). Compute p50/p95/max and anomaly score per [`anomaly-detection.md`](anomaly-detection.md) §4.

### Product RCA collection (CDB / Redis / ES / COS / CKafka / MongoDB / Postgres)

See [`product-rca-rules.md`](product-rca-rules.md) Rules H–P. Examples:

```bash
# H/I/J (existing)
tccli cdb DescribeDBInstances --InstanceIds '["{{user.resource_id}}"]'
tccli redis DescribeInstances --InstanceId "{{user.resource_id}}"
tccli es DescribeInstances --InstanceIds '["{{user.resource_id}}"]'

# K — COS (verify bucket dimension via DescribeBaseMetrics --Namespace QCE/COS)
tccli cos ListBuckets --Region {{env.TENCENTCLOUD_REGION}}
tccli monitor GetMonitorData --Namespace QCE/COS --MetricName 5xxResponse \
  --Instances '[{"Dimensions":[{"Name":"bucket","Value":"{{user.bucket_name}}-{{user.app_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300

# L — CKafka
tccli ckafka DescribeInstances --InstanceIdList '["{{user.resource_id}}"]' --Region {{env.TENCENTCLOUD_REGION}}
tccli monitor GetMonitorData --Namespace QCE/CKAFKA --MetricName ConsumerGroupOffsetLag \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300

# M — MongoDB
tccli mongodb DescribeDBInstances --InstanceIds '["{{user.resource_id}}"]'
tccli monitor GetMonitorData --Namespace QCE/CMONGO --MetricName Connper \
  --Instances '[{"Dimensions":[{"Name":"target","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300

# N — Postgres
tccli postgres DescribeDBInstances --Filters '[{"Name":"db-instance-id","Values":["{{user.resource_id}}"]}]'
tccli monitor GetMonitorData --Namespace QCE/POSTGRES --MetricName cpu_usage \
  --Instances '[{"Dimensions":[{"Name":"DBInstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300

# O — SCF
tccli scf GetFunction --FunctionName "{{user.function_name}}" --Namespace "{{user.scf_namespace}}"
tccli scf GetFunctionLogs --FunctionName "{{user.function_name}}" --Namespace "{{user.scf_namespace}}" \
  --StartTime {{user.time_start_epoch}} --EndTime {{user.time_end_epoch}} --Limit 50
tccli monitor GetMonitorData --Namespace QCE/SCF --MetricName Error \
  --Instances '[{"Dimensions":[{"Name":"FunctionName","Value":"{{user.function_name}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300

# P — CDN
tccli cdn DescribeDomainsConfig --Domains '["{{user.domain}}"]'
tccli monitor GetMonitorData --Namespace QCE/CDN --MetricName StatusCode5XX \
  --Instances '[{"Dimensions":[{"Name":"Domain","Value":"{{user.domain}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
```

### VPC network path (Rule G)

See [`network-rca.md`](network-rca.md). Infer `vpc_id` from `DescribeInstances` when omitted.

```bash
tccli cvm DescribeInstances --InstanceIds '["{{user.instance_id}}"]'
tccli vpc DescribeSecurityGroups --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'
tccli vpc DescribeRouteTables --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'
tccli vpc DescribeNatGateways --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'
```

Product SDK clients for RCA: see [`api-sdk-usage.md`](api-sdk-usage.md#allowed-methods-by-product).

## Output

Normalize raw data into the Event Bundle schema in [`alarm-handling.md`](alarm-handling.md), or the Multi-Source RCA Bundle schema in [`multi-source-rca.md`](multi-source-rca.md), including `data_quality.status`, `data_quality.degraded`, `missing_sources`, `warnings`, `source_recency`, and `evidence_by_layer`.

See [`multi-source-rca.md`](multi-source-rca.md) §4 for the RCA Bundle output schema. After bundling, assemble Incident Timeline per [`incident-timeline.md`](incident-timeline.md); persist to `./audit-results/incident-timeline-YYYYMMDD-HHMMSS.json`.

Anomaly-only scans: output schema in [`anomaly-detection.md`](anomaly-detection.md) §6; persist to `./audit-results/anomaly-bundle-YYYYMMDD-HHMMSS.json`.

Impact assessment uses CLB `DescribeTargetHealth` / `DescribeTargets` (see [`incident-knowledge.md`](incident-knowledge.md) §1). KB records persist to `./audit-results/incident-kb-YYYYMMDD-HHMMSS.json`; optional index at `./audit-results/incident-kb-index.json`.

Cross-skill orchestration: do **not** call billing APIs from this skill during F1/F2 — consume `{{user.finops_handoff}}` from `qcloud-finops-ops`. Persist merged output to `./audit-results/cross-skill-bundle-YYYYMMDD-HHMMSS.json` per [`cross-skill-orchestration.md`](cross-skill-orchestration.md).
