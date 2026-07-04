# Direct Connect SDK Code Examples

## Create Direct Connect

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.dc import dc_client, models
import os, json

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = dc_client.DcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateDirectConnectRequest()
req.DirectConnectName = "{{user.dc_name}}"
req.AccessPointId = "{{user.access_point}}"
req.LineOperator = "{{user.operator}}"
req.Bandwidth = {{user.bandwidth}}

resp = client.CreateDirectConnect(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Create Direct Connect Tunnel

```python
req = models.CreateDirectConnectTunnelRequest()
req.DirectConnectId = "{{output.dc_id}}"
req.DirectConnectTunnelName = "{{user.tunnel_name}}"
req.DirectConnectGatewayId = "{{user.gateway_id}}"
req.NetworkType = "{{user.network_type}}"
req.NetworkRegion = "{{user.network_region}}"
resp = client.CreateDirectConnectTunnel(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Describe Direct Connects

```python
req = models.DescribeDirectConnectsRequest()
req.Filters = [{"Name": "direct-connect-name", "Values": ["{{user.dc_name}}"]}]
resp = client.DescribeDirectConnects(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Delete Direct Connect

```python
# Delete tunnel first
req_tunnel = models.DeleteDirectConnectTunnelRequest()
req_tunnel.DirectConnectTunnelId = "{{user.tunnel_id}}"
client.DeleteDirectConnectTunnel(req_tunnel)

# Delete DC
req_dc = models.DeleteDirectConnectRequest()
req_dc.DirectConnectId = "{{output.dc_id}}"
resp = client.DeleteDirectConnect(req_dc)
print(json.dumps(resp.to_json_string(), indent=2))
```
