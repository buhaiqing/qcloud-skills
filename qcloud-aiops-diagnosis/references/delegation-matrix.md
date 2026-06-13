# Delegation Matrix — AIOps Diagnosis

## Cross-Skill Diagnosis Routing

| Source Skill | Delegates To | Trigger |
|-------------|-------------|---------|
| qcloud-cvm-ops | qcloud-aiops-diagnosis | Performance degradation, OOM, CPU spike |
| qcloud-redis-ops | qcloud-aiops-diagnosis | Memory growth, connection storm, slow commands |
| qcloud-cdb-ops | qcloud-aiops-diagnosis | Slow queries, lock contention, connection exhaustion |
| qcloud-tke-ops | qcloud-aiops-diagnosis | Pod crashes, node failures, resource pressure, TKE alarm storm/event aggregation |
| qcloud-es-ops | qcloud-aiops-diagnosis | Cluster red/yellow, indexing slowdown |
| qcloud-clb-ops | qcloud-aiops-diagnosis | Backend health failure, connection drops, CLS log anomaly correlation, CLB 5xx → TKE backend correlation |
| qcloud-monitor-ops | qcloud-aiops-diagnosis | Alarm storm, multi-metric correlation, alarm history collection for event bundles |
| qcloud-cos-ops | qcloud-aiops-diagnosis | Request latency spike, error rate increase |
| qcloud-ckafka-ops | qcloud-aiops-diagnosis | Consumer lag, disk usage, throughput imbalance |
| qcloud-mongodb-ops | qcloud-aiops-diagnosis | Connection saturation, replication lag, CPU/disk pressure |
| qcloud-postgres-ops | qcloud-aiops-diagnosis | Slow queries, connection exhaustion, replication lag |
| qcloud-scf-ops | qcloud-aiops-diagnosis | Function errors, timeout, cold start, throttle/concurrency |
| qcloud-cdn-ops | qcloud-aiops-diagnosis | Origin 5xx, cache hit drop, edge latency |

## Internal Routing (within aiops-diagnosis)

| Symptom Category | Primary Analysis | Secondary Analysis |
|-----------------|------------------|-------------------|
| Performance | Metric threshold check | Log correlation |
| Availability | Health check status | Dependency chain trace |
| Capacity | Resource utilization trend | Growth rate projection |
| Security | CAM audit log review | Network anomaly detection |

## Alarm Storm → Root Cause Chain

```
Alarm storm detected
  → Deduplicate by resource_id + metric_name
  → Find earliest alarm (root trigger)
  → Apply diagnostic workflow from diagnostic-workflows.md
  → Correlate with logs from log-intelligence.md
  → Output: root cause + resolution strategy
```

## Multi-Source RCA Delegation

When the agent performs Multi-Source Root Cause Localization (see [`multi-source-rca.md`](multi-source-rca.md)), the evidence collection and recommendation delegation follows:

| Evidence Layer | Read From | Delegates Mutation To |
|---|---|---|
| CLB 5xx / backend health | `qcloud-clb-ops` (read-only: DescribeTargetHealth, DescribeTargets) | `qcloud-clb-ops` for config changes |
| Node / Pod pressure | `qcloud-tke-ops` (read-only: DescribeClusters, DescribeClusterInstances, DescribeClusterNodePools, DescribeAddon) | `qcloud-tke-ops` for node pool changes, pod/workload actions |
| CVM metrics / instance | `qcloud-cvm-ops` (read-only: DescribeInstances, Monitor GetMonitorData) | `qcloud-cvm-ops` for VM diagnostics |
| Monitor metrics / alarms | `qcloud-monitor-ops` (read-only: GetMonitorData, DescribeAlarmHistories) | `qcloud-monitor-ops` for alarm policy tuning |
| CLS logs | `cls` (read-only: SearchLog) | App owner for code/config fixes |

> RCA collection is read-only. All mutation recommendations use the prefix `RECOMMENDATION (not execution)` and are delegated to the listed skill.

## TKE Alarm Aggregation Routing

