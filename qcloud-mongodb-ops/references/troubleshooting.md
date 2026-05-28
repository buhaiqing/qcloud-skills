# Troubleshooting Guide — TencentDB for MongoDB

## Error Code Taxonomy

### Authentication & Authorization Errors

| Code | Meaning | Recovery |
|------|---------|----------|
| AuthFailure | CAM签名/鉴权错误 | Check TENCENTCLOUD_SECRET_ID/TENCENTCLOUD_SECRET_KEY; verify CAM policy |
| UnauthorizedOperation.NoAccess | 没有访问权限 | Check CAM policy; grant mongodb:* permissions |
| InvalidParameter.PermissionDenied | 子账号无权执行 | Escalate to account admin |

### Instance Errors

| Code | Meaning | Recovery |
|------|---------|----------|
| InvalidParameterValue.NotFoundInstance | 未找到实例 | Verify instance ID; use DescribeDBInstances to search |
| InvalidParameterValue.InstanceHasBeenDeleted | 实例已删除 | Cannot recover; create new instance |
| InvalidParameterValue.InstanceHasBeenIsolated | 实例已隔离 | Renew or restore from isolation |
| InvalidParameterValue.IllegalInstanceStatus | 实例状态不允许操作 | DescribeDBInstances to check current status; wait for running |
| FailedOperation.OperationNotAllowedInInstanceLocking | 实例锁定中 | Retry 3x with 30s backoff |
| FailedOperation.DeletionProtectionEnabled | 销毁保护已开启 | Disable via SetDBInstanceDeletionProtection first |
| InvalidParameterValue.PrePaidInstanceUnableToIsolate | 预付费不支持销毁 | Use TerminateDBInstances instead of IsolateDBInstance |

### Parameter & Spec Errors

| Code | Meaning | Recovery |
|------|---------|----------|
| InvalidParameterValue.ModifyModeError | 内存和磁盘必须同时升配或降配 | Adjust both Memory and Volume in same direction |
| InvalidParameterValue.SetDiskLessThanUsed | 磁盘需≥已用磁盘1.2倍 | Increase Volume to ≥ 1.2× used disk |
| InvalidParameterValue.SpecNotOnSale | 购买规格错误 | Use DescribeSpecInfo to list on-sale specs |
| InvalidParameterValue.ZoneClosed | 可用区已关闭售卖 | Choose different zone |
| InvalidParameterValue.PasswordRuleFailed | 密码不符合规范 | 8-32 chars, include letters + digits + special chars |
| InvalidParameterValue.OplogSizeOutOfRange | OplogSize需在磁盘10%-90% | Adjust OplogSize within range |

### Quota & Rate Limit Errors

| Code | Meaning | Recovery |
|------|---------|----------|
| InvalidParameterValue.PostPaidInstanceBeyondLimit | 后付费实例超限 | Delete unused instances or switch to prepaid |
| LimitExceeded.TooManyRequests | 请求太过频繁 | Retry 3x with exponential backoff |
| RequestLimitExceeded | 接口频率限制 | Reduce request rate; retry with backoff |

### Operation & Version Errors

| Code | Meaning | Recovery |
|------|---------|----------|
| UnsupportedOperation.VersionNotSupport | 版本不支持 | Upgrade MongoDB version |
| InvalidParameterValue.QueryTimeOutOfRange | 只能查询7天内的慢日志 | Reduce query range to 7 days max |
| FailedOperation.FlashbackByKeyNotOpen | 按key回档未开启 | Check if instance type supports this feature |
| FailedOperation.TransparentDataEncryptionAlreadyOpen | 已开启透明加密，不支持物理备份 | Use logical backup instead |

### System Errors

| Code | Meaning | Recovery |
|------|---------|----------|
| InternalError.TradeError | 交易系统错误 | Retry 3x with 5s backoff; escalate with RequestId |
| InternalError.DBError | 数据库异常 | Retry; escalate with RequestId |
| InternalError.FindInstanceFailed | 实例查询失败 | Retry; check instance ID |
| InternalError | 内部错误 | Retry 3x (2s, 4s, 8s); escalate with RequestId |

## Diagnostic Workflows

### 1. Instance Creation Fails

```
User: "Create MongoDB instance fails"

Step 1: Check DescribeSpecInfo → verify spec is on sale in the zone
Step 2: Check InquirePriceCreateDBInstances → verify price can be calculated
Step 3: Check error message:
  ├─ SpecNotOnSale → suggest available specs
  ├─ ZoneClosed → suggest different zone
  ├─ PostPaidInstanceBeyondLimit → suggest prepaid or clean up
  └─ TradeError → retry with backoff

Step 4: If price check passes but creation fails, check:
  ├─ Subnet available IPs (if VPC)
  ├─ Account balance (for prepaid)
  └─ CAM permissions for mongodb:Create*
```

