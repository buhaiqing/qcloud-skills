# CKafka Troubleshooting Guide

CKafka-specific error codes, diagnostic steps, and recovery patterns for Tencent Cloud CKafka (Message Queue).

---

## 1. Error Code Reference (CKafka-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter` | Parameter validation failed | Fix parameter per API spec |
| `InvalidParameterValue` | Parameter value out of range | Adjust value per spec |
| `MissingParameter` | Required parameter missing | Add missing parameter |
| `ResourceNotFound` | Resource not found | Verify instance/topic ID |
| `ResourceNotFound.InstanceNotExist` | Instance not found | Verify InstanceId |
| `ResourceNotFound.TopicNotExist` | Topic not found | Verify TopicName |
| `ResourceNotFound.GroupNotExist` | Consumer group not found | Verify Group name |
| `ResourceInsufficient` | Resource quota insufficient | HALT; raise quota or delete resources |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `InvalidSecretId` | Credential ID invalid | HALT; fix credentials |
| `OperationDenied.InstanceStatusError` | Wrong instance status for op | Check status via DescribeInstances |
| `OperationDenied.InstanceLocked` | Instance locked by operation | Retry (3x, 30s); wait for completion |
| `OperationDenied.NotSupported` | Operation not supported | Check instance type/version |
| `OperationDenied.PayModeError` | Billing mode doesn't support op | Check prepaid vs postpaid |
| `OperationDenied.TopicPartitionLimit` | Topic partition limit exceeded | Delete unused topics or upgrade instance |
| `OperationDenied.GroupNotEmpty` | Consumer group not empty | Remove all consumers first |
| `OperationDenied.AclAlreadyExist` | ACL rule already exists | Use ModifyAclRule instead |
| `FailedOperation` | General operation failure | Check error message for details |
| `FailedOperation.TaskAlreadyExist` | Task already in progress | Retry (3x, 30s); check DescribeTaskStatus |
| `FailedOperation.CreateOrderFailed` | Order creation failed | HALT; check account balance/spec validity |
| `FailedOperation.StatusConflict` | Status conflict | Retry (2x, 10s); wait and retry |
| `FailedOperation.InsufficientBalance` | Insufficient account balance | HALT; add funds |
| `LimitExceeded.InstanceNum` | Instance count limit exceeded | HALT; raise quota or delete instances |
| `LimitExceeded.TopicNum` | Topic count limit exceeded | Delete unused topics |
| `LimitExceeded.PartitionNum` | Partition count limit exceeded | Delete unused partitions/topics |
| `LimitExceeded.ConsumerGroupNum` | Consumer group limit exceeded | Delete unused consumer groups |
| `LimitExceeded.UserNum` | User count limit exceeded | Delete unused users |
| `LimitExceeded.AclRuleNum` | ACL rule count limit exceeded | Delete unused ACL rules |
| `RequestLimitExceeded` | API rate limit exceeded | Retry (3x); exponential backoff (2s, 4s, 8s) |
| `InternalError` | Internal server error | Retry (3x); escalate with RequestId |
| `InternalError.KafkaError` | Kafka internal error | Retry (3x); check broker health |
| `InternalError.DbError` | Database internal error | Retry (3x); escalate with RequestId |
| `InternalError.TaskError` | Task internal error | Retry (3x); check task details |
| `UnauthorizedOperation` | Unauthorized operation | HALT; check CAM permissions |
| `UnsupportedOperation` | Unsupported operation | Check version/region compatibility |
| `AuthFailure` | Authentication failure | Check SASL credentials |
| `AuthFailure.UnauthorizedOperation` | CAM permission denied | Check IAM policies |

---

## 2. Diagnostic Workflow

### Step 1: Check Instance Exists and Status

```bash
tccli ckafka DescribeInstances --InstanceIdList '["ckafka-xxxxxx"]' --Region ap-guangzhou
```

- If `TotalCount: 0` → Instance not found or wrong InstanceId
- If `InstanceList[0].Status: 3` → Instance is isolated

### Step 2: Check Instance State

