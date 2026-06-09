# Multi-Source Root Cause Localization — Pod / Node / CLB / CVM

> **Read-only RCA runbook.** This skill collects evidence only. All mutation recommendations are prefixed `RECOMMENDATION (not execution)` and delegated to product skills. See rubric rules §1 (confidence disclosure), §3 (time-range correlation), §4 (data recency), and §5 (recommendation boundary) in [`rubric.md`](rubric.md).

## 1. Evidence Model

Every evidence fragment is normalized before hypothesis scoring:

```json
{
  "source": "monitor|tke|clb|cvm|cls|cloudaudit|vpc|cdb|redis|es",
  "entity_id": "ins-xxx|pod-xxx|np-xxx|lb-xxx|cdb-xxx|crs-xxx|es-xxx|sg-xxx",
  "entity_type": "node|pod|node_pool|clb_backend|cluster|addon|cvm_instance|cdb_instance|redis_instance|es_cluster|security_group|route_table|nat_gateway|vpc_subnet",
  "signal": "metric|metric_anomaly|alarm|log|config|status",
  "metric_or_pattern": "CpuUsage|NodeNotReady|OOM|5xx|Pending",
  "severity": "P0|P1|P2|P3",
  "confidence": "HIGH|MEDIUM|LOW",
  "timestamp": "2026-06-09T10:00:00+08:00",
  "window_start": "2026-06-09T10:00:00+08:00",
  "window_end": "2026-06-09T10:15:00+08:00",
  "value_or_sample": "97% | 5 occurrences | excerpt",
  "linkage": {
    "cluster_id": "cls-xxx",
    "node_name": "node-1",
    "instance_id": "ins-xxx",
    "load_balancer_id": "lb-xxx",
    "backend_id": "ins-yyy",
    "namespace": "prod",
    "workload": "api-deploy",
    "pod_name": "api-xxxxx"
  },
  "raw": {}  
}
```

### Entity Types and Linkage Expectations

> Use API for latest metric names/dimensions: run `tccli monitor DescribeAllNamespaces --SceneType ST_ALARM` and `tccli monitor DescribeBaseMetrics` for current names before relying on defaults.

| entity_type | linkage fields expected | Primary CLI source |
|---|---|---|
| cluster | cluster_id | `DescribeClusters` |
| node | cluster_id, node_name, instance_id | `DescribeClusterInstances` |
| node_pool | cluster_id, node_pool_id | `DescribeClusterNodePools` |
| pod | cluster_id, namespace, workload, pod_name, node_name | Alarm dimensions / CLS events / `DescribePodsBySpec` (degraded) |
| clb_backend | load_balancer_id, backend_id, instance_id | `DescribeTargetHealth`, `DescribeTargets` |
| cvm_instance | instance_id | `DescribeInstances` (CVM product) / Monitor metrics |
| addon | cluster_id, addon_name | `DescribeAddon` |

## 2. RCA Pipeline

```
Collect Evidence → Normalize → Topology Link → Align Time Windows → Score Hypotheses → Produce RCA Bundle
```

### Step 1: Collect Evidence (read-only)

Gather evidence from available sources. See [`cli-usage.md`](cli-usage.md) for full command syntax; only summaries are listed here.

| Source | What to collect | Degrades if |
|---|---|---|
| Monitor alarm history | TKE + CVM alarms in time window | API rate limit; retry once, then degrade |
| TKE inventory | Cluster, node, node-pool, addon, resource usage context | Missing cluster_id → HALT |
| Pod evidence | Alarm dimensions + CLS events (primary); `DescribePodsBySpec` (degraded fallback only when CPU/Memory filters available) | No pod-level CLS topic → degrade |
| CLB backend health | `DescribeTargetHealth`, `DescribeTargets` | No load_balancer_id → skip `clb_backend` evidence layer |
| CVM metrics | Monitor `GetMonitorData` for CPU/memory/disk/network | No instance_id known from inventory → skip |
| Baseline anomalies | Multi-window `GetMonitorData` per [`anomaly-detection.md`](anomaly-detection.md) | Baselines unavailable → static fallback; lower confidence |
| CLS event/log | TKE Kubernetes events, app error logs | No topic_id → skip |
| Change events | CloudAudit `LookUpEvents`, CLS rollout events | CloudAudit disabled or AccessDenied → skip; see [`change-correlation.md`](change-correlation.md) |
| CDB/Redis/ES metrics | Product `Describe*` + Monitor `QCE/CDB|REDIS|CES` | Missing `resource_id` → skip; see [`product-rca-rules.md`](product-rca-rules.md) |
| VPC network path | SG, route, NAT read-only | Missing `vpc_id` and cannot infer → skip; see [`network-rca.md`](network-rca.md) |

All collection is read-only. Missing sources are recorded in `evidence_by_layer` with `data_quality.degraded=true` and a warning.

### Step 2: Normalize

Map each collected datum into the Evidence Model (§1). If a linkage field cannot be determined (e.g., pod-to-node mapping unavailable), leave it null and note the gap in `data_quality.warnings`.

### Step 3: Topology Link

Build a directed graph of entity relationships within the cluster:

```
Cluster
 ├── Node (instance_id, node_name)
 │    ├── Pod (namespace, workload, pod_name)
 │    │    └── Container (via log source)
 │    └── CLB Backend (instance_id → load_balancer_id)
 ├── NodePool (node_pool_id)
 │    └── Node (instance_id)
 └── Addon (addon_name)
```

Link entities that share `cluster_id`, then node-level links via `node_name`/`instance_id`, and CLB links via backend `instance_id`. Produce a `topology_links` array:

```json
[
  {"from_type":"node","from_id":"ins-xxx","to_type":"pod","to_id":"pod-xxx","via":"node_name:node-1"},
  {"from_type":"node","from_id":"ins-xxx","to_type":"clb_backend","to_id":"lb-xxx","via":"instance_id:ins-xxx"}
]
```

If topology linkage is incomplete (no node_name, no instance_id mapping), note in `warnings` and avoid HIGH confidence for hypotheses that depend on that missing link.

### Step 4: Align Time Windows

Check that evidence timestamps overlap. Rules:
- All evidence must fall within `diagnosis_window` (max 24h).
- At least one evidence fragment from each layer must overlap the **root symptom window** (earliest → latest alarm/max spike).
- If layers have non-overlapping windows, set `time_alignment.status=partial`, add a warning, and lower hypothesis confidence.

### Step 5: Score Hypotheses

For each candidate hypothesis, score based on:

| Factor | Points | Notes |
|---|---|---|
| Topology linkage | +2 | Pod on same node as NodeNotReady |
| Time coincidence | +1 | Evidence windows overlap |
| Direction match | +2 | Root→symptom direction aligned |
| Confidence per evidence | +1 | Each HIGH-confidence evidence fragment |
| Log match | +1 | Log pattern supports the hypothesis |
| Baseline anomaly on root entity | +1 | HIGH+ anomaly score from [`anomaly-detection.md`](anomaly-detection.md) §4 |
| Baseline anomaly precedes alarm ≤10min | +2 | Supports root-cause direction |
| Alternative explanation | -2 | Another hypothesis also fits with high score |

Score thresholds:
- **HIGH** ≥ 4 points and no conflicting topology
- **MEDIUM** 2–3 points, or plausible topology with weak time alignment
- **LOW** < 2 points, or conflicting evidence

Score multiple hypotheses; sort by score. The highest-scoring hypothesis becomes `top_cause`.

### Step 6: Produce RCA Bundle

Assemble findings into the Multi-Source RCA Bundle (§4).

## 3. Correlation Rules and Hypothesis Scoring

### Rule F: Post-Change Regression

Canonical details: [`change-correlation.md`](change-correlation.md) §4. Summary:

| Evidence Layer | Signal | Scoring |
|---|---|---|
| Change | deploy/config/scale in lead window | Trigger (+3 if HIGH mapping) |
| Pod | CrashLoopBackOff after change | +2 if workload matches |
| CLB | 5xx after change | +1 symptom |
| Pre-change metrics normal | CPU/Mem stable before change | +1 supports regression |

Hypotheses F1–F5 (deploy regression, CLB config change, scale/reboot, network/SG, coincidental). **Change-as-root HIGH** requires lead-lag validity and total score ≥ 5.

### Rule G: VPC Network Path (summary)

Canonical details: [`network-rca.md`](network-rca.md). Apply on timeout/refused with healthy compute metrics, or with Rule F4 network changes. Hypotheses G1–G5 (SG, route, NAT, NACL, ruled-out).

### Rules H / I / J: CDB / Redis / ES (summary)

Canonical details: [`product-rca-rules.md`](product-rca-rules.md).

| Rule | Product | Trigger |
|---|---|---|
| **H** | CDB | SlowQueries, CpuUseRate, connection exhaustion → app/CLB timeout |
| **I** | Redis | Storage, Connections, memory/eviction storm |
| **J** | ES | Cluster red/yellow, JVM/indexing/search latency |

### Rule A: CLB 5xx / Health Failure → Backend Pod / Node

| Evidence Layer | Signal | Scoring |
|---|---|---|
| CLB | 5xx rate > threshold or HealthCheckFail | Trigger |
| Backend node | NodeNotReady or high CpuUsage | +2 root if node unhealthy |
| Backend pod | CrashLoopBackOff, OOMKilled, Pending | +2 root if pod unhealthy; +1 if same node as node pressure |
| CVM | CPU/memory/disk high on backend instance | +1 if matches node evidence window |
| Time | CLB 5xx window overlaps backend alarm window | +1 |

Hypotheses:
- **Node failure → backend unhealthy → CLB 5xx**: `{node: P0/P1, pod: symptom, clb: symptom}`. HIGH if node time-coincident with CLB 5xx.
- **Pod crash (app regression) → CLB 5xx**: `{pod: P0/P1, node: normal, clb: symptom}`. HIGH if pod OOM/restart precedes 5xx, node metrics normal.
- **CLB config/network → 5xx (no backend issue)**: `{clb: root, pod/node: unrelated}`. MEDIUM if no backend evidence found. RECOMMENDATION: delegate to qcloud-clb-ops for config audit.

Verification steps to include in RCA Bundle:
- `Verify CLB backend health group: tccli clb DescribeTargetHealth --LoadBalancerIds '["lb-xxx"]'`
- `Verify node status: tccli tke DescribeClusterInstances --ClusterId "cls-xxx"`
- `Verify pod logs via CLS: tccli cls SearchLog --TopicId "topic-xxx" --QueryString "pod_name:api-xxxxx"`

### Rule B: Pod CrashLoopBackOff / OOMKilled

| Evidence Layer | Signal | Scoring |
|---|---|---|
| Pod | CrashLoopBackOff, OOMKilled, restart count high | Trigger |
| Node | MemoryPressure, DiskPressure, CpuUsage > 90% | +2 root if node pressure coincident |
| CVM | MemoryUsage > 90%, high I/O wait | +1 if matches node pressure window |
| CLS app logs | OOM pattern, app exception, config error | +1 if log matches pod restart window |
| CLB | 5xx from backend if pod serves traffic | +1 symptom (if CLB 5xx present) |

Hypotheses:
- **App regression (code/config bug)**: `{pod: root, node: normal, logs: app error}`. HIGH if app error log precedes OOM and node resources normal.
- **Node memory pressure → OOMKilled**: `{node: root, pod: symptom}`. HIGH if node MemUsage > 90% at pod restart time.
- **Image/deployment issue**: `{pod: root, logs: ImagePullBackOff or CrashLoop}`. MEDIUM if no resource pressure found.

Verification steps:
- `Check pod events: tccli cls SearchLog --TopicId "topic-xxx" --QueryString "pod_name:{{pod_name}} AND (OOMKilled OR CrashLoopBackOff)"`
- `Check node memory: tccli monitor GetMonitorData --Namespace QCE/CVM --MetricName MemUsage`

### Rule C: Pod Pending — Capacity / Quota

| Evidence Layer | Signal | Scoring |
|---|---|---|
| Pod | Pending, multiple pods pending across workloads | Trigger |
| Node pool | DesiredNodeCount >= MaxNum, current == MaxNum | +2 root if node pool saturated |
| CVM | Quota exhausted (DescribeUserQuota / DescribeResourceUsage) | +2 root if quota/capacity exhausted |
| Node | Node conditions: ready count < expected | +1 if node count shows shortage |
| Time | Pending window matches capacity data window | +1 |

Hypotheses:
- **Node pool capacity exhausted**: `{node_pool: root, pods: symptom}`. HIGH if MaxNum reached and pods started pending at same time.
- **CVM quota limit**: `{cvm_quota: root, pods: symptom}`. HIGH if DescribeUserQuota shows limit reached.
- **Resource request too high**: `{pods: root, node_pool: adequate}`. MEDIUM if capacity available but pods still pending (check taints/tolerations/PVC).