### 2. Instance Connection Timeout

```
User: "Can't connect to MongoDB instance"

Step 1: DescribeDBInstances → check status
  ├─ Status=0 or 1 → wait for provisioning
  ├─ Status=3 → instance is isolated (renew needed)
  ├─ Status=-2 → instance deleted
  └─ Status=2 → continue

Step 2: Check network
  ├─ DescribeSecurityGroup → verify inbound rule allows MongoDB port (27017)
  ├─ DescribeClientConnections → check active connections
  └─ If VPC: verify subnet and routing

Step 3: Check connection info
  ├─ DescribeInstanceSSL → SSL mode may affect connection string
  ├─ DescribeDBInstanceURL → get correct URI format
  └─ Verify IP (Vip) and port (Vport) are correct

Step 4: If all looks correct but still cannot connect:
  ├─ Check if EnableWanService is needed (public access)
  └─ Suggest checking application-side firewall/network
```

### 3. Slow Query Performance

```
User: "MongoDB queries are slow"

Step 1: Check instance load
  ├─ DescribeCurrentOp → see running operations
  ├─ DescribeClientConnections → check connection count
  └─ Monitoring: CPU, Disk, Connections utilization

Step 2: Analyze slow queries
  ├─ DescribeSlowLogPatterns → find frequent patterns
  ├─ DescribeDetailedSlowLogs → get specific slow queries
  └─ Note: query range limited to 7 days

Step 3: Check instance health
  ├─ DescribeDBInstanceNodeProperty → check node roles and status
  ├─ Check SlaveDelay (replica set → primary lag)
  └─ Check OplogReservedTime → may need oplog size increase

Step 4: Optimization options
  ├─ ModifyInstanceParams → tune slowMS, maxConns
  ├─ ModifyDBInstanceSpec → scale up memory/disk
  └─ Suggest indexing strategy changes (app-level)
```

### 4. Backup Failure

```
User: "Backup failed"

Step 1: DescribeDBBackups → check recent backup status
Step 2: Check error:
  ├─ Status=1 (in progress) → wait and retry
  ├─ TDE enabled + physical backup → switch to logical backup
  └─ Instance locked/isolated → resolve instance state first

Step 3: Verify backup configuration
  ├─ DescribeBackupRules → check auto backup settings
  └─ If retention changed recently → verify disk space
```

### 5. Account Authentication Failure

```
User: "Can't authenticate to MongoDB"

Step 1: DescribeAccountUsers → verify account exists
Step 2: If account exists:
  ├─ ResetDBInstancePassword with new password
  └─ Check auth source database (admin by default)
Step 3: If account does not exist:
  └─ CreateAccountUser with proper AuthRole mask
```

### 6. Spec Modification Fails

```
User: "Failed to modify instance spec"

Step 1: DescribeDBInstances → check current Memory/Volume
Step 2: Check ModifyModeError:
  ├─ Memory and Volume must both increase or both decrease
  └─ SetDiskLessThanUsed: Volume must be ≥ 1.2× UsedVolume
Step 3: Check IllegalInstanceStatus:
  └─ Instance must be in running state (status=2)
Step 4: InquirePriceModifyDBInstanceSpec → verify price first
```

### 7. Instance Cannot Be Deleted

```
User: "Can't delete my MongoDB instance"

Step 1: DescribeDBInstances → check current status
  ├─ Status=2 (running) → can isolate
  └─ Status=3 (isolated) → can offline

Step 2: Check deletion protection:
  └─ If FailedOperation.DeletionProtectionEnabled → use SetDBInstanceDeletionProtection

Step 3: Check payment mode:
  ├─ Postpaid → use IsolateDBInstance + OfflineIsolatedDBInstance
  └─ Prepaid → use TerminateDBInstances
```

### 8. Audit Service Issues

```
User: "Audit service not working"

Step 1: DescribeAuditConfig → check current audit status
Step 2: If not enabled → OpenAuditService with desired retention
Step 3: If enabled but no logs:
  ├─ DescribeAuditLogs with correct time range
  └─ Verify instance version supports audit (≥ certain kernel version)
Step 4: Check OperationDenied errors:
  └─ Verify sub-account has audit operation permissions
```