```bash
STATUS=$(tccli ckafka DescribeInstances --InstanceIdList '["ckafka-xxxxxx"]' --Region ap-guangzhou | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['InstanceList'][0]['Status'])")
echo "Instance state: $STATUS"
# 0=creating, 1=running, 2=isolating, 3=isolated, 4=upgrading, 5=restarting
```

Valid states for operations:
- CreateTopic → Status=1 (running)
- DeleteTopic → Status=1 (running)
- ModifyPartitionNum → Status=1 (running)
- CreateAclRule → Status=1 (running)
- RestartInstance → Status=1 (running)

### Step 3: Check Topic Existence

```bash
tccli ckafka DescribeTopic --InstanceId "ckafka-xxxxxx" --TopicName "test-topic"
```

### Step 4: Check Consumer Group

```bash
tccli ckafka DescribeGroup --InstanceId "ckafka-xxxxxx" --GroupName "consumer-group-1"
```

### Step 5: Check Quotas

```bash
# List instances to check count
tccli ckafka DescribeInstances --Region ap-guangzhou | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Total instances: {d[\"Response\"][\"TotalCount\"]}')"

# Check topic count for instance
tccli ckafka DescribeTopic --InstanceId "ckafka-xxxxxx" --Limit 1 | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Topic count: {d[\"Response\"][\"Result\"][\"TotalCount\"]}')"
```

### Step 6: Check Recent Tasks

```bash
tccli ckafka DescribeTaskStatus --InstanceId "ckafka-xxxxxx" --FlowId 12345
```

---

## 3. Common Issues and Solutions

### Issue 1: Cannot Connect to CKafka

**Symptoms:** Connection timeout, `Connection refused`, SASL authentication failure.

**Diagnosis:**
```bash
# Check instance status and endpoint
tccli ckafka DescribeInstances --InstanceIdList '["ckafka-xxxxxx"]' --Region ap-guangzhou | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['InstanceList'][0]
print(f'Status: {i[\"Status\"]}')
print(f'VIP: {i.get(\"Vip\", \"N/A\")}')
print(f'VPort: {i.get(\"VPort\", \"N/A\")}')
print(f'PublicAccess: {i.get(\"PublicAccess\", \"N/A\")}')
print(f'KafkaVersion: {i.get(\"Version\", \"N/A\")}')
"

# Check topic exists
tccli ckafka DescribeTopic --InstanceId "ckafka-xxxxxx" --TopicName "test-topic"
```

**Root Causes:**
- Instance is isolated (Status=3)
- Instance is restarting or upgrading (Status=5,4)
- Security group blocks access
- Wrong SASL credentials
- Topic doesn't exist
- Using wrong endpoint (VIP vs Public IP)

**Solutions:**
1. If Status=3 → renew instance:
   ```bash
   tccli ckafka RenewCkafkaInstance --InstanceId "ckafka-xxxxxx" --TimeSpan 1 --TimeUnit "m"
   ```
2. If Status=4,5 → wait for completion, check task status
3. Check security group via `qcloud-vpc-ops`
4. Verify SASL credentials:
   ```bash
   tccli ckafka DescribeUser --InstanceId "ckafka-xxxxxx"
   ```
5. Enable public access if needed:
   ```bash
   tccli ckafka ModifyInstanceAttributes --InstanceId "ckafka-xxxxxx" --EnablePublicAccess 1
   ```

### Issue 2: High Consumer Lag

**Symptoms:** Message processing delay, consumer lag increasing, alerts firing.

**Diagnosis:**
```bash
# Check consumer group offsets
tccli ckafka DescribeGroupOffsets --InstanceId "ckafka-xxxxxx" --Group "consumer-group-1"

# Get metrics via Cloud Monitor
tccli monitor GetMonitorData \
  --Namespace QCE/CKAFKA \
  --MetricName ConsumerGroupOffsetLag \
  --Dimensions '[{"Name":"InstanceId","Value":"ckafka-xxxxxx"},{"Name":"ConsumerGroup","Value":"consumer-group-1"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 300
```

**Root Causes:**
- Insufficient consumer instances
- Consumer processing too slow
- Network latency
- Message size too large
- Consumer rebalancing frequently

