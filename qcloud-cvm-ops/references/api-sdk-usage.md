# CVM API & SDK Usage

Operation map, required fields, pagination, and request/response examples for `tencentcloud-sdk-python-cvm`.

---

## 1. SDK Installation

```bash
pip install tencentcloud-sdk-python-cvm
```

---

## 2. Client Setup

```python
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm import cvm_client, models

# Credential from environment
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

# Client with region
client = cvm_client.CvmClient(cred, "ap-guangzhou")
```

---

## 3. Operation Map

### Instance Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| RunInstances | `RunInstances` | `Placement`, `InstanceType`, `ImageId` | `InstanceIdSet` |
| DescribeInstances | `DescribeInstances` | — | `InstanceSet`, `TotalCount` |
| StartInstances | `StartInstances` | `InstanceIds` | `RequestId` |
| StopInstances | `StopInstances` | `InstanceIds` | `RequestId` |
| RebootInstances | `RebootInstances` | `InstanceIds` | `RequestId` |
| TerminateInstances | `TerminateInstances` | `InstanceIds` | `RequestId` |
| ModifyInstanceAttribute | `ModifyInstanceAttribute` | `InstanceId` | `RequestId` |
| ResizeInstanceDisks | `ResizeInstanceDisks` | `InstanceId`, `DataDisks` | `RequestId` |

### Image Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| CreateImage | `CreateImage` | `InstanceId`, `ImageName` | `ImageId` |
| DescribeImages | `DescribeImages` | — | `ImageSet`, `TotalCount` |
| DeleteImage | `DeleteImage` | `ImageId` | `RequestId` |
| ShareImage | `ShareImage` | `ImageId`, `AccountIds` | `RequestId` |
| SyncImages | `SyncImages` | `ImageIds`, `DestinationRegions` | `RequestId` |

### Host Operations (CDH)

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| AllocateHosts | `AllocateHosts` | `Zone`, `HostType`, `ChargeType` | `HostIdSet` |
| DescribeHosts | `DescribeHosts` | — | `HostSet` |
| ModifyHostsAttribute | `ModifyHostsAttribute` | `HostIds` | `RequestId` |

---

## 4. RunInstances (Create Instance)

### Required Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `Placement` | Object | Yes | Zone and project info |
| `InstanceType` | String | Yes | e.g., `S5.SMALL1` |
| `ImageId` | String | Yes | e.g., `img-xxx` |
| `InstanceChargeType` | String | No | `POSTPAID_BY_HOUR` (default) |

### Optional Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `InstanceName` | String | Display name |
| `SystemDisk` | Object | System disk config |
| `DataDisks` | Array | Data disk configs |
| `InternetAccessible` | Object | Public IP config |
| `VpcId` | String | VPC ID |
| `SubnetId` | String | Subnet ID |
| `SecurityGroupIds` | Array | Security group IDs |
| `LoginSettings` | Object | SSH key or password |
| `ClientToken` | String | Idempotency token |
| `TagSpecification` | Array | Tags |

### Example

```python
req = models.RunInstancesRequest()
req.Placement = models.Placement()
req.Placement.Zone = "ap-guangzhou-3"
req.InstanceType = "S5.LARGE4"
req.ImageId = "img-xxx"
req.InstanceName = "web-server"
req.InstanceChargeType = "POSTPAID_BY_HOUR"

req.SystemDisk = models.SystemDisk()
req.SystemDisk.DiskType = "CLOUD_PREMIUM"
req.SystemDisk.DiskSize = 50

req.InternetAccessible = models.InternetAccessible()
req.InternetAccessible.InternetChargeType = "TRAFFIC_POSTPAID_BY_HOUR"
req.InternetAccessible.PublicIpAssigned = True

req.VpcId = "vpc-xxx"
req.SubnetId = "subnet-xxx"
req.SecurityGroupIds = ["sg-xxx"]

req.ClientToken = str(int(time.time() * 1000000))

resp = client.RunInstances(req)
instance_id = resp.InstanceIdSet[0]
print(f"Created instance: {instance_id}")
```

### Response Schema

```json
{
  "InstanceIdSet": ["ins-xxx", "ins-yyyy"],
  "RequestId": "abc123"
}
```

---

## 5. DescribeInstances

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `InstanceIds` | Array | No | Filter by IDs |
| `Filters` | Array | No | Filter by attributes |
| `Offset` | Integer | No | Pagination offset (default 0) |
| `Limit` | Integer | No | Pagination limit (default 20, max 100) |

