# CCN Core Concepts

## What is CCN

CCN (Cloud Connect Network, 云联网) is Tencent Cloud's **private network backbone** for connecting VPCs, Direct Connect gateways, and VPN gateways across **regions and accounts**. It replaces a full mesh of VPC peerings with a single hub-and-spoke model.

```
                 ┌──────────────────┐
                 │   CCN instance   │
                 │ (global, has a   │
                 │  default route   │
                 │  table)          │
                 └────────┬─────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ VPC-A   │       │ VPC-B   │       │ DC-GW   │
   │ (广州)  │       │ (上海)  │       │ (account│
   │         │       │         │       │   B)    │
   └─────────┘       └─────────┘       └─────────┘
```

## Why use CCN vs VPC Peering

| Criterion | VPC Peering | CCN |
|---|---|---|
| Same-region same-account | ✅ preferred (cheaper, lower latency) | ⚠️ over-engineered |
| Cross-region | ❌ not supported | ✅ primary use case |
| Cross-account | ⚠️ requires manual accept, no transitive routing | ✅ native support, transitive |
| Number of VPCs | N² peerings for full mesh | N attachments to one CCN |
| Pricing | Free (intra-region) / inter-region bandwidth priced per peering | Inter-region bandwidth priced per region pair; instance has hourly fee |

**Rule of thumb:**
- 1–2 VPCs, same region, same account → use VPC Peering (`qcloud-vpc-ops`)
- 3+ VPCs, or any cross-region / cross-account scenario → use CCN

## Key Concepts

| Concept | Description |
|---|---|
| **CCN instance** | The hub; one per organization typically. Global, has a default route table. |
| **Attachment** | A VPC / DC gateway / VPN gateway associated with a CCN. Each attachment can be in a different region and account. |
| **CCN route table** | Every CCN has one. Holds auto-learned routes (from attached VPCs) and static routes. |
| **Static route** | Manually added route in the CCN route table. Overrides auto-learned path for a specific destination. |
| **Inter-region bandwidth limit** | Cap on bandwidth between two regions, in Mbps. Default is 1 Gbps but the **cost** is the actual used bandwidth, not the cap. |
| **Route learning** | When a VPC is attached, the CCN automatically learns that VPC's CIDR. Other attached VPCs reach it through the CCN. |

## Cross-Account Attachments

A CCN instance can have attachments from VPCs in **other accounts** under the same organization. The flow:

1. Initiator (CCN owner) calls `AttachCcnInstances` with `InstanceAccountId = <peer uin>`.
2. The peer account **accepts** the attachment (or rejects / lets it expire).
3. After acceptance, both sides' VPCs reach each other through the CCN.

For CAM-side requirements, delegate to `qcloud-cam-ops` if the user asks about the role policy itself.

## Pricing Snapshot

| Cost item | Notes |
|---|---|
| CCN instance hourly fee | Charged per CCN, per hour |
| Inter-region bandwidth | Per Mbps, per region pair, monthly |
| Intra-region bandwidth | Free within a region |

> **Always use the API for the latest pricing** — do not hardcode unit prices. The CLI query for current rates is on the billing console / `qcloud-finops-ops`.

## Quotas

| Resource | Adjustable |
|---|---|
| CCNs per region | Yes |
| Attachments per CCN | Yes |
| Static routes per CCN route table | Yes |
| Inter-region bandwidth limits per CCN | Yes |

```bash
tccli vpc DescribeCCNs --Region ap-guangzhou | jq '.Response.TotalCount'
```

## References

- [CCN Documentation](https://cloud.tencent.com/document/product/215/30394)
- [CCN Limits](https://cloud.tencent.com/document/product/215/30394)
