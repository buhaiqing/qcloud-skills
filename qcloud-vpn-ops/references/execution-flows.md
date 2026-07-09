# VPN Execution Flows

> **What vs. How** — This file describes **HOW** to execute each VPN operation (CLI/SDK commands).
> For **WHAT** each operation does and when to use it, see the parent `SKILL.md`.

## Index

| # | Operation | CLI Command | SDK Method |
|---|-----------|-------------|------------|
| 1 | Create VPN Gateway | `tccli vpc CreateVpnGateway` | `client.CreateVpnGateway()` |
| 2 | Describe VPN Gateways | `tccli vpc DescribeVpnGateways` | `client.DescribeVpnGateways()` |
| 3 | Create Customer Gateway | `tccli vpc CreateCustomerGateway` | `client.CreateCustomerGateway()` |
| 4 | Create VPN Connection (IPSec) | `tccli vpc CreateVpnConnection` | `client.CreateVpnConnection()` |
| 5 | Describe VPN Connections | `tccli vpc DescribeVpnConnections` | `client.DescribeVpnConnections()` |
| 6 | Delete VPN Connection | `tccli vpc DeleteVpnConnection` | `client.DeleteVpnConnection()` |
| 7 | Delete VPN Gateway | `tccli vpc DeleteVpnGateway` | `client.DeleteVpnGateway()` |
| 8 | Create SSL VPN Server | `tccli vpc CreateVpnGatewaySslServer` | `client.CreateVpnGatewaySslServer()` |
| 9 | Create SSL VPN Client | `tccli vpc CreateVpnGatewaySslClient` | `client.CreateVpnGatewaySslClient()` |
| 10 | Delete SSL VPN Client | `tccli vpc DeleteVpnGatewaySslClient` | `client.DeleteVpnGatewaySslClient()` |
| 11 | Delete Customer Gateway | `tccli vpc DeleteCustomerGateway` | `client.DeleteCustomerGateway()` |
| 12 | Multi-Branch Hub-Spoke Deployment | See §12 | See §12 |
| 13 | Modify VPN Gateway Attribute | `tccli vpc ModifyVpnGatewayAttribute` | `client.ModifyVpnGatewayAttribute()` |
| 14 | Modify VPN Connection Attribute | `tccli vpc ModifyVpnConnectionAttribute` | `client.ModifyVpnConnectionAttribute()` |
| 15 | Delete SSL VPN Server | `tccli vpc DeleteVpnGatewaySslServers` | `client.DeleteVpnGatewaySslServers()` |

---

## 1. Create VPN Gateway

### CLI

```bash
tccli vpc CreateVpnGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.vpc_id}}" \
  --VpnGatewayName "{{user.vpn_gateway_name}}" \
  --Bandwidth {{user.bandwidth}} \
  --Zone "{{user.zone}}" \
  --InstanceChargeType "POSTPAID_BY_HOUR" \
  --ClientToken "$(date +%s%N)"
```

### SDK

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.vpc import vpc_client, models
import os, json, time

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateVpnGatewayRequest()
req.VpcId = "{{user.vpc_id}}"
req.VpnGatewayName = "{{user.vpn_gateway_name}}"
req.Bandwidth = int("{{user.bandwidth}}")
req.Zone = "{{user.zone}}"
req.InstanceChargeType = "POSTPAID_BY_HOUR"
req.ClientToken = str(int(time.time() * 1000000))

resp = client.CreateVpnGateway(req)
print(resp.to_json_string())
```

### Post-execution Validation

```bash
for i in $(seq 1 18); do
  STATE=$(tccli vpc DescribeVpnGateways --VpnGatewayIds "[\"{{output.vpn_gateway_id}}\"]" | \
    jq -r '.Response.VpnGatewaySet[0].State')
  [ "$STATE" = "AVAILABLE" ] && break
  sleep 10
