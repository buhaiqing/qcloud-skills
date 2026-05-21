# TencentDB for Redis Troubleshooting Guide

## Error Code Reference

| Code | Meaning | Retry? | Agent Action | UX Feedback |
|------|---------|--------|--------------|-------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter per API spec | `[ERROR] InvalidParameter: Check API spec → Fix → Retry` |
| `InvalidParameterValue` | Parameter value out of range | No | Adjust value per spec | `[ERROR] InvalidParameterValue: Use valid value → Retry` |
| `MissingParameter` | Required parameter missing | No | Add missing parameter | `[ERROR] MissingParameter: Add required param → Retry` |
| `ResourceNotFound` | Instance does not exist | No | Verify InstanceId; list instances | `[ERROR] Instance not found → Run DescribeInstanceList` |
| `ResourceInsufficient` | Instance type/spec unavailable | No | Check DescribeProductInfo | `[ERROR] Spec unavailable → Choose different type` |
| `ResourceInUse` | Instance name already used | No | Use unique name | `[ERROR] Name exists → Choose different name` |
| `InstancePreRunning` | Instance not yet ready | Yes (3x, 30s) | Poll status; retry when running | `⚠️ Instance initializing → Retrying in 30s` |
| `InstancePreIsolate` | Instance not yet isolatable | Yes (3x, 30s) | Wait; retry | `⚠️ Cannot isolate yet → Waiting → Retrying` |
| `OperationConflict` | Concurrent operation | Yes (3x, 30s) | Wait for completion; retry | `⚠️ Operation in progress → Retrying in 30s` |
| `InvalidSecretKey` / `InvalidSecretId` | Credential invalid | No | HALT; fix credentials | `[ERROR] Credential invalid → Check env vars` |
| `RequestLimitExceeded` | API rate limit | Yes (3x) | Exponential backoff | `⚠️ Rate limit → Retry in {backoff}s` |
| `InternalError` | Server-side error | Yes (3x) | Retry; escalate with RequestId | `[ERROR] InternalError → Escalate with RequestId` |
| `QuotaExceeded` | Instance quota exceeded | No | HALT; request increase | `[ERROR] Quota exceeded → Request increase` |
| `VPCNotInZone` | VPC not in selected zone | No | Create VPC in correct zone | `[ERROR] VPC zone mismatch → Fix VPC` |

## Diagnostic Procedures

### Procedure 1: Connectivity Issue

**Symptom**: Cannot connect to Redis instance

**Steps**:
1. Verify instance status: `tccli redis DescribeInstances --InstanceId <id>` → expect Status = 2
2. Verify network: instance ip/port in same VPC as client
3. Check security group rules: allow inbound on Redis port
4. Verify password: test with `redis-cli -h <ip> -p <port> -a <password>`

**Decision Tree**:
- Status != 2 → Wait for initialization or investigate
- Wrong VPC → Instance must be in client's VPC; recreate
- Security group blocks → Modify security group rules
- Password wrong → Verify or modify password

### Procedure 2: Memory Exhaustion

**Symptom**: Redis returns OOM error or evicts keys unexpectedly

**Steps**:
1. Check memory usage via Monitor API or DescribeInstanceMonitor
2. Verify maxmemory-policy (allkeys-lru, volatile-lru, noeviction)
3. Run big key analysis: `tccli redis DescribeInstanceMonitorBigKey`
4. If memory > 80% → recommend UpgradeInstance

### Procedure 3: Slow Query / High Latency

**Symptom**: Redis operations taking longer than expected

**Steps**:
1. Check CPU/Memory metrics via Monitor
2. Identify slow commands: `slowlog get` via redis-cli
3. Check for big keys or blocking operations (KEYS, SMEMBERS on large sets)
4. Verify network bandwidth is not saturated

### Procedure 4: Instance Upgrade Failure

**Symptom**: UpgradeInstance returns error or instance stuck

**Steps**:
1. Verify instance is in running state (Status = 2)
2. Check trade/deal detail: `tccli redis DescribeInstanceDealDetail`
3. Verify target memory/spec is available via DescribeProductInfo
4. If upgrade is mid-flight → poll until complete (max 1200s)

## Common Scenarios

### Scenario: Prepaid Instance Expired

**Problem**: Instance auto-expired due to non-renewal

**Resolution**:
1. Check instance status — should be isolated (Status 4)
2. If within grace period (7 days): `tccli redis ManualRenewInstance --InstanceId <id> --Period 1`
3. If past grace period: data may be lost; check backup via DescribeInstanceBackupRecords

### Scenario: Need to Change VPC

**Problem**: Redis instance must move to different VPC

**Resolution**:
1. TencentDB Redis does not support direct VPC migration
2. Create new instance in target VPC
3. Export data via redis-cli RDB migration
4. Import to new instance
5. Update application connection strings
6. Isolate old instance

### Scenario: High Connection Count

**Problem**: Too many connections causing Redis issues

**Resolution**:
1. Check current connections via DescribeInstanceMonitor
2. Identify connection sources (client IPs)
3. Implement connection pooling in application
4. If hitting connection limit → upgrade to larger instance type with higher max connections