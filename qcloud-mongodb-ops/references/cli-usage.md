# CLI Usage — tccli mongodb

## Version

Always use API version 2019-07-25:
```bash
tccli mongodb <Action> --version 2019-07-25 [options...]
```

> Note: `--version` is optional if your tccli is configured to default to 2019-07-25.

## Command Map (79 Actions)

### Instance Management

| Action | CLI Command |
|--------|-------------|
| Create (prepaid) | `tccli mongodb CreateDBInstance --Zone ap-guangzhou-3 --NodeNum 3 --Memory 4 --Volume 10 --MongoVersion MONGO_60_WT --MachineCode HCD --GoodsNum 1 --ClusterType 0 --Period 1` |
| Create (postpaid) | `tccli mongodb CreateDBInstanceHour --Zone ap-guangzhou-3 --NodeNum 3 --Memory 4 --Volume 10 --MongoVersion MONGO_60_WT --MachineCode HCD --GoodsNum 1 --ClusterType 0` |
| List | `tccli mongodb DescribeDBInstances --Limit 20` |
| Describe | `tccli mongodb DescribeDBInstances --InstanceIds '["cmgo-xxxxx"]'` |
| Modify Spec | `tccli mongodb ModifyDBInstanceSpec --InstanceId cmgo-xxxxx --Memory 8 --Volume 20` |
| Isolate | `tccli mongodb IsolateDBInstance --InstanceId cmgo-xxxxx` |
| Offline Delete | `tccli mongodb OfflineIsolatedDBInstance --InstanceId cmgo-xxxxx` |
| Terminate (prepaid) | `tccli mongodb TerminateDBInstances --InstanceId cmgo-xxxxx` |
| Rename | `tccli mongodb RenameInstance --InstanceId cmgo-xxxxx --NewName "my-mongo-v2"` |
| Assign Project | `tccli mongodb AssignProject --InstanceIds '["cmgo-xxxxx"]' --ProjectId 123` |

### Backup & Restore

| Action | CLI Command |
|--------|-------------|
| Manual Backup | `tccli mongodb CreateBackupDBInstance --InstanceId cmgo-xxxxx` |
| List Backups | `tccli mongodb DescribeDBBackups --InstanceId cmgo-xxxxx` |
| Set Backup Rules | `tccli mongodb SetBackupRules --InstanceId cmgo-xxxxx --BackupType 0 --BackupTime 01:00-02:00 --BackupRetentionPeriod 7` |
| Restore from Backup | `tccli mongodb RestoreDBInstance --InstanceId cmgo-xxxxx --BackupId 12345` |

### Account Management

| Action | CLI Command |
|--------|-------------|
| Create Account | `tccli mongodb CreateAccountUser --InstanceId cmgo-xxxxx --UserName myuser --Password 'MyP@ss123' --AuthRole '[{"Mask":1,"NameSpace":"admin"}]'` |
| List Accounts | `tccli mongodb DescribeAccountUsers --InstanceId cmgo-xxxxx` |
| Set Privilege | `tccli mongodb SetAccountUserPrivilege --InstanceId cmgo-xxxxx --UserName myuser --AuthRole '[{"Mask":3,"NameSpace":"testdb"}]'` |
| Reset Password | `tccli mongodb ResetDBInstancePassword --InstanceId cmgo-xxxxx --UserName myuser --Password 'NewP@ss456'` |

### Parameters

| Action | CLI Command |
|--------|-------------|
| List Params | `tccli mongodb DescribeInstanceParams --InstanceId cmgo-xxxxx` |
| Modify Params | `tccli mongodb ModifyInstanceParams --InstanceId cmgo-xxxxx --InstanceParams '[{"Key":"operationProfiling.slowOpThresholdMs","Value":"200"}]'` |

### SSL & Security

| Action | CLI Command |
|--------|-------------|
| Check SSL | `tccli mongodb DescribeInstanceSSL --InstanceId cmgo-xxxxx` |
| Enable SSL | `tccli mongodb InstanceEnableSSL --InstanceId cmgo-xxxxx --SslSwitch on` |
| Describe SGroup | `tccli mongodb DescribeSecurityGroup --InstanceId cmgo-xxxxx` |
| Modify SGroup | `tccli mongodb ModifyDBInstanceSecurityGroup --InstanceId cmgo-xxxxx --SecurityGroupIds '["sg-xxxxx"]'` |
| Deletion Protection | `tccli mongodb SetDBInstanceDeletionProtection --InstanceId cmgo-xxxxx --ProtectionFlag 1` |

