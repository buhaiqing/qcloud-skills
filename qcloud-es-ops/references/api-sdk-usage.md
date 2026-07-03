# ES API & SDK Usage

Operation map, method signatures, required parameters, and request/response examples for `tencentcloud-sdk-python-es`.

---

## 1. SDK Installation

```bash
pip install tencentcloud-sdk-python-es
```

---

## 2. Client Setup

```python
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.es.v20180416 import es_client, models

# Credential from environment
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

# Client with region
client = es_client.EsClient(cred, "ap-guangzhou")
```

---

## 3. Operation Map

### Instance Lifecycle Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| CreateInstance | `CreateInstance` | `Zone`, `NodeType`, `NodeNum`, `DiskSize`, `DiskType`, `EsVersion`, `VpcId`, `SubnetId`, `Password` | `InstanceId`, `DealName` |
| DescribeInstances | `DescribeInstances` | — | `InstanceList`, `TotalCount` |
| UpdateInstance | `UpdateInstance` | `InstanceId` | `RequestId` |
| DeleteInstance | `DeleteInstance` | `InstanceId` | `RequestId` |
| UpgradeInstance | `UpgradeInstance` | `InstanceId`, `EsVersion` | `RequestId` |
| UpgradeLicense | `UpgradeLicense` | `InstanceId`, `NodeType`, `NodeNum`, `DiskSize` | `RequestId` |
| RestartInstance | `RestartInstance` | `InstanceId` | `RequestId` |
| RestartNodes | `RestartNodes` | `InstanceId`, `NodeNames` | `RequestId` |
| RestartKibana | `RestartKibana` | `InstanceId` | `RequestId` |

### Index Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| CreateIndex | `CreateIndex` | `InstanceId`, `IndexName`, `IndexMetaJson` | `IndexName` |
| DescribeIndexList | `DescribeIndexList` | `InstanceId` | `IndexMetaFields`, `TotalCount` |
| DescribeIndexMeta | `DescribeIndexMeta` | `InstanceId`, `IndexName` | `IndexMetaField` |
| UpdateIndex | `UpdateIndex` | `InstanceId`, `IndexName` | `RequestId` |
| DeleteIndex | `DeleteIndex` | `InstanceId`, `IndexName` | `RequestId` |

### Snapshot Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| CreateClusterSnapshot | `CreateClusterSnapshot` | `InstanceId`, `SnapshotName` | `SnapshotId` |
| DescribeClusterSnapshot | `DescribeClusterSnapshot` | `InstanceId` | `ClusterSnapshotSet` |
| DeleteClusterSnapshot | `DeleteClusterSnapshot` | `InstanceId`, `SnapshotId` | `RequestId` |
| RestoreClusterSnapshot | `RestoreClusterSnapshot` | `InstanceId`, `SnapshotId` | `RequestId` |

### Plugin and Dictionary Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| UpdatePlugins | `UpdatePlugins` | `InstanceId`, `InstallPluginList`, `RemovePluginList` | `RequestId` |
| UpdateDictionaries | `UpdateDictionaries` | `InstanceId`, `IkMainDicts`, `IkStopwords`, `JiebaDicts` | `RequestId` |

### Diagnostics and Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| DiagnoseInstance | `DiagnoseInstance` | `InstanceId` | `RequestId` |
| DescribeDiagnose | `DescribeDiagnose` | `InstanceId` | `DiagnoseResult` |
| DescribeInstanceLogs | `DescribeInstanceLogs` | `InstanceId` | `InstanceLogList` |
| DescribeInstanceOperations | `DescribeInstanceOperations` | `InstanceId` | `Operations` |

---

## 4. CreateInstance (Create ES Cluster)

### Request Example

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.es.v20180416 import es_client, models

def create_es_cluster():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))

        req = models.CreateInstanceRequest()
        req.Zone = "ap-guangzhou-3"
        req.NodeType = "ES.S1.MEDIUM4"
        req.NodeNum = 3
        req.DiskSize = 200
        req.DiskType = "CLOUD_SSD"
        req.EsVersion = "7.14.2"
        req.VpcId = "vpc-xxxxxx"
        req.SubnetId = "subnet-xxxxxx"
        req.Password = os.environ.get("ES_PASSWORD", "YourPassword123")
        req.InstanceName = "my-es-cluster"

        # Optional: dedicated master nodes
        req.EnableDedicatedMaster = True
        req.MasterNodeNum = 3
        req.MasterNodeType = "ES.S1.MEDIUM4"
        req.MasterNodeDiskSize = 50

        # Optional: basic security
        req.BasicSecurityType = 1  # 1=enabled, 0=disabled

        resp = client.CreateInstance(req)
        print(json.dumps(resp.to_json_string(), indent=2))
        # Response: instance_id and deal_name
        
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

create_es_cluster()
```

### Response Example

```json
{
  "Response": {
    "InstanceId": "es-xxxxxx",
    "DealName": "20260521xxxxxx",
    "RequestId": "abc-123-def-456"
  }
}
```

---

## 5. DescribeInstances (List ES Clusters)

```python
def list_es_clusters():
    try:
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
        req = models.DescribeInstancesRequest()
        req.Offset = 0
        req.Limit = 20
        # Optional filters:
        # req.InstanceIds = ["es-xxxxxx"]
        # req.Status = ["1"]  # 1=normal

        resp = client.DescribeInstances(req)
        print(json.dumps(resp.to_json_string(), indent=2))
        
        # Access fields
        for instance in resp.InstanceList:
            print(f"ID: {instance.InstanceId}, Name: {instance.InstanceName}, "
                  f"Status: {instance.Status}, Version: {instance.EsVersion}")
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