done
```

---

## 2. Describe VPN Gateways

### CLI — By ID

```bash
tccli vpc DescribeVpnGateways \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayIds "[\"{{output.vpn_gateway_id}}\"]"
```

### CLI — Filter by VPC

```bash
tccli vpc DescribeVpnGateways \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"
```

### SDK

```python
req = models.DescribeVpnGatewaysRequest()
req.VpnGatewayIds = ["{{output.vpn_gateway_id}}"]
resp = client.DescribeVpnGateways(req)
print(resp.to_json_string())
```

---

## 3. Create Customer Gateway

### CLI

```bash
tccli vpc CreateCustomerGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CustomerGatewayName "{{user.customer_gateway_name}}" \
  --IpAddress "{{user.peer_public_ip}}" \
  --ClientToken "$(date +%s%N)"
```

### SDK

```python
req = models.CreateCustomerGatewayRequest()
req.CustomerGatewayName = "{{user.customer_gateway_name}}"
req.IpAddress = "{{user.peer_public_ip}}"
resp = client.CreateCustomerGateway(req)
print(resp.to_json_string())
```

---

## 4. Create VPN Connection (IPSec Tunnel)

### CLI

```bash
tccli vpc CreateVpnConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayId "{{output.vpn_gateway_id}}" \
  --CustomerGatewayId "{{output.customer_gateway_id}}" \
  --VpnConnectionName "{{user.vpn_connection_name}}" \
  --PreShareKey "{{user.pre_shared_key}}" \
  --VpnProto "IPsec" \
  --IKESettings '{"IkeVersion":"{{user.ike_version}}","Identity":"ADDRESS","ExchangeMode":"{{user.ike_exchange_mode}}","LocalAddress":"{{output.vpn_gateway_public_ip}}","RemoteAddress":"{{user.peer_public_ip}}","LocalId":"{{output.vpn_gateway_public_ip}}","RemoteId":"{{user.peer_public_ip}}","IKESaLifetimeSeconds":{{user.ike_sa_lifetime}},"IKEEncryptionAlgorithm":"{{user.ike_encryption}}","IKEIntegrityAlgorithm":"{{user.ike_integrity}}","DHGroupName":"{{user.ike_dh_group}}"}' \
  --IPSECSettings '{"IpsecSaLifetimeTraffic": {{user.ipsec_sa_lifetime_traffic}}, "IpsecSaLifetimeSeconds": {{user.ipsec_sa_lifetime_seconds}}, "@type": "system"}' \
  --LocalCidrBlocks '["{{user.local_cidr}}"]' \
  --RemoteCidrBlocks '["{{user.peer_cidr}}"]' \
  --ClientToken "$(date +%s%N)"
```

> **PSK handling:** The PSK is passed via `--PreShareKey` only. Never echo the PSK back to the user.

### SDK

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.vpc import vpc_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateVpnConnectionRequest()
req.VpnGatewayId = "{{output.vpn_gateway_id}}"
req.CustomerGatewayId = "{{output.customer_gateway_id}}"
req.VpnConnectionName = "{{user.vpn_connection_name}}"
req.PreShareKey = "{{user.pre_shared_key}}"
req.VpnProto = "IPsec"
req.LocalCidrBlocks = ["{{user.local_cidr}}"]
req.RemoteCidrBlocks = ["{{user.peer_cidr}}"]
# IKESettings / IPSECSettings: build per API spec
resp = client.CreateVpnConnection(req)
print(resp.to_json_string())
```

### Post-execution Validation

```bash
for i in $(seq 1 18); do
  STATE=$(tccli vpc DescribeVpnConnections \
    --VpnConnectionIds "[\"{{output.vpn_connection_id}}\"]" | \
    jq -r '.Response.VpnConnectionSet[0].State')
  [ "$STATE" = "AVAILABLE" ] && break
  sleep 10
done
```

---

## 5. Describe VPN Connections

### CLI — By ID