**Solutions:**
1. Scale consumer group (add more consumers)
2. Optimize consumer processing logic
3. Increase partition count to scale parallelism:
   ```bash
   tccli ckafka ModifyPartitionNum --InstanceId "ckafka-xxxxxx" --TopicName "topic-name" --PartitionNum 12
   ```
4. Check CVM resources via `qcloud-cvm-ops`
5. Consider increasing `max.poll.records`
6. Check for consumer rebalancing issues (consumer session timeout)

### Issue 3: Topic Creation Fails

**Error:** `OperationDenied.TopicPartitionLimit` or `LimitExceeded.TopicNum`

**Diagnosis:**
```bash
# Check current topic count
tccli ckafka DescribeTopic --InstanceId "ckafka-xxxxxx" --Limit 1 | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Topics: {d[\"Response\"][\"Result\"][\"TotalCount\"]}')"

# Check instance limits
tccli ckafka DescribeInstanceAttributes --InstanceId "ckafka-xxxxxx" | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['Result']
print(f'MaxTopicNumber: {i.get(\"MaxTopicNumber\", \"N/A\")}')
print(f'MaxPartitionNumber: {i.get(\"MaxPartitionNumber\", \"N/A\")}')
"
```

**Solutions:**
1. Delete unused topics:
   ```bash
   tccli ckafka DeleteTopic --InstanceId "ckafka-xxxxxx" --TopicName "unused-topic"
   ```
2. Upgrade instance for higher limits:
   ```bash
   tccli ckafka ModifyInstancePre --InstanceId "ckafka-xxxxxx" --Bandwidth 800
   ```

### Issue 4: Message Production Fails

**Symptoms:** Producer timeout, `NotEnoughReplicasException`, `RecordTooLargeException`.

**Diagnosis:**
```bash
# Check topic configuration
tccli ckafka DescribeTopicAttributes --InstanceId "ckafka-xxxxxx" --TopicName "test-topic"

# Check broker metrics
tccli monitor GetMonitorData \
  --Namespace QCE/CKAFKA \
  --MetricName InstanceMessagesIn \
  --Dimensions '[{"Name":"InstanceId","Value":"ckafka-xxxxxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 60
```

**Root Causes:**
- Insufficient replicas available
- Message exceeds max size (12MB)
- Producer buffer full
- Network issues
- Broker overloaded

**Solutions:**
1. Check replica status:
   ```bash
   tccli ckafka DescribeTopicAttributes --InstanceId "ckafka-xxxxxx" --TopicName "test-topic" | python3 -c "
   import sys,json
   d=json.load(sys.stdin)
   for p in d['Response']['Result'].get('Partitions', []):
       print(f'Partition {p[\"Partition\"]}: Leader={p[\"Leader\"]}, ISR={p[\"Isr\"]}')
   "
   ```
2. Reduce message size or batch size
3. Increase `request.timeout.ms` in producer config
4. Check disk usage and upgrade if needed

### Issue 5: Partition Reassignment Stuck

**Symptoms:** Reassignment not completing, ISR shrinking, under-replicated partitions.

**Diagnosis:**
```bash
# Check partition status
tccli ckafka DescribeTopicAttributes --InstanceId "ckafka-xxxxxx" --TopicName "test-topic"

# Check task status
tccli ckafka DescribeTaskStatus --InstanceId "ckafka-xxxxxx" --FlowId 12345
```

**Root Causes:**
- Network issues between brokers
- Destination broker overloaded
- Insufficient disk space
- Task timeout

**Solutions:**
1. Check broker health via metrics
2. Retry reassignment with smaller batches
3. Check disk usage:
   ```bash
   tccli monitor GetMonitorData \
     --Namespace QCE/CKAFKA \
     --MetricName InstanceDiskUsage \
     --Dimensions '[{"Name":"InstanceId","Value":"ckafka-xxxxxx"}]' \
     --StartTime 2026-05-20T00:00:00+08:00 \
     --EndTime 2026-05-21T00:00:00+08:00 \
     --Period 300
   ```
4. Upgrade disk size if needed:
   ```bash
   tccli ckafka ModifyInstancePre --InstanceId "ckafka-xxxxxx" --DiskSize 3000
   ```

### Issue 6: Consumer Rebalance Storm

**Symptoms:** Frequent rebalances, message processing interruptions, high latency.