### Filter Types

| Filter Name | Values | Description |
|-------------|--------|-------------|
| `instance-name` | String (wildcard) | Instance name pattern |
| `instance-status` | RUNNING, STOPPED | Instance state |
| `instance-type` | String | Instance type |
| `zone` | String | Availability zone |
| `image-id` | String | Image ID |
| `vpc-id` | String | VPC ID |
| `tag-key` | String | Tag key |
| `tag-value` | String | Tag value |

### Example

```python
req = models.DescribeInstancesRequest()
req.Limit = 100
req.Offset = 0

# Filter by status
req.Filters = []
filter1 = models.Filter()
filter1.Name = "instance-status"
filter1.Values = ["RUNNING"]
req.Filters.append(filter1)

resp = client.DescribeInstances(req)
for instance in resp.InstanceSet:
    print(f"ID: {instance.InstanceId}, Name: {instance.InstanceName}, Status: {instance.Status}")
```

### Response Schema

```json
{
  "TotalCount": 10,
  "InstanceSet": [
    {
      "InstanceId": "ins-xxx",
      "InstanceName": "web-server",
      "Status": "RUNNING",
      "CPU": 4,
      "Memory": 8,
      "InstanceType": "S5.LARGE4",
      "Zone": "ap-guangzhou-3",
      "PrivateIpAddresses": ["10.0.0.1"],
      "PublicIpAddresses": ["123.123.123.123"],
      "CreatedTime": "2026-05-21T10:00:00+08:00",
      "ExpiredTime": "",
      "ImageId": "img-xxx",
      "SystemDisk": {
        "DiskType": "CLOUD_PREMIUM",
        "DiskId": "disk-xxx",
        "DiskSize": 50
      },
      "DataDisks": [],
      "VirtualPrivateCloud": {
        "VpcId": "vpc-xxx",
        "SubnetId": "subnet-xxx"
      },
      "SecurityGroupIds": ["sg-xxx"],
      "Tags": [],
      "InstanceStateNote": "",
      "LatestOperation": "",
      "LatestOperationState": "",
      "LatestOperationRequestId": ""
    }
  ],
  "RequestId": "abc123"
}
```

---

## 6. Pagination

### Pattern

```python
offset = 0
limit = 100
all_instances = []

while True:
    req = models.DescribeInstancesRequest()
    req.Offset = offset
    req.Limit = limit
    
    resp = client.DescribeInstances(req)
    all_instances.extend(resp.InstanceSet)
    
    if len(resp.InstanceSet) < limit:
        break
    offset += limit

print(f"Total instances: {len(all_instances)}")
```

---

## 7. StartInstances / StopInstances / RebootInstances

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `InstanceIds` | Array | Yes | List of instance IDs |

### StopInstances Additional Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `StopType` | String | No | `SOFT` (default) or `HARD` |

### RebootInstances Additional Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `RebootType` | String | No | `SOFT` (default) or `HARD` |

### Example

```python
# Stop instance
req = models.StopInstancesRequest()
req.InstanceIds = ["ins-xxx"]
req.StopType = "SOFT"

resp = client.StopInstances(req)
print(f"Stop request: {resp.RequestId}")

# Poll status
import time
for i in range(24):
    describe_req = models.DescribeInstancesRequest()
    describe_req.InstanceIds = ["ins-xxx"]
    describe_resp = client.DescribeInstances(describe_req)
    status = describe_resp.InstanceSet[0].Status
    if status == "STOPPED":
        print("Instance stopped")
        break
    time.sleep(5)
```

---

## 8. TerminateInstances (Delete)

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `InstanceIds` | Array | Yes | List of instance IDs |

### Example

```python
req = models.TerminateInstancesRequest()
req.InstanceIds = ["ins-xxx"]

resp = client.TerminateInstances(req)
print(f"Terminate request: {resp.RequestId}")
```

---

## 9. ModifyInstanceAttribute

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `InstanceId` | String | Yes | Instance ID |
| `InstanceName` | String | No | New name |
| `SecurityGroupIds` | Array | No | New security groups |
| `ProjectId` | Integer | No | Project ID |

### Example

```python
req = models.ModifyInstanceAttributeRequest()
req.InstanceId = "ins-xxx"
req.InstanceName = "new-name"

resp = client.ModifyInstanceAttribute(req)
print(f"Modified: {resp.RequestId}")
```

---

