# CDB Troubleshooting Guide

CDB-specific error codes, diagnostic steps, and recovery patterns for Tencent Cloud TencentDB for MySQL.

---

## 1. Error Code Reference (CDB-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter` | Parameter validation failed | Fix parameter per API spec |
| `InvalidParameterValue` | Parameter value out of range | Adjust value per spec |
| `MissingParameter` | Required parameter missing | Add missing parameter |
| `ResourceNotFound` | Resource not found | Verify instance ID via DescribeDBInstances |
| `ResourceNotFound.NoDBInstanceFound` | DB instance not found | Verify InstanceId |
| `ResourceInsufficient` | Resource quota insufficient | HALT; raise quota or delete resources |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `InvalidSecretId` | Credential ID invalid | HALT; fix credentials |
| `OperationDenied.InstanceLocked` | Instance locked by operation | Retry (3x, 30s); wait for completion |
| `OperationDenied.InstanceStatusError` | Wrong instance status for op | Check status via DescribeDBInstances |
| `OperationDenied.NotSupported` | Operation not supported | Check instance type/version |
| `OperationDenied.PayModeError` | Billing mode doesn't support op | Check prepaid vs postpaid |
| `FailedOperation.AsyncTaskError` | Async task execution failure | Retry (3x); check async task or escalate |
| `FailedOperation.CreateOrderFailed` | Order creation failed | HALT; check account balance/spec validity |
| `FailedOperation.StatusConflict` | Status conflict | Retry (2x, 10s); wait and retry |
| `FailedOperation.TaskAlreadyExist` | Task already in progress | Retry (3x, 30s); check DescribeTasks |
| `FailedOperation.AuthStrategyError` | Authentication strategy error | Check account privileges |
| `FailedOperation.TagDryRunError` | Tag dry-run error | Check tag format; retry without tags |
| `LimitExceeded.ExceedMaxInstanceCount` | Max instance count exceeded | HALT; raise instance quota |
| `LimitExceeded.ExceedMaxBackupCount` | Max backup count exceeded | Delete old backups |
| `LimitExceeded.TooManyAccounts` | Too many accounts | Delete unused accounts |
| `RequestLimitExceeded` | API rate limit exceeded | Retry (3x); exponential backoff (2s, 4s, 8s) |
| `InternalError` | Internal server error | Retry (3x); escalate with RequestId |
| `InternalError.DBError` | Database internal error | Retry (3x); escalate with RequestId |
| `InternalError.TaskError` | Task internal error | Retry (3x); check task details |
| `UnauthorizedOperation` | Unauthorized operation | HALT; check CAM permissions |
| `UnsupportedOperation` | Unsupported operation | Check version/region compatibility |

---

## 2. Diagnostic Workflow

### Step 1: Check Instance Exists

```bash
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]' --Region ap-guangzhou
```

- If `TotalCount: 0` → Instance not found or wrong InstanceId
- If `Items[0].Status: 5` → Instance is isolated

### Step 2: Check Instance State

```bash
STATUS=$(tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['Items'][0]['Status'])")
echo "Instance state: $STATUS"
# 0=creating, 1=running, 4=isolating, 5=isolated
```

Valid states for operations:
- UpgradeDBInstance → Status=1 (running)
- IsolateDBInstance → Status=1 (running)
- RestartDBInstances → Status=1 (running)
- ModifyInstanceParam → Status=1 (running)
- CreateBackup → Status=1 (running)

### Step 3: Check Connection

```bash
# Get connection info
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]' | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['Items'][0]
print(f'Host: {i[\"Vip\"]}')
print(f'Port: {i[\"Vport\"]}')
print(f'Status: {i[\"Status\"]}')
print(f'Engine: {i[\"EngineVersion\"]}')
"
```

Test connectivity (from a CVM in the same VPC):
```bash
mysql -h 10.0.0.10 -P 3306 -u dbuser -p -e "SELECT 1"
```

### Step 4: Check Quota

```bash
# Describe quotas
tccli cdb DescribeDBInstances --Region ap-guangzhou | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Total instances: {d[\"Response\"][\"TotalCount\"]}')"
```

### Step 5: Check Recent Tasks

```bash
tccli cdb DescribeTasks \
  --InstanceId "cdb-xxxxxx" \
  --StartTimeBegin "2026-05-20 00:00:00" \
  --StartTimeEnd "2026-05-21 00:00:00"
```

---

## 3. Common Issues and Solutions

### Issue 1: Cannot Connect to MySQL Instance

**Symptoms:** Connection timeout, `Can't connect to MySQL server`, `Connection refused`.

