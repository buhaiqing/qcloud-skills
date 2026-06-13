# Product RCA Rules — CDB / Redis / ES / COS / CKafka / MongoDB / Postgres / SCF / CDN

> **Read-only cross-product RCA.** Rules **H–N** (datastore/messaging), **O** (SCF), **P** (CDN) extend [`multi-source-rca.md`](multi-source-rca.md). Mutations delegated to product ops skills.

## 1. Shared Evidence Extensions

Add entity types to the Evidence Model:

| entity_type | linkage fields | Primary CLI |
|---|---|---|
| `cdb_instance` | `instance_id`, `vpc_id` | `tccli cdb DescribeDBInstances` |
| `redis_instance` | `instance_id`, `vpc_id` | `tccli redis DescribeInstances` |
| `es_cluster` | `instance_id`, `vpc_id` | `tccli es DescribeInstances` |
| `cos_bucket` | `bucket_name`, `app_id` | `tccli cos ListBuckets` / CLS access logs |
| `ckafka_instance` | `instance_id`, `vpc_id` | `tccli ckafka DescribeInstances` |
| `mongodb_instance` | `instance_id`, `vpc_id` | `tccli mongodb DescribeDBInstances` |
| `postgres_instance` | `instance_id`, `vpc_id` | `tccli postgres DescribeDBInstances` |
| `scf_function` | `function_name`, `scf_namespace` | `tccli scf GetFunction`, `GetFunctionLogs` |
| `cdn_domain` | `domain` | `tccli cdn DescribeDomainsConfig` |

Monitor namespaces (TE-1: verify via `DescribeBaseMetrics`):

| Product | Namespace | Dimension name |
|---|---|---|
| CDB | `QCE/CDB` | `instanceId` |
| Redis | `QCE/REDIS` | `instanceid` |
| ES | `QCE/CES` | `instanceId` |
| COS | `QCE/COS` | `bucket` (value often `<name>-<appid>`) |
| CKafka | `QCE/CKAFKA` | `InstanceId` |
| MongoDB | `QCE/CMONGO` | `target` |
| Postgres | `QCE/POSTGRES` | `DBInstanceId` |
| SCF | `QCE/SCF` | `FunctionName` (may include `Namespace`; verify via API) |
| CDN | `QCE/CDN` | `Domain` |

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

## 5. Rule K: COS Request Latency / 4xx / 5xx Chain

**Trigger:** `4xxResponse` / `5xxResponse` ↑, `FirstByteDelay` ↑, upload/download timeout, app errors on object storage.

| Evidence Layer | Signal | Scoring |
|---|---|---|
| COS Monitor | `5xxResponse` > 0 sustained; `InternalError` spike | +2 service-side root |
| COS Monitor | `4xxResponse` spike (auth/signature/not-found) | +2 client/config root |
| COS Monitor | `FirstByteDelay` / downlink latency ↑ | +2 latency root |
| COS Monitor | `TotalRequest` spike with flat error rate | +1 traffic surge (symptom) |
| CLS | Access log 403/404/503 patterns on bucket | +2 if log matches metric window |
| CAM/CloudAudit | Credential or policy change (Rule F) | +2 if change precedes 403 spike |
| VPC | Rule G if timeout without HTTP status | +2 alternate layer |
| Baseline | Request/error rate anomaly vs yesterday | +1 |

### Hypotheses

| ID | Narrative | Root | HIGH when |
|---|---|---|---|
| **K1** | CAM/signature/ACL misconfig → 403/4xx | `cos_bucket` (auth) | 4xx spike + CloudAudit CAM change or 403 in CLS |
| **K2** | COS service/internal error → 5xx | `cos_bucket` (service) | 5xxResponse + InternalError; not client-only 4xx |
| **K3** | Hot object / small object storm → latency | `cos_bucket` (traffic) | TotalRequest ↑ + FirstByteDelay ↑; errors normal |
| **K4** | Network path (not COS) | `vpc_network` | Metrics normal; timeout only; Rule G evidence |

### Verification (read-only)

```bash
tccli cos ListBuckets --Region {{env.TENCENTCLOUD_REGION}}
# Use API for latest metric names:
tccli monitor DescribeBaseMetrics --Namespace QCE/COS
tccli monitor GetMonitorData --Namespace QCE/COS --MetricName 5xxResponse \
  --Instances '[{"Dimensions":[{"Name":"bucket","Value":"{{user.bucket_name}}-{{user.app_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
tccli monitor GetMonitorData --Namespace QCE/COS --MetricName 4xxResponse \
  --Instances '[{"Dimensions":[{"Name":"bucket","Value":"{{user.bucket_name}}-{{user.app_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
```

If `{{user.app_log_topic_id}}` or COS access-log CLS topic configured, search 403/5xx patterns per [`log-intelligence.md`](log-intelligence.md).

