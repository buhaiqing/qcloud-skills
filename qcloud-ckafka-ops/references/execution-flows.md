# CKafka Execution Flows

This file contains detailed CLI/SDK command blocks for all CKafka operations.
SKILL.md describes **what to do**; this file provides **how to do** (CLI + SDK commands).

## Index

| § | Operation | CLI Command | SDK Command |
|---|-----------|-------------|-------------|
| 1 | CreateInstance | `tccli ckafka CreateInstance` | `client.CreateInstance()` |
| 2 | CreateTopic | `tccli ckafka CreateTopic` | `client.CreateTopic()` |
| 3 | DescribeConsumerGroup | `tccli ckafka DescribeConsumerGroup` | `client.DescribeConsumerGroup()` |
| 4 | CreateAcl | `tccli ckafka CreateAcl` | `client.CreateAcl()` |
| 5 | SendMessage | `tccli ckafka SendMessages` | `client.SendMessage()` |

---

## 1. CreateInstance

### CLI

```bash
# Basic create (required params)
tccli ckafka CreateInstance \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ZoneId "{{user.zone_id}}" \
  --InstanceName "{{user.instance_name}}" \
  --VpcId "{{user.vpc_id}}" \
  --SubnetId "{{user.subnet_id}}" \
  --SpecType "standard" \
  --DiskType "CLOUD_SSD" \
  --DiskSize 1000 \
  --MsgRetentionTime 1440

# Professional tier with multi-AZ
tccli ckafka CreateInstance \
  --Region "ap-guangzhou" \
  --ZoneId "ap-guangzhou-3" \
  --InstanceName "my-ckafka-cluster" \
  --VpcId "vpc-xxxxxx" \
  --SubnetId "subnet-xxxxxx" \
  --SpecType "professional" \
  --DiskType "CLOUD_SSD" \
  --DiskSize 3000 \
  --MsgRetentionTime 10080 \
  --InstanceVersion "2.4.1"
```

### SDK (Python)

```python
#!/usr/bin/env python3
import os
import json
import time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ckafka.v20190819 import ckafka_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = ckafka_client.CkafkaClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateInstanceRequest()
        req.ZoneId = "ap-guangzhou-3"
        req.InstanceName = "my-ckafka-cluster"
        req.VpcId = "vpc-xxxxxx"
        req.SubnetId = "subnet-xxxxxx"
        req.SpecType = "standard"
        req.DiskType = "CLOUD_SSD"
        req.DiskSize = 1000
        req.MsgRetentionTime = 1440
        req.InstanceVersion = "2.4.1"

        resp = client.CreateInstance(req)
        result = json.loads(resp.to_json_string())
        print(resp.to_json_string())

        instance_id = result["Response"]["InstanceId"]
        print(f"Instance created: {instance_id}")

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

---

## 2. CreateTopic

### CLI

```bash
# Create topic with basic config
tccli ckafka CreateTopic \
  --InstanceId "{{user.instance_id}}" \
  --TopicName "{{user.topic_name}}" \
  --PartitionNum {{user.partition_num}} \
  --ReplicaNum {{user.replica_num}}

# Create topic with advanced config
tccli ckafka CreateTopic \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "order-events" \
  --PartitionNum 6 \
  --ReplicaNum 3 \
  --EnableWhiteList 0 \
  --RetentionMs 604800000 \
  --Note "Order processing events topic"
```

### SDK (Python)

```python
#!/usr/bin/env python3
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ckafka.v20190819 import ckafka_client, models

def main():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = ckafka_client.CkafkaClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

    req = models.CreateTopicRequest()
    req.InstanceId = "{{user.instance_id}}"
    req.TopicName = "{{user.topic_name}}"
    req.PartitionNum = {{user.partition_num}}
    req.ReplicaNum = {{user.replica_num}}
    req.Note = "Created via API"
    resp = client.CreateTopic(req)
    print(resp.to_json_string())

if __name__ == "__main__":
    main()