**Diagnosis:**
```bash
# Check consumer group details
tccli ckafka DescribeGroupInfo --InstanceId "ckafka-xxxxxx" --GroupName "consumer-group-1"

# Monitor consumer count stability
tccli monitor GetMonitorData \
  --Namespace QCE/CKAFKA \
  --MetricName ConsumerGroupMembers \
  --Dimensions '[{"Name":"InstanceId","Value":"ckafka-xxxxxx"},{"Name":"ConsumerGroup","Value":"consumer-group-1"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 60
```

**Root Causes:**
- Consumer session timeout too short
- Frequent consumer failures/restarts
- Consumer processing taking too long
- Network instability

**Solutions:**
1. Increase `session.timeout.ms` (default: 10s → 30s)
2. Increase `heartbeat.interval.ms` proportionally
3. Increase `max.poll.interval.ms` for slow consumers
4. Enable static membership (group.instance.id)
5. Check consumer health and logs

### Issue 7: SASL Authentication Failure

**Error:** `AuthFailure`, `SASL authentication failed`, `Invalid user credentials`.

**Diagnosis:**
```bash
# List users
tccli ckafka DescribeUser --InstanceId "ckafka-xxxxxx"

# Check ACL rules
tccli ckafka DescribeAclRule --InstanceId "ckafka-xxxxxx" --ResourceType 2 --ResourceName "test-topic"
```

**Root Causes:**
- Wrong username/password
- User doesn't exist
- ACL rules blocking access
- SASL mechanism mismatch

**Solutions:**
1. Reset user password:
   ```bash
   tccli ckafka ModifyUser --InstanceId "ckafka-xxxxxx" --Name "user1" --Password "NewPassword123!"
   ```
2. Check user exists:
   ```bash
   tccli ckafka DescribeUser --InstanceId "ckafka-xxxxxx" | grep "user1"
   ```
3. Verify ACL rules grant access
4. Ensure client uses correct SASL mechanism (SCRAM-SHA-512)

### Issue 8: Disk Full

**Symptoms:** Production blocked, `KafkaStorageException`, retention not working.

**Diagnosis:**
```bash
# Check disk usage metrics
tccli monitor GetMonitorData \
  --Namespace QCE/CKAFKA \
  --MetricName InstanceDiskUsage \
  --Dimensions '[{"Name":"InstanceId","Value":"ckafka-xxxxxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 300

# Check topic retention settings
tccli ckafka DescribeTopicAttributes --InstanceId "ckafka-xxxxxx" --TopicName "test-topic" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'RetentionMs: {d[\"Response\"][\"Result\"].get(\"RetentionMsConfig\", \"N/A\")}')"
```

**Solutions:**
1. Expand disk size:
   ```bash
   tccli ckafka ModifyInstancePre --InstanceId "ckafka-xxxxxx" --DiskSize 4000
   ```
2. Reduce retention time for topics:
   ```bash
   tccli ckafka ModifyTopicAttributes --InstanceId "ckafka-xxxxxx" --TopicName "test-topic" --RetentionMs 86400000
   ```
3. Delete old topics
4. Enable compression on producers
5. Clean up consumer offsets (if using compacted topics)

### Issue 9: Upgrade Fails

**Error:** `OperationDenied.InstanceStatusError` or `InvalidParameterValue`

**Diagnosis:**
```bash
# Check current version and status
tccli ckafka DescribeInstances --InstanceIdList '["ckafka-xxxxxx"]' --Region ap-guangzhou | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['InstanceList'][0]
print(f'Version: {i[\"Version\"]}')
print(f'Status: {i[\"Status\"]}')
"
```

**Solutions:**
1. Ensure instance status is 1 (running)
2. Check no tasks are in progress:
   ```bash
   # List topics to verify instance is responsive
   tccli ckafka DescribeTopic --InstanceId "ckafka-xxxxxx" --Limit 1
   ```
3. Wait for any pending operations to complete
4. Retry upgrade with proper parameters

---

## 4. API Retry Strategy