**Delegate:** `qcloud-cos-ops` (ACL, lifecycle, CORS); `qcloud-cam-ops` if K1; `qcloud-vpc-ops` if K4.

---

## 6. Rule L: CKafka Consumer Lag / Throughput / Disk

**Trigger:** `ConsumerGroupOffsetLag` ↑, `InstanceDiskUsage` > 85%, produce/consume stall, message backlog alarms.

| Evidence Layer | Signal | Scoring |
|---|---|---|
| CKafka | `ConsumerGroupOffsetLag` sustained high | +2 lag root |
| CKafka | `InstanceDiskUsage` > 85% | +2 disk pressure |
| CKafka | `InstanceMessagesIn` ↑ with flat `MessagesOut` | +2 consumer slower than producer |
| CKafka | `InstanceCpuUsage` / `InstanceMemoryUsage` high | +1 broker resource pressure |
| App/CLS | Consumer rebalance / commit failure logs | +1 symptom |
| Baseline | Lag/disk anomaly vs week | +1 |

### Hypotheses

| ID | Narrative | Root | HIGH when |
|---|---|---|---|
| **L1** | Consumer group stalled / slow processing → lag | `ckafka_instance` (consumer) | Lag ↑; MessagesIn > MessagesOut; consumer logs |
| **L2** | Broker disk full → produce/consume blocked | `ckafka_instance` (disk) | DiskUsage > 90%; retention not keeping pace |
| **L3** | Traffic spike / burst produce | `ckafka_instance` (throughput) | MessagesIn spike; lag transient then recovers |
| **L4** | Topic misconfig / ACL (not broker) | `app` | Broker metrics normal; client auth errors only |

### Verification (read-only)

```bash
tccli ckafka DescribeInstances --InstanceIdList '["{{user.resource_id}}"]' --Region {{env.TENCENTCLOUD_REGION}}
tccli monitor GetMonitorData --Namespace QCE/CKAFKA --MetricName ConsumerGroupOffsetLag \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
tccli monitor GetMonitorData --Namespace QCE/CKAFKA --MetricName InstanceDiskUsage \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
```

**Delegate:** `qcloud-ckafka-ops` (scale, retention, consumer group); app owner for L4.

---

## 7. Rule M: MongoDB Connection / Replication / CPU-Disk Chain

**Trigger:** `Connper` > 80%, `SlaveDelay` ↑, `MonogdMaxCpuUsage` high, `ClusterDiskUsage` > 85%, app timeout on MongoDB.

| Evidence Layer | Signal | Scoring |
|---|---|---|
| MongoDB | `Connper` > 85% or `ClusterConn` spike | +2 connection saturation |
| MongoDB | `SlaveDelay` / `NodeSlavedelay` > 60s | +2 replication lag root |
| MongoDB | `MonogdMaxCpuUsage` > 80% + `AvgAllRequestDelay` ↑ | +2 query/load pressure |
| MongoDB | `ClusterDiskUsage` > 85% | +2 capacity root |
| MongoDB | `HitRatio` drop + delay ↑ | +1 cache/working-set pressure |
| CDB/Redis/ES | N/A unless multi-product incident | cross-link only |
| Baseline | Qps/Connper anomaly | +1 |

### Hypotheses

| ID | Narrative | Root | HIGH when |
|---|---|---|---|
| **M1** | Connection pool leak / flash traffic → Connper max | `mongodb_instance` (connections) | Connper high; CPU moderate |
| **M2** | Primary load / missing index → CPU + delay | `mongodb_instance` (query) | CpuUsage high; AvgReadDelay/AvgAllRequestDelay ↑ |
| **M3** | Replication lag → read stale / secondary catch-up | `mongodb_instance` (replication) | SlaveDelay high; write burst window |
| **M4** | Disk watermark / oplog window risk | `mongodb_instance` (disk) | ClusterDiskUsage > 90% |
| **M5** | App misconfiguration; DB healthy | `app` | All MongoDB metrics normal |

### Verification (read-only)

```bash
tccli mongodb DescribeDBInstances --InstanceIds '["{{user.resource_id}}"]'
tccli monitor GetMonitorData --Namespace QCE/CMONGO --MetricName Connper \
  --Instances '[{"Dimensions":[{"Name":"target","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
tccli monitor GetMonitorData --Namespace QCE/CMONGO --MetricName SlaveDelay \
  --Instances '[{"Dimensions":[{"Name":"target","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
```

Optional: `tccli mongodb DescribeClientConnections --InstanceId {{user.resource_id}}` for connection source IPs (read-only).

**Delegate:** `qcloud-mongodb-ops` (scale, params, index advisory); app owner for M5.

---

## 8. Rule N: Postgres Slow Query / Connection / Replication

