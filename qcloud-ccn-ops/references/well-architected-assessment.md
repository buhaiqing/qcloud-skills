# CCN Well-Architected Assessment

Read-only assessment for the CCN worker when invoked by `qcloud-well-architected-review`. Return shape matches [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md) with `product: ccn`.

## Pillar Coverage

| Pillar | What to inspect for CCN |
|---|---|
| **可靠性 (Reliability)** | Multi-region attachments present; no single-region dependency; CCN not in `ISOLATED` state; inter-region bandwidth limits reasonable for the workloads |
| **安全性 (Security)** | Cross-account attachments come from accounts under the same organization; no orphan attachments; static routes that bypass intended paths are flagged |
| **成本 (Cost)** | Inter-region bandwidth limits set explicitly (not default); no CCN with zero attachments; large bandwidth caps matched to actual usage (via `qcloud-finops-ops`) |
| **效率 (Efficiency)** | No N² peering sprawl (CCN should be the chosen backbone when 3+ VPCs are involved); route table static routes ≤ 10% of total entries |

## Worker Output Contract (excerpt)

The worker MUST return `{{output.product_assessment}}` with `product: ccn`, `scope: single-resource | account-wide`, plus the canonical four-pillar `findings[]` and `summary`.

## Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-ccn-ops",
  "product": "ccn",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-07-03T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 1,
  "pillars": {
    "reliability": {
      "score": 80,
      "status": "assessed",
      "findings": [
        {
          "id": "ccn-rel-001",
          "severity": "Medium",
          "confidence": "HIGH",
          "title": "CCN backbone is single-region",
          "evidence": "All attachments in ap-guangzhou; no ap-shanghai / ap-beijing attachments",
          "recommendation": "Add a multi-region attachment or document the SPOF acceptance in the runbook",
          "effort": "medium"
        }
      ]
    },
    "security": {
      "score": 90,
      "status": "assessed",
      "findings": []
    },
    "cost": {
      "score": 70,
      "status": "assessed",
      "findings": [
        {
          "id": "ccn-cost-001",
          "severity": "Low",
          "confidence": "MEDIUM",
          "title": "Inter-region bandwidth limits not set explicitly",
          "evidence": "All attachments use default 1 Gbps cap; no `CcnBandwidthLimitSet` entries on the CCN",
          "recommendation": "Set explicit `CcnBandwidthLimitSet` per region pair to match workload needs",
          "effort": "quick"
        }
      ]
    },
    "efficiency": {
      "score": 85,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": 2,
      "pillar": "reliability",
      "action": "Add a second-region attachment to the CCN",
      "effort": "medium"
    },
    {
      "priority": 3,
      "pillar": "cost",
      "action": "Set explicit `CcnBandwidthLimitSet` for ap-guangzhou ↔ ap-shanghai",
      "effort": "quick"
    }
  ],
  "trace": {
    "commands": [
      "tccli vpc DescribeCCNs --Region ap-guangzhou",
      "tccli vpc DescribeCcnAttachedInstances --Region ap-guangzhou --Filters Name=ccn-id,Values=ccn-xxx",
      "tccli vpc DescribeCcnRegionBandwidthLimits --Region ap-guangzhou --CcnId ccn-xxx",
      "tccli vpc DescribeCcnRoutes --Region ap-guangzhou --CcnId ccn-xxx"
    ]
  },
  "errors": []
}
```
