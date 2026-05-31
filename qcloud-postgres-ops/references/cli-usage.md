# CLI Usage — tccli postgres

## Setup

```bash
# Verify CLI support
tccli postgres help

# List all actions
tccli postgres help | grep -E "^\s+[A-Z]"
```

## Command Map

| Operation | CLI Command | Description |
|-----------|-------------|-------------|
| Create | `tccli postgres CreateDBInstances` | Create instance |
| Describe | `tccli postgres DescribeDBInstances` | List/describe instances |
| Modify | `tccli postgres UpgradeDBInstance` | Modify instance spec |
| Isolate | `tccli postgres IsolateDBInstance` | Isolate instance |
| Delete | `tccli postgres DeleteDBInstance` | Delete instance |
| Backup | `tccli postgres CreateBackup` | Create backup |
| Backup List | `tccli postgres DescribeDBBackups` | List backups |
| Restore | `tccli postgres RestoreDBInstance` | Restore instance |
| SSL Status | `tccli postgres DescribeDBInstanceSSL` | Get SSL info |
| SSL Toggle | `tccli postgres ModifyDBInstanceSSL` | Enable/disable SSL |
| Account List | `tccli postgres DescribeAccounts` | List accounts |
| Create Account | `tccli postgres CreateAccount` | Create account |
| Reset Pwd | `tccli postgres ResetAccountPassword` | Reset password |
| Parameters | `tccli postgres DescribeInstanceParameters` | List parameters |
| Modify Params | `tccli postgres ModifyDBInstanceParameters` | Set parameters |
| Slow Queries | `tccli postgres DescribeSlowQueryList` | List slow queries |
| Versions | `tccli postgres DescribeDBVersions` | List PG versions |
| Config | `tccli postgres DescribeProductConfig` | List spec config |
| Security Groups | `tccli postgres DescribeDBInstanceSecurityGroups` | List SGs |
| Modify SGs | `tccli postgres ModifyDBInstanceSecurityGroups` | Bind SGs |

## Common Invocation Patterns

### Use --version always
```bash
tccli postgres DescribeDBInstances --version 2017-03-12 --Limit 20
```

### JSON output (default)
```bash
tccli postgres DescribeDBInstances --Limit 5 | jq '.Response.DBInstanceSet[].DBInstanceId'
```

### Filter by instance ID
```bash
tccli postgres DescribeDBInstances --Filters '[{"Name":"db-instance-id","Values":["postgres-xxxxx"]}]'
```

## Coverage Gaps

| Operation | CLI | SDK | Notes |
|-----------|-----|-----|-------|
| Create DBInstance | ✅ | ✅ | Both paths work |
| Describe DBInstances | ✅ | ✅ | Both paths work |
| Upgrade | ✅ | ✅ | Both paths work |
| Backup | ✅ | ✅ | Both paths work |
| Restore | ✅ | ✅ | Both paths work |
| Account create | ✅ | ✅ | Both paths work |
| SSL toggle | ✅ | ✅ | Both paths work |
| Parameters | ✅ | ✅ | Both paths work |
| Slow logs | ✅ | ✅ | Both paths work |
| Migration | ✅ | ✅ | SDK for complex cases |
| Download backup | ✅ | ✅ | Both paths work |

CLI applicability: `dual-path` — CLI covers all major operations. SDK is fallback.
