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
from tencentcloud.msp import msp_client, models
import os, json

def call_api():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = msp_client.MspClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        # Make API calls
        return client
    except TencentCloudSDKException as e:
        print(f"API Error: {e}")
        raise
```

## Common Operations

| Operation | SDK Method | Notes |
|-----------|------------|-------|
| RegisterMigrationTask | `RegisterMigrationTask` | Requires source/target config |
| ListMigrationTask | `ListMigrationTask` | Supports filtering |
| DescribeMigrationTask | `DescribeMigrationTask` | Get task details |
| ModifyMigrationTaskStatus | `ModifyMigrationTaskStatus` | Update task state |
| DeregisterMigrationTask | `DeregisterMigrationTask` | Remove task metadata |

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
#     resp = client.ListMigrationTask(req)
#     process(resp.Tasks)
#     req.Offset += len(resp.Tasks)
#     has_more = len(resp.Tasks) == req.Limit
```
