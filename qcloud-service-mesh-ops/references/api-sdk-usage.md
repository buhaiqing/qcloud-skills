# API & SDK Usage Guide

## SDK Installation

```bash
pip install tencentcloud-sdk-python
```

## TCM Service Client

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.tcm import tcm_client, models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
import os, json

def get_tcm_client():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    return tcm_client.TcmClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
```

## Common Operations

| Operation | SDK Method | CLI Command |
|-----------|------------|-------------|
| CreateMesh | `CreateMesh` | `tccli tcm CreateMesh` |
| DescribeMeshList | `DescribeMeshList` | `tccli tcm DescribeMeshList` |
| DescribeMesh | `DescribeMesh` | `tccli tcm DescribeMesh` |
| DeleteMesh | `DeleteMesh` | `tccli tcm DeleteMesh` |
| LinkClusterList | `LinkClusterList` | `tccli tcm LinkClusterList` |
| UnlinkCluster | `UnlinkCluster` | `tccli tcm UnlinkCluster` |
| ModifyMesh | `ModifyMesh` | `tccli tcm ModifyMesh` |
| ModifyTracingConfig | `ModifyTracingConfig` | `tccli tcm ModifyTracingConfig` |
| ModifyAccessLogConfig | `ModifyAccessLogConfig` | `tccli tcm ModifyAccessLogConfig` |

## Example: Create Mesh

```python
#!/usr/bin/env python3
try:
    client = get_tcm_client()
    req = models.CreateMeshRequest()
    req.MeshName = "production-mesh"
    req.MeshVersion = "1.18.1-istio"
    
    resp = client.CreateMesh(req)
    mesh_id = resp.MeshId
    print(f"Created mesh: {mesh_id}")
    
except TencentCloudSDKException as e:
    print(f"Error: {e}")
```

## Example: Link Cluster

```python
#!/usr/bin/env python3
try:
    client = get_tcm_client()
    req = models.LinkClusterListRequest()
    req.MeshId = "mesh-xxx"
    req.ClusterList = ["cls-xxx"]
    
    resp = client.LinkClusterList(req)
    print(f"Linked clusters: {resp.LinkedClusterSet}")
    
except TencentCloudSDKException as e:
    print(f"Error: {e}")
```

## Error Handling

```python
from tencentcloud.common.exception.tencent_cloud_sdkException import TencentCloudSDKException

try:
    response = client.SomeAction(request)
except TencentCloudSDKException as e:
    error_code = e.get_code()
    error_message = e.get_message()
    request_id = e.get_request_id()
    # Handle specific error codes
```
