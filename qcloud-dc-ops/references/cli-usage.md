# CLI Usage Guide

## Command Map

| Operation | CLI Command | SDK Method |
|-----------|------------|------------|
| List Access Points | `tccli dc DescribeAccessPoints` | `DescribeAccessPoints` |
| Create DC | `tccli dc CreateDirectConnect` | `CreateDirectConnect` |
| List DCs | `tccli dc DescribeDirectConnects` | `DescribeDirectConnects` |
| Delete DC | `tccli dc DeleteDirectConnect` | `DeleteDirectConnect` |
| Create Tunnel | `tccli dc CreateDirectConnectTunnel` | `CreateDirectConnectTunnel` |
| List Tunnels | `tccli dc DescribeDirectConnectTunnels` | `DescribeDirectConnectTunnels` |
| Modify Tunnel | `tccli dc ModifyDirectConnectTunnelAttribute` | `ModifyDirectConnectTunnelAttribute` |
| Create Gateway | `tccli dc CreateDirectConnectGateway` | `CreateDirectConnectGateway` |
| List Gateways | `tccli dc DescribeDirectConnectGateways` | `DescribeDirectConnectGateways` |
| Create Tunnel (failover) | `tccli dc CreateDirectConnectTunnel --BfdEnable 1 --NqaEnable 1` | `CreateDirectConnectTunnel` |
| Configure Health Check | `tccli dc ModifyDirectConnectTunnelExtra --BfdEnable 1` | `ModifyDirectConnectTunnelExtra` |
| Tunnel Health Detail | `tccli dc DescribeDirectConnectTunnelExtra` | `DescribeDirectConnectTunnelExtra` |
| Cloud Attach (CCN) | `tccli dc CreateCloudAttachService --Data '<CreateCasInput>'` | `CreateCloudAttachService` |

## Common Patterns

```bash
# List available access points
tccli dc DescribeAccessPoints --Region ap-guangzhou

# List all dedicated connections
tccli dc DescribeDirectConnects --Region ap-guangzhou

# Filter by DC name
tccli dc DescribeDirectConnects \
  --Filters "Name=direct-connect-name,Values=my-dc"

# List tunnels for a specific DC
tccli dc DescribeDirectConnectTunnels \
  --Filters "Name=direct-connect-id,Values=dc-xxx"
```

## Filtering Examples

```bash
# Filter by status
tccli dc DescribeDirectConnects \
  --Filters "Name=state,Values=AVAILABLE"

# Filter by access point
tccli dc DescribeDirectConnects \
  --Filters "Name=access-point-id,Values=ap-guangzhou-1"
```

## Failover & Multi-cloud

```bash
# Create a redundant (backup) tunnel with BFD/NQA health check
tccli dc CreateDirectConnectTunnel \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DirectConnectId "dc-backup-xxx" --DirectConnectTunnelName "backup" \
  --DirectConnectGatewayId "dcg-xxx" --NetworkType VPC \
  --Bandwidth 100 --BfdEnable 1 --NqaEnable 1

# Enable/adjust health check on an existing tunnel
tccli dc ModifyDirectConnectTunnelExtra \
  --DirectConnectTunnelId "dct-xxx" --BfdEnable 1 \
  --BfdInfo '{"ProbeInterval":1000,"ProbeThreshold":3,"ProbeTimeout":200}'

# Inspect tunnel health / BGP session
tccli dc DescribeDirectConnectTunnelExtra --DirectConnectTunnelId "dct-xxx"

# Attach DC to CCN for multi-cloud / multi-region reach
tccli dc CreateCloudAttachService \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Data '{"CcasType":"CCN","ProviderName":"tencent","DirectConnectGatewayId":"dcg-xxx","CcnId":"ccn-xxx"}'
```

> Complex `BfdInfo` / `NqaInfo` / `Data` are passed as inline JSON. CCN routing config is
> delegated to `qcloud-ccn-ops`.
