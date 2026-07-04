# Service Mesh (TCM) SDK Code Examples

Python SDK fallback code examples for operations where `tccli` fields are incomplete or complex JSON parameters are needed.

## Create Mesh (SDK Fallback)

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.tcm import tcm_client, models
import os, json

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = tcm_client.TcmClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateMeshRequest()
req.MeshName = "{{user.mesh_name}}"
req.MeshVersion = "1.18.1-istio"

resp = client.CreateMesh(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Link Cluster (SDK Fallback)

```python
req = models.LinkClusterListRequest()
req.MeshId = "{{output.mesh_id}}"
req.ClusterList = ["{{user.cluster_id}}"]
resp = client.LinkClusterList(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Delete Mesh (SDK Fallback)

```python
# Unlink cluster
req_unlink = models.UnlinkClusterRequest()
req_unlink.MeshId = "{{output.mesh_id}}"
req_unlink.ClusterId = "{{user.cluster_id}}"
client.UnlinkCluster(req_unlink)

# Delete mesh
req_delete = models.DeleteMeshRequest()
req_delete.MeshId = "{{output.mesh_id}}"
resp = client.DeleteMesh(req_delete)
print(json.dumps(resp.to_json_string(), indent=2))
```
