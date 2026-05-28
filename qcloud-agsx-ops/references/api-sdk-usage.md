# API & SDK Usage

All examples use `tencentcloud-sdk-python` >= 3.0.1300. Install: `pip install tencentcloud-sdk-python-ags`.

## Setup

```python
import os
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.ags.v20250920 import ags_client, models

cred = credential.Credential(os.environ["TENCENTCLOUD_SECRET_ID"], os.environ["TENCENTCLOUD_SECRET_KEY"])
http_profile = HttpProfile(endpoint="ags.tencentcloudapi.com")
client_profile = ClientProfile(httpProfile=http_profile)
client = ags_client.AgsClient(cred, "ap-guangzhou", client_profile)
```

## Flow 1: CreateSandboxTool

```python
req = models.CreateSandboxToolRequest()
req.from_json_string('{"ToolName":"my-code-tool","ToolType":"CodeSandbox","DefaultTimeout":3600,"Description":"Code sandbox for AI agent"}')
resp = client.CreateSandboxTool(req)
# resp.ToolId -> stool-xxxxxxxx
```

## Flow 2: DescribeSandboxToolList

```python
req = models.DescribeSandboxToolListRequest()
req.from_json_string('{"Limit":20,"Offset":0}')
resp = client.DescribeSandboxToolList(req)
for tool in resp.ToolSet:
    print(tool.ToolId, tool.ToolName, tool.Status)
```

## Flow 3: UpdateSandboxTool

```python
req = models.UpdateSandboxToolRequest()
req.from_json_string('{"ToolId":"stool-xxxxxxxx","Description":"Updated description"}')
resp = client.UpdateSandboxTool(req)
```

## Flow 4: DeleteSandboxTool (SAFETY GATE)

```python
# Pre-check: confirm no active instances
desc_req = models.DescribeSandboxInstanceListRequest()
desc_req.from_json_string('{"ToolId":"stool-xxxxxxxx"}')
desc_resp = client.DescribeSandboxInstanceList(desc_req)
assert len(desc_resp.InstanceSet) == 0, "Stop instances first"
# Require user confirmation
req = models.DeleteSandboxToolRequest()
req.from_json_string('{"ToolId":"stool-xxxxxxxx"}')
resp = client.DeleteSandboxTool(req)
```

## Flow 5: StartSandboxInstance

```python
req = models.StartSandboxInstanceRequest()
req.from_json_string('{"ToolId":"stool-xxxxxxxx","ToolName":"my-instance","Timeout":3600,"Metadata":[{"Key":"agent_id","Value":"agent-001"}]}')
resp = client.StartSandboxInstance(req)
# resp.InstanceId -> si-xxxxxxxx
```

## Flow 6: DescribeSandboxInstanceList

```python
req = models.DescribeSandboxInstanceListRequest()
req.from_json_string('{"InstanceIds":["si-xxxxxxxx"],"Limit":20}')
resp = client.DescribeSandboxInstanceList(req)
for inst in resp.InstanceSet:
    print(inst.InstanceId, inst.Status, inst.CreatedAt, inst.ExpireAt)
```

## Flow 7: StopSandboxInstance (SAFETY GATE)

```python
# Require user confirmation for stopping instance
req = models.StopSandboxInstanceRequest()
req.from_json_string('{"InstanceId":"si-xxxxxxxx"}')
resp = client.StopSandboxInstance(req)
```

## Flow 8: PauseSandboxInstance

```python
req = models.PauseSandboxInstanceRequest()
req.from_json_string('{"InstanceId":"si-xxxxxxxx"}')
resp = client.PauseSandboxInstance(req)
# Status becomes PAUSED
```

## Flow 9: ResumeSandboxInstance

```python
req = models.ResumeSandboxInstanceRequest()
req.from_json_string('{"InstanceId":"si-xxxxxxxx"}')
resp = client.ResumeSandboxInstance(req)
# Status becomes RUNNING
```

## Flow 10: CreateAPIKey

```python
req = models.CreateAPIKeyRequest()
req.from_json_string('{"Name":"prod-key-01"}')
resp = client.CreateAPIKey(req)
# resp.ApiKey -> store securely, shown only once
# MASK in logs: ak-****resp.ApiKey[-4:]
```

## Flow 11: DeleteAPIKey (SAFETY GATE)

```python
# Warn: all sandbox instances using this key will lose connectivity
req = models.DeleteAPIKeyRequest()
req.from_json_string('{"KeyId":"ak-xxxxxxxx"}')
resp = client.DeleteAPIKey(req)
```

## Flow 12: CreatePreCacheImageTask

```python
req = models.CreatePreCacheImageTaskRequest()
req.from_json_string('{"Image":"img-default-python311","ImageRegistryType":"DockerHub"}')
resp = client.CreatePreCacheImageTask(req)
# Reduces cold-start from ~500ms to ~100ms
```

## Client-side: e2b-code-interpreter

```python
import os
os.environ["E2B_DOMAIN"] = "ap-guangzhou.tencentags.com"
os.environ["E2B_API_KEY"] = "ak-xxxxxxxx"  # from CreateAPIKey

from e2b_code_interpreter import Sandbox
with Sandbox() as sbx:
    exec_result = sbx.run_code("print(1+1)")
    print(exec_result.logs.stdout)
```
