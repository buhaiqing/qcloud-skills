# API & SDK Usage Guide

## SDK Installation

```bash
pip install tencentcloud-sdk-python
```

## Basic SDK Pattern

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
import os, json

def call_api():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        # Client initialization depends on specific service module
        # client = ServiceClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        # response = client.SomeAction(request)
        # return response
    except TencentCloudSDKException as e:
        print(f"API Error: {e}")
        raise
```

## Common Operations

| Operation | SDK Method | Notes |
|-----------|------------|-------|
| CreatePipeline | `CreatePipeline` | Requires pipeline configuration |
| DescribePipelines | `DescribePipelines` | Supports filtering and pagination |
| DeletePipeline | `DeletePipeline` | Destructive — requires confirmation |
| StartPipeline | `StartPipeline` | Trigger new build |
| StopPipeline | `StopPipeline` | Cancel running build |
| DescribeBuildLogs | `DescribeBuildLogs` | Retrieve execution logs |

## Error Handling

```python
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

try:
    response = client.SomeAction(request)
except TencentCloudSDKException as e:
    error_code = e.get_code()
    error_message = e.get_message()
    request_id = e.get_request_id()
    # Handle specific error codes
```

## Pagination

For list operations:

```python
# req.Limit = 100
# req.Offset = 0
# while has_more:
#     resp = client.DescribePipelines(req)
#     process(resp.PipelineSet)
#     req.Offset += len(resp.PipelineSet)
#     has_more = len(resp.PipelineSet) == req.Limit
```
