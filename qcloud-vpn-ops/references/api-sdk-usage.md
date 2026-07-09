# VPN API & SDK Usage

> VPN API and SDK reference. All VPN APIs share the `vpc` product namespace.

## SDK Installation

```bash
pip install tencentcloud-sdk-python-vpc
```

## SDK Setup

```python
import os, json, time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.vpc.v20170312 import vpc_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
```

## API Reference

| API | SDK Method | CLI |
|-----|------------|-----|
| CreateVpnGateway | `client.CreateVpnGateway(req)` | `tccli vpc CreateVpnGateway` |
| DescribeVpnGateways | `client.DescribeVpnGateways(req)` | `tccli vpc DescribeVpnGateways` |
| DeleteVpnGateway | `client.DeleteVpnGateway(req)` | `tccli vpc DeleteVpnGateway` |
| ModifyVpnGatewayAttribute | `client.ModifyVpnGatewayAttribute(req)` | `tccli vpc ModifyVpnGatewayAttribute` |
| CreateCustomerGateway | `client.CreateCustomerGateway(req)` | `tccli vpc CreateCustomerGateway` |
| DescribeCustomerGateways | `client.DescribeCustomerGateways(req)` | `tccli vpc DescribeCustomerGateways` |
| DeleteCustomerGateway | `client.DeleteCustomerGateway(req)` | `tccli vpc DeleteCustomerGateway` |
| CreateVpnConnection | `client.CreateVpnConnection(req)` | `tccli vpc CreateVpnConnection` |
| DescribeVpnConnections | `client.DescribeVpnConnections(req)` | `tccli vpc DescribeVpnConnections` |
| DeleteVpnConnection | `client.DeleteVpnConnection(req)` | `tccli vpc DeleteVpnConnection` |
| CreateVpnGatewaySslServer | `client.CreateVpnGatewaySslServer(req)` | `tccli vpc CreateVpnGatewaySslServer` |
| DescribeVpnGatewaySslServers | `client.DescribeVpnGatewaySslServers(req)` | `tccli vpc DescribeVpnGatewaySslServers` |
| DeleteVpnGatewaySslServers | `client.DeleteVpnGatewaySslServers(req)` | `tccli vpc DeleteVpnGatewaySslServers` |
| CreateVpnGatewaySslClient | `client.CreateVpnGatewaySslClient(req)` | `tccli vpc CreateVpnGatewaySslClient` |
| DescribeVpnGatewaySslClients | `client.DescribeVpnGatewaySslClients(req)` | `tccli vpc DescribeVpnGatewaySslClients` |
| DeleteVpnGatewaySslClient | `client.DeleteVpnGatewaySslClient(req)` | `tccli vpc DeleteVpnGatewaySslClient` |

## SDK Quick Examples

> Detailed step-by-step flows with both CLI and SDK are in [execution-flows.md](execution-flows.md).

### Create VPN Gateway

```python
req = models.CreateVpnGatewayRequest()
req.VpcId = "vpc-xxx"
req.VpnGatewayName = "to-dc-1"
req.Bandwidth = 100
req.Zone = "ap-guangzhou-3"
req.InstanceChargeType = "POSTPAID_BY_HOUR"
req.ClientToken = str(int(time.time() * 1000000))
resp = client.CreateVpnGateway(req)
```

### Create Customer Gateway

```python
req = models.CreateCustomerGatewayRequest()
req.CustomerGatewayName = "onprem-fw-1"
req.IpAddress = "1.2.3.4"
resp = client.CreateCustomerGateway(req)
```

### Create VPN Connection (IPSec)

> PSK MUST be read from env var; never inline or echo.

```python
req = models.CreateVpnConnectionRequest()
req.VpnGatewayId = "vpngw-xxx"
req.CustomerGatewayId = "cgw-xxx"
req.VpnConnectionName = "tunnel-to-onprem-1"
req.PreShareKey = os.environ.get("PSK")  # NEVER inline or echo
req.VpnProto = "IPsec"
req.LocalCidrBlocks = ["10.0.0.0/16"]
req.RemoteCidrBlocks = ["192.168.0.0/16"]
resp = client.CreateVpnConnection(req)
```

### Describe VPN Connections

```python
req = models.DescribeVpnConnectionsRequest()
req.VpnGatewayIds = ["vpngw-xxx"]
resp = client.DescribeVpnConnections(req)
for conn in resp.VpnConnectionSet:
    print(f"{conn.VpnConnectionId}: {conn.State}")
```

### Delete VPN Connection

```python
req = models.DeleteVpnConnectionRequest()
req.VpnConnectionId = "vpnx-xxx"
try:
    client.DeleteVpnConnection(req)
except TencentCloudSDKException as e:
    if "ResourceNotFound" not in str(e):
        raise  # Already deleted — treat as success
```

### Delete VPN Gateway

```python
req = models.DeleteVpnGatewayRequest()
req.VpnGatewayId = "vpngw-xxx"
try:
    client.DeleteVpnGateway(req)
except TencentCloudSDKException as e:
    if "ResourceNotFound" not in str(e):
        raise
```

### Create SSL VPN Server

```python
req = models.CreateVpnGatewaySslServerRequest()
req.VpnGatewayId = "vpngw-xxx"
req.SslVpnServerName = "ops-ssl"
req.LocalAddress = "10.0.0.0/16"
req.RemoteAddress = "172.20.0.0/22"
req.SslVpnProtocol = "UDP"
req.Port = 1194
resp = client.CreateVpnGatewaySslServer(req)
```

### Create SSL VPN Client

```python
req = models.CreateVpnGatewaySslClientRequest()
req.SslVpnServerId = "sslvpns-xxx"
req.SslVpnClientName = "alice"
resp = client.CreateVpnGatewaySslClient(req)
```

### Delete SSL VPN Client

```python
req = models.DeleteVpnGatewaySslClientRequest()
req.SslVpnClientId = "sslvpnc-xxx"
client.DeleteVpnGatewaySslClient(req)
```

### Delete Customer Gateway

```python
req = models.DeleteCustomerGatewayRequest()
req.CustomerGatewayId = "cgw-xxx"
client.DeleteCustomerGateway(req)
```

## Error Handling

```python
try:
    resp = client.CreateVpnGateway(req)
    print(resp.to_json_string())
except TencentCloudSDKException as err:
    print(f"[ERROR] {err}")
```

## See also
- [Execution Flows](execution-flows.md) — Full CLI + SDK step-by-step for every operation
- [Core Concepts](core-concepts.md)
- [CLI Usage](cli-usage.md)
