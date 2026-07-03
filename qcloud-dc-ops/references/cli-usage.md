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
