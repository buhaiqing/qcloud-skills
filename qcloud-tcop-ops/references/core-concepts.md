# TCOP Core Concepts

## What is TCOP?

Tencent Cloud Optimization Platform (TCOP) is a unified optimization service that helps
Tencent Cloud users reduce costs, improve resource utilization, and align their cloud
architecture with Well-Architected best practices.

## Three Optimization Dimensions

### 1. Cost Optimization
Focuses on reducing cloud spending without sacrificing performance or reliability.

| Capability | Description |
|-----------|-------------|
| Cost Analysis | Breakdown by product, project, region, and time period |
| Anomaly Detection | Identifies unusual cost spikes and patterns |
| Waste Detection | Finds idle, unattached, or underutilized resources |
| Savings Plan / RI Coverage | Analyzes coverage gaps and purchase recommendations |
| Reserved Instance Recommendations | Right-size RI purchases based on historical usage |

### 2. Resource Optimization
Focuses on maximizing resource utilization and efficiency.

| Capability | Description |
|-----------|-------------|
| Right-Sizing | Recommends instance spec adjustments based on utilization |
| Idle Resource Detection | Identifies resources with near-zero utilization |
| Lifecycle Optimization | Suggests release, stop, or schedule-based management |
| Storage Optimization | Analyzes disk/volume utilization and tiering |

### 3. Architecture Optimization
Focuses on architecture quality via the Well-Architected Framework.

| Capability | Description |
|-----------|-------------|
| Reliability Assessment | Identifies single points of failure, backup gaps, SLA risks |
| Security Posture Review | Checks compliance with security best practices |
| Cost Efficiency Analysis | Evaluates architecture cost-effectiveness |
| Operational Efficiency | Reviews automation, monitoring, and operations practices |

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Analysis Period** | Time range for optimization analysis (e.g., last-30d, last-90d) |
| **Potential Savings** | Estimated monthly cost reduction if all recommendations are applied |
| **Confidence Level** | How confident the recommendation is based on utilization data (high/medium/low) |
| **Waste Score** | A score (0-100) indicating how much cost waste exists in the account |
| **Optimization Score** | A score (0-100) reflecting overall optimization maturity |

## Product Relationships

| Related Product | Relationship |
|----------------|-------------|
| FinOps | TCOP provides the optimization analysis; FinOps handles billing data and budgets |
| Cloud Monitor | TCOP uses monitoring data for utilization analysis |
| Well-Architected Review | TCOP's architecture assessment feeds into the full review |
| Product Skills (CVM/CDB/CLB etc.) | TCOP recommendations are executed through product-specific skills |

## Best Practices

1. Run cost analysis at least monthly to catch anomalies early
2. Review right-sizing recommendations with 30+ days of utilization data
3. Always validate idle resource detection before taking action
4. Use architecture assessment at least quarterly for production workloads
5. Track recommendation closure rate to measure optimization effectiveness