# AIOps Diagnosis CLI Usage — TKE Alarm Aggregation

This cross-cutting diagnosis skill is **CLI-first with SDK fallback**. All commands here are read-only collection steps for TKE alarm noise reduction and Event Bundle generation.

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

## SDK Fallback

Use `tencentcloud-sdk-python` when CLI JSON quoting, pagination, or batch fan-in becomes cumbersome. Keep the same read-only boundary.

### SDK Client Setup

```python
import os
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.monitor import monitor_client, models as monitor_models
from tencentcloud.tke import tke_client, models as tke_models
from tencentcloud.clb import clb_client, models as clb_models
from tencentcloud.cls import cls_client, models as cls_models

# Credential from environment (never print secret values)
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")

# Clients (use _cli suffix to avoid shadowing module names)
monitor_cli = monitor_client.MonitorClient(cred, region)
tke_cli = tke_client.TkeClient(cred, region)
clb_cli = clb_client.ClbClient(cred, region)
cls_cli = cls_client.ClsClient(cred, region)
```

### Allowed Methods by Product

| Product | SDK client | Allowed methods |
|---|---|---|
| Monitor | `monitor_client.MonitorClient` | `DescribeAlarmHistories`, `GetMonitorData`, `DescribeAllNamespaces` (`SceneType=ST_ALARM`), `DescribeBaseMetrics` |
| TKE | `tke_client.TkeClient` | `DescribeClusters`, `DescribeClusterInstances`, `DescribeClusterNodePools`, `DescribeClusterNodePoolDetail`, `DescribeAddon`, `DescribePodsBySpec` (best-effort with CPU/Memory filters), `DescribeResourceUsage` |
| CLB | `clb_client.ClbClient` | `DescribeTargetHealth`, `DescribeTargets` |
| CLS | `cls_client.ClsClient` | `SearchLog` |
| CloudAudit | `cloudaudit_client.CloudauditClient` | `LookUpEvents` |

### SDK Example: Monitor Alarm History

```python
def describe_alarm_histories(start_time: int, end_time: int) -> dict:
    """Query TKE alarm history via SDK fallback.

    Args:
        start_time: Unix epoch seconds
        end_time: Unix epoch seconds

    Returns:
        Alarm history response dict
    """
    req = monitor_models.DescribeAlarmHistoriesRequest()
    req.Module = "monitor"
    req.Namespaces = [{"MonitorType": "MT_QCE", "Namespace": "QCE/TKE"}]
    req.StartTime = start_time
    req.EndTime = end_time
    req.PageNumber = 1
    req.PageSize = 100

    try:
        resp = monitor_cli.DescribeAlarmHistories(req)
        return resp.to_json_string()
    except TencentCloudSDKException as e:
        return {"error": str(e), "code": e.get_code()}
```

### SDK Example: TKE Cluster Inventory

```python
def describe_cluster_context(cluster_id: str) -> dict:
    """Collect TKE cluster context via SDK.

    Args:
        cluster_id: TKE cluster ID (cls-xxxxxx)

    Returns:
        Cluster context with nodes, node pools, addons
    """
    result = {"cluster_id": cluster_id, "sources": {}}

    # Cluster info
    req = tke_models.DescribeClustersRequest()
    req.ClusterIds = [cluster_id]
    try:
        resp = tke_cli.DescribeClusters(req)
        result["sources"]["cluster"] = resp.to_json_string()
    except TencentCloudSDKException as e:
        result["sources"]["cluster"] = {"error": str(e)}

    # Node instances
    req = tke_models.DescribeClusterInstancesRequest()
    req.ClusterId = cluster_id
    try:
        resp = tke_cli.DescribeClusterInstances(req)
        result["sources"]["nodes"] = resp.to_json_string()
    except TencentCloudSDKException as e:
        result["sources"]["nodes"] = {"error": str(e)}

    # Node pools
    req = tke_models.DescribeClusterNodePoolsRequest()
    req.ClusterId = cluster_id
    try:
        resp = tke_cli.DescribeClusterNodePools(req)
        result["sources"]["node_pools"] = resp.to_json_string()
    except TencentCloudSDKException as e:
        result["sources"]["node_pools"] = {"error": str(e)}

    return result
```

### SDK Example: CLS Log Search

