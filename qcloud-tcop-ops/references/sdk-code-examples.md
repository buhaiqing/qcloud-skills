# TCOP SDK Usage Examples

## Prerequisites

```python
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tcop import tcop_client, models  # adjust module name as needed per API version
```

> **Note:** TCOP API module (`tencentcloud.tcop`) may require installing a product-specific
> SDK package or using a specific API version. Adjust imports based on actual SDK availability.

## Common Pattern

All TCOP operations follow this pattern:

```python
def call_tcop_api(action_name, request_obj):
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = tcop_client.TcopClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
        
        # Call the specific action
        method = getattr(client, action_name)
        resp = method(request_obj)
        print(json.dumps(resp.to_json_string(), indent=2))
        return resp
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
        return None
```

## 1. Cost Analysis

```python
def describe_cost_analysis():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = tcop_client.TcopClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    
    req = models.DescribeCostAnalysisRequest()
    req.Period = "last-30d"  # or "last-90d", or ISO range "2026-06-01|2026-06-30"
    req.ProductFilter = "all"  # or "cvm", "cdb", etc.
    req.GroupBy = "product"    # product / project / region / day
    
    resp = client.DescribeCostAnalysis(req)
    return json.loads(resp.to_json_string())
```

## 2. Right-Sizing Recommendations

```python
def describe_rightsizing():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = tcop_client.TcopClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    
    req = models.DescribeRightSizingRecommendationsRequest()
    req.Period = "last-30d"
    req.ProductFilter = "cvm"  # filter to CVM instances
    req.MinConfidence = "medium"  # high / medium / low
    
    resp = client.DescribeRightSizingRecommendations(req)
    return json.loads(resp.to_json_string())
```

## 3. Idle Resource Detection

```python
def describe_idle_resources():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = tcop_client.TcopClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    
    req = models.DescribeIdleResourcesRequest()
    req.Period = "last-30d"
    req.ResourceType = "all"  # cvm / cdb / clb / cbs / all
    req.MetricThreshold = "cpu:5,network:1"  # idle threshold per metric
    
    resp = client.DescribeIdleResources(req)
    return json.loads(resp.to_json_string())
```

## 4. Savings Plan Coverage Analysis

```python
def describe_savings_plan_coverage():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = tcop_client.TcopClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    
    req = models.DescribeSavingsPlanCoverageRequest()
    req.Period = "last-30d"
    req.ProductFilter = "all"
    
    resp = client.DescribeSavingsPlanCoverage(req)
    return json.loads(resp.to_json_string())
```

## 5. Waste Analysis

```python
def describe_waste_analysis():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = tcop_client.TcopClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    
    req = models.DescribeWasteAnalysisRequest()
    req.Period = "last-30d"
    
    resp = client.DescribeWasteAnalysis(req)
    return json.loads(resp.to_json_string())
```

## 6. Architecture Assessment

```python
def describe_architecture_assessment():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = tcop_client.TcopClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    
    req = models.DescribeArchitectureAssessmentRequest()
    req.ProductFilter = "all"
    req.Pillars = "reliability,security,cost,efficiency"  # or "all"
    
    resp = client.DescribeArchitectureAssessment(req)
    return json.loads(resp.to_json_string())
```

## 7. Generate Optimization Report

```python
def generate_optimization_report():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = tcop_client.TcopClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    
    req = models.GenerateOptimizationReportRequest()
    req.Period = "last-30d"
    req.ReportType = "summary"  # summary / detail / json
    req.IncludeArchitecture = True
    
    resp = client.GenerateOptimizationReport(req)
    return json.loads(resp.to_json_string())
```

## Error Handling Pattern

```python
import time
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

def safe_tcop_call(func, *args, **kwargs):
    for attempt in range(3):
        try:
            return func(*args, **kwargs)
        except TencentCloudSDKException as err:
            code = err.get_code()
            if code == "RequestLimitExceeded":
                wait = 2 ** attempt
                print(f"Rate limited. Retrying in {wait}s (attempt {attempt + 1}/3)")
                time.sleep(wait)
                continue
            elif code in ("InvalidParameter", "InvalidParameterValue", "MissingParameter"):
                print(f"[ERROR] {code}: Fix parameters and retry.")
                return None
            elif code in ("InvalidSecretKey", "InvalidSecretId"):
                print("[ERROR] Credential issue. Check TENCENTCLOUD_SECRET_ID / SECRET_KEY.")
                return None
            else:
                print(f"[ERROR] {code}: {err.get_message()}")
                return None
    print("[ERROR] Max retries exceeded.")
    return None
```

## Verification Script

```python
#!/usr/bin/env python3
"""Verify TCOP SDK availability and basic connectivity."""
import os
import sys

required_modules = ["tencentcloud.common", "tencentcloud.tcop"]
for mod in required_modules:
    try:
        __import__(mod)
        print(f"✓ {mod}")
    except ImportError:
        print(f"✗ {mod} — install tencentcloud-sdk-python")
        sys.exit(1)

for var in ["TENCENTCLOUD_SECRET_ID", "TENCENTCLOUD_SECRET_KEY"]:
    if not os.environ.get(var):
        print(f"✗ {var} not set")
        sys.exit(1)
    else:
        print(f"✓ {var} is set")

print("All checks passed.")
```