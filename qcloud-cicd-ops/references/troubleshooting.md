# CI/CD Troubleshooting

## Build Failure Diagnosis

1. **Check build logs**: Query logs via API or console
2. **Verify code repository access**: Ensure credentials are valid
3. **Check build environment**: Resource limits, dependency versions
4. **Validate deployment target availability**: Ensure target service is healthy

## Common Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Build hangs | Resource limit reached | Check concurrent build limit |
| Deploy fails | Target service unavailable | Check target health status |
| Source fetch fails | Credential expired | Rotate code repo token |
| Permission denied | CAM policy insufficient | Grant required permissions |
| API rate limit | Too many requests | Implement exponential backoff |

## Error Code Quick Reference

| Error Code | Meaning | Action |
|------------|---------|--------|
| `InvalidParameter` | Parameter validation failed | Check request parameters |
| `ResourceNotFound` | Resource doesn't exist | Verify resource ID |
| `ResourceQuotaExceeded` | Quota limit reached | Request quota increase |
| `OperationDenied` | Operation not allowed | Check permissions |
| `InternalError` | Service internal error | Retry with backoff |

## Debug Steps

1. **Enable verbose logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Verify credentials**:
   ```bash
   test -n "$TENCENTCLOUD_SECRET_ID" && echo "✅ Secret ID is set"
   test -n "$TENCENTCLOUD_SECRET_KEY" && echo "✅ Secret Key is set"
   ```

3. **Test network connectivity**:
   ```bash
   curl -I https://cloud.tencent.com
   ```

4. **Check SDK version**:
   ```bash
   pip show tencentcloud-sdk-python
   ```
