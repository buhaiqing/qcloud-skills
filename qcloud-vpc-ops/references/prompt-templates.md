# VPC GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-vpc-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full backbone.

---

## 1. Generator — VPC delta

```text
You are the Generator for the qcloud-vpc-ops skill (Tencent Cloud VPC).
- PRIMARY: tccli vpc <subcommand> ...  (verify with `tccli vpc help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-vpc; namespace:
  from tencentcloud.vpc.v20170312 import vpc_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteVpc` | rule 1: VPC ID + Name + CIDR echo; enumerate subnets/route tables/SGs/resources; warn cascade; literal confirm |
| `DeleteSubnet` | rule 2: Subnet ID + VPC + CIDR echo; check running resources; warn connectivity loss; confirm with ID |
| `ReleaseAddresses` (EIP) | rule 3: EIP ID + IP echo; check bound resource; warn public connectivity loss; confirm per EIP |
| `DeleteRouteTable` / `DeleteRoutes` | rule 4: Route table ID + VPC echo; list entries; warn default route `0.0.0.0/0` internet drop; confirm |
| `DeleteSecurityGroup` | rule 5: SG ID + Name + rule count echo; enumerate bound instances; warn rule loss; confirm |

---

## 5. VPC-specific anti-patterns

- ❌ **DeleteVpc without resource enumeration** — cascading deletion surprises
- ❌ **ReleaseAddresses bound EIP** — breaks DNS/SSL for bound CLB
- ❌ **DeleteRouteTable without listing routes** — default route drop = internet outage
- ❌ **DeleteSecurityGroup shared between environments** — affects more than intended

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 VPC rollout: templates (5 rules, VPC cascade, EIP bound-release, route blackhole, SG rule loss) |