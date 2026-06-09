# Product RCA Rules — CDB / Redis / ES

> **Read-only cross-product RCA.** Rules **H** (CDB), **I** (Redis), **J** (ES) extend [`multi-source-rca.md`](multi-source-rca.md) beyond the TKE/CLB/CVM stack. Mutations delegated to `qcloud-cdb-ops`, `qcloud-redis-ops`, `qcloud-es-ops`.

## 1. Shared Evidence Extensions

Add entity types to the Evidence Model:

| entity_type | linkage fields | Primary CLI |
|---|---|---|
| `cdb_instance` | `instance_id`, `vpc_id` | `tccli cdb DescribeDBInstances` |
| `redis_instance` | `instance_id`, `vpc_id` | `tccli redis DescribeInstances` |
| `es_cluster` | `instance_id`, `vpc_id` | `tccli es DescribeInstances` |

Monitor namespaces (TE-1: verify via `DescribeBaseMetrics`):

| Product | Namespace | Dimension name |
|---|---|---|
| CDB | `QCE/CDB` | `instanceId` |
| Redis | `QCE/REDIS` | `instanceid` |
| ES | `QCE/CES` | `instanceId` |

## 2. Rule H: CDB Slow Query / Connection Exhaustion Chain

**Trigger:** `SlowQueries` ↑, `CpuUseRate` ↑, `ThreadsConnected` near max, app/CLB timeout alarms.

| Evidence Layer | Signal | Scoring |
|---|---|---|
| CDB | `SlowQueries` > 0 sustained; `CpuUseRate` > 80% | Trigger |
| CDB | `VolumeRate` > 85%; `IOPS` spike | +1 I/O pressure |
| CDB | `ThreadsConnected` / max connections high | +2 connection exhaustion root |
| App/CLS | Slow query log pattern; lock wait timeout | +2 if log precedes app timeout |
| CLB | 5xx or latency ↑ on DB-backed service | +1 symptom |
| VPC | High latency SG/NAT (Rule G) | +2 if network path blocked |
| Baseline | [`anomaly-detection.md`](anomaly-detection.md) on `Qps`/`CpuUseRate` | +1 if anomaly precedes symptom |

### Hypotheses

| ID | Narrative | Root | HIGH when |
|---|---|---|---|
| **H1** | Missing index / bad SQL → slow queries → CPU ↑ → app timeout | `cdb_instance` (query) | SlowQueries + slow log match; Qps normal |
| **H2** | Connection pool leak / traffic spike → threads max → refused connections | `cdb_instance` (connections) | ThreadsConnected peak + connection errors in CLS |
| **H3** | CDB CPU/IOPS saturation (undersized) | `cdb_instance` (capacity) | CpuUseRate + VolumeRate high; baseline anomaly |
| **H4** | Network path issue (not DB) | `vpc_network` | CDB metrics normal; Rule G evidence (delegate) |

### Verification (read-only)

```bash
tccli cdb DescribeDBInstances --InstanceIds '["{{user.resource_id}}"]'
tccli monitor GetMonitorData --Namespace QCE/CDB --MetricName SlowQueries \
  --Instances '[{"Dimensions":[{"Name":"instanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
tccli monitor GetMonitorData --Namespace QCE/CDB --MetricName CpuUseRate \
  --Instances '[{"Dimensions":[{"Name":"instanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
```

**Delegate:** `qcloud-cdb-ops` (kill slow query, index, scale); `qcloud-vpc-ops` if H4.

---

## 3. Rule I: Redis Memory / Connection Storm

**Trigger:** `Storage` ↑, `Connections` ↑, `CpuUs` ↑, `CmdSlow` / evicted keys, app `ECONNREFUSED` / timeout.

| Evidence Layer | Signal | Scoring |
|---|---|---|
| Redis | `Storage` > 85% of max; `EvictedKeys` > 0 | +2 memory pressure root |
| Redis | `Connections` spike; `InFlow`/`OutFlow` ↑ | +2 connection storm |
| Redis | `CpuUs` high with stable Storage | +1 hot-key / CPU-bound commands |
| App/CLS | OOM, connection pool exhausted, timeout | +1 symptom |
| CLB | Backend timeout on cache-backed API | +1 symptom |
| Baseline | Storage/Connections anomaly vs yesterday | +1 |

### Hypotheses

| ID | Narrative | Root | HIGH when |
|---|---|---|---|
| **I1** | Memory growth / no eviction policy → OOM risk → app errors | `redis_instance` (memory) | Storage > 90% or EvictedKeys spike |
| **I2** | Connection storm (client leak or flash crowd) | `redis_instance` (connections) | Connections anomaly; Storage normal |
| **I3** | Hot key / big value / inefficient command | `redis_instance` (workload) | CpuUs high; single-key pattern in slow log |
| **I4** | Redis healthy; app misconfiguration | `app` | Redis metrics normal; app connection errors only |

### Verification (read-only)

```bash
tccli redis DescribeInstances --InstanceId "{{user.resource_id}}"
tccli monitor GetMonitorData --Namespace QCE/REDIS --MetricName Storage \
  --Instances '[{"Dimensions":[{"Name":"instanceid","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
tccli monitor GetMonitorData --Namespace QCE/REDIS --MetricName Connections \
  --Instances '[{"Dimensions":[{"Name":"instanceid","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
```

**Delegate:** `qcloud-redis-ops` (memory policy, scale, flush advisory); app owner for I4.

---

## 4. Rule J: ES Cluster Red/Yellow / Indexing Lag

**Trigger:** `HealthStatus` yellow/red, `ClusterStatus` alarm, search timeout, indexing backlog.

| Evidence Layer | Signal | Scoring |
|---|---|---|
| ES | `HealthStatus` 2 (red) or 1 (yellow) | Trigger |
| ES | `JvmMemUsage` > 85%; `CpuUsage` high | +2 JVM/resource pressure |
| ES | `IndexSpeed` drop; `SearchLatency` ↑ | +2 indexing/search degradation |
| ES | Unassigned shards (from DescribeInstances status fields) | +2 allocation failure |
| App/CLS | search timeout, 503 from ES client | +1 symptom |
| CVM/node | Underlying node disk/cpu if exposed | +1 if host pressure |

### Hypotheses

| ID | Narrative | Root | HIGH when |
|---|---|---|---|
| **J1** | Shard unassigned / disk watermark → yellow/red | `es_cluster` (allocation) | Red status + disk metric high |
| **J2** | JVM heap pressure → GC pause → search latency | `es_cluster` (jvm) | JvmMemUsage high; search latency correlated |
| **J3** | Bulk indexing overload → thread pool reject | `es_cluster` (indexing) | IndexSpeed drop during bulk window |
| **J4** | Query storm / expensive aggregation | `es_cluster` (query) | SearchLatency ↑; CPU high; JVM moderate |

### Verification (read-only)

```bash
tccli es DescribeInstances --InstanceIds '["{{user.resource_id}}"]'
tccli monitor GetMonitorData --Namespace QCE/CES --MetricName ClusterStatus \
  --Instances '[{"Dimensions":[{"Name":"instanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
```

> Metric names vary by ES version. Use `tccli monitor DescribeBaseMetrics --Namespace QCE/CES` for current catalog.

**Delegate:** `qcloud-es-ops` (shard allocation, scale, index settings).

---

## 5. RCA Bundle Integration

When `resource_type` is `cdb`, `redis`, or `es`, populate:

```json
"product_rca": {
  "rule_set": "H|I|J",
  "resource_type": "cdb",
  "resource_id": "cdb-xxx",
  "hypotheses": [{"hypothesis_id": "H1", "confidence": "HIGH", "score": 6}]
},
"evidence_by_layer": {
  "cdb_metrics": {"status": "complete", "evidence_count": 4},
  "redis_metrics": {"status": "skipped"},
  "es_metrics": {"status": "skipped"}
}
```

Cross-link to CLB/VPC layers when user supplies `{{user.load_balancer_id}}` or `{{user.vpc_id}}`.

## 6. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-09 | Rules H/I/J for CDB slow-query chain, Redis memory/connection storm, ES cluster health |
