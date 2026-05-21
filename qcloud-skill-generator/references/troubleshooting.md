# Troubleshooting Guide Template

Template for product-specific troubleshooting documentation.

---

## Overview

Every generated skill MUST include a troubleshooting guide with:
- Error code table (≥ 10 product-specific codes)
- Ordered diagnostic steps
- Multi-round diagnosis procedures

---

## Template Structure

```markdown
# [Product Name] Troubleshooting Guide

## Error Code Reference

| Code | Meaning | Retry | Agent Action | UX Feedback |
|------|---------|-------|--------------|-------------|
| InvalidParameter | Parameter validation failed | No | Fix parameter value | `[ERROR] InvalidParameter: The parameter is invalid → Check docs → Retry` |
| InvalidParameterValue | Parameter value out of range | No | Adjust value | `[ERROR] InvalidParameterValue: Value out of range → Use valid range → Retry` |
| MissingParameter | Required parameter missing | No | Add parameter | `[ERROR] MissingParameter: Required param missing → Add [param] → Retry` |
| ResourceNotFound | Resource does not exist | No | Verify ID | `[ERROR] ResourceNotFound: Resource not found → Verify ID → Retry with valid ID` |
| ResourceInsufficient | Quota exceeded | No | Request quota increase | `[ERROR] ResourceInsufficient: Quota exceeded → Request increase → Contact support` |
| InvalidSecretKey | Credential invalid | No | Fix credentials | `[ERROR] InvalidSecretKey: Credential invalid → Verify SecretKey → Retry` |
| InvalidSecretId | Credential ID invalid | No | Fix credentials | `[ERROR] InvalidSecretId: Credential ID invalid → Verify SecretId → Retry` |
| RequestLimitExceeded | Rate limit exceeded | Yes (3x) | Backoff and retry | `⚠️ Rate limit reached → Retry in {backoff}s → (Attempt {n}/3)` |
| InternalError | Server error | Yes (3x) | Retry with RequestId | `[ERROR] InternalError: Server error → Retry → Escalate with RequestId if persists` |
| OperationDenied | Permission denied | No | Check CAM policy | `[ERROR] OperationDenied: No permission → Check CAM → Add required permission` |
| [Product-specific] | [Meaning] | [Retry?] | [Action] | [UX feedback] |

---

## Diagnostic Procedures

### Procedure 1: Connectivity Issue Diagnosis

**Symptom**: Cannot connect to resource

**Steps**:
1. Check resource status: `tccli [product] Describe[Resource] --[Id] [ID]`
2. Verify network: Check VPC and Security Groups
3. Check port availability: Verify service is listening
4. Validate credentials: Test API call with DescribeRegions

**Decision Tree**:
- Status != RUNNING → Start/restart resource
- Security Group blocks → Modify Security Group rules
- Port not listening → Check application configuration
- Credentials invalid → Fix environment variables

---

### Procedure 2: Performance Issue Diagnosis

**Symptom**: Slow response or high latency

**Steps**:
1. Check CPU/Memory metrics: Monitor API or console
2. Analyze resource utilization patterns
3. Check for I/O bottlenecks
4. Review recent changes

**Metrics to Check**:
| Metric | Threshold | Action |
|--------|-----------|--------|
| CPUUsage | > 80% | Upsize or optimize |
| MemUsage | > 85% | Upsize or check leak |
| DiskIO | > limit | Optimize I/O |
| NetworkLatency | > baseline | Check network |

---

### Procedure 3: Quota Issue Diagnosis

**Symptom**: Cannot create new resource

**Steps**:
1. Query current quota: `tccli [product] Describe[Quotas]`
2. Count existing resources: `tccli [product] Describe[Resources]`
3. Identify quota limit hit
4. Request quota increase or delete unused

---

### Procedure 4: Credential Issue Diagnosis

**Symptom**: Authentication failed

**Steps**:
1. Verify environment variables exist: `test -n "$TENCENTCLOUD_SECRET_ID"`
2. Test with minimal API: `tccli cvm DescribeZones`
3. Check CAM permissions for product
4. Verify SecretKey not expired

---

## Multi-Round Diagnosis

### Round 1: Initial Assessment

```yaml
round_1:
  checks:
    - resource_exists
    - resource_status_running
    - credentials_valid
    - quota_available
  actions:
    - describe_resource
    - test_api_call
  decision:
    - if all pass: proceed to Round 2
    - if any fail: fix issue and retry Round 1
```

### Round 2: Detailed Analysis

```yaml
round_2:
  checks:
    - metrics_collection
    - log_analysis
    - dependency_verification
  actions:
    - get_monitor_data
    - check_recent_logs
    - verify_dependencies
  decision:
    - if anomaly found: proceed to Round 3
    - if no anomaly: escalate
```

### Round 3: Root Cause Determination

```yaml
round_3:
  checks:
    - metric_correlation
    - event_timeline
    - config_diff
  actions:
    - correlate_metrics
    - build_timeline
    - compare_configs
  output:
    - root_cause_hypothesis
    - evidence_chain
    - resolution_recommendation
```

---

## Common Scenarios

### Scenario 1: Resource Creation Fails

```markdown
**Problem**: RunInstances returns error

**Diagnosis Steps**:
1. Check quota: `tccli cvm DescribeInstancesQuota`
2. Validate InstanceType: `tccli cvm DescribeInstanceTypeConfigs`
3. Verify ImageId: `tccli cvm DescribeImages`
4. Check SecurityGroups exist
5. Verify VPC/Subnet available

**Most Likely Causes**:
1. InstanceType not available in region
2. ImageId invalid or deprecated
3. Quota exceeded
4. SecurityGroup not found
```

### Scenario 2: Resource Status Unknown

```markdown
**Problem**: Resource shows unexpected status

**Diagnosis Steps**:
1. Poll status: Repeat Describe[Resource]
2. Check recent operations: DescribeOperationsLog
3. Review async task status
4. Verify terminal state expected

**Resolution**:
- Wait for terminal state (timeout: 300s)
- If timeout, check task status separately
- If stuck, escalate with RequestId
```

---

## Escalation Criteria

Escalate when:
- InternalError persists after 3 retries
- Unknown status for > 300s
- Multi-round diagnosis inconclusive
- Platform-level issue suspected

**Escalation Protocol**:
1. Collect RequestId from last API call
2. Document symptom and diagnosis attempts
3. Contact Tencent Cloud support
4. Provide: ResourceId, RequestId, Timestamp, Error messages

---

## Integration with Skill

This guide is referenced from SKILL.md:
```markdown
- [Troubleshooting Guide](references/troubleshooting.md) — Fix common issues
```

Error handling in Execution Flows references this table.
```

---

## References

- [Tencent Cloud Error Codes](https://cloud.tencent.com/document/api)
- [AIOps Best Practices](aiops-best-practices.md)
- [Optimization Analysis](optimization-analysis.md)