Verification steps:
- `Check node pool: tccli tke DescribeClusterNodePools --ClusterId "cls-xxx"`
- `Check quota: tccli tke DescribeResourceUsage --ClusterId "cls-xxx"`

### Rule D: Node NotReady — CVM / Network / Disk

| Evidence Layer | Signal | Scoring |
|---|---|---|
| Node | NodeNotReady alarm or condition | Trigger |
| CVM | Instance status not Running, CpuUsage 100%, DiskUsage > 95% | +2 root if CVM issue |
| Monitor CVM metrics | CpuUsage spike, MemUsage spike, DiskUsage > 95% | +2 root if sustained spike at node fail time |
| Pod | CrashLoopBackOff, pending on affected node | +1 symptom |
| CLB | Backend health failure if node hosts CLB backend | +1 symptom |
| Time | CVM metric spike within 5min of NodeNotReady | +1 |

Hypotheses:
- **CVM failure (OS/disk/kernel)**: `{cvm: root, node: symptom}`. HIGH if CVM metrics show disk/cpu anomaly at fail time.
- **kubelet/cri issue**: `{node: root, cvm: normal}`. HIGH if CVM healthy but kubelet unreachable (check CLS for kubelet errors).
- **Network partition**: `{node: root, cvm: normal, network: suspected}`. MEDIUM if no CVM/disk evidence.

Verification steps:
- `Check CVM status: tccli cvm DescribeInstances --InstanceIds '["ins-xxx"]' --limit 1`
- `Check CVM CPU/memory/disk: tccli monitor GetMonitorData`

### Rule E: CVM Saturation → TKE Symptoms

| Evidence Layer | Signal | Scoring |
|---|---|---|
| CVM | CpuUsage > 90%, MemUsage > 90%, DiskUsage > 95%, NetworkIn/Out max | Trigger |
| Node | Same instance as CVM; node condition pressure | +1 symptom |
| Pod | OOMKilled, Pending, restart count high on same node | +2 symptom if pod affected |
| CLB | 5xx increase from backends on affected CVM | +1 symptom |
| Time | CVM metric spike precedes pod/CLB symptoms | +2 root if CVM spike leads |

Hypotheses:
- **Traffic burst → CVM saturation → TKE symptoms**: `{cvm: root, node: symptom, pod: symptom}`. HIGH if NetworkIn/NetworkOut spike precedes CPU/Mem.
- **Application resource leak → CVM saturation**: `{app: root, cvm: symptom, pod: symptom}`. HIGH if pod memory grows continuously before CVM saturation.
- **Denial of service / external attack**: `{network: suspected, cvm: symptom}`. MEDIUM if traffic unusual and no app change.

Verification steps:
- `Check traffic pattern: tccli monitor GetMonitorData --Namespace QCE/CVM --MetricName NetworkIn`
- `Check pod resource trends via CLS metrics or k8s events`

## 4. Multi-Source RCA Bundle Output Schema

