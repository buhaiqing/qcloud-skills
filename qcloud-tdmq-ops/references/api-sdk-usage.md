# TDMQ API & SDK Usage

## SDK Package

```bash
pip install tencentcloud-sdk-python-tdmq
```

## Client Init

```python
from tencentcloud.common import credential
from tencentcloud.tdmq import tdmq_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = tdmq_client.TdmqClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
```

## Create RocketMQ Topic (SDK)

```python
req = models.CreateRocketMQTopicRequest()
req.ClusterId = "{{user.cluster_id}}"
req.Namespace = "{{user.namespace}}"
req.Topic = "{{user.topic_name}}"
resp = client.CreateRocketMQTopic(req)
print(resp.TopicId)
```

## Error Pattern

TDMQ uses the standard `Response.Error` pattern:

```json
{ "Response": { "Error": { "Code": "ResourceNotFound.Topic", "Message": "..." } } }
```

Map to the Error Code Reference in `SKILL.md`.
