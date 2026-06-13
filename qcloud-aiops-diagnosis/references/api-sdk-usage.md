# AIOps Diagnosis — API & SDK Usage

Python SDK fallback for `qcloud-aiops-diagnosis`. **CLI is primary** — see [`cli-usage.md`](cli-usage.md). Use SDK when JSON quoting, pagination loops, or batch fan-in become cumbersome. **Read-only boundary:** no `Create*` / `Modify*` / `Delete*` / `Install*` / `Update*` / `Drain*`.

## Preconditions

Same as CLI: credentials from environment only; ISO → epoch for alarm/CLS windows; missing optional IDs → skip layer and set `data_quality.degraded=true`.

## SDK Client Setup

```python
import os
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.monitor import monitor_client, models as monitor_models
from tencentcloud.tke import tke_client, models as tke_models
from tencentcloud.clb import clb_client, models as clb_models
from tencentcloud.cls import cls_client, models as cls_models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")

monitor_cli = monitor_client.MonitorClient(cred, region)
tke_cli = tke_client.TkeClient(cred, region)
clb_cli = clb_client.ClbClient(cred, region)
cls_cli = cls_client.ClsClient(cred, region)
```

## Allowed Methods by Product

| Product | SDK client | Allowed methods |
|---|---|---|
| Monitor | `monitor_client.MonitorClient` | `DescribeAlarmHistories`, `GetMonitorData`, `DescribeAllNamespaces` (`SceneType=ST_ALARM`), `DescribeBaseMetrics` |
| TKE | `tke_client.TkeClient` | `DescribeClusters`, `DescribeClusterInstances`, `DescribeClusterNodePools`, `DescribeClusterNodePoolDetail`, `DescribeAddon`, `DescribePodsBySpec` (degraded; needs CPU/Memory filters), `DescribeResourceUsage` |
| CLB | `clb_client.ClbClient` | `DescribeTargetHealth`, `DescribeTargets` |
| CLS | `cls_client.ClsClient` | `SearchLog` |
| CloudAudit | `cloudaudit_client.CloudauditClient` | `LookUpEvents` |
| CVM | `cvm_client.CvmClient` | `DescribeInstances` |
| CDB | `cdb_client.CdbClient` | `DescribeDBInstances` |
| Redis | `redis_client.RedisClient` | `DescribeInstances` |
| ES | `es_client.EsClient` | `DescribeInstances` |
| COS | `cos_client.CosClient` | `ListBuckets` (SDK); metrics via Monitor client |
| CKafka | `ckafka_client.CkafkaClient` | `DescribeInstances` |
| MongoDB | `mongodb_client.MongodbClient` | `DescribeDBInstances`, `DescribeClientConnections` |
| Postgres | `postgres_client.PostgresClient` | `DescribeDBInstances`, `DescribeSlowQueryList` |
| SCF | `scf_client.ScfClient` | `GetFunction`, `GetFunctionLogs`, `ListFunctions` |
| CDN | `cdn_client.CdnClient` | `DescribeDomainsConfig`, `DescribeCdnData` |
| VPC | `vpc_client.VpcClient` | `DescribeSecurityGroups`, `DescribeRouteTables`, `DescribeNatGateways` |

## SDK Example: Monitor Alarm History (with pagination)

```python
def describe_alarm_histories_paged(start_time: int, end_time: int, max_alarms: int = 100) -> dict:
    collected = []
    page = 1
    page_size = 100
    while len(collected) < max_alarms:
        req = monitor_models.DescribeAlarmHistoriesRequest()
        req.Module = "monitor"
        req.Namespaces = [{"MonitorType": "MT_QCE", "Namespace": "QCE/TKE"}]
        req.StartTime = start_time
        req.EndTime = end_time
        req.PageNumber = page
        req.PageSize = page_size
        try:
            resp = monitor_cli.DescribeAlarmHistories(req)
            batch = resp.Histories or []
            collected.extend(batch)
            if len(batch) < page_size:
                break
            page += 1
        except TencentCloudSDKException as e:
            return {"error": str(e), "code": e.get_code(), "partial": collected}
    return {"Histories": collected[:max_alarms], "truncated": len(collected) >= max_alarms}
```

## SDK Example: TKE Cluster Inventory

```python
def describe_cluster_context(cluster_id: str) -> dict:
    result = {"cluster_id": cluster_id, "sources": {}}
    for key, call in [
        ("cluster", lambda: tke_cli.DescribeClusters(
            tke_models.DescribeClustersRequest(ClusterIds=[cluster_id]))),
        ("nodes", lambda: tke_cli.DescribeClusterInstances(
            tke_models.DescribeClusterInstancesRequest(ClusterId=cluster_id))),
        ("node_pools", lambda: tke_cli.DescribeClusterNodePools(
            tke_models.DescribeClusterNodePoolsRequest(ClusterId=cluster_id))),
    ]:
        try:
            result["sources"][key] = call().to_json_string()
        except TencentCloudSDKException as e:
            result["sources"][key] = {"error": str(e), "code": e.get_code()}
    return result
```

## SDK Example: CLS Log Search

```python
def search_cls_events(topic_id: str, query: str, start_time: int, end_time: int) -> dict:
    req = cls_models.SearchLogRequest()
    req.TopicId = topic_id
    req.Query = query
    req.StartTime = start_time
    req.EndTime = end_time
    req.Limit = 100
    try:
        return cls_cli.SearchLog(req).to_json_string()
    except TencentCloudSDKException as e:
        return {"error": str(e), "code": e.get_code(), "data_quality": {"degraded": True}}
```

## SDK Example: Multi-Window Baseline (GetMonitorData)

Mirror CLI triple-window pattern from [`cli-usage.md#dynamic-baseline-metric-windows`](cli-usage.md#dynamic-baseline-metric-windows):

```python
def get_metric_windows(namespace: str, metric: str, instance_dims: list, windows: list[tuple[str, str]]) -> dict:
    out = {}
    for label, (start, end) in windows:
        req = monitor_models.GetMonitorDataRequest()
        req.Namespace = namespace
        req.MetricName = metric
        req.Instances = [{"Dimensions": instance_dims}]
        req.StartTime = start
        req.EndTime = end
        req.Period = 300
        try:
            out[label] = monitor_cli.GetMonitorData(req).to_json_string()
        except TencentCloudSDKException as e:
            out[label] = {"error": str(e), "code": e.get_code()}
    return out
```

## Safety Constraints

- Never call mutation APIs; recommendations use `RECOMMENDATION (not execution)` + `delegate_to`.
- Mask credentials in logs/errors per skill rubric.
- On SDK error: follow [`troubleshooting.md`](troubleshooting.md) HALT/retry/degrade table.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-06-13 | Phase F: SCF + CDN clients (Rules O/P) |