### Response Example

```json
{
  "Response": {
    "TotalCount": 5,
    "InstanceList": [
      {
        "InstanceId": "es-xxxxxx",
        "InstanceName": "production-cluster",
        "NodeType": "ES.S1.LARGE8",
        "NodeNum": 5,
        "DiskSize": 500,
        "DiskType": "CLOUD_SSD",
        "EsVersion": "7.14.2",
        "Status": 1,
        "HealthStatus": 0,
        "EsDomain": "es-xxxxxx.ap-guangzhou.es.tencentcloud.com",
        "KibanaUrl": "https://es-xxxxxx.ap-guangzhou.es.tencentcloud.com:5601",
        "Zone": "ap-guangzhou-3",
        "CreateTime": "2026-05-21T10:00:00+08:00",
        "VpcId": "vpc-xxxxxx",
        "SubnetId": "subnet-xxxxxx"
      }
    ],
    "RequestId": "abc-123-def-456"
  }
}
```

---

## 6. UpdateInstance (Scale Cluster)

```python
def scale_es_cluster(instance_id, new_node_type, new_node_num, new_disk_size):
    try:
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.UpdateInstanceRequest()
        req.InstanceId = instance_id
        req.NodeType = new_node_type
        req.NodeNum = new_node_num
        req.DiskSize = new_disk_size
        # Optional: cos backup before scaling
        # req.CosBackup = True

        resp = client.UpdateInstance(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 7. Index Operations

### CreateIndex

```python
def create_index(instance_id, index_name):
    try:
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.CreateIndexRequest()
        req.InstanceId = instance_id
        req.IndexName = index_name
        req.IndexType = "normal"  # "normal" or "auto"
        
        # Optional: index mapping in JSON
        req.IndexMetaJson = json.dumps({
            "settings": {
                "number_of_shards": 5,
                "number_of_replicas": 1
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "price": {"type": "float"}
                }
            }
        })

        resp = client.CreateIndex(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

### DescribeIndexList

```python
def list_indices(instance_id):
    try:
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.DescribeIndexListRequest()
        req.InstanceId = instance_id
        req.Offset = 0
        req.Limit = 20

        resp = client.DescribeIndexList(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 8. Snapshot Operations

### CreateClusterSnapshot

```python
from datetime import datetime

def create_snapshot(instance_id):
    try:
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.CreateClusterSnapshotRequest()
        req.InstanceId = instance_id
        req.SnapshotName = f"auto-snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        resp = client.CreateClusterSnapshot(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

### RestoreClusterSnapshot

```python
def restore_snapshot(instance_id, snapshot_id):
    try:
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.RestoreClusterSnapshotRequest()
        req.InstanceId = instance_id
        req.SnapshotId = snapshot_id

        resp = client.RestoreClusterSnapshot(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 9. Plugin Management

```python
def update_plugins(instance_id, install_list=None, remove_list=None):
    try:
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.UpdatePluginsRequest()
        req.InstanceId = instance_id
        if install_list:
            req.InstallPluginList = install_list  # ["analysis-ik", "analysis-pinyin"]
        if remove_list:
            req.RemovePluginList = remove_list

        resp = client.UpdatePlugins(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 10. Diagnostics

```python
def diagnose_instance(instance_id):
    try:
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        
        # Run diagnostics
        diag_req = models.DiagnoseInstanceRequest()
        diag_req.InstanceId = instance_id
        diag_resp = client.DiagnoseInstance(diag_req)
        print("Diagnosis triggered:", json.dumps(diag_resp.to_json_string(), indent=2))
        
        # Check diagnosis results
        desc_req = models.DescribeDiagnoseRequest()
        desc_req.InstanceId = instance_id
        desc_resp = client.DescribeDiagnose(desc_req)
        print("Diagnosis results:", json.dumps(desc_resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 11. Pagination Pattern

All list APIs follow the same pagination pattern:

```python
def paginate_all(instance_id):
    # Fetch all items with pagination.
    all_items = []
    offset = 0
    limit = 100
    
    while True:
        req = models.DescribeInstancesRequest()
        req.Offset = offset
        req.Limit = limit
        
        resp = client.DescribeInstances(req)
        items = resp.InstanceList
        if not items:
            break
        all_items.extend(items)
        
        if len(items) < limit:
            break
        offset += limit
    
    return all_items
```

---

## 12. Error Handling Pattern

```python
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

def safe_api_call(func, *args, max_retries=3, **kwargs):
    # Retry wrapper for ES API calls.
    last_error = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except TencentCloudSDKException as err:
            last_error = err
            code = err.code
            if code in ["RequestLimitExceeded", "InternalError", "FailedOperation.ClusterStateError"]:
                import time
                wait = 2 ** attempt
                print(f"[RETRY] {code}: retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            else:
                raise
    raise last_error
```
