# SCF Troubleshooting Guide

## Error Code Reference

| Code | Meaning | Retry? | Agent Action | UX Feedback |
|------|---------|--------|--------------|-------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter against API spec | `[ERROR] InvalidParameter: Check API spec → Fix → Retry` |
| `InvalidParameterValue` | Parameter value out of valid range | No | Adjust value per API spec | `[ERROR] InvalidParameterValue: Use valid value → Check spec → Retry` |
| `MissingParameter` | Required parameter not provided | No | Add missing parameter | `[ERROR] MissingParameter: Add required parameter → Retry` |
| `ResourceNotFound` | Target resource does not exist | No | Verify resource ID; suggest List | `[ERROR] ResourceNotFound: Verify ID with List API → Retry` |
| `ResourceNotFound.Function` | Function not found | No | List functions to find correct name | `[ERROR] Function not found → Run ListFunctions → Verify name` |
| `ResourceNotFound.Trigger` | Trigger not found | No | Verify trigger name | `[ERROR] Trigger not found → Run ListTriggers → Verify` |
| `ResourceNotFound.Version` | Function version not found | No | List versions to find correct version | `[ERROR] Version not found → Run ListVersions → Verify` |
| `ResourceInUse` | Name already in use | No | Use unique name | `[ERROR] Name in use → Choose different name → Retry` |
| `ResourceLimitExceeded` | Quota exceeded | No | HALT; request quota increase | `[ERROR] Quota exceeded → Contact support` |
| `ResourceUnavailable` | Resource temporarily unavailable | Yes (3x) | Wait; poll status; retry | `⚠️ Resource unavailable → Retrying...` |
| `FailedOperation` | General operation failure | No | Check function state | `[ERROR] Operation failed → Check state → Retry` |
| `FailedOperation.FunctionStatusError` | Function not in correct state | Yes (3x) | Wait for Active state | `⚠️ Function not Active → Waiting → Retrying` |
| `FailedOperation.InvokeFunctionFailed` | Function invocation failed | Yes (3x) | Check code; retry invoke | `⚠️ Invoke failed → Retrying...` |
| `FailedOperation.ProvisionedConcurrencyConfigError` | Provisioned concurrency config error | No | Check configuration | `[ERROR] Concurrency config error → Verify settings` |
| `OperationConflict` | Concurrent operation conflict | Yes (3x) | Wait; retry after completion | `⚠️ Operation in progress → Waiting → Retrying` |
| `InvalidSecretKey` / `InvalidSecretId` | Credential invalid | No | HALT; fix environment variables | `[ERROR] Credential invalid → Verify TENCENTCLOUD_SECRET_ID/KEY` |
| `RequestLimitExceeded` | API rate limit exceeded | Yes (3x) | Exponential backoff | `⚠️ Rate limit → Retry in {backoff}s` |
| `InternalError` | Server-side internal error | Yes (3x) | Retry; escalate with RequestId | `[ERROR] InternalError → Retry → Escalate with RequestId` |
| `InvalidCode` | Deployment package invalid | No | Fix zip format | `[ERROR] Invalid package → Check zip format and handler` |
| `CodeExceeded` | Package size exceeds limit | No | Reduce package size | `[ERROR] Package too large → Reduce to <500MB` |
| `HandlerNotFound` | Handler function not found | No | Verify handler name | `[ERROR] Handler not found → Check handler format` |

## Diagnostic Procedures

### Procedure 1: Function Creation Failure

**Symptom:** CreateFunction returns error

**Steps:**
1. Validate function name: Check format (letters, numbers, underscores, hyphens only)
2. Verify zip file exists: `test -f {{user.zip_file_path}}`
3. Check zip file size: `stat -f%z {{user.zip_file_path}}` must be < 500MB
4. Validate handler format per runtime (Python: `file.function`, Node.js: `file.function`)
5. Check namespace exists or use `default`
6. Verify memory size is valid (128-30080, multiple of 64)
7. Verify timeout is valid (1-900 seconds)

**Most Likely Causes:**
1. Invalid function name format
2. Zip file doesn't exist or is corrupted
3. Package size exceeds 500MB limit
4. Handler format doesn't match runtime
5. Memory/timeout values out of valid range

### Procedure 2: Function Invocation Failure

