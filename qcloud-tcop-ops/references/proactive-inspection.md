# TCOP Proactive Inspection

> **delegate-from: qcloud-proactive-inspection**
>
> When invoked by the proactive inspection orchestrator, TCOP provides
> optimization health data for the Discovery and Detection phases.

## Delegation Contract

| Property | Value |
|----------|-------|
| Mode | read-only |
| Execution path | SDK only (sdk-only product) |
| Output format | Structured JSON per product convention |

## Discovery Phase

TCOP contributes the following data points:

| Data Point | API | Purpose |
|------------|-----|---------|
| Cost analysis snapshot | `DescribeCostAnalysis` | Current spend by product |
| Waste detection | `DescribeWasteAnalysis` | Waste categories and amounts |
| Right-sizing candidates | `DescribeRightSizingRecommendations` | Instances needing spec adjustment |
| Idle resources | `DescribeIdleResources` | Unused / near-zero utilization resources |
| Savings plan coverage | `DescribeSavingsPlanCoverage` | Gap analysis |

## Detection Phase

TCOP flags:

- **Cost anomaly**: Unusual spending pattern compared to baseline (MoM > 20%)
- **Waste threshold**: Monthly waste > 10% of total spend
- **Coverage gap**: Savings plan coverage < 60%
- **Idle ratio**: Idle resources > 5% of active resource count
- **Right-sizing opportunity**: > 10 instances with utilization below 20%

## Execution

```python
import os
import json
from tencentcloud.common import credential
from tencentcloud.tcop import tcop_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = tcop_client.TcopClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
```