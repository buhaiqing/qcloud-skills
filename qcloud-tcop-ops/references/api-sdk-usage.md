# TCOP API & SDK Usage

## Overview

TCOP (Tencent Cloud Optimization Platform) is accessed via the Tencent Cloud API.
Since `tccli` does not support TCOP, all operations use `tencentcloud-sdk-python`.

## API Endpoint

- **Service**: `tcop` 
- **Endpoint**: `tcop.tencentcloudapi.com` (expected, subject to change)
- **API Version**: <!-- TBD: verify against official documentation when published -->

## SDK Installation

```bash
# Standard SDK
pip install tencentcloud-sdk-python

# Product-specific SDK (if available)
pip install tencentcloud-sdk-python-tcop
```

## Authentication

All TCOP APIs use standard Tencent Cloud API authentication:

```python
from tencentcloud.common import credential

cred = credential.Credential(
    "{{env.TENCENTCLOUD_SECRET_ID}}",
    "{{env.TENCENTCLOUD_SECRET_KEY}}"
)
```

## Client Initialization

```python
from tencentcloud.tcop import tcop_client, models

client = tcop_client.TcopClient(cred, "{{env.TENCENTCLOUD_REGION}}")
```

## Available Operations

| SDK Method | Description | Risk |
|-----------|-------------|------|
| `DescribeCostAnalysis` | Analyze spending by product/project/region | None |
| `DescribeRightSizingRecommendations` | Get instance right-sizing suggestions | None |
| `DescribeIdleResources` | Detect idle/unused resources | None |
| `DescribeSavingsPlanCoverage` | Analyze savings plan / RI coverage | None |
| `DescribeWasteAnalysis` | Identify waste items with cost impact | None |
| `DescribeArchitectureAssessment` | Run Well-Architected framework assessment | None |
| `GenerateOptimizationReport` | Generate consolidated optimization report | Low |

## Request/Response Patterns

### Common Request Pattern

```python
req = models.DescribeCostAnalysisRequest()
req.Period = "last-30d"
req.ProductFilter = "all"

resp = client.DescribeCostAnalysis(req)
```

### Common Response Pattern

```python
{
    "RequestId": "req-abc123",
    # operation-specific fields
}
```

## Rate Limits

Standard Tencent Cloud API rate limits apply:
- Read operations: ~20 QPS per account
- Report generation: ~1 QPS per account

Use exponential backoff for `RequestLimitExceeded` errors.

## See Also

- [SDK Code Examples](sdk-code-examples.md) — Runnable Python scripts
- [Troubleshooting Guide](troubleshooting.md) — Error remediation
- [Tencent Cloud API Documentation](https://cloud.tencent.com/document/api) (search for TCOP)