```bash
tccli vpc DescribeVpnConnections \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnConnectionIds "[\"{{output.vpn_connection_id}}\"]"
```

### CLI — Filter by Gateway

```bash
tccli vpc DescribeVpnConnections \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpn-gateway-id,Values={{output.vpn_gateway_id}}"
```

### SDK

```python
req = models.DescribeVpnConnectionsRequest()
req.VpnConnectionIds = ["{{output.vpn_connection_id}}"]
resp = client.DescribeVpnConnections(req)
print(resp.to_json_string())
```

---

## 6. Delete VPN Connection

### CLI

```bash
tccli vpc DeleteVpnConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnConnectionId "{{output.vpn_connection_id}}"
```

### SDK

```python
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

req = models.DeleteVpnConnectionRequest()
req.VpnConnectionId = "{{output.vpn_connection_id}}"
try:
    client.DeleteVpnConnection(req)
except TencentCloudSDKException as e:
    if "ResourceNotFound" not in str(e):
        raise  # Already deleted — treat as success
```

### Post-execution Validation

Poll `DescribeVpnConnections`; expect absent within 60s.

---

## 7. Delete VPN Gateway

### CLI

```bash
tccli vpc DeleteVpnGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayId "{{output.vpn_gateway_id}}"
```

### SDK

```python
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

req = models.DeleteVpnGatewayRequest()
req.VpnGatewayId = "{{output.vpn_gateway_id}}"
try:
    client.DeleteVpnGateway(req)
except TencentCloudSDKException as e:
    if "ResourceNotFound" not in str(e):
        raise
```

### Post-execution Validation

Poll `DescribeVpnGateways`; expect absent within 120s.

---

## 8. Create SSL VPN Server

### CLI

```bash
tccli vpc CreateVpnGatewaySslServer \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayId "{{output.vpn_gateway_id}}" \
  --SslVpnServerName "{{user.ssl_vpn_server_name}}" \
  --LocalAddress "{{user.ssl_local_cidr}}" \
  --RemoteAddress "{{user.ssl_client_cidr}}" \
  --SslVpnProtocol "UDP" \
  --Port "{{user.ssl_port}}"
```

### SDK

```python
req = models.CreateVpnGatewaySslServerRequest()
req.VpnGatewayId = "{{output.vpn_gateway_id}}"
req.SslVpnServerName = "{{user.ssl_vpn_server_name}}"
req.LocalAddress = "{{user.ssl_local_cidr}}"
req.RemoteAddress = "{{user.ssl_client_cidr}}"
req.SslVpnProtocol = "UDP"
req.Port = int("{{user.ssl_port}}")
resp = client.CreateVpnGatewaySslServer(req)
print(resp.to_json_string())
```

### Post-execution Validation

Poll `DescribeVpnGatewaySslServers` until visible (max 30s).

---

## 9. Create SSL VPN Client

### CLI

```bash
tccli vpc CreateVpnGatewaySslClient \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --SslVpnServerId "{{output.ssl_server_id}}" \
  --SslVpnClientName "{{user.ssl_client_name}}"
```

### SDK

```python
req = models.CreateVpnGatewaySslClientRequest()
req.SslVpnServerId = "{{output.ssl_server_id}}"
req.SslVpnClientName = "{{user.ssl_client_name}}"
resp = client.CreateVpnGatewaySslClient(req)
print(resp.to_json_string())
```

### Post-execution Validation

Capture the cert payload from the response; warn user it is shown only once.

---

## 10. Delete SSL VPN Client

### CLI

```bash
tccli vpc DeleteVpnGatewaySslClient \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --SslVpnClientId "{{output.ssl_client_id}}"
```

### SDK

```python
req = models.DeleteVpnGatewaySslClientRequest()
req.SslVpnClientId = "{{output.ssl_client_id}}"
client.DeleteVpnGatewaySslClient(req)
```

