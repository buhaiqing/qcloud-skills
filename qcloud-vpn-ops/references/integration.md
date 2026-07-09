# VPN Integration

> VPN integration patterns with other Tencent Cloud services and hybrid cloud architectures.

## VPC Integration

VPN Gateway must be attached to a VPC:

1. Create VPC and subnet via `qcloud-vpc-ops`
2. Create VPN Gateway: `tccli vpc CreateVpnGateway --VpcId vpc-xxx`
3. Create Customer Gateway for on-prem peer
4. Create VPN Connection (tunnel)
5. Configure VPC route table with `NextType=VPNGW`

### Route Table Configuration

After creating a VPN Connection, add a route in the VPC route table:

```bash
# Delegate to qcloud-vpc-ops
tccli vpc CreateRoutes \
  --RouteTableId "rtb-xxx" \
  --Routes '[{
    "DestinationCidrBlock": "192.168.0.0/16",
    "GatewayType": "VPNGW",
    "GatewayId": "vpngw-xxx"
  }]'
```

## On-Premises Integration

- VPN connects on-premises network to Tencent Cloud VPC
- Customer Gateway IP must be a public IP address
- Both ends must have matching IKE and IPSec policies
- Required ports: UDP 500 (IKE), UDP 4500 (NAT-T)

### Firewall Requirements

| Direction | Port | Protocol | Purpose |
|-----------|------|----------|---------|
| Inbound | 500 | UDP | IKE negotiation |
| Inbound | 4500 | UDP | NAT traversal (NAT-T) |
| Outbound | 500 | UDP | IKE negotiation |
| Outbound | 4500 | UDP | NAT traversal |

## CCN Integration (VPN + CCN Hybrid)

For multi-region hybrid cloud, combine VPN with Cloud Connect Network (CCN):

```
                    ┌──────────────────────────────────────┐
                    │            CCN (qcloud-ccn-ops)      │
                    │                                      │
    ┌───────────────┼──────────────┐   ┌─────────────────┼──────────────┐
    │               │              │   │                 │              │
    ▼               ▼              │   ▼                 ▼              │
┌─────────┐   ┌─────────┐         │ ┌─────────┐   ┌─────────┐         │
│ VPC-A   │   │ VPC-B   │         │ │ VPC-C   │   │ VPC-D   │         │
│ Guangzhou│   │ Shanghai│         │ │ Beijing │   │ Chengdu │         │
└────┬────┘   └─────────┘         │ └────┬────┘   └─────────┘         │
     │                              │      │                           │
     │ VPN Gateway                  │      │ VPN Gateway               │
     │                              │      │                           │
     ▼                              │      ▼                           │
┌─────────────┐                     │  ┌─────────────┐                 │
│ On-prem DC  │                     │  │ Branch Office│                 │
│ (IPSec VPN) │                     │  │ (IPSec VPN)  │                 │
└─────────────┘                     │  └─────────────┘                 │
                                    └──────────────────────────────────┘
```

### Use Case: VPN as Backup for CCN

When CCN is the primary path, VPN can serve as backup:

1. **Primary**: CCN connects VPCs across regions
2. **Backup**: VPN tunnel provides fallback if CCN fails
3. **Routing**: Configure route priority (CCN higher priority than VPN)

```bash
# Route via CCN (priority 100)
tccli vpc CreateRoutes \
  --RouteTableId "rtb-xxx" \
  --Routes '[{
    "DestinationCidrBlock": "10.1.0.0/16",
    "GatewayType": "CCN",
    "GatewayId": "ccn-xxx"
  }]'

# Route via VPN (priority 200, backup)
tccli vpc CreateRoutes \
  --RouteTableId "rtb-xxx" \
  --Routes '[{
    "DestinationCidrBlock": "10.1.0.0/16",
    "GatewayType": "VPNGW",
    "GatewayId": "vpngw-xxx"
  }]'
```

## Direct Connect Integration (VPN + DC Hybrid)

For high-availability hybrid cloud, combine VPN with Direct Connect:

```
                    ┌──────────────────────────────────────┐
                    │          Tencent Cloud VPC           │
                    │                                      │
                    │  ┌─────────────┐  ┌─────────────┐   │
                    │  │ VPN Gateway │  │ Direct      │   │
                    │  │ (Backup)    │  │ Connect GW  │   │
                    │  └──────┬──────┘  └──────┬──────┘   │
                    └─────────│────────────────│──────────┘
                              │                │
                              │                │ Dedicated Line
                              │                │ (High BW, Low Latency)
                              │                │
                              ▼                ▼
                    ┌──────────────────────────────────────┐
                    │        On-Premises Data Center       │
                    │                                      │
                    │  ┌─────────────┐  ┌─────────────┐   │
                    │  │ VPN Router  │  │ DC Router   │   │
                    │  │ (Backup)    │  │ (Primary)   │   │
                    │  └─────────────┘  └─────────────┘   │
                    └──────────────────────────────────────┘
```

### Use Case: VPN as Backup for Direct Connect

| Path | Bandwidth | Latency | Cost | Use Case |
|------|-----------|---------|------|----------|
| Direct Connect | 1-100 Gbps | <5ms | High | Primary production traffic |
| VPN | 5-1000 Mbps | 20-100ms | Low | Backup, non-critical traffic |

### Configuration Steps

1. **Primary**: Set up Direct Connect via `qcloud-dc-ops`
2. **Backup**: Set up VPN Gateway and tunnel
3. **Routing**: Configure route priority

```bash
# Route via Direct Connect (priority 100)
tccli vpc CreateRoutes \
  --RouteTableId "rtb-xxx" \
  --Routes '[{
    "DestinationCidrBlock": "192.168.0.0/16",
    "GatewayType": "DIRECTCONNECT",
    "GatewayId": "dcg-xxx"
  }]'

# Route via VPN (priority 200, backup)
tccli vpc CreateRoutes \
  --RouteTableId "rtb-xxx" \
  --Routes '[{
    "DestinationCidrBlock": "192.168.0.0/16",
    "GatewayType": "VPNGW",
    "GatewayId": "vpngw-xxx"
  }]'
```

### Failover Detection

Monitor both paths and trigger failover when primary is down:

```bash
# Check Direct Connect status (via qcloud-dc-ops)
tccli dc DescribeDirectConnectTunnels \
  --DirectConnectTunnelIds "[\"dcx-xxx\"]" | \
  jq '.Response.DirectConnectTunnelSet[0].State'

# Check VPN status
tccli vpc DescribeVpnConnections \
  --VpnConnectionIds "[\"vpnx-xxx\"]" | \
  jq '.Response.VpnConnectionSet[0].State'
```

## Multi-Branch Topology

For connecting multiple branch offices to a central VPC, see [multi-branch-topology.md](multi-branch-topology.md) for:
- Hub-Spoke architecture
- Active-standby failover
- Bandwidth planning
- IPSec + SSL VPN hybrid

## SSL VPN for Remote Access

SSL VPN is for individual remote users (telecommuters, O&M engineers):

1. Create VPN Gateway with SSL support (`Type=SSL` or `Type=CC`)
2. Create SSL VPN Server
3. Provision SSL VPN Client certs for each user
4. Users connect via SSL VPN client software

### Integration with CAM

Control who can provision SSL VPN clients:

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "vpc:CreateVpnGatewaySslClient",
        "vpc:DescribeVpnGatewaySslClients"
      ],
      "resource": "*"
    }
  ]
}
```

## Security Integration

### Cloud Firewall

For additional security layer, route VPN traffic through Cloud Firewall:

```
On-Prem ──VPN──> VPC ──> Cloud Firewall ──> Application
```

### Security Group

VPN Gateway itself does not have security groups. Apply security groups to backend instances:

```bash
# Allow traffic from on-prem CIDR to application instances
tccli vpc AuthorizeSecurityGroupIngress \
  --SecurityGroupId "sg-xxx" \
  --IpProtocol "tcp" \
  --PortRange "80,443" \
  --CidrIp "192.168.0.0/16"
```

## Monitoring Integration

VPN metrics are available via Cloud Monitor. See [aiops-best-practices.md](aiops-best-practices.md) for:
- Metric queries via CLI/SDK
- Alarm configuration via `qcloud-monitor-ops`
- Anomaly detection patterns

## See also
- [Core Concepts](core-concepts.md)
- [Multi-Branch Topology](multi-branch-topology.md)
- [qcloud-vpc-ops](../../qcloud-vpc-ops/SKILL.md) — VPC and route table management
- [qcloud-ccn-ops](../../qcloud-ccn-ops/SKILL.md) — Multi-region VPC interconnect
- [qcloud-dc-ops](../../qcloud-dc-ops/SKILL.md) — Direct Connect
- [qcloud-monitor-ops](../../qcloud-monitor-ops/SKILL.md) — Monitoring and alarms