```

---

## 3. DescribeConsumerGroup

### CLI

```bash
# List all consumer groups
tccli ckafka DescribeConsumerGroup \
  --InstanceId "{{user.instance_id}}" \
  --Offset 0 \
  --Limit 20

# List with filter
tccli ckafka DescribeConsumerGroup \
  --InstanceId "ckafka-xxxxxx" \
  --SearchWord "order-consumer"
```

### SDK (Python)

```python
#!/usr/bin/env python3
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ckafka.v20190819 import ckafka_client, models

def main():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = ckafka_client.CkafkaClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

    req = models.DescribeConsumerGroupRequest()
    req.InstanceId = "{{user.instance_id}}"
    req.Offset = 0
    req.Limit = 20
    resp = client.DescribeConsumerGroup(req)
    print(resp.to_json_string())

    result = json.loads(resp.to_json_string())
    # Parse consumer group info
    for group in result["Response"]["Result"]["ConsumerGroupList"]:
        print(f"Group: {group['ConsumerGroupName']}, Lag: {group.get('ConsumeLag', 'N/A')}")

if __name__ == "__main__":
    main()
```

---

## 4. CreateAcl

### CLI

```bash
# Create ACL for producer
tccli ckafka CreateAcl \
  --InstanceId "{{user.instance_id}}" \
  --ResourceType "TOPIC" \
  --ResourceName "{{user.topic_name}}" \
  --Principal "User:*" \
  --Host "*" \
  --Operation "Write" \
  --PermissionType "Allow"

# Create ACL for consumer (Read)
tccli ckafka CreateAcl \
  --InstanceId "ckafka-xxxxxx" \
  --ResourceType "TOPIC" \
  --ResourceName "order-events" \
  --Principal "User:consumer-app" \
  --Host "10.0.0.0/8" \
  --Operation "Read" \
  --PermissionType "Allow"

# Create consumer group ACL
tccli ckafka CreateAcl \
  --InstanceId "ckafka-xxxxxx" \
  --ResourceType "GROUP" \
  --ResourceName "order-consumer-group" \
  --Principal "User:consumer-app" \
  --Host "*" \
  --Operation "Read" \
  --PermissionType "Allow"
```

### SDK (Python)

```python
#!/usr/bin/env python3
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ckafka.v20190819 import ckafka_client, models

def main():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = ckafka_client.CkafkaClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

    req = models.CreateAclRequest()
    req.InstanceId = "{{user.instance_id}}"
    req.ResourceType = "TOPIC"
    req.ResourceName = "{{user.topic_name}}"
    req.Principal = "User:*"
    req.Host = "*"
    req.Operation = "Write"
    req.PermissionType = "Allow"
    resp = client.CreateAcl(req)
    print(resp.to_json_string())

if __name__ == "__main__":
    main()
```

---

## 5. SendMessage

### CLI

```bash
# Send a single message
tccli ckafka SendMessages \
  --InstanceId "{{user.instance_id}}" \
  --Topic "{{user.topic_name}}" \
  --Partition 0 \
  --Message 'Hello Kafka!'

# Send JSON message (escape properly)
tccli ckafka SendMessages \
  --InstanceId "ckafka-xxxxxx" \
  --Topic "order-events" \
  --Message '{"orderId":"12345","status":"created","timestamp":"2026-05-28T10:00:00Z"}'
```

### SDK (Python)

```python
#!/usr/bin/env python3
import os
import json
import base64
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ckafka.v20190819 import ckafka_client, models

def main():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = ckafka_client.CkafkaClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

    req = models.SendMessageRequest()
    req.InstanceId = "{{user.instance_id}}"
    req.Topic = "{{user.topic_name}}"
    req.Partition = 0

    # Encode message (if required by SDK version)
    message = '{"event":"test","data":"hello"}'
    req.Message = base64.b64encode(message.encode()).decode()

    resp = client.SendMessage(req)
    print(resp.to_json_string())
    result = json.loads(resp.to_json_string())
    print(f"Message sent, offset: {result['Response'].get('Offset', 'N/A')}")

if __name__ == "__main__":
    main()
```