### Post-execution Validation

Poll `DescribeVpnGatewaySslClients`; expect absent within 30s.

---

## 11. Delete Customer Gateway

### CLI

```bash
tccli vpc DeleteCustomerGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CustomerGatewayId "{{output.customer_gateway_id}}"
```

### SDK

```python
req = models.DeleteCustomerGatewayRequest()
req.CustomerGatewayId = "{{output.customer_gateway_id}}"
client.DeleteCustomerGateway(req)
```

### Post-execution Validation

Poll `DescribeCustomerGateways`; expect absent within 30s.

---

## 12. Multi-Branch Hub-Spoke Topology Deployment

Deploy a Hub-Spoke topology with a single VPN Gateway in the VPC (Hub) and multiple branch offices (Spokes), each connected via an IPSec tunnel.

### Pre-flight Checks

> **General checks**: See [SKILL.md §Create VPN Gateway](../SKILL.md#operation-create-vpn-gateway) and [SKILL.md §Create VPN Connection](../SKILL.md#operation-create-vpn-connection-ipsec-tunnel) for standard pre-flight validation.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Branch CIDRs non-overlapping | Validate each `{{user.branch_n_cidr}}` against VPC CIDR and other branch CIDRs | No overlap | HALT; ask user to re-plan CIDR allocation |
| Bandwidth adequate | Sum of branch bandwidth expectations ≤ gateway bandwidth | Sum ≤ gateway spec | HALT; upgrade gateway or reduce branches |

### CLI — Create Customer Gateways for Each Branch

```bash
# Branch 1
tccli vpc CreateCustomerGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CustomerGatewayName "branch1-cgw" \
  --IpAddress "{{user.branch1_public_ip}}" \
  --ClientToken "$(date +%s%N)1"

# Branch 2
tccli vpc CreateCustomerGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CustomerGatewayName "branch2-cgw" \
  --IpAddress "{{user.branch2_public_ip}}" \
  --ClientToken "$(date +%s%N)2"

# Repeat for N branches...
```

### CLI — Create VPN Connections (One per Branch)

```bash
# Tunnel to Branch 1
tccli vpc CreateVpnConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayId "{{output.vpn_gateway_id}}" \
  --CustomerGatewayId "{{output.branch1_cgw_id}}" \
  --VpnConnectionName "tunnel-to-branch1" \
  --PreShareKey "{{user.pre_shared_key}}" \
  --VpnProto "IPsec" \
  --LocalCidrBlocks '["{{user.vpc_cidr}}"]' \
  --RemoteCidrBlocks '["{{user.branch1_cidr}}"]' \
  --ClientToken "$(date +%s%N)b1"

# Tunnel to Branch 2
tccli vpc CreateVpnConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayId "{{output.vpn_gateway_id}}" \
  --CustomerGatewayId "{{output.branch2_cgw_id}}" \
  --VpnConnectionName "tunnel-to-branch2" \
  --PreShareKey "{{user.pre_shared_key}}" \
  --VpnProto "IPsec" \
  --LocalCidrBlocks '["{{user.vpc_cidr}}"]' \
  --RemoteCidrBlocks '["{{user.branch2_cidr}}"]' \
  --ClientToken "$(date +%s%N)b2"
```

### SDK

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.vpc import vpc_client, models
import os, json, time

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

branches = [
    {"name": "branch1", "ip": "{{user.branch1_public_ip}}", "cidr": "{{user.branch1_cidr}}"},
    {"name": "branch2", "ip": "{{user.branch2_public_ip}}", "cidr": "{{user.branch2_cidr}}"},
]

# Create Customer Gateways
cgw_ids = {}
for b in branches:
    req = models.CreateCustomerGatewayRequest()
    req.CustomerGatewayName = f"{b['name']}-cgw"
    req.IpAddress = b["ip"]
    resp = client.CreateCustomerGateway(req)
    parsed = json.loads(resp.to_json_string())
    cgw_ids[b["name"]] = parsed["Response"]["CustomerGateway"]["CustomerGatewayId"]

# Create VPN Connections
for b in branches:
    req = models.CreateVpnConnectionRequest()
    req.VpnGatewayId = "{{output.vpn_gateway_id}}"
    req.CustomerGatewayId = cgw_ids[b["name"]]
    req.VpnConnectionName = f"tunnel-to-{b['name']}"
    req.PreShareKey = "{{user.pre_shared_key}}"
    req.VpnProto = "IPsec"
    req.LocalCidrBlocks = ["{{user.vpc_cidr}}"]
    req.RemoteCidrBlocks = [b["cidr"]]
    resp = client.CreateVpnConnection(req)
    print(resp.to_json_string())
```

### Post-execution Validation

```bash
# Verify all tunnels are AVAILABLE
tccli vpc DescribeVpnConnections \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpn-gateway-id,Values={{output.vpn_gateway_id}}" | \
  jq -r '.Response.VpnConnectionSet[] | "\(.VpnConnectionName): \(.State)"'

# Expected output (example):
# tunnel-to-branch1: AVAILABLE
# tunnel-to-branch2: AVAILABLE
```

### Recover

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| `InvalidParameterValue.Malformed` | Parameter format error | Check JSON/string format; verify CIDR notation |
| `LimitExceeded` | Quota exceeded (too many connections per gateway) | HALT; raise quota or use multiple gateways |
| `ResourceInUse` | Customer Gateway already referenced | Use existing CGW or delete conflicting references |
| `InvalidParameterValue.Duplicate` | Duplicate tunnel name | Use unique connection names per branch |

---

## 13. Modify VPN Gateway Attribute

### CLI

```bash
tccli vpc ModifyVpnGatewayAttribute \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayId "{{output.vpn_gateway_id}}" \
  --VpnGatewayName "{{user.new_vpn_gateway_name}}" \
  --Bandwidth {{user.new_bandwidth}}
```

### SDK

```python
req = models.ModifyVpnGatewayAttributeRequest()
req.VpnGatewayId = "{{output.vpn_gateway_id}}"
req.VpnGatewayName = "{{user.new_vpn_gateway_name}}"
req.Bandwidth = int("{{user.new_bandwidth}}")
client.ModifyVpnGatewayAttribute(req)
```

### Post-execution Validation

```bash
tccli vpc DescribeVpnGateways \
  --VpnGatewayIds "[\"{{output.vpn_gateway_id}}\"]" | \
  jq -r '.Response.VpnGatewaySet[0] | {Name: .VpnGatewayName, Bandwidth: .Bandwidth}'
```

---

## 14. Modify VPN Connection Attribute

### CLI

```bash
tccli vpc ModifyVpnConnectionAttribute \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnConnectionId "{{output.vpn_connection_id}}" \
  --VpnConnectionName "{{user.new_vpn_connection_name}}"
```

### SDK

```python
req = models.ModifyVpnConnectionAttributeRequest()
req.VpnConnectionId = "{{output.vpn_connection_id}}"
req.VpnConnectionName = "{{user.new_vpn_connection_name}}"
client.ModifyVpnConnectionAttribute(req)
```

> **Warning:** Modifying IKE/IPSec crypto policy requires recreating the connection. This API only supports name and health check modifications.

---

## 15. Delete SSL VPN Server

### CLI

```bash
tccli vpc DeleteVpnGatewaySslServers \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --SslVpnServerIds "[\"{{output.ssl_server_id}}\"]"
```

### SDK

```python
req = models.DeleteVpnGatewaySslServersRequest()
req.SslVpnServerIds = ["{{output.ssl_server_id}}"]
client.DeleteVpnGatewaySslServers(req)
```

### Post-execution Validation

Poll `DescribeVpnGatewaySslServers`; expect absent within 30s.
