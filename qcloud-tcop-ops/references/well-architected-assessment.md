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

### Sample Output

```json
{
  "product": "tcop",
  "assessments": {
    "reliability": {
      "score": 72,
      "risks": [
        {"id": "REL-001", "description": "Primary workload in single AZ", "severity": "high"},
        {"id": "REL-002", "description": "No cross-region DR plan found", "severity": "medium"}
      ]
    },
    "security": {
      "score": 68,
      "risks": [
        {"id": "SEC-001", "description": "Storage buckets not encrypted by default", "severity": "high"}
      ]
    },
    "cost": {
      "score": 55,
      "risks": [
        {"id": "CST-001", "description": "25% of compute resources idle or underutilized", "severity": "high", "estimated_monthly_waste": "1234.50"},
        {"id": "CST-002", "description": "Savings plan coverage at 30% — below 60% target", "severity": "medium", "estimated_monthly_savings": "800.00"}
      ],
      "waste_summary": {
        "total_monthly_waste": "2034.00",
        "idle_resources_count": 12,
        "right_sizing_candidates_count": 8
      }
    },
    "efficiency": {
      "score": 70,
      "risks": [
        {"id": "EFF-001", "description": "Average CPU utilization below 20% across 15 instances", "severity": "medium"}
      ]
    }
  },
  "overall_score": 66
}
```