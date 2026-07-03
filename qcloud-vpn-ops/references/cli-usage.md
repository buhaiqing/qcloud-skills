# VPN CLI Usage (tccli)

> **cli_applicability: dual-path** — every execution flow in `SKILL.md` shows both `tccli` and Python SDK. This file is a quick reference for the most common CLI patterns.

## Verify CLI Support

```bash
tccli vpc help | grep -iE 'vpn|customer-gateway|ssl'
# Expected: CreateVpnGateway, DescribeVpnGateways, DeleteVpnGateway,
#           CreateVpnConnection, DescribeVpnConnections, DeleteVpnConnection,
#           CreateCustomerGateway, DescribeCustomerGateways, DeleteCustomerGateway,
#           CreateVpnGatewaySslServer, CreateVpnGatewaySslClient, ...
```

## Common Patterns

### List VPN Gateways

```bash
tccli vpc DescribeVpnGateways --Region ap-guangzhou
```

### Create VPN Gateway

```bash
tccli vpc CreateVpnGateway \
  --Region ap-guangzhou \
  --VpcId vpc-xxx \
  --VpnGatewayName "to-dc-1" \
  --Bandwidth 10 \
  --Zone ap-guangzhou-3 \
  --InstanceChargeType POSTPAID_BY_HOUR
```

### Register a Customer Gateway

```bash
tccli vpc CreateCustomerGateway \
  --Region ap-guangzhou \
  --CustomerGatewayName "onprem-fw-1" \
  --IpAddress 1.2.3.4
```

### Create IPSec Tunnel

```bash
# IMPORTANT: pass --PreShareKey via env var, not inline literal
export PSK='<16-32 char secret, never echo>'
tccli vpc CreateVpnConnection \
  --Region ap-guangzhou \
  --VpnGatewayId vpngw-xxx \
  --CustomerGatewayId cgw-xxx \
  --VpnConnectionName "to-onprem-1" \
  --PreShareKey "$PSK" \
  --VpnProto IPsec \
  --LocalCidrBlocks '["10.0.0.0/16"]' \
  --RemoteCidrBlocks '["192.168.0.0/16"]'
unset PSK
```

### Check Tunnel State

```bash
tccli vpc DescribeVpnConnections \
  --Region ap-guangzhou \
  --VpnConnectionIds "[\"vpnx-xxx\"]"
```

### SSL VPN Server / Client

```bash
# Create SSL server
tccli vpc CreateVpnGatewaySslServer \
  --Region ap-guangzhou \
  --VpnGatewayId vpngw-xxx \
  --SslVpnServerName "ops-ssl" \
  --LocalAddress 10.0.0.0/16 \
  --RemoteAddress 172.20.0.0/22 \
  --SslVpnProtocol UDP \
  --Port 1194

# Provision a client
tccli vpc CreateVpnGatewaySslClient \
  --Region ap-guangzhou \
  --SslVpnServerId sslvpns-xxx \
  --SslVpnClientName "alice"
```

## Coverage Gap (CLI vs SDK)

| API | `tccli vpc` |
|---|---|
| `CreateVpnGateway` / `DescribeVpnGateways` / `DeleteVpnGateways` / `ModifyVpnGatewayAttribute` | ✅ |
| `CreateVpnConnection` / `DescribeVpnConnections` / `DeleteVpnConnections` / `ModifyVpnConnectionAttribute` | ✅ |
| `CreateCustomerGateway` / `DescribeCustomerGateways` / `DeleteCustomerGateways` / `ModifyCustomerGatewayAttribute` | ✅ |
| `CreateVpnGatewaySslServer` / `DescribeVpnGatewaySslServers` / `DeleteVpnGatewaySslServers` | ✅ |
| `CreateVpnGatewaySslClient` / `DescribeVpnGatewaySslClients` / `DeleteVpnGatewaySslClients` | ✅ |

> SDK fallback is required for any future operation not exposed by the CLI; the dual-path pattern in `SKILL.md` already covers this.

## Error-Handling Pattern

CLI responses wrap the real error in `Response.Error`. To detect API errors from CLI:

```bash
out=$(tccli vpc CreateVpnGateway --Region ap-guangzhou --VpcId vpc-xxx --VpnGatewayName "test" --Bandwidth 10 --Zone ap-guangzhou-3 2>&1)
if echo "$out" | jq -e '.Response.Error' >/dev/null 2>&1; then
  code=$(echo "$out" | jq -r '.Response.Error.Code')
  msg=$(echo "$out" | jq -r '.Response.Error.Message')
  echo "[ERROR] $code: $msg"
  exit 1
fi
```

## Credential Safety Reminder

Never inline `PreShareKey` in a chat echo or log. The CLI accepts it via a shell variable; the SDK reads it from a `PSK` env var. Always `unset` after use.
