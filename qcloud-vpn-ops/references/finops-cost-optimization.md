# VPN FinOps Cost Optimization

> VPN cost optimization strategies.

## Cost Components

| Component | Billing Mode | Notes |
|-----------|--------------|-------|
| VPN Gateway | Hourly | Based on bandwidth tier |
| VPN Connection | Free | No additional charge |
| Traffic | Pay-as-you-go | Outbound from VPC |

## Optimization Strategies

| Strategy | Description |适用场景 |
|----------|-------------|---------|
| Bandwidth selection | Choose appropriate bandwidth (5/10/20/50/100/200/500/1000 Mbps) | Avoid over-provisioning |
| Connection monitoring | Detect idle VPN connections | Identify waste |
| Prepaid vs hourly | Prepaid for stable 24/7 connections | Save ~30% on stable VPN |
| Multi-region consolidation | Single VPN gateway for multiple VPCs | Reduce gateway count |

## Idle Connection Detection

```bash
tccli vpc DescribeVpnConnections --Output json | jq '.VpnConnectionSet[] | select(.State=="closed")'
```

## See also
- [Core Concepts](core-concepts.md)
- [Integration](integration.md)
