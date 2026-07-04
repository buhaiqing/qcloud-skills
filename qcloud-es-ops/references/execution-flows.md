# ES Execution Flows (How-To Reference)

> **Purpose:** This file contains the detailed CLI/SDK command blocks for ES operations.
> SKILL.md describes **what to do**; this file describes **how to do it**.

## Index

| Section | Operation | CLI Command | SDK Command |
|---------|-----------|-------------|-------------|
| §1 | CreateInstance | `tccli es CreateInstance` | `client.CreateInstance()` |
| §2 | DescribeInstances | `tccli es DescribeInstances` | `client.DescribeInstances()` |
| §3 | DeleteInstance | `tccli es DeleteInstance` | `client.DeleteInstance()` |
| §4 | UpdateInstance | `tccli es UpdateInstance` | `client.UpdateInstance()` |
| §5 | RestartInstance | `tccli es RestartInstance` | `client.RestartInstance()` |
| §6 | RestartNodes | `tccli es RestartNodes` | `client.RestartNodes()` |
| §7 | CreateClusterSnapshot | `tccli es CreateClusterSnapshot` | `client.CreateClusterSnapshot()` |
| §8 | RestoreClusterSnapshot | `tccli es RestoreClusterSnapshot` | `client.RestoreClusterSnapshot()` |
| §9 | DiagnoseInstance | `tccli es DiagnoseInstance` | `client.DiagnoseInstance()` |

---

## §1 CreateInstance

### CLI

```bash
# Basic create (required params)
tccli es CreateInstance \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Zone "{{user.zone}}" \
  --NodeType "ES.S1.MEDIUM4" \
  --NodeNum 3 \
  --DiskSize 200 \
  --DiskType "CLOUD_SSD" \
  --EsVersion "7.14.2" \
  --VpcId "{{user.vpc_id}}" \
  --SubnetId "{{user.subnet_id}}" \
  --Password "{{user.password}}" \
  --InstanceName "{{user.cluster_name}}"

# With dedicated master node and Kibana
tccli es CreateInstance \
  --Region "ap-guangzhou" \
  --Zone "ap-guangzhou-3" \
  --NodeType "ES.S1.MEDIUM4" \
  --NodeNum 3 \
  --DiskSize 200 \
  --DiskType "CLOUD_SSD" \
  --EsVersion "7.14.2" \
  --VpcId "vpc-xxxx" \
  --SubnetId "subnet-xxxx" \
  --Password "{{user.password}}" \
  --InstanceName "my-es-cluster" \
  --EnableDedicatedMaster true \
  --MasterNodeNum 3 \
  --MasterNodeType "ES.S1.MEDIUM4" \
  --MasterNodeDiskSize 50
```

### SDK