```bash
# Retry wrapper for CKafka CLI commands
retry_ckafka_command() {
  local cmd="$1"
  local max_attempts=3
  local attempt=1
  
  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt/$max_attempts..."
    output=$(eval "$cmd" 2>&1)
    if echo "$output" | grep -q "RequestLimitExceeded\|InternalError\|OperationDenied.InstanceLocked\|FailedOperation.StatusConflict"; then
      wait=$((2 ** attempt))
      echo "Retrying in ${wait}s..."
      sleep $wait
      attempt=$((attempt + 1))
    else
      echo "$output"
      return 0
    fi
  done
  echo "Command failed after $max_attempts attempts"
  echo "$output"
  return 1
}

# Usage: retry_ckafka_command "tccli ckafka CreateTopic --InstanceId ckafka-xxxxxx --TopicName test-topic --PartitionNum 6 --ReplicaNum 3"
```

---

## 5. Health Check Runbook

```bash
#!/bin/bash
# CKafka instance health check
INSTANCE_ID="${1:-ckafka-xxxxxx}"
REGION="${2:-ap-guangzhou}"

echo "=== CKafka Instance Health Check ==="
echo "Instance: $INSTANCE_ID"
echo "Region: $REGION"

# 1. Basic info and status
echo ""
echo "--- Instance Info ---"
tccli ckafka DescribeInstances --InstanceIdList "[\"$INSTANCE_ID\"]" --Region $REGION | python3 -c "
import sys,json
d=json.load(sys.stdin)
if d['Response']['InstanceList']:
    i=d['Response']['InstanceList'][0]
    print(f'Name: {i.get(\"InstanceName\", \"N/A\")}')
    print(f'Status: {i[\"Status\"]} (0=creating, 1=running, 3=isolated)')
    print(f'Version: {i.get(\"Version\", \"N/A\")}')
    print(f'Type: {i.get(\"InstanceType\", \"N/A\")}')
    print(f'VIP: {i.get(\"Vip\", \"N/A\")}')
    print(f'VPort: {i.get(\"VPort\", \"N/A\")}')
    print(f'Zone: {i.get(\"ZoneId\", \"N/A\")}')
else:
    print('ERROR: Instance not found!')
"

# 2. Topic count
echo ""
echo "--- Topic Summary ---"
tccli ckafka DescribeTopic --InstanceId "$INSTANCE_ID" --Limit 1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
total=d['Response']['Result']['TotalCount']
print(f'Total Topics: {total}')
"

# 3. Consumer groups
echo ""
echo "--- Consumer Group Summary ---"
tccli ckafka DescribeGroup --InstanceId "$INSTANCE_ID" --Limit 1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
total=d['Response']['Result']['TotalCount']
print(f'Total Consumer Groups: {total}')
"

# 4. Recent metrics (last 1 hour)
echo ""
echo "--- Recent Metrics (1h) ---"
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_TIME=$(date -u -v-1H +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d '1 hour ago' +"%Y-%m-%dT%H:%M:%SZ")

tccli monitor GetMonitorData \
  --Namespace QCE/CKAFKA \
  --MetricName InstanceMessagesIn \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"$INSTANCE_ID\"}]" \
  --StartTime "$START_TIME" \
  --EndTime "$END_TIME" \
  --Period 300 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
if 'Response' in d and 'DataPoints' in d['Response']:
    points = d['Response']['DataPoints'][0].get('Values', [])
    if points:
        avg = sum(points) / len(points)
        print(f'Messages In (avg): {avg:.2f} msg/s')
    else:
        print('No data points')
else:
    print('Metrics unavailable')
"

echo ""
echo "=== Health Check Complete ==="
```

---

## 6. Performance Tuning Quick Reference

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| **Consumer Lag** | < 1000 | 1000-10000 | > 10000 |
| **Disk Usage** | < 70% | 70-85% | > 85% |
| **CPU Usage** | < 60% | 60-80% | > 80% |
| **Memory Usage** | < 70% | 70-85% | > 85% |
| **ISR Expansion** | 0% | < 5% | > 5% |
| **Request Latency** | < 10ms | 10-50ms | > 50ms |

**Immediate Actions:**
- **Consumer Lag Critical:** Add consumers, increase partitions
- **Disk Usage Critical:** Expand disk, reduce retention, delete data
- **CPU/Memory Critical:** Upgrade instance, optimize producers/consumers
