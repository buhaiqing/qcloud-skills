# ES Troubleshooting Guide

ES-specific error codes, diagnostic steps, and recovery patterns for Tencent Cloud Elasticsearch Service.

---

## 1. Error Code Reference (ES-Specific)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameterValue` | Parameter value invalid | No | Check parameter per API spec |
| `InvalidParameter.InvalidNodeType` | Node type not supported | No | DescribeInstances to list available types |
| `InvalidParameter.InvalidAppId` | AppId mismatch | No | Check account configuration |
| `MissingParameter` | Required parameter missing | No | Add missing required parameter |
| `ResourceNotFound` | ES instance not found | No | Verify InstanceId via DescribeInstances |
| `ResourceInsufficient` | Resource quota exceeded | No | HALT; raise quota or delete unused clusters |
| `AuthFailure.UnAuthDescribeInstances` | No CAM permission | No | HALT; add CAM policy |
| `FailedOperation.ClusterStateError` | Cluster in wrong state for operation | Yes (3x, 30s) | Wait for stable state; retry |
| `FailedOperation.NoEnoughNodes` | Insufficient node resources | No | Choose different AZ or node type |
| `FailedOperation.PayFailed` | Payment failure | No | HALT; check account balance |
| `FailedOperation.GetTagInfoError` | Tag query error | Yes (2x) | Retry; skip tag filter if persists |
| `FailedOperation.CosBackupModeError` | COS backup mode misconfigured | No | Check COS backup config |
| `OperationDenied` | Operation not allowed | No | Check instance status and permissions |
| `OperationDenied.InstanceStatusError` | Instance status invalid for op | No | Wait for correct state; check DescribeInstances |
| `RequestLimitExceeded` | API rate limit exceeded | Yes (3x) | Exponential backoff (2s, 4s, 8s) |
| `InternalError` | Internal server error | Yes (3x) | Retry; escalate with RequestId |
| `InternalError.DBError` | Database internal error | Yes (3x) | Retry; escalate with RequestId |

---

## 2. Diagnostic Workflow

### Step 1: Check Cluster Exists

```bash
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' --Region ap-guangzhou
```

- If `TotalCount: 0` → Cluster not found or wrong InstanceId
- If `InstanceList[0].Status: -1` → Cluster is stopped/isolated

### Step 2: Check Cluster Health

```bash
HEALTH=$(tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Response']['InstanceList'][0]['HealthStatus'])")
echo "Health status: $HEALTH"
# 0=green, 1=yellow, 2=red, -1=unknown
```

| Health | Action |
|--------|--------|
| Green (0) | Normal — no action needed |
| Yellow (1) | Check unassigned replica shards; may have insufficient nodes |
| Red (2) | Some primary shards unavailable — CRITICAL |
| Unknown (-1) | Cannot determine health — check connectivity |

### Step 3: Check Cluster Status

```bash
STATUS=$(tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Response']['InstanceList'][0]['Status'])")
echo "Cluster status: $STATUS"
# 0=processing, 1=normal, -1=stopped
```

Valid states for operations:
- UpdateInstance → Status=1 (normal)
- DeleteInstance → Status=1 (normal) or -1 (stopped)
- RestartInstance → Status=1 (normal)
- UpgradeInstance → Status=1 (normal)

### Step 4: Check Recent Operations

```bash
tccli es DescribeInstanceOperations \
  --InstanceId "es-xxxxxx" \
  --Offset 0 --Limit 10
```

Check for failed operations or ongoing tasks that might block the current request.

### Step 5: Check Logs

```bash
# ES logs
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 1

# Search slow logs
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 2

# Indexing slow logs
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 3
```

---

## 3. Common Issues and Solutions

### Issue 1: Health Status is Red (2)

**Symptoms:** Data unavailable, search/indexing failures, alerts firing.

**Diagnosis:**
```bash
# Check cluster health
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['InstanceList'][0]['HealthStatus'])"

# Run diagnostics
tccli es DiagnoseInstance --InstanceId "es-xxxxxx"

# Check diagnosis result
tccli es DescribeDiagnose --InstanceId "es-xxxxxx"
```

**Root Causes:**
- Node failure / CVM instance crash
- Disk full on one or more nodes
- Excessive shard allocation due to node loss

**Solutions:**
1. Restart the cluster: `tccli es RestartInstance --InstanceId "es-xxxxxx"`
2. If disk full: scale up disk via `UpdateInstance`
3. If node failure: replace nodes via `RestartNodes`
4. If shard issues: re-route unassigned shards via Kibana dev tools

### Issue 2: Health Status is Yellow (1)

**Symptoms:** Search works, but some replica shards not assigned; increased query latency.

**Diagnosis:**
```bash
# Check node count and disk
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' | python3 -c "import sys,json;d=json.load(sys.stdin);i=d['Response']['InstanceList'][0];print(f'Nodes:{i[\"NodeNum\"]}, Disk:{i[\"DiskSize\"]}GB')"
```

**Root Causes:**
- Not enough nodes to allocate all replica shards (need ≥ 2 nodes for replica=1)
- Node with replicas is unavailable
- Disk space low

**Solutions:**
1. Add more nodes: `tccli es UpdateInstance --InstanceId "es-xxxxxx" --NodeNum 5`
2. Reduce replica count per index via Kibana
3. Check disk usage and expand if needed

### Issue 3: Cluster Creation Fails

**Error:** `FailedOperation.NoEnoughNodes` or `ResourceInsufficient`

**Diagnosis:**
```bash
# Check available node types
tccli es DescribeInstances --Limit 1

# Verify zone resources
tccli es DescribeInstances --Region ap-guangzhou
```

**Solutions:**
1. Try a different AZ
2. Choose a different node type (smaller or larger)
3. Request quota increase from Tencent Cloud support
4. Delete unused clusters and retry

### Issue 4: Snapshot Backup Fails

**Error:** `FailedOperation.CosBackupModeError`

**Diagnosis:**
```bash
# Check snapshot configuration
tccli es DescribeClusterSnapshot --InstanceId "es-xxxxxx"
```

**Solutions:**
1. Verify COS bucket exists and is accessible
2. Check COS bucket permissions (required: write access)
3. Reconfigure COS backup settings
4. Delete old snapshots if quota exceeded

### Issue 5: Cannot Connect to Cluster (Kibana/API)

**Symptoms:** Connection timeout, `Connection refused`, unable to access Kibana.

**Diagnosis:**
```bash
# Check cluster status
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]'

# Verify Kibana URL
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['InstanceList'][0].get('KibanaUrl','N/A'))"
```

**Solutions:**
1. Ensure cluster is in Status=1 (normal)
2. Check VPC/security group rules allow traffic on ES port (9200) and Kibana (5601)
3. Delegate to `qcloud-vpc-ops` to verify security group rules
4. Restart Kibana: `tccli es RestartKibana --InstanceId "es-xxxxxx"`
5. Restart cluster: `tccli es RestartInstance --InstanceId "es-xxxxxx"`

### Issue 6: Slow Search Performance

**Symptoms:** High query latency, timeouts, CPU saturation.

**Diagnosis:**
```bash
# Check search slow logs
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 2

# Check JVM heap usage via Cloud Monitor (delegate to qcloud-monitor-ops)
tccli monitor GetMonitorData \
  --Namespace QCE/ES \
  --MetricName JvmHeapUsage \
  --Dimensions '[{"Name":"InstanceId","Value":"es-xxxxxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 300
```

**Solutions:**
1. **JVM heap > 80%:** Scale up node type via `UpdateInstance`
2. **High CPU:** Add more nodes or upgrade CPU
3. **Slow queries:** Optimize query patterns; use filters instead of queries where possible
4. **Large shards:** Re-index with more shards; enable ILM for rollover
5. **Force-merge:** `POST /my-index/_forcemerge?max_num_segments=1` (during maintenance window)

### Issue 7: Indexing Performance Issues

**Symptoms:** High indexing latency, bulk queue rejections, node dropping documents.

**Diagnosis:**
```bash
# Check indexing slow logs
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 3

# Check ES instance operations for recent scaling events
tccli es DescribeInstanceOperations --InstanceId "es-xxxxxx" --Offset 0 --Limit 5
```

**Solutions:**
1. **Bulk queue full:** Increase `thread_pool.bulk.queue_size` in index settings
2. **Disk I/O bottleneck:** Upgrade to CLOUD_HSSD or LOCAL_SSD
3. **Too many shards:** Reduce number of shards; merge small indices
4. **Refresh interval too frequent:** Set `index.refresh_interval: 30s` for bulk loading

### Issue 8: Version Upgrade Failure

**Error:** `FailedOperation.ClusterStateError` during `UpgradeInstance`

**Diagnosis:**
```bash
# Check current version
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['InstanceList'][0]['EsVersion'])"

# Check upgrade feasibility
tccli es UpgradeInstance \
  --InstanceId "es-xxxxxx" \
  --EsVersion "7.14.2" \
  --CheckOnly true
```

**Solutions:**
1. Ensure cluster health is green before upgrade
2. Take a snapshot before upgrade: `CreateClusterSnapshot`
3. Verify cluster has sufficient disk space for upgrade
4. Upgrade one major version at a time (e.g., 6.x → 7.x → 7.14)
5. If check fails, address issues shown in diagnosis result

---

## 4. API Retry Strategy

```bash
# Retry wrapper for ES CLI commands
retry_es_command() {
  local cmd="$1"
  local max_attempts=3
  local attempt=1
  
  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt/$max_attempts..."
    output=$(eval "$cmd" 2>&1)
    if echo "$output" | grep -q "RequestLimitExceeded\|InternalError\|FailedOperation.ClusterStateError"; then
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

# Usage
retry_es_command "tccli es UpdateInstance --InstanceId es-xxxxxx --NodeNum 5"
```

---

## 5. Health Check Runbook

```bash
#!/bin/bash
# ES cluster health check
INSTANCE_ID="${1:-es-xxxxxx}"

echo "=== ES Cluster Health Check ==="
echo "Instance: $INSTANCE_ID"

# 1. Basic info
echo "--- Cluster Info ---"
tccli es DescribeInstances --InstanceIds "[\"$INSTANCE_ID\"]" | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['InstanceList'][0]
print(f'Name: {i[\"InstanceName\"]}')
print(f'Status: {i[\"Status\"]}')
print(f'Health: {i[\"HealthStatus\"]}')
print(f'Version: {i[\"EsVersion\"]}')
print(f'Nodes: {i[\"NodeNum\"]}')
print(f'Disk: {i[\"DiskSize\"]}GB')
print(f'Domain: {i.get(\"EsDomain\",\"N/A\")}')
"

# 2. Diagnostics
echo "--- Diagnostics ---"
tccli es DiagnoseInstance --InstanceId "$INSTANCE_ID" > /dev/null 2>&1
sleep 5
tccli es DescribeDiagnose --InstanceId "$INSTANCE_ID"

# 3. Recent operations
echo "--- Recent Operations ---"
tccli es DescribeInstanceOperations --InstanceId "$INSTANCE_ID" --Offset 0 --Limit 5
```