**Symptom:** Invoke or InvokeAsync returns error or function throws exception

**Steps:**
1. Check function status: Must be `Active` (not `Updating`, `Creating`, etc.)
2. Get function logs: `tccli scf GetFunctionLogs --FunctionName {{user.function_name}} --Limit 50`
3. Check for syntax errors in logs
4. Verify environment variables are set correctly
5. Check if function has required IAM permissions
6. Verify VPC configuration (if using VPC)

**Decision Tree:**
- `RetCode = 0` → Success
- `RetCode = 1` → Function exception (check logs for stack trace)
- `RetCode = -1` → Invocation error (network, timeout)

**Most Likely Causes:**
1. Code syntax error
2. Missing environment variables
3. IAM permission denied
4. VPC networking issue
5. Timeout (execution exceeded timeout setting)
6. Out of memory

### Procedure 3: Cold Start Performance Issues

**Symptom:** Function latency is high (>1s) on first invocation

**Steps:**
1. Check function package size: Smaller is better for cold start
2. Review initialization code: Move heavy operations outside handler
3. Check if using VPC: VPC functions have slower cold starts
4. Verify provisioned concurrency settings
5. Check layer usage: Layers reduce package size

**Optimization Recommendations:**
1. Reduce deployment package size
2. Move global initialization outside handler function
3. Use provisioned concurrency for latency-sensitive apps
4. Use layers for common dependencies
5. Avoid VPC unless necessary
6. Use keep-alive for internal connections

### Procedure 4: Trigger Configuration Failure

**Symptom:** CreateTrigger returns error or trigger doesn't invoke function

**Steps:**
1. Verify function exists and is `Active`
2. Check trigger type is supported for the function configuration
3. Validate trigger configuration JSON format
4. For COS triggers: Verify bucket exists and has correct permissions
5. For timer triggers: Validate cron expression format
6. For API Gateway triggers: Verify API Gateway configuration
7. Check trigger status: Must be `Enabled`

**Most Likely Causes:**
1. Function not in Active state
2. Invalid trigger configuration JSON
3. Missing permissions on source resource (COS bucket, etc.)
4. Cron expression format error
5. API Gateway misconfiguration

### Procedure 5: Concurrency and Throttling Issues

**Symptom:** Functions being throttled (429 errors) or not scaling

**Steps:**
1. Check current concurrency usage via Cloud Monitor
2. Verify account concurrency limit (default: 128,000)
3. Check function reserved concurrency settings
4. Review provisioned concurrency allocation
5. Check for burst limit (1,000-3,000 per region)
6. Analyze invocation patterns (spikes vs steady)

**Solutions:**
1. Request account concurrency increase
2. Configure reserved concurrency for critical functions
3. Use provisioned concurrency for predictable traffic
4. Implement async processing for burst traffic
5. Use SQS/CMQ to buffer requests

## Multi-Round Diagnosis

### Round 1: Initial Assessment

```yaml
round_1:
  checks:
    - function_exists
    - function_status_active
    - credentials_valid
    - quota_available
  actions:
    - get_function
    - test_invoke
    - check_quotas
  decision:
    - if all pass: proceed to Round 2
    - if any fail: fix issue and retry Round 1
```

### Round 2: Configuration Analysis

```yaml
round_2:
  checks:
    - handler_format_correct
    - runtime_supported
    - memory_size_valid
    - timeout_valid
    - code_package_valid
  actions:
    - validate_handler
    - check_package_size
    - verify_runtime
  decision:
    - if all pass: proceed to Round 3
    - if any fail: fix configuration and retry
```

### Round 3: Runtime Diagnostics

```yaml
round_3:
  checks:
    - function_logs_errors
    - environment_variables_set
    - iam_permissions_ok
    - vpc_connectivity
  actions:
    - get_function_logs
    - check_iam_policies
    - verify_vpc_config
  output:
    - root_cause_hypothesis
    - evidence_chain
    - resolution_recommendation
```

## Common Scenarios

### Scenario: Function Returns "Internal Server Error"

**Problem:** HTTP 500 error when invoking via API Gateway

**Resolution:**
1. Check function logs for exception details
2. Verify function returns proper response format:
   ```python
   return {
       "statusCode": 200,
       "headers": {"Content-Type": "application/json"},
       "body": json.dumps({"message": "success"})
   }
   ```