```json
{
  "rca_id": "rca-20260609-001",
  "diagnosis_window": "1h",
  "trigger_signals": ["NodeNotReady", "CLB_5xx", "CrashLoopBackOff"],
  "top_cause": {
    "hypothesis_id": "H1",
    "description": "Node failure (CVM disk pressure) caused node NotReady → pod CrashLoopBackOff → CLB 5xx",
    "confidence": "HIGH",
    "score": 7,
    "root_entity_type": "cvm_instance",
    "root_entity_id": "ins-xxx",
    "root_entity_name": "node-1"
  },
  "hypotheses": [
    {
      "hypothesis_id": "H1",
      "narrative": "CVM disk pressure (DiskUsage 97% at 10:02) → kubelet degraded, NodeNotReady (10:03) → pods evicted, CrashLoopBackOff (10:04) → CLB marks backends unhealthy, 5xx spike (10:05)",
      "cause": "CVM disk pressure",
      "symptom": "CLB 5xx / Pod CrashLoopBackOff",
      "confidence": "HIGH",
      "score": 7,
      "evidence_count": 5,
      "topology_linked": true,
      "time_aligned": true,
      "root_entity_type": "cvm_instance",
      "root_entity_id": "ins-xxx"
    },
    {
      "hypothesis_id": "H2",
      "narrative": "Pod app regression causes CrashLoopBackOff → CLB marks backend unhealthy → 5xx increase; node/CVM metrics normal throughout",
      "cause": "Application regression (pod crash)",
      "symptom": "CLB 5xx / Pod CrashLoopBackOff",
      "confidence": "MEDIUM",
      "score": 3,
      "evidence_count": 2,
      "topology_linked": true,
      "time_aligned": true,
      "root_entity_type": "pod"
    }
  ],
  "evidence_by_layer": {
    "monitor_alarm_history": {"sources_used": 1, "evidence_count": 3, "status": "complete", "latest_timestamp": "2026-06-09T10:15:00+08:00"},
    "tke_inventory": {"sources_used": 2, "evidence_count": 2, "status": "complete", "latest_timestamp": "2026-06-09T10:15:30+08:00"},
    "clb_backend": {"sources_used": 1, "evidence_count": 2, "status": "complete", "latest_timestamp": "2026-06-09T10:16:00+08:00"},
    "cvm_metrics": {"sources_used": 1, "evidence_count": 3, "status": "complete", "latest_timestamp": "2026-06-09T10:14:00+08:00"},
    "cls_events": {"sources_used": 0, "evidence_count": 0, "status": "unavailable", "warning": "No CLS topic_id configured"},
    "change_events": {"sources_used": 1, "evidence_count": 1, "status": "complete", "latest_timestamp": "2026-06-09T10:02:00+08:00"}
  },
  "topology_links": [
    {"from_type":"cvm_instance","from_id":"ins-xxx","to_type":"node","to_id":"ins-xxx","via":"instance_id"},
    {"from_type":"node","from_id":"ins-xxx","to_type":"pod","to_id":"pod-xxx","via":"node_name:node-1"},
    {"from_type":"node","from_id":"ins-xxx","to_type":"clb_backend","to_id":"lb-xxx","via":"instance_id"}
  ],
  "time_alignment": {
    "overall_window": {"start":"2026-06-09T10:00:00+08:00","end":"2026-06-09T10:16:00+08:00"},
    "layers": {"monitor":true,"tke":true,"clb":true,"cvm":true,"cls":"unavailable"},
    "status": "partial",
    "warnings": ["CLS events unavailable: evidence gap"]
  },
  "data_quality": {
    "status": "partial",
    "degraded_sources": ["cls_events"],
    "warnings": ["CLS topic_id not supplied; pod-level evidence may be incomplete"],
    "source_recency": {
      "monitor_alarm_history": "2026-06-09T10:15:00+08:00",
      "tke_inventory": "2026-06-09T10:15:30+08:00",
      "clb_backend": "2026-06-09T10:16:00+08:00",
      "cvm_metrics": "2026-06-09T10:14:00+08:00"
    }
  },
  "recommendations": [
    {
      "action": "RECOMMENDATION (not execution): investigate disk pressure on CVM ins-xxx",
      "delegate_to": "qcloud-cvm-ops",
      "priority": "P0"
    },
    {
      "action": "RECOMMENDATION (not execution): drain and replace node-1 via node pool if unrecoverable",
      "delegate_to": "qcloud-tke-ops",
      "priority": "P0"
    },
    {
      "action": "RECOMMENDATION (not execution): verify CLB backend health after node recovery",
      "delegate_to": "qcloud-clb-ops",
      "priority": "P1"
    }
  ],
  "verification_steps": [
    "tccli cvm DescribeInstances --InstanceIds '[\"ins-xxx\"]'",
    "tccli tke DescribeClusterInstances --ClusterId \"cls-xxx\"",
    "tccli clb DescribeTargetHealth --LoadBalancerIds '[\"lb-xxx\"]'",
    "tccli monitor GetMonitorData --Namespace QCE/CVM --MetricName DiskUsage --Instances '[{\"Dimensions\":[{\"Name\":\"InstanceId\",\"Value\":\"ins-xxx\"}]}]'"
  ],
  "change_timeline": [
    {
      "change_id": "chg-20260609-001",
      "source": "cls_k8s_event",
      "change_type": "deploy",
      "resource_id": "api-deploy",
      "timestamp": "2026-06-09T10:02:00+08:00",
      "summary": "RollingUpdate revision 42",
      "confidence": "HIGH"
    }
  ],
  "likely_change_trigger": {
    "change_id": "chg-20260609-001",
    "change_type": "deploy",
    "resource_id": "api-deploy",
    "timestamp": "2026-06-09T10:02:00+08:00",
    "confidence": "HIGH",
    "hypothesis_id": "F1"
  },
  "anomaly_findings": [
    {"metric": "DiskUsage", "anomaly_score": 72, "anomaly_severity": "CRITICAL", "vs_yesterday_p95_ratio": 1.85, "detection_method": "baseline_ratio"}
  ],
  "product_rca": null,
  "network_rca": null,
  "incident_timeline_ref": {
    "timeline_id": "tl-20260609-001",
    "narrative_summary": "Deploy api-deploy@10:02 → pod CrashLoop@10:04 → CLB 5xx@10:05",
    "event_count": 6
  },
  "feedback_loop": {
    "was_accurate": null,
    "actual_root_cause": null,
    "notes": null
  }
}
```

