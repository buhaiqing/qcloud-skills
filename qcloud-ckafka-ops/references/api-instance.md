# CKafka Instance API

> CKafka instance operations.

## API Reference

| API | Description | CLI Example |
|-----|-------------|-------------|
| DescribeInstances | Query instance list | `tccli ckafka DescribeInstances` |
| CreateInstance | Create CKafka instance | `tccli ckafka CreateInstance` |
| DeleteInstance | Delete CKafka instance | `tccli ckafka DeleteInstance` |
| ModifyInstanceAttributes | Modify instance attributes | `tccli ckafka ModifyInstanceAttributes` |

## Instance Lifecycle

1. **Create**: `tccli ckafka CreateInstance --InstanceName my-kafka --VpcId vpc-xxx --SubnetId subnet-xxx`
2. **Configure**: Add topic, ACL, user configurations
3. **Monitor**: Check health via `DescribeInstanceAttributes`
4. **Delete**: Ensure all topics and ACLs are removed first

## SDK Code Example

```python
from tencentcloud.ckafka.v20190819 import CkafkaClient
from tencentcloud.ckafka.v20190819.models import DescribeInstancesRequest

client = CkafkaClient(cred, region, profile)
req = DescribeInstancesRequest()
resp = client.DescribeInstances(req)
for inst in resp.InstanceList:
    print(f"{inst.InstanceId}: {inst.InstanceName}")
```

## See also
- [Core Concepts](core-concepts.md)
- [CLI Usage](cli-usage.md)
