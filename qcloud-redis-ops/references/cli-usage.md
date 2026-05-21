# TencentDB for Redis CLI Usage Reference

## Overview

The `tccli redis` command group provides CLI access to TencentDB for Redis operations.

## CLI Command Map

### Instance Lifecycle

| CLI Command | API Method | Description |
|-------------|------------|-------------|
| `tccli redis CreateInstance` | CreateInstance | Create Redis instance |
| `tccli redis DescribeInstances` | DescribeInstances | Query instance detail |
| `tccli redis DescribeInstanceList` | DescribeInstanceList | Paginated instance list |
| `tccli redis IsolateInstance` | IsolateInstance | Soft-delete instance |
| `tccli redis OnlineIsolateInstance` | OnlineIsolateInstance | Online isolate |
| `tccli redis OfflineIsolateInstance` | OfflineIsolateInstance | Offline isolate |
| `tccli redis CleanInstance` | CleanInstance | Hard-delete isolated instance |
| `tccli redis UnIsolateInstance` | UnIsolateInstance | Restore from isolated |

### Instance Management

| CLI Command | API Method | Description |
|-------------|------------|-------------|
| `tccli redis UpgradeInstance` | UpgradeInstance | Upgrade memory/spec |
| `tccli redis AutoRenewInstance` | AutoRenewInstance | Enable auto-renew |
| `tccli redis ManualRenewInstance` | ManualRenewInstance | Manual renewal |
| `tccli redis ModifyInstanceName` | ModifyInstanceName | Rename instance |
| `tccli redis ModifyInstancePassword` | ModifyInstancePassword | Change password |
| `tccli redis ModifyInstanceParams` | ModifyInstanceParams | Modify runtime params |
| `tccli redis DescribeParamTemplateInfo` | DescribeParamTemplateInfo | Query param templates |

### Backup

| CLI Command | API Method | Description |
|-------------|------------|-------------|
| `tccli redis DescribeInstanceBackupRecords` | DescribeInstanceBackupRecords | List backups |
| `tccli redis DescribeAutoBackupConfig` | DescribeAutoBackupConfig | Get backup config |
| `tccli redis ModifyAutoBackupConfig` | ModifyAutoBackupConfig | Set backup schedule |

### Product Info

| CLI Command | API Method | Description |
|-------------|------------|-------------|
| `tccli redis DescribeProductInfo` | DescribeProductInfo | Query available specs |
| `tccli redis DescribeInstanceDealDetail` | DescribeInstanceDealDetail | Trade details |

### Security

| CLI Command | API Method | Description |
|-------------|------------|-------------|
| `tccli redis DescribeInstanceSecurityGroups` | DescribeInstanceSecurityGroups | List security groups |
| `tccli redis AssociateSecurityGroups` | AssociateSecurityGroups | Bind security groups |
| `tccli redis DisassociateSecurityGroups` | DisassociateSecurityGroups | Unbind security groups |

### Monitoring

| CLI Command | API Method | Description |
|-------------|------------|-------------|
| `tccli redis DescribeInstanceMonitorToCloudMonitor` | DescribeInstanceMonitorToCloudMonitor | Monitor data |
| `tccli redis DescribeInstanceMonitorBigKey` | DescribeInstanceMonitorBigKey | Big key analysis |

## CLI Invocation Patterns

```bash
# List all instances
tccli redis DescribeInstanceList --Region ap-guangzhou --Offset 0 --Limit 100

# Get specific instance
tccli redis DescribeInstances --Region ap-guangzhou --InstanceId "crs-xxxxxxxx"

# Extract endpoint
tccli redis DescribeInstances --Region ap-guangzhou --InstanceId "crs-xxxxxxxx" \
  | jq -r '.Response.InstanceSet[0] | "Endpoint: \(.Ip):\(.Port)"'

# Check backup records
tccli redis DescribeInstanceBackupRecords \
  --InstanceId "crs-xxxxxxxx" \
  --BeginTime "2026-05-20 00:00:00" \
  --EndTime "2026-05-21 23:59:59"

# Help
tccli redis help
tccli redis help CreateInstance
```

## Coverage Gap Analysis

CLI covers the vast majority of Redis API operations. All critical lifecycle operations (create, describe, upgrade, backup, isolate, clean) are fully exposed via CLI. SDK fallback is recommended only for complex parameter construction or batch operations involving multiple instances with different configurations.