# TKE Pod RCA Fast Path

> AIOps-native triage for TKE Pod failures. Distinct from `qcloud-tke-ops/references/troubleshooting.md` (product ops runbook) — this focuses on **alarm aggregation → 4-layer cross-topology → RCA Bundle**. Target MTTR < 30 min.

## Quick Start

```text
Pod CrashLoop/OOM/kill alarm → fetch Pod/Node/CLB/CVM 4-layer evidence → topology correlation → RCA Bundle
```

## 4-Layer Triage Tree

```
Pod alarm detected (CrashLoop/OOM/OOMKilled/Evicted/NotReady)
  ↓
Layer 1: Pod itself
  Containers restart count? Exit code?
  OOMKilled? → memory limit hit
  CrashLoopBackOff? → liveness probe fail / init error
  ImagePullBackOff? → registry auth / image tag
  ↓
Layer 2: Node pressure (per [`tke-node-pressure.md`](tke-node-pressure.md))
  Node condition: MemoryPressure / DiskPressure / PIDPressure?
  Node allocatable vs pod requests/limits
  → Node pressure → other pods on same node affected?
  ↓
Layer 3: CLB backend (per [`clb-backend-health.md`](clb-backend-health.md))
  Pod endpoint removed from CLB target group?
  Health check failure → all traffic diverted → 502/504
  → Same CLB → other backend pods healthy?
  ↓
Layer 4: CVM (per [`cvm-performance-diagnosis-optimized.md`](cvm-performance-diagnosis-optimized.md))
  Node host CVM CPU/Mem/Disk saturation?
  → Node not ready → pod eviction
```

## Evidence Collection Commands

```bash
# Layer 1: Pod status
kubectl get pod {{user.pod_name}} -n {{user.namespace}} -o wide
kubectl describe pod {{user.pod_name}} -n {{user.namespace}}
kubectl logs {{user.pod_name}} -n {{user.namespace}} --previous 2>/dev/null

# Layer 2: Node pressure
kubectl get node {{user.node_name}} -o go-template='{{range .status.conditions}}{{.type}}={{.status}} {{end}}'
kubectl top node {{user.node_name}} --no-headers

# Layer 3: CLB backend (via TKE console or tccli)
tccli clb DescribeTargets \
  --LoadBalancerIds '["{{user.lb_id}}"]' \
  --SearchTargets '[{"TargetValue":"{{user.pod_ip}}"}]'

# Layer 4: CVM node metrics
tccli monitor GetMonitorData \
  --Namespace QCE/CVM --MetricName CpuUsage \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.node_instance_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 60
```

## Hypothesis Scoring

| Hypothesis | Evidence | Score |
|-----------|----------|-------|
| **TP1**: Pod OOM → memory limit too low | `OOMKilled` exit + memory limit vs usage | +3 |
| **TP2**: Liveness probe fail → app crash | `CrashLoopBackOff` + probe logs | +3 |
| **TP3**: Node MemoryPressure → evictions | `MemoryPressure` node condition + same-node pods affected | +2 |
| **TP4**: CLB health check fail → 502 | Pod IP removed from target group + CLB 5xx | +2 |
| **TP5**: Node DiskPressure → pod eviction | `DiskPressure` node condition + `Evicted` pod | +2 |
| **TP6**: CVM saturation → node not ready | Node CVM CPU > 90% + `NotReady` | +2 |
| **TP7**: App misconfig → self-crash | Exit code 1/137 + no node/net issue | +1 |

## Alarm Aggregation

TKE alarm storms often bundle: Node NotReady + Pod Evicted + Pod OOMKilled + CLB 5xx. Correlate by:

- **Time coincidence** within 5-min window → single incident
- **Same node** → group Node + Pod events
- **Same CLB** → group backend + 5xx events

See [`alarm-handling.md`](alarm-handling.md) §TKE Grouping Keys.

## Cross-Link Rules

| Trigger | Link to |
|---------|---------|
| TKE → CDB slow query (DB-backed pod) | Rule H (`product-rca-rules.md` §2) |
| TKE → Redis connection refused | Rule I (`product-rca-rules.md` §3) |
| TKE → CloudAudit recent deployment | Rule F (`change-correlation.md`) |
| TKE → VPC CNI / network policy | Rule G (`network-rca.md`) |

## Output

`RCA Bundle` with `topology_links[]` connecting Pod → Node → CLB → CVM.

**Delegate:** `qcloud-tke-ops` for remediation (evict, cordon, restart, limit adjust).

## See also

- [`multi-source-rca.md`](multi-source-rca.md) — cross-layer RCA methodology
- [`alarm-handling.md`](alarm-handling.md) — storm bundling
- [`cvm-performance-diagnosis-optimized.md`](cvm-performance-diagnosis-optimized.md) — Layer 4 CVM triage