> `change_timeline` and `likely_change_trigger` are populated when change evidence is collected; set `likely_change_trigger` to `null` when unavailable. Full timeline: [`incident-timeline.md`](incident-timeline.md). Persist to `./audit-results/incident-timeline-YYYYMMDD-HHMMSS.json`.

> All `recommendations` are advisory. Mutation actions are prefixed `RECOMMENDATION (not execution)` and delegated to product skills. `verification_steps` are read-only; verify locally before interpreting results.

## 5. Compact CLI/SDK Reference

CLI syntax for each collection command (read-only) is maintained in [`cli-usage.md`](cli-usage.md). Key command families:

| Data layer | CLI entry point | SDK fallback client |
|---|---|---|
| Monitor alarm history | `tccli monitor DescribeAlarmHistories` | `monitor_client.MonitorClient` |
| Monitor metrics | `tccli monitor GetMonitorData` | `monitor_client.MonitorClient` |
| TKE cluster info | `tccli tke DescribeClusters` | `tke_client.TkeClient` |
| TKE node list | `tccli tke DescribeClusterInstances` | `tke_client.TkeClient` |
| TKE node pools | `tccli tke DescribeClusterNodePools` | `tke_client.TkeClient` |
| TKE addon status | `tccli tke DescribeAddon` | `tke_client.TkeClient` |
| TKE resource usage | `tccli tke DescribeResourceUsage` | `tke_client.TkeClient` |
| CLB backend health | `tccli clb DescribeTargetHealth` | `clb_client.ClbClient` |
| CLB targets | `tccli clb DescribeTargets` | `clb_client.ClbClient` |
| CVM instance info | `tccli cvm DescribeInstances` | `cvm_client.CvmClient` |
| CLS log search | `tccli cls SearchLog` | `cls_client.ClsClient` |
| Change events | `tccli cloudaudit LookUpEvents` | `cloudaudit_client.CloudauditClient` |
| CDB instance | `tccli cdb DescribeDBInstances` | `cdb_client.CdbClient` |
| Redis instance | `tccli redis DescribeInstances` | `redis_client.RedisClient` |
| ES cluster | `tccli es DescribeInstances` | `es_client.EsClient` |
| VPC network | `tccli vpc DescribeSecurityGroups`, `DescribeRouteTables`, `DescribeNatGateways` | `vpc_client.VpcClient` |
| Monitor namespaces | `tccli monitor DescribeAllNamespaces --SceneType ST_ALARM` | `monitor_client.MonitorClient` |

All fallback methods are read-only. Use product skills (qcloud-tke-ops, qcloud-cvm-ops, qcloud-clb-ops, qcloud-monitor-ops) for any mutation.

## 6. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-09 | Initial release — Multi-Source RCA evidence model, 6-step pipeline, 5 correlation rules with hypothesis scoring, RCA Bundle output schema, topology linkage, time alignment, verification steps, and delegation mapping |
| 1.1.0 | 2026-06-09 | Rule F post-change regression, change evidence layer, `change_timeline` / `likely_change_trigger` / `incident_timeline_ref` in RCA Bundle |
| 1.2.0 | 2026-06-09 | Baseline anomaly evidence layer, hypothesis scoring boost, `anomaly_findings` in RCA Bundle |
| 1.3.0 | 2026-06-09 | Rule G VPC network path; Rules H/I/J CDB/Redis/ES; product + vpc evidence layers; `product_rca` / `network_rca` bundle fields |