```python
def search_cls_events(topic_id: str, query: str, start_time: int, end_time: int) -> dict:
    """Search CLS logs via SDK.

    Args:
        topic_id: CLS topic ID
        query: Query string (e.g., "(level:Warning OR level:Error) AND cluster_id:cls-xxx")
        start_time: Unix epoch seconds
        end_time: Unix epoch seconds

    Returns:
        Log search results
    """
    req = cls_models.SearchLogRequest()
    req.TopicId = topic_id
    req.Query = query
    req.StartTime = start_time
    req.EndTime = end_time
    req.Limit = 100

    try:
        resp = cls_cli.SearchLog(req)
        return resp.to_json_string()
    except TencentCloudSDKException as e:
        return {"error": str(e), "code": e.get_code(), "data_quality": {"degraded": True}}
```

### Safety Constraints

Do not call mutation APIs (`Create*`, `Modify*`, `Delete*`, `Install*`, `Update*`, `Drain*`, scaling APIs). Recommendations must be emitted as `RECOMMENDATION (not execution)` and delegated to product skills.

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

### Product RCA collection (CDB / Redis / ES)

See [`product-rca-rules.md`](product-rca-rules.md). Examples:

```bash
tccli cdb DescribeDBInstances --InstanceIds '["{{user.resource_id}}"]'
tccli monitor GetMonitorData --Namespace QCE/CDB --MetricName SlowQueries \
  --Instances '[{"Dimensions":[{"Name":"instanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300

tccli redis DescribeInstances --InstanceId "{{user.resource_id}}"
tccli monitor GetMonitorData --Namespace QCE/REDIS --MetricName Storage \
  --Instances '[{"Dimensions":[{"Name":"instanceid","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300

tccli es DescribeInstances --InstanceIds '["{{user.resource_id}}"]'
```

### VPC network path (Rule G)

See [`network-rca.md`](network-rca.md). Infer `vpc_id` from `DescribeInstances` when omitted.

```bash
tccli cvm DescribeInstances --InstanceIds '["{{user.instance_id}}"]'
tccli vpc DescribeSecurityGroups --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'
tccli vpc DescribeRouteTables --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'
tccli vpc DescribeNatGateways --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'
```

### SDK Fallback (RCA additions)

| Product | SDK client | Additional RCA methods |
|---|---|---|
| CVM | `cvm_client.CvmClient` | `DescribeInstances` |
| CDB | `cdb_client.CdbClient` | `DescribeDBInstances` |
| Redis | `redis_client.RedisClient` | `DescribeInstances` |
| ES | `es_client.EsClient` | `DescribeInstances` |
| VPC | `vpc_client.VpcClient` | `DescribeSecurityGroups`, `DescribeRouteTables`, `DescribeNatGateways` |

## Output

Normalize raw data into the Event Bundle schema in [`alarm-handling.md`](alarm-handling.md), or the Multi-Source RCA Bundle schema in [`multi-source-rca.md`](multi-source-rca.md), including `data_quality.status`, `data_quality.degraded`, `missing_sources`, `warnings`, `source_recency`, and `evidence_by_layer`.

See [`multi-source-rca.md`](multi-source-rca.md) §4 for the RCA Bundle output schema. After bundling, assemble Incident Timeline per [`incident-timeline.md`](incident-timeline.md); persist to `./audit-results/incident-timeline-YYYYMMDD-HHMMSS.json`.

Anomaly-only scans: output schema in [`anomaly-detection.md`](anomaly-detection.md) §6; persist to `./audit-results/anomaly-bundle-YYYYMMDD-HHMMSS.json`.

Impact assessment uses CLB `DescribeTargetHealth` / `DescribeTargets` (see [`incident-knowledge.md`](incident-knowledge.md) §1). KB records persist to `./audit-results/incident-kb-YYYYMMDD-HHMMSS.json`; optional index at `./audit-results/incident-kb-index.json`.

Cross-skill orchestration: do **not** call billing APIs from this skill during F1/F2 — consume `{{user.finops_handoff}}` from `qcloud-finops-ops`. Persist merged output to `./audit-results/cross-skill-bundle-YYYYMMDD-HHMMSS.json` per [`cross-skill-orchestration.md`](cross-skill-orchestration.md).
