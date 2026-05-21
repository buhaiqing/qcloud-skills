# TKE Monitoring & Alerts

## Overview

TKE monitoring integrates with Tencent Cloud Monitor (TCOP) to provide cluster-level, node-level, and workload-level observability. The monitoring namespace is **QCE/TKE**.

## Metrics

### Cluster-Level Metrics

| Metric Name | Unit | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| `cluster_running_nodes` | Count | Number of running nodes in cluster | `< min_node_count` |
| `cluster_total_nodes` | Count | Total number of nodes (running + abnormal) | — |
| `cluster_node_status` | Status | Overall cluster health (0=healthy, 1=abnormal) | `== 1` |
| `cluster_pod_count` | Count | Total pods running across all nodes | Sudden drops |

### Node-Level Metrics

Retrieved via **QCE/CVM** for each worker node:

| Metric Name | Unit | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| `CpuUsage` | % | Node CPU utilization | > 85% sustained |
| `MemUsage` | % | Node memory utilization | > 90% sustained |
| `DiskUsage` | % | Node disk utilization | > 85% |
| `NetworkIn` | KB/s | Incoming network traffic | Sudden spikes |
| `NetworkOut` | KB/s | Outgoing network traffic | Sudden spikes |

### Kubernetes Workload Metrics (via metrics-server addon)

| Metric Name | Unit | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| `pod_cpu_usage` | millicore | Pod CPU usage | > limits for 5min |
| `pod_memory_usage` | bytes | Pod memory usage | Near OOM Kill |
| `pod_restart_count` | Count | Pod restart events | > 5 in 10min |

## Query Monitor Data via API

### Get Cluster Node Metrics

```bash
tccli monitor GetMonitorData \
  --Namespace "QCE/TKE" \
  --MetricName "cluster_running_nodes" \
  --Instances.0.Dimensions.0.Name "clusterid" \
  --Instances.0.Dimensions.0.Value "{{user.cluster_id}}" \
  --Period 300 \
  --StartTime "2026-05-21 00:00:00" \
  --EndTime "2026-05-21 23:59:59"
```

### Get Node CVM Metrics

```bash
tccli monitor GetMonitorData \
  --Namespace "QCE/CVM" \
  --MetricName "CpuUsage" \
  --Instances.0.Dimensions.0.Name "uninstanceid" \
  --Instances.0.Dimensions.0.Value "{{user.node_instance_id}}" \
  --Period 60 \
  --StartTime "2026-05-21 00:00:00" \
  --EndTime "2026-05-21 23:59:59"
```

## Alert Rule Templates

### Cluster Health Alert

- **Metric:** `cluster_node_status == 1`
- **Period:** 1 minute
- **Threshold:** continuous 3 periods
- **Action:** Notify via webhook/SMS
- **Severity:** Critical

### Node Resource Exhaustion Alert

- **Metric:** `CpuUsage > 85%` OR `MemUsage > 90%`
- **Period:** 5 minutes
- **Threshold:** continuous 3 periods
- **Action:** Notify + auto-scale node pool (if configured)
- **Severity:** Warning

### Node Pool Scaling Alert

- **Condition:** Node pool reaches `MaxNum`
- **Action:** Notify — may indicate need to increase MaxNum
- **Severity:** Warning

### Pod Crash Alert (via metrics-server)

- **Metric:** `pod_restart_count > 5` in 10 minutes
- **Action:** Notify — investigate pod logs
- **Severity:** Critical

## Dashboard Integration

TKE integrates with Grafana via:

1. **Tencent Cloud Dashboard** — Built-in TKE dashboards in TCOP console
2. **Prometheus Managed** — Use tke-connector-prometheus addon for Grafana
3. **Custom Grafana** — Connect to TKE metrics-server with kube-state-metrics

## Recommended Alerts by Severity

| Severity | Metric | Condition | Notification |
|----------|--------|-----------|--------------|
| P0 (Critical) | Cluster status abnormal | Any | Immediate SMS + webhook |
| P0 (Critical) | All nodes down | Running nodes = 0 | Immediate SMS |
| P1 (Warning) | Node CPU/Memory > threshold | Sustained 15min | Slack/Email |
| P1 (Warning) | Node pool at MaxNum | Capacity reached | Email |
| P2 (Info) | Cluster version outdated | LTS version EOL approaching | Weekly digest |