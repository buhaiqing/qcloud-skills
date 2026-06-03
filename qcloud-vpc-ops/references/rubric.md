# VPC Quality-Gate Rubric (GCL)

> Runtime scoring rubric for **Generator-Critic-Loop (GCL)** of `qcloud-vpc-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the 5-dimension backbone.

---

## 4. VPC-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteVpc` (any) | **VPC ID + Name + CIDR echo; enumerate ALL subnets, route tables, security groups, and dependent resources (CVM instances, CLB, NAT Gateways, VPN Gateway, Peering Connections) via `DescribeVpcResourceDashboard` or equivalent; warn that deletion cascades: all subnets, route tables, and default security groups are removed; require literal "CONFIRM DELETE VPC <vpc_id>" confirmation** | VPC deletion is the most destructive network operation. It cascades: every subnet inside the VPC is also deleted, and every resource (CVM, CLB, NAT) in those subnets loses network connectivity. The most common VPC incident: "I deleted a staging VPC but a production CLB had a cross-VPC peering to it, and the peering broke all traffic" |
| 2 | `DeleteSubnet` (any, especially with running resources) | **Subnet ID + VPC ID + CIDR echo; check if subnet has running resources via `DescribeSubnetResourceDashboard` or `DescribeInstances` with `SubnetId` filter; warn that all CVM instances / CLBs / NAT Gateways in this subnet lose network connectivity; require confirmation with subnet ID** | Subnet deletion does NOT delete the instances (they remain but lose their ENI), but the instances become unreachable. The most common incident: "I deleted the subnet to reorganize IPs but forgot the CVM in it was the production database" |
| 3 | `ReleaseAddresses` (EIP — single or batch) | **EIP ID + IP address echoed; check if EIP is bound to a CVM / CLB / NAT Gateway via `DescribeAddresses`; warn that releasing a bound EIP will terminate the public internet connectivity for the bound resource; require confirmation for each EIP (no batch confirm)** | EIP release gives the IP back to the pool. If the EIP is bound to a CLB, all DNS pointing to that IP breaks. The most common incident: "I released the EIP to save costs but the production CLB was still using it for the SSL certificate domain validation" |
| 4 | `DeleteRouteTable` / `DeleteRoutes` (any, especially default route `0.0.0.0/0`) | **Route table ID + VPC ID + all route entries listed; for default route deletion (`0.0.0.0/0`): warn that all internet-bound traffic drops (no Internet gateway route); for non-default: warn that specific traffic patterns will fall through to the next matching route or drop; require confirmation with route table ID** | Route deletion creates a traffic blackhole. The default route `0.0.0.0/0` delete is the most critical: all internet egress drops. The most common pattern: "I deleted the default route to reconfigure it, but the NAT gateway's traffic went black for 30 seconds" |
| 5 | `DeleteSecurityGroup` (any with rules) | **Security group ID + Name + Inbound/Outbound rule count; warn that all instances bound to this SG will lose those rules; enumerate instances using this SG (via `DescribeSecurityGroupReferences`); for default SG: warn that it is created by VPC and a new one will be auto-created; require confirmation with SG ID** | Security group deletion does not cascade (unlike VPC), but it silently removes traffic rules for all bound instances. The most common incident: "I deleted the 'staging' SG but the production instances were still bound to it because someone shared the SG between environments" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 VPC rollout: rubric (5 rules: VPC cascade delete, subnet resource dependency, EIP bound-release, route blackhole, SG rule loss) |

## 8. See also

- [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill), [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud)
- [`prompt-templates.md`](prompt-templates.md)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations)