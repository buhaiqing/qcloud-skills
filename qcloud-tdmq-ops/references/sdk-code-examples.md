# TDMQ SDK Code Examples

## Create RocketMQ Cluster

```python
import os
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tdmq import tdmq_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = tdmq_client.TdmqClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateRocketMQClusterRequest()
req.ClusterName = os.environ.get("CLUSTER_NAME", "my-cluster")
req.Remark = "created via sdk"
resp = client.CreateRocketMQCluster(req)
print(resp.ClusterId)
```

## Send RocketMQ Message

```python
req = models.SendRocketMQMessageRequest()
req.ClusterId = "rocketmq-xxx"
req.Namespace = "ns-prod"
req.Topic = "orders"
req.Body = "order-payload"
resp = client.SendRocketMQMessage(req)
print(resp.MsgId, resp.ReturnCode)
```

## Create Topic (SDK)

```python
req = models.CreateRocketMQTopicRequest()
req.ClusterId = "rocketmq-xxx"
req.Namespace = "ns-prod"
req.Topic = "orders"
resp = client.CreateRocketMQTopic(req)
print(resp.TopicId)
```

> All credentials read from environment — never hardcode or print `SecretKey`.