**Diagnosis:**
```bash
# Check instance status
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]' | python3 -c "import sys,json;d=json.load(sys.stdin);i=d['Response']['Items'][0];print(f'Status:{i[\"Status\"]}, IP:{i[\"Vip\"]}:{i[\"Vport\"]}')"

# Check if WAN is enabled
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['Items'][0])"
```

**Root Causes:**
- Instance is isolated (Status=5)
- Instance is restarting or in maintenance
- Security group does not allow traffic from source IP
- WAN access not enabled (for external connections)

**Solutions:**
1. If Status=5 → renew instance: `tccli cdb RenewDBInstance --InstanceId "cdb-xxxxxx" --TimeSpan 1`
2. If Status=1 but cannot connect → check security group via `qcloud-vpc-ops`
3. For external access → enable WAN: `tccli cdb OpenWanService --InstanceId "cdb-xxxxxx"`
4. Verify port settings: `tccli cdb ModifyDBInstanceVipVport` if non-standard

### Issue 2: Slow Queries

**Symptoms:** Application timeouts, high response time, increased database CPU.

**快速诊断路径 (MTTD ≤ 5 分钟):**

> **推荐**: 对于慢查询问题，请使用 [CDB 慢查询快速诊断决策树](cdb-slow-query-diagnosis-optimized.md) 进行结构化诊断。

**快速检查:**
```bash
# 1. 确认慢查询是否存在 (最近 1 小时)
tccli cdb DescribeSlowLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')" \
  --Limit 5 \
  --OrderBy "QueryTime" \
  --Order "DESC"

# 2. 检查慢查询日志是否开启
tccli cdb DescribeInstanceParams \
  --InstanceId "cdb-xxxxxx" \
  --ParamNames '["slow_query_log","long_query_time"]'
```

**慢查询分类 (基于决策树):**

| 类型 | 特征 | 优先级 | 自动化恢复 |
|------|------|--------|------------|
| **Type A: 超长查询** | QueryTime > 10s | P0 | 终止查询 |
| **Type B: 资源瓶颈** | CPU > 80% | P1 | 参数调优/规格升级 |
| **Type C: 锁等待** | LockTime/QueryTime > 50% | P1 | 终止阻塞事务 |
| **Type D: 查询优化** | QueryTime 1-10s | P2 | SQL 重写/添加索引 |

**详细诊断:**
```bash
# 获取慢查询详情
tccli cdb DescribeSlowLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')" \
  --Limit 20 \
  --OrderBy "QueryTime" \
  --Order "DESC"

# 检查实例 CPU/内存
tccli monitor GetMonitorData \
  --Namespace QCE/CDB \
  --MetricName CpuUseRate \
  --Dimensions '[{"Name":"InstanceId","Value":"cdb-xxxxxx"}]' \
  --StartTime "$(date -v-1H +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Period 300
```

**快速恢复策略 (MTTR ≤ 15 分钟):**

| 策略 | 适用场景 | 命令 |
|------|----------|------|
| 终止超长查询 | Type A | `CALL mysql.rds_kill(<thread_id>)` |
| 添加索引 | Type D | `CREATE INDEX idx_xxx ON table(col)` |
| 参数调优 | Type B/C | `ModifyInstanceParam` |
| 规格升级 | Type B (长期) | `UpgradeDBInstance` |

**验证恢复效果:**
```bash
# 等待 5 分钟后重新检查
sleep 300
tccli cdb DescribeSlowLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "$(date -v-5M +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')" \
  --Limit 5 \
  --OrderBy "QueryTime" \
  --Order "DESC"
```

**参考文档:**
- [CDB 慢查询快速诊断决策树](cdb-slow-query-diagnosis-optimized.md) - 完整诊断流程和自动化恢复策略
- [CDB 监控配置](monitoring.md) - 慢查询告警配置

### Issue 3: High CPU Usage

**Symptoms:** Instance CPU > 80%, queries slowing down, connection accumulation.

**Diagnosis:**
```bash
# Get CPU metrics
tccli monitor GetMonitorData \
  --Namespace QCE/CDB \
  --MetricName CpuUseRate \
  --Dimensions '[{"Name":"InstanceId","Value":"cdb-xxxxxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 300

# Check slow queries
tccli cdb DescribeSlowLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "2026-05-20 00:00:00" \
  --EndTime "2026-05-21 00:00:00" \
  --OrderBy "QueryTime" \
  --Order "DESC" \
  --Limit 10
```

