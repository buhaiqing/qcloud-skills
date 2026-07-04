# CI/CD SDK Code Examples

## Your First Command — Credential Configuration

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
import os

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
print("Credentials configured successfully")
```

## Create Pipeline

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
import os, json

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

# Note: Actual client import depends on specific Tencent Cloud CI/CD service
# Example structure (replace with actual service module):
# from tencentcloud.[service] import [service]_client, models
# client = [service]_client.[Service]Client(cred, os.environ.get("TENCENTCLOUD_REGION"))
# req = models.CreatePipelineRequest()
# req.PipelineName = "{{user.pipeline_name}}"
# req.PipelineDesc = "{{user.pipeline_desc}}"
# resp = client.CreatePipeline(req)
# print(json.dumps(resp.to_json_string(), indent=2))
```

## Trigger Pipeline

```python
#!/usr/bin/env python3
# req = models.StartPipelineRequest()
# req.PipelineId = "{{user.pipeline_id}}"
# req.Branch = "{{user.branch}}"
# resp = client.StartPipeline(req)
# print(json.dumps(resp.to_json_string(), indent=2))
```

## Poll Pipeline Status

```python
import time
for i in range(60):
    # resp = client.DescribePipelineStatus(req)
    # status = resp.PipelineStatus
    # if status == "SUCCEEDED": break
    # if status == "FAILED": raise Exception("Build failed")
    time.sleep(10)
```

## Describe Pipelines

```python
#!/usr/bin/env python3
# req = models.DescribePipelinesRequest()
# resp = client.DescribePipelines(req)
# print(json.dumps(resp.to_json_string(), indent=2))
```

## Delete Pipeline

```python
#!/usr/bin/env python3
# req = models.DeletePipelineRequest()
# req.PipelineId = "{{output.pipeline_id}}"
# resp = client.DeletePipeline(req)
# print(json.dumps(resp.to_json_string(), indent=2))
```
