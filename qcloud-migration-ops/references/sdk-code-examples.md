# Migration SDK Code Examples

## Register Migration Task

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.msp import msp_client, models
import os, json

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = msp_client.MspClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.RegisterMigrationTaskRequest()
req.TaskName = "{{user.task_name}}"
req.TaskType = "{{user.task_type}}"
req.SrcNode = json.loads("{{user.source_config}}")
req.DstNode = json.loads("{{user.target_config}}")

resp = client.RegisterMigrationTask(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Describe Migration Task

```python
req = models.DescribeMigrationTaskRequest()
req.TaskId = "{{output.task_id}}"
resp = client.DescribeMigrationTask(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## List Migration Tasks

```python
req = models.ListMigrationTaskRequest()
resp = client.ListMigrationTask(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Deregister Migration Task

```python
req = models.DeregisterMigrationTaskRequest()
req.TaskId = "{{output.task_id}}"
resp = client.DeregisterMigrationTask(req)
print(json.dumps(resp.to_json_string(), indent=2))
```