| Input Signal | Read From | Correlate With | Recommendation Delegation |
|---|---|---|---|
| NodeNotReady / NodePressure | `qcloud-tke-ops` + `qcloud-monitor-ops` | Pod CrashLoopBackOff, CLB backend health, CVM CPU/memory | `qcloud-tke-ops` for node drain/replace; `qcloud-cvm-ops` for VM diagnostics |
| Pod CrashLoopBackOff / OOMKilled | `qcloud-tke-ops` + CLS | Node pressure, image pull, app logs | `qcloud-tke-ops` for workload/node actions; app owner for code/config |
| PodPending / Capacity | `qcloud-tke-ops` + Monitor quota metrics | NodePool Desired/Max, HPA max, quota | `qcloud-tke-ops` for node pool changes; `qcloud-monitor-ops` for alert tuning |
| CLB 5xx / HealthCheckFail | `qcloud-clb-ops` + `qcloud-tke-ops` | Backend pod/node health | `qcloud-clb-ops` for LB config; `qcloud-tke-ops` for backend health |
| DNS / metrics-server / network addon | `qcloud-tke-ops` + CLS | Addon pods, node pressure | `qcloud-tke-ops` for addon remediation |

> Routing boundary: `qcloud-aiops-diagnosis` reads and aggregates only. All remediation is `RECOMMENDATION (not execution)` and delegated to the listed skill.

## Change Correlation Routing

| Change signal | Read from | Correlate with | Delegate fix to |
|---|---|---|---|
| Deployment / rollout (CLS K8s event) | CLS + TKE inventory | Pod CrashLoop, CLB 5xx, error-rate spike (Rule F) | `qcloud-tke-ops` rollback; app owner for code |
| CLB config change (CloudAudit) | `cloudaudit LookUpEvents` + CLB Describe* | CLB 5xx without pod crash (F2) | `qcloud-clb-ops` |
| SG / route change (CloudAudit) | CloudAudit + optional VPC read | Connection timeout/refused (F4) | `qcloud-vpc-ops` |
| Node pool scale / CVM reboot | CloudAudit + TKE/CVM | NodeNotReady, transient pod pending (F3) | `qcloud-tke-ops` / `qcloud-cvm-ops` |
| CAM / credential change | CloudAudit | Auth errors in CLS logs | `qcloud-cam-ops` |
| Alarm policy change | CloudAudit + Monitor | New alarm storm vs real incident | `qcloud-monitor-ops` |

Incident Timeline assembly is internal to this skill; no mutation. See [`incident-timeline.md`](incident-timeline.md).

## Baseline Anomaly Routing

| Finding | Detection | Correlate with | Delegate when sustained |
|---|---|---|---|
| CpuUsage/MemUsage anomaly (ratio ≥ 1.5) | [`anomaly-detection.md`](anomaly-detection.md) | NetworkIn, alarms, CLS logs | `qcloud-cvm-ops` right-size / investigate |
| Redis Storage/Connections anomaly | Multi-window REDIS metrics | Slow commands, connection errors | `qcloud-redis-ops` |
| CDB Qps/SlowQueries anomaly | Multi-window CDB metrics | Lock wait, VPC latency | `qcloud-cdb-ops` |
| CKafka lag/disk anomaly | Multi-window CKAFKA metrics | Consumer stall logs | `qcloud-ckafka-ops` |
| MongoDB Connper/SlaveDelay anomaly | Multi-window CMONGO metrics | App timeout | `qcloud-mongodb-ops` |
| Postgres cpu/slow-query anomaly | Multi-window POSTGRES metrics | CLB timeout | `qcloud-postgres-ops` |
| COS 4xx/5xx anomaly | Multi-window COS metrics | CLS access log | `qcloud-cos-ops` |
| SCF Error/Duration anomaly | Multi-window SCF metrics | GetFunctionLogs | `qcloud-scf-ops` |
| CDN StatusCode5XX anomaly | Multi-window CDN metrics | Origin health (COS/CVM/CLB) | `qcloud-cdn-ops` + origin skill |
| CLB UnhealthNum/DropTotal anomaly | Multi-window LB metrics | TKE backend health, RCA Rule A | `qcloud-clb-ops` + `qcloud-tke-ops` |
| Gradual week-over-week drift | Week ratio > yesterday ratio | FinOps cost trend | `qcloud-finops-ops` (advisory) |

Proactive-only scans output **Anomaly Bundle**; incident response embeds `anomaly_findings[]` in RCA Bundle.