## 10. ResizeInstanceDisks

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `InstanceId` | String | Yes | Instance ID |
| `DataDisks` | Array | Yes | Disk resize configs |

### Example

```python
req = models.ResizeInstanceDisksRequest()
req.InstanceId = "ins-xxx"

disk = models.DataDisk()
disk.DiskId = "disk-xxx"
disk.DiskSize = 200  # New size in GB
req.DataDisks = [disk]

resp = client.ResizeInstanceDisks(req)
print(f"Resize request: {resp.RequestId}")
```

---

## 11. CreateImage

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `InstanceId` | String | Yes | Source instance ID |
| `ImageName` | String | Yes | Image name |
| `ImageDescription` | String | No | Description |
| `Sysprep` | String | No | Windows sysprep |
| `ForcePoweroff` | String | No | Force instance stop |

### Example

```python
req = models.CreateImageRequest()
req.InstanceId = "ins-xxx"
req.ImageName = "backup-image"
req.ImageDescription = "Backup for web server"
req.ForcePoweroff = "TRUE"

resp = client.CreateImage(req)
print(f"Created image: {resp.ImageId}")
```

---

## 12. DescribeImages

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ImageIds` | Array | No | Image IDs |
| `Filters` | Array | No | Filters |
| `Offset` | Integer | No | Pagination |
| `Limit` | Integer | No | Pagination limit |

### Filter Types

| Filter Name | Values | Description |
|-------------|--------|-------------|
| `image-type` | PRIVATE_IMAGE, PUBLIC_IMAGE | Image category |
| `image-id` | String | Image ID |
| `image-name` | String (wildcard) | Image name |
| `platform` | String | OS platform |
| `image-state` | NORMAL | Image state |

### Example

```python
req = models.DescribeImagesRequest()
req.Filters = []

filter1 = models.Filter()
filter1.Name = "image-type"
filter1.Values = ["PUBLIC_IMAGE"]
req.Filters.append(filter1)

filter2 = models.Filter()
filter2.Name = "platform"
filter2.Values = ["CentOS"]
req.Filters.append(filter2)

resp = client.DescribeImages(req)
for image in resp.ImageSet:
    print(f"Image: {image.ImageId}, Name: {image.ImageName}, Platform: {image.Platform}")
```

---

## 13. Error Handling

### Pattern

```python
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

try:
    req = models.RunInstancesRequest()
    resp = client.RunInstances(req)
    print(resp.InstanceIdSet)
    
except TencentCloudSDKException as err:
    print(f"[ERROR] Code: {err.code}")
    print(f"[ERROR] Message: {err.message}")
    print(f"[ERROR] RequestId: {err.requestId}")
    
    if err.code == "InvalidParameter":
        print("Fix: Check parameter format")
    elif err.code == "ResourceInsufficient":
        print("Fix: Request quota increase")
    elif err.code == "InternalError":
        print("Fix: Retry operation")
```

---

## 14. Async Operation Pattern

### Polling Pattern

```python
import time

def wait_for_instance(client, instance_id, target_state, timeout=300):
    """Wait for instance to reach target state"""
    start = time.time()
    
    while time.time() - start < timeout:
        req = models.DescribeInstancesRequest()
        req.InstanceIds = [instance_id]
        
        resp = client.DescribeInstances(req)
        if resp.TotalCount == 0:
            return "TERMINATED"  # Instance deleted
        
        state = resp.InstanceSet[0].Status
        if state == target_state:
            return state
        
        time.sleep(5)
    
    raise TimeoutError(f"Timeout waiting for instance {instance_id} to reach {target_state}")

# Usage
instance_id = resp.InstanceIdSet[0]
final_state = wait_for_instance(client, instance_id, "RUNNING")
print(f"Instance ready: {final_state}")
```

---

## 15. Batch Operations

```python
def batch_describe(client, instance_ids, batch_size=20):
    """Batch describe with chunking"""
    results = []
    
    for i in range(0, len(instance_ids), batch_size):
        chunk = instance_ids[i:i+batch_size]
        req = models.DescribeInstancesRequest()
        req.InstanceIds = chunk
        resp = client.DescribeInstances(req)
        results.extend(resp.InstanceSet)
    
    return results

# Usage
all_ids = ["ins-xxx", "ins-yyyy", ...]
instances = batch_describe(client, all_ids)
```

---

## References

- [SDK GitHub](https://github.com/TencentCloud/tencentcloud-sdk-python)
- [CVM API Docs](https://cloud.tencent.com/document/api/213)