**Solutions:**
1. Identify CPU-intensive queries from slow log; optimize or add indexes
2. Scale up instance: `tccli cdb UpgradeDBInstance --InstanceId "cdb-xxxxxx" --Memory 8000 --Volume 500`
3. Check for table locks or concurrent full table scans
4. Implement read replicas for read-heavy workloads

### Issue 4: Disk Full

**Symptoms:** MySQL error `Error 1114: The table is full`, unable to write data, INSERT/UPDATE fails.

**Diagnosis:**
```bash
# Check disk usage
tccli monitor GetMonitorData \
  --Namespace QCE/CDB \
  --MetricName DiskUseRate \
  --Dimensions '[{"Name":"InstanceId","Value":"cdb-xxxxxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 300

# Check backup size (backups count against disk quota)
tccli cdb DescribeBackups --InstanceId "cdb-xxxxxx" --Limit 10
```

**Solutions:**
1. Scale up disk: `tccli cdb UpgradeDBInstance --InstanceId "cdb-xxxxxx" --Volume 500`
2. Delete old backups: `tccli cdb DeleteBackups --InstanceId "cdb-xxxxxx" --BackupIds "[12345]"`
3. Archive and drop old data from large tables
4. Optimize tables: `OPTIMIZE TABLE my_table` (reclaims space)
5. Check binlog retention: modify `binlog_expire_logs_seconds`

### Issue 5: Backup Failure

**Error:** `FailedOperation.AsyncTaskError` or `LimitExceeded.ExceedMaxBackupCount`

**Diagnosis:**
```bash
# Check backup list
tccli cdb DescribeBackups --InstanceId "cdb-xxxxxx"

# Check backup config
tccli cdb DescribeBackupConfig --InstanceId "cdb-xxxxxx"
```

**Solutions:**
1. Delete old backups to free up quota: `tccli cdb DeleteBackups`
2. If disk is full → expand disk first, then retry backup
3. Retry with different backup method (physical vs logical)
4. Ensure backup window has enough time for completion

### Issue 6: Version Upgrade Fails

**Error:** `OperationDenied.InstanceStatusError` or `InvalidParameterValue`

**Diagnosis:**
```bash
# Check supported versions
tccli cdb DescribeSupportedEngineVersions --InstanceId "cdb-xxxxxx"

# Check current version
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['Items'][0]['EngineVersion'])"
```

**Solutions:**
1. Ensure instance status is 1 (running)
2. Create a backup before upgrade
3. Upgrade one major version at a time (5.5 → 5.6 → 5.7 → 8.0)
4. Check if any deprecated features are being used (e.g., old password hashing)

### Issue 7: Account/Password Issues

**Symptoms:** `Access denied for user`, password lost, account locked.

**Diagnosis:**
```bash
# List accounts
tccli cdb DescribeAccounts --InstanceId "cdb-xxxxxx"
```

**Solutions:**
1. Reset password: `tccli cdb ModifyAccountPassword --InstanceId "cdb-xxxxxx" --Accounts '[{"User":"user","Host":"%"}]' --NewPassword "NewSecurePass123!"`
2. Check account privileges: use `ModifyAccountPrivileges` regrant
3. Delete and recreate account if corrupted

---

## 4. API Retry Strategy

```bash
# Retry wrapper for CDB CLI commands
retry_cdb_command() {
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

# Usage: retry_cdb_command "tccli cdb UpgradeDBInstance --InstanceId cdb-xxxxxx --Memory 8000 --Volume 500"
```

---

## 5. Health Check Runbook

```bash
#!/bin/bash
# CDB instance health check
INSTANCE_ID="${1:-cdb-xxxxxx}"

echo "=== CDB Instance Health Check ==="
echo "Instance: $INSTANCE_ID"

# 1. Basic info and status
echo "--- Instance Info ---"
tccli cdb DescribeDBInstances --InstanceIds "[\"$INSTANCE_ID\"]" | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['Items'][0]
print(f'Name: {i[\"InstanceName\"]}')
print(f'Status: {i[\"Status\"]}')
print(f'Version: {i[\"EngineVersion\"]}')
print(f'Spec: {i[\"Memory\"]}MB / {i[\"Volume\"]}GB')
print(f'IP: {i[\"Vip\"]}:{i[\"Vport\"]}')
print(f'Zone: {i[\"Zone\"]}')
"

echo "--- Recent Tasks ---"
tccli cdb DescribeTasks --InstanceId "$INSTANCE_ID" \
  --StartTimeBegin "$(date -v-1d +'%Y-%m-%d 00:00:00')" \
  --StartTimeEnd "$(date +'%Y-%m-%d %H:%M:%S')"
```
