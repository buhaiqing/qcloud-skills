# AGSX SDK Code Examples

This file contains all Python SDK code examples extracted from the AGSX SKILL.md.

## Table of Contents

1. [Quick Start - Your First Command](#quick-start---your-first-command)
2. [CreateSandboxTool](#createsandboxtool)
3. [DescribeSandboxToolList](#describesandboxtoollist)
4. [UpdateSandboxTool](#updatesandboxtool)
5. [DeleteSandboxTool](#deletesandboxtool)
6. [StartSandboxInstance](#startsandboxinstance)
7. [DescribeSandboxInstanceList](#describesandboxinstancelist)
8. [StopSandboxInstance](#stopsandboxinstance)
9. [CreateAPIKey](#createapikey)
10. [DeleteAPIKey](#deleteapikey)
11. [CreatePreCacheImageTask](#createprecachimagetask)

---

## Quick Start - Your First Command

```python
import os
from tencentcloud.common import credential
from tencentcloud.ags.v20250920 import ags_client, models

cred = credential.Credential(
    os.environ["TENCENTCLOUD_SECRET_ID"],
    os.environ["TENCENTCLOUD_SECRET_KEY"]
)
client = ags_client.AgsClient(cred, "ap-guangzhou")
resp = client.DescribeSandboxToolList(models.DescribeSandboxToolListRequest())
print(resp.to_json_string())
```

## CreateSandboxTool

```python
import json
from tencentcloud.ags.v20250920 import ags_client, models

req = models.CreateSandboxToolRequest()
req.from_json_string(json.dumps({
    "ToolName": "{{user.tool_name}}",
    "ToolType": "CodeSandbox",       # CodeSandbox | BrowserSandbox | CustomSandbox
    "DefaultTimeout": 3600,
    "Description": "Created by AGSX skill"
}))
resp = client.CreateSandboxTool(req)
# resp.ToolId -> stool-xxxxxxxx (capture as {{output.resource_id}})
```

## DescribeSandboxToolList

```python
req = models.DescribeSandboxToolListRequest()
req.from_json_string('{"Limit": 20, "Offset": 0}')
resp = client.DescribeSandboxToolList(req)
for tool in resp.ToolSet:
    print(tool.ToolId, tool.ToolName, tool.Status)
```

## UpdateSandboxTool

```python
import json
req = models.UpdateSandboxToolRequest()
req.from_json_string(json.dumps({
    "ToolId": "{{user.tool_id}}",
    "Description": "Updated description"
}))
resp = client.UpdateSandboxTool(req)
```

## DeleteSandboxTool

```python
import json
# Pre-check: confirm no active instances
desc_req = models.DescribeSandboxInstanceListRequest()
desc_req.from_json_string(json.dumps({"ToolId": "{{user.tool_id}}"}))
desc_resp = client.DescribeSandboxInstanceList(desc_req)
if len(desc_resp.InstanceSet) > 0:
    print(f"[WARN] {len(desc_resp.InstanceSet)} active instances. Stop first.")
    # HALT until instances cleared

# User confirmed; proceed
req = models.DeleteSandboxToolRequest()
req.from_json_string(json.dumps({"ToolId": "{{user.tool_id}}"}))
resp = client.DeleteSandboxTool(req)
```

## StartSandboxInstance

```python
import json
req = models.StartSandboxInstanceRequest()
req.from_json_string(json.dumps({
    "ToolId": "{{user.tool_id}}",
    "ToolName": "{{user.tool_name}}",
    "Timeout": 3600,
    "Metadata": [{"Key": "agent_id", "Value": "agent-001"}]
}))
resp = client.StartSandboxInstance(req)
# resp.InstanceId -> si-xxxxxxxx
# resp.Endpoint -> wss://si-xxx.ap-guangzhou.tencentags.com
```

## DescribeSandboxInstanceList

```python
import json
req = models.DescribeSandboxInstanceListRequest()
req.from_json_string(json.dumps({"InstanceIds": ["{{user.instance_id}}"]}))
resp = client.DescribeSandboxInstanceList(req)
for inst in resp.InstanceSet:
    print(inst.InstanceId, inst.Status, inst.CreatedAt, inst.ExpireAt)
```

## StopSandboxInstance

```python
import json
req = models.StopSandboxInstanceRequest()
req.from_json_string(json.dumps({"InstanceId": "{{user.instance_id}}"}))
resp = client.StopSandboxInstance(req)
```

## CreateAPIKey

```python
req = models.CreateAPIKeyRequest()
req.from_json_string(json.dumps({"Name": "prod-key-01"}))
resp = client.CreateAPIKey(req)
# resp.ApiKey -> store securely, shown only once
# MASK in logs: ak-****resp.ApiKey[-4:]
```

## DeleteAPIKey

```python
req = models.DeleteAPIKeyRequest()
req.from_json_string(json.dumps({"KeyId": "{{user.key_id}}"}))
resp = client.DeleteAPIKey(req)
```

## CreatePreCacheImageTask

```python
import json
req = models.CreatePreCacheImageTaskRequest()
req.from_json_string(json.dumps({
    "Image": "{{user.image_id}}",
    "ImageRegistryType": "DockerHub"
}))
resp = client.CreatePreCacheImageTask(req)
# Reduces cold-start from ~500ms to ~100ms
```