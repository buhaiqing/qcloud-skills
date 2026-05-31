# Troubleshooting — TencentDB for PostgreSQL

## Error Code Reference

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| InvalidParameterValue.NotFoundInstance | 未找到实例 | Verify instance ID via DescribeDBInstances |
| InvalidParameterValue.IllegalInstanceStatus | 实例状态不允许操作 | Check status; wait for running state |
| InvalidParameterValue.SpecNotOnSale | 购买规格错误 | Use DescribeProductConfig for available specs |
| InvalidParameterValue.ZoneClosed | 可用区已关闭售卖 | Choose different AZ |
| InvalidParameterValue.PostPaidInstanceBeyondLimit | 后付费实例超限 | Delete unused instances or switch to prepaid |
| InvalidParameterValue.PasswordRuleFailed | 密码不符合规范 | 8-32 chars, letters + digits + special chars |
| FailedOperation.DeletionProtectionEnabled | 实例开启了销毁保护 | Disable deletion protection first |
| FailedOperation.OperationNotAllowedInInstanceLocking | 实例锁定中 | Retry 3x with 30s backoff |
| InternalError.TradeError | 交易系统错误 | Retry 3x with 5s backoff; escalate with RequestId |
| LimitExceeded.TooManyRequests | 请求太过频繁 | Retry 3x with exponential backoff |
| AuthFailure | CAM鉴权错误 | HALT; check credentials |
| FailedOperation.QueryInstanceError | 查询实例错误 | Retry; if persistent contact support |
| InvalidParameterValue.BackupNotFound | 备份不存在 | List backups to find valid backup ID |
| InvalidParameterValue.StorageLessThanUsed | 磁盘容量低于已用量 | Increase Storage to ≥ current used |

## Diagnostic Workflows

### Instance Unreachable

1. Check instance status:
   ```bash
   tccli postgres DescribeDBInstances --Filters '[{"Name":"db-instance-id","Values":["{{user.instance_id}}"]}]'
   ```
2. If status is `isolated`, check billing status and re-activate
3. If status is `creating`, wait and retry
4. If status is `deleted`, instance is gone — create a new one

### Connection Failure

1. Verify network: instance is in same VPC as your client
2. Check security group allows inbound on port 5432
3. Check `pg_hba.conf` via parameter group settings
4. Verify account exists and password is correct
5. Test telnet: `telnet <vip> 5432`

### Slow Queries

1. Enable slow query logging:
   ```bash
   tccli postgres ModifyDBInstanceParameters --DBInstanceId "{{user.instance_id}}" --ParamList '[{"Name":"log_min_duration_statement","Value":"1000"}]'
   ```
2. Query slow logs:
   ```bash
   tccli postgres DescribeSlowQueryList --DBInstanceId "{{user.instance_id}}" --StartTime "2026-05-28 00:00:00" --EndTime "2026-05-31 00:00:00"
   ```
3. Check for missing indexes, sequential scans, or high `work_mem` needs

### Backup Failure

1. Check available storage (backup needs space)
2. Verify instance is in `running` state
3. Check backup retention limit
4. For large databases, use physical backup type

### Insufficient Disk Space

1. Query current usage: check `Storage` vs free space
2. Archive or delete old data
3. Upgrade storage: `tccli postgres UpgradeDBInstance --DBInstanceId "{{user.instance_id}}" --Memory <current> --Storage <new>`
4. Consider archiving old WAL logs

### Multi-round Diagnostics

```
Issue reported → "I can't connect to my PostgreSQL instance"
  ├─ Check instance status (running?)
  │  ├─ NO → Is it creating? Wait. Is it isolated? Check payment.
  │  └─ YES → Continue
  ├─ Check network (same VPC?)
  │  ├─ NO → Configure VPC peering or re-deploy
  │  └─ YES → Continue
  ├─ Check security group (port 5432 open?)
  │  ├─ NO → Add inbound rule
  │  └─ YES → Continue
  ├─ Check credentials (password correct?)
  │  ├─ NO → Reset password
  │  └─ YES → Continue
  └─ Connection pool full? → Increase max_connections
```