3. Ensure no unhandled exceptions in code
4. Check timeout isn't exceeded

### Scenario: Function Times Out

**Problem:** Function execution exceeds timeout setting

**Resolution:**
1. Increase timeout: `tccli scf UpdateFunctionConfiguration --Timeout 300`
2. Optimize code to reduce execution time
3. Use async processing for long operations
4. Implement pagination for large data processing
5. Consider using SCF async invocation pattern

### Scenario: Environment Variables Not Available

**Problem:** Function can't access environment variables

**Resolution:**
1. Verify variables are set: `tccli scf GetFunction --FunctionName {{user.function_name}}`
2. Check variable names (case-sensitive)
3. Ensure variables are set in correct namespace
4. For sensitive data, use Secrets Manager

### Scenario: VPC Function Can't Access Internet

**Problem:** Function in VPC can't reach public endpoints

**Resolution:**
1. Configure NAT Gateway for VPC subnet
2. Use VPC endpoints for Tencent Cloud services
3. Or use public subnet with public IP (not recommended)

### Scenario: Layer Not Working

**Problem:** Function can't access layer content

**Resolution:**
1. Verify layer is compatible with function runtime
2. Check layer path matches runtime expectations:
   - Python: `/opt/python/lib/python3.8/site-packages/`
   - Node.js: `/opt/nodejs/node_modules/`
3. Verify layer version is correct
4. Check layer size doesn't exceed limit

### Scenario: Trigger Not Firing

**Problem:** Event not triggering function

**Resolution:**
1. Verify trigger status is `Enabled`: `tccli scf ListTriggers --FunctionName {{user.function_name}}`
2. Check source resource permissions (COS bucket policy, etc.)
3. For timer triggers: Verify cron expression in CloudWatch
4. For API Gateway: Verify API deployment stage
5. Check if function has sufficient concurrency

## Escalation Criteria

Escalate when:
- `InternalError` persists after 3 retries with different RequestIds
- Function stuck in non-terminal state for > 60s
- Multi-round diagnosis inconclusive
- Platform-level SCF service outage suspected

**Escalation Protocol:**
1. Collect last RequestId from API response
2. Document: function name, region, operation attempted, error codes encountered, diagnosis steps taken
3. Contact Tencent Cloud support with: FunctionName, RequestId, Timestamp, Error messages

## Quick Fixes

### Restart Function (Cold Start)

```bash
# Update with same code to force cold start
tccli scf UpdateFunctionCode \
  --FunctionName {{user.function_name}} \
  --Code.ZipFile {{user.zip_file_path}}
```

### Clear Provisioned Concurrency

```bash
# Remove provisioned concurrency
tccli scf DeleteProvisionedConcurrencyConfig \
  --FunctionName {{user.function_name}} \
  --Qualifier {{user.version}}
```

### Disable All Triggers

```bash
# List and disable all triggers
tccli scf ListTriggers --FunctionName {{user.function_name}} | \
  jq -r '.Response.Triggers[].TriggerName' | \
  while read trigger; do
    tccli scf UpdateTriggerStatus \
      --FunctionName {{user.function_name}} \
      --TriggerName "$trigger" \
      --Enable CLOSE
  done
```

### Get Last Error Log

```bash
# Get most recent error log
tccli scf GetFunctionLogs \
  --FunctionName {{user.function_name}} \
  --Limit 10 \
  --Order DESC | \
  jq -r '.Response.Data[] | select(.RetCode != 0) | .Log' | head -1
```

## Monitoring and Alerting

### Key Metrics to Monitor

| Metric | Warning Threshold | Critical Threshold |
|--------|-------------------|-------------------|
| Error Rate | > 1% | > 5% |
| Throttles | > 10/min | > 100/min |
| Duration (p99) | > timeout × 0.8 | > timeout × 0.95 |
| Iterator Age (stream) | > 1 hour | > 24 hours |
| Concurrent Executions | > 80% limit | > 95% limit |

### Common CloudWatch Alarms

```bash
# Create error rate alarm
tccli monitor CreateAlarmPolicy \
  --PolicyName "SCF-HighErrorRate" \
  --PolicyType 0 \
  --Conditions '[{"MetricName":"Duration","Period":60,"Operator":">","Value":5000}]'
```