**Trigger:** `cpu_usage` ↑, slow query count ↑, connections max, `standby_replication_lag` ↑ (verify metric names via API).

| Evidence Layer | Signal | Scoring |
|---|---|---|
| Postgres | `cpu_usage` > 80% + slow query metric ↑ | +2 query regression |
| Postgres | connections near max | +2 pool exhaustion |
| Postgres | replication lag > 60s | +2 standby drift |
| Postgres | `disk_usage` > 85% | +2 capacity |
| Product API | `DescribeSlowQueryList` non-empty in window | +2 if matches app timeout |
| CLB/App | Timeout on PG-backed service | +1 symptom |
| Rule G | Network if timeout without DB load | +2 alternate |

### Hypotheses

| ID | Narrative | Root | HIGH when |
|---|---|---|---|
| **N1** | Bad query / missing index → CPU + slow queries | `postgres_instance` (query) | SlowQueryList + cpu_usage correlated |
| **N2** | Connection storm / pool leak | `postgres_instance` (connections) | Connections max; CPU moderate |
| **N3** | Standby replication lag | `postgres_instance` (replication) | Lag metric + write burst |
| **N4** | Disk/WAL growth | `postgres_instance` (disk) | disk_usage high |
| **N5** | Network not DB (Rule G) | `vpc_network` | DB metrics normal |

### Verification (read-only)

```bash
tccli postgres DescribeDBInstances --Filters '[{"Name":"db-instance-id","Values":["{{user.resource_id}}"]}]'
tccli monitor GetMonitorData --Namespace QCE/POSTGRES --MetricName cpu_usage \
  --Instances '[{"Dimensions":[{"Name":"DBInstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
tccli postgres DescribeSlowQueryList --DBInstanceId "{{user.resource_id}}" \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}"
```

> Metric names vary by PG version. Use `tccli monitor DescribeBaseMetrics --Namespace QCE/POSTGRES`.

**Delegate:** `qcloud-postgres-ops` (kill query, index, scale); `qcloud-vpc-ops` if N5.

---

## 9. Rule O: SCF Error / Timeout / Cold Start / Throttle

**Trigger:** `Error` / `FunctionError` ↑, `Duration` p99 spike, `Throttle` / concurrency limit, cold-start latency, API Gateway 502 on function backend.

| Evidence Layer | Signal | Scoring |
|---|---|---|
| SCF Monitor | Error count or error rate ↑ | +2 execution failure root |
| SCF Monitor | Duration p99 >> timeout budget | +2 timeout / slow dependency |
| SCF Monitor | Throttle / concurrent cap hit | +2 concurrency exhaustion |
| SCF Monitor | Invocation ↑ with flat errors | +1 traffic surge (symptom) |
| SCF API | `GetFunction` Memory/Timeout/VpcConfig changed recently | +2 if aligns with CloudAudit/Rule F |
| SCF logs | `GetFunctionLogs` OOM, timeout, unhandled exception | +2 if log precedes error metric |
| Downstream | CDB/Redis/VPC timeout in logs | +1 cross-link Rules H/I/G |
| Baseline | Duration/Error anomaly vs yesterday | +1 |

### Hypotheses

| ID | Narrative | Root | HIGH when |
|---|---|---|---|
| **O1** | Code bug / unhandled exception → Error spike | `scf_function` (code) | Error ↑ + exception stack in logs |
| **O2** | Timeout too low or slow downstream (DB/API) | `scf_function` (timeout/deps) | Duration at timeout ceiling; downstream errors in logs |
| **O3** | Cold start / large package / VPC ENI delay | `scf_function` (cold_start) | First-invocation latency spike; InitDuration high in logs |
| **O4** | Concurrency / account throttle | `scf_function` (quota) | Throttle metric ↑; 429 in logs |
| **O5** | Downstream healthy; trigger/API misconfig | `app` | Function metrics normal; API GW config issue |

### Verification (read-only)

```bash
tccli scf GetFunction --FunctionName "{{user.function_name}}" --Namespace "{{user.scf_namespace}}"
tccli scf GetFunctionLogs --FunctionName "{{user.function_name}}" --Namespace "{{user.scf_namespace}}" \
  --StartTime {{user.time_start_epoch}} --EndTime {{user.time_end_epoch}} --Limit 50
tccli monitor DescribeBaseMetrics --Namespace QCE/SCF
tccli monitor GetMonitorData --Namespace QCE/SCF --MetricName Error \
  --Instances '[{"Dimensions":[{"Name":"FunctionName","Value":"{{user.function_name}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
tccli monitor GetMonitorData --Namespace QCE/SCF --MetricName Duration \
  --Instances '[{"Dimensions":[{"Name":"FunctionName","Value":"{{user.function_name}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
```