```python
#!/usr/bin/env python3
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.es.v20180416 import es_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateInstanceRequest()
        req.Zone = "{{user.zone}}"
        req.NodeType = "ES.S1.MEDIUM4"
        req.NodeNum = 3
        req.DiskSize = 200
        req.DiskType = "CLOUD_SSD"
        req.EsVersion = "7.14.2"
        req.VpcId = "{{user.vpc_id}}"
        req.SubnetId = "{{user.subnet_id}}"
        req.Password = "{{user.password}}"
        req.InstanceName = "{{user.cluster_name}}"

        resp = client.CreateInstance(req)
        print(resp.to_json_string())

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

### Post-execution Polling

#### CLI

```bash
# CLI polling
for i in $(seq 1 60); do
  STATUS=$(tccli es DescribeInstances --InstanceIds '["{{output.instance_id}}"]' --Region {{env.TENCENTCLOUD_REGION}} | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Response']['InstanceList'][0]['HealthStatus'])")
  [ "$STATUS" = "0" ] || [ "$STATUS" = "1" ] && break
  sleep 10
done
```

#### SDK

```python
# SDK polling
import time
for i in range(60):
    desc_req = models.DescribeInstancesRequest()
    desc_req.InstanceIds = ["{{output.instance_id}}"]
    resp = client.DescribeInstances(desc_req)
    if resp.InstanceList[0].HealthStatus in [0, 1]:
        break
    time.sleep(10)
```

---

## §2 DescribeInstances

### CLI

```bash
# List all clusters (paginated)
tccli es DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Offset 0 --Limit 20

# Filter by specific instance IDs
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' --Region {{env.TENCENTCLOUD_REGION}}

# Filter by health status (0=green, 1=yellow, 2=red)
tccli es DescribeInstances --HealthStatus "[0]" --Region {{env.TENCENTCLOUD_REGION}}
```

### SDK

```python
req = models.DescribeInstancesRequest()
req.Offset = 0
req.Limit = 20
resp = client.DescribeInstances(req)
print(resp.to_json_string())
```

---

## §3 DeleteInstance

### CLI

```bash
tccli es DeleteInstance --InstanceId "{{user.instance_id}}" --Region {{env.TENCENTCLOUD_REGION}}
```

### SDK

```python
req = models.DeleteInstanceRequest()
req.InstanceId = "{{user.instance_id}}"
resp = client.DeleteInstance(req)
print(resp.to_json_string())
```

### Post-execution Validation

```bash
# Verify deletion
tccli es DescribeInstances --InstanceIds '["{{user.instance_id}}"]' --Region {{env.TENCENTCLOUD_REGION}}
# Expected: ResourceNotFound or empty result
```

---

## §4 UpdateInstance

### CLI

```bash
# Scale node type and count
tccli es UpdateInstance \
  --InstanceId "{{user.instance_id}}" \
  --NodeType "ES.S1.LARGE8" \
  --NodeNum 5 \
  --DiskSize 500 \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### SDK

```python
req = models.UpdateInstanceRequest()
req.InstanceId = "{{user.instance_id}}"
req.NodeType = "ES.S1.LARGE8"
req.NodeNum = 5
req.DiskSize = 500
resp = client.UpdateInstance(req)
print(resp.to_json_string())
```

---

## §5 RestartInstance

### CLI

```bash
tccli es RestartInstance --InstanceId "{{user.instance_id}}" --Region {{env.TENCENTCLOUD_REGION}}
```

### SDK

```python
req = models.RestartInstanceRequest()
req.InstanceId = "{{user.instance_id}}"
resp = client.RestartInstance(req)
print(resp.to_json_string())
```

---

## §6 RestartNodes

### CLI

```bash
# Restart specific nodes
tccli es RestartNodes --InstanceId "{{user.instance_id}}" --NodeNames '["node1","node2"]' --Region {{env.TENCENTCLOUD_REGION}}
```

### SDK

```python
req = models.RestartNodesRequest()
req.InstanceId = "{{user.instance_id}}"
req.NodeNames = ["node1", "node2"]
resp = client.RestartNodes(req)
print(resp.to_json_string())
```

---

## §7 CreateClusterSnapshot

### CLI

```bash
tccli es CreateClusterSnapshot \
  --InstanceId "{{user.instance_id}}" \
  --SnapshotName "auto-snapshot-$(date +%Y%m%d-%H%M%S)" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### SDK

```python
req = models.CreateClusterSnapshotRequest()
req.InstanceId = "{{user.instance_id}}"
req.SnapshotName = "auto-snapshot-$(date +%Y%m%d-%H%M%S)"
resp = client.CreateClusterSnapshot(req)
print(resp.to_json_string())
```

---

## §8 RestoreClusterSnapshot

### CLI

```bash
tccli es RestoreClusterSnapshot \
  --InstanceId "{{user.instance_id}}" \
  --SnapshotId "{{user.snapshot_id}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### SDK

```python
req = models.RestoreClusterSnapshotRequest()
req.InstanceId = "{{user.instance_id}}"
req.SnapshotId = "{{user.snapshot_id}}"
resp = client.RestoreClusterSnapshot(req)
print(resp.to_json_string())
```

---

## §9 DiagnoseInstance

### CLI

```bash
# Run diagnostics
tccli es DiagnoseInstance --InstanceId "{{user.instance_id}}" --Region {{env.TENCENTCLOUD_REGION}}

# Get diagnosis settings
tccli es DescribeDiagnose --InstanceId "{{user.instance_id}}" --Region {{env.TENCENTCLOUD_REGION}}
```

### SDK

```python
# Run diagnostics
req = models.DiagnoseInstanceRequest()
req.InstanceId = "{{user.instance_id}}"
resp = client.DiagnoseInstance(req)
print(resp.to_json_string())

# Get diagnosis settings
req = models.DescribeDiagnoseRequest()
req.InstanceId = "{{user.instance_id}}"
resp = client.DescribeDiagnose(req)
print(resp.to_json_string())
```

---

## Key Response Fields

| Field | JSON Path | Notes |
|-------|-----------|-------|
| InstanceId | `$.Response.InstanceList[].InstanceId` | Cluster unique ID |
| InstanceName | `$.Response.InstanceList[].InstanceName` | Cluster name |
| HealthStatus | `$.Response.InstanceList[].HealthStatus` | 0=green, 1=yellow, 2=red, -1=unknown |
| EsVersion | `$.Response.InstanceList[].EsVersion` | Elasticsearch version |
| NodeType | `$.Response.InstanceList[].NodeType` | Node specification |
| NodeNum | `$.Response.InstanceList[].NodeNum` | Number of nodes |
| DiskSize | `$.Response.InstanceList[].DiskSize` | Disk size in GB |
| EsDomain | `$.Response.InstanceList[].EsDomain` | ES cluster access domain |
| KibanaUrl | `$.Response.InstanceList[].KibanaUrl` | Kibana dashboard URL |
| Status | `$.Response.InstanceList[].Status` | 0=processing, 1=normal, -1=stopped |
| CreateTime | `$.Response.InstanceList[].CreateTime` | Creation time (ISO 8601) |
