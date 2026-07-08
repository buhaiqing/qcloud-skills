# TCOP Troubleshooting Guide

## Error Codes and Remediation

| Error Code | Common Causes | Diagnosis | Resolution |
|------------|--------------|-----------|------------|
| `InvalidParameter` | Wrong period format, invalid product filter | Check period syntax (`last-Nd` or ISO range) | Fix parameter and retry |
| `InvalidParameterValue` | Period too short (< 7 days) or too long (> 365 days) | Validate analysis range | Adjust to 7-365 days |
| `MissingParameter` | Required field not set (e.g., Period) | Check request object fields | Add missing field |
| `ResourceNotFound` | Product filter matches no resources | Verify account has resources of that type | Change product filter |
| `InvalidSecretKey` | Wrong or expired API secret | `test -n "$TENCENTCLOUD_SECRET_KEY"` | Regenerate in CAM console |
| `InvalidSecretId` | Wrong or deleted API key ID | `test -n "$TENCENTCLOUD_SECRET_ID"` | Check CAM for active keys |
| `RequestLimitExceeded` | Too many API calls per second | Check call frequency | Implement exponential backoff |
| `InternalError` | Tencent Cloud server-side issue | Retry; capture RequestId | Retry 2s/4s/8s; escalate if persistent |
| `UnsupportedOperation` | Feature not available in this region | Check product availability | Switch to ap-guangzhou |
| `OperationDenied` | TCOP not enabled for account | Check console activation | Enable TCOP in console |

## Common Issues

### "No data returned for this period"

| Possible Cause | How to Check | Fix |
|---------------|-------------|-----|
| Account has no activity in period | `DescribeCostAnalysis` with expanded range | Extend period to 90 days |
| New account with limited history | Check account creation date | Use max available period |
| Wrong region filter | Verify region setting | Set to `ap-guangzhou` or account's main region |

### "Right-sizing recommendations empty"

| Possible Cause | How to Check | Fix |
|---------------|-------------|-----|
| All instances already optimized | Check utilization data | No action needed |
| Insufficient monitoring data | Verify CloudMonitor agent is installed | Install agent on target CVM |
| Filter too restrictive | Check product filter and confidence level | Widen filter or lower confidence |

### "Savings plan coverage analysis shows no data"

| Possible Cause | How to Check | Fix |
|---------------|-------------|-----|
| No existing savings plans | `DescribeSavingsPlanCoverage` with expanded period | Analysis is valid — shows 0% coverage |
| Wrong product filter | Check if product has savings plans | Verify eligible product list |
| Account ineligible | Check account tier | Some savings plans require specific commitment levels |

## Connectivity Checks

```bash
# 1. Verify SDK is installed
python3 -c "import tencentcloud.tcop; print('SDK ready')" 2>&1 || echo "Need: pip install tencentcloud-sdk-python"

# 2. Verify credentials (safe check - no value echo)
test -n "$TENCENTCLOUD_SECRET_ID" && echo "SecretId: set" || echo "SecretId: MISSING"
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "SecretKey: set" || echo "SecretKey: MISSING"

# 3. Verify region
echo "Region: ${TENCENTCLOUD_REGION:-ap-guangzhou}"
```

## Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| TCOP may not support all regions | Analysis limited to supported regions | Check product documentation for regional availability |
| Minimum analysis period: 7 days | Cannot analyze very short windows | Use 7+ day periods |
| Recommendation delays | Right-sizing data may be 24-48h delayed | Allow settling time after resource changes |
| API may be in beta | Endpoints and shapes may change | Verify against latest API doc before critical use |