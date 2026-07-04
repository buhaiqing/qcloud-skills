# Redis SDK Code Examples

## Create Instance

```python
#!/usr/bin/env python3
"""SDK fallback: Redis CreateInstance"""
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.redis import redis_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = redis_client.RedisClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.CreateInstanceRequest()
        req.Memory = int(os.environ.get("REDIS_MEMORY_MB", "1024"))
        req.Period = 1
        req.GoodsNum = 1
        req.Zone = os.environ.get("REDIS_ZONE")
        req.ProjectId = 0
        req.Password = os.environ.get("REDIS_PASSWORD")
        req.VpcId = os.environ.get("VPC_ID")
        req.SubnetId = os.environ.get("SUBNET_ID")
        req.InstanceName = os.environ.get("INSTANCE_NAME")
        resp = client.CreateInstance(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

## Describe Instances

```python
# SDK
req = models.DescribeInstancesRequest()
req.InstanceId = os.environ.get("INSTANCE_ID")
resp = client.DescribeInstances(req)
print(json.dumps(resp.to_json_string(), indent=2))
```