### Audit

| Action | CLI Command |
|--------|-------------|
| Open Audit | `tccli mongodb OpenAuditService --InstanceId cmgo-xxxxx --LogExpireDay 30` |
| Close Audit | `tccli mongodb CloseAuditService --InstanceId cmgo-xxxxx` |
| Query Audit | `tccli mongodb DescribeAuditLogs --InstanceId cmgo-xxxxx --StartTime "2026-05-22 00:00:00" --EndTime "2026-05-29 00:00:00" --Limit 20` |

### Slow Logs & Monitoring

| Action | CLI Command |
|--------|-------------|
| Slow Log Patterns | `tccli mongodb DescribeSlowLogPatterns --InstanceId cmgo-xxxxx --StartTime "2026-05-22 00:00:00" --EndTime "2026-05-29 00:00:00" --SlowMS 100` |
| Detailed Slow Logs | `tccli mongodb DescribeDetailedSlowLogs --InstanceId cmgo-xxxxx --StartTime "2026-05-22 00:00:00" --EndTime "2026-05-29 00:00:00" --SlowMS 100` |
| Current Ops | `tccli mongodb DescribeCurrentOp --InstanceId cmgo-xxxxx` |
| Client Connections | `tccli mongodb DescribeClientConnections --InstanceId cmgo-xxxxx` |
| Node Properties | `tccli mongodb DescribeDBInstanceNodeProperty --InstanceId cmgo-xxxxx` |
| Error Logs | `tccli mongodb DescribeMongodbLogs --InstanceId cmgo-xxxxx --StartTime "2026-05-22 00:00:00" --EndTime "2026-05-29 00:00:00"` |
| Spec Info | `tccli mongodb DescribeSpecInfo --Zone ap-guangzhou` |

### Async Operations

| Action | CLI Command |
|--------|-------------|
| Track Deal | `tccli mongodb DescribeAsyncRequestInfo --DealId "12345678"` |
| Price Inquiry (Create) | `tccli mongodb InquirePriceCreateDBInstances --Zone ap-guangzhou-3 --NodeNum 3 --Memory 4 --Volume 10 --MongoVersion MONGO_60_WT --MachineCode HCD --GoodsNum 1 --ClusterType 0` |

### Price Inquiry

| Action | CLI Command |
|--------|-------------|
| Modify Price | `tccli mongodb InquirePriceModifyDBInstanceSpec --InstanceId cmgo-xxxxx --Memory 8 --Volume 20` |
| Renew Price | `tccli mongodb InquirePriceRenewDBInstances --InstanceId cmgo-xxxxx --Period 1` |

## JSON Output Handling

All tccli mongodb commands return JSON by default. Use `jq` for field extraction:

```bash
# Extract instance ID from list
tccli mongodb DescribeDBInstances --Limit 1 | jq -r '.Response.InstanceDetails[0].InstanceId'

# Extract status
tccli mongodb DescribeDBInstances --InstanceIds '["cmgo-xxxxx"]' | jq -r '.Response.InstanceDetails[0].Status'

# Extract async task status
tccli mongodb DescribeAsyncRequestInfo --DealId "12345678" | jq -r '.Response.Status'

# Count instances
tccli mongodb DescribeDBInstances | jq -r '.Response.TotalCount'

# Extract all instance IDs
tccli mongodb DescribeDBInstances | jq -r '.Response.InstanceDetails[].InstanceId'

# Pretty-print full response
tccli mongodb DescribeDBInstances --InstanceIds '["cmgo-xxxxx"]' | jq '.'
```

## Credential Configuration

```bash
# Environment variables (recommended for agents) — check existence only, never echo values
test -n "$TENCENTCLOUD_SECRET_ID" && echo "✅ SecretId is set" || echo "❌ SecretId missing"
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "✅ SecretKey is set" || echo "❌ SecretKey missing"
test -n "$TENCENTCLOUD_REGION" && echo "✅ Region is set" || echo "❌ Region missing"

# Alternative: CLI config file (~/.tccli/config)
# tccli configure
```

## Coverage Notes

tccli mongodb (version 2019-07-25) covers all 79 API actions. No CLI coverage gaps for this product. All operations can be performed via CLI as the primary path.
