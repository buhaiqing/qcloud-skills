# Delegation Matrix — AIOps Diagnosis

## Cross-Skill Diagnosis Routing

| Source Skill | Delegates To | Trigger |
|-------------|-------------|---------|
| qcloud-cvm-ops | qcloud-aioops-diagnosis | Performance degradation, OOM, CPU spike |
| qcloud-redis-ops | qcloud-aioops-diagnosis | Memory growth, connection storm, slow commands |
| qcloud-cdb-ops | qcloud-aioops-diagnosis | Slow queries, lock contention, connection exhaustion |
| qcloud-tke-ops | qcloud-aioops-diagnosis | Pod crashes, node failures, resource pressure |
| qcloud-es-ops | qcloud-aioops-diagnosis | Cluster red/yellow, indexing slowdown |
| qcloud-clb-ops | qcloud-aioops-diagnosis | Backend health failure, connection drops |
| qcloud-monitor-ops | qcloud-aioops-diagnosis | Alarm storm, multi-metric correlation |
| qcloud-cos-ops | qcloud-aioops-diagnosis | Request latency spike, error rate increase |

## Internal Routing (within aioops-diagnosis)

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
