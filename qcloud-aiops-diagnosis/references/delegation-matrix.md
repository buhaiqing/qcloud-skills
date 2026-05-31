# Delegation Matrix — AIOps Diagnosis

## Cross-Skill Diagnosis Routing

| Source Skill | Delegates To | Trigger |
|-------------|-------------|---------|
| qcloud-cvm-ops | qcloud-aiops-diagnosis | Performance degradation, OOM, CPU spike |
| qcloud-redis-ops | qcloud-aiops-diagnosis | Memory growth, connection storm, slow commands |
| qcloud-cdb-ops | qcloud-aiops-diagnosis | Slow queries, lock contention, connection exhaustion |
| qcloud-tke-ops | qcloud-aiops-diagnosis | Pod crashes, node failures, resource pressure |
| qcloud-es-ops | qcloud-aiops-diagnosis | Cluster red/yellow, indexing slowdown |
| qcloud-clb-ops | qcloud-aiops-diagnosis | Backend health failure, connection drops, CLS log anomaly correlation |
| qcloud-monitor-ops | qcloud-aiops-diagnosis | Alarm storm, multi-metric correlation |
| qcloud-cos-ops | qcloud-aiops-diagnosis | Request latency spike, error rate increase |

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
