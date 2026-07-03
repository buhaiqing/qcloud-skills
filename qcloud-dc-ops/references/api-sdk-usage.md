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
from tencentcloud.dc import dc_client, models
import os, json

def call_api():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = dc_client.DcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        # Make API calls
        return client
    except TencentCloudSDKException as e:
        print(f"API Error: {e}")
        raise
```

## Common Operations

| Operation | SDK Method | Notes |
|-----------|------------|-------|
| CreateDirectConnect | `CreateDirectConnect` | Requires access point ID |
| DescribeDirectConnects | `DescribeDirectConnects` | Supports filtering |
| DeleteDirectConnect | `DeleteDirectConnect` | Destructive — requires confirmation |
| CreateDirectConnectTunnel | `CreateDirectConnectTunnel` | Requires DC and gateway IDs |
| DescribeDirectConnectTunnels | `DescribeDirectConnectTunnels` | List tunnels |
| CreateDirectConnectGateway | `CreateDirectConnectGateway` | VPC-side gateway |
| DescribeDirectConnectGateways | `DescribeDirectConnectGateways` | List gateways |

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
req = models.DescribeDirectConnectsRequest()
req.Limit = 100
req.Offset = 0

all_dcs = []
while True:
    resp = client.DescribeDirectConnects(req)
    all_dcs.extend(resp.DirectConnectSet)
    if len(resp.DirectConnectSet) < req.Limit:
        break
    req.Offset += len(resp.DirectConnectSet)
```