> Metric names (`Error`, `Duration`, `Throttle`) vary — use `DescribeBaseMetrics --Namespace QCE/SCF`.

**Delegate:** `qcloud-scf-ops` (timeout/memory/concurrency config); downstream product skill if O2 cross-links.

---

## 10. Rule P: CDN Origin 5xx / Cache Miss / Edge Latency

**Trigger:** `StatusCode5XX` ↑, `CacheHitRate` ↓, `CdnResponseTime` ↑, origin pull failures, user reports CDN slow or stale content.

| Evidence Layer | Signal | Scoring |
|---|---|---|
| CDN | `StatusCode5XX` > 1% sustained | +2 origin error root |
| CDN | `StatusCode4XX` spike | +1 client/config symptom |
| CDN | `CacheHitRate` drop + bandwidth ↑ | +2 cache bust / misconfig |
| CDN | `CdnResponseTime` p99 ↑ | +2 latency root |
| CDN config | `DescribeDomainsConfig` origin offline/unhealthy | +2 origin unreachable |
| Origin product | COS/CVM/CLB metrics on origin (Rules K/A/G) | +2 if origin layer fails |
| Change | Domain/origin config change (Rule F2) | +2 if change precedes 5xx |
| Baseline | 5xx/latency anomaly vs week | +1 |

### Hypotheses

| ID | Narrative | Root | HIGH when |
|---|---|---|---|
| **P1** | Origin server 5xx/unhealthy | `cdn_domain` (origin) | StatusCode5XX ↑ + origin health/metrics bad |
| **P2** | Origin timeout / network to origin | `cdn_domain` (origin_path) | 5xx + Rule G or origin connect timeout |
| **P3** | Cache purge / bad Cache-Control → origin storm | `cdn_domain` (cache) | HitRate ↓ + bandwidth ↑; purge in CloudAudit |
| **P4** | CDN edge/config regression | `cdn_domain` (edge) | Origin healthy; 5xx only at edge metrics |
| **P5** | Client/request issue (4xx only) | `app` | StatusCode4XX ↑; 5xx normal |

### Verification (read-only)

```bash
tccli cdn DescribeDomainsConfig --Domains '["{{user.domain}}"]'
tccli monitor DescribeBaseMetrics --Namespace QCE/CDN
tccli monitor GetMonitorData --Namespace QCE/CDN --MetricName StatusCode5XX \
  --Instances '[{"Dimensions":[{"Name":"Domain","Value":"{{user.domain}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
tccli monitor GetMonitorData --Namespace QCE/CDN --MetricName CacheHitRate \
  --Instances '[{"Dimensions":[{"Name":"Domain","Value":"{{user.domain}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
tccli monitor GetMonitorData --Namespace QCE/CDN --MetricName CdnResponseTime \
  --Instances '[{"Dimensions":[{"Name":"Domain","Value":"{{user.domain}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300
```

Cross-link origin: if origin is COS → Rule K; CVM → CVM metrics; CLB → Rule A/multi-source RCA.

**Delegate:** `qcloud-cdn-ops` (origin/cache/HTTPS config); origin product skill (`qcloud-cos-ops`, `qcloud-cvm-ops`, `qcloud-clb-ops`) for P1/P2.

---

## 11. RCA Bundle Integration

When `resource_type` is `cdb`, `redis`, `es`, `cos`, `ckafka`, `mongodb`, `postgres`, `scf`, or `cdn`, populate:

```json
"product_rca": {
  "rule_set": "H|I|J|K|L|M|N|O|P",
  "resource_type": "cdn",
  "resource_id": "cdn.example.com",
  "hypotheses": [{"hypothesis_id": "P1", "confidence": "HIGH", "score": 6}]
},
"evidence_by_layer": {
  "cdb_metrics": {"status": "skipped"},
  "redis_metrics": {"status": "skipped"},
  "es_metrics": {"status": "skipped"},
  "cos_metrics": {"status": "skipped"},
  "ckafka_metrics": {"status": "skipped"},
  "mongodb_metrics": {"status": "skipped"},
  "postgres_metrics": {"status": "skipped"},
  "scf_metrics": {"status": "skipped"},
  "cdn_metrics": {"status": "complete", "evidence_count": 4}
}
```

Cross-link to CLB/VPC/origin layers when user supplies `{{user.load_balancer_id}}`, `{{user.vpc_id}}`, or origin domain from `DescribeDomainsConfig`.

## 12. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-09 | Rules H/I/J for CDB slow-query chain, Redis memory/connection storm, ES cluster health |
| 2.0.0 | 2026-06-13 | **Phase F:** Rules K–N (COS, CKafka, MongoDB, Postgres) |
| 2.1.0 | 2026-06-13 | **Phase F cont.:** Rules O (SCF error/timeout/throttle), P (CDN origin 5xx/cache/latency) |
