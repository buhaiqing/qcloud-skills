# Alarm Handling — AIOps Alarm Storm & Event Aggregation

> Applies to all products; **§TKE-Specific** sections add Kubernetes/TKE correlation rules. This is a **read-only diagnosis** runbook: it collects Monitor/TKE/CLS/CLB data and only suppresses/de-prioritizes alarms inside the generated Event Bundle output. It does not modify alarm policies, notification templates, resources, workloads, or CLB configuration.

## 0. Freshness and API Notes

- **Use API for latest metrics/namespaces:** run `tccli monitor DescribeAllNamespaces --SceneType ST_ALARM`, `tccli monitor DescribeBaseMetrics`, and `tccli monitor GetMonitorData` for current metric names/dimensions. Hardcoded metric names and thresholds below are defaults for correlation, not authoritative product catalogs.
- If the user gives ISO time (`{{user.time_start}}`, `{{user.time_end}}`), convert it to Unix epoch seconds before Monitor alarm-history or CLS log queries and store as `{{user.time_start_epoch}}` / `{{user.time_end_epoch}}`.
- If a source is unavailable or a field mapping is ambiguous, continue with `data_quality.degraded=true`, list `missing_sources`, and lower confidence.

## 1. Alarm Event Model

Every alarm is normalized into a **Canonical Alarm Event** before aggregation:

```json
{
  "alarm_id": "alarm-xxx",
  "source_ns": "QCE/TKE",
  "resource_type": "node|pod|cluster|service|addon",
  "resource_id": "ins-xxx|pod-xxx|cls-xxx|svc-xxx|addon-xxx",
  "cluster_id": "cls-xxx",
  "metric_name": "CpuUsage|NodeNotReady|PodRestart|...|CLB_5xx",
  "severity": "P0|P1|P2|P3",
  "labels": {"namespace":"prod","workload":"api-deploy","node_name":"node-1"},
  "first_fire": "2026-06-09T10:00:00+08:00",
  "last_fire": "2026-06-09T10:05:00+08:00",
  "fire_count": 12,
  "status": "firing|resolved"
}
```

### Raw → Canonical Mapping (best effort)

| Source | Raw fields to inspect | Canonical fields |
|---|---|---|
| Monitor `DescribeAlarmHistories` | `AlarmObject`, `MetricNames`, `AlarmLevels`, `Content`, `StartTime/EndTime` | `alarm_id`, `source_ns`, `metric_name`, `severity`, `resource_id`, timestamps |
| TKE `DescribeClusters` / `DescribeClusterInstances` | cluster and instance IDs/status fields from response | `cluster_id`, `resource_type=node|cluster`, `resource_id`, `labels.node_name` when present |
| TKE `DescribeClusterNodePools` / `DescribeClusterNodePoolDetail` | node pool IDs, desired/current/max capacity fields | capacity evidence; no absolute JSON path assumed |
| TKE `DescribeAddon` / `DescribePodsBySpec` (best-effort) | addon/pod status fields | `resource_type=addon|pod`, `labels.namespace`, `labels.workload`, `labels.node_name` when present. **Note:** `DescribePodsBySpec` requires CPU/Memory params; use alarm dimensions + CLS events as the normal pod evidence path, and `DescribePodsBySpec` only as a degraded-data fallback when filters are available |
| CLS `SearchLog` | log records and parsed labels | evidence patterns; optional canonical event if record maps to pod/node |
| CLB `DescribeTargetHealth` / `DescribeTargets` | target instance/backend health fields | `resource_type=service`, CLB health evidence, backend linkage |

> Field names may vary by API version and product response. Treat mapping as read-only best-effort; if a field cannot be mapped, preserve the raw excerpt in `evidence` and add a warning.

### TKE Grouping Keys

| Group Scope | Grouping Key | Example |
|---|---|---|
| Cluster-wide | `(cluster_id, metric_name)` | All NodeNotReady in cls-xxx |
| Node-local | `(cluster_id, labels.node_name)` | All metrics on node-1 |
| Workload-local | `(cluster_id, labels.namespace, labels.workload)` | All pod alarms for api-deploy in prod |
| Service-chain | `(cluster_id, labels.service_name)` + CLB linkage | CLB 5xx + backend pod alarms |
| Topology-chain | `(cluster_id, labels.node_name, labels.namespace, labels.workload)` | Node → Pod cascade |

## 2. Aggregation Pipeline

```
Collect → Normalize → Deduplicate → Correlate → Classify → Bundle
```

### Step 1: Collect (read-only)

Use CLI first. All collection steps below are intended read-only; verify availability with `tccli ... help` in your environment. Full command syntax is in [`cli-usage.md`](cli-usage.md); only summaries are listed here.

- Monitor alarm history: collect `QCE/TKE` alarms for `{{user.time_start_epoch}}` → `{{user.time_end_epoch}}`; see [`cli-usage.md#monitor-alarm-history`](cli-usage.md#monitor-alarm-history).
- Metric metadata/data: use `DescribeAllNamespaces --SceneType ST_ALARM`, `DescribeBaseMetrics`, and `GetMonitorData`; see [`cli-usage.md#metric-metadata-and-metric-data`](cli-usage.md#metric-metadata-and-metric-data).
- TKE inventory/context: collect cluster, node, node-pool, addon, and resource-usage context; see [`cli-usage.md#tke-inventory-and-context`](cli-usage.md#tke-inventory-and-context).
- Pod evidence: normal path is Monitor alarm dimensions + CLS events. `DescribePodsBySpec` is best-effort/degraded only because it requires user-supplied CPU/Memory filters; see [`cli-usage.md#tke-inventory-and-context`](cli-usage.md#tke-inventory-and-context).
- CLB and CLS evidence: collect only when the user supplies CLB IDs or TKE event topic IDs; see [`cli-usage.md#clb-backend-correlation`](cli-usage.md#clb-backend-correlation) and [`cli-usage.md#cls-eventlog-search`](cli-usage.md#cls-eventlog-search).

**Degraded-data behavior:** If optional `node_pool_id`, `addon_name`, `load_balancer_id`, or `tke_event_topic_id` is missing, skip that source, set `data_quality.degraded=true`, add the source to `missing_sources`, and avoid HIGH confidence unless the remaining evidence is sufficient.

### Step 2: Normalize

Map each raw alarm into the Canonical Alarm Event schema (§1). Extract `cluster_id`, `resource_type`, `labels.node_name`, `labels.namespace`, and `labels.workload` from dimensions/log labels when available. If extraction is uncertain, keep raw evidence and add a warning.

### Step 3: Deduplicate

Group by `(resource_id, metric_name)` within the time window. Keep the **highest-severity** representative; set `fire_count` to group size. Dedup removes redundant repeated alerts for the same condition.

### Step 4: Correlate

Apply topology-aware correlation rules (§4). Link alarms that share `cluster_id` + node/workload/chain relationships. Produce **correlation edges**:

```json
{"from":"node-1:NodeNotReady","to":"pod-xxx:CrashLoopBackOff","type":"node→pod_cascade"}
```

### Step 5: Classify

Assign each correlated group an **incident class** (§4 table). Determine root vs symptom using directional rules.

### Step 6: Bundle

Produce an **Event Bundle** (§5 output schema) — the single aggregated incident representation.

## 3. Noise-Reduction Policies

| Policy | Trigger | Output-only Action | Config Key |
|---|---|---|---|
| Deduplicate | Same `(resource_id, metric_name)` within window | Merge in bundle; keep highest severity; set `fire_count` | `alarm_handling.auto_deduplicate` |
| Storm threshold | > N alarms in M minutes from same `cluster_id` | Activate storm mode; de-prioritize P2/P3 inside bundle; surface P0/P1 first | `alarm_handling.storm_threshold` / `storm_window_minutes` |
| Flapping suppress | Alarm fires/resolves ≥ K times in W minutes | Mark as `flapping`; delay *bundle-level resolved status* until stable | `alarm_handling.flapping_window_minutes` / `flapping_count_threshold` |
| Maintenance window | `cluster_id` in known maintenance set | De-prioritize non-P0 inside bundle; tag `suppressed_by: maintenance` | `alarm_handling.maintenance_clusters` |
| Symptom suppression | Alarm classified as symptom of a root-cause alarm | Mark `suppressed=true` only in Event Bundle; include as evidence | Applied by correlation rules §4 |
| Cluster-scoped throttle | > `max_alarms_per_cluster` in window | Surface P0/P1 sections first; put P2/P3 in post-storm digest section | `alarm_handling.max_alarms_per_cluster` |

All suppression/de-prioritization actions are **output-only** and auditable. Suppressed alarms appear in the Event Bundle under `suppressed_alarms` with a reason; no cloud-side notification or alarm policy is changed.

## 4. TKE Correlation Rules

### Incident Classification

| Incident Class | Root Alarm | Correlated Symptoms | Typical Root Cause |
|---|---|---|---|
| Node Pressure | `NodeNotReady` / high CPU/memory / disk pressure | Pod restart, pod eviction, CLB backend unhealthy | CVM failure, resource exhaustion, kubelet issue |
| Pod Crash Loop | `PodRestart` / `CrashLoopBackOff` | OOM log, config error log, image pull failure | App bug, OOM, misconfigured probe, bad image |
| Capacity Exhaustion | `PodPending` / running nodes drop | Node pool capacity ceiling, CLB backend unhealthy | Insufficient nodes, quota/capacity limit, HPA maxed |
| CLB 5xx Chain | `CLB_5xx` / `CLB HealthCheckFail` | Backend pod CrashLoopBackOff, node NotReady | Unhealthy backends → CLB marks failed → 5xx |
| Addon Failure | `coredns` / `metrics-server` / `network-plugin` error | DNS resolution failure, HPA unable to read metrics, pod network unreachable | Addon crash, version incompatibility, resource starvation |
| Disk Pressure | high disk usage / `DiskPressure` | Log rotation failure, pod eviction, image pull failure | Unrotated logs, large cache, excessive container logs |

> Thresholds are defaults only. **Use API for latest:** query `DescribeBaseMetrics`, `DescribeAllNamespaces --SceneType ST_ALARM`, and current policy thresholds before finalizing severity.

### Directional Rules (Root vs Symptom)

```
NodeNotReady → suppress downstream pod/CLB alarms inside Event Bundle (symptoms of node failure)
PodPending  ← check node pool capacity using DescribeClusterNodePools/DescribeClusterNodePoolDetail
CLB 5xx     ← check backend pod/node health using CLB read-only target APIs + TKE inventory
Addon error → suppress downstream DNS/metrics/network alarms inside Event Bundle (infra root cause)
OOMKilled   ← check node MemoryPressure and CLS app logs before claiming app memory leak
```

### TKE-Specific Aggregation Flows

**Flow A: Node Pressure Cascade**
```
1. NodeNotReady alarm fires.
2. Read cluster/node inventory: DescribeClusters + DescribeClusterInstances.
3. Collect pod evidence from alarm dimensions, CLS event logs, or `DescribePodsBySpec` when CPU/Memory filters are available (best-effort/degraded otherwise).
4. Collect CLB backend evidence with DescribeTargetHealth/DescribeTargets if CLB IDs are known.
5. Classify: root=NodeNotReady, symptoms=pod+CLB; confidence=HIGH only when time/node linkage exists.
6. Bundle as a single incident with output-only symptom suppression.
```

**Flow B: Capacity Saturation**
```
1. PodPending alarms fire for multiple pods/workloads.
2. Check node pool capacity with DescribeClusterNodePools and optional DescribeClusterNodePoolDetail.
3. Check resource usage with DescribeResourceUsage when quota/capacity context is needed.
4. Mark missing HPA/quota details as degraded unless available from logs/metrics/product skill.
5. Classify: root=capacity if node pool/current usage evidence supports it.
6. RECOMMENDATION (not execution): increase MaxNum, add node pool, or request quota via qcloud-tke-ops; do not execute here.
```

**Flow C: CLB 5xx Backtrace**
```
1. CLB 5xx / HealthCheckFail alarm fires.
2. Identify backend instances via DescribeTargetHealth or DescribeTargets (read-only; qcloud-clb-ops boundary).
3. Correlate backend instance/node with TKE DescribeClusterInstances and pod/node alarms.
4. If backend pod CrashLoopBackOff exists, classify application/backend root; if node NotReady exists, classify infrastructure root.
5. Mark CLB alarm as symptom in bundle when backend evidence is stronger.
6. RECOMMENDATION (not execution): delegate CLB config checks to qcloud-clb-ops and backend health actions to qcloud-tke-ops/qcloud-cvm-ops.
```

**Flow D: Addon Degradation**
```
1. DNS resolution failure / metrics-server unavailable / network-plugin alarm fires.
2. Check addon status with DescribeAddon.
3. Check addon pod evidence through CLS events or `DescribePodsBySpec` when CPU/Memory filters are available (best-effort/degraded otherwise).
4. Check node resources/pressure using Monitor metrics and DescribeClusterInstances.
5. Classify: root=addon failure or root=node pressure → addon symptom.
6. RECOMMENDATION (not execution): reinstall/update addon or fix node via qcloud-tke-ops; do not execute here.
```

## 5. Event Bundle Output Schema

The aggregation pipeline outputs one **Event Bundle** per incident:

```json
{
  "bundle_id": "tke-evt-20260609-001",
  "cluster_id": "cls-xxx",
  "incident_class": "Node Pressure",
  "severity": "P1",
  "confidence": "HIGH",
  "data_quality": {
    "status": "complete|partial|stale",
    "degraded": false,
    "missing_sources": [],
    "warnings": [],
    "source_recency": {
      "monitor_alarm_history": "2026-06-09T10:15:00+08:00",
      "tke_inventory": "2026-06-09T10:15:30+08:00",
      "cls_events": "2026-06-09T10:14:00+08:00"
    }
  },
  "time_window": {
    "first_alarm": "2026-06-09T10:00:00+08:00",
    "last_alarm":  "2026-06-09T10:15:00+08:00",
    "diagnosis_window": "1h"
  },
  "root_alarm": {
    "alarm_id": "alarm-001",
    "resource_type": "node",
    "resource_id": "ins-xxx",
    "metric_name": "NodeNotReady",
    "labels": {"node_name":"node-1","cluster_id":"cls-xxx"}
  },
  "correlated_alarms": [
    {
      "alarm_id": "alarm-002",
      "resource_type": "pod",
      "resource_id": "pod-xxx",
      "metric_name": "CrashLoopBackOff",
      "correlation_type": "node→pod_cascade",
      "suppressed": true
    }
  ],
  "suppressed_alarms": [
    {"alarm_id":"alarm-003","reason":"symptom_of_root","root_alarm_id":"alarm-001"}
  ],
  "evidence": [
    {"source":"QCE/CVM","metric":"CpuUsage","value":"97%","timestamp":"..."},
    {"source":"CLS","pattern":"OOM","count":5,"sample":"..."},
    {"source":"QCE/TKE","metric":"cluster_running_nodes","value":"2/3"}
  ],
  "recommendations": [
    {
      "action": "RECOMMENDATION (not execution): inspect node-1 via CVM diagnostics",
      "delegate_to": "qcloud-cvm-ops"
    },
    {
      "action": "RECOMMENDATION (not execution): cordon and drain node-1 if unrecoverable",
      "delegate_to": "qcloud-tke-ops"
    }
  ],
  "incident_timeline_ref": {
    "timeline_id": "tl-20260609-001",
    "narrative_summary": "NodeNotReady@10:00 → pod CrashLoop@10:03 → CLB backend unhealthy@10:05",
    "event_count": 5
  }
}
```

Optional: when change evidence is collected per [`change-correlation.md`](change-correlation.md), embed `change_timeline[]` summary in `evidence` and link full timeline via `incident_timeline_ref`. Assemble per [`incident-timeline.md`](incident-timeline.md).

> **Boundary:** All `recommendations` are advisory. This skill never mutates resources.
> Every recommendation that involves mutation is prefixed `RECOMMENDATION (not execution)` and
> delegated to the appropriate product skill (`qcloud-tke-ops`, `qcloud-cvm-ops`, `qcloud-clb-ops`, `qcloud-monitor-ops`).

## 6. SDK Fallback (compact)

When CLI JSON quoting is difficult or batch collection is needed, use `tencentcloud-sdk-python` read clients only:

- Monitor: `monitor_client.MonitorClient` → `DescribeAlarmHistories`, `GetMonitorData`, `DescribeAllNamespaces` (`SceneType=ST_ALARM`), `DescribeBaseMetrics`.
- TKE: `tke_client.TkeClient` → `DescribeClusters`, `DescribeClusterInstances`, `DescribeClusterNodePools`, `DescribeClusterNodePoolDetail`, `DescribeAddon`, `DescribePodsBySpec` (best-effort with CPU/Memory filters), `DescribeResourceUsage`.
- CLB: `clb_client.ClbClient` → `DescribeTargetHealth`, `DescribeTargets`.
- CLS: `cls_client.ClsClient` → `SearchLog`.

Do not call `Create*`, `Modify*`, `Delete*`, `Install*`, `Update*`, `Drain*`, or scaling APIs from this diagnosis skill.

## 7. Alarm Priority Rules (Unchanged)

| Priority | Criteria | Response Time |
|----------|----------|---------------|
| P0 (Critical) | Service down, data loss risk, cluster unreachable | < 5 min |
| P1 (High) | Node NotReady, pod crash storm, performance degraded | < 15 min |
| P2 (Medium) | Capacity warning, single pod restart, addon warning | < 1 hour |
| P3 (Low) | Informational, trend alert, non-blocking | < 4 hours |

## 8. Storm Response Checklist

1. Identify storm source (`cluster_id` with highest alarm volume)
2. Normalize all alarms into Canonical Alarm Events (§1)
3. Deduplicate by `(resource_id, metric_name)` (§3)
4. Correlate by topology/time/resource (§4)
5. Classify incident and identify root alarm (§4)
6. Mark symptom alarms as output-only suppressed; bundle into Event Bundle (§5)
7. Apply output-only noise-reduction policies: de-prioritize P2/P3 during storm (§3)
8. Output Event Bundle with confidence, data quality, and recommendations
9. Delegate fix actions to product skills — **do not execute**
10. Document storm pattern for future automation

## Changelog

| Version | Date | Changes |
|---|---|---|
| 1.1.2 | 2026-06-09 | Event Bundle optional `incident_timeline_ref`; change evidence cross-link to `change-correlation.md` |
| 1.1.1 | 2026-06-09 | Round-1 review fixes: corrected Monitor alarm-history syntax, added verified read-only TKE/CLB/CLS commands, data-quality schema, raw-to-canonical mapping, output-only suppression wording, SDK fallback note, and TE-1 API freshness note |
| 1.1.0 | 2026-06-09 | TKE alarm noise reduction & event aggregation: added canonical alarm event model, TKE grouping keys, 6-step aggregation pipeline, 6 noise-reduction policies, 6 TKE incident classes with directional rules, 4 TKE aggregation flows, event bundle output schema with confidence/evidence/recommendations, explicit read-only boundary |
| 1.0.0 | 2026-05-21 | Initial release — alarm storm patterns, dedup, priority rules |
