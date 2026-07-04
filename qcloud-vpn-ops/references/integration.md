# VPN Integration

> VPN integration patterns with other Tencent Cloud services.

## VPC Integration

VPN Gateway must be attached to a VPC:
1. Create VPC and subnet via `qcloud-vpc-ops`
2. Create VPN Gateway: `tccli vpc CreateVpnGateway --VpcId vpc-xxx`
3. Create Customer Gateway for on-prem peer
4. Create VPN Connection (tunnel)
5. Configure VPC route table with `NextType=VPNGW`

## On-Premises Integration

- VPN connects on-premises network to Tencent Cloud VPC
- Customer Gateway IP must be a public IP address
- Both ends must have matching IKE and IPSec policies

## See also
- [Core Concepts](core-concepts.md)
- [Multi-Branch Topology](multi-branch-topology.md)