## Product RCA Routing (Rules H–P)

| Rule | Trigger | Read from | Cross-correlate | Delegate fix |
|---|---|---|---|---|
| **H** CDB | SlowQueries, CPU, connections | `qcloud-cdb-ops` Describe + Monitor QCE/CDB | CLB 5xx, CLS slow log, Rule G | `qcloud-cdb-ops` |
| **I** Redis | Storage, Connections | `qcloud-redis-ops` Describe + Monitor QCE/REDIS | App pool errors, CLB timeout | `qcloud-redis-ops` |
| **J** ES | Red/yellow, JVM, latency | `qcloud-es-ops` Describe + Monitor QCE/CES | Search timeout logs | `qcloud-es-ops` |
| **K** COS | 4xx/5xx, latency, TotalRequest | `qcloud-cos-ops` ListBuckets + Monitor QCE/COS | CLS access log, CAM change | `qcloud-cos-ops` |
| **L** CKafka | Lag, disk, MessagesIn/Out | `qcloud-ckafka-ops` Describe + Monitor QCE/CKAFKA | Consumer logs | `qcloud-ckafka-ops` |
| **M** MongoDB | Connper, SlaveDelay, CPU/disk | `qcloud-mongodb-ops` Describe + Monitor QCE/CMONGO | App timeout | `qcloud-mongodb-ops` |
| **N** Postgres | CPU, slow query, connections, lag | `qcloud-postgres-ops` Describe + Monitor QCE/POSTGRES | CLB 5xx, Rule G | `qcloud-postgres-ops` |
| **O** SCF | Error, Duration, Throttle | `qcloud-scf-ops` GetFunction/Logs + Monitor QCE/SCF | Downstream DB/VPC | `qcloud-scf-ops` |
| **P** CDN | 5xx, CacheHitRate, latency | `qcloud-cdn-ops` DescribeDomainsConfig + Monitor QCE/CDN | Origin Rules K/A/G | `qcloud-cdn-ops` + origin skill |

See [`product-rca-rules.md`](product-rca-rules.md).

## Network RCA Routing (Rule G)

| Trigger | Read from | Delegate fix |
|---|---|---|
| Timeout/refused; metrics normal | `qcloud-vpc-ops` SG/route/NAT Describe* + CloudAudit | `qcloud-vpc-ops` |
| NodeNotReady + CVM Running | Rule D + Rule G | `qcloud-vpc-ops` then `qcloud-tke-ops` |
| F4 SG/route change | [`change-correlation.md`](change-correlation.md) + Rule G | `qcloud-vpc-ops` |

See [`network-rca.md`](network-rca.md).

## Incident Knowledge Routing

| Step | Action | Output |
|---|---|---|
| Impact assessment | CLB `DescribeTargetHealth` + alarm counts | `impact` block on bundle |
| Similar cases | Read `./audit-results/incident-kb-*.json` | `similar_incidents[]` (advisory) |
| KB write | After bundle complete | `incident-kb-*.json` + index update |
| User feedback | `{{user.feedback_was_accurate}}` | Update KB `resolution.*` |

See [`incident-knowledge.md`](incident-knowledge.md). No mutation from KB layer.

## Cross-Skill Orchestration (Phase E)

Bidirectional flows — full spec [`cross-skill-orchestration.md`](cross-skill-orchestration.md).

| Direction | Mode | Trigger | This skill action | Delegate to |
|---|---|---|---|---|
| FinOps → AIOps | F1 | Bill anomaly HIGH + dispatch_inspection | Receive handoff; after inspection, RCA | `qcloud-proactive-inspection` first |
| FinOps → AIOps | F2 | Bill anomaly + product delta | Joint hypothesis + RCA/anomaly | `qcloud-finops-ops` for bill context only |
| Inspection → AIOps | P1 | CRITICAL/HIGH finding | Deep RCA validate | source: `qcloud-proactive-inspection` |
| AIOps → Inspection | A1 | Post-incident prevention | `prevention_items[]` | `qcloud-proactive-inspection` |
| AIOps → FinOps | A2 | Capacity/saturation/drift | `finops_advisory` | `qcloud-finops-ops` |

**Boundary:** AIOps does not own `DescribeBill*` as primary path; FinOps does not own RCA bundles.
