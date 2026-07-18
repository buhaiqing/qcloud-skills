# TCOP Well-Architected Assessment

## Worker Output Contract (delegate-from: qcloud-well-architected-review)

When invoked by the Well-Architected orchestrator (`{{user.mode}} = well-architected-readonly`),
return output matching the schema in
[qcloud-well-architected-review/references/worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md).

### Read-Only Operations Allowed

| Operation | API | Purpose |
|-----------|-----|---------|
| DescribeCostAnalysis | `DescribeCostAnalysis` | Cost pillar: spending analysis by product/project/region |
| DescribeRightSizingRecommendations | `DescribeRightSizingRecommendations` | Efficiency pillar: resource utilization |
| DescribeIdleResources | `DescribeIdleResources` | Cost pillar: waste detection |
| DescribeSavingsPlanCoverage | `DescribeSavingsPlanCoverage` | Cost pillar: coverage analysis |
| DescribeWasteAnalysis | `DescribeWasteAnalysis` | Cost pillar: waste identification |
| DescribeArchitectureAssessment | `DescribeArchitectureAssessment` | All pillars: current assessment state |

### Prohibited Operations

| Operation | Why |
|-----------|-----|
| GenerateOptimizationReport | Mutation (creates report resource) |

### Pillar Mapping

| Pillar | TCOP Data Source | Assessment Criteria |
|--------|-----------------|-------------------|
| **Reliability** | `DescribeArchitectureAssessment` → Reliability score + risk items | Single points of failure, backup gaps, SLA risks |
| **Security** | `DescribeArchitectureAssessment` → Security score + risk items | Compliance, IAM best practices, encryption |
| **Cost** | `DescribeCostAnalysis` + `DescribeWasteAnalysis` + `DescribeSavingsPlanCoverage` + `DescribeRightSizingRecommendations` + `DescribeIdleResources` | Waste level, RI coverage, right-sizing opportunities |
| **Efficiency** | `DescribeRightSizingRecommendations` + `DescribeIdleResources` | Utilization rates, right-sizing needs |

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-tcop-ops",
  "product": "tcop",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-07-10T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 6,
  "pillars": {
    "reliability": {
      "score": 72,
      "status": "assessed",
      "findings": [
        {
          "id": "tcop-rel-001",
          "severity": "High",
          "confidence": "MEDIUM",
          "title": "Primary workload in single AZ",
          "evidence": "DescribeArchitectureAssessment shows no cross-region DR plan",
          "recommendation": "Establish cross-region DR plan for primary workload",
          "effort": "major"
        }
      ]
    },
    "security": {
      "score": 68,
      "status": "assessed",
      "findings": [
        {
          "id": "tcop-sec-001",
          "severity": "High",
          "confidence": "MEDIUM",
          "title": "Storage buckets not encrypted by default",
          "evidence": "DescribeArchitectureAssessment security score 68 with encryption gaps",
          "recommendation": "Enable default encryption on storage buckets",
          "effort": "medium"
        }
      ]
    },
    "cost": {
      "score": 55,
      "status": "assessed",
      "findings": [
        {
          "id": "tcop-cost-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "25% of compute resources idle or underutilized",
          "evidence": "DescribeIdleResources + DescribeRightSizingRecommendations",
          "recommendation": "Reclaim idle resources; right-size underutilized instances",
          "effort": "medium"
        },
        {
          "id": "tcop-cost-002",
          "severity": "Medium",
          "confidence": "HIGH",
          "title": "Savings plan coverage at 30% — below 60% target",
          "evidence": "DescribeSavingsPlanCoverage",
          "recommendation": "Increase savings plan coverage toward 60% target",
          "effort": "medium"
        }
      ]
    },
    "efficiency": {
      "score": 70,
      "status": "assessed",
      "findings": [
        {
          "id": "tcop-eff-001",
          "severity": "Medium",
          "confidence": "HIGH",
          "title": "Average CPU utilization below 20% across 15 instances",
          "evidence": "DescribeRightSizingRecommendations",
          "recommendation": "Right-size instances with low utilization",
          "effort": "medium"
        }
      ]
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "cost",
      "action": "Reclaim idle resources; right-size underutilized instances",
      "effort": "medium"
    },
    {
      "priority": "High",
      "pillar": "security",
      "action": "Enable default encryption on storage buckets",
      "effort": "medium"
    },
    {
      "priority": "Medium",
      "pillar": "efficiency",
      "action": "Right-size instances with low utilization",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli tcop DescribeCostAnalysis (SecretKey=<masked>)",
      "tccli tcop DescribeIdleResources (SecretKey=<masked>)",
      "tccli tcop DescribeArchitectureAssessment (SecretKey=<masked>)"
    ],
    "request_ids": [
      "c3d4e5f6-a7b8-9012-cdef-0123456789ab"
    ]
  },
  "errors": []